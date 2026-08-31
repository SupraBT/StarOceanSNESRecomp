#!/usr/bin/env python3
"""Load the verified ship savestate, run ~50 frames, screenshot + pixel report."""
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
N = int(sys.argv[1]) if len(sys.argv) > 1 else 50


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        time.sleep(2)
    log = (OUT / "exp2.stderr.log").open("wb")
    proc = subprocess.Popen([str(EXE)], cwd=str(EXE.parent),
                            stdout=subprocess.DEVNULL, stderr=log)
    try:
        client = wait_client(60)
        r = client.cmd(f"load_state {STATE}", timeout=30)
        print(f"[exp2] load: {r[:80]}")
        # The emulation thread keeps running during load and re-boots a couple
        # frames later, so screenshot IMMEDIATELY after the load returns.
        bmp = OUT / "x00000.bmp"
        ok = client.screenshot(bmp)
        p = client.ppu()
        from PIL import Image
        try:
            im = Image.open(bmp).convert("RGB")
            px = list(im.getdata())
            nb = sum(1 for r, g, b in px if r > 8 or g > 8 or b > 8)
            pct = 100 * nb / len(px)
        except Exception:
            pct = -1
        print(f"[exp2] shot={ok} nb={pct:.1f}% mode={p['bgmode']} "
              f"tm={p['screenEnabled']} bgXsc={p['bgXsc']} inidisp={p['inidisp']}")
        print("[exp2] done")
        client.close()
    finally:
        log.close()
        kill_process(proc)


if __name__ == "__main__":
    main()
