#!/usr/bin/env python3
"""Bridge diagnostic v3: measure the WRAM palette offset (cross-correlation),
full CGRAM byte diff, and the BG tilemap VRAM content diff in the settled frame."""
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

def cross_corr(palA, palB, maxoff=64):
    """Best shift s (B shifted right by s => matches A) minimizing diff."""
    best = None
    for s in range(0, maxoff):
        # compare A[x] vs B[x-s] for x>=s (B's palette written s bytes later)
        diff = sum(1 for x in range(s, len(palA)) if palA[x] != palB[x - s])
        if best is None or diff < best[1]:
            best = (s, diff)
    return best

def main():
    pa, pb = sys.argv[1], sys.argv[2]
    fa, fb = frames(pa), frames(pb)
    offs = []
    while True:
        try:
            ra = parse(next(fa))
        except StopIteration:
            break
        try:
            rb = parse(next(fb))
        except StopIteration:
            break
        fr = ra["frame"]
        if 1200 <= fr <= 2100:
            palA = ra["wram"][D873:D873 + 0x40]
            palB = rb["wram"][D873:D873 + 0x40]
            if any(palA) and any(palB):
                s, d = cross_corr(palA, palB)
                offs.append((fr, s, d))
        if fr in (3141, 3164, 3187, 3200):
            # CGRAM full diff
            cgA, cgB = ra["cgram"], rb["cgram"]
            diffb = [i for i in range(0, 0x200, 2)
                     if cgA[i] != cgB[i] or cgA[i+1] != cgB[i+1]]
            # VRAM BG tilemap diff at tilemap addr from ppu
            bgTile = struct.unpack_from("<H", ra["ppu"], 10)[0]
            tmA = (bgTile & 0x000F) << 12
            tmB = (struct.unpack_from("<H", rb["ppu"], 10)[0] & 0x000F) << 12
            vA = ra["vram"]; vB = rb["vram"]
            nA = sum(1 for i in range(tmA, tmA + 0x800, 2) if vA[i] or vA[i+1])
            nB = sum(1 for i in range(tmB, tmB + 0x800, 2) if vB[i] or vB[i+1])
            nA_full = sum(1 for i in range(0, 0x10000, 2) if vA[i] or vA[i+1])
            nB_full = sum(1 for i in range(0, 0x10000, 2) if vB[i] or vB[i+1])
            print(f"\n=== frame {fr} ===  (A idx {ra['frame']} B idx {rb['frame']})")
            print(f"  bgTile A={bgTile:04X} ($210B={bgTile&0xFF:02X} $210C={(bgTile>>8)&0xFF:02X})"
                  f"  B={struct.unpack_from('<H', rb['ppu'],10)[0]:04X}")
            print(f"  CGRAM diffs: {len(diffb)} words of 256  (first 12: "
                  f"{[f'${i//2:03X}' for i in diffb[:12]]})")
            print(f"  VRAM nonzero words A tilemap@{tmA:04X}: {nA}  B tilemap@{tmB:04X}: {nB}")
            print(f"  VRAM nonzero words full: A={nA_full} B={nB_full}")
    if offs:
        print("\n=== WRAM $D873 palette offset (B lagging by N bytes) ===")
        from collections import Counter
        c = Counter(s for _, s, _ in offs)
        print("  most common offsets:", c.most_common(5))
        # show a few samples
        for fr, s, d in offs[:8]:
            print(f"  frame {fr}: offset={s} bytes (diff={d})")

if __name__ == "__main__":
    main()
