#!/usr/bin/env python3
"""Investigate the beep at ~f10134. Freeze emulation, dump SPC state."""
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

env = dict(os.environ)
env["SNESRECOMP_REPLAY_FILE"] = REPLAY
env["SNESRECOMP_REPLAY_UP_PAUSE_MS"] = "0"
# Exit at frame 10200 to be safe
env["SNESRECOMP_EXIT_AT_FRAME"] = "10200"

proc = subprocess.Popen([EXE], cwd=WORK, env=env)
print("Exe launched...", flush=True)
time.sleep(3)

try:
    # Wait until we reach ~f10120
    while True:
        f = get_frame()
        if f < 0:
            if proc.poll() is not None:
                print("exe exited early"); break
            time.sleep(1); continue
        print("frame=%d" % f, flush=True)
        if f >= 10120:
            break

    # Freeze at frame 10125 (just before the beep at ~10134)
    print("\n=== FREEZE at f10125 (antes del pitido) ===", flush=True)
    r = send_cmd("freeze_at_frame 10125")
    print("freeze_at_frame:", r, flush=True)
    time.sleep(2)

    # Dump SPC state
    r = send_cmd("spc_dump")
    print("spc_dump:", r[:500], flush=True)

    # Audio stats
    r = send_cmd("audio_stats")
    print("audio_stats:", r[:500], flush=True)

    # Audio events
    r = send_cmd("audio_events")
    print("audio_events:", r[:500], flush=True)

    # Unfreeze and let it pass the beep
    print("\n=== Unfreeze, let it pass f10134 ===", flush=True)
    send_cmd("unfreeze")
    time.sleep(1)

    # Freeze again at ~f10145 (after the beep)
    r = send_cmd("freeze_at_frame 10145")
    print("freeze_at_frame 10145:", r, flush=True)
    time.sleep(2)

    # Dump SPC state again
    r = send_cmd("spc_dump")
    print("spc_dump:", r[:500], flush=True)

    # Audio stats after beep
    r = send_cmd("audio_stats")
    print("audio_stats:", r[:500], flush=True)

    # Audio events
    r = send_cmd("audio_events")
    print("audio_events:", r[:500], flush=True)

finally:
    if proc.poll() is None:
        proc.kill()
    print("\nDone.")
