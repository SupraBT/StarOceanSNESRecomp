#!/usr/bin/env python3
"""Trace audio events near the beep. Freeze at multiple points and
look for KON writes and DSP register changes."""
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
env["SNESRECOMP_EXIT_AT_FRAME"] = "10800"

proc = subprocess.Popen([EXE], cwd=WORK, env=env)
print("Exe launched...", flush=True)
time.sleep(3)

# Freeze at f10100, f10130, f10140 (near the beep)
FREEZE_POINTS = [9800, 10050, 10125, 10135, 10145, 10200]

try:
    for target in FREEZE_POINTS:
        send_cmd("unfreeze")
        time.sleep(0.5)
        deadline = time.time() + 120
        while time.time() < deadline:
            f = get_frame()
            if f >= target: break
            time.sleep(0.3)
        f = get_frame()
        if f < target:
            print("WARN: could not reach f%d" % target, flush=True)
            continue
        send_cmd("freeze_at_frame %d" % target)
        time.sleep(1.5)

        # Get full audio events
        events_raw = send_cmd("audio_events")
        events = json.loads(events_raw)

        # Get audio stats
        stats_raw = send_cmd("audio_stats")
        stats = json.loads(stats_raw)

        print("\n=== Frame %d (actual %d) ===" % (target, f))
        print("kon_writes: %d, reg_writes: %d, underflows: %d" % (
            stats.get("kon_writes", -1),
            stats.get("reg_writes", -1),
            stats.get("output_underflows", -1)))

        # Show only spc_wr events (DSP register writes from the SPC)
        evts = events.get("events", [])
        spc_wr = [e for e in evts if e.get("t") == "spc_wr"]
        cpu_ap = [e for e in evts if e.get("t") == "cpu_ap"]

        print("Total events: %d, spc_wr: %d, cpu_ap: %d" % (len(evts), len(spc_wr), len(cpu_ap)))

        # Show the last 10 spc_wr events (closest to this frame)
        if spc_wr:
            print("Last 10 SPC->DSP writes:")
            for e in spc_wr[-10:]:
                print("  cycle=%s addr=%s val=%s" % (e.get("s","?"), e.get("adr","?"), e.get("val","?")))

        # Show last 10 CPU->APU port writes
        if cpu_ap:
            print("Last 10 CPU->APU port writes:")
            for e in cpu_ap[-10:]:
                print("  cycle=%s port=%s val=%s" % (e.get("s","?"), e.get("adr","?"), e.get("val","?")))

finally:
    if proc.poll() is None:
        proc.kill()
    print("\nDone.")
