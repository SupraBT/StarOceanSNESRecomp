import re

# ── Runner values (captured via reg-trace at the Mode 0 transition) ──
runner = {
    "2105": "00", "2107": "48", "2108": "4c", "2109": "50", "210a": "58",
    "210b": "22", "210c": "42", "212c": "1f", "212e": "1f", "212d": "00",
    "212f": "00", "2130": "20", "2131": "60", "2132": "e0",
}

# ── Extract bsnes values: first write of each reg AFTER the Mode 0 write ──
path = r'E:\Recompilador Super Nintendo\Star Ocean (Japan)-trace.log'
targets = set(runner.keys())
bsnes = {}
mode0_line = None
with open(path, 'rb') as f:
    for i, line in enumerate(f):
        m = re.search(rb'([0-9a-f]{6}) sta \$2105\s+\[002105\] A:([0-9a-f]{4})', line)
        if m and m.group(2) == b'0000':
            mode0_line = i
            break
if mode0_line is None:
    print("Mode 0 write not found")
    raise SystemExit(1)
print("bsnes Mode 0 write at line %d" % mode0_line)

with open(path, 'rb') as f:
    for i, line in enumerate(f):
        if i < mode0_line:
            continue
        if i > mode0_line + 30000:
            break
        m = re.search(rb'([0-9a-f]{6}) (?:sta|stz)\s*\$([0-9a-f]{4})\s+\[[0-9a-f]{6}\] A:([0-9a-f]{4})', line)
        if not m:
            continue
        reg = m.group(2).decode().lower()
        if reg in targets and reg not in bsnes:
            bsnes[reg] = m.group(3).decode()
        if set(bsnes.keys()) == targets:
            break

print("\n%-6s %-8s %-8s %s" % ("reg", "bsnes", "runner", "match"))
for reg in sorted(targets, key=lambda r: int(r, 16)):
    b = bsnes.get(reg, "?")
    r = runner[reg]
    match = "OK" if (b and b[-2:] == r) else "DIFF"
    print("%-6s %-8s %-8s %s" % (reg, b, r, match))
