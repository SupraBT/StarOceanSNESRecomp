#!/usr/bin/env python3
"""Find writes to $210A (BG4SC) and $210C (BG34NBA) in the bsnes trace,
especially around the name screen (mode 0) entry. F: is modulo 60."""
import re

path = r"E:\Recompilador Super Nintendo\Star Ocean (Japan)-trace.log"

# Track: find the mode-0 BGMODE write first, then list SC/NBA writes after it.
# Also list ALL BG4SC writes with their V/F position.
pat_2105 = re.compile(r"sta \$2105\s+\[002105\] A:([0-9a-f]{4})")
pat_sc = re.compile(r"sta \$(2107|2108|2109|210a)\s+\[00(2107|2108|2109|210a)\] A:([0-9a-f]{4})")
pat_nba = re.compile(r"sta \$(210b|210c)\s+\[00(210b|210c)\] A:([0-9a-f]{4})")
vhf = re.compile(r"V:(\d+)\s+H:\s*(\d+)\s+F:\s*(\d+)")

mode0_line = None
mode0_seen = False
after = []

with open(path, "r", encoding="utf-8", errors="replace") as f:
    for i, line in enumerate(f):
        if i < 400000:
            # still scanning for the mode-0 write
            m = pat_2105.search(line)
            if m and m.group(1) == "0000":
                mode0_line = (i, line.strip())
                mode0_seen = True
                continue
        if mode0_seen:
            m = pat_sc.search(line)
            n = pat_nba.search(line)
            if m or n:
                v = vhf.search(line)
                vtxt = v.groups() if v else ("?", "?", "?")
                after.append((i, (m or n).group(1), (m or n).group(3), vtxt, line.strip()[:100]))
            if len(after) > 60:
                break
        if i > 600000:
            break

if mode0_line:
    print("MODE0 BGMODE write at line %d: %s" % (mode0_line[0], mode0_line[1][:120]))
else:
    print("mode0 write not found before line 400000")
print("\n=== SC/NBA writes after mode 0 ===")
for i, reg, val, v, txt in after:
    print("L%6d reg=$%s val=$%s V=%s H=%s F=%s | %s" % (i, reg, val, v[0], v[1], v[2], txt))
