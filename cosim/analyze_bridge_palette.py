#!/usr/bin/env python3
"""Track-B bridge diagnostic: extract WRAM $D873 palette buffer + CGRAM from both
state files frame by frame, find the first divergence, and dump the timeline."""
import struct, sys

MAGIC = b"SOCO"
REC = 197238
CPU_O = 4
DEV_O = CPU_O + 18
PPU_O = DEV_O + 16
MASK_O = PPU_O + 66
SDD1_O = MASK_O + 8
WRAM_O = SDD1_O + 6
VRAM_O = WRAM_O + 0x20000
CGRAM_O = VRAM_O + 0x10000

D873 = 0xD873          # palette staging buffer start (WRAM offset)
PAL_LEN = 0x41         # D873..D8B3 (32 colors = 64 bytes) + a bit
CGR_F0 = 0xF0 * 2      # CGRAM colors $F0-$FF used by the bridge palette

def read_frames(path):
    with open(path, "rb") as f:
        if f.read(4) != MAGIC:
            raise SystemExit(f"{path}: bad magic")
        ver, rsz = struct.unpack("<II", f.read(8))
        if rsz != REC:
            raise SystemExit(f"{path}: recordSize {rsz} != {REC}")
        while True:
            rec = f.read(REC)
            if not rec:
                return
            yield rec

def parse(rec):
    frame = struct.unpack_from("<I", rec, 0)[0]
    wram = rec[WRAM_O:WRAM_O + 0x20000]
    cgram = rec[CGRAM_O:CGRAM_O + 0x200]
    cpu = rec[CPU_O:DEV_O]
    dev = rec[DEV_O:PPU_O]
    # A (2B), X (2B), Y (2B), S (2B), D (2B), DB, P, E, pad
    A = struct.unpack_from("<H", cpu, 0)[0]
    X = struct.unpack_from("<H", cpu, 2)[0]
    Y = struct.unpack_from("<H", cpu, 4)[0]
    S = struct.unpack_from("<H", cpu, 6)[0]
    P = cpu[11]
    hPos = struct.unpack_from("<H", dev, 0)[0]
    vPos = struct.unpack_from("<H", dev, 2)[0]
    return dict(frame=frame, wram=wram, cgram=cgram, A=A, X=X, Y=Y, S=S, P=P, hPos=hPos, vPos=vPos)

def pal_summary(wram):
    """Return (nonzero_bytes, first_blue_pair) over the D873..D8B3 region."""
    pal = wram[D873:D873 + 0x40]
    nz = sum(1 for b in pal if b != 0)
    # look for a '42 08' (dark blue) or similar non-zero color pair
    pairs = [i for i in range(0, len(pal) - 1, 2) if pal[i] or pal[i+1]]
    return nz, pairs[:3]

def cgram_summary(cgram, start=0xF0):
    cols = []
    for i in range(start, 0x100):
        lo = cgram[i*2]; hi = cgram[i*2+1]
        if lo or hi:
            cols.append((i, lo | (hi << 8)))
    return cols

def main():
    pa, pb = sys.argv[1], sys.argv[2]
    fa, fb = read_frames(pa), read_frames(pb)
    ra = rb = None
    first_diff = None
    timeline = []
    n = 0
    while True:
        try:
            ra = parse(next(fa))
        except StopIteration:
            break
        try:
            rb = parse(next(fb))
        except StopIteration:
            break
        if ra["frame"] != rb["frame"]:
            print(f"frame index drift at {n}: A={ra['frame']} B={rb['frame']}")
            break
        nzA, pairsA = pal_summary(ra["wram"])
        nzB, pairsB = pal_summary(rb["wram"])
        palA = ra["wram"][D873:D873+0x40]
        palB = rb["wram"][D873:D873+0x40]
        if palA != palB and first_diff is None:
            first_diff = ra["frame"]
            print(f"=== FIRST PALETTE ($D873) DIVERGENCE at frame {ra['frame']} ===")
            print(f"  A(so): nz={nzA} pairs={pairsA}")
            print(f"  B(bsnes): nz={nzB} pairs={pairsB}")
            print(f"  A bytes: {palA[:16].hex(' ')}")
            print(f"  B bytes: {palB[:16].hex(' ')}")
            print(f"  A cpu A={ra['A']:04X} X={ra['X']:04X} S={ra['S']:04X} P={ra['P']:02X} hPos={ra['hPos']:04X} vPos={ra['vPos']:04X}")
            print(f"  B cpu A={rb['A']:04X} X={rb['X']:04X} S={rb['S']:04X} P={rb['P']:02X} hPos={rb['hPos']:04X} vPos={rb['vPos']:04X}")
        # record interesting transitions (nonzero palette state changes)
        if (nzA > 0) != (nzB > 0) or (nzA and nzB and pairsA != pairsB):
            if not timeline or timeline[-1][1] != (nzA, nzB):
                timeline.append((ra["frame"], (nzA, nzB), pairsA, pairsB))
        # CGRAM divergence at the palette slots
        cgA = cgram_summary(ra["cgram"])
        cgB = cgram_summary(rb["cgram"])
        if (bool(cgA) != bool(cgB)) and (ra["frame"] > 1200):
            if not timeline or (timeline[-1][1] != (nzA, nzB)):
                pass
        n += 1
        if n % 500 == 0:
            pass
    print(f"\n=== processed {n} frames ===")
    if first_diff is None:
        print("NO palette divergence found — $D873 identical between A and B all frames")
    print("\n=== palette nonzero-bytes timeline (A vs B), frames > 1000 ===")
    for fr, (nzA, nzB), pA, pB in timeline:
        if fr > 1000:
            mark = " <-- DIVERGE" if nzA != nzB else ""
            print(f"  frame {fr:5d}: A nz={nzA:3d} B nz={nzB:3d}  A pairs={pA} B pairs={pB}{mark}")

if __name__ == "__main__":
    main()
