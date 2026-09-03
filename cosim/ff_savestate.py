#!/usr/bin/env python3
"""Fast-forward the .bsv replay to a target frame and save a savestate.

Uses fire-and-forget controller sends (like bsv_profiler) so the emulation
runs at full speed, then dumps a savestate at the target frame for fast
iteration on the ship-scene render bug."""
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
EVENTS = ROOT / "cosim" / "bsv_all_inputs.txt"
EXE = ROOT / "build" / "Release" / "StarOcean.exe"
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 14900
STATE = str((ROOT / "build-cosim" / "ship-lines" / f"ship{TARGET}.state").resolve())


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


def send(sock, cmd):
    try:
        sock.sendall((cmd + "\n").encode())
    except OSError:
        pass


def drain(sock):
    try:
        sock.settimeout(0.05)
        while True:
            if not sock.recv(1 << 20):
                break
    except Exception:
        pass
    sock.settimeout(0.5)


def main():
    frames = events_to_frames(parse_events(EVENTS))
    print(f"[ff] target frame {TARGET}")

    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        time.sleep(2)

    log = open(ROOT / "build-cosim" / "ship-lines" / "ff.stderr.log", "wb")
    proc = subprocess.Popen([str(EXE)], cwd=str(EXE.parent),
                            stdout=subprocess.DEVNULL, stderr=log)
    try:
        client = wait_client(60)
        print("[ff] connected")
        t0 = time.monotonic()
        # Frame-synchronous pacing: set the controller mask for the frame the
        # server is about to run, keeping Python exactly one frame ahead.
        cur = -1
        while True:
            cur = client.frame()
            idx = cur + 1
            if idx >= len(frames):
                break
            if idx >= TARGET + 3:
                break
            client.controller(frames[idx])
            if idx % 500 == 0:
                print(f"  frame={idx} ({idx / max(time.monotonic()-t0, .001):.0f} fps)")
        el = time.monotonic() - t0
        print(f"[ff] frame {cur} in {el:.1f}s")
        sock = client.sock
        drain(sock)
        # settle a few frames so the state is mid-scene, not mid-transition
        time.sleep(0.5)
        send(sock, f"save_state {STATE}")
        time.sleep(1.0)
        drain(sock)
        print(f"[ff] state saved: {STATE}")
        sock.close()
    finally:
        log.close()
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


if __name__ == "__main__":
    main()
