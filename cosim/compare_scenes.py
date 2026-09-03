#!/usr/bin/env python3
"""Scene-aligned pixel comparison between the recomp and the bsnes oracle.

Frame offsets drift between the two sides (the recomp's quiescent-point frame
driver runs busy sections at a different frame rate than hard frames), so we
align by VRAM content: for each recomp frame, find the oracle frame with the
smallest VRAM difference (scene fingerprint), then compare the rendered pixels.

Usage:
  compare_scenes.py <recomp_state.bin> <oracle_state.bin>
                    <recomp_pixdir> <oracle_pixdir>
                    [--min K] [--max K] [--thresh VRAM_DIFF]
"""
import sys, os, glob
import numpy as np

REC = 197238
HDR = 12
WO = 118
VO = WO + 0x20000
CO = VO + 0x10000


def load_records(path):
    data = open(path, 'rb').read()
    n = (len(data) - HDR) // REC
    out = []
    for i in range(n):
        rec = data[HDR + i * REC: HDR + (i + 1) * REC]
        k = int.from_bytes(rec[0:4], 'little')
        vram = np.frombuffer(rec, dtype='<u2', count=0x8000, offset=VO).astype(np.int16)
        out.append((k, vram, rec))
    return out


def load_recomp(path):
    d = np.frombuffer(open(path, 'rb').read(), dtype=np.uint8).reshape(224, 256, 4)
    # renderer packs byte0=B, byte1=G, byte2=R -> convert to RGB
    return d[:, :, [2, 1, 0]].astype(np.int16)


def load_oracle(path):
    d = np.frombuffer(open(path, 'rb').read(), dtype='<u2').reshape(224, -1)
    if d.shape[1] == 512:
        d = d[:, 0::2]
    # RGB555: bits 10-14=R, 5-9=G, 0-4=B
    r = ((d >> 10) & 0x1F) * 255 // 31
    g = ((d >> 5) & 0x1F) * 255 // 31
    b = ((d >> 0) & 0x1F) * 255 // 31
    return np.stack([r, g, b], axis=-1).astype(np.int16)


def main():
    recomp_state, oracle_state = sys.argv[1], sys.argv[2]
    recomp_pix, oracle_pix = sys.argv[3], sys.argv[4]
    lo, hi = 0, 10 ** 9
    if '--min' in sys.argv: lo = int(sys.argv[sys.argv.index('--min') + 1])
    if '--max' in sys.argv: hi = int(sys.argv[sys.argv.index('--max') + 1])
    thresh = int(sys.argv[sys.argv.index('--thresh') + 1]) if '--thresh' in sys.argv else 200000

    print('loading states...')
    rrec = load_records(recomp_state)
    orec = load_records(oracle_state)
    print(f'  recomp {len(rrec)} recs, oracle {len(orec)} recs')

    # Build oracle VRAM matrix for the region of interest
    oidx = [i for i, (k, v, rec) in enumerate(orec) if lo <= k <= hi]
    print(f'  oracle frames in window: {len(oidx)}')
    OV = np.stack([orec[i][1] for i in oidx])          # (m, 0x8000)
    ok = np.array([orec[i][0] for i in oidx])

    rows = []
    for rk, vram, rec in rrec:
        if rk < lo or rk > hi: continue
        d = np.abs(OV - vram[None, :]).sum(axis=1)
        j = int(d.argmin())
        f = int(ok[j])
        vdiff = int(d[j])
        rp = os.path.join(recomp_pix, f'f_{rk:05d}.raw')
        op = os.path.join(oracle_pix, f'f_{f:05d}.raw')
        if not (os.path.exists(rp) and os.path.exists(op)):
            continue
        rimg = load_recomp(rp)
        oimg = load_oracle(op)
        diff = np.abs(rimg - oimg).sum(axis=2)
        mean = float(diff.mean())
        frac = float((diff > 40).mean())
        rg = rimg.mean(axis=2)
        og = oimg.mean(axis=2)
        rblack = float((rg < 12).mean())
        oblack = float((og < 12).mean())
        bad = (rblack > 0.5) and (oblack < 0.5)
        rows.append((rk, f, vdiff, mean, frac, rblack, oblack, bad))

    print(f'compared {len(rows)} frames (VRAM thresh {thresh})')
    good = [r for r in rows if r[2] <= thresh]
    print(f'  VRAM-matched (diff<={thresh}): {len(good)}')
    badlist = [r for r in good if r[7]]
    print(f'  black-bad among matched: {len(badlist)}')
    for r in badlist[:40]:
        print(f'    k={r[0]} f={r[1]} vdiff={r[2]} mean={r[3]:.1f} frac={r[4]:.3f} rb={r[5]:.3f} ob={r[6]:.3f}')
    # stats for matched
    if good:
        import statistics
        md = [r[3] for r in good]
        print(f'  matched mean_pixdiff: median={statistics.median(md):.1f} '
              f'p90={sorted(md)[int(len(md)*0.9)]:.1f}')
    with open('scene_compare_report.txt', 'w') as fh:
        fh.write('# k oracle_f vram_diff mean_pixdiff frac_pixdiff recomp_black oracle_black bad\n')
        for r in rows:
            fh.write('%d %d %d %.1f %.3f %.3f %.3f %d\n' % r)


if __name__ == '__main__':
    main()
