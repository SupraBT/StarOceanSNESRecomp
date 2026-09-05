#!/usr/bin/env python3
"""Capture DSP-register-write events + audio ring around the pitido zone (f9808-f10520).

Runs the replay, lets the ring accumulate well past the pitido, then freezes and
dumps: (a) whole PCM ring WAV, (b) port-traffic events (which carry the SNES
frame in aux) so sample_idx <-> frame can be anchored, (c) DSP reg-write events.
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
        line = send_cmd("ping", timeout=10)
        return json.loads(line).get("frame", -1)
    except Exception:
        return -1

env = dict(os.environ)
env["SNESRECOMP_REPLAY_FILE"] = REPLAY
env["SNESRECOMP_REPLAY_UP_PAUSE_MS"] = "0"
env["SNESRECOMP_EXIT_AT_FRAME"] = "20000"

proc = subprocess.Popen([EXE], cwd=WORK, env=env)
print("Exe launched, waiting for debug server...", flush=True)
time.sleep(3)

try:
    # Let it run until frame >= 10600 (pitido zone well inside the PCM ring).
    deadline = time.time() + 600
    last = -1
    while time.time() < deadline:
        f = get_frame()
        if f > 0:
            if f != last:
                sys.stdout.write("\rframe=%d" % f)
                sys.stdout.flush()
                last = f
            if f >= 10600:
                break
        time.sleep(0.5)
    print("\nReached frame %d; freezing." % get_frame(), flush=True)

    r = send_cmd("freeze_at_frame %d" % get_frame())
    print("freeze:", r, flush=True)
    time.sleep(1)

    # 1) Whole PCM ring WAV (everything still in ring)
    wav = os.path.join(WORK, "deep_pcm_ring.wav").replace("\\", "/")
    r = send_cmd("audio_wav %s -1 0" % wav, timeout=120)
    print("audio_wav:", r, flush=True)
    wj = json.loads(r)
    start, count = wj.get("start", 0), wj.get("count", 0)

    # 2) Port traffic + reg events in the retained window. Events ring is big
    #    (2^19); scan from oldest in 8000-event chunks and keep the tail.
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
        first = oldest + (len(all_events))
    print("collected %d events" % len(all_events), flush=True)

    # anchor: port events carry frame in aux
    anchors = [e for e in all_events if e["t"] in ("cpu_wr", "cpu_ap", "spc_wr")]
    print("port events:", len(anchors), flush=True)
    # print a sample anchor every ~200 frames of the zone
    prev = None
    with open(os.path.join(WORK, "deep_events.json"), "w") as fh:
        json.dump(all_events, fh)
    print("saved deep_events.json", flush=True)

    # 3) spc_dump at the freeze point for reference
    spc = os.path.join(WORK, "deep_spc_end.bin").replace("\\", "/")
    r = send_cmd("spc_dump %s" % spc)
    print("spc_dump:", r, flush=True)

finally:
    if proc.poll() is None:
        proc.kill()
print("\nDone.")
