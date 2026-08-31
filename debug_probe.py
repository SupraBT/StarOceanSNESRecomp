#!/usr/bin/env python3
"""Launch the game and probe the TCP debug server (port 13308).

Usage: python debug_probe.py [exe] [out_prefix] [seconds]
Queries at several time points: get_ppu_state, dump_vram (name-screen
tilemap ranges), dump_cgram, and screenshot -> <prefix>_t<N>.bmp.
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
PREFIX = sys.argv[3] if len(sys.argv) > 3 else "probe"
TOTAL = int(sys.argv[4]) if len(sys.argv) > 4 else 18

QUERY_TIMES = sorted(set([4, 6, 8, 10, 12, 14, 16, TOTAL]))


def connect(retries=40):
    for _ in range(retries):
        try:
            s = socket.create_connection(("127.0.0.1", PORT), timeout=2)
            return s
        except OSError:
            time.sleep(0.25)
    return None


def cmd(sock, line, timeout=8):
    sock.sendall((line + "\n").encode())
    sock.settimeout(timeout)
    buf = b""
    while b"\n" not in buf:
        try:
            chunk = sock.recv(65536)
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


def main():
    log = open(PREFIX + "_stderr.log", "wb")
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
                print("===== t=%4.1fs =====" % now)
                st = cmd(sock, "get_ppu_state")
                print("PPU:", st[:400])
                vr = cmd(sock, "dump_vram 0x4800 1024")
                blob = parse_hex_blob(vr)
                if blob is not None:
                    words = [blob[i] | (blob[i + 1] << 8) for i in range(0, len(blob), 2)]
                    nz = sum(1 for w in words if w != 0)
                    print("VRAM[4800-4BFF]: nonzero words %d/%d" % (nz, len(words)))
                vr2 = cmd(sock, "dump_vram 0x5000 1024")
                blob2 = parse_hex_blob(vr2)
                if blob2 is not None:
                    words2 = [blob2[i] | (blob2[i + 1] << 8) for i in range(0, len(blob2), 2)]
                    nz2 = sum(1 for w in words2 if w != 0)
                    print("VRAM[5000-53FF]: nonzero words %d/%d" % (nz2, len(words2)))
                cg = cmd(sock, "dump_cgram")
                try:
                    cj = json.loads(cg)
                    hexv = cj.get("hex", "")
                    cgram = bytes.fromhex(hexv) if hexv else b""
                    cnz = sum(1 for i in range(0, len(cgram), 2)
                              if (cgram[i] | (cgram[i + 1] << 8)) != 0)
                    print("CGRAM: nonzero colors %d/%d" % (cnz, len(cgram) // 2))
                except Exception:
                    print("CGRAM: parse fail", cg[:120])
                shot = cmd(sock, "screenshot %s_t%.0f.bmp" % (PREFIX, now))
                print("SHOT:", shot[:160])
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
