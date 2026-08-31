#!/usr/bin/env python3
"""Trace the PPU mode trajectory of the trace build (no input) to learn at
which snes_frame_counter values the title and name menu appear."""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, ".")
from so_drive import connect, cmd, kill_tree, BASE

EXE = os.path.join(BASE, "build-trace", "StarOcean.exe")
ROM = os.path.join(BASE, "build-trace", "Star Ocean (Japan).sfc")

env = dict(os.environ)
for k in ("SNESRECOMP_INPUT_MODE", "SNESRECOMP_INPUT_FILE"):
    env.pop(k, None)

p = subprocess.Popen([EXE, ROM], env=env,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    sock = connect()
    if not sock:
        print("FAIL: no debug server")
        sys.exit(1)
    t0 = time.time()
    last = None
    while time.time() - t0 < 45:
        try:
            fr = int(json.loads(cmd(sock, "frame"))["frame"])
            st = json.loads(cmd(sock, "get_ppu_state"))
            mode, inidisp, tile = st.get("bgmode"), st.get("inidisp"), st.get("bgTileAdr")
            key = (mode, inidisp, tile)
            if key != last:
                print("t=%6.1fs frame=%6d mode=%s inidisp=%s bgTileAdr=%s" % (
                    time.time() - t0, fr, mode, inidisp, tile))
                last = key
        except Exception as e:
            pass
        time.sleep(0.5)
    sock.close()
finally:
    kill_tree(p)
