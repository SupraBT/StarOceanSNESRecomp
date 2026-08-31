#!/usr/bin/env python3
"""Compare the lettering region (STAR OCEAN) across: bsnes screenshot,
our screenshot, and our Python render of BG4 from the live VRAM."""
import os
from PIL import Image

BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2"
BSNES = r"C:\Users\E5-SEG~1\AppData\Local\Temp\freebuff-desktop-pastes\paste-1787581225389-5780.png"
OURS = os.path.join(BASE, "build-trace", "live_frame.bmp")

# ---- Load bsnes screenshot and find the game canvas ----
bs = Image.open(BSNES).convert("RGB")
w, h = bs.size
print("bsnes shot size:", bs.size)

# Scan for the canvas: rows that are mostly dark/teal (game content)
rows_dark = []
for y in range(h):
    row = [bs.getpixel((x, y)) for x in range(0, w, 4)]
    dark = sum(1 for r, g, b in row if r + g + b < 600)
    rows_dark.append(dark / len(row))
# canvas = contiguous middle region with high dark fraction
ys = [y for y in range(h) if rows_dark[y] > 0.9]
canvas_y0, canvas_y1 = min(ys), max(ys) + 1
# find canvas x extent on a canvas row
mid = (canvas_y0 + canvas_y1) // 2
xs = [x for x in range(w) if sum(bs.getpixel((x, mid))) < 600]
canvas_x0, canvas_x1 = min(xs), max(xs) + 1
print("canvas: x=%d..%d y=%d..%d" % (canvas_x0, canvas_x1, canvas_y0, canvas_y1))
ch = canvas_y1 - canvas_y0
cw = canvas_x1 - canvas_x0
scale = ch / 224.0
print("scale (canvas_h/224):", scale)

def sn(x, y):
    """map SNES coords (256x224) to bsnes canvas pixel"""
    # canvas is 512 wide (2x) with aspect stretch; lettering is centered
    return int(canvas_x0 + (canvas_x0 + canvas_x1) / 2 - 128 * scale + x * scale), \
           int(canvas_y0 + y * scale)

def region_stats(img, y0, y1, x0, x1):
    tot = 0
    bright = 0  # greyish-bright pixels (letters)
    teal = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = img.getpixel((x, y))
            tot += 1
            if r + g + b > 380 and abs(r - g) < 40 and abs(g - b) < 60 and r > 90:
                bright += 1
            if b > 80 and g > 60 and r < 120:
                teal += 1
    return bright, teal, tot

# Lettering region from memory: game y 84-110, x centered (letters span ~128 px around center)
for name, img in (("bsnes", bs), ("ours", Image.open(OURS).convert("RGB"))):
    print("\n== %s ==" % name)
    if name == "bsnes":
        sx0, sy0 = sn(0, 0)
        sx1, sy1 = sn(256, 224)
        print("canvas in SNES coords: x=%d..%d y=%d..%d" % (sx0, sx1, sy0, sy1))
        # lettering: game y 84..110, x 60..200 (center-ish)
        lx0, ly0 = sn(56, 80)
        lx1, ly1 = sn(200, 114)
        b, t, tot = region_stats(img, ly0, ly1, lx0, lx1)
        print("lettering region x=%d..%d y=%d..%d: bright=%d teal=%d tot=%d" % (lx0, lx1, ly0, ly1, b, t, tot))
    else:
        ow, oh = img.size
        print("our shot size:", img.size)
        if ow > 256:  # scaled up, assume 2x-ish
            sx = ow // 256
        else:
            sx = 1
        lx0, ly0 = 56 * sx, 80 * sx
        lx1, ly1 = 200 * sx, 114 * sx
        if lx1 <= ow and ly1 <= oh:
            b, t, tot = region_stats(img, ly0, ly1, lx0, lx1)
            print("lettering region x=%d..%d y=%d..%d: bright=%d teal=%d tot=%d" % (lx0, lx1, ly0, ly1, b, t, tot))
        else:
            print("region out of bounds for %dx%d" % (ow, oh))
