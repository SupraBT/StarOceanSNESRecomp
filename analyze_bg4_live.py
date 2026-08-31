#!/usr/bin/env python3
"""Analyze the live VRAM capture: is BG4's lettering data present, and does
rendering BG4 from word $5800 (map) / $4000 (tiles) produce the STAR OCEAN
lettering?"""
import os

BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2"
VR = os.path.join(BASE, "build-trace", "verify_replay", "vram_live.bin")
CG = os.path.join(BASE, "build-trace", "verify_replay", "cgram_live.bin")

v = open(VR, "rb").read()
c = open(CG, "rb").read()
assert len(v) == 65536, len(v)


def word(byte_off):
    return v[byte_off] | (v[byte_off + 1] << 8)


def words(byte_off, n):
    out = []
    for i in range(n):
        out.append(word(byte_off + 2 * i))
    return out


# --- BG4 map at word $5800 (dump byte $B000), 32x32 entries ---
map_b4 = words(0xB000, 1024)
nz_b4 = sum(1 for t in map_b4 if t & 0x3FF)
print("BG4 map @word $5800 (byte $B000): %d/1024 nonzero tiles" % nz_b4)
if nz_b4:
    print("  sample entries:", [hex(t) for t in map_b4[:12]])

# --- BG4 tiles at word $4000 (dump byte $8000): any nonzero plane words? ---
tiles_b4 = words(0x8000, 0x2000)  # 8KB of words = 1024 tiles * 8
nz_tiles = sum(1 for t in tiles_b4 if t)
print("BG4 tiles @word $4000 (byte $8000): %d/8192 nonzero words" % nz_tiles)

# --- Render BG4: 2bpp, map word $5800, tiles word $4000, scroll 0 ---
cgram = [c[i] | (c[i + 1] << 8) for i in range(0, 512, 2)]


def render_bg(map_base_word, tile_base_word, bpp=2, vscroll=0, hscroll=0,
              w=256, h=224, big=False):
    img = [[0] * w for _ in range(h)]
    for y in range(h):
        sy = y + vscroll
        row = (sy >> 3) & 31
        sc = map_base_word + (row << 5)
        for x in range(w):
            sx = x + hscroll
            col = (sx >> 3) & 31
            tile = word(sc * 2 + col * 2) if False else \
                v[(sc + col) * 2] | (v[(sc + col) * 2 + 1] << 8)
            tno = tile & 0x3FF
            pal = (tile >> 10) & 7
            px = sx & 7
            py = sy & 7
            if tile & 0x4000:
                px = 7 - px
            if tile & 0x8000:
                py = 7 - py
            row_w = tile_base_word + tno * 8 + py
            plane = v[row_w * 2] | (v[row_w * 2 + 1] << 8)
            bit = 7 - px
            pix = ((plane >> bit) & 1) | (((plane >> (bit + 8)) & 1) << 1)
            if pix:
                idx = pal * 4 + pix
                colr = cgram[idx]
                r = (colr & 0x1F) * 255 // 31
                g = ((colr >> 5) & 0x1F) * 255 // 31
                b2 = ((colr >> 10) & 0x1F) * 255 // 31
                img[y][x] = (r, g, b2)
    return img


img4 = render_bg(0x5800, 0x4000)
nz = sum(1 for row in img4 for p in row if p)
print("BG4 render (map $5800/tiles $4000): %d colored pixels" % nz)

# ASCII art of the top half to spot the lettering
for y in range(0, 112, 4):
    line = ""
    for x in range(0, 256, 4):
        pix = img4[y][x]
        line += "#" if pix else "."
    print(line)

# Save a PPM for inspection
with open(os.path.join(BASE, "build-trace", "bg4_render.ppm"), "w") as f:
    f.write("P3\n256 224\n255\n")
    for row in img4:
        for p in row:
            f.write("%d %d %d " % (p[0], p[1], p[2]) if p else "0 0 0 ")
        f.write("\n")
print("saved bg4_render.ppm")
