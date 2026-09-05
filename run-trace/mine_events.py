#!/usr/bin/env python3
"""Mine deep_events.json for DSP writes around candidate pitido frames."""
import json, bisect

WORK = r"F:\StarOceanRecompRAID\run-trace"
evs = json.load(open(WORK + r"\deep_events.json"))

ports = [e for e in evs if e["t"] in ("cpu_wr", "cpu_ap", "spc_wr", "cpu_rd", "spc_rd")]
frame_sorted = sorted((e["aux"], e["s"]) for e in ports if e["t"] in ("cpu_wr", "cpu_ap"))
fs = [f for f, s in frame_sorted]
xs = [s for f, s in frame_sorted]

def sample_of_frame(fr):
    i = bisect.bisect_left(fs, fr)
    if i == 0: return xs[0]
    if i >= len(fs): return xs[-1]
    f0, f1 = fs[i-1], fs[i]
    x0, x1 = xs[i-1], xs[i]
    if f1 == f0: return x0
    return x0 + (fr - f0) * (x1 - x0) // (f1 - f0)

def frame_of_sample(s):
    i = bisect.bisect_left(xs, s)
    if i == 0: return fs[0]
    if i >= len(xs): return fs[-1]
    f0, f1 = fs[i-1], fs[i]
    x0, x1 = xs[i-1], xs[i]
    if x1 == x0: return f0
    return f0 + (s - x0) * (f1 - f0) // (x1 - x0)

REG_NAMES = {
    0x00:"VOLL0",0x01:"VOLR0",0x02:"PITL0",0x03:"PITH0",0x04:"SRCN0",0x05:"ADSR0",0x06:"ADSR1",0x07:"GAIN0",
    0x08:"VOLL1",0x09:"VOLR1",0x0a:"PITL1",0x0b:"PITH1",0x0c:"SRCN1",0x0d:"ADSR0",0x0e:"ADSR1",0x0f:"GAIN1",
    0x10:"VOLL2",0x11:"VOLR2",0x12:"PITL2",0x13:"PITH2",0x14:"SRCN2",0x15:"ADSR0",0x16:"ADSR1",0x17:"GAIN2",
    0x18:"VOLL3",0x19:"VOLR3",0x1a:"PITL3",0x1b:"PITH3",0x1c:"SRCN3",0x1d:"ADSR0",0x1e:"ADSR1",0x1f:"GAIN3",
    0x20:"VOLL4",0x21:"VOLR4",0x22:"PITL4",0x23:"PITH4",0x24:"SRCN4",0x25:"ADSR0",0x26:"ADSR1",0x27:"GAIN4",
    0x28:"VOLL5",0x29:"VOLR5",0x2a:"PITL5",0x2b:"PITH5",0x2c:"SRCN5",0x2d:"ADSR0",0x2e:"ADSR1",0x2f:"GAIN5",
    0x30:"VOLL6",0x31:"VOLR6",0x32:"PITL6",0x33:"PITH6",0x34:"SRCN6",0x35:"ADSR0",0x36:"ADSR1",0x37:"GAIN6",
    0x38:"VOLL7",0x39:"VOLR7",0x3a:"PITL7",0x3b:"PITH7",0x3c:"SRCN7",0x3d:"ADSR0",0x3e:"ADSR1",0x3f:"GAIN7",
    0x4c:"KON",0x5c:"KOF",0x6c:"FLG",0x7c:"ENDX",0x0c:"MVOL_L",0x1c:"MVOL_R",
    0x2c:"EVOL_L",0x3c:"EVOL_R",0x4d:"EON",0x5d:"DIR",0x6d:"ESA",0x7d:"EDL",0x0d:"EFB",0x2d:"PMON",0x3d:"NON",
}

regs = [e for e in evs if e["t"] == "reg"]
for e in regs:
    e["adr"] = int(str(e["adr"]), 16)
    e["val"] = int(str(e["val"]), 16)
for e in evs:
    if e["t"] != "reg":
        e["adr"] = int(str(e["adr"]), 16)
        e["val"] = int(str(e["val"]), 16)
print("reg events:", len(regs))

def dump_window(fr_lo, fr_hi, label):
    s_lo, s_hi = sample_of_frame(fr_lo), sample_of_frame(fr_hi)
    print("\n=== %s (frames %d..%d, samples %d..%d) ===" % (label, fr_lo, fr_hi, s_lo, s_hi))
    sel = [e for e in regs if s_lo <= e["s"] <= s_hi]
    print("reg writes in window:", len(sel))
    # KON/KOF and voice volume/gain writes, with frame of each
    interesting = [e for e in sel if e["adr"] in (0x4c, 0x5c) or (e["adr"] & 0x07) in (0x00,0x01,0x05,0x06,0x07) or e["adr"] in (0x0c,0x1c)]
    for e in interesting:
        fr = frame_of_sample(e["s"])
        name = REG_NAMES.get(e["adr"], "r%02x" % e["adr"])
        print("  fr %5d  s %9d  %s[0x%02x] = 0x%02x" % (fr, e["s"], name, e["adr"], e["val"]))

# Zone per user: f9808..f10520. Pitido reported ~f10134-10157 in earlier run;
# in THIS run look at the widest candidate windows.
dump_window(10050, 10200, "candidate window 1")
dump_window(10400, 10520, "candidate window 2")
