#!/usr/bin/env python3
"""Replay to ship scene, dump CGRAM, screenshot, and check BG1 palette entries."""
import sys, os, subprocess, time, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import DebugClient, kill_process, wait_client

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(ROOT)
EXE = os.path.join(PROJECT, 'build', 'Release', 'StarOcean.exe')
EVENTS = os.path.join(ROOT, 'intro_101648_inputs.txt')
OUT = os.path.join(PROJECT, 'build-cosim', 'diag-cgram')

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
print(f"[cgram] exe pid={proc.pid}")

try:
    client = wait_client(60)
    print("[cgram] connected")
    
    frames = events_to_frames(parse_events(EVENTS))
    print(f"[cgram] {len(frames)} input frames")
    
    client.frame()
    
    TARGET = 15100
    t0 = time.monotonic()
    
    idx = 1
    while idx < len(frames):
        cur = client.frame()
        if cur >= TARGET:
            break
        idx = cur + 1
        if idx < len(frames):
            client.controller(frames[idx])
        if cur % 1000 == 0:
            el = time.monotonic() - t0
            print(f"  [{el:6.1f}s] frame={cur} ({cur/max(el,.001):.0f} fps)")
    
    el = time.monotonic() - t0
    print(f"[cgram] Reached frame {cur} in {el:.1f}s")
    
    # Capture PPU state and CGRAM at the target frame
    ppu = client.ppu()
    ppu_file = os.path.join(OUT, 'ppu_state.json')
    with open(ppu_file, 'w') as f:
        json.dump(ppu, f, indent=2)
    print(f"[cgram] PPU state saved")
    
    # Dump CGRAM (full 512 bytes = 256 uint16 LE colors)
    cgram_bytes = client.cgram()
    if cgram_bytes:
        cgram = struct.unpack_from(f'<{len(cgram_bytes)//2}H', cgram_bytes)
        
        cgram_file = os.path.join(OUT, 'cgram.bin')
        with open(cgram_file, 'wb') as f:
            f.write(cgram_bytes)
        
        # Check BG1 palette entries (palette 6: indices 0xC0-0xFF)
        print(f"\n[CGRAM] BG1 palette 6 entries (0xC0-0xFF):")
        for i in range(0xC0, 0x100):
            color = cgram[i]
            if color != 0:
                r5 = color & 0x1F
                g5 = (color >> 5) & 0x1F
                b5 = (color >> 10) & 0x1F
                print(f"  cgram[0x{i:02X}] = 0x{color:04X} R={r5} G={g5} B={b5}")
        
        # Check backdrop (index 0)
        print(f"\n[CGRAM] Backdrop: cgram[0] = 0x{cgram[0]:04X}")
        
        # Summary: how many CGRAM entries are non-zero?
        nonzero = sum(1 for c in cgram if c != 0)
        print(f"[CGRAM] Non-zero entries: {nonzero}/256")
    else:
        print("[cgram] Failed to get CGRAM data")
    
    # Screenshot
    bmp = os.path.join(OUT, 'ship_frame.bmp')
    ok = client.screenshot(bmp)
    print(f"[cgram] Screenshot: {ok}")
    
    # Check BMP pixels
    from PIL import Image
    img = Image.open(bmp)
    pixels = list(img.getdata())
    non_black = sum(1 for p in pixels if any(c > 5 for c in p))
    print(f"[cgram] BMP non-black: {non_black}/57344 ({100*non_black/57344:.1f}%)")
    
finally:
    try:
        client.close()
    except Exception:
        pass
    proc.kill()
    log.close()
    print("[cgram] Done.")
