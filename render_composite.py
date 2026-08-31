#!/usr/bin/env python3
"""Composite the 4 BG layers with correct hardware tile bases and the REAL
per-line scrolls, then ASCII-art the result to find the STAR OCEAN lettering."""
import json
from PIL import Image

BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2\build-trace"
vram = open(BASE + r"\verify_replay\vram_hdma.bin", "rb").read()
scrolls = json.load(open(BASE + r"\ppu_lines_full.json"))

# layer config: (map_base, tile_base) per hardware ($2107-210A + $210B/210C)
L = [(0x4800, 0x2000), (0x4C00, 0x2000), (0x5000, 0x4000), (0x5800, 0x2000)]

img = Image.new("RGB", (256, 224), (0, 0, 0))
pix = img.load()

for y in range(224):
    vs = scrolls.get(str(y), {}).get("v", [0, 0, 0, 0])
    for bg in range(4):
        tm, tb = L[bg]
        v = vs[bg]
        ty = ((v + y) // 8) % 32
        py = (v + y) % 8
        for tx in range(32):
            w = tm + (ty * 32 + tx) * 2
            word = vram[w] | (vram[w + 1] << 8)
            if word == 0:
                continue
            t = word & 0x3FF
            fx = bool(word & 0x4000)
            fy = bool(word & 0x8000)
            base = tb + t * 16
            for xx in range(8):
                sx = 7 - xx if fx else xx
                p0 = vram[base + py]
                p1 = vram[base + py + 8]
                bit = ((p0 >> sx) & 1) | (((p1 >> sx) & 1) << 1)
                if bit:
                    pix[tx * 8 + xx, y] = (255, 255, 255)

print("=== composite (any layer, per-line scrolls) ===")
for y in range(0, 224, 4):
    row = ""
    for x in range(0, 256, 4):
        cnt = sum(1 for yy in range(y, y + 4) for xx in range(x, x + 4) if pix[xx, yy] != (0, 0, 0))
        row += "#" if cnt > 8 else ("." if cnt == 0 else "+")
    print("%3d %s" % (y, row))
