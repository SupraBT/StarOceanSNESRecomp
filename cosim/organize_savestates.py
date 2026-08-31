#!/usr/bin/env python3
"""Organize savestates at the player's Up-press markers.

Replays build-cosim/grabacion_inputs.txt (the player's real presses: Up at
2803/3187/4313/5108 = subtitle-346, bad bridge, meteor, good bridge) and, for
each Up-press frame, saves a savestate with a descriptive name so the player
can jump straight to each scene.

Savestates use the L3SN format (debug_server save_state -> state_file.c),
compatible with the player's build/Release/StarOcean.exe F9/F10 savestates,
as long as both are built from the same code base.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from semantic_cosim import DebugClient, wait_client  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "build-cosim" / "grabacion_inputs.txt"      # player's real presses
# Build with the TCP debug server compiled in + savestate hotkeys (state_file.c).
# This is the base-good build + debug server, in the StarOceanTest2-ccc worktree.
EXE = Path(r"E:/Recompilador Super Nintendo/StarOceanTest2-ccc/build-ccc-dbg/Release/StarOcean.exe")
OUTDIR = ROOT / "build-cosim" / "organized-savestates"

# (label, frame) for each Up-press marker. Frame = the frame eb the recording
# first holds Up. The savestate is taken ~60 frames after so the scene has
# settled (mid-scene, not mid-transition).
MARKERS = [
    ("subtitle-346", 2803 + 60),
    ("bad-bridge",   3187 + 60),
    ("meteor",       4313 + 60),
    ("good-bridge",  5108 + 60),
]


def parse_events(path: Path):
    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                fr = int(parts[0])
                mask = int(parts[1], 16)
            except ValueError:
                continue
            events.append((fr, mask))
    return events


def events_to_frames(events):
    if not events:
        return []
    last = max(e[0] for e in events) + 1
    frames = [0] * last
    for fr, mask in events:
        frames[fr] = mask
    return frames


def connect(port=13308, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=2)
            s.settimeout(0.5)
            try:
                s.recv(65536)
            except Exception:
                pass
            return s
        except OSError:
            time.sleep(0.3)
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    frames = events_to_frames(parse_events(EVENTS))
    # sort targets ascending
    targets = sorted((f, label) for label, f in MARKERS)
    print(f"[org] markers: {sorted((l, f) for l, f in MARKERS)}")

    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        time.sleep(2)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    log = open(ROOT / "build-cosim" / "organized-savestates" / "run.stderr.log", "wb")
    proc = subprocess.Popen([str(EXE)], cwd=str(EXE.parent),
                            stdout=subprocess.DEVNULL, stderr=log)
    try:
        client = wait_client(60)
        print("[org] connected")
        t0 = time.monotonic()
        cur = -1
        done = set()
        # Frame-synchronous replay: set controller mask one frame ahead.
        while True:
            cur = client.frame()
            idx = cur + 1
            if idx >= len(frames):
                print(f"[org] end of recording reached at frame {cur}")
                break
            client.controller(frames[idx])

            # At each target frame (once), save the state with a label.
            for target, label in targets:
                key = label
                if key not in done and idx > target and cur >= target:
                    done.add(key)
                    outdir = OUTDIR / label
                    outdir.mkdir(parents=True, exist_ok=True)
                    state = str(outdir / "state.st")
                    # pause-free save at frame boundary via debug server
                    client.cmd(f"save_state {state}", timeout=8)
                    print(f"[org] saved {label} at frame {cur} -> {state}", flush=True)

            if len(done) >= len(targets):
                print("[org] all markers saved", flush=True)
                break
            if time.monotonic() - t0 > 600:
                print("[org] TIMEOUT", flush=True)
                break
        print("[org] done.", flush=True)
    finally:
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


if __name__ == "__main__":
    main()