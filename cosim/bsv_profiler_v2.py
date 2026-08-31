#!/usr/bin/env python3
"""
BSV Profiler v2 — Replay intro_101648_inputs.txt via debug server TCP
and capture per-frame FPS telemetry + tier2 dispatch diagnostics.

Events file format: frame:duration:mask (hex mask, e.g. 100 = A button)
"""
import subprocess, time, socket, os, sys, json, struct

sys.stdout.reconfigure(encoding='utf-8')

PORT = 13308
EVENTS_FILE = r"cosim\intro_101648_inputs.txt"
EXE_PATH = r"build\Release\StarOcean.exe"
OUTPUT_DIR = r"build-cosim"
RESULT_FILE = os.path.join(OUTPUT_DIR, "bsv_profile_v2.json")
STDERR_LOG = os.path.join(OUTPUT_DIR, "bsv_v2_stderr.log")

BTN = ['B','Y','Sel','Sta','Up','Dn','Lf','Rt','A','X','L','R']

def parse_events(path):
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(':')
            frame, duration, mask = int(parts[0]), int(parts[1]), int(parts[2], 16)
            events.append((frame, duration, mask))
    return events

def events_to_frames(events):
    if not events:
        return []
    last_frame = events[-1][0] + events[-1][1]
    frames = [0] * last_frame
    for start, dur, mask in events:
        for i in range(start, min(start + dur, last_frame)):
            frames[i] = mask
    return frames

def connect(port=PORT, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=2)
            s.settimeout(5)
            try:
                s.recv(4096)
            except:
                pass
            return s
        except:
            time.sleep(0.3)
    return None

def send_cmd(sock, cmd, timeout=2.0):
    """Send a command and return the response."""
    try:
        sock.sendall((cmd + "\n").encode())
        sock.settimeout(timeout)
        data = b""
        try:
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                data += chunk
                # Check if we got a complete JSON line
                if b"\n" in data:
                    break
        except socket.timeout:
            pass
        return data.decode(errors='replace').strip()
    except (BrokenPipeError, OSError) as e:
        return f"ERROR: {e}"

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Parse events
    print("[Profiler v2] Parsing events file...")
    events = parse_events(EVENTS_FILE)
    total_events_frames = events[-1][0] + events[-1][1] if events else 0
    active_events = sum(1 for _, _, m in events if m != 0)
    print(f"  Events: {len(events)} ({active_events} active)")
    print(f"  Total frames to replay: {total_events_frames} ({total_events_frames/60:.1f}s)")

    frame_masks = events_to_frames(events)
    print(f"  Frame array length: {len(frame_masks)}")

    # Kill existing
    os.system("taskkill /F /IM StarOcean.exe 2>nul")
    time.sleep(2)

    # Launch exe
    print("[Profiler v2] Launching exe...")
    exe = os.path.abspath(EXE_PATH)
    cwd = os.path.dirname(exe)
    env = os.environ.copy()
    env["SNESRECOMP_FPS"] = "1"
    env["SNESRECOMP_NO_DEBUG_WINDOW"] = "1"

    stderr_log = open(STDERR_LOG, "w")
    proc = subprocess.Popen(
        [exe], cwd=cwd, env=env,
        stdout=subprocess.DEVNULL, stderr=stderr_log
    )
    print(f"  PID={proc.pid}")

    # Connect
    print("[Profiler v2] Connecting to debug server...")
    sock = connect()
    if not sock:
        print("ERROR: Could not connect!")
        proc.kill()
        stderr_log.close()
        return
    print("  Connected!")

    # Enable profiling
    resp = send_cmd(sock, "profile_on")
    print(f"  profile_on: {resp}")

    # Replay
    print(f"[Profiler v2] Replaying {len(frame_masks)} frames...")
    t_start = time.time()
    fps_log = []
    frame_count = 0

    for idx in range(len(frame_masks)):
        mask = frame_masks[idx]
        cmd = f"set_controller 0x{mask:04X}"
        try:
            sock.sendall((cmd + "\n").encode())
            sock.settimeout(0.02)
            try:
                sock.recv(4096)
            except:
                pass
        except (BrokenPipeError, OSError):
            print(f"  Connection lost at frame {idx}")
            break

        frame_count = idx + 1

        if frame_count % 1000 == 0:
            now = time.time()
            elapsed = now - t_start
            total_fps = frame_count / max(elapsed, 0.001)
            btns = [BTN[b] for b in range(12) if mask & (1 << b)]
            btn_str = ','.join(btns) if btns else '---'
            print(f"  [{elapsed:7.1f}s] frame={frame_count:6d} "
                  f"fps_avg={total_fps:6.1f} 0x{mask:04X}({btn_str})")
            fps_log.append({
                "frame": frame_count,
                "elapsed_s": round(elapsed, 3),
                "avg_fps": round(total_fps, 1),
                "mask": f"0x{mask:04X}",
                "buttons": btn_str
            })

        if idx % 100 == 0:
            time.sleep(0.001)

    elapsed = time.time() - t_start
    avg_fps = frame_count / max(elapsed, 0.001)
    print(f"\n[Profiler v2] REPLAY COMPLETE")
    print(f"  Frames: {frame_count}, Wall: {elapsed:.1f}s, Avg: {avg_fps:.1f} fps")

    # === DIAGNOSTIC QUERIES ===
    print("\n" + "=" * 60)
    print("DIAGNOSTIC QUERIES")
    print("=" * 60)

    # 1. interp_stats (AOT vs LLE split)
    print("\n--- interp_stats ---")
    interp_resp = send_cmd(sock, "interp_stats")
    print(interp_resp[:1000])
    try:
        interp_data = json.loads(interp_resp)
    except:
        interp_data = {}

    # 2. profile query
    print("\n--- profile ---")
    profile_resp = send_cmd(sock, "profile")
    print(profile_resp[:1000])
    try:
        profile_data = json.loads(profile_resp)
    except:
        profile_data = {}

    # 3. dispatch_log_get (last 256 dispatches)
    print("\n--- dispatch_log (last 256) ---")
    dispatch_resp = send_cmd(sock, "dispatch_log_get count=256", timeout=5)
    print(dispatch_resp[:2000])
    try:
        dispatch_data = json.loads(dispatch_resp)
    except:
        dispatch_data = {"raw": dispatch_resp[:2000]}

    # 4. tier2_dump
    print("\n--- tier2_dump ---")
    tier2_resp = send_cmd(sock, "tier2_dump", timeout=5)
    print(tier2_resp[:500])
    try:
        tier2_info = json.loads(tier2_resp)
    except:
        tier2_info = {"raw": tier2_resp[:500]}

    # Save all results
    result = {
        "total_frames": frame_count,
        "wall_time_s": round(elapsed, 2),
        "avg_fps": round(avg_fps, 1),
        "fps_samples": fps_log,
        "interp_stats": interp_data,
        "profile": profile_data,
        "dispatch_log": dispatch_data,
        "tier2_dump": tier2_info,
    }
    with open(RESULT_FILE, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Results saved: {RESULT_FILE}")

    stderr_log.close()
    sock.close()
    proc.kill()
    proc.wait()

if __name__ == "__main__":
    main()
