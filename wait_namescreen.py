#!/usr/bin/env python3
"""Launch the game and wait for a HUMAN to press A (3 times) to reach the
name-selection screen, then capture VRAM/CGRAM/screenshot as evidence.

Usage: python wait_namescreen.py [max_seconds]
"""
import json
import os
import sys
import time

sys.path.insert(0, ".")
from so_drive import launch_and_drive, cmd, kill_tree

BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2"
EXE = os.path.join(BASE, "build-trace", "StarOcean.exe")
ROM = os.path.join(BASE, "build-trace", "Star Ocean (Japan).sfc")
MAX_S = int(sys.argv[1]) if len(sys.argv) > 1 else 240

p, sock, logf = launch_and_drive(
    EXE, ROM, log_path=os.path.join(BASE, "build-trace", "wait_namescreen.log"))
if sock is None:
    print("DEBUG SERVER NOT REACHABLE")
    kill_tree(p)
    sys.exit(1)

print(">>> Window abierta. Cuando veas el título, pulsa A 3 veces (tecla X) para llegar al menú de selección de nombre.")
t0 = time.time()
seen = False
try:
    while time.time() - t0 < MAX_S:
        st = cmd(sock, "get_ppu_state")
        try:
            d = json.loads(st)
            mode, inidisp = d.get("bgmode"), d.get("inidisp")
        except Exception:
            mode = inidisp = None
        if mode == 0 and inidisp == "0x0f":
            if not seen:
                seen = True
                print("MODE 0 (menú) a t=%.1fs — esperando población..." % (time.time() - t0))
            v = bytes.fromhex(json.loads(cmd(sock, "dump_vram 0 65536"))["hex"])
            b = v[0x9000:0x9000 + 2048]
            nz = sum(1 for k in range(0, len(b), 2) if b[k] | b[k + 1])
            if nz >= 400:
                c = bytes.fromhex(json.loads(cmd(sock, "dump_cgram"))["hex"])
                open(os.path.join(BASE, "build-trace", "verify_replay", "vram_human.bin"), "wb").write(v)
                open(os.path.join(BASE, "build-trace", "verify_replay", "cgram_human.bin"), "wb").write(c)
                shot = os.path.join(BASE, "build-trace", "name_human.bmp").replace("\\", "/")
                cmd(sock, "screenshot %s" % shot)
                print("CAPTURED at t=%.1fs: BG1=%d/1024 (vram_human.bin, cgram_human.bin, name_human.bmp)" % (time.time() - t0, nz))
                break
        if int(time.time() - t0) % 10 == 0:
            print("  esperando... t=%ds mode=%s inidisp=%s" % (int(time.time() - t0), mode, inidisp))
        time.sleep(0.2)
    if not seen:
        print("TIMEOUT: mode 0 nunca apareció (t=%ds, mode=%s inidisp=%s)" % (int(time.time() - t0), mode, inidisp))
finally:
    sock.close()
    kill_tree(p)
    logf.close()
