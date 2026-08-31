#!/usr/bin/env python3
"""Render all 4 BG layers of the name screen with the CORRECT tile bases
(derived from bgTileAdr=0x4222: BG1/2/3=$2000, BG4=$4000) and the real
per-line BG3 vScroll (from ppu_lines probe), then save a composite."""
import os
from PIL import Image

BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2\build-trace\verify_replay"
vram = open(os.path.join(BASE, "vram_hdma.bin"), "rb").read()
cgram = open(os.path.join(BASE, "cgram_hdma.bin"), "rb").read()


def cgram_rgb(i):
    v = cgram[i * 2] | (cgram[i * 2 + 1] << 8)
    return (((v) & 0x1F) << 3, ((v >> 5) & 0x1F) << 3, ((v >> 10) & 0x1F) << 3)


def render(tm_base, tile_base, name, bpp=2, vscroll=None, hscroll=0):
    img = Image.new("RGB", (256, 224), (0, 0, 0))
    pix = img.load()
    for ty in range(28):
        for tx in range(32):
            w = tm_base + (ty * 32 + tx) * 2
            word = vram[w] | (vram[w + 1] << 8)
            if word == 0:
                continue
            t = word & 0x3FF
            pal = (word >> 10) & 7
            fx = bool(word & 0x4000)
            fy = bool(word & 0x8000)
            for yy in range(8):
                for xx in range(8):
                    sx = 7 - xx if fx else xx
                    sy = 7 - yy if fy else yy
                    base = tile_base + t * 16
                    p0 = vram[base + sy]
                    p1 = vram[base + sy + 8]
                    bit = ((p0 >> sx) & 1) | (((p1 >> sx) & 1) << 1)
                    if bit:
                        pix[tx * 8 + xx, ty * 8 + yy] = cgram_rgb(pal * 16 + bit)
    img.save(os.path.join(BASE, name))
    nb = sum(1 for y in range(224) for x in range(256) if pix[x, y] != (0, 0, 0))
    print("saved %-22s nonblack=%d" % (name, nb))
    return img


render(0x4800, 0x2000, "bg1_correct.png")
render(0x4C00, 0x2000, "bg2_correct.png")
render(0x5000, 0x2000, "bg3_correct.png")
render(0x5800, 0x4000, "bg4_correct.png")
render(0xB000, 0x8000, "bg4_tileviewer.png")
