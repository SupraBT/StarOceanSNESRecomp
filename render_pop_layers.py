#!/usr/bin/env python3
"""Render BG1/BG2 from the populated VRAM dump with correct bases and
per-line scrolls, printing ASCII art to locate the STAR OCEAN lettering."""
import json
import os
from PIL import Image

BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2\build-trace"
vram = open(BASE + r"\verify_replay\vram_pop.bin", "rb").read()
cgram = open(BASE + r"\verify_replay\cgram_pop.bin", "rb").read()
scrolls = json.load(open(BASE + r"\ppu_lines_full.json"))

def cgram_rgb(i):
    v = cgram[i * 2] | (cgram[i * 2 + 1] << 8)
    return (((v) & 0x1F) << 3, ((v >> 5) & 0x1F) << 3, ((v >> 10) & 0x1F) << 3)

def render(tm, tb, name):
    img = Image.new("RGB", (256, 224), (0, 0, 0))
    pix = img.load()
    for y in range(224):
        vs = scrolls.get(str(y), {}).get("v", [1023, 1023, 1010, 1023])
        v = vs[[0x4800, 0x4C00, 0x5000, 0x5800].index(tm)]
        ty = ((v + y) // 8) % 32
        py = (v + y) % 8
        for tx in range(32):
            w = tm + (ty * 32 + tx) * 2
            word = vram[w] | (vram[w + 1] << 8)
            if word == 0:
                continue
            t = word & 0x3FF
            pal = (word >> 10) & 7
            fx = bool(word & 0x4000)
            fy = bool(word & 0x8000)
            base = tb + t * 16
            for xx in range(8):
                sx = 7 - xx if fx else xx
                p0 = vram[base + py]
                p1 = vram[base + py + 8]
                bit = ((p0 >> sx) & 1) | (((p1 >> sx) & 1) << 1)
                if bit:
                    pix[tx * 8 + xx, y] = cgram_rgb(pal * 4 + bit)
    img.save(os.path.join(BASE, "verify_replay", name))
    nb = sum(1 for y in range(224) for x in range(256) if pix[x, y] != (0, 0, 0))
    print("%s nonblack=%d" % (name, nb))
    for y in range(0, 224, 8):
        row = ""
        for x in range(0, 256, 4):
            cnt = sum(1 for yy in range(y, y + 8) for xx in range(x, x + 4) if pix[xx, yy] != (0, 0, 0))
            row += "#" if cnt > 12 else ("." if cnt == 0 else "+")
        print("%3d %s" % (y, row))
    print()

render(0x4800, 0x2000, "bg1_pop.png")
render(0x4C00, 0x2000, "bg2_pop.png")
