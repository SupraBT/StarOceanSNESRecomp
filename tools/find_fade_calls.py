#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Localiza todos los sitios que llaman a la biblioteca de fundidos C8:F4xx.

Uso: python tools/find_fade_calls.py [min][max]
Imprime, por cada JSR/JSL a C8:F4xx, la direccion ROM, el destino y un
desensamblado corto hacia atras (para ver la bifurcacion que elige rutina).
"""
import os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "snesrecomp", "recompiler"))
import snes65816 as s  # noqa: E402

ROM = os.path.join(ROOT, "Star Ocean (Japan).sfc")
TARGET_LO = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0xF400
TARGET_HI = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0xF540

data = open(ROM, "rb").read()


def off_to_bankaddr(off):
    """HiROM: los bancos $C0-$FF cubren los primeros 4 MB (64 KB por banco)."""
    if off < 0x400000:
        return 0xC0 + (off >> 16), off & 0xFFFF
    return None, None


hits = collections.defaultdict(list)
for off in range(len(data) - 3):
    if data[off] != 0x20:
        continue
    lo, hi = data[off + 1], data[off + 2]
    if hi != 0xF4:
        continue
    tgt = 0xF400 | lo
    if not (TARGET_LO <= tgt <= TARGET_HI):
        continue
    bank, addr = off_to_bankaddr(off)
    if bank is None:
        continue
    hits[tgt].append((off, bank, addr))

print("destino  llamadas  sitios (banco:addr)")
for tgt in sorted(hits):
    print("  C8:%04X  %d" % (tgt, len(hits[tgt])))
print()

for tgt in sorted(hits):
    print("=== C8:%04X ===" % tgt)
    for off, bank, addr in hits[tgt][:12]:
        print("  llamada en %02X:%04X (rom %06X)" % (bank, addr, off))
    print()
