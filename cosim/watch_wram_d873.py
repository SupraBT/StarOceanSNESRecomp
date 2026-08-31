#!/usr/bin/env python3
"""Trace every write to the palette staging buffer $7E:D873-D8B2 (+$D913)
during the bridge transition (frames 2350-2620) to identify the mechanism
that fills it (DMA burst vs CPU routine) and whether it produces real data.

Usage: python cosim/watch_wram_d873.py
"""
import os, sys, subprocess, time, json, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import DebugClient, wait_client

EXE = os.path.join(ROOT, "build", "Release", "StarOcean.exe")
INPUTS = os.path.join(ROOT, "build-cosim", "grabacion_inputs.txt")
TO_FRAME = 2620
FROM_FRAME = 2350
OUT = os.path.join(ROOT, "build-cosim", "watch-d873.json")


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


def events_to_frames(ev):
    last = max(ev)
    frames = [0] * (last + 1)
    for fr, mask in ev.items():
        frames[fr] = mask
    return frames


def main():
    subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    time.sleep(2)
    frames = events_to_frames(parse_events(INPUTS))
    print(f"[watch] replaying to frame {TO_FRAME}", flush=True)
    proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        c = wait_client(90)
        print("[watch] connected", flush=True)
        # Arm watches: every byte of $7E:D873..D8B2 plus $D913..D92F
        armed = 0
        for a in range(0xD873, 0xD8B3):
            c.cmd("set_wram_watch 7E %04x 1" % a, timeout=8)
            armed += 1
        for a in range(0xD913, 0xD930):
            c.cmd("set_wram_watch 7E %04x 1" % a, timeout=8)
            armed += 1
        print(f"[watch] armed {armed} watches", flush=True)
        time.sleep(0.3)
        start = time.monotonic()
        while True:
            cur = c.frame()
            idx = cur + 1
            if idx < len(frames):
                c.controller(frames[idx])
            if cur >= TO_FRAME:
                print(f"[watch] reached frame {cur}", flush=True)
                break
            if cur >= len(frames) + 1000:
                print(f"[watch] end of recording at frame {cur}", flush=True)
                break
            if time.monotonic() - start > 400:
                print(f"[watch] TIMEOUT at frame {cur}", flush=True)
                break
        time.sleep(0.3)
        resp = c.cmd("wram_watch_log_get all %d %d 4000" % (FROM_FRAME, TO_FRAME), timeout=60)
        events = []
        m = re.search(r"\"events\":\[(.*)\],\"returned\"", resp, re.S)
        if m:
            chunk = m.group(1)
            if chunk.strip():
                events = json.loads("[" + chunk + "]")
        json.dump({"events": events, "matched": len(events)},
                  open(OUT, "w"), indent=1)
        # Summary: group by frame
        by_frame = {}
        for e in events:
            f = e["frame"]
            by_frame.setdefault(f, []).append(e)
        print(f"[watch] {len(events)} events in frames {FROM_FRAME}-{TO_FRAME}", flush=True)
        for f in sorted(by_frame):
            evs = by_frame[f]
            nz = sum(1 for e in evs if int(e["byte_new"], 16) != 0)
            addrs = sorted(set(int(e["addr"], 16) for e in evs))
            print(f"  frame {f}: {len(evs)} writes ({nz} nonzero), "
                  f"addrs {hex(addrs[0])}-{hex(addrs[-1])}", flush=True)
        print("[watch] first 12 events:", flush=True)
        for e in events[:12]:
            print("   f=%d pc=%s addr=%s new=%s func=%s A=%s X=%s" % (
                e["frame"], e["pc24"], e["addr"], e["byte_new"],
                e["func_pc"], e["A"], e["X"]), flush=True)
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    print("[watch] done - game closed", flush=True)


if __name__ == "__main__":
    main()
