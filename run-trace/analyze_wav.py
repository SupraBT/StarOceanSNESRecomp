#!/usr/bin/env python3
"""Locate tone bursts (beep) in the dumped ring WAV.

Reads field_zone.wav, computes per-window dominant-frequency analysis,
and prints regions where a narrow-band tone is sustained significantly
above the local broadband floor.
"""
import wave, sys
import numpy as np

fn = sys.argv[1] if len(sys.argv) > 1 else "field_zone.wav"
w = wave.open(fn, "rb")
ch = w.getnchannels()
sw = w.getsampwidth()
sr = w.getframerate()
nf = w.getnframes()
print("channels=%d sampwidth=%d rate=%d frames=%d dur=%.2fs"
      % (ch, sw, sr, nf, nf / float(sr)))
raw = np.frombuffer(w.readframes(nf), dtype=np.int16)
w.close()
if ch == 2:
    data = raw[0::2].astype(np.float64)
else:
    data = raw.astype(np.float64)

# --- per-window spectral stats ---
win = 2048          # 64 ms @ 32 kHz
hop = 512           # 16 ms hop
n = len(data)
nw = (n - win) // hop
freqs = np.fft.rfftfreq(win, 1.0 / sr)
print("windows=%d freqres=%.1f Hz" % (nw, freqs[1]))

rows = []
for i in range(nw):
    seg = data[i * hop:i * hop + win]
    rms = np.sqrt(np.mean(seg ** 2))
    mag = np.abs(np.fft.rfft(seg * np.hanning(win)))
    peak_i = int(np.argmax(mag[10:])) + 10  # skip DC/low
    peak_db = 20 * np.log10(mag[peak_i] + 1e-9)
    total_db = 20 * np.log10(np.sqrt(np.sum(mag ** 2)) + 1e-9)
    # narrowband-ness: peak power share
    share = (mag[peak_i] ** 2) / (np.sum(mag ** 2) + 1e-9)
    rows.append((i, rms, freqs[peak_i], peak_db, total_db, share))

# Find sustained high-share narrowband peaks (beep candidates)
cand = []
for i, rms, f, pdb, tdb, share in rows:
    if share > 0.25 and pdb - tdb > -3 and f > 500:
        cand.append((i, f, share, pdb, tdb, rms))

# group consecutive
groups = []
for c in cand:
    if groups and c[0] - groups[-1][-1][0] <= 3:
        groups[-1].append(c)
    else:
        groups.append([c])
print("\n=== narrowband sustained regions (candidate beeps) ===")
for g in groups:
    if len(g) < 3:
        continue
    t0 = g[0][0] * hop / float(sr)
    t1 = (g[-1][0] * hop + win) / float(sr)
    f = np.median([x[1] for x in g])
    sh = np.median([x[2] for x in g])
    print("sample %.0f..%.0f  t %.3f..%.3fs  dur=%.0fms  freq=%.0fHz  share=%.2f"
          % (g[0][0] * hop, g[-1][0] * hop + win, t0, t1,
             (t1 - t0) * 1000, f, sh))

# absolute max spikes (click candidates): large |sample| jumps
d = np.abs(np.diff(data))
thr = np.percentile(d, 99.99)
spikes = np.where(d > thr)[0]
print("\n=== top 20 biggest sample-to-sample jumps ===")
idx = np.argsort(d[spikes])[::-1][:20]
for k in idx:
    s = spikes[k]
    print("sample %d (t=%.3fs) jump=%d" % (s, s / float(sr), d[s]))
