#!/usr/bin/env python3
"""List all writes to $2100-$2133 in the bsnes trace between the mode-0
setup (L403092) and the end of the trace, with V/H/F and unique values."""
import re

path = r"E:\Recompilador Super Nintendo\Star Ocean (Japan)-trace.log"
pat = re.compile(r"sta \$21([0-3][0-9a-f])\s+\[0021[0-3][0-9a-f]\] A:([0-9a-f]{4})")
vhf = re.compile(r"V:(\d+)\s+H:\s*(\d+)\s+F:\s*(\d+)")

from collections import Counter
uniq = Counter()
detail = []
with open(path, "r", encoding="utf-8", errors="replace") as f:
    for i, line in enumerate(f):
        if i < 403100:
            continue
        m = pat.search(line)
        if m:
            reg = "21" + m.group(1)
            val = m.group(3)
            v = vhf.search(line)
            uniq[(reg, val)] += 1
            if len(detail) < 120:
                detail.append((i, reg, val, v.groups() if v else None))

print("=== unique (reg=val): count ===")
for (reg, val), c in sorted(uniq.items()):
    print("  $%s=$%s x%d" % (reg, val, c))
print("\n=== first 120 writes after mode-0 setup ===")
for i, reg, val, v in detail:
    vtxt = "V=%s H=%s F=%s" % v if v else "?"
    print("L%7d $%s=$%s %s" % (i, reg, val, vtxt))
