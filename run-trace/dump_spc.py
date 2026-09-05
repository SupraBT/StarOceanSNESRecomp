#!/usr/bin/env python3
"""Dump SPC state at two freeze points and compare."""
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

try:
    for target in [10050, 10200]:
        send_cmd("unfreeze")
        time.sleep(0.5)
        deadline = time.time() + 120
        while time.time() < deadline:
            f = get_frame()
            if f >= target: break
            time.sleep(0.3)
        f = get_frame()
        send_cmd("freeze_at_frame %d" % target)
        time.sleep(2)

        # Dump SPC to file
        spc_path = os.path.join(WORK, "spc_f%d.bin" % target).replace("\\", "/")
        r = send_cmd("spc_dump %s" % spc_path)
        print("f%d: spc_dump -> %s | %s" % (target, spc_path, r), flush=True)

        # Also get audio_stats
        stats = json.loads(send_cmd("audio_stats"))
        print("f%d: kon=%d reg=%d underflows=%d" % (
            target, stats.get("kon_writes", 0),
            stats.get("reg_writes", 0),
            stats.get("output_underflows", 0)), flush=True)

finally:
    if proc.poll() is None:
        proc.kill()

# Now compare the SPC dumps
print("\nComparing SPC dumps...")
for target in [10050, 10200]:
    path = os.path.join(WORK, "spc_f%d.bin" % target)
    if os.path.exists(path):
        sz = os.path.getsize(path)
        print("spc_f%d.bin: %d bytes" % (target, sz))

# If both exist, diff key DSP registers
f1 = os.path.join(WORK, "spc_f10050.bin")
f2 = os.path.join(WORK, "spc_f10200.bin")
if os.path.exists(f1) and os.path.exists(f2):
    d1 = open(f1, "rb").read()
    d2 = open(f2, "rb").read()
    print("\nSPC dump sizes: %d vs %d" % (len(d1), len(d2)))
    # DSP registers are typically at a specific offset in the SPC dump
    # In SPC format, DSP regs start at offset 0x10100 (64KB SPC RAM + header)
    # Or in raw dump, they might be at the start
    # Let's look for the DSP register area
    # Standard SPC file: 0x100 = header, then 64KB RAM, then DSP regs at 0x10100
    dsp_off = 0x10100 if len(d1) > 0x10200 else 0
    if len(d1) > 0x10200:
        print("Likely SPC file format, DSP at offset 0x10100")
    else:
        print("Raw dump format")
        # Try to find DSP-like data
        dsp_off = 0

    # Compare DSP registers (128 bytes)
    if dsp_off + 128 <= len(d1) and dsp_off + 128 <= len(d2):
        regs1 = d1[dsp_off:dsp_off+128]
        regs2 = d2[dsp_off:dsp_off+128]
        diffs = []
        for i in range(128):
            if regs1[i] != regs2[i]:
                diffs.append((i, regs1[i], regs2[i]))
        print("\nDSP register differences (%d):" % len(diffs))
        # DSP register names
        dsp_names = {
            0x00: "VOLL0", 0x01: "VOLR0", 0x02: "PITCH0L", 0x03: "PITCH0H",
            0x04: "SRCN0", 0x05: "ADSR0_0", 0x06: "ADSR0_1", 0x07: "GAIN0",
            0x08: "VOLL1", 0x09: "VOLR1", 0x0C: "SRCN1",
            0x10: "VOLL2", 0x11: "VOLR2", 0x14: "SRCN2",
            0x18: "VOLL3", 0x19: "VOLR3", 0x1C: "SRCN3",
            0x20: "VOLL4", 0x21: "VOLR4", 0x24: "SRCN4",
            0x28: "VOLL5", 0x29: "VOLR5", 0x2C: "SRCN5",
            0x30: "VOLL6", 0x31: "VOLR6", 0x34: "SRCN6",
            0x38: "VOLL7", 0x39: "VOLR7", 0x3C: "SRCN7",
            0x4C: "KON", 0x5C: "KOF", 0x6C: "FLG", 0x7C: "ENDX",
            0x0C: "SRCN1", 0x6D: "EVB", 0x0D: "ENVX1",
        }
        for reg, old, new in diffs:
            name = dsp_names.get(reg, "reg%02x" % reg)
            print("  DSP[$%02X] (%s): $%02X -> $%02X" % (reg, name, old, new))
    else:
        print("Cannot determine DSP offset, sizes: %d vs %d" % (len(d1), len(d2)))
