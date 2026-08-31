#!/usr/bin/env python3
"""Compare the user's bsnes screenshot against ours to find the missing
STAR OCEAN lettering region. Saves crops for inspection."""
from PIL import Image

BSNES = r"C:\Users\E5-SEG~1\AppData\Local\Temp\freebuff-desktop-pastes\paste-1787581225389-5780.png"
OURS = r"C:\Users\E5-SEG~1\AppData\Local\Temp\freebuff-desktop-pastes\paste-1787581113790-5780.png"

b = Image.open(BSNES).convert("RGB")
o = Image.open(OURS).convert("RGB")
print("bsnes:", b.size, " ours:", o.size)

# The SNES canvas is 256x224 (scaled). bsnes window has titlebar+menubar+canvas+statusbar.
# Try to locate the canvas by scanning for the game's distinctive colors.
# Both games show the same name screen; let's find the aspect-ratio-preserved canvas.
# bsnes-plus default: integer scaling? Let's just scan rows for the canvas bounds.

def find_canvas(img):
    w, h = img.size
    # The canvas background is dark; titlebar/menubar are light gray (240ish)
    # Find the largest dark rectangle region.
    rows_dark = []
    for y in range(h):
        r, g, bl = img.getpixel((w // 2, y))
        rows_dark.append((r, g, bl))
    # find contiguous run of dark rows
    dark = [(r < 120 and g < 120 and bl < 120) for r, g, bl in rows_dark]
    runs = []
    start = None
    for i, d in enumerate(dark):
        if d and start is None:
            start = i
        elif not d and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(dark)))
    print("dark row runs (mid-column):", runs[:10])
    return runs

print("--- bsnes ---")
find_canvas(b)
print("--- ours ---")
find_canvas(o)
