#!/usr/bin/env python3
"""Replay a recorded input log and grab the name-screen state quickly.

Flow: launch trace build with the replay log -> poll PPU until the Mode 0
name screen appears -> wait until it is populated -> dump VRAM/CGRAM/BMP ->
kill the game and exit. Total ~15-20s, no idle tail.

Usage: python probe_replay.py [input_log] [outdir] [max_seconds]
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
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, "build-trace", "verify_replay")
MAX_TOTAL = int(sys.argv[3]) if len(sys.argv) > 3 else 45
EXE = os.path.join(BASE, "build-trace", "StarOcean.exe")
ROM = os.path.join(BASE, "build-trace", "Star Ocean (Japan).sfc")

# Once the Mode 0 name screen appears, allow this many seconds for the
# tilemaps to populate, then dump. ~40 frames of S-DD1 loading at 26fps.
POPULATE_WINDOW = 8.0
# Tilemap entries considered "populated" (populated state has 542).
POPULATED_ENTRIES = 400

os.makedirs(OUT, exist_ok=True)


def connect(retries=60):
    for _ in range(retries):
        try:
            s = socket.create_connection(("127.0.0.1", PORT), timeout=2)
            return s
        except OSError:
            time.sleep(0.25)
    return None


def cmd(sock, line, timeout=15):
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


def ppu_summary(st):
    try:
        d = json.loads(st)
        return (d.get("bgmode"), d.get("bgTileAdr"), d.get("inidisp"),
                d.get("screenEnabled", [None, None])[0])
    except Exception:
        return None


def tilemap_entries(blob, tm_word):
    words = [blob[i] | (blob[i + 1] << 8) for i in range(0, len(blob), 2)]
    return sum(1 for w in words[tm_word:tm_word + 0x400] if w != 0)


def analyze_vram(blob, tag, outdir):
    words = [blob[i] | (blob[i + 1] << 8) for i in range(0, len(blob), 2)]
    blocks = []
    for b in range(0, 0x8000, 0x800):
        nz = sum(1 for w in words[b:b + 0x400] if w != 0)
        if nz:
            blocks.append("%04X:%d" % (b * 2, nz))
    print("VRAM nonzero blocks (%s): %s" % (tag, " ".join(blocks)))
    for name, tm in (("BG1", 0x4800), ("BG2", 0x4C00), ("BG3", 0x5000), ("BG4", 0x5800)):
        nz = sum(1 for w in words[tm // 2:tm // 2 + 0x400] if w != 0)
        print("  tilemap %s @ %04X: %d/1024 entries nonzero" % (name, tm, nz))
    with open(os.path.join(outdir, "vram_%s.bin" % tag), "wb") as f:
        f.write(blob)


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
        EXE, ROM, log_path=os.path.join(OUT, "stderr.log"))
    t0 = time.time()
    if sock is None:
        print("DEBUG SERVER NOT REACHABLE")
        kill_tree(p)
        logf.close()
        return
    entered = False
    entry_t = 0.0
    dumped = False
    try:
        while True:
            now = time.time() - t0
            if now > MAX_TOTAL:
                print("TIMEOUT after %.1fs - game never reached name screen" % now)
                break
            st = cmd(sock, "get_ppu_state")
            summ = ppu_summary(st)
            if summ:
                mode, tileadr, inidisp, screen = summ
                if not entered and mode == 0 and tileadr == "0x4222" and inidisp != "0x00":
                    entered = True
                    entry_t = now
                    print("t=%5.1fs NAME SCREEN ENTRY (bgmode=0 bgTileAdr=0x4222)" % now)
                if entered and not dumped:
                    waited = now - entry_t
                    # Wait for population, but dump once and exit fast.
                    vr = cmd(sock, "dump_vram 0x0 65536")
                    blob = parse_hex_blob(vr)
                    entries = tilemap_entries(blob, 0x4800 // 2) if blob else 0
                    print("t=%5.1fs wait=%.1fs BG1 tilemap: %d/1024 entries"
                          % (now, waited, entries))
                    if entries >= POPULATED_ENTRIES or waited >= POPULATE_WINDOW:
                        tag = "t%d" % int(now)
                        print("===== POPULATED, dumping =====")
                        if blob is not None:
                            analyze_vram(blob, tag, OUT)
                        cg = cmd(sock, "dump_cgram")
                        cgram = parse_hex_blob(cg)
                        if cgram is not None:
                            with open(os.path.join(OUT, "cgram_%s.bin" % tag), "wb") as f:
                                f.write(cgram)
                            cnz = sum(1 for i in range(0, 512, 2)
                                      if (cgram[i] | (cgram[i + 1] << 8)) != 0)
                            print("CGRAM: nonzero colors %d/256" % cnz)
                        shot = cmd(sock, "screenshot %s.bmp"
                                   % os.path.join(OUT, "shot_%s" % tag).replace("\\", "/"))
                        print("SHOT:", shot[:110])
                        dumped = True
                        print("DONE - closing game now (total %.1fs)" % (time.time() - t0))
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
