#!/usr/bin/env python3
"""Align recomp frames to oracle frames by WRAM and diff rendered pixels.

Usage:
  python compare_video.py <recomp_state.bin> <oracle_state.bin>
                          <recomp_pix_dir> <oracle_pix_dir>
                          [--out report.txt]

Pixel formats (verified against bsnes-plus light_table + color_convert):
  recomp: 256x224 RGBA32 (raw, 1024-byte rows); the renderer writes
          byte0=B, byte1=G, byte2=R (ARGB8888 memory order)
  oracle: 512x224 RGB555 (raw, 1024-byte rows; hires) or 256x224
          (512-byte rows); bits 10-14=R, 5-9=G, 0-4=B
"""
import os
import sys
import struct
import glob

import numpy as np

REC = 197238
HDR = 12
WRAM_OFF = 118
WRAM_LEN = 0x20000
VRAM_OFF = WRAM_OFF + WRAM_LEN
CGRAM_OFF = VRAM_OFF + 0x10000
CGRAM_LEN = 0x200


def load_records(path):
    data = open(path, "rb").read()
    n = (len(data) - HDR) // REC
    recs = []
    for i in range(n):
        off = HDR + i * REC
        rec = data[off:off + REC]
        frame = struct.unpack_from("<I", rec, 0)[0]
        wram = np.frombuffer(rec, dtype=np.uint8, count=WRAM_LEN, offset=WRAM_OFF)
        ppu = rec[38:38 + 66]
        sdd1 = rec[112:112 + 6]
        recs.append((frame, wram, ppu, sdd1, rec))
    return recs


def load_pix(path, w):
    """Load raw pixel file; return RGB888 array (h, w, 3).

    NOTE: a 256x224x4 recomp file and a 512x224x2 oracle file are BOTH
    229376 bytes, so the width argument must disambiguate the format.
    """
    data = open(path, "rb").read()
    if w >= 512:
        # oracle hires: RGB555 (bits 10-14=R, 5-9=G, 0-4=B), 512x224
        u = np.frombuffer(data, dtype="<u2").reshape(224, 512)
        # downsample pairs -> 256
        u = u.reshape(224, 256, 2).mean(axis=2).astype(np.uint16)
        return rgb555_to_rgb(u)
    if len(data) == 256 * 224 * 4:
        # recomp: 256x224 RGBA32; renderer packs byte0=B, byte1=G, byte2=R
        arr = np.frombuffer(data, dtype=np.uint8).reshape(224, 256, 4)
        return arr[:, :, [2, 1, 0]].copy()
    # oracle 256x224 RGB555
    u = np.frombuffer(data, dtype="<u2").reshape(224, 256)
    return rgb555_to_rgb(u)


def rgb555_to_rgb(u):
    r = ((u >> 10) & 0x1F) * 255 // 31
    g = ((u >> 5) & 0x1F) * 255 // 31
    b = ((u >> 0) & 0x1F) * 255 // 31
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


def align(recomp, oracle, window=0x400):
    """Fixed-offset alignment: recomp[k] ~ oracle[k + offset]. The recomp
    boots ~77 frames faster than the oracle (quiescent-point framing skips
    boot wait loops), so inputs must be shifted by that offset to keep the
    game states in sync. Returns list of (k, k+offset, diff)."""
    offset = 77
    pairs = []
    for k in range(len(recomp)):
        f = k + offset
        if f >= len(oracle):
            break
        diff = int(np.abs(recomp[k][1][:window].astype(np.int16) -
                           oracle[f][1][:window].astype(np.int16)).sum())
        pairs.append((k, f, diff))
    return pairs


def frame_black_frac(img, thresh=8):
    g = img.mean(axis=2)
    return float((g < thresh).mean())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    recomp_state, oracle_state = args[0], args[1]
    recomp_pix, oracle_pix = args[2], args[3]
    out = "video_compare_report.txt"
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]

    print("loading states...")
    rec = load_records(recomp_state)
    orc = load_records(oracle_state)
    print(f"  recomp {len(rec)} recs, oracle {len(orc)} recs")

    print("aligning by WRAM...")
    pairs = align(rec, orc)

    # sanity: how tight is the match?
    diffs = np.array([p[2] for p in pairs])
    print(f"  WRAM diff: median={np.median(diffs)} mean={diffs.mean():.1f} "
          f"max={diffs.max()}")

    # candidate recomp pixel files
    rp_files = sorted(glob.glob(os.path.join(recomp_pix, "*.raw")))
    op_files = sorted(glob.glob(os.path.join(oracle_pix, "*.raw")))
    print(f"  recomp pix {len(rp_files)}, oracle pix {len(op_files)}")

    rows = []
    checked = 0
    black_bad = []
    for k, f, d in pairs:
        rp = os.path.join(recomp_pix, f"f_{k:05d}.raw")
        op = os.path.join(oracle_pix, f"f_{f:05d}.raw")
        if not (os.path.exists(rp) and os.path.exists(op)):
            continue
        try:
            rimg = load_pix(rp, 256)
            oimg = load_pix(op, 512 if os.path.getsize(op) > 256 * 224 * 2 else 256)
        except Exception as e:
            print(f"  pix load fail k={k}: {e}")
            continue
        checked += 1
        # per-pixel RGB distance
        diff = np.abs(rimg.astype(np.int16) - oimg.astype(np.int16)).sum(axis=2)
        mean_diff = float(diff.mean())
        frac_diff = float((diff > 30).mean())
        rf = frame_black_frac(rimg)
        of = frame_black_frac(oimg)
        bad_black = rf > 0.5 and of < 0.5
        rows.append((k, f, d, mean_diff, frac_diff, rf, of, bad_black))
        _ = None  # noqa
        if bad_black:
            black_bad.append((k, f, rf, of, mean_diff))

    with open(out, "w") as fh:
        fh.write("# k recomp_frame oracle_frame wram_diff mean_pixdiff frac_pixdiff recomp_black oracle_black bad_black\n")
        for r in rows:
            fh.write("%d %d %d %.2f %.3f %.3f %.3f %d\n" % r)
        # k->f mapping summary
        fh.write("# --- k->f mapping (every 50th) ---\n")
        for r in rows[::50]:
            fh.write("# k=%d f=%d wram_diff=%d\n" % (r[0], r[1], r[2]))
    print(f"checked {checked} frames; black-bad frames: {len(black_bad)}")
    for b in black_bad[:40]:
        print(f"  k={b[0]} oracle_f={b[1]} recomp_black={b[2]:.2f} oracle_black={b[3]:.2f} mean_diff={b[4]:.1f}")
    print(f"report: {out}")


if __name__ == "__main__":
    main()
