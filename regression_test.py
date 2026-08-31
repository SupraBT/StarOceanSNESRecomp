#!/usr/bin/env python3
"""Regression test for the name screen (Fase 0).

Reproduces so_inputs.log in the trace build, waits until the Mode 0 name
screen is populated, then dumps VRAM/CGRAM/WRAM from the historical ring
at a FIXED frame and compares SHA-256 hashes against stored references.

Usage:
  python regression_test.py --store [log] [max_seconds]   # save reference
  python regression_test.py        [log] [max_seconds]   # check (default)
Exits 0 on PASS, 1 on FAIL/mismatch.

The ring snapshot is taken at the same frame number every run (deterministic
replay), so the animated $C000 region is identical too. WRAM is included so
a regression in CPU/DMA/S-DD1 state is caught even before it reaches VRAM.
"""

import hashlib
import json
import os
import socket
import subprocess
import sys
import time

PORT = 13308
BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2"
STORE = len(sys.argv) > 1 and sys.argv[1] == "--store"
ARGI = 2 if STORE else 1
LOG = sys.argv[ARGI] if len(sys.argv) > ARGI else os.path.join(BASE, "so_inputs.log")
MAX_TOTAL = int(sys.argv[ARGI + 1]) if len(sys.argv) > ARGI + 1 else 45
EXE = os.path.join(BASE, "build-trace", "StarOcean.exe")
ROM = os.path.join(BASE, "build-trace", "Star Ocean (Japan).sfc")
REF = os.path.join(BASE, "build-trace", "namescreen_ref.json")

POPULATE_WINDOW = 8.0
POPULATED_ENTRIES = 400


def connect(retries=60):
    for _ in range(retries):
        try:
            s = socket.create_connection(("127.0.0.1", PORT), timeout=2)
            return s
        except OSError:
            time.sleep(0.25)
    return None


def cmd(sock, line, timeout=30):
    sock.sendall((line + "\n").encode())
    sock.settimeout(timeout)
    buf = b""
    while not buf.endswith(b"}\n"):
        try:
            chunk = sock.recv(1 << 20)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
    return buf.decode("utf-8", errors="replace").strip()


def parse_hex_blob(resp):
    try:
        return bytes.fromhex(json.loads(resp).get("hex", ""))
    except Exception:
        return None


def sha(b):
    return hashlib.sha256(b).hexdigest()


def kill_tree(p):
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                       capture_output=True, timeout=10)
    except Exception:
        pass
    try:
        p.kill()
        p.wait(timeout=5)
    except Exception:
        pass


def tilemap_entries(blob, tm_word):
    words = [blob[i] | (blob[i + 1] << 8) for i in range(0, len(blob), 2)]
    return sum(1 for w in words[tm_word:tm_word + 0x400] if w != 0)


def capture():
    from so_drive import launch_and_drive
    p, sock, logf = launch_and_drive(
        EXE, ROM, log_path=os.path.join(BASE, "build-trace", "regression_stderr.log"))
    t0 = time.time()
    if sock is None:
        print("DEBUG SERVER NOT REACHABLE")
        kill_tree(p)
        logf.close()
        return None
    entered = False
    entry_t = 0.0
    try:
        while True:
            now = time.time() - t0
            if now > MAX_TOTAL:
                print("TIMEOUT after %.1fs - name screen never populated" % now)
                return None
            st = cmd(sock, "get_ppu_state")
            try:
                d = json.loads(st)
                mode, tileadr, inidisp = d.get("bgmode"), d.get("bgTileAdr"), d.get("inidisp")
            except Exception:
                mode = tileadr = inidisp = None
            if not entered and mode == 0 and tileadr == "0x4222" and inidisp != "0x00":
                entered = True
                entry_t = now
                print("t=%5.1fs NAME SCREEN ENTRY" % now)
            if entered:
                waited = now - entry_t
                vr = cmd(sock, "dump_vram 0x4800 1024")
                blob = parse_hex_blob(vr)
                entries = tilemap_entries(blob, 0) if blob else 0
                print("t=%5.1fs wait=%.1fs BG1 tilemap: %d/1024" % (now, waited, entries))
                if entries >= POPULATED_ENTRIES or waited >= POPULATE_WINDOW:
                    # The ring only contains frames up to the last COMPLETED
                    # frame (newest from `history`), so dump that exact frame
                    # for determinism. Also grab a screenshot for the record.
                    shot = cmd(sock, "screenshot %s.bmp"
                               % os.path.join(BASE, "build-trace", "regression_shot.bmp")
                               .replace("\\", "/"))
                    hist = cmd(sock, "history")
                    try:
                        frame = json.loads(hist)["history"]["newest"]
                    except Exception:
                        frame = None
                    if frame is None:
                        print("could not get newest frame:", hist[:120])
                        return None
                    print("capturing frame %d (ring newest)..." % frame)
                    # Dump the three rings at the SAME frame (deterministic).
                    v = parse_hex_blob(cmd(sock, "dump_frame_vram %d 0 65536" % frame))
                    c = parse_hex_blob(cmd(sock, "dump_frame_cgram %d" % frame))
                    w = parse_hex_blob(cmd(sock, "dump_frame_wram %d 0 131072" % frame))
                    if v is None or c is None or w is None or len(v) != 0x10000 or len(w) != 0x20000:
                        print("incomplete ring dumps v=%s c=%s w=%s"
                              % (len(v) if v else None, len(c) if c else None,
                                 len(w) if w else None))
                        return None
                    return {"frame": frame,
                            "vram_sha256": sha(v),
                            "cgram_sha256": sha(c),
                            "wram_sha256": sha(w),
                            "bg1_tilemap_entries": entries,
                            "captured_at_s": round(time.time() - t0, 1)}
    finally:
        if sock:
            sock.close()
        kill_tree(p)
        logf.close()


def main():
    data = capture()
    if data is None:
        print("FAIL: capture failed")
        sys.exit(1)
    print("captured: frame=%d bg1_entries=%d" % (data["frame"], data["bg1_tilemap_entries"]))
    print("  vram_sha256  = %s" % data["vram_sha256"])
    print("  cgram_sha256 = %s" % data["cgram_sha256"])
    print("  wram_sha256  = %s" % data["wram_sha256"])
    if STORE:
        with open(REF, "w") as f:
            json.dump(data, f, indent=1)
        print("REFERENCE STORED -> %s" % REF)
        sys.exit(0)
    if not os.path.exists(REF):
        print("FAIL: no reference at %s - run with --store first" % REF)
        sys.exit(1)
    ref = json.load(open(REF))
    fails = []
    for k in ("vram_sha256", "cgram_sha256", "wram_sha256"):
        if data[k] != ref.get(k):
            fails.append(k)
    if fails:
        print("FAIL: %d hash(es) differ:" % len(fails))
        for k in fails:
            print("  %s: ref=%s got=%s" % (k, ref.get(k), data[k]))
        print("  (reference frame %d, this frame %d)"
              % (ref.get("frame"), data["frame"]))
        sys.exit(1)
    print("PASS: VRAM/CGRAM/WRAM hashes match reference (frame %d)" % data["frame"])
    sys.exit(0)


if __name__ == "__main__":
    main()
