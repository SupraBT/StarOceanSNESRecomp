#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Histograma de `resume` (PC de 24 bits) por fase de `inidisp` en un [fstate].

Uso: python phase_pc.py <log> [minframes]
"""
import sys, os, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_boot as A


def main():
    rows = A.load_recomp(sys.argv[1])
    minlen = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    # fases por inidisp
    ph = []
    prev = None
    start = None
    for r in rows:
        if r.inidisp != prev:
            if prev is not None:
                ph.append((start, r.f - 1, prev))
            prev = r.inidisp
            start = r.f
    ph.append((start, rows[-1].f, prev))
    by = {r.f: r for r in rows}
    for a, b, v in ph:
        n = b - a + 1
        if n < minlen:
            continue
        c = collections.Counter()
        e4 = collections.Counter()
        for f in range(a, b + 1):
            r = by.get(f)
            if r:
                c[r.resume] += 1
                e4[r.e4] += 1
        top = " ".join("%s:%d" % (k, v2) for k, v2 in c.most_common(6))
        print("inidisp=%s  f %d..%d (%d)   E4=%s" % (
            v, a, b, n,
            " ".join("%s:%d" % ("%04X" % k, v2) for k, v2 in e4.most_common(4))))
        print("    resume: %s" % top)


if __name__ == "__main__":
    main()
