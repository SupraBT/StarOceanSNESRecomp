#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Parser del oraculo viejo (mesen_oracle.tsv) — la unica fuente fiable que
tenemos de las ESCRITURAS REALES a $2100 en hardware.

Cabecera: fr master cpuCyc inidisp w2140 r2140 ram83 spcOut dspw reg4200 pad

Hechos medidos el 29/09:
  * El fichero son DOS pasadas concatenadas (salto de fr 11788 -> 411).  Ambas
    pasadas son la MISMA corrida determinista (mismo `master` en el mismo `fr`),
    asi que se puede usar la union.
  * Hay filas corruptas (col 0 no numerica: la lista de valores de $2100 acaba
    en la primera columna).  Se descartan.
  * La columna `inidisp` NO es un snapshot del registro: son las **escrituras a
    $2100** de ese frame (`80`, `00+80`, `81+01+00+00`...).  Esta vacia en los
    frames sin escritura, por eso parece que hay huecos: hay que sostener el
    ultimo valor escrito para reconstruir la pantalla.
  * El `master` de fr820 (292632288) coincide EXACTAMENTE con mesen_intro_probe.tsv
    -> mismo run, misma linea temporal.

Uso: python oracle_tsv.py pantalla
     python oracle_tsv.py writes
"""
import sys, os, re

TSV = r"E:\Experimento Hermes\Documentacion\TracesMesen\mesen_oracle.tsv"
ITEM = re.compile(r"([0-9A-F]{2})")


def load(path=TSV):
    """Devuelve lista de (fr, master, writes) con writes = [valores $2100]."""
    out = []
    for line in open(path, errors="replace"):
        line = line.rstrip("\r\n")
        if not line or line.startswith("fr\t"):
            continue
        c = line.split("\t")
        try:
            fr = int(c[0])
        except ValueError:
            continue                       # fila corrupta
        ini = c[3].strip() if len(c) > 3 else ""
        vals = [int(x, 16) for x in ini.split("+")] if ini else []
        out.append((fr, c[1], vals))
    return out


def pantalla(rows):
    """Reconstruye el valor de $2100 sosteniendo la ultima escritura."""
    print("=== $2100 en hardware: secuencia de valores escritos ===")
    last = None
    cur = None
    start = None
    for fr, m, vals in rows:
        for v in vals:
            if cur is None:
                cur, start = v, fr
            elif v != cur:
                print("  %-5d..%-5d %5d  $2100=%02X%s" % (
                    start, fr - 1, fr - start, cur,
                    "   (sostenido)" if last is not None else ""))
                cur, start = v, fr
            last = fr
    print("  %-5d..%-5d        $2100=%02X" % (start, last, cur))
    print()
    print("=== frames con escritura a $2100 ===")
    n = 0
    for fr, m, vals in rows:
        if vals:
            print("  fr%-5d %s" % (fr, "+".join("%02X" % v for v in vals)))
            n += 1
    print("  (total %d frames con escritura de %d frames)" % (n, len(rows)))
    print()
    print("=== tramos de frames SIN escritura (pantalla congelada) ===")
    prev = None
    st = None
    for fr, m, vals in rows:
        has = bool(vals)
        if has != prev:
            if prev is False and st is not None:
                print("  fr %-5d..%-5d  %5d frames sin escritura" % (st, fr - 1, fr - st))
            st = fr
            prev = has
    if prev is False:
        print("  fr %-5d..%-5d  %5d frames sin escritura" % (st, rows[-1][0], rows[-1][0] - st + 1))


if __name__ == "__main__":
    rows = load()
    print("filas utiles=%d  fr %d..%d" % (len(rows), rows[0][0], rows[-1][0]))
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pantalla"
    if cmd == "writes":
        for fr, m, vals in rows:
            if vals:
                print("fr%-6d %s" % (fr, "+".join("%02X" % v for v in vals)))
    else:
        pantalla(rows)
