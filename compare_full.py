#!/usr/bin/env python3
"""Side-by-side ASCII of our screenshot vs the bsnes canvas (lettering zone)."""
import os
from PIL import Image

BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2"
BSNES = r"C:\Users\E5-SEG~1\AppData\Local\Temp\freebuff-desktop-pastes\paste-1787581225389-5780.png"
OURS = os.path.join(BASE, "build-trace", "live_frame.bmp")

bs = Image.open(BSNES).convert("RGB")
w, h = bs.size
# Canvas located in earlier analysis: 512x448 game at 2x inside x=39..550,y=52..499
x0, x1, y0, y1 = 39, 551, 52, 500
print("bsnes canvas: x=%d..%d y=%d..%d (%dx%d)" % (x0, x1, y0, y1, x1 - x0, y1 - y0))
# downsample canvas to 256 wide
cw = x1 - x0
ch = y1 - y0
sx = cw / 256.0
sy = ch / 224.0
print("scale: x=%.2f y=%.2f" % (sx, sy))

ours = Image.open(OURS).convert("RGB")


def ascii_row(img, y, is_bsnes):
    line = ""
    for x in range(0, 256, 2):
        if is_bsnes:
            px = img.getpixel((int(x0 + x * 2 + 1), int(y0 + y * 2 + 1)))
        else:
            px = img.getpixel((x, y))
        r, g, b = px
        if r + g + b > 380 and r > 90:
            line += "#"
        elif b > 70 and g > 50 and r < 130:
            line += "~"
        elif r + g + b < 180:
            line += "."
        else:
            line += " "
    return line


print("\ny   bsnes                             | ours")
print("-" * 130)
for y in range(76, 140, 2):
    print("%3d %s | %s" % (y, ascii_row(bs, y, True), ascii_row(ours, y, False)))
