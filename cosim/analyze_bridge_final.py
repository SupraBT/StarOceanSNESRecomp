#!/usr/bin/env python3
"""Bridge diagnostic v4: signature-aligned comparison (A@settle vs B@settle).
Dumps the tiledata VRAM regions for both $210B/$210C interpretations and the
full BG CGRAM palette, to decide which base is correct."""
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

D873 = 0xD873

def frames(path):
    with open(path, "rb") as f:
        if f.read(4) != MAGIC:
            raise SystemExit(f"{path}: bad magic")
        ver, rsz = struct.unpack("<II", f.read(8))
        assert rsz == REC
        while True:
            rec = f.read(REC)
            if not rec:
                return
            yield rec

def parse(rec):
    return dict(
        frame=struct.unpack_from("<I", rec, 0)[0],
        wram=rec[WRAM_O:WRAM_O + 0x20000],
        vram=rec[VRAM_O:CGRAM_O],
        cgram=rec[CGRAM_O:CGRAM_O + 0x200],
        ppu=rec[PPU_O:MASK_O],
    )

def nz_pal(w):
    return sum(1 for b in w[D873:D873 + 0x40] if b)

def main():
    pa, pb = sys.argv[1], sys.argv[2]
    fa, fb = frames(pa), frames(pb)
    settleA = settleB = None
    recA = recB = {}
    while True:
        try:
            ra = parse(next(fa))
        except StopIteration:
            break
        try:
            rb = parse(next(fb))
        except StopIteration:
            break
        recA[ra["frame"]] = ra
        recB[rb["frame"]] = rb
        if 3141 <= ra["frame"] <= 3150 and settleA is None:
            if nz_pal(ra["wram"]) >= 11:
                settleA = ra["frame"]
        if 3164 <= rb["frame"] <= 3180 and settleB is None:
            if nz_pal(rb["wram"]) >= 11:
                settleB = rb["frame"]
        if settleA and settleB:
            break
    if not settleA or not settleB:
        print("settle frames not found"); return
    print(f"settled: A@{settleA} B@{settleB}  (delta {settleB - settleA} frames)")
    ra, rb = recA[settleA], recB[settleB]

    for name, r in (("A(so)", ra), ("B(bsnes)", rb)):
        ppu = r["ppu"]
        bgTile = struct.unpack_from("<H", ppu, 10)[0]
        bgXsc = list(ppu[6:10])
        print(f"\n=== {name} frame {r['frame']} ===")
        print(f"  $210B/$210C (bgTileAdr) = {bgTile:04X} -> per-layer tiledata:")
        for i in range(4):
            print(f"    BG{i}: tilemap=${(bgXsc[i] & 0xfc) << 8:04X}  tiledata=${(bgTile >> (i*4) & 0xf) << 12:04X}")
    # VRAM tiledata regions: dump nonzero counts for both interpretations
    vA, vB = ra["vram"], rb["vram"]
    print("\n=== VRAM tiledata region nonzero words (A vs B) ===")
    for base in (0x0000, 0x1000, 0x2000, 0x4000, 0x8000):
        nA = sum(1 for i in range(base, base + 0x1000, 2) if vA[i] or vA[i+1])
        nB = sum(1 for i in range(base, base + 0x1000, 2) if vB[i] or vB[i+1])
        print(f"  ${base:04X}-${base+0xFFF:04X}: A={nA:5d} B={nB:5d}")
    # CGRAM BG palette comparison
    print("\n=== CGRAM BG palette (0-127) ===")
    for name, r in (("A(so)", ra), ("B(bsnes)", rb)):
        cg = r["cgram"]
        cols = [(i, cg[i*2] | (cg[i*2+1] << 8)) for i in range(0, 128) if cg[i*2] or cg[i*2+1]]
        print(f"  {name}: {len(cols)} colors  first 16: {cols[:16]}")
    # WRAM $D873 staging (identical?)
    palA = ra["wram"][D873:D873+0x40]
    palB = rb["wram"][D873:D873+0x40]
    print(f"\n  WRAM $D873 staging identical: {palA == palB}")
    if palA != palB:
        for i in range(0x40):
            if palA[i] != palB[i]:
                print(f"    first diff at +{i:02X}: A={palA[i]:02X} B={palB[i]:02X}")
                break

if __name__ == "__main__":
    main()
