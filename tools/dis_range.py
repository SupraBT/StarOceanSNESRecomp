#!/usr/bin/env python3
"""Linear 65816 disassembler over a HiROM address range.

Usage: python tools/dis_range.py BANK:START BANK2:END [--m 1 --x 0]

Uses the recompiler decoder (snes65816) so the mnemonic/mode rendering matches
the AOT build.  M/X flag widths are held constant across the walk (callers must
pass the width in force at the entry point).
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "snesrecomp", "recompiler"))

import snes65816 as s  # noqa: E402

ROM = os.path.join(ROOT, "Star Ocean (Japan).sfc")


def parse(spec):
    b, a = spec.split(":")
    return int(b, 16), int(a, 16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("start")
    ap.add_argument("end")
    ap.add_argument("--m", type=int, default=1)
    ap.add_argument("--x", type=int, default=1)
    ap.add_argument("--no-track", action="store_true",
                    help="keep M/X fixed instead of following REP/SEP")
    args = ap.parse_args()

    sb, sa = parse(args.start)
    eb, ea = parse(args.end)

    data = open(ROM, "rb").read()
    s.set_rom_mapping("hirom")
    if s.detect_rom_mapping(data) != "hirom":
        pass

    m, x = args.m, args.x
    bank, pc = sb, sa
    while (bank, pc) <= (eb, ea):
        off = s.rom_offset(bank, pc)
        if off is None or off < 0:
            print(f"${bank:02X}:{pc:04X}  <no rom mapping>")
            pc += 1
            continue
        insn = s.decode_insn(data, off, pc, bank, m, x)
        if insn is None:
            print(f"${bank:02X}:{pc:04X}  db ${data[off]:02X}   ; ???")
            pc += 1
            continue
        raw = data[off:off + insn.length].hex(" ").upper()
        print(f"${bank:02X}:{pc:04X}  {raw:<11} {insn.mnem:<5} {insn._fmt()}"
              f"        ; M={m} X={x}")
        if not args.no_track and insn.mnem in ("SEP", "REP"):
            v = insn.operand
            if v & 0x20: m = 1 if insn.mnem == "SEP" else 0
            if v & 0x10: x = 1 if insn.mnem == "SEP" else 0
        pc += insn.length


if __name__ == "__main__":
    main()
