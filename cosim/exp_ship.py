#!/usr/bin/env python3
"""Load the ship-scene savestate, run ~150 frames, screenshot at intervals.

Used to iterate quickly on the ship-scene black-background bug: rebuild the
exe with a patch, load the state, and compare the screenshots."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from semantic_cosim import DebugClient, kill_process, wait_client  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "build" / "Release" / "StarOcean.exe"
OUT = ROOT / "build-cosim" / "ship-exp"
STATE = str((ROOT / "build-cosim" / "ship-lines" / "ship14900.state").resolve())
START = int(sys.argv[1]) if len(sys.argv) > 1 else 14902
N = int(sys.argv[2]) if len(sys.argv) > 2 else 160
SHOTS = [int(x) for x in sys.argv[3:]] or [14920, 14960, 15000, 15040]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        time.sleep(2)

    log = (OUT / "runner.stderr.log").open("wb")
    proc = subprocess.Popen([str(EXE)], cwd=str(EXE.parent),
                            stdout=subprocess.DEVNULL, stderr=log)
    try:
        client = wait_client(60)
        resp = client.cmd(f"load_state {STATE}", timeout=30)
        print(f"[exp] load_state: {resp[:120]}")
        time.sleep(0.3)
        cur = client.frame()
        print(f"[exp] state at frame {cur}")
        shot_set = set(SHOTS)
        end = START + N
        while cur < end:
            client.controller(0)
            cur = client.frame()
            if cur in shot_set:
                bmp = OUT / f"exp_{cur:05d}.bmp"
                ok = client.screenshot(bmp)
                ppu = client.ppu()
                print(f"  [{cur}] shot={ok} tm={ppu.get('screenEnabled')} "
                      f"mode={ppu.get('bgmode')} inidisp={ppu.get('inidisp')}")
        print("[exp] done")
    finally:
        log.close()
        try:
            client.close()
        except Exception:
            pass
        kill_process(proc)


if __name__ == "__main__":
    main()
