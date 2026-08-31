#!/usr/bin/env python3
"""Replay the intro recording ONCE and save named savestates at strategic
points so we never have to watch the whole intro again.

Strategic points (from grabacion_inputs.txt + prior analysis):
  f=  50  boot / title screen (pre-input)
  f= 350  after title A-presses, intro scene 1 (palette load window)
  f=1450  intro scene w/ real palette in $7E:D873 (before fade-out wipe)
  f=2700  just before bridge transition (before Up at 2803)
  f=3010  bridge fade-in start (C3:AF9A palette writes begin f=3012)
  f=3187  NORMAL bridge (BAD: black background)  <- diagnostic target
  f=4313  planet explosion scene
  f=5108  ALARM bridge (working background)      <- comparison target

States are saved via the TCP `save_state` command (deferred to the main
loop frame boundary). We advance one extra frame after each save so the
deferred write completes before we continue.

Usage: python cosim/make_key_states.py
"""
import os, sys, subprocess, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import DebugClient, wait_client

EXE = os.path.join(ROOT, "build", "Release", "StarOcean.exe")
INPUTS = os.path.join(ROOT, "build-cosim", "grabacion_inputs.txt")
OUTDIR = os.path.join(ROOT, "build-cosim", "states")
os.makedirs(OUTDIR, exist_ok=True)

# frame -> save filename (names in order of appearance)
POINTS = [
    (50,   "000_boot_title.st"),
    (350,  "100_intro_scene1.st"),
    (1450, "200_palette_loaded.st"),
    (2700, "300_pre_bridge.st"),
    (3010, "400_bridge_fadein.st"),
    (3187, "500_bridge_bad.st"),
    (4313, "600_planet.st"),
    (5108, "700_bridge_alarm.st"),
]


def parse_events(path):
    ev = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.split()
            if len(p) < 2:
                continue
            try:
                fr = int(p[0]); mask = int(p[1], 16)
            except ValueError:
                continue
            ev[fr] = mask
    return ev


def main():
    subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    time.sleep(2)
    frames = parse_events(INPUTS)
    last = max(frames)
    frame_masks = [0] * (last + 1)
    for fr, mask in frames.items():
        frame_masks[fr] = mask

    proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    saved = []
    try:
        c = wait_client(90)
        time.sleep(0.5)
        cur = 0
        target_idx = 0
        while True:
            cur = c.frame()
            idx = cur + 1
            if idx <= last:
                c.controller(frame_masks[idx])
            # Save at each strategic point when we reach it
            while target_idx < len(POINTS) and cur >= POINTS[target_idx][0]:
                fname = POINTS[target_idx][1]
                path = os.path.join(OUTDIR, fname)
                c.j(f"save_state {path.replace(os.sep, '/')}")
                # advance a couple frames so the deferred save runs at frame boundary
                for _ in range(3):
                    c.frame()
                cur = c.frame()
                # wait for the serialization (heavy on first save: ~0.3-1s)
                sz = 0
                for _ in range(20):
                    if os.path.exists(path):
                        sz = os.path.getsize(path)
                        break
                    time.sleep(0.25)
                if sz > 0:
                    print(f"[save] {fname} @ f={POINTS[target_idx][0]} ({sz} bytes)", flush=True)
                    saved.append((fname, sz))
                else:
                    print(f"[save] WARNING {fname} not written yet (deferred)", flush=True)
                target_idx += 1
            if target_idx >= len(POINTS):
                break
            if cur >= last + 1000:
                break
        time.sleep(0.5)
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    print(f"\n=== Saved {len(saved)} states in {OUTDIR} ===")
    for fname, sz in saved:
        print(f"  {fname:32s} {sz:>8} bytes")


if __name__ == "__main__":
    main()
