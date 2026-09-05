#!/usr/bin/env python3
"""Freeze at key frames around each nonzero KON + the loudest audio jump in zone B,
and spc_dump each so per-voice DSP state can be inspected."""
import json, os, socket, subprocess, sys, time

WORK = r"F:\StarOceanRecompRAID\run-trace"
EXE = os.path.join(WORK, "StarOcean.exe")
REPLAY = os.path.join(WORK, "replay_3_peleas.txt")
HOST, PORT = "127.0.0.1", 13308

def send_cmd(cmd, timeout=30):
    s = socket.create_connection((HOST, PORT), timeout=timeout)
    s.settimeout(timeout)
    s.sendall((cmd + "\n").encode())
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = s.recv(65536)
        if not chunk: break
        buf += chunk
    s.close()
    return buf.decode(errors="replace").strip()

def get_frame():
    try:
        return json.loads(send_cmd("ping", timeout=10)).get("frame", -1)
    except Exception:
        return -1

# Frames to dump: ±2 around each nonzero KON, plus the loud-jump frame 10464/10465.
# Deterministic replay: freeze_at_frame(n) pauses AT n; wait until frozen.
TARGETS = [9918, 9921, 9923, 9925, 10279, 10283, 10287,
           10399, 10403, 10407, 10462, 10464, 10466, 10470]

env = dict(os.environ)
env["SNESRECOMP_REPLAY_FILE"] = REPLAY
env["SNESRECOMP_REPLAY_UP_PAUSE_MS"] = "0"
env["SNESRECOMP_EXIT_AT_FRAME"] = "20000"

proc = subprocess.Popen([EXE], cwd=WORK, env=env)
print("Exe launched...", flush=True)
time.sleep(3)
t0 = time.time()
try:
    idx = 0
    while time.time() - t0 < 900:
        f = get_frame()
        if f < 0:
            time.sleep(0.3); continue
        if idx < len(TARGETS) and f >= TARGETS[idx] - 1:
            t = TARGETS[idx]
            # arm freeze at t (if not already past), wait until frozen at t
            send_cmd("freeze_at_frame %d" % t)
            deadline = time.time() + 60
            while time.time() < deadline:
                st = json.loads(send_cmd("freeze_status", timeout=10))
                if st.get("freeze_capture") and st.get("frame", -1) >= t:
                    break
                time.sleep(0.1)
            time.sleep(0.3)
            cur = get_frame()
            spc = os.path.join(WORK, "sweep_f%d.bin" % t).replace("\\", "/")
            r = send_cmd("spc_dump %s" % spc)
            print("frame %d (frozen@%d): %s" % (t, cur, r), flush=True)
            idx += 1
            send_cmd("unfreeze")
            time.sleep(0.3)
        elif idx >= len(TARGETS):
            break
        else:
            sys.stdout.write("\rframe=%d next=%d" % (f, TARGETS[idx]))
            sys.stdout.flush()
            time.sleep(0.3)
    print("\nDone, dumps: %d" % idx, flush=True)
finally:
    if proc.poll() is None:
        proc.kill()
