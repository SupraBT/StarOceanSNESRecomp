#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Oraculo de ESTADO: compara el estado del invitado del recomp con el trace de
hardware, frame a frame, alineando por reloj master.

Por que registros y no PC: `CpuState` no guarda PC (el codigo AOT usa control de
flujo nativo y el LLE solo publica su punto de reanudacion), asi que el PC no es
comparable. Los registros A/X/Y/SP/D/DB/P si son estado del invitado, y el trace
de Mesen los trae por frame.

El muestreo no cae en el mismo instante exacto en ambos lados (nuestra frontera
de frame esta ~0,15 frame despues de la de Mesen), asi que comparar frame a
frame da ruido de +-1 instruccion. Lo que se mide, por tanto, no es "el primer
frame distinto" sino **donde se desploma el acuerdo**: se calcula el porcentaje
de registros iguales en ventanas de N frames y se busca la primera ventana que
cae muy por debajo de la linea base (el punto en que el juego deja de ir por el
mismo camino).

Uso:
  python tools/oraculo_estado.py --fstate logs/s_estado.log --trace <trace.tsv>
"""
import argparse
import bisect
import sys

MASTER_PER_FRAME = 1364 * 262
FIELDS = ["A", "X", "Y", "S", "DP", "DB", "P"]


def load_fstate(path):
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "[fstate]" not in line:
                continue
            d = {}
            for tok in line.split():
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    if k != "[fstate]":
                        d[k] = v
            if d:
                out.append(d)
    return out


def load_trace(path, lo, hi):
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("#"):
                continue
            c = line.rstrip("\r\n").split("\t")
            if len(c) < 14 or not c[0].strip().isdigit():
                continue
            fr = int(c[0])
            if fr < lo or fr > hi:
                continue
            try:
                out.append(dict(fr=fr, master=int(c[4]), pc=int(c[6], 16),
                                a=int(c[7] or 0, 16), x=int(c[8] or 0, 16),
                                y=int(c[9] or 0, 16), sp=int(c[10] or 0, 16),
                                d=int(c[11] or 0, 16), db=int(c[12] or 0, 16),
                                p=int(c[13] or 0, 16)))
            except ValueError:
                continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fstate", required=True)
    ap.add_argument("--trace", required=True)
    ap.add_argument("--desde", type=int, default=1)
    ap.add_argument("--hasta", type=int, default=100000)
    ap.add_argument("--ventana", type=int, default=60)
    ap.add_argument("--umbral", type=float, default=0.5,
                    help="fraccion de registros iguales por debajo de la cual se considera rotura")
    a = ap.parse_args()

    O = load_fstate(a.fstate)
    T = load_trace(a.trace, a.desde, a.hasta)
    if not O or not T:
        print("ERROR: falta estado de algun lado (fstate=%d filas, trace=%d filas)" % (len(O), len(T)))
        return 1
    om = [int(r["master"]) for r in O]
    print("nuestro: %d muestras | hardware: %d frames (%d..%d)" % (len(O), len(T), T[0]["fr"], T[-1]["fr"]))

    filas = []
    for r in T:
        i = bisect.bisect_left(om, r["master"])
        cand = [j for j in (i - 1, i) if 0 <= j < len(O)]
        if not cand:
            continue
        j = min(cand, key=lambda k: abs(om[k] - r["master"]))
        if abs(om[j] - r["master"]) > MASTER_PER_FRAME // 4:
            continue          # fast-forward: sin frame equiparable
        o = O[j]
        vals = dict(A=int(o.get("A", "0"), 16), X=int(o.get("X", "0"), 16),
                    Y=int(o.get("Y", "0"), 16), S=int(o.get("S", "0"), 16),
                    DP=int(o.get("DP", "0"), 16), DB=int(o.get("DB", "0"), 16),
                    P=int(o.get("P", "0"), 16))
        filas.append((r, o, vals))
    print("frames comparables: %d" % len(filas))
    if not filas:
        return 1

    # Acuerdo por registro y total.
    for f in FIELDS:
        ok = sum(1 for r, o, v in filas
                 if v[f] == {"A": r["a"], "X": r["x"], "Y": r["y"], "S": r["sp"],
                             "DP": r["d"], "DB": r["db"], "P": r["p"]}[f])
        print("  %-4s coincide en %6d/%6d (%5.1f%%)" % (f, ok, len(filas), 100.0 * ok / len(filas)))

    # Curva de acuerdo en ventanas, y primera caida fuerte.
    base = None
    print("\nventana de %d frames: acuerdo total y por registro" % a.ventana)
    caida = None
    for s in range(0, len(filas), a.ventana):
        w = filas[s:s + a.ventana]
        acuerdos = {}
        for f in FIELDS:
            acuerdos[f] = sum(1 for r, o, v in w
                              if v[f] == {"A": r["a"], "X": r["x"], "Y": r["y"], "S": r["sp"],
                                          "DP": r["d"], "DB": r["db"], "P": r["p"]}[f]) / float(len(w))
        tot = sum(acuerdos.values()) / len(FIELDS)
        if base is None and s >= a.ventana * 3:
            base = max(0.35, tot)   # linea base = regimen ya asentado
        if caida is None and base is not None and tot < max(a.umbral, base * 0.5):
            caida = (w[0][0]["fr"], w[-1][0]["fr"], tot, dict(acuerdos))
        if s % (a.ventana * 10) == 0 or (caida and caida[0] == w[0][0]["fr"]):
            print("  fr %6d-%6d total=%5.1f%%  " % (w[0][0]["fr"], w[-1][0]["fr"], 100 * tot)
                  + " ".join("%s=%3.0f%%" % (f, 100 * acuerdos[f]) for f in FIELDS))

    if caida:
        print("\nROTURA: el acuerdo se desploma en fr %d-%d (total %.1f%%)"
              % (caida[0], caida[1], 100 * caida[2]))
        print("  " + " ".join("%s=%.0f%%" % (f, 100 * caida[3][f]) for f in FIELDS))
        print("  antes de esa ventana el acuerdo era del %.0f%%;" % (100 * (base or 0))
              + " a partir de ahi el invitado va por otro camino.")
    else:
        print("\nSin rotura: el estado se mantiene alineado con hardware en toda la ventana comparada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
