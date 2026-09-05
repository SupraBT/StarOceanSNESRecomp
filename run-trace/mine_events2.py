#!/usr/bin/env python3
"""Compressed summary of DSP activity across zone B (f9808..f10520)."""
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

regs = [e for e in evs if e["t"] == "reg"]

# scope: samples corresponding to frames 9808..10520 via port frame anchor
def sample_of_frame(fr):
    i = bisect.bisect_left(fs, fr)
    if i == 0: return xs[0]
    if i >= len(fs): return xs[-1]
    f0, f1 = fs[i-1], fs[i]
    x0, x1 = xs[i-1], xs[i]
    if f1 == f0: return x0
    return x0 + (fr - f0) * (x1 - x0) // (f1 - f0)

s0, s1 = sample_of_frame(9808), sample_of_frame(10520)
zone = [e for e in regs if s0 <= e["s"] <= s1]
print("zone reg writes:", len(zone))

# nonzero KON / KOF events
kon = [e for e in zone if e["adr"] == 0x4c and e["val"] != 0]
kof = [e for e in zone if e["adr"] == 0x5c and e["val"] != 0]
print("nonzero KON writes:", len(kon))
for e in kon[:40]:
    print("  fr %5d KON=0x%02x" % (frame_of_sample(e["s"]), e["val"]))
print("nonzero KOF writes:", len(kof))
for e in kof[:20]:
    print("  fr %5d KOF=0x%02x" % (frame_of_sample(e["s"]), e["val"]))

# volume/gain/adsr writes per voice register that changed, grouped by ~frame
print("\nper-voice volume/gain writes (frame, adr, val):")
VREG = {0x00: "VOLL", 0x01: "VOLR", 0x05: "A0", 0x06: "A1", 0x07: "GAIN"}
for e in zone:
    off = e["adr"] & 0x0f
    if off in VREG and e["adr"] < 0x40:
        v = e["val"]
        print("  fr %5d  v%d %s = 0x%02x" % (frame_of_sample(e["s"]), e["adr"] >> 4, VREG[off], v))
