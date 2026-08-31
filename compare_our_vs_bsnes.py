#!/usr/bin/env python3
"""Compare our build's name-screen screenshot against the bsnes screenshot.
Extract bsnes canvas (512x448 at x=39,y=52 in the 590x520 window), downscale
to 256x224, and diff against our BMP render."""
from PIL import Image

BSNES = r"C:\Users\E5-SEG~1\AppData\Local\Temp\freebuff-desktop-pastes\paste-1787581225389-5780.png"
OURS = r"E:\Recompilador Super Nintendo\StarOceanTest2\build-trace\ppu_lines_name.bmp"
OUT = r"E:\Recompilador Super Nintendo\StarOceanTest2\build-trace\verify_replay\bsnes_canvas.png"

# --- bsnes canvas: 512x448 at x=39..550, y=52..499 ---
img = Image.open(BSNES).convert("RGB")
w, h = img.size
# Find exact bounds by scanning for the game's dark border (teal bg ~ (0,30,30))
px = img.load()

def is_teal(c):
    r, g, b = c
    return g > 20 and r < 40 and g - r > 10 and abs(g - b) < 25

# top: first row with a run of >300 teal pixels
def teal_run_row(y):
    run = 0
    for x in range(w):
        if is_teal(px[x, y]):
            run += 1
            if run > 300:
                return True
        else:
            run = 0
    return False

y0 = None
for y in range(h):
    if teal_run_row(y):
        y0 = y
        break
y1 = None
for y in range(h - 1, -1, -1):
    if teal_run_row(y):
        y1 = y
        break
# left/right edges at mid-height
yc = (y0 + y1) // 2
x0, x1 = None, None
for x in range(w):
    if is_teal(px[x, yc]):
        x0 = x
        break
for x in range(w - 1, -1, -1):
    if is_teal(px[x, yc]):
        x1 = x
        break
print("bsnes canvas: x=%d..%d y=%d..%d (%dx%d)" % (x0, x1, y0, y1, x1 - x0 + 1, y1 - y0 + 1))
bsnes = img.crop((x0, y0, x1 + 1, y1 + 1)).resize((256, 224), Image.LANCZOS)
bsnes.save(OUT)

# --- our BMP ---
ours = Image.open(OURS).convert("RGB")
print("ours size:", ours.size)

# --- diff ---
bp = bsnes.load()
op = ours.load()
diff_px = 0
for y in range(224):
    for x in range(256):
        b = bp[x, y]
        o = op[x, y]
        if abs(b[0] - o[0]) + abs(b[1] - o[1]) + abs(b[2] - o[2]) > 90:
            diff_px += 1
print("differing pixels: %d / %d (%.1f%%)" % (diff_px, 256 * 224, 100.0 * diff_px / (256 * 224)))

# ASCII map of WHERE they differ (8x8 blocks)
print("\nDiff map (rows 0..223 step 8, cols step 8; X=diff, .=same):")
for y in range(0, 224, 8):
    row = ""
    for x in range(0, 256, 8):
        cnt = sum(1 for yy in range(y, y + 8) for xx in range(x, x + 8)
                  if abs(bp[xx, yy][0] - op[xx, yy][0]) + abs(bp[xx, yy][1] - op[xx, yy][1]) + abs(bp[xx, yy][2] - op[xx, yy][2]) > 90)
        row += "X" if cnt > 20 else ("+" if cnt > 5 else ".")
    print("%3d %s" % (y, row))
