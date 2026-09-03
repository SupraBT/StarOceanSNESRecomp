#!/usr/bin/env python3
"""Diagnose ship-scene black BG: dump VRAM tiles at the tile address the
renderer uses, and manually compute what PpuDrawBackground_4bpp would produce.

Usage: python cosim/diag_ship.py [--exe build/Release/StarOcean.exe]
"""
import sys, os, socket, struct, subprocess, time, json, glob, re

EXE = os.path.join(os.path.dirname(__file__), '..', 'build', 'Release', 'StarOcean.exe')
BSV = os.path.join(os.path.dirname(__file__), '..', 'Star Ocean (Japan) [Traducida Castellano]-20260825-101648.bsv')
PORT = 12345

def tcp_connect(port, retries=60, delay=0.5):
    for attempt in range(retries):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect(('127.0.0.1', port))
            s.settimeout(2.0)
            try: s.recv(4096)
            except: pass
            return s
        except:
            if attempt < retries - 1:
                time.sleep(delay)
    return None

def cmd(s, command, timeout=5.0):
    s.sendall((command + '\n').encode())
    s.settimeout(timeout)
    try:
        data = s.recv(65536)
        return data.decode('utf-8', errors='replace').strip()
    except socket.timeout:
        return ''

def parse_bsv_inputs(path):
    """Parse BSV header and return list of (frame, button_word)."""
    with open(path, 'rb') as f:
        hdr = f.read(16)
        inputs = []
        while True:
            pair = f.read(4)
            if len(pair) < 4:
                break
            lo, hi = struct.unpack('<BB', pair[:2])
            inputs.append((lo, hi))
        return inputs

def main():
    exe = sys.argv[1] if len(sys.argv) > 1 else EXE
    bsv = sys.argv[2] if len(sys.argv) > 2 else BSV
    
    # Kill old
    os.system('taskkill /F /IM StarOcean.exe 2>nul')
    time.sleep(1)
    
    print(f"[DIAG] Launching {exe}...")
    proc = subprocess.Popen(
        [os.path.abspath(exe)],
        cwd=os.path.dirname(os.path.abspath(exe)),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(3)
    
    s = tcp_connect(PORT)
    if not s:
        print("[DIAG] FAIL: cannot connect"); proc.kill(); return
    
    print("[DIAG] Connected. Loading inputs...")
    inputs = parse_bsv_inputs(bsv)
    print(f"[DIAG] {len(inputs)} input frames in BSV")
    
    # Feed inputs to advance to ship scene (~frame 15000)
    TARGET_FRAME = 15100
    SHIP_WINDOW = range(14800, 15400)
    
    ok = cmd(s, 'ok')
    print(f"[DIAG] Server ready: {ok}")
    
    # Advance frame by frame, set controller each frame
    prev_ctrl = None
    for i, (lo, hi) in enumerate(inputs):
        if i >= TARGET_FRAME + 200:
            break
        
        # Build button word: lo is low byte, hi is high byte
        # For set_controller, we send the 16-bit joypad register
        ctrl_val = lo | (hi << 8)
        
        # Only send set_controller if value changed
        if ctrl_val != prev_ctrl:
            cmd(s, f'set_controller {ctrl_val}')
            prev_ctrl = ctrl_val
        
        # Signal next frame
        resp = cmd(s, 'ok', timeout=10)
        
        if i in SHIP_WINDOW and i % 50 == 0:
            # Capture PPU state at key ship-scene frames
            ppu_resp = cmd(s, 'get_ppu_state')
            try:
                ppu = json.loads(ppu_resp)
                print(f"[DIAG] Frame {i}: mode={ppu.get('bgmode')} TM={ppu.get('tm')} "
                      f"BGSC={ppu.get('bgXsc')} NBA={ppu.get('bgTileAdr')} "
                      f"screen={ppu.get('screenEnabled')} scroll={ppu.get('hScroll')[:2]}/{ppu.get('vScroll')[:2]}")
            except:
                print(f"[DIAG] Frame {i}: ppu parse error: {ppu_resp[:100]}")
        
        if i == TARGET_FRAME:
            print(f"\n[DIAG] === REACHED TARGET FRAME {i} ===")
            
            # Dump PPU state
            ppu_resp = cmd(s, 'get_ppu_state')
            ppu = json.loads(ppu_resp)
            print(f"[DIAG] PPU: {json.dumps(ppu, indent=2)}")
            
            # Dump VRAM region for BG1 tiles (based on NBA)
            # BG1 tile base = (bgTileAdr & 0x0F) << 12
            bg_tile_base = int(ppu.get('bgTileAdr', '0x0000'), 16) & 0x0F
            bg1_tile_adr = bg_tile_base << 12
            print(f"[DIAG] BG1 tile base: ${bg1_tile_adr:04X}")
            
            # BG1 map base = (BGSC & 0xFC) << 8
            bgsc = int(ppu.get('bgXsc', ['0x00'])[0], 16)
            bg1_map_adr = (bgsc & 0xFC) << 8
            print(f"[DIAG] BG1 map base: ${bg1_map_adr:04X}")
            
            # Dump first 256 bytes of BG1 tilemap
            vram_resp = cmd(s, f'dump_vram {bg1_map_adr} 256')
            print(f"[DIAG] VRAM dump ({bg1_map_adr:04X}): {vram_resp[:200]}")
            
            # Dump first 128 bytes of BG1 tile data
            vram_tiles = cmd(s, f'dump_vram {bg1_tile_adr} 128')
            print(f"[DIAG] VRAM tiles ({bg1_tile_adr:04X}): {vram_tiles[:200]}")
            
            # Screenshot
            out_dir = os.path.join(os.path.dirname(__file__), '..', 'build-cosim', 'diag-ship')
            os.makedirs(out_dir, exist_ok=True)
            ss_path = os.path.join(out_dir, f'ship_frame_{i}.bmp').replace('\\', '/')
            # Convert to forward slashes for the exe
            ss_path_fwd = ss_path.replace('\\', '/')
            cmd(s, f'screenshot {ss_path_fwd}')
            print(f"[DIAG] Screenshot saved to {ss_path}")
            
            # Now let's try dump_vram of a larger region to analyze tiles
            # Dump 2048 bytes starting at BG1 tile base
            vram_region = cmd(s, f'dump_vram {bg1_tile_adr} 2048')
            print(f"[DIAG] Tile data (first 200 chars): {vram_region[:200]}")
            
            # Now analyze: which map entries reference which tiles
            # Dump 512 bytes of the map
            vram_map = cmd(s, f'dump_vram {bg1_map_adr} 512')
            print(f"[DIAG] Map data (first 200 chars): {vram_map[:200]}")
            
            break
    
    # Cleanup
    cmd(s, 'shutdown')
    time.sleep(1)
    proc.kill()
    time.sleep(1)
    os.system('taskkill /F /IM StarOcean.exe 2>nul')
    print("[DIAG] Done.")

if __name__ == '__main__':
    main()
