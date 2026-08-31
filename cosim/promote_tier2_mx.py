#!/usr/bin/env python3
"""Promote tier-2 LLE gaps to AOT by pinning the runtime-observed entry M/X.

The static analyzer seeds cfg `func` entries with the SNES reset width
(M=1, X=1).  Star Ocean calls many of those functions with other widths
(e.g. M1X0 / M0X0), so the emitted M1X1 variant never matches dispatch and
the interpreter keeps owning the hot loop.  The tier-2 coverage manifest
records the ACTUAL entry width per (target, mx) — ground truth from the
replay.  For every discovery whose current dispatch variant slot is NULL,
add an `entry_mx_at <pc16> <M> <X>` directive to the owning bank cfg so a
regeneration emits the correct AOT body.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TIER2 = sys.argv[1] if len(sys.argv) > 1 else \
    r"build/Release/tier2_so_20260826_000240_000.json"
DISPATCH = Path("generated/dispatch_v2.c")
CFG_DIR = Path("config")
MIN_HITS = int(sys.argv[2]) if len(sys.argv) > 2 else 30

# ---- parse tier2 manifest (lenient: the file has one raw entry that breaks
# strict json; the discovery objects themselves are well-formed) ----
txt = Path(TIER2).read_text(encoding="utf-8", errors="replace")
objs = re.findall(
    r'\{"site_pc24":\s*"([^"]+)",\s*"target_pc24":\s*"([^"]+)",\s*'
    r'"entry_mx":\s*"([^"]+)",\s*"site_kind":\s*"([^"]+)",\s*'
    r'"clean_hits":\s*(\d+),\s*"bail_hits":\s*(\d+)', txt)
print(f"tier2 discoveries parsed: {len(objs)}")

# aggregate hits per (target, mx)
hits = defaultdict(int)
for site, tgt, mx, kind, ch, bh in objs:
    hits[(int(tgt, 16), mx)] += int(ch)

# ---- parse current dispatch variants per pc24 ----
# rows look like:
#   { 0x00F000u, { NULL, NULL, bank_00_F000_M1X0, bank_00_F000_M1X1 }, 0 },
dispatch = {}
for m in re.finditer(
        r"\{ 0x([0-9A-Fa-f]+)u, \{ ([^}]*)\} \},", DISPATCH.read_text()):
    pc = int(m.group(1), 16)
    slots = [s.strip() for s in m.group(2).split(",")]
    # slots: M0X0, M0X1, M1X0, M1X1
    dispatch[pc] = slots

MX_IDX = {"M0X0": 0, "M0X1": 1, "M1X0": 2, "M1X1": 3}

# ---- collect missing variants ----
missing = defaultdict(list)  # bank -> list of (pc16, m, x, hits)
for (tgt, mx), n in sorted(hits.items(), key=lambda kv: -kv[1]):
    if n < MIN_HITS:
        continue
    bank = (tgt >> 16) & 0xFF
    slots = dispatch.get(tgt)
    idx = MX_IDX.get(mx)
    if idx is None:
        continue
    has_body = slots is not None and idx < len(slots) and slots[idx] != "NULL"
    if not has_body:
        m_val, x_val = int(mx[1]), int(mx[3])
        missing[bank].append((tgt & 0xFFFF, m_val, x_val, n))

total_added = 0
for bank in sorted(missing):
    path = CFG_DIR / f"bank{bank:02X}.cfg"
    if not path.exists():
        print(f"  WARN: {path} missing, skipping")
        continue
    lines = path.read_text(encoding="utf-8").rstrip().splitlines()
    lines.append("")
    lines.append("# --- tier2 runtime entry-mx pins (auto-generated) ---")
    for pc16, m_val, x_val, n in missing[bank]:
        lines.append(f"entry_mx_at {pc16:04X} {m_val} {x_val}  # tier2 hits={n}")
        total_added += 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  bank{bank:02X}.cfg: {len(missing[bank])} entry_mx_at added")

print(f"\nTOTAL entry_mx_at directives added: {total_added}")
