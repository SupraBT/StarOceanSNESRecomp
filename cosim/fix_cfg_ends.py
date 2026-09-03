#!/usr/bin/env python3
"""
fix_cfg_ends.py — Compute real function end boundaries for cfg `func` entries
whose declared `end` is suspiciously short (end <= start+8). The tier2 batch
script wrote `end:addr+4` for every discovered target, which is too short for
the AOT emitter to produce a body — those functions stay LLE (NULL dispatch
variants).

Algorithm: for each bank, collect all declared function starts. For a function
at `start`, the exclusive end can never exceed the NEXT declared start in the
bank (functions don't overlap). We disassemble from `start` walking straight
line + local branches, stopping at RTS/RTL and NOT following JMP/JML that jump
beyond the next function start (those are tail calls into other functions).

Usage: python fix_cfg_ends.py [--dry-run]
"""
import sys, os, re, glob
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "snesrecomp-tool"))
sys.path.insert(0, os.path.join(BASE, "snesrecomp-tool", "recompiler"))

from snes65816 import load_rom, decode_insn  # noqa: E402

CONFIG_DIR = os.path.join(BASE, "config")
ROM_PATH = os.path.join(BASE, "Star Ocean (Japan).sfc")

def lorom_off(bank, addr):
    if bank >= 0xC0:
        return (bank - 0xC0) * 0x8000 + (addr & 0x7FFF)
    return (bank & 0x7F) * 0x8000 + (addr & 0x7FFF)

RETURN_OPS = {0x60, 0x6B}   # RTS, RTL
COND_BRANCH = {0x10, 0x30, 0x50, 0x70, 0x90, 0xB0, 0xD0, 0xF0}
BRA = {0x80, 0x82}          # BRA, BRL
JMP_ABS = {0x4C, 0x5C, 0xDC}  # JMP abs / JML abs / JML [abs]
JMP_IND = {0x6C, 0x7C, 0xFC}  # JMP (abs) / JMP (abs,X) / JSR (abs,X) — stop
STOP_OPS = {0x00, 0x02, 0x40, 0xDB}  # BRK, COP, RTI, STP

def compute_end(rom, bank, start, next_start, max_scan=0x800):
    """Walk instructions from `start`, following straight-line + local branches.
    Never passes next_start (the next declared function in the bank).
    Returns the exclusive end (max PC + 1), at least start+2."""
    m = x = 1
    visited = set()
    worklist = [start]
    max_pc = start
    hard_limit = min(next_start, start + max_scan) if next_start else start + max_scan

    while worklist:
        pc = worklist.pop()
        if pc in visited or pc > 0xFFFF:
            continue
        visited.add(pc)
        if pc < start or pc >= hard_limit:
            continue
        off = lorom_off(bank, pc)
        if off < 0 or off >= len(rom):
            continue
        insn = decode_insn(rom, off, pc, bank, m, x)
        if insn is None:
            continue
        next_pc = pc + insn.length
        max_pc = max(max_pc, next_pc)
        op = rom[off]
        if op in RETURN_OPS or op in STOP_OPS:
            continue
        if op in JMP_ABS:
            target = insn.operand & 0xFFFF
            if next_start and target >= next_start:
                continue  # tail call into next function — boundary
            if start <= target < hard_limit:
                worklist.append(target)
            continue
        if op in JMP_IND:
            continue
        if op in BRA or op in COND_BRANCH:
            target = insn.operand & 0xFFFF
            if start <= target < hard_limit:
                worklist.append(target)
            worklist.append(next_pc)
            continue
        worklist.append(next_pc)
    return min(max_pc + 1, hard_limit)

def main():
    dry_run = "--dry-run" in sys.argv or "--run" not in sys.argv
    rom = load_rom(ROM_PATH)
    changes = 0

    # First pass: collect all starts per bank
    bank_starts = defaultdict(list)
    for cfg_path in sorted(glob.glob(os.path.join(CONFIG_DIR, "bank*.cfg"))):
        bank = None
        for line in open(cfg_path, encoding="utf-8", errors="replace"):
            m_bank = re.match(r'^\s*bank\s*=\s*0x([0-9A-Fa-f]+)', line)
            if m_bank:
                bank = int(m_bank.group(1), 16)
            m = re.match(r'^\s*func\s+\w+\s+([0-9A-Fa-f]+)\s+end:', line)
            if m and bank is not None:
                bank_starts[bank].append(int(m.group(1), 16))
    for bank in bank_starts:
        bank_starts[bank].sort()

    # Second pass: fix ends
    for cfg_path in sorted(glob.glob(os.path.join(CONFIG_DIR, "bank*.cfg"))):
        bank = None
        lines = open(cfg_path, encoding="utf-8", errors="replace").read().splitlines()
        out = []
        for line in lines:
            m_bank = re.match(r'^\s*bank\s*=\s*0x([0-9A-Fa-f]+)', line)
            if m_bank:
                bank = int(m_bank.group(1), 16)
            m = re.match(r'^(\s*func\s+\w+\s+([0-9A-Fa-f]+)\s+end:)([0-9A-Fa-f]+)(.*)$', line)
            if m and bank is not None:
                start = int(m.group(2), 16)
                end = int(m.group(3), 16)
                if end <= start + 8:
                    starts = bank_starts.get(bank, [])
                    next_start = None
                    for s in starts:
                        if s > start:
                            next_start = s
                            break
                    real_end = compute_end(rom, bank, start, next_start)
                    if real_end > end and real_end > start + 1:
                        comment = m.group(4)
                        out.append(f"{m.group(1)}{real_end:04X}{comment}")
                        changes += 1
                        print(f"  {os.path.basename(cfg_path)}: {bank:02X}:{start:04X} end {end:04X} -> {real_end:04X}")
                        continue
            out.append(line)
        if not dry_run:
            with open(cfg_path, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(out) + "\n")
    print(f"\n{'DRY-RUN: ' if dry_run else ''}{changes} function ends corrected.")
    if dry_run:
        print("Re-run with --run to apply.")

if __name__ == "__main__":
    main()
