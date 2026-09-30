#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compara el registro del DSP de hardware con el del motor.

La traza de Mesen trae una linea por cada escritura del SPC al DSP con su
registro y su valor, asi que se puede RECONSTRUIR el estado final del registro
del DSP en cualquier fotograma y compararlo con el del motor. Es el unico
orculo completo que hay del lado del audio: dice registro a registro que
configuracion espera el hardware.

Uso:
    python tools/dsp_regs_hardware.py --events <events.tsv> --frames 1,120,400
    python tools/dsp_regs_hardware.py --events <events.tsv> --motor <traza del motor>
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import re

REG_RE = re.compile(r"reg=([0-9A-Fa-f]+)")


def hardware(hasta_frame: int, events: pathlib.Path):
    """Ultimo valor de cada registro del DSP escrito hasta ese fotograma.

    Columnas del fichero de eventos (separadas por TAB):
      0 fr   1 master   2 src   3 kind   4 addr   5 VALOR   6 nota
    El SPC escribe primero la direccion en $F2 (evento `sdsp_addr`, con el
    valor en la columna 5) y luego el dato en $F3 (`sdsp_data`), cuyo registro
    es el ultimo latch de direccion.  La nota de `sdsp_data` lo repite como
    `reg=XX`, que es lo que se usa aqui para no depender del latch.
    """
    reg: dict[int, int] = {}
    for line in events.open(encoding="utf-8", errors="replace"):
        if line.startswith("#"):
            continue
        f = line.rstrip("\n").split("\t")
        if len(f) < 6:
            continue
        try:
            fr = int(f[0])
        except ValueError:
            continue
        if fr > hasta_frame:
            break
        if f[3] != "sdsp_data":
            continue
        nota = f[6] if len(f) > 6 else ""
        m = REG_RE.search(nota)
        if not m:
            continue
        try:
            reg[int(m.group(1), 16)] = int(f[5], 16)
        except ValueError:
            continue
    return reg


def motor(hasta_frame: int, traza: pathlib.Path):
    """Ultimo valor de cada registro del DSP segun la traza del motor."""
    reg: dict[int, int] = {}
    pat = re.compile(
        r'\{"f":(\d+),"adr":"0x([0-9a-fA-F]+)","old":"0x[0-9a-fA-F]+",'
        r'"val":"0x([0-9a-fA-F]+)"\}')
    for m in pat.finditer(traza.read_text(encoding="utf-8", errors="replace")):
        if int(m.group(1)) > hasta_frame:
            continue
        reg[int(m.group(2), 16)] = int(m.group(3), 16)
    return reg


def vol_por_canal(reg: dict[int, int]) -> dict:
    """Mapa del DSP: cada canal ocupa 16 bytes, base = canal*16.
    +0 pitch L, +1 pitch H, +2 volumen L, +3 volumen R, +4.. ADSR.
    El canal 0 esta en $00-$0F, el 1 en $10-$1F, etc.  Escribir $20+n seria
    el canal 2, no el 0: asi se confundieron los volumenes una vez."""
    out = {}
    for ch in range(8):
        base = ch * 16
        out[f"ch{ch}"] = (reg.get(base + 2), reg.get(base + 3))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", required=True)
    ap.add_argument("--motor", default="")
    ap.add_argument("--frames", default="400")
    args = ap.parse_args()

    ev = pathlib.Path(args.events)
    mot = pathlib.Path(args.motor) if args.motor else None
    for fr in [int(x) for x in args.frames.split(",")]:
        h = hardware(fr, ev)
        print(f"\n=== frame {fr}: HARDWARE ({len(h)} registros escritos) ===")
        if mot:
            m = motor(fr, mot)
            print(f"    motor: {len(m)} registros")
            faltan = sorted(set(h) - set(m))
            sobran = sorted(set(m) - set(h))
            print(f"    en hardware y NO en motor: "
                  f"{[('%02X' % r) for r in faltan][:24]}")
            print(f"    en motor y NO en hardware: "
                  f"{[('%02X' % r) for r in sobran][:24]}")
            distintos = [(r, h[r], m[r]) for r in sorted(set(h) & set(m))
                         if h[r] != m[r]]
            print(f"    mismos registros, VALOR distinto: {len(distintos)}")
            for r, a, b in distintos[:24]:
                print(f"      reg %02X: hardware=%02X  motor=%02X" % (r, a, b))
        print("    volumenes por canal (hardware): %s"
              % ", ".join("%s=%s/%s" % (k, ("%02X" % v[0]) if v[0] is not None
                                        else "--",
                                        ("%02X" % v[1]) if v[1] is not None
                                        else "--")
                          for k, v in vol_por_canal(h).items()))
        print("    TODOS los registros escritos: %s"
              % ", ".join("%02X=%02X" % (r, h[r]) for r in sorted(h)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())