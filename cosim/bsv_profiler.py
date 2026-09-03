#!/usr/bin/env python3
"""BSV replay profiler - run as standalone script."""
import subprocess, time, socket, os, sys, json, struct

sys.stdout.reconfigure(encoding='utf-8')

PORT = 13308
BSV_PATH = r"Star Ocean (Japan) [Traducida Castellano]-20260825-101648.bsv"
EXE_PATH = r"build\Release\StarOcean.exe"
MAX_FRAMES = 200000
OUTPUT = r"build-cosim\bsv_profile_result.json"

def parse_bsv(path):
    with open(path, "rb") as f:
        data = f.read()
    INPUT_START = 0x22C
    inputs = []
    remaining = data[INPUT_START:]
    n_frames = len(remaining) // 2
    for i in range(min(n_frames, MAX_FRAMES)):
        val = struct.unpack('<H', remaining[i*2:i*2+2])[0]
        inputs.append((INPUT_START//2 + i, val & 0x0FFF))
    return inputs

def launch_exe():
    exe = os.path.abspath(EXE_PATH)
    cwd = os.path.dirname(exe)
    env = os.environ.copy()
    env["SNESRECOMP_FPS"] = "1"
    env["SNESRECOMP_NO_DEBUG_WINDOW"] = "1"
    proc = subprocess.Popen([exe], cwd=cwd, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc

def connect(port=PORT, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=2)
            s.settimeout(5)
            try: s.recv(4096)
            except: pass
            return s
        except:
            time.sleep(0.2)
    return None

def main():
    os.makedirs("build-cosim", exist_ok=True)
    
    print("[BSV Profiler] Parsing BSV...")
    inputs = parse_bsv(BSV_PATH)
    last_active = max((i for i, (_, m) in enumerate(inputs) if m != 0), default=0)
    active = sum(1 for _, m in inputs if m != 0)
    print(f"  {len(inputs)} frames, {active} active, last_active={last_active}")

    # Kill existing
    os.system("taskkill /F /IM StarOcean.exe 2>nul")
    time.sleep(2)

    print("[BSV Profiler] Launching exe...")
    proc = launch_exe()
    print(f"  PID={proc.pid}")

    print("[BSV Profiler] Connecting to debug server...")
    sock = connect(timeout=60)
    if not sock:
        print("ERROR: Could not connect!")
        os.system("taskkill /F /IM StarOcean.exe 2>nul")
        return
    print("  Connected!")

    # Profile loop
    fps_data = []
    t_start = time.time()
    frames_sent = 0
    log_count = 0

    for idx, (orig, mask) in enumerate(inputs):
        if idx >= MAX_FRAMES:
            break
        
        cmd = f"set_controller 0x{mask:04X}"
        try:
            sock.sendall((cmd + "\n").encode())
            # Read response (non-blocking)
            sock.settimeout(0.1)
            try:
                sock.recv(4096)
            except:
                pass
        except (BrokenPipeError, OSError):
            print(f"  Connection lost at frame {idx}")
            break

        frames_sent += 1
        log_count += 1

        if log_count >= 500:
            now = time.time()
            elapsed = now - t_start
            fps = log_count / max(elapsed - (fps_data[-1][2] if fps_data else 0), 0.001)
            btn_names = ['B','Y','Sel','Sta','Up','Dn','Lf','Rt','A','X','L','R']
            btns = [btn_names[b] for b in range(12) if mask & (1 << b)]
            total_fps = frames_sent / max(now - t_start, 0.001)
            print(f"  [{elapsed:7.1f}s] frame={idx:7d} inst_fps={fps:5.1f} total={total_fps:5.1f} "
                  f"input=0x{mask:04X}({','.join(btns) if btns else '---'})")
            fps_data.append((idx, round(fps, 1), round(elapsed, 3)))
            log_count = 0

        # Brief yield to prevent socket buffer issues
        if idx % 100 == 0:
            time.sleep(0.001)

    elapsed = time.time() - t_start
    print(f"\n[BSV Profiler] DONE: {frames_sent} frames in {elapsed:.1f}s ({frames_sent/elapsed:.1f} fps)")

    # Save results
    with open(OUTPUT, "w") as f:
        json.dump({
            "total_frames": frames_sent,
            "wall_time_s": round(elapsed, 2),
            "avg_fps": round(frames_sent/elapsed, 1),
            "fps_samples": fps_data,
        }, f, indent=2)
    print(f"  Results saved to {OUTPUT}")

    sock.close()
    os.system("taskkill /F /IM StarOcean.exe 2>nul")

if __name__ == "__main__":
    main()
