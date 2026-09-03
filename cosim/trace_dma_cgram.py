#!/usr/bin/env python3
"""Replay recorded inputs to a target frame with SNESRECOMP_DMA_DEBUG=1 and
capture the [DMA_CGRAM] stderr trace to a file for analysis.

Usage: python cosim/trace_dma_cgram.py <target_frame> <out_log> [frame_from]
"""
import os, sys, subprocess, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import DebugClient, wait_client

EXE = os.path.join(ROOT, "build", "Release", "StarOcean.exe")
INPUTS = os.path.join(ROOT, "build-cosim", "grabacion_inputs.txt")
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 3200
LOG = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "build-cosim", "dma-cgram.log")
FRAME_FROM = sys.argv[3] if len(sys.argv) > 3 else None


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
    print(f"[dma] replaying to frame {TARGET}", flush=True)
    env = os.environ.copy()
    env["SNESRECOMP_DMA_DEBUG"] = "1"
    if FRAME_FROM:
        env["SNESRECOMP_DMA_FRAME_FROM"] = FRAME_FROM
    err = open(LOG, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE), env=env,
                            stdout=subprocess.DEVNULL, stderr=err)
    try:
        c = wait_client(90)
        print("[dma] connected", flush=True)
        time.sleep(0.5)
        start = time.monotonic()
        while True:
            cur = c.frame()
            idx = cur + 1
            if idx < len(frames):
                c.controller(frames[idx])
            if cur >= TARGET:
                print(f"[dma] reached frame {cur}", flush=True)
                break
            if cur >= len(frames) + 1000:
                print(f"[dma] end of recording at frame {cur}", flush=True)
                break
            if time.monotonic() - start > 400:
                print(f"[dma] TIMEOUT at frame {cur}", flush=True)
                break
        time.sleep(0.5)
    finally:
        err.close()
        try:
            proc.terminate()
        except Exception:
            pass
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    print(f"[dma] done - log at {LOG}", flush=True)


if __name__ == "__main__":
    main()
