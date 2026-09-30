#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A/B byte-exacto de dos corridas del motor por sus lineas `[fstate]`.

Por que existe: la puerta A/B de `tools/verificar.py` compara una corrida contra
un baseline guardado, o sea contra si misma. Eso no puede detectar que el camino
AOT (los bancos de `generated/`) difiera del camino interpretado: las dos
corridas serian igual de divergentes y el A/B pasaria.

La referencia de exactitud del proyecto es el **interprete puro**, y el motor ya
trae la palanca: `SNESRECOMP_LLE_BOUNCE=0` desactiva el salto a los cuerpos AOT
("interpret-everything behavior", ver interp_bridge.c). Corriendo el MISMO
binario y el MISMO guion con la palanca a 1 (AOT, por defecto) y a 0 (LLE puro)
y comparando los `[fstate]` linea a linea se mide lo unico que importa:
si el codigo generado es equivalente al interprete.

Uso:
  python tools/ab_lle.py --a logs/f0_aot.log --b logs/f0_lle.log
"""
import argparse
import re
import sys

FSTATE = re.compile(r"\[fstate\]\s+f=(\d+)\s+nmiEn=\d+\s+resume=([0-9A-F]{6})\s+.*?master=(\d+)")


def load(path):
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "[fstate]" not in line:
                continue
            m = FSTATE.search(line)
            if m:
                out.append((int(m.group(1)), m.group(2), int(m.group(3)), line.rstrip("\n")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="log del lado AOT (snapshot a validar)")
    ap.add_argument("--b", required=True, help="log del lado LLE puro (referencia)")
    ap.add_argument("--etiqueta-a", default="AOT")
    ap.add_argument("--etiqueta-b", default="LLE")
    a = ap.parse_args()

    A = load(a.a)
    B = load(a.b)
    print("A (%s): %d frames -> %s" % (a.etiqueta_a, len(A), a.a))
    print("B (%s): %d frames -> %s" % (a.etiqueta_b, len(B), a.b))
    n = min(len(A), len(B))
    if n == 0:
        print("ERROR: alguno de los dos logs no tiene lineas [fstate]")
        return 1

    dif = None
    for i in range(n):
        if A[i][3] != B[i][3]:
            dif = i
            break

    if dif is None:
        print("IDENTICOS en los %d frames comunes (master final A=%d B=%d)"
              % (n, A[n - 1][2], B[n - 1][2]))
        if len(A) != len(B):
            print("aviso: longitudes distintas (%d vs %d), comparado el prefijo" % (len(A), len(B)))
        return 0

    print("PRIMERA DIVERGENCIA en el frame comun #%d (f_%s=%d, f_%s=%d)"
          % (dif, a.etiqueta_a, A[dif][0], a.etiqueta_b, B[dif][0]))
    print("  master: A=%d  B=%d  (delta %+d ciclos = %+.4f frames)"
          % (A[dif][2], B[dif][2], A[dif][2] - B[dif][2],
             (A[dif][2] - B[dif][2]) / 357368.0))
    for i in range(max(0, dif - 2), min(n, dif + 3)):
        marca = "  <<<" if i == dif else ""
        print("  #%d A=%s" % (i, A[i][3]))
        print("  #%d B=%s%s" % (i, B[i][3], marca))
    total = sum(1 for i in range(n) if A[i][3] != B[i][3])
    print("  frames distintos en el prefijo comun: %d/%d (%.2f%%)" % (total, n, 100.0 * total / n))
    return 1


if __name__ == "__main__":
    sys.exit(main())
