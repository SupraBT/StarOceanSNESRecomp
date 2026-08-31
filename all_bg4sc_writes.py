#!/usr/bin/env python3
"""List ALL writes to $210A (BG4SC) and $210C (BG34NBA) in the bsnes trace
with their position, plus every distinct value written (with context)."""
import re

path = r"E:\Recompilador Super Nintendo\Star Ocean (Japan)-trace.log"

pat = re.compile(r"sta \$(210a|210c)\s+\[00(210a|210c)\] A:([0-9a-f]{4})")
vhf = re.compile(r"V:(\d+)\s+H:\s*(\d+)\s+F:\s*(\d+)")

writes = []
distinct = set()
with open(path, "r", encoding="utf-8", errors="replace") as f:
    for i, line in enumerate(f):
        m = pat.search(line)
        if m:
            v = vhf.search(line)
            writes.append((i, m.group(1), m.group(3), v.groups() if v else None))
            distinct.add(m.group(1) + "=" + m.group(3))
            if len(writes) > 200:
                break

print("distinct (reg=val):", sorted(distinct))
print("total writes listed:", len(writes))
print("\n=== all writes ===")
for i, reg, val, v in writes:
    vtxt = "V=%s H=%s F=%s" % v if v else "?"
    print("L%7d reg=$%s val=$%s %s" % (i, reg, val, vtxt))
