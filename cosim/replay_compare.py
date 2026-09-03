#!/usr/bin/env python3
"""Frame-accurate replay of intro_101648_inputs.txt against the recomp exe.

Paces off the debug server's frame counter: for every emulated frame it sets
the controller mask for the frame the server is about to run, so the inputs
stay aligned with the .bsv recording regardless of emulation speed.

Captures, in the ship-scene window [FIRST..LAST]:
  - ppu state JSON every frame (small)
  - VRAM dump every VRAM_STEP frames
  - screenshot BMP every SHOT_STEP frames

Artifacts land in OUT. Cleanly kills the exe afterwards.
"""
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
EVENTS = ROOT / "cosim" / "intro_101648_inputs.txt"
EXE = ROOT / "build" / "Release" / "StarOcean.exe"
OUT = ROOT / "build-cosim" / "ship-replay"
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else 13800
LAST = int(sys.argv[2]) if len(sys.argv) > 2 else 16600
VRAM_STEP = int(sys.argv[3]) if len(sys.argv) > 3 else 10
SHOT_STEP = int(sys.argv[4]) if len(sys.argv) > 4 else 25


def parse_events(path: Path):
    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            a, b, c = line.split(":")
            events.append((int(a), int(b), int(c, 16)))
    return events


def events_to_frames(events):
    if not events:
        return []
    last = events[-1][0] + events[-1][1]
    frames = [0] * last
    for start, dur, mask in events:
        for i in range(start, min(start + dur, last)):
            frames[i] = mask
    return frames


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames = events_to_frames(parse_events(EVENTS))
    print(f"[replay] {len(frames)} input frames; window {FIRST}..{LAST}")

    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        time.sleep(2)

    log = (OUT / "runner.stderr.log").open("wb")
    proc = subprocess.Popen([str(EXE)], cwd=str(EXE.parent),
                            stdout=subprocess.DEVNULL, stderr=log)
    print(f"[replay] exe pid={proc.pid}")
    try:
        client = wait_client(60)
        print("[replay] connected")
        client.frame()

        shots = set(range(FIRST, LAST + 1, SHOT_STEP))
        vrams = set(range(FIRST, LAST + 1, VRAM_STEP))
        ppu_count = 0
        t0 = time.monotonic()
        idx = 0
        while idx < len(frames):
            cur = client.frame()
            idx = cur + 1  # mask for the frame the server is about to run
            if idx >= len(frames):
                break
            client.controller(frames[idx] if idx < len(frames) else 0)
            if FIRST <= cur <= LAST:
                ppu = client.ppu()
                ppu_count += 1
                if cur in vrams or cur in shots:
                    ppu_file = OUT / f"f{cur:05d}_ppu.json"
                    ppu_file.write_text(json.dumps(ppu, indent=2), encoding="utf-8")
                if cur in vrams:
                    (OUT / f"f{cur:05d}_vram.bin").write_bytes(client.vram())
                if cur in shots:
                    bmp = OUT / f"f{cur:05d}.bmp"
                    ok = client.screenshot(bmp)
                    print(f"  [{cur}] shot={ok} bgXsc={ppu.get('bgXsc')} "
                          f"tm={ppu.get('screenEnabled')} mode={ppu.get('bgmode')} "
                          f"inidisp={ppu.get('inidisp')} cgadsub={ppu.get('cgadsub')}")
            if idx % 2000 == 0:
                el = time.monotonic() - t0
                print(f"  [{el:6.1f}s] frame={cur} ({cur / max(el, .001):.0f} fps)")
        el = time.monotonic() - t0
        print(f"[replay] done in {el:.1f}s, ppu states saved: {ppu_count}")
    finally:
        log.close()
        try:
            client.close()
        except Exception:
            pass
        kill_process(proc)


if __name__ == "__main__":
    main()
