#!/usr/bin/env python3
"""Frame-synchronized BSV replay. Injects inputs matching each frame."""
import json, os, socket, struct, subprocess, sys, time

EXE = os.path.join(os.path.dirname(__file__), '..', 'build', 'Release', 'StarOcean.exe')
BSV = os.path.join(os.path.dirname(__file__), '..', 'Star Ocean (Japan) [Traducida Castellano]-20260825-101648.bsv')
PORT = 13308
OUT = os.path.join(os.path.dirname(__file__), '..', 'build-cosim', 'replay_sync')
os.makedirs(OUT, exist_ok=True)

def kill():
    subprocess.run(['powershell', '-NoProfile', '-Command',
        'Get-Process -Name StarOcean -ErrorAction SilentlyContinue | Stop-Process -Force'],
        capture_output=True)

def parse_bsv(path):
    data = open(path, 'rb').read()
    sz = struct.unpack_from('<III', data, 4)[2]
    stream = data[16+sz:]
    frames = len(stream) // 64
    def get_mask(f):
        base = f * 64
        m = 0
        for k in range(12):
            if struct.unpack_from('<H', stream, base + 2*k*2)[0]:
                m |= (1 << k)
        return m
    return frames, get_mask

def tcp(s, cmd_str):
    s.sendall((cmd_str + '\n').encode())
    buf = b''
    while True:
        try:
            chunk = s.recv(4096)
            buf += chunk
        except socket.timeout:
            break
        if b'\n' in buf:
            break
    return buf.decode().strip()

def get_frame(s):
    resp = tcp(s, 'frame')
    try:
        return json.loads(resp).get('frame', 0)
    except:
        return 0

def main():
    kill()
    time.sleep(1)
    
    total_frames, get_mask = parse_bsv(BSV)
    print(f'BSV: {total_frames} frames')
    
    # Launch
    print('Launching exe...')
    proc = subprocess.Popen([os.path.abspath(EXE)],
        cwd=os.path.dirname(os.path.abspath(EXE)),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(('127.0.0.1', PORT))
        s.settimeout(2)
        try: s.recv(4096)
        except: pass
        
        # Wait for emulator to start
        cur = get_frame(s)
        print(f'Initial frame: {cur}')
        
        # Replay: for each frame, set the correct input
        prev_mask = 0
        target = min(total_frames, 16000)
        frames_since_print = 0
        
        for f in range(target):
            mask = get_mask(f)
            
            # Only send set_controller if mask changed
            if mask != prev_mask:
                if mask:
                    tcp(s, f'set_controller 0 {mask}')
                else:
                    tcp(s, 'clear_controller 0')
                prev_mask = mask
            
            # Wait for emulator to reach this frame
            t0 = time.time()
            while time.time() - t0 < 5:
                cur = get_frame(s)
                if cur >= f:
                    break
                time.sleep(0.001)
            
            frames_since_print += 1
            if frames_since_print >= 1000:
                print(f'  Frame {f}/{target} (emulator at {cur})')
                frames_since_print = 0
            
            # Capture at key frames
            if f in [500, 2000, 5000, 10000, 14000, 15000, 15200]:
                bmp = os.path.join(OUT, f'f{f}.bmp')
                tcp(s, f'screenshot {bmp}')
                ppu = tcp(s, 'get_ppu_state')
                try:
                    p = json.loads(ppu)
                    print(f'  *** Frame {f}: TM=0x{p["screenEnabled"][0]} mode={p["bgmode"]} SC0=0x{p["bgXsc"][0]}')
                except:
                    print(f'  *** Frame {f}: screenshot captured')
        
        tcp(s, 'continue')
        s.close()
        
        # Analyze BMPs
        print('\n--- BMP Analysis ---')
        from PIL import Image
        for f in sorted(os.listdir(OUT)):
            if f.endswith('.bmp'):
                img = Image.open(os.path.join(OUT, f))
                pixels = list(img.getdata())
                nonblack = sum(1 for p in pixels if p != (0,0,0))
                pct = nonblack * 100 / len(pixels)
                print(f'{f}: {pct:.1f}% non-black')
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        kill()

if __name__ == '__main__':
    main()
