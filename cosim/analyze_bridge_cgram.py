#!/usr/bin/env python3
"""Bridge diagnostic v2: dump CGRAM colors + PPU summary around the bridge scene,
aligned by palette signature, comparing recomp (A) vs bsnes (B)."""
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
    frame = struct.unpack_from("<I", rec, 0)[0]
    wram = rec[WRAM_O:WRAM_O + 0x20000]
    cgram = rec[CGRAM_O:CGRAM_O + 0x200]
    ppu = rec[PPU_O:MASK_O]
    dev = rec[DEV_O:PPU_O]
    return dict(frame=frame, wram=wram, cgram=cgram, ppu=ppu, dev=dev)

def nz_pal(wram):
    pal = wram[D873:D873 + 0x40]
    return sum(1 for b in pal if b)

def cgram_colors(cgram, lo=0, hi=0x100):
    return [(i, cgram[i*2] | (cgram[i*2+1] << 8)) for i in range(lo, hi)
            if cgram[i*2] or cgram[i*2+1]]

def ppu_brief(ppu):
    inidisp = ppu[0]
    bgmode = ppu[4]
    bgXsc = list(ppu[6:10])
    bgTile = struct.unpack_from("<H", ppu, 10)[0]
    setini = ppu[13]
    hScroll = [struct.unpack_from("<H", ppu, 14 + 2*i)[0] for i in range(4)]
    vScroll = [struct.unpack_from("<H", ppu, 22 + 2*i)[0] for i in range(4)]
    return f"inidisp={inidisp:02X} bgmode={bgmode} bgXsc={[f'{x:02X}' for x in bgXsc]} bgTile={bgTile:04X} setini={setini:02X} hS={[f'{x:04X}' for x in hScroll]} vS={[f'{x:04X}' for x in vScroll]}"

def main():
    pa, pb = sys.argv[1], sys.argv[2]
    fa, fb = frames(pa), frames(pb)
    # collect palette-signature frames in range [3100, 3300) for both sides
    sigA, sigB = [], []
    cgramA, cgramB = {}, {}
    ppuA, ppuB = {}, {}
    devA, devB = {}, {}
    allA, allB = [], []
    while True:
        try:
            ra = parse(next(fa))
        except StopIteration:
            break
        try:
            rb = parse(next(fb))
        except StopIteration:
            break
        allA.append(ra); allB.append(rb)
        if 3100 <= ra["frame"] < 3300:
            sigA.append((ra["frame"], nz_pal(ra["wram"])))
            cgramA[ra["frame"]] = ra["cgram"]
            ppuA[ra["frame"]] = ra["ppu"]
            devA[ra["frame"]] = ra["dev"]
        if 3100 <= rb["frame"] < 3300:
            sigB.append((rb["frame"], nz_pal(rb["wram"])))
            cgramB[rb["frame"]] = rb["cgram"]
            ppuB[rb["frame"]] = rb["ppu"]
            devB[rb["frame"]] = rb["dev"]

    print("=== palette $D873 nonzero-bytes signature, frames 3100-3299 ===")
    print("  A(so):   ", " ".join(f"{fr}:{nz}" for fr, nz in sigA if nz))
    print("  B(bsnes):", " ".join(f"{fr}:{nz}" for fr, nz in sigB if nz))

    # find the 'settled bridge' frame: max nonzero palette in range
    def settle(sig):
        return max(sig, key=lambda t: t[1])[0] if sig else None
    fA, fB = settle(sigA), settle(sigB)
    print(f"\n=== settled-bridge frame (max palette): A={fA} B={fB} ===")
    for name, fr, cg, pp, dv in (("A(so)", fA, cgramA, ppuA, devA), ("B(bsnes)", fB, cgramB, ppuB, devB)):
        if fr is None: continue
        cols = cgram_colors(cg[fr], 0, 0x80)
        cols_f0 = cgram_colors(cg[fr], 0xF0, 0x100)
        print(f"  {name} frame {fr}:")
        print(f"    PPU: {ppu_brief(pp[fr])}")
        print(f"    BG palette (0-127): {len(cols)} colors -> {cols[:12]}")
        print(f"    CGRAM $F0-$FF: {len(cols_f0)} colors -> {cols_f0[:12]}")
        print(f"    WRAM $D873 nz bytes: {nz_pal(allA[fr].get('wram') if name.startswith('A') else allB[fr]['wram'])}")
    # PPU summary for the frames around the transition (2828-2908 fade-out)
    print("\n=== PPU at fade-out (frame 2860) and settled (frame 3187±) ===")
    for name, d, pp in (("A", devA, ppuA), ("B", devB, ppuB)):
        for fr in (2860, 3187, 3190, 3200):
            if fr in pp:
                print(f"  {name} frame {fr}: {ppu_brief(pp[fr])}")

if __name__ == "__main__":
    main()
