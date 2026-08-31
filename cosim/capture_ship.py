#!/usr/bin/env python3
"""Replay the real intro inputs and capture BMP screenshots at intervals so
the ship/battle scene can be inspected for the black-background bug."""
import subprocess, time, socket, os, sys, glob

sys.stdout.reconfigure(encoding="utf-8")

PORT = 13308
EVENTS_FILE = r"cosim\intro_101648_inputs.txt"
EXE_PATH = r"build\Release\StarOcean.exe"
OUT_DIR = r"build-cosim\ship-caps"
FIRST_IDX = int(sys.argv[1]) if len(sys.argv) > 1 else 400
LAST_IDX = int(sys.argv[2]) if len(sys.argv) > 2 else 12000
STEP = int(sys.argv[3]) if len(sys.argv) > 3 else 700

os.makedirs(OUT_DIR, exist_ok=True)

def parse_events(path):
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(':')
            events.append((int(parts[0]), int(parts[1]), int(parts[2], 16)))
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

def connect(port=PORT, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=2)
            s.settimeout(5)
            try:
                s.recv(4096)
            except Exception:
                pass
            return s
        except Exception:
            time.sleep(0.3)
    return None

def send(sock, cmd, timeout=2.0):
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
                if b"\n" in data:
                    break
        except socket.timeout:
            pass
        return data.decode(errors="replace").strip()
    except (BrokenPipeError, OSError) as e:
        return f"ERROR: {e}"

# clean stale captures
for f in glob.glob(os.path.join(OUT_DIR, "*.bmp")):
    os.remove(f)

frames = events_to_frames(parse_events(EVENTS_FILE))
print(f"[capture] {len(frames)} input frames, capturing {FIRST_IDX}..{LAST_IDX} every {STEP}")

os.system("taskkill /F /IM StarOcean.exe 2>nul")
time.sleep(2)
stderr_log = open(os.path.join(OUT_DIR, "stderr.log"), "w")
exe = os.path.abspath(EXE_PATH)
env = os.environ.copy()
env["SNESRECOMP_NO_DEBUG_WINDOW"] = "1"
proc = subprocess.Popen([exe], cwd=os.path.dirname(exe), env=env,
                        stdout=subprocess.DEVNULL, stderr=stderr_log)
print(f"  PID={proc.pid}")
sock = connect()
if not sock:
    print("ERROR: no debug server"); proc.kill(); sys.exit(1)
print("  connected")

next_cap = FIRST_IDX
for idx in range(min(len(frames), LAST_IDX)):
    mask = frames[idx]
    try:
        sock.sendall((f"set_controller 0x{mask:04X}\n").encode())
        sock.settimeout(0.02)
        try:
            sock.recv(4096)
        except Exception:
            pass
    except (BrokenPipeError, OSError):
        print(f"  conn lost at {idx}"); break
    if idx >= next_cap:
        path = os.path.abspath(os.path.join(OUT_DIR, f"cap_{idx:05d}.bmp"))
        resp = send(sock, f"screenshot {path}", timeout=3)
        print(f"  [{idx}] screenshot -> {resp[:80]}")
        next_cap += STEP
    if idx % 500 == 0:
        time.sleep(0.002)

stderr_log.close()
sock.close()
proc.kill()
proc.wait()
print("[capture] done")
