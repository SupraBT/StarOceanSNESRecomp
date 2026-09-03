#!/usr/bin/env python3
"""Race-free ship-scene experiment: park the emulation with run_to_frame,
load the savestate, resume, then screenshot at visible frames."""
from __future__ import annotations

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
STATE = str((OUT / "ship15040.state").resolve())
N = int(sys.argv[1]) if len(sys.argv) > 1 else 40


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        time.sleep(2)
    log = (OUT / "exp3.stderr.log").open("wb")
    proc = subprocess.Popen([str(EXE)], cwd=str(EXE.parent),
                            stdout=subprocess.DEVNULL, stderr=log)
    try:
        client = wait_client(60)
        print("[exp3] park:", client.cmd("run_to_frame 8", timeout=10)[:80])
        time.sleep(1.0)  # let the emulation reach the target and park
        print("[exp3] load:", client.cmd(f"load_state {STATE}", timeout=30)[:80])
        time.sleep(0.3)
        print("[exp3] resume:", client.cmd("continue", timeout=5)[:60])
        # pace frames, screenshot at visible ones
        base = client.frame()
        shots = 0
        cur = base
        end = base + N
        while cur < end:
            client.controller(0)
            cur = client.frame()
            p = client.ppu()
            vis = (int(p["inidisp"], 16) & 0x0F) != 0 and not (int(p["inidisp"], 16) & 0x80)
            if vis and cur >= base + 2:
                bmp = OUT / f"e{cur:05d}.bmp"
                ok = client.screenshot(bmp)
                from PIL import Image
                try:
                    im = Image.open(bmp).convert("RGB")
                    px = list(im.getdata())
                    nb = sum(1 for r, g, b in px if r > 8 or g > 8 or b > 8)
                    pct = 100 * nb / len(px)
                except Exception:
                    pct = -1
                print(f"  [{cur}] shot={ok} nb={pct:.1f}% mode={p['bgmode']} "
                      f"tm={p['screenEnabled']} bgXsc={p['bgXsc']} inidisp={p['inidisp']}")
                shots += 1
                if shots >= 4:
                    break
        print(f"[exp3] done ({shots} shots)")
        client.close()
    finally:
        log.close()
        kill_process(proc)


if __name__ == "__main__":
    main()
