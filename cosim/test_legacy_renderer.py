#!/usr/bin/env python3
"""Test legacy renderer on ship scene."""
import json, os, socket, struct, subprocess, sys, time

EXE = os.path.join(os.path.dirname(__file__), '..', 'build', 'Release', 'StarOcean.exe')
BSV = os.path.join(os.path.dirname(__file__), '..', 'Star Ocean (Japan) [Traducida Castellano]-20260825-101648.bsv')
PORT = 13308
OUT = os.path.join(os.path.dirname(__file__), "..", "build-cosim", "new_test")
os.makedirs(OUT, exist_ok=True)

def kill_game():
    subprocess.run(['powershell', '-NoProfile', '-Command',
        'Get-Process -Name StarOcean -ErrorAction SilentlyContinue | Stop-Process -Force'],
        capture_output=True)

def parse_bsv(path):
    data = open(path, 'rb').read()
    sz = struct.unpack_from('<III', data, 4)[2]
    stream = data[16+sz:]
    frames = len(stream) // 64
    def mask(f):
        base = f * 64
        m = 0
        for k in range(12):
            if struct.unpack_from('<H', stream, base + 2*k*2)[0]:
                m |= (1 << k)
        return m
    return frames, mask

def tcp_cmd(s, cmd_str):
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

def main():
    kill_game()
    time.sleep(1)
    
    frames_total, get_mask = parse_bsv(BSV)
    print(f'BSV: {frames_total} frames')
    
    # Launch
    print('Launching exe with NewRenderer=0...')
    proc = subprocess.Popen([os.path.abspath(EXE)],
        cwd=os.path.dirname(os.path.abspath(EXE)),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(4)
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(('127.0.0.1', PORT))
        s.settimeout(2)
        try: s.recv(4096)
        except: pass
        print('Connected to debug server')
        
        # Pre-inject all controller inputs
        print('Injecting controller inputs...')
        injected = 0
        for f in range(min(16000, frames_total)):
            mask = get_mask(f)
            if mask:
                s.sendall(f'set_controller 0 {mask}\n'.encode())
                try: s.recv(128)
                except: pass
                injected += 1
        print(f'Injected {injected} input frames')
        
        # Advance to target frame using run_to_frame
        targets = [15050, 15100, 15150, 15200]
        for target in targets:
            print(f'Running to frame {target}...')
            tcp_cmd(s, f'run_to_frame {target}')
            # Wait for frame to be reached
            t0 = time.time()
            while time.time() - t0 < 60:
                resp = tcp_cmd(s, 'get_frame')
                try:
                    cur = int(resp)
                except:
                    try:
                        cur = json.loads(resp).get('frame', 0)
                    except:
                        cur = 0
                if cur >= target:
                    break
                time.sleep(0.5)
            
            # Capture
            bmp = os.path.join(OUT, f'legacy_f{target}.bmp')
            tcp_cmd(s, f'screenshot {bmp}')
            ppu_resp = tcp_cmd(s, 'get_ppu_state')
            try:
                p = json.loads(ppu_resp)
                print(f'  Frame {target}: TM=0x{p["screenEnabled"][0]} mode={p["bgmode"]}')
            except:
                print(f'  Frame {target}: screenshot captured')
        
        # Final: advance a bit more and capture
        tcp_cmd(s, 'run_to_frame 15300')
        time.sleep(3)
        bmp = os.path.join(OUT, 'legacy_f15300.bmp')
        tcp_cmd(s, f'screenshot {bmp}')
        
        tcp_cmd(s, 'continue')
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
        kill_game()

if __name__ == '__main__':
    main()
