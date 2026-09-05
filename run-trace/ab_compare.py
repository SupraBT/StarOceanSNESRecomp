#!/usr/bin/env python3
"""Compare two A/B captures: per-frame DSP reg writes + port traffic in zone B."""
import json, bisect

WORK = r"F:\StarOceanRecompRAID\run-trace"

def load(tag):
    d = json.load(open(WORK + r"\%s_events.json" % tag))
    evs = d["events"]
    for e in evs:
        e["adr"] = int(str(e["adr"]), 16)
        e["val"] = int(str(e["val"]), 16)
    return d["freeze_frame"], evs

def build(tag):
    ff, evs = load(tag)
    ports = sorted((e["aux"], e["s"]) for e in evs if e["t"] in ("cpu_wr", "cpu_ap"))
    fs = [p[0] for p in ports]
    xs = [p[1] for p in ports]
    def frame_of_sample(s):
        i = bisect.bisect_left(xs, s)
        if i == 0: return fs[0]
        if i >= len(fs): return fs[-1]
        f0, f1 = fs[i-1], fs[i]
        x0, x1 = xs[i-1], xs[i]
        if x1 == x0: return f0
        return f0 + (s - x0) * (f1 - f0) // (x1 - x0)
    regs = {}
    portseq = {}
    for e in evs:
        if e["t"] == "reg":
            fr = frame_of_sample(e["s"])
            regs.setdefault(fr, []).append((e["s"], e["adr"], e["val"]))
        elif e["t"] in ("cpu_wr", "cpu_ap"):
            portseq.setdefault(e["aux"], []).append((e["s"], e["t"], e.get("p", 0)))
    return ff, regs, portseq, (min(fs), max(fs))

f1, r1, p1, rng1 = build("ab1")
f2, r2, p2, rng2 = build("ab2")
print("ab1 freeze=%d anchor range=%s | ab2 freeze=%d anchor range=%s" % (f1, rng1, f2, rng2))

lo, hi = 9808, 10520
tot = eq = 0
diffframes = []
for fr in range(lo, hi + 1):
    a = r1.get(fr, [])
    b = r2.get(fr, [])
    # compare sequence of (adr, val) only (ignore sample timing for the write test)
    ka = [(adr, val) for _, adr, val in a]
    kb = [(adr, val) for _, adr, val in b]
    if ka == kb:
        eq += 1
    else:
        diffframes.append(fr)
    tot += 1
print("reg-write frames equal: %d/%d ; differing frames: %d" % (eq, tot, len(diffframes)))
print("first 15 differing frames:", diffframes[:15])
for fr in diffframes[:4]:
    a = [(adr, val) for _, adr, val in r1.get(fr, [])]
    b = [(adr, val) for _, adr, val in r2.get(fr, [])]
    print(" f%d:" % fr)
    print("   ab1: %s" % a)
    print("   ab2: %s" % b)

# port traffic comparison per frame (counts + last value per port)
peq = pdiff = 0
pfirst = None
for fr in range(lo, hi + 1):
    a = p1.get(fr, [])
    b = p2.get(fr, [])
    ka = [(t, p) for _, t, p in a]
    kb = [(t, p) for _, t, p in b]
    if ka == kb:
        peq += 1
    else:
        pdiff += 1
        if pfirst is None: pfirst = fr
print("port frames equal: %d/%d ; first differing frame: %s" % (peq, tot, pfirst))
if pfirst:
    fr = pfirst
    print(" f%d ab1 port seq (%d): %s" % (fr, len(p1[fr]), [(t, p) for _, t, p in p1[fr]][:40]))
    print(" f%d ab2 port seq (%d): %s" % (fr, len(p2[fr]), [(t, p) for _, t, p in p2[fr]][:40]))
