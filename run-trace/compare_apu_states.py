#!/usr/bin/env python3
"""Compare SPC/APU state at multiple frames in the f9808-f10520 range."""
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
        line = send_cmd("ping", timeout=10)
        return json.loads(line).get("frame", -1)
    except:
        return -1

# Freeze points: one BEFORE the range (baseline), several inside
FREEZE_POINTS = [9700, 9900, 10000, 10100, 10200, 10300, 10400, 10600]

env = dict(os.environ)
env["SNESRECOMP_REPLAY_FILE"] = REPLAY
env["SNESRECOMP_REPLAY_UP_PAUSE_MS"] = "0"
env["SNESRECOMP_EXIT_AT_FRAME"] = "10800"

proc = subprocess.Popen([EXE], cwd=WORK, env=env)
print("Exe launched...", flush=True)
time.sleep(3)

results = {}
try:
    for target in FREEZE_POINTS:
        # Unfreeze and wait for target frame
        send_cmd("unfreeze")
        time.sleep(0.5)

        # Poll until we reach target
        deadline = time.time() + 120
        while time.time() < deadline:
            f = get_frame()
            if f >= target:
                break
            time.sleep(0.3)

        f = get_frame()
        if f < target:
            print("WARN: could not reach f%d, at f%d" % (target, f), flush=True)
            continue

        # Freeze
        send_cmd("freeze_at_frame %d" % target)
        time.sleep(1.5)

        # Dump audio_stats and spc_dump
        audio_stats = send_cmd("audio_stats")
        spc = send_cmd("spc_dump")
        audio_events = send_cmd("audio_events")

        results[target] = {
            "frame": f,
            "audio_stats": audio_stats,
            "spc_dump": spc,
            "audio_events": audio_events,
        }
        print("f%d captured (actual f%d)" % (target, f), flush=True)

finally:
    if proc.poll() is None:
        proc.kill()

# Print comparison
print("\n\n===== COMPARISON =====\n")
for target in sorted(results.keys()):
    r = results[target]
    print("--- Frame %d ---" % target)
    print("audio_stats: %s" % r["audio_stats"][:300])
    print("spc_dump: %s" % r["spc_dump"][:300])
    print("audio_events: %s" % r["audio_events"][:300])
    print()
