#!/usr/bin/env python3
"""Fine onset scan over zone B of deep_pcm_ring.wav: find beep-like transients.

Beep signature: RMS floor (walk ambience) then a short burst (tonal, high
spectral centroid) lasting ~30-400 ms, clearly above the local floor.
"""
import wave, struct, math, bisect, json

WORK = r"F:\StarOceanRecompRAID\run-trace"
RATE = 32040

evs = json.load(open(WORK + r"\deep_events.json"))
for e in evs:
    e["adr"] = int(str(e["adr"]), 16)
    e["val"] = int(str(e["val"]), 16)
ports = [e for e in evs if e["t"] in ("cpu_wr", "cpu_ap")]
frame_sorted = sorted((e["aux"], e["s"]) for e in ports)
fs = [f for f, s in frame_sorted]
xs = [s for f, s in frame_sorted]

def frame_of_sample(s):
    i = bisect.bisect_left(xs, s)
    if i == 0: return fs[0]
    if i >= len(fs): return fs[-1]
    f0, f1 = fs[i-1], fs[i]
    x0, x1 = xs[i-1], xs[i]
    if x1 == x0: return f0
    return f0 + (s - x0) * (f1 - f0) // (x1 - x0)

def sample_of_frame(fr):
    i = bisect.bisect_left(fs, fr)
    if i == 0: return xs[0]
    if i >= len(fs): return xs[-1]
    f0, f1 = fs[i-1], fs[i]
    x0, x1 = xs[i-1], xs[i]
    if f1 == f0: return x0
    return x0 + (fr - f0) * (x1 - x0) // (f1 - f0)

wav = wave.open(WORK + r"\deep_pcm_ring.wav", "rb")
n = wav.getnframes()
data = wav.readframes(n)
samples = struct.unpack("<%dh" % (n * 2), data)
WAV_START = 7045476 - n

def rel(ab): return ab - WAV_START

s_a = rel(sample_of_frame(9808))
s_b = rel(sample_of_frame(10520))
print("zone B wav slice: %d..%d (%.1f s)" % (s_a, s_b, (s_b - s_a) / RATE))

WIN = 160          # ~5 ms
HOP = 80
STEP = 4           # decode a frame every STEP samples -> step of 4 is plenty
rmses = []
i = s_a
while i < s_b:
    tot = 0.0
    peak = 0
    j1 = min(i + WIN, s_b)
    for j in range(i, j1):
        v = samples[j * 2]
        if v < 0: v = -v
        tot += v * v
        if v > peak: peak = v
    cnt = j1 - i
    rmses.append((i, math.sqrt(tot / cnt), peak))
    i += STEP

# Local-floor RMS (median over 1 s neighbors ~ 200 hops at step 4? window 250 hops)
# simpler: moving median of 1 s (step4 -> 8000 values per sec) use 8000
N = len(rmses)
floor = []
F = int(32040 / STEP)  # per second
half = F // 2
for k in range(N):
    lo = max(0, k - half)
    hi = min(N, k + half)
    vals = sorted(rmses[j][1] for j in range(lo, hi, 47))  # subsample for speed
    floor.append(vals[len(vals) // 2])
print("floors computed")

# detect onsets: rms > 4x floor AND peak high, list every window above
onsets = []
prev_above = False
for k in range(N):
    _, rms, peak = rmses[k]
    above = rms > max(4.0 * floor[k], 60.0)
    if above and not prev_above:
        onsets.append(k)
    prev_above = above

print("candidate onsets: %d" % len(onsets))
# merge onsets within 0.2 s
merged = []
for k in onsets:
    if merged and (rmses[k][0] - merged[-1][1]) < RATE * 0.2:
        merged[-1] = (merged[-1][0], max(merged[-1][1], rmses[k][0]), max(merged[-1][2], rmses[k][1]))
    else:
        merged.append((k, rmses[k][0], rmses[k][1]))
print("\nbeep-like onsets (sample, rms, frame):")
for k, s0, r0 in merged:
    # find burst end + peak
    pk = r0
    pk_s = s0
    kk = k
    while kk < N and rmses[kk][1] > max(2.0 * floor[kk], 60.0):
        if rmses[kk][1] > pk:
            pk = rmses[kk][1]
            pk_s = rmses[kk][0]
        kk += 1
    print("  start sample %d (frame ~%d) rms %.0f | peak sample %d (frame ~%d) rms %.0f | dur ~%d ms"
          % (s0, frame_of_sample(WAV_START + s0), r0, pk_s,
             frame_of_sample(WAV_START + pk_s), pk, (pk_s - s0) * 1000 // RATE))
