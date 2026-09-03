#!/usr/bin/env python3
"""Replay to the bad bridge (f=3187), dump CGRAM + TM/registers, and check
whether the palette actually reached CGRAM."""
import os, sys, subprocess, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import DebugClient, wait_client

EXE = os.path.join(ROOT, "build", "Release", "StarOcean.exe")
INPUTS = os.path.join(ROOT, "build-cosim", "grabacion_inputs.txt")
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 3187


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
    try:
        c = wait_client(90)
        time.sleep(0.5)
        cur = 0
        while True:
            cur = c.frame()
            idx = cur + 1
            if idx <= last:
                c.controller(frame_masks[idx])
            if cur >= TARGET:
                break
            if cur >= last + 1000:
                break
        time.sleep(0.3)
        state = c.ppu()
        print(f"=== PPU state @ frame {cur} ===")
        for k in ("tm", "tmw", "sc0", "sc1", "bgon", "mode", "bgmode",
                  "cgwsel", "cgadsub", "mainWindowEnable", "subWindowEnable",
                  "window1Left", "window1Right", "window2Left", "window2Right"):
            if k in state:
                print(f"  {k} = {state[k]}")
        cg = c.cgram()
        nonblack = sum(1 for i in range(0, 256) if
                       cg[2*i] != 0 or cg[2*i+1] != 0)
        print(f"  cgram non-black colors: {nonblack}/256")
        # BG1 palette = entries 0..127; count non-black
        bg1 = sum(1 for i in range(0, 128) if cg[2*i] != 0 or cg[2*i+1] != 0)
        print(f"  cgram BG1 (0-127) non-black: {bg1}/128")
        # dump BG1 first 16 colors
        print("  BG1 colors 0-15:")
        for i in range(0, 16):
            lo = cg[2*i]; hi = cg[2*i+1]
            print(f"    {i:2d}: 0x{hi:02x}{lo:02x}")
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


if __name__ == "__main__":
    main()
