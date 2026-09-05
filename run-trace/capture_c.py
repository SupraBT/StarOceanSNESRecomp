#!/usr/bin/env python3
"""Reference capture with VERIFIED freeze: saves the audio_wav response (exact
ring start) so ring offsets are known precisely."""
import json, os, socket, subprocess, sys, time

WORK = r"F:\StarOceanRecompRAID\run-trace"
EXE = os.path.join(WORK, "StarOcean.exe")
REPLAY = os.path.join(WORK, "replay_3_peleas.txt")
HOST, PORT = "127.0.0.1", 13308
TARGET = 10560
tag = sys.argv[1] if len(sys.argv) > 1 else "c1"

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
        time.sleep(0.2)
    fnow = get_frame()
    print("frame now: %d" % fnow, flush=True)

    # freeze at current frame, then VERIFY the exe is actually stopped
    send_cmd("freeze_at_frame %d" % fnow)
    time.sleep(1.0)
    f1 = get_frame()
    time.sleep(0.5)
    f2 = get_frame()
    st = send_cmd("freeze_status")
    print("freeze check: f1=%d f2=%d status=%s" % (f1, f2, st[:120]), flush=True)

    wav = os.path.join(WORK, "%s_ring.wav" % tag).replace("\\", "/")
    r = send_cmd("audio_wav %s -1 0" % wav, timeout=120)
    print("audio_wav:", r[:200], flush=True)
    try:
        wj = json.loads(r)
    except Exception:
        wj = {}
    meta = {"freeze_frame": f2, "wav": wj}
    json.dump(meta, open(os.path.join(WORK, "%s_meta.json" % tag), "w"))
    print("saved %s_meta.json" % tag, flush=True)

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
        if j.get("returned", 0) < 8000:
            break
        first = j.get("oldest", 0) + len(all_events)
    print("collected %d events" % len(all_events), flush=True)
    json.dump({"events": all_events}, open(os.path.join(WORK, "%s_events.json" % tag), "w"))

    spc = os.path.join(WORK, "%s_spc.bin" % tag).replace("\\", "/")
    r = send_cmd("spc_dump %s" % spc)
    print("spc_dump:", r[:120], flush=True)

finally:
    if proc.poll() is None:
        proc.kill()
print("Done.", flush=True)
