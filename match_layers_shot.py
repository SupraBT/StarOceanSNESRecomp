#!/usr/bin/env python3
"""Correlate candidate layer renders against our build's actual screenshot to
find which (map, tile base) the renderer really uses."""
import json
import os
from PIL import Image

BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2\build-trace"
vram = open(os.path.join(BASE, "verify_replay", "vram_pop.bin"), "rb").read()
cgram = open(os.path.join(BASE, "verify_replay", "cgram_pop.bin"), "rb").read()
scrolls = json.load(open(os.path.join(BASE, "ppu_lines_full.json")))
shot = Image.open(os.path.join(BASE, "ppu_lines_name.bmp")).convert("RGB")
sp = shot.load()

MAP_INDEX = {0x4800: 0, 0x4C00: 1, 0x5000: 2, 0x5800: 3}


def cgram_rgb(i):
    v = cgram[i * 2] | (cgram[i * 2 + 1] << 8)
    return (((v) & 0x1F) << 3, ((v >> 5) & 0x1F) << 3, ((v >> 10) & 0x1F) << 3)


def render(tm, tb):
    img = Image.new("RGB", (256, 224), (0, 0, 0))
    pix = img.load()
    for y in range(224):
        vs = scrolls.get(str(y), {}).get("v", [1023, 1023, 1010, 1023])
        v = vs[MAP_INDEX[tm]]
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
    return img


def agreement(img):
    pix = img.load()
    match = tot = 0
    for y in range(0, 224, 4):
        for x in range(0, 256, 4):
            mp = pix[x, y] != (0, 0, 0)
            s = sp[x, y]
            spresent = (s[0] + s[1] + s[2]) / 3 > 12 or s[1] > 12
            tot += 1
            if mp == spresent:
                match += 1
    return 100.0 * match / tot


for tm in (0x4800, 0x4C00):
    for tb in (0x0000, 0x2000, 0x4000, 0x6000, 0x8000, 0xA000, 0xC000, 0xE000):
        img = render(tm, tb)
        print("map $%04X tiles $%04X: agreement %.1f%%" % (tm, tb, agreement(img)))
