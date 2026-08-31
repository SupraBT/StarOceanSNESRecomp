#!/usr/bin/env python3
"""Render the 4 BG layers of the name screen from the VRAM/CGRAM dumps
using the real PPU register layout, to see what each layer contains."""
import os
import sys
from PIL import Image

BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2\build-trace\verify_replay"

vram = open(os.path.join(BASE, "vram_hdma.bin"), "rb").read()
cgram = open(os.path.join(BASE, "cgram_hdma.bin"), "rb").read()


def cgram_rgb(i):
    if i * 2 + 1 >= len(cgram):
        return (0, 0, 0)
    v = cgram[i * 2] | (cgram[i * 2 + 1] << 8)
    r = (v & 0x1F) << 3
    g = ((v >> 5) & 0x1F) << 3
    b = ((v >> 10) & 0x1F) << 3
    return (r, g, b)


def render_layer(tm_base, tile_base, name, bpp=2):
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
            flipx = bool(word & 0x4000)
            flipy = bool(word & 0x8000)
            for yy in range(8):
                for xx in range(8):
                    sx = 7 - xx if flipx else xx
                    sy = 7 - yy if flipy else yy
                    base = tile_base + t * 16
                    if bpp == 2:
                        p0 = vram[base + sy]
                        p1 = vram[base + sy + 8]
                        bit = ((p0 >> sx) & 1) | (((p1 >> sx) & 1) << 1)
                    else:  # 4bpp
                        base = tile_base + t * 32
                        p0 = vram[base + sy]
                        p1 = vram[base + sy + 8]
                        p2 = vram[base + sy + 16]
                        p3 = vram[base + sy + 24]
                        bit = ((p0 >> sx) & 1) | (((p1 >> sx) & 1) << 1) | \
                              (((p2 >> sx) & 1) << 2) | (((p3 >> sx) & 1) << 3)
                    if bit:
                        pix[tx * 8 + xx, ty * 8 + yy] = cgram_rgb(pal * 16 + bit)
    img.save(os.path.join(BASE, name))
    print("saved", name)


# Name screen: BG1/BG2/BG3 maps at $4800/$4C00/$5000, BG4 at $5800 (empty)
# Tile bases: $210B=0x22 -> BG1 tiles $2200; $210C=0x42 -> BG3 tiles $4200?
# In mode 0 all BGs are 2bpp. BG12NBA=0x22: BG1=(0x22>>4)=0x2? No:
# BG12NBA bits 7-4 = BG1, 3-0 = BG2 (each nibble * 0x1000)
# 0x22 -> BG1=0x2 -> $2000, BG2=0x2 -> $2000
# BG34NBA=0x42 -> BG3=0x4 -> $4000, BG4=0x4 -> $4000
render_layer(0x4800, 0x2000, "layer_bg1.png", 2)
render_layer(0x4C00, 0x2000, "layer_bg2.png", 2)
render_layer(0x5000, 0x4000, "layer_bg3.png", 2)
render_layer(0x5800, 0x4000, "layer_bg4.png", 2)
