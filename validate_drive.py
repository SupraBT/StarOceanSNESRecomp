#!/usr/bin/env python3
"""Validate the recorded A-press timing: drive title -> name selection with
frame-accurate set_controller presses and report the resulting PPU state.

The press frames come from so_inputs_timed.log, recorded from a manual play
session (see NAME_SCREEN_PRESSES in so_drive.py).
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, ".")
from so_drive import connect, cmd, kill_tree, drive_to_namescreen, BASE

EXE = os.path.join(BASE, "build", "Release", "StarOcean.exe")
ROM = os.path.join(BASE, "build", "Release", "Star Ocean (Japan).sfc")

env = dict(os.environ)
for k in ("SNESRECOMP_INPUT_MODE", "SNESRECOMP_INPUT_FILE"):
    env.pop(k, None)

p = subprocess.Popen([EXE, ROM, "--paused"], env=env,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    sock = connect()
    if not sock:
        print("FAIL: no debug server")
        sys.exit(1)
    cmd(sock, "continue")
    ok = drive_to_namescreen(sock)
    print("presses delivered: %s" % ok)

    # Wait for the menu to settle and populate (a few frames after last press).
    time.sleep(1.0)
    d = json.loads(cmd(sock, "get_ppu_state"))
    print("inidisp=%s bgmode=%d bgTileAdr=%s bgXsc=%s" % (
        d.get("inidisp"), d.get("bgmode"), d.get("bgTileAdr"), d.get("bgXsc")))

    # Occupancy of each tilemap (word-space: maps live at $4800/$4C00/$5000/$5800).
    for word, name in ((0x4800, "BG1"), (0x4C00, "BG2"), (0x5000, "BG3"), (0x5800, "BG4")):
        r = cmd(sock, "dump_vram 0x%x 0x800" % (word * 2))
        try:
            hexs = json.loads(r)["hex"].split()
            # count non-zero 16-bit entries
            nonz = sum(1 for i in range(0, len(hexs) - 1, 2)
                       if hexs[i] != "00" or hexs[i + 1] != "00")
            print("  %s map $%04x: %d/1024 entries" % (name, word, nonz))
        except Exception as e:
            print("  %s map $%04x: parse failed (%r)" % (name, word, r[:80]))

    sock.close()
finally:
    kill_tree(p)
