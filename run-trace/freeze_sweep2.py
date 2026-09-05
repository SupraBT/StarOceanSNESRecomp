#!/usr/bin/env python3
"""Freeze EARLY (frame target-400) so the emulator stops exactly at target,
then spc_dump. Covers frames around the loudest zone-B jump and each nonzero KON."""
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

# The deep-run audio showed the biggest jump f10464->10465 and big RMS at f10466-10503.
# Nonzero KONs were f9923 (0x80), f10283 (0x40), f10403 (0x80).
# Freeze at a spread around each so we can watch per-voice DSP state evolve.
TARGETS = [9910, 9915, 9920, 9923, 9926,
           10270, 10278, 10283, 10288, 10300,
           10390, 10400, 10403, 10406, 10410,
           10430, 10450, 10460, 10464, 10468, 10480, 10500]

env = dict(os.environ)
env["SNESRECOMP_REPLAY_FILE"] = REPLAY
env["SNESRECOMP_REPLAY_UP_PAUSE_MS"] = "0"
env["SNESRECOMP_EXIT_AT_FRAME"] = "20000"

proc = subprocess.Popen([EXE], cwd=WORK, env=env)
print("Exe launched...", flush=True)
time.sleep(3)
t0 = time.time()
done = set()
try:
    while time.time() - t0 < 1200:
        f = get_frame()
        if f < 0:
            time.sleep(0.3); continue
        # arm freeze for the next target that is at least 300 frames ahead
        nxt = None
        for t in TARGETS:
            if t not in done and f < t - 300:
                nxt = t
                break
        if nxt is None:
            # all armed-or-passed targets that we haven't dumped and are <= f: skip (missed)
            for t in TARGETS:
                if t not in done and t <= f:
                    done.add(t)  # passed while busy; will not chase
            if len(done) == len(TARGETS):
                break
            time.sleep(0.2); continue
        send_cmd("freeze_at_frame %d" % nxt)
        # wait until actually frozen at >= nxt
        deadline = time.time() + 90
        frozen_at = -1
        while time.time() < deadline:
            st = json.loads(send_cmd("freeze_status", timeout=10))
            if st.get("freeze_capture") and st.get("boundary_frozen"):
                frozen_at = st.get("frame", -1)
                break
            if get_frame() >= nxt + 5:
                break  # overshot; something wrong
            time.sleep(0.05)
        if frozen_at >= nxt:
            spc = os.path.join(WORK, "sweep_f%d.bin" % nxt).replace("\\", "/")
            r = send_cmd("spc_dump %s" % spc)
            print("frozen@%d (target %d): ok=%s" % (frozen_at, nxt, "true" in r), flush=True)
            done.add(nxt)
            send_cmd("unfreeze")
            time.sleep(0.2)
        else:
            print("missed target %d (f=%d)" % (nxt, get_frame()), flush=True)
            done.add(nxt)
            send_cmd("unfreeze")
        sys.stdout.write("\rprogress %d/%d frame=%d" % (len(done), len(TARGETS), f))
        sys.stdout.flush()
    print("\nDone: %d dumps" % len([t for t in TARGETS if os.path.exists(
        os.path.join(WORK, "sweep_f%d.bin" % t))]), flush=True)
finally:
    if proc.poll() is None:
        proc.kill()
