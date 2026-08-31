#!/usr/bin/env python3
"""Scan a pixel dump directory for black-background frames.

A frame counts as 'black' when a large fraction of the screen is black. We
also report the non-black fraction (content) and where content sits, so real
'background missing' frames can be told apart from legitimately dark scenes.

Usage: find_black.py <pixdir> [<state.bin>] [--min 11500] [--max 14500]
"""
import sys, os, glob
import numpy as np

def load(path):
    d = np.frombuffer(open(path, 'rb').read(), dtype=np.uint8).reshape(224, 256, 4)
    # renderer packs byte0=B, byte1=G, byte2=R -> convert to RGB
    return d[:, :, [2, 1, 0]].astype(np.int16)

def main():
    pixdir = sys.argv[1]
    state_path = sys.argv[2] if len(sys.argv) > 2 and os.path.exists(sys.argv[2]) else None
    lo = 0; hi = 10**9
    if '--min' in sys.argv: lo = int(sys.argv[sys.argv.index('--min') + 1])
    if '--max' in sys.argv: hi = int(sys.argv[sys.argv.index('--max') + 1])

    # preload state records for PPU context
    recs = {}
    if state_path:
        data = open(state_path, 'rb').read()
        REC = 197238; HDR = 12
        n = (len(data) - HDR) // REC
        for i in range(n):
            rec = data[HDR + i * REC: HDR + (i + 1) * REC]
            k = int.from_bytes(rec[0:4], 'little')
            if lo <= k <= hi:
                recs[k] = rec

    files = sorted(glob.glob(os.path.join(pixdir, '*.raw')))
    black_segs = []
    cur = None; start = 0
    rows = []
    for fp in files:
        k = int(os.path.basename(fp)[2:7])
        if k < lo or k > hi: continue
        img = load(fp)
        g = img.mean(axis=2)
        black = float((g < 12).mean())
        content = float((g > 30).mean())
        # content bounding box
        ys, xs = np.where(g > 30)
        box = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(xs) else None
        rec = recs.get(k)
        bgmode = rec[38 + 4] if rec else -1
        inidisp = rec[38 + 0] if rec else -1
        rows.append((k, black, content, box, bgmode, inidisp))
        isb = black > 0.85
        if isb and cur is None: cur = True; start = k
        elif not isb and cur is True: black_segs.append((start, k - 1)); cur = None
    if cur: black_segs.append((start, rows[-1][0]))

    print("black(>85%) segments:")
    for a, b in black_segs:
        print(f"  {a}..{b} ({b - a + 1} frames)")
    print("\nk  black content box bgmode inidisp")
    # sample: boundaries + a few inside each segment
    shown = set()
    for a, b in black_segs:
        for k in [a, a + 1, a + 5, (a + b) // 2, b]:
            if k in shown or k < a or k > b: continue
            shown.add(k)
            for r in rows:
                if r[0] == k:
                    print(f"{k} {r[1]:.3f} {r[2]:.3f} {r[3]} bg={r[4]} inidisp={r[5]:#04x}")
    print("\nnon-black frames (content>8%):")
    for r in rows:
        if r[2] > 0.08:
            print(f"  k={r[0]} content={r[2]:.3f} box={r[3]} bg={r[4]} inidisp={r[5]:#04x}")

if __name__ == '__main__':
    main()
