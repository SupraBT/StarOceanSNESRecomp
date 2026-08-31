#!/usr/bin/env python3
"""Render each BG layer (real bases, real scrolls) in the lettering region
from the live VRAM/CGRAM dump, to see which layer covers what."""
import os

BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2"
v = open(os.path.join(BASE, "build-trace", "verify_replay", "vram_live.bin"), "rb").read()
c = open(os.path.join(BASE, "build-trace", "verify_replay", "cgram_live.bin"), "rb").read()
cg = [c[i] | (c[i + 1] << 8) for i in range(0, 512, 2)]


def word(o):
    return v[o] | (v[o + 1] << 8)


# Layer configs: (map_word, tile_word, vscroll, hscroll, name)
layers = [
    (0x4800, 0x2000, 1023, 0, "BG1"),
    (0x4C00, 0x2000, 1023, 0, "BG2"),
    (0x5000, 0x4000, 1010, 0, "BG3"),
    (0x5800, 0x4000, 1023, 0, "BG4"),
]


def render_layer(map_w, tile_w, vsc, hsc, x0, x1, y0, y1):
    img = [[0] * (x1 - x0) for _ in range(y1 - y0)]
    for y in range(y0, y1):
        sy = y + vsc
        row = (sy >> 3) & 31
        sc = map_w + (row << 5)
        for x in range(x0, x1):
            sx = x + hsc
            col = (sx >> 3) & 31
            t = word((sc + col) * 2)
            tno = t & 0x3FF
            if not tno:
                continue
            pal = (t >> 10) & 7
            px, py = sx & 7, sy & 7
            if t & 0x4000:
                px = 7 - px
            if t & 0x8000:
                py = 7 - py
            wrd = (tile_w + tno * 8 + py) * 2
            plane = v[wrd] | (v[wrd + 1] << 8)
            bit = 7 - px
            pix = ((plane >> bit) & 1) | (((plane >> (bit + 8)) & 1) << 1)
            if pix:
                colr = cg[pal * 4 + pix]
                r = (colr & 0x1F) * 255 // 31
                g = ((colr >> 5) & 0x1F) * 255 // 31
                b = ((colr >> 10) & 0x1F) * 255 // 31
                img[y - y0][x - x0] = (r, g, b)
    return img


X0, X1, Y0, Y1 = 40, 200, 84, 140
print("Region x=%d..%d y=%d..%d — occupancy per layer (chars):" % (X0, X1, Y0, Y1))
for map_w, tile_w, vsc, hsc, name in layers:
    img = render_layer(map_w, tile_w, vsc, hsc, X0, X1, Y0, Y1)
    nz = sum(1 for row in img for p in row if p)
    print("\n== %s (map $%04X tiles $%04X vsc=%d): %d colored px ==" % (name, map_w, tile_w, vsc, nz))
    for i in range(0, Y1 - Y0, 2):
        y = Y0 + i
        line = ""
        for j in range(X1 - X0):
            p = img[i][j]
            if p:
                r, g, b = p
                line += "#" if r + g + b > 300 else "+"
            else:
                line += "."
        print("%3d %s" % (y, line))
