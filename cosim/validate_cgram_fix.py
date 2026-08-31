#!/usr/bin/env python3
"""Validate the CGRAM byte-address fix: replay the recorded inputs and count
non-black BG1 palette colors at the bad-bridge transition (2650), settled bad
bridge (3187) and good bridge (5108). Regression check vs. the pre-fix
numbers (bad: 73->28, good: 115).

Usage: python cosim/validate_cgram_fix.py [max_frame]
"""
import os, sys, subprocess, time, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import DebugClient, wait_client

EXE = os.path.join(ROOT, "build", "Release", "StarOcean.exe")
INPUTS = os.path.join(ROOT, "build-cosim", "grabacion_inputs.txt")
OUT = os.path.join(ROOT, "build-cosim", "validate-cgram")
TARGETS = [2650, 3187, 5108]
MAX_FRAME = int(sys.argv[1]) if len(sys.argv) > 1 else max(TARGETS) + 400


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


def count_palette(cgram: bytes, lo: int, hi: int) -> tuple:
    """cgram is 512 bytes (256 colors x2). Count non-black colors in [lo,hi)."""
    n = 0
    first_nonzero = None
    for i in range(lo, hi):
        w = cgram[2 * i] | (cgram[2 * i + 1] << 8)
        if w & 0x7FFF:
            n += 1
            if first_nonzero is None:
                first_nonzero = i
    return n, first_nonzero


def main():
    os.makedirs(OUT, exist_ok=True)
    subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    time.sleep(2)
    frames = events_to_frames(parse_events(INPUTS))
    print(f"[fix] replaying to frame {MAX_FRAME} (recording: {len(frames)} frames)", flush=True)
    proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    results = {}
    try:
        c = wait_client(90)
        print("[fix] connected", flush=True)
        time.sleep(0.5)
        start = time.monotonic()
        last_done = -1
        while True:
            cur = c.frame()
            idx = cur + 1
            if idx < len(frames):
                c.controller(frames[idx])
            for t in TARGETS:
                if t > last_done and cur >= t:
                    last_done = t
                    cg = c.cgram()
                    bg1, first = count_palette(cg, 0, 128)
                    sprites, _ = count_palette(cg, 128, 256)
                    ppu = c.ppu()
                    results[t] = {
                        "frame": cur,
                        "bg1_nonblack": bg1,
                        "sprite_nonblack": sprites,
                        "first_bg1_color": first,
                        "tm": ppu.get("tm"),
                        "bgmode": ppu.get("bgmode"),
                        "cgramPointer": ppu.get("cgramPointer"),
                    }
                    print(f"[fix] frame {cur}: BG1={bg1} sprites={sprites} "
                          f"tm={results[t]['tm']} mode={results[t]['bgmode']} "
                          f"ptr={results[t]['cgramPointer']}", flush=True)
                    shot = os.path.join(OUT, f"frame_{t}.bmp")
                    try:
                        c.screenshot(shot)
                    except Exception as e:
                        print(f"[fix] screenshot {t}: {e}", flush=True)
            if cur >= MAX_FRAME:
                print(f"[fix] reached frame {cur}", flush=True)
                break
            if cur >= len(frames) + 1000:
                print(f"[fix] end of recording at frame {cur}", flush=True)
                break
            if time.monotonic() - start > 400:
                print(f"[fix] TIMEOUT at frame {cur}", flush=True)
                break
        json.dump(results, open(os.path.join(OUT, "results.json"), "w"), indent=1)
        print("[fix] RESULTS:", json.dumps(results, indent=1), flush=True)
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    print("[fix] done - game closed", flush=True)


if __name__ == "__main__":
    main()
