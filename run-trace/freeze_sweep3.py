#!/usr/bin/env python3
"""Robust freeze sweep: while frozen at target N, arm freeze for N+1 BEFORE
unfreezing, so even fast-forward stops exactly at each target."""
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

def frozen_at():
    try:
        st = json.loads(send_cmd("freeze_status", timeout=10))
        if st.get("freeze_capture") and st.get("boundary_frozen"):
            return st.get("frame", -1)
    except Exception:
        pass
    return -1

TARGETS = [9900, 9910, 9915, 9920, 9923, 9926, 9932,
           10120, 10128, 10134, 10140, 10150, 10157, 10165,
           10270, 10278, 10283, 10288,
           10390, 10400, 10403, 10406, 10410,
           10430, 10450, 10460, 10464, 10468, 10480, 10500]

env = dict(os.environ)
env["SNESRECOMP_REPLAY_FILE"] = REPLAY
env["SNESRECOMP_REPLAY_UP_PAUSE_MS"] = "0"
env["SNESRECOMP_EXIT_AT_FRAME"] = "20000"

proc = subprocess.Popen([EXE], cwd=WORK, env=env)
print("Exe launched...", flush=True)
time.sleep(3)

# First target: arm freeze now (frame is low), wait until frozen
def arm_and_wait(t, timeout=180):
    send_cmd("freeze_at_frame %d" % t)
    deadline = time.time() + timeout
    while time.time() < deadline:
        f = frozen_at()
        if f >= t:
            return f
        time.sleep(0.05)
    return -1

cur = -1
try:
    for i, t in enumerate(TARGETS):
        if cur >= 0:
            # while still frozen, arm next target
            send_cmd("freeze_at_frame %d" % t)
            send_cmd("unfreeze")
        f = arm_and_wait(t)
        if f >= t:
            spc = os.path.join(WORK, "sweep_f%d.bin" % t).replace("\\", "/")
            r = send_cmd("spc_dump %s" % spc)
            print("target %d frozen@%d dump=%s" % (t, f, "ok" if "ok" in r else r[:60]), flush=True)
            cur = f
        else:
            print("target %d MISSED" % t, flush=True)
            cur = -1
            send_cmd("unfreeze")
            time.sleep(0.5)
            # try to catch up by waiting for frame near t
            deadline = time.time() + 120
            while time.time() < deadline:
                fr = get_frame()
                if fr >= t - 2:
                    break
                time.sleep(0.1)
    print("\nDone", flush=True)
finally:
    if proc.poll() is None:
        proc.kill()
