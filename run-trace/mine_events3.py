#!/usr/bin/env python3
"""Unfiltered DSP write stream for the pitido window (f10080..f10200) + KON windows."""
import json, bisect

WORK = r"F:\StarOceanRecompRAID\run-trace"
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

regs = [e for e in evs if e["t"] == "reg"]

def dump(fr_lo, fr_hi, label):
    s0, s1 = sample_of_frame(fr_lo), sample_of_frame(fr_hi)
    sel = [e for e in regs if s0 <= e["s"] <= s1]
    print("=== %s f%d..f%d (%d writes) ===" % (label, fr_lo, fr_hi, len(sel)))
    prev = None
    for e in sel:
        line = "  fr %5d s %9d  0x%02x <- 0x%02x" % (frame_of_sample(e["s"]), e["s"], e["adr"], e["val"])
        print(line)

dump(10080, 10100, "pre-pitido")
dump(10100, 10140, "pitido start")
dump(10140, 10180, "pitido end")
dump(10270, 10300, "KON 0x40 zone")
