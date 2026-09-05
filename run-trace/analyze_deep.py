#!/usr/bin/env python3
"""Locate the pitido in the deep capture and extract DSP reg writes around it."""
import json, math, struct, wave

WORK = r"F:\StarOceanRecompRAID\run-trace"
RATE = 32040
SNES_FPS = 60.0988
SAMPLES_PER_FRAME = RATE / SNES_FPS  # ~533.1

evs = json.load(open(WORK + r"\deep_events.json"))

# ---- 1. frame <-> sample mapping from port events (aux = frame) ----
ports = [e for e in evs if e["t"] in ("cpu_wr", "cpu_ap", "spc_wr")]
# sample_idx -> frame for the zone
frame_map = sorted((e["s"], e["aux"]) for e in ports if 9000 <= e["aux"] <= 11000)
print("port-frame anchors in zone:", len(frame_map))
if frame_map:
    print("first anchor: sample=%d frame=%d" % frame_map[0])
    print("last  anchor: sample=%d frame=%d" % frame_map[-1])

def sample_of_frame(fr):
    xs = [s for s, f in frame_map]
    fs = [f for s, f in frame_map]
    if fr <= fs[0]: return xs[0]
    if fr >= fs[-1]: return xs[-1]
    # bisect
    lo, hi = 0, len(fs) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if fs[mid] <= fr: lo = mid
        else: hi = mid
    if fs[hi] == fs[lo]: return xs[lo]
    return xs[lo] + (fr - fs[lo]) * (xs[hi] - xs[lo]) // (fs[hi] - fs[lo])

# ---- 2. read WAV ----
wav = wave.open(WORK + r"\deep_pcm_ring.wav", "rb")
n = wav.getnframes()
print("wav frames:", n, "rate:", wav.getframerate())
data = wav.readframes(n)
samples = struct.unpack("<%dh" % (n * 2), data)
L = samples[0::2]
R = samples[1::2]
# WAV holds the ring tail: absolute produced clock at dump ~7045476 (spc_dump).
WAV_START = 7045476 - n  # absolute sample of wav[0]
print("wav_start (abs):", WAV_START)

def rel(ab):
    return ab - WAV_START

# indices used below are absolute; convert once
s_zone_a = rel(sample_of_frame(9808))
s_zone_b = rel(sample_of_frame(10520))

# ---- 3. per-frame RMS over the f9808..f10520 zone ----
abs_a = sample_of_frame(9808)
abs_b = sample_of_frame(10520)
print("zone abs range: %d..%d (%.1f s)" % (abs_a, abs_b, (abs_b - abs_a) / RATE))
s_zone_a = rel(abs_a)
s_zone_b = rel(abs_b)
print("zone wav range: %d..%d (%d samples, %.1f s)" % (s_zone_a, s_zone_b, s_zone_b - s_zone_a, (s_zone_b - s_zone_a) / RATE))

def rms_window(i0, i1):
    tot = 0
    for i in range(i0, i1, 1):
        v = samples[i * 2]
        tot += v * v
    return math.sqrt(tot / max(1, i1 - i0))

rows = []
i = s_zone_a
frame = 9808
while i < s_zone_b - int(SAMPLES_PER_FRAME):
    i1 = i + int(SAMPLES_PER_FRAME)
    r = rms_window(i, i1)
    rows.append((frame, i, r))
    frame += 1
    i = i1

# print frames around peaks
print("\nper-frame RMS (frame: rms) around loudest frames:")
peaks = sorted(rows, key=lambda r: -r[2])[:8]
for fr, sidx, r in sorted(peaks):
    print("  frame %d  sample %d  rms %.0f" % (fr, sidx, r))

# print a windowed table around the maximum (or the onset of a jump)
# find biggest adjacent jump in rms
best = None
for a, b in zip(rows, rows[1:]):
    if a[2] > 100:  # skip silence
        j = b[2] - a[2]
        if best is None or j > best[0]:
            best = (j, a, b)
if best:
    print("\nbiggest RMS jump: frame %d (%.0f) -> frame %d (%.0f)" % (best[1][0], best[1][2], best[2][0], best[2][2]))
