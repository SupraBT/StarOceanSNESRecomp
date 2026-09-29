#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Perfil de lecturas por frame del recomp (rd_count.log de SNESRECOMP_RDCOUNT).

Uso: python rd_profile.py <rd_count.log> [a] [b]
     python rd_profile.py <rd_count.log> runs      (resumen por tramos estables)
"""
import re, sys

LINE = re.compile(r"f(\d+)\s+master=(\d+) (.*?) ((\$[0-9A-F]{4}=\d+/[0-9A-F]{2} ?)*)$")
ITEM = re.compile(r"\$([0-9A-F]{4})=(\d+)/([0-9A-F]{2})")


def load(path):
    out = []
    for line in open(path, errors="replace"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = LINE.match(line)
        if not m:
            continue
        d = {}
        for a, n, v in ITEM.findall(m.group(4)):
            d[a] = (int(n), int(v, 16))
        out.append((int(m.group(1)), m.group(3), d))
    return out


def main():
    path = sys.argv[1]
    rows = load(path)
    print("frames con datos = %d" % len(rows))
    if len(sys.argv) > 2 and sys.argv[2] == "runs":
        for key in ("4800", "4801", "4806", "4807", "4212", "2140", "2141"):
            prev = None
            start = None
            print("=== $%s ===" % key)
            for f, fn, d in rows:
                v = d.get(key)
                sig = None if v is None else (v[0] // 50, v[0] // 8 if v[1] else 0)
                if sig != prev:
                    if prev is not None:
                        print("   f%-6d..%-6d  %s" % (start, f - 1, last))
                    prev = sig
                    start = f
                last = "n=%s v=%02X fn=%s" % (v[0], v[1], fn[:26]) if v else "(sin lecturas)"
            if prev is not None:
                print("   f%-6d..%-6d  %s" % (start, rows[-1][0], last))
        return
    a = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    b = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 9
    for f, fn, d in rows:
        if a <= f <= b:
            print("f%-6d %-26s %s" % (f, fn[:26],
                                      " ".join("%s=%s/%02X" % (k, v[0], v[1])
                                               for k, v in sorted(d.items()))))


if __name__ == "__main__":
    main()
