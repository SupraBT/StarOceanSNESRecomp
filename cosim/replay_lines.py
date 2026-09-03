#!/usr/bin/env python3
"""Focused ship-scene capture: per-scanline renderer state (ppu_lines),
window spans (ppu_window) + screenshots, paced off the server frame counter."""
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
OUT = ROOT / "build-cosim" / "ship-lines"
FIRST = int(sys.argv[1]) if len(sys.argv) > 1 else 14940
LAST = int(sys.argv[2]) if len(sys.argv) > 2 else 15220
LINE_STEP = int(sys.argv[3]) if len(sys.argv) > 3 else 2
SHOT_STEP = 10


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
    print(f"[lines] window {FIRST}..{LAST} step {LINE_STEP}")

    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        time.sleep(2)

    log = (OUT / "runner.stderr.log").open("wb")
    proc = subprocess.Popen([str(EXE)], cwd=str(EXE.parent),
                            stdout=subprocess.DEVNULL, stderr=log)
    try:
        client = wait_client(60)
        client.frame()
        lines_targets = set(range(FIRST, LAST + 1, LINE_STEP))
        shots = set(range(FIRST, LAST + 1, SHOT_STEP))
        idx = 0
        while idx < len(frames):
            cur = client.frame()
            idx = cur + 1
            if idx >= len(frames):
                break
            client.controller(frames[idx] if idx < len(frames) else 0)
            if cur in shots:
                (OUT / f"f{cur:05d}.bmp")
                client.screenshot(OUT / f"f{cur:05d}.bmp")
            if cur in lines_targets:
                pl = client.cmd("ppu_lines 0 224", timeout=15)
                (OUT / f"f{cur:05d}_lines.json").write_text(pl, encoding="utf-8")
                pw = client.cmd("ppu_window 120 0", timeout=5)
                (OUT / f"f{cur:05d}_win120.json").write_text(pw, encoding="utf-8")
                ppu = client.ppu()
                (OUT / f"f{cur:05d}_ppu.json").write_text(
                    json.dumps(ppu, indent=2), encoding="utf-8")
                print(f"  [{cur}] lines+win saved")
            if idx % 2000 == 0:
                print(f"  frame={cur}")
        print("[lines] done")
    finally:
        log.close()
        try:
            client.close()
        except Exception:
            pass
        kill_process(proc)


if __name__ == "__main__":
    main()
