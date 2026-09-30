#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diferencia fotograma a fotograma dos logs [fstate] + [irqstate].

Muestra, para cada fotograma cuyo consumo de reloj master no sea el nominal
(357368), la fila de ambos lados. Sirve para localizar los tramos donde la
deadline de fotograma realmente cambia el comportamiento del invitado.

Uso:
    python tools/fdiff.py build-hm/Release/irqab_A.log build-hm/Release/irqab_B.log [--top 60]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

NOMINAL = 357368


def parse(log: pathlib.Path):
    out = {}
    for line in log.read_text(errors="replace").splitlines():
        if line.startswith("[fstate]"):
            d = dict(kv.split("=", 1) for kv in line.split()[1:] if "=" in kv)
            f = int(d.get("f", -1))
            if f >= 0:
                out[f] = {"irq": int(d.get("irq", 0)),
                          "nmi": int(d.get("nmi", 0)),
                          "master": int(d.get("master", 0)),
                          "resume": d.get("resume", ""),
                          "D8": d.get("D8"), "E1": None, "F7": None,
                          "DA": d.get("DA"), "inidisp": d.get("inidisp")}
        elif line.startswith("[irqstate]"):
            d = dict(kv.split("=", 1) for kv in line.split()[1:] if "=" in kv)
            f = int(d.get("f", -1))
            if f in out:
                out[f]["E1"] = int(d.get("E1", 0), 16)
                out[f]["F7"] = int(d.get("F7", 0), 16)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--top", type=int, default=60)
    args = ap.parse_args()
    A, B = parse(pathlib.Path(args.a)), parse(pathlib.Path(args.b))
    common = sorted(set(A) & set(B))
    print("fotogramas comunes: %d" % len(common))

    rows = []
    prev_a = prev_b = None
    for f in common:
        da = A[f]["master"] - prev_a if prev_a is not None else 0
        db = B[f]["master"] - prev_b if prev_b is not None else 0
        prev_a, prev_b = A[f]["master"], B[f]["master"]
        # un salto del reloj mayor que 1 frame de invitado
        if da > NOMINAL * 3 // 2 or db > NOMINAL * 3 // 2:
            rows.append((f, da, db))
    print("fotogramas con salto de reloj (>1,5 frames): %d" % len(rows))
    for f, da, db in rows[:args.top]:
        a, b = A[f], B[f]
        print("f=%-5d A: dM=%-9d resume=%s E1=%s D8=%s | B: dM=%-9d "
              "resume=%s E1=%s D8=%s"
              % (f, da, a["resume"], a["E1"], a["D8"],
                 db, b["resume"], b["E1"], b["D8"]))

    # divergencia de estado: primer fotograma donde A y B dejan de coincidir
    for k in ("master", "irq", "nmi", "E1", "D8", "F7", "resume", "DA",
              "inidisp"):
        for f in common:
            if A[f][k] != B[f][k]:
                print("primera divergencia en %s: f=%d  A=%s  B=%s"
                      % (k, f, A[f][k], B[f][k]))
                break
        else:
            print("%-8s identico en los %d fotogramas comunes" % (k, len(common)))
    return 0


if __name__ == "__main__":
    sys.exit(main())