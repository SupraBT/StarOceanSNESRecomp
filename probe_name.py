#!/usr/bin/env python3
"""Long probe: dump full VRAM + CGRAM + screenshot at several times.

Usage: python probe_name.py [exe] [rom] [outdir] [total_seconds]
"""

import json
import os
import socket
import subprocess
import sys
import time

PORT = 13308
BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2"
EXE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "build-trace", "StarOcean.exe")
ROM = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, "build-trace", "Star Ocean (Japan).sfc")
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(BASE, "build-trace", "verify")
TOTAL = int(sys.argv[4]) if len(sys.argv) > 4 else 70

os.makedirs(OUT, exist_ok=True)
QUERY_TIMES = sorted(set([20, 30, 40, 50, 60, TOTAL]))


def connect(retries=40):
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
    while b"\n" not in buf:
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
        data = json.loads(resp)
        return bytes.fromhex(data.get("hex", ""))
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


def analyze_vram(blob, tag):
    """Report nonzero words per 0x800-byte VRAM block + detect Mode0 tilemaps."""
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


def main():
    log = open(os.path.join(OUT, "stderr.log"), "wb")
    p = subprocess.Popen([EXE, ROM], stderr=log, stdout=subprocess.DEVNULL)
    t0 = time.time()
    qi = 0
    sock = None
    try:
        while time.time() - t0 < TOTAL and qi < len(QUERY_TIMES):
            now = time.time() - t0
            if now >= QUERY_TIMES[qi]:
                if sock is None:
                    sock = connect()
                    if sock is None:
                        print("t=%4.1f DEBUG SERVER NOT REACHABLE" % now)
                        qi += 1
                        continue
                tag = "t%d" % int(now)
                print("===== t=%4.1fs (%s) =====" % (now, tag))
                st = cmd(sock, "get_ppu_state")
                print("PPU:", st[:300])
                vr = cmd(sock, "dump_vram 0x0 65536")
                blob = parse_hex_blob(vr)
                if blob is not None and len(blob) == 0x10000:
                    with open(os.path.join(OUT, "vram_%s.bin" % tag), "wb") as f:
                        f.write(blob)
                    analyze_vram(blob, tag)
                else:
                    print("VRAM dump FAILED (len=%r)" % (len(blob) if blob else None))
                cg = cmd(sock, "dump_cgram")
                cgram = parse_hex_blob(cg)
                if cgram is not None and len(cgram) == 512:
                    with open(os.path.join(OUT, "cgram_%s.bin" % tag), "wb") as f:
                        f.write(cgram)
                    cnz = sum(1 for i in range(0, 512, 2)
                              if (cgram[i] | (cgram[i + 1] << 8)) != 0)
                    print("CGRAM: nonzero colors %d/256" % cnz)
                else:
                    print("CGRAM dump FAILED")
                shot = cmd(sock, "screenshot %s.bmp" % os.path.join(OUT, "shot_%s" % tag))
                print("SHOT:", shot[:120])
                qi += 1
            time.sleep(0.2)
    finally:
        if sock:
            sock.close()
        kill_tree(p)
        log.close()
    print("done")


if __name__ == "__main__":
    main()
