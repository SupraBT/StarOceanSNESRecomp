#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Genera la tabla `local STORE2100 = {...}` de la sonda de Mesen a partir del ROM.

Los 95 sitios NO se escriben a mano (hacerlo fue un error de una version previa
de la sonda): se escanean los opcodes que almacenan en $2100 y se injertan en
`tools/mesen_intro_probe.lua` entre las marcas

    local STORE2100 = {
    ...
    }

Uso: python tools/gen_2100_sites.py            (regenera e injerta)
     python tools/gen_2100_sites.py --dry      (solo imprime la tabla)
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ROM = os.path.join(ROOT, "Star Ocean (Japan).sfc")
LUA = os.path.join(HERE, "mesen_intro_probe.lua")

# Solo sitios < 0x400000 (bancos $C0-$FF, donde vive el codigo de HiROM).
def pc24(off):
    return ((0xC0 + (off >> 16)) << 16) | (off & 0xFFFF)


def scan(data):
    sites = []
    for pat, kind in ((bytes.fromhex("8D0021"), "STA $2100"),
                      (bytes.fromhex("8E0021"), "STX $2100")):
        i = 0
        while True:
            i = data.find(pat, i)
            if i < 0:
                break
            if i < 0x400000:
                sites.append((pc24(i), pat.hex().upper()))
            i += 1
    # STA long: 8F 00 21 xx -> solo si xx direcciona I/O ($00-$3F, $80-$BF)
    i = 0
    while True:
        i = data.find(bytes.fromhex("8F0021"), i)
        if i < 0:
            break
        if i + 3 < len(data):
            db = data[i + 3]
            if i < 0x400000 and (db <= 0x3F or 0x80 <= db <= 0xBF):
                sites.append((pc24(i), "8F0021" + "%02X" % db))
        i += 1
    sites.sort()
    return sites


def table_text(sites):
    out = ["local STORE2100 = {"]
    line = "  "
    for a, b in sites:
        item = ' { 0x%06X, "%s" },' % (a, b)
        if len(line) + len(item) > 96:
            out.append(line.rstrip())
            line = "  "
        line += item
    if line.strip():
        out.append(line.rstrip())
    out.append("}")
    return "\n".join(out)


def main():
    data = open(ROM, "rb").read()
    sites = scan(data)
    txt = table_text(sites)
    print("sitios encontrados: %d" % len(sites))

    if "--dry" in sys.argv:
        print(txt)
        return 0

    src = open(LUA, encoding="utf-8").read()
    m = re.search(r"^local STORE2100 = \{\n.*?^\}\n", src, flags=re.S | re.M)
    if not m:
        print("ERROR: no encuentro el bloque `local STORE2100 = {` en %s" % LUA)
        return 1
    new = src[:m.start()] + txt + "\n" + src[m.end():]
    open(LUA, "w", encoding="utf-8", newline="\n").write(new)
    print("injertado en %s (bloque de %d lineas -> %d lineas)"
          % (LUA, m.group(0).count("\n"), txt.count("\n") + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
