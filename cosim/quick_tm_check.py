#!/usr/bin/env python3
"""Quick check: take screenshot at ship scene and verify TM from debug output."""
import sys, os, subprocess, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import DebugClient, wait_client

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(ROOT)
EXE = os.path.join(PROJECT, 'build', 'Release', 'StarOcean.exe')
EVENTS = os.path.join(ROOT, 'intro_101648_inputs.txt')
OUT = os.path.join(PROJECT, 'build-cosim', 'tm-check')

def parse_events(path):
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

os.makedirs(OUT, exist_ok=True)
os.system('taskkill /F /IM StarOcean.exe 2>nul')
time.sleep(1)

log_path = os.path.join(OUT, 'exe_stderr.log')
log = open(log_path, 'w')
proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE),
                        stdout=subprocess.DEVNULL, stderr=log)
print(f"[tm] exe pid={proc.pid}")

try:
    client = wait_client(60)
    print("[tm] connected")
    
    frames = events_to_frames(parse_events(EVENTS))
    print(f"[tm] {len(frames)} input frames")
    
    client.frame()
    
    # Advance to ship scene
    TARGET = 15100
    idx = 1
    while idx < len(frames):
        cur = client.frame()
        if cur >= TARGET:
            break
        idx = cur + 1
        if idx < len(frames):
            client.controller(frames[idx])
        if cur % 2000 == 0:
            print(f"  frame={cur}")
    
    print(f"[tm] Reached frame {cur}")
    
    # Take screenshots at several consecutive frames and check TM
    for i in range(10):
        cur = client.frame()
        idx = cur + 1
        if idx < len(frames):
            client.controller(frames[idx])
        
        ppu = client.ppu()
        tm = int(ppu['screenEnabled'][0], 16)
        inidisp = int(ppu['inidisp'], 16)
        forced = bool(inidisp & 0x80)
        
        bmp = os.path.join(OUT, f'shot_f{cur}.bmp')
        ok = client.screenshot(bmp)
        
        from PIL import Image
        img = Image.open(bmp)
        pixels = list(img.getdata())
        non_black = sum(1 for p in pixels if any(c > 5 for c in p))
        
        print(f"  frame {cur}: TM=0x{tm:02X} forced={forced} "
              f"non-black={non_black} ({100*non_black/57344:.1f}%) screenshot={ok}")

finally:
    log.flush()
    # Check SCREENSHOT debug lines
    with open(log_path) as f:
        for line in f:
            if 'SCREENSHOT' in line:
                print(f"  DEBUG: {line.strip()}")
    
    try: client.close()
    except: pass
    proc.kill()
    log.close()
    print("[tm] Done.")
