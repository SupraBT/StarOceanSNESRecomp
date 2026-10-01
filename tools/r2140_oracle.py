#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compara el flujo de LECTURAS de $2140 entre hardware (Mesen) y el motor.

Por que existe
--------------
El invitado en $C0:859E hace

    LDA $2140
    CMP $2140
    BNE $859D        ; repetir si las dos lecturas NO coinciden

Es el handshake de "el SPC ya consumio lo que le mande". En hardware sale a la
primera; en el motor no converge nunca y el invitado se queda 15-25 ms por
fotograma interpretando cuatro instrucciones.

Este script contrasta los dos lados con la MISMA pregunta, que es la que decide
la semantica del registro:

  1. Cuantas veces lee el invitado $2140 en el spin $C0859D-$C085D0.
  2. Cuantas lecturas consecutivas devuelven el MISMO valor.
  3. En que PCs lee, y coinciden los dos lados.

La respuesta a (2) es la que manda: si el hardware repite el valor, $2140 es un
pestillo que solo cambia al escribir, y leerlo dos veces sin escribir entre
medias tiene que devolver lo mismo SIEMPRE.

Uso
---
    python tools/r2140_oracle.py                       # pide fichero
    python tools/r2140_oracle.py docs/traces/hw_r2140.tsv
    python tools/r2140_oracle.py docs/traces/hw_r2140.tsv motor_r2140.tsv
"""
from __future__ import annotations

import collections
import pathlib
import sys

SPIN_LO, SPIN_HI = 0xC0859D, 0xC085D0


def parse(path):
    """Devuelve (lecturas, por_frame, por_pc, en_spin_por_frame, repeticiones)."""
    lectures = []
    por_pc = collections.Counter()
    por_frame = collections.Counter()
    spin_frame = collections.Counter()
    iguales = distintos = 0
    prev = None
    with pathlib.Path(path).open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            c = line.rstrip("\n").split("\t")
            if len(c) < 5:
                continue
            try:
                fr = int(c[0])
                val = int(c[3], 16)
                pc = int(c[4], 16)
            except ValueError:
                continue
            addr = int(c[2], 16) if len(c[2]) == 4 else 0
            lectures.append((fr, addr, val, pc))
            por_pc[pc] += 1
            por_frame[fr] += 1
            if SPIN_LO <= pc <= SPIN_HI:
                spin_frame[fr] += 1
            if val == prev:
                iguales += 1
            else:
                distintos += 1
            prev = val
    total = iguales + distintos
    return lectures, por_frame, por_pc, spin_frame, (iguales, distintos, total)


def informe(nombre, path, filas=14):
    lectures, por_frame, por_pc, spin, (iguales, distintos, total) = parse(path)
    print("=== %s: %s" % (nombre, path))
    print("    lecturas=%d  frames con lectura=%d" % (len(lectures), len(por_frame)))
    pct = 100.0 * iguales / total if total else 0.0
    print("    lectura que REPITE el valor anterior: %d/%d = %.1f%%" % (iguales, total, pct))
    print("    lecturas dentro del spin $%06X-$%06X: %d" % (SPIN_LO, SPIN_HI, sum(spin.values())))
    if spin:
        top = ", ".join("f%d=%d" % (f, n) for f, n in sorted(spin.items())[:8])
        print("      en frames: %s" % top)
    print("    PCs que mas leen:")
    for pc, n in por_pc.most_common(6):
        print("      $%06X  %d" % (pc, n))
    print("    primeras %d lecturas:" % filas)
    for fr, addr, val, pc in lectures[:filas]:
        marca = " <-- SPIN" if SPIN_LO <= pc <= SPIN_HI else ""
        print("      f%-6d $%04X=$%02X  pc=$%06X%s" % (fr, addr, val, pc, marca))
    print()
    return spin, por_pc


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print(__doc__)
        return 2
    hw = args[0]
    if len(args) < 2:
        informe("HARDWARE", hw)
        print("Solo hardware. Para contrastar:")
        print("  python tools/r2140_oracle.py <hw.tsv> <motor.tsv>")
        return 0
    motor = args[1]
    spin_hw, pc_hw = informe("HARDWARE", hw)
    spin_mo, pc_mo = informe("MOTOR", motor)

    print("=== VEREDICTO")
    tot_hw, tot_mo = sum(spin_hw.values()), sum(spin_mo.values())
    print("    lecturas en el spin: hardware=%d  motor=%d" % (tot_hw, tot_mo))
    if tot_hw == 0 and tot_mo > 1000:
        print("    DIVERGE: el motor entra en un bucle que en hardware no se")
        print("    ejecuta nunca. Ahi esta el bajon de frames del arranque.")
    only_mo = ["$%06X" % pc for pc in pc_mo.most_common(8) if pc not in pc_hw]
    if only_mo:
        print("    PCs que SOLO lee el motor: %s" % ", ".join(only_mo))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
