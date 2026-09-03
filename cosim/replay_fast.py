#!/usr/bin/env python3
"""Fast replay: uses the TRACE=OFF exe (which still has the debug server compiled
via a separate check) to drive to the ship scene."""
import sys, os, subprocess, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import DebugClient, kill_process, wait_client

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(ROOT)
EXE = os.path.join(PROJECT, 'build', 'Release', 'StarOcean.exe')
EVENTS = os.path.join(ROOT, 'intro_101648_inputs.txt')
OUT = os.path.join(PROJECT, 'build-cosim', 'diag-run')

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
print(f"[fast] exe pid={proc.pid}")

try:
    client = wait_client(60)
    print("[fast] connected")
    
    frames = events_to_frames(parse_events(EVENTS))
    print(f"[fast] {len(frames)} input frames")
    
    client.frame()
    
    TARGET = 15100
    t0 = time.monotonic()
    
    for idx in range(1, min(TARGET + 100, len(frames))):
        cur = client.frame()
        client.controller(frames[idx] if idx < len(frames) else 0)
        
        if idx % 3000 == 0:
            el = time.monotonic() - t0
            print(f"  [{el:6.1f}s] frame={cur} ({cur/max(el,.001):.0f} fps)")
    
    el = time.monotonic() - t0
    print(f"[fast] Reached frame ~{TARGET} in {el:.1f}s")
    
    # Run 50 more frames to ensure debug dump fires
    for i in range(50):
        cur = client.frame()
        idx = cur + 1
        client.controller(frames[idx] if idx < len(frames) else 0)
    
    el = time.monotonic() - t0
    print(f"[fast] Done in {el:.1f}s")
    
    log.flush()
    with open(log_path) as f:
        content = f.read()
    
    if '[BG1_DBG]' in content:
        print("\n=== BG1 DEBUG OUTPUT ===")
        for line in content.split('\n'):
            if '[BG1_DBG]' in line:
                print(line)
    else:
        print("[fast] No BG1_DBG found. Last 10 lines:")
        lines = content.strip().split('\n')
        for line in lines[-10:]:
            print(line)

finally:
    try:
        client.close()
    except Exception:
        pass
    proc.kill()
    log.close()
    print("[fast] Cleaned up.")
