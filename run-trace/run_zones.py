#!/usr/bin/env python3
"""Run replay through both zones, dump ring buffer at zone boundaries."""
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

proc = subprocess.Popen([EXE], cwd=WORK, env=env)
print("Exe launched, waiting for debug server...", flush=True)
time.sleep(3)

last_dump = -1
try:
    while proc.poll() is None:
        f = get_frame()
        if f > 0:
            if f >= 7589 and last_dump < 7589:
                p = os.path.join(WORK, "zone_A_end.wav")
                r = send_cmd("audio_wav %s -1 0" % p.replace("\\", "/"))
                print("\nframe=%d DUMP zone_A_end: %s" % (f, r), flush=True)
                last_dump = 7589
            elif f >= 10520 and last_dump < 10520:
                p = os.path.join(WORK, "zone_B_end.wav")
                r = send_cmd("audio_wav %s -1 0" % p.replace("\\", "/"))
                print("\nframe=%d DUMP zone_B_end: %s" % (f, r), flush=True)
                last_dump = 10520
                break
            sys.stdout.write("\rframe=%d " % f)
            sys.stdout.flush()
        time.sleep(3)
    print("\nDone (rc=%s)" % proc.returncode)
finally:
    if proc.poll() is None:
        proc.kill()
