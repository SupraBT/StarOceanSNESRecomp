#!/usr/bin/env python3
"""Compare menu-setup register write TIMING (V scanline) between the runner
(regtrace.json) and the bsnes-plus reference trace.

Usage: python compare_timing_vh.py [regtrace.json]

Prints, for each key PPU register, the V scanline at which the runner and
bsnes write it. The runner's H differs (~600 dots) because it executes the
setup in a burst after the quiescent yield, but the V scanline must match
(both write in vblank / the same line) for the visible frame to be correct.
"""

import json
import os
import re
import sys

BASE = r"E:\Recompilador Super Nintendo"
TRACE = os.path.join(BASE, "Star Ocean (Japan)-trace.log")
RTRACE = (sys.argv[1] if len(sys.argv) > 1 else
          os.path.join(BASE, "StarOceanTest2", "build-trace", "regtrace.json"))

# reg -> (bsnes $21XX reg, value to look for in bsnes A register, runner adr)
REGS = [
    ("BGMODE",     "2105", "0000", "0x2105"),
    ("BG1 map",    "2107", "0048", "0x2107"),
    ("BG2 map",    "2108", "004c", "0x2108"),
    ("BG3 map",    "2109", "0050", "0x2109"),
    ("BG4 map",    "210a", "0058", "0x210a"),
    ("BG1 tiles",  "210b", "0022", "0x210b"),
    ("BG2 tiles",  "210c", "0042", "0x210c"),
    ("window1",    "212c", "001f", "0x212c"),
    ("window2",    "212e", "001f", "0x212e"),
    ("window3",    "212d", "0000", "0x212d"),
    ("window4",    "212f", "0000", "0x212f"),
    ("col math",   "2130", "0020", "0x2130"),
    ("cgadsub",    "2131", "0060", "0x2131"),
    ("fixedColor", "2132", "00e0", "0x2132"),
]


def bsnes_vh(reg, val, is_mode0=False):
    """Return (V, H) of the first sta $21{reg} with A:{val} after the Mode 0
    BGMODE write (A:0000 to $2105) — i.e. the menu-setup burst. For BGMODE
    itself (is_mode0), return the trigger write."""
    pat = re.compile(r"sta \$%s\s+\[00[0-9a-f]+\] A:%s " % (reg, val))
    vhpat = re.compile(r"V:(\d+) H:\s*(\d+)")
    mode0 = False
    with open(TRACE, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not mode0:
                m = re.search(r"sta \$2105\s+\[002105\] A:0000", line)
                if m:
                    mode0 = True
                    if is_mode0:
                        vh = vhpat.search(line)
                        if vh:
                            return (int(vh.group(1)), int(vh.group(2)))
                continue
            m = pat.search(line)
            if m:
                vh = vhpat.search(line)
                if vh:
                    return (int(vh.group(1)), int(vh.group(2)))
    return None


def main():
    data = json.load(open(RTRACE))
    log = data["log"]
    runner = {}
    for e in log:
        runner.setdefault(e["adr"], []).append(e)
    print("%-12s %-22s %-22s  %s" % ("reg", "bsnes (V,H)", "runner (V,H)", "V match"))
    print("-" * 78)
    all_ok = True
    for name, reg, val, radr in REGS:
        b = bsnes_vh(reg, val, is_mode0=(name == "BGMODE"))
        r_entries = runner.get(radr, [])
        # runner: the write inside the menu-setup frame (the last occurrence
        # at V >= 200 — vblank burst)
        rv = rh = None
        for e in r_entries:
            if e.get("V", 0) >= 200:
                rv, rh = e.get("V"), e.get("H")
        ok = (b is not None and rv is not None and b[0] == rv)
        if not ok:
            all_ok = False
        bs = "%d,%d" % b if b else "?"
        rs = "%d,%d" % (rv, rh) if rv is not None else "?"
        print("%-12s %-22s %-22s  %s" % (name, bs, rs, "OK" if ok else "DIFF"))
    print("-" * 78)
    print("V scanline match (menu setup): %s" % ("ALL OK" if all_ok else "DIFFERENCES"))
    if all_ok:
        print("-> runner writes the menu PPU setup on the SAME scanlines as bsnes")
    else:
        print("-> investigate the DIFF rows")


if __name__ == "__main__":
    main()
