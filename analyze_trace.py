import re
from collections import Counter

with open('E:/Recompilador Super Nintendo/Star Ocean (Japan)-trace.log', 'r', errors='ignore') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Find Mode 0 transition
mode0_line = None
for i, line in enumerate(lines):
    if '$2105' in line and 'A:0000' in line and i > 400000:
        mode0_line = i
        print(f"Mode 0 (BGMODE=$00) at line {i}: {line.rstrip()[:130]}")
        break

if not mode0_line:
    print("Mode 0 not found")
    exit()

# Look for all register writes after Mode 0, grouped by type
print(f"\n=== Register writes from line {mode0_line} to {mode0_line + 5000} ===")
c = Counter()
for i in range(mode0_line, min(len(lines), mode0_line + 5000)):
    line = lines[i]
    m = re.search(r'sta \$([0-9a-fA-F]{4})', line)
    if m:
        reg = m.group(1).lower()
        c[reg] += 1

# Show most common
for reg, count in c.most_common(40):
    print(f"  ${reg}: {count}")

# Find CGRAM-related writes (2121, 2122) in the FULL range after Mode 0
print(f"\n=== CGRAM writes ($2121/$2122) from line {mode0_line} to end ===")
for i in range(mode0_line, min(len(lines), len(lines))):
    line = lines[i]
    if '$2121' in line or '$2122' in line:
        print(f"  L{i}: {line.rstrip()[:130]}")
        if i > mode0_line + 50000:
            break

# Find HDMAEN writes
print(f"\n=== HDMAEN ($420C) writes from line {mode0_line} to end ===")
for i in range(mode0_line, min(len(lines), len(lines))):
    line = lines[i]
    if '$420c' in line.lower():
        print(f"  L{i}: {line.rstrip()[:130]}")
        if i > mode0_line + 5000:
            break
