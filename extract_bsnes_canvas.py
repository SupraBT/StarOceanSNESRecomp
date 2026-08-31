#!/usr/bin/env python3
"""Extract the SNES canvas from the user's bsnes-plus screenshot.
The window is 590x520; canvas is 2x (512x448) or ~2.2x, bounded by the
light menubar (top) and dark statusbar (bottom). We find the biggest run
of rows where >55% of pixels are dark-game pixels, then the columns."""
from PIL import Image

BSNES = r"C:\Users\E5-SEG~1\AppData\Local\Temp\freebuff-desktop-pastes\paste-1787581225389-5780.png"
OUT = r"E:\Recompilador Super Nintendo\StarOceanTest2\build-trace\verify_replay\bsnes_canvas.png"

img = Image.open(BSNES).convert("RGB")
w, h = img.size
px = img.load()

# game pixels: teal (0,94,94) fill, dark teal (0,15,15), portrait colors, lettering.
# chrome: (34,34,34) window bg, (204,225,225) borders, near-white menubar.
# Simplest robust discriminator at full rows: the game rows are NEVER dominated
# by light pixels. Use: dark = r+g+b < 420 OR teal (g>r+10 and g>30).
def is_game(c):
    r, g, b = c
    if g > 30 and g - r > 10:
        return True  # teal/blue-teal (lettering, panel fill)
    return r + g + b < 420  # dark

rows = [sum(1 for x in range(w) if is_game(px[x, y])) / w for y in range(h)]

# biggest run of rows with frac > 0.5
best = (0, 0, 0)
cur = None
for y in range(h):
    if rows[y] > 0.5:
        if cur is None:
            cur = y
    else:
        if cur is not None and y - cur > best[2]:
            best = (cur, y - 1, y - cur)
        cur = None
if cur is not None and h - cur > best[2]:
    best = (cur, h - 1, h - cur)
y0, y1 = best[0], best[1]
print("row band y=%d..%d (len %d), scale=%.2f" % (y0, y1, best[2], best[2] / 224.0))

# columns within band
cols = []
for x in range(w):
    dark = sum(1 for y in range(y0, y1 + 1) if is_game(px[x, y]))
    cols.append(dark / best[2])
bestx = (0, 0, 0)
cur = None
for x in range(w):
    if cols[x] > 0.5:
        if cur is None:
            cur = x
    else:
        if cur is not None and x - cur > bestx[2]:
            bestx = (cur, x - 1, x - cur)
        cur = None
if cur is not None and w - cur > bestx[2]:
    bestx = (cur, w - 1, w - cur)
x0, x1 = bestx[0], bestx[1]
print("col band x=%d..%d (len %d), scale=%.2f" % (x0, x1, bestx[2], bestx[2] / 256.0))

canvas = img.crop((x0, y0, x1 + 1, y1 + 1)).resize((256, 224), Image.LANCZOS)
canvas.save(OUT)
print("saved", OUT, canvas.size)
