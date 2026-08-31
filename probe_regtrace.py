#!/usr/bin/env python3
"""Capture the runner's $2105-$2133 + $4800-$4807 write sequence at the
populated name screen, via the debug server reg-trace ring.

Usage: python probe_regtrace.py [input_log] [outfile.json] [max_seconds]
"""

import json
import os
import socket
import subprocess
import sys
import time

PORT = 13308
BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2"
LOG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "so_inputs.log")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, "build-trace", "regtrace.json")
MAX_TOTAL = int(sys.argv[3]) if len(sys.argv) > 3 else 45
EXE = os.path.join(BASE, "build-trace", "StarOcean.exe")
ROM = os.path.join(BASE, "build-trace", "Star Ocean (Japan).sfc")

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


def cmd(sock, line, timeout=20):
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


def main():
    from so_drive import launch_and_drive
    p, sock, logf = launch_and_drive(
        EXE, ROM, log_path=os.path.join(os.path.dirname(OUT), "regtrace_stderr.log"))
    t0 = time.time()
    if sock is None:
        print("DEBUG SERVER NOT REACHABLE")
        kill_tree(p)
        logf.close()
        return
    # Arm reg-trace ranges (reset first). Deliberately EXCLUDE $2118/$2119
    # (VRAM data port) — the name-screen load spams thousands of writes per
    # frame and would bury the 32K ring before BGMODE/S-DD1 events arrive.
    print("reset:", cmd(sock, "trace_reg_reset")[:60])
    for lo, hi in (("2105", "2105"),   # BGMODE
                   ("2107", "210c"),   # BG tilemap/tile-data addrs (BG1SC..BG34NBA)
                   ("2115", "2117"),   # VMAIN/VMADD
                   ("2121", "2133"),   # CGRAM addr/data + window/color math
                   ("4800", "4807")):  # S-DD1 control + MMC
        # NOTE: $210D-$2114 (BG scroll regs) deliberately excluded — the game
        # writes BG1HOFS ($210D) thousands of times per frame during the menu
        # load, burying the 32K ring before BGMODE/S-DD1 arrive.
        r = cmd(sock, "trace_reg %s %s" % (lo, hi))
        print("arm %s-%s:" % (lo, hi), r[:60])
    entered = False
    entry_t = 0.0
    dumped = False
    try:
        while True:
            now = time.time() - t0
            if now > MAX_TOTAL:
                print("TIMEOUT after %.1fs" % now)
                break
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
            if entered and not dumped:
                waited = now - entry_t
                vr = cmd(sock, "dump_vram 0x4800 1024")
                blob = parse_hex_blob(vr)
                entries = 0
                if blob is not None:
                    words = [blob[i] | (blob[i + 1] << 8) for i in range(0, len(blob), 2)]
                    entries = sum(1 for w in words if w != 0)
                print("t=%5.1fs wait=%.1fs BG1 tilemap: %d/1024" % (now, waited, entries))
                if entries >= POPULATED_ENTRIES or waited >= POPULATE_WINDOW:
                    resp = cmd(sock, "get_reg_trace nostack")
                    print("get_reg_trace len:", len(resp))
                    try:
                        data = json.loads(resp)
                        with open(OUT, "w") as f:
                            json.dump(data, f, indent=1)
                        print("entries:", data.get("entries"), "-> saved", OUT)
                        # Show BGMODE + S-DD1 writes summary
                        bg = [e for e in data.get("log", []) if e["adr"] == "0x2105"]
                        sd = [e for e in data.get("log", []) if e["adr"] in ("0x4806", "0x4807")]
                        print("BGMODE writes:", [(e["f"], e["val"]) for e in bg])
                        print("S-DD1 MMC writes ($4806/7): %d total" % len(sd))
                        for e in sd[:6]:
                            print("  f=%d %s=%s func=%s" % (e["f"], e["adr"], e["val"], e.get("func")))
                    except Exception as ex:
                        print("parse fail:", ex, resp[:200])
                    dumped = True
                    print("DONE (total %.1fs)" % (time.time() - t0))
                    break
            time.sleep(1.0)
    finally:
        if sock:
            sock.close()
        kill_tree(p)
        logf.close()
    print("done")


if __name__ == "__main__":
    main()
