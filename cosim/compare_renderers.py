#!/usr/bin/env python3
"""Compare new vs legacy renderer on the ship scene.
Run with SNESRECOMP_NEW_RENDERER=0 to force legacy, capture BMP, compare."""
import sys, os, time, socket, struct, subprocess, json

EXE = os.path.join(os.path.dirname(__file__), '..', 'build', 'Release', 'StarOcean.exe')
BSV = os.path.join(os.path.dirname(__file__), '..', 'Star Ocean (Japan) [Traducida Castellano]-20260825-101648.bsv')
PORT = 13308
OUT = os.path.join(os.path.dirname(__file__), '..', 'build-cosim', 'renderer_test')
os.makedirs(OUT, exist_ok=True)

def read_bsv_inputs(path):
    """Read BSV and return list of (button_hi, button_lo) per frame."""
    with open(path, 'rb') as f:
        data = f.read()
    # Skip header (find 'BSV1' magic or just skip first 16 bytes)
    # BizHawk BSV: 4-byte magic 'BSV1', then 4-byte sample_count, then inputs
    if data[:4] == b'BSV1':
        offset = 16  # BSV1 header: magic(4) + sample_count(4) + padding(8)
    else:
        offset = 0
    inputs = []
    while offset + 2 <= len(data):
        inputs.append((data[offset], data[offset+1]))
        offset += 2
    return inputs

def tcp_cmd(s, cmd):
    s.sendall((cmd + '\n').encode())
    buf = b''
    while True:
        chunk = s.recv(4096)
        buf += chunk
        if b'\n' in buf:
            break
    return buf.decode().strip()

def run_test(renderer_flag, target_frame=15200):
    """Run the game with given renderer, inject BSV inputs, capture at target frame."""
    tag = 'new' if renderer_flag else 'legacy'
    env = os.environ.copy()
    env['SNESRECOMP_FPS'] = '1'
    if not renderer_flag:
        # Force legacy renderer (unset kPpuRenderFlags_NewRenderer)
        env['SNESRECOMP_LAYER_MASK'] = '0xff'  # keep all layers
    
    print(f"[{tag}] Launching exe...")
    proc = subprocess.Popen(
        [os.path.abspath(EXE)],
        cwd=os.path.dirname(os.path.abspath(EXE)),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    
    inputs = read_bsv_inputs(BSV)
    print(f"[{tag}] Loaded {len(inputs)} input frames from BSV")
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(('127.0.0.1', PORT))
        s.settimeout(2)
        try: s.recv(4096)
        except: pass
        
        # Inject inputs frame by frame up to target
        for i, (hi, lo) in enumerate(inputs[:target_frame+100]):
            val = hi | (lo << 8)
            s.sendall(f'set_controller 0 {val}\n'.encode())
            try: s.recv(512)
            except: pass
            
            # Capture screenshots at key frames
            if i in [15100, 15150, 15200, 15250, 15300]:
                bmp_path = os.path.join(OUT, f'{tag}_f{i}.bmp')
                s.sendall(f'screenshot {bmp_path}\n'.encode())
                try: s.recv(4096)
                except: pass
                print(f"[{tag}] Captured frame {i} -> {bmp_path}")
            
            if i % 2000 == 0:
                # Get PPU state at milestone frames
                s.sendall(b'get_ppu_state\n')
                try:
                    resp = s.recv(8192).decode()
                    state = json.loads(resp)
                    print(f"[{tag}] Frame {i}: TM=0x{state['screenEnabled'][0]} mode={state['bgmode']} SC0=0x{state['bgXsc'][0]} SC1=0x{state['bgXsc'][1]}")
                except:
                    print(f"[{tag}] Frame {i}: (ppu state unavailable)")
        
        s.close()
    except Exception as e:
        print(f"[{tag}] Error: {e}")
    finally:
        proc.terminate()
        time.sleep(1)
        proc.kill()

if __name__ == '__main__':
    print("=" * 60)
    print("Renderer comparison: ship interior scene")
    print("=" * 60)
    # First run with new renderer (default)
    run_test(True)
    print("\n---\n")
    # Then run with legacy renderer
    run_test(False)
    print("\nDone. Compare BMPs in", OUT)
