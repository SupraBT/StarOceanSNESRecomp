#!/usr/bin/env python3
"""A/B determinism capture: freeze just past f10560, dump ring WAV + all events.

Run twice -> compare per-frame DSP reg writes + port traffic between the runs.
"""
import json, os, socket, subprocess, sys, time

WORK = r"F:\StarOceanRecompRAID\run-trace"
EXE = os.path.join(WORK, "StarOcean.exe")
REPLAY = os.path.join(WORK, "replay_3_peleas.txt")
HOST, PORT = "127.0.0.1", 13308

def send_cmd(cmd, timeout=60):
    s = socket.create_connection((HOST, PORT), timeout=timeout)
    s.settimeout(timeout)
    s.sendall((cmd + "\n").encode())
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
    s.close()
    return buf.decode(errors="replace").strip()

def get_frame():
    try:
        return json.loads(send_cmd("ping", timeout=10)).get("frame", -1)
    except Exception:
        return -1

TARGET = 10560
tag = sys.argv[1] if len(sys.argv) > 1 else "ab"

env = dict(os.environ)
env["SNESRECOMP_REPLAY_FILE"] = REPLAY
env["SNESRECOMP_REPLAY_UP_PAUSE_MS"] = "0"
env["SNESRECOMP_EXIT_AT_FRAME"] = "20000"

proc = subprocess.Popen([EXE], cwd=WORK, env=env)
print("Exe launched...", flush=True)
time.sleep(3)

try:
    deadline = time.time() + 600
    while time.time() < deadline:
        f = get_frame()
        if f >= TARGET:
            break
        time.sleep(0.25)
    fnow = get_frame()
    print("frame now: %d (target %d)" % (fnow, TARGET), flush=True)

    # Arm freeze at the exact current frame so the stop is deterministic-ish.
    r = send_cmd("freeze_at_frame %d" % fnow)
    time.sleep(1)
    frozen = get_frame()
    print("frozen frame: %d" % frozen, flush=True)

    wav = os.path.join(WORK, "%s_ring.wav" % tag).replace("\\", "/")
    r = send_cmd("audio_wav %s -1 0" % wav, timeout=120)
    wj = json.loads(r)
    print("audio_wav:", wj, flush=True)

    all_events = []
    first = 0
    for _ in range(80):
        r = send_cmd("audio_events %d 8000 0" % first, timeout=60)
        try:
            j = json.loads(r)
        except Exception:
            print("parse err at first=%d: %s" % (first, r[:120]), flush=True)
            break
        evs = j.get("events", [])
        all_events.extend(evs)
        returned = j.get("returned", 0)
        oldest = j.get("oldest", 0)
        if returned < 8000:
            break
        first = oldest + len(all_events)
    print("collected %d events" % len(all_events), flush=True)

    with open(os.path.join(WORK, "%s_events.json" % tag), "w") as fh:
        json.dump({"freeze_frame": frozen, "events": all_events}, fh)
    print("saved %s_events.json" % tag, flush=True)

    spc = os.path.join(WORK, "%s_spc.bin" % tag).replace("\\", "/")
    r = send_cmd("spc_dump %s" % spc)
    print("spc_dump:", r, flush=True)

finally:
    if proc.poll() is None:
        proc.kill()
print("Done.", flush=True)
