#!/usr/bin/env python3
"""Analyze PPU dump: VRAM (64KB) + CGRAM (512B)."""
import struct, sys, os

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "ppu_dump.bin")
if len(sys.argv) > 1:
    path = sys.argv[1]

with open(path, "rb") as f:
    data = f.read()

print(f"Total size: {len(data)} bytes")

vram = data[:0x10000]  # 64KB VRAM
cgram = data[0x10000:0x100200]  # 512B CGRAM

# === Decode CGRAM ===
print("\n=== CGRAM (512 bytes = 256 colors) ===")
print("First 32 palette entries (BG palettes 0-7):")
for pal in range(8):  # BG palettes 0-7
    print(f"\n  Palette {pal}:", end="")
    for c in range(8):
        idx = pal * 16 + c * 2
        if idx + 1 < len(cgram):
            lo = cgram[idx]
            hi = cgram[idx + 1]
            snes_color = lo | (hi << 8)
            r5 = snes_color & 0x1F
            g5 = (snes_color >> 5) & 0x1F
            b5 = (snes_color >> 10) & 0x1F
            r8 = (r5 << 3) | (r5 >> 2)
            g8 = (g5 << 3) | (g5 >> 2)
            b8 = (b5 << 3) | (b5 >> 2)
            print(f" [{r5:2d},{g5:2d},{b5:2d}]", end="")
    print()

print("\nFirst 8 sprite palettes (8-15):")
for pal in range(8, 16):
    print(f"\n  Palette {pal}:", end="")
    for c in range(8):
        idx = pal * 16 + c * 2
        if idx + 1 < len(cgram):
            lo = cgram[idx]
            hi = cgram[idx + 1]
            snes_color = lo | (hi << 8)
            r5 = snes_color & 0x1F
            g5 = (snes_color >> 5) & 0x1F
            b5 = (snes_color >> 10) & 0x1F
            print(f" [{r5:2d},{g5:2d},{b5:2d}]", end="")
    print()

# === Decode VRAM word-addressed ===
print("\n=== VRAM Analysis ===")
# SNES VRAM is word-addressed (16-bit words)
# Read as 16-bit words
words = struct.unpack_from(f"<{len(vram)//2}H", vram)
print(f"Total VRAM words: {len(words)}")

# Check common VRAM layouts for Mode 1:
# BG1: tilemap at $0000-$07FF, tiles at $0000-$3FFF
# BG2: tilemap at $0800-$0FFF, tiles at $0000-$3FFF  
# BG3: tilemap at $1000-$17FF, tiles at $2000-$3FFF
# OBJ: tilemap at $1000-$17FF, tiles at $2000-$3FFF

# Check tilemap at $0000 (word addr)
print("\n--- BG1 Tilemap at VRAM $0000 (first 32 entries) ---")
for row in range(8):
    for col in range(16):
        waddr = row * 16 + col
        if waddr < len(words):
            entry = words[waddr]
            tile_num = entry & 0x03FF
            pal = (entry >> 10) & 7
            pri = (entry >> 13) & 3
            hflip = (entry >> 14) & 1
            vflip = (entry >> 15) & 1
            print(f" T{tile_num:4d}p{pal}", end="")
    print()

print("\n--- BG2 Tilemap at VRAM $0800 (first 32 entries) ---")
for row in range(8):
    for col in range(16):
        waddr = 0x400 + row * 16 + col  # $0800 = word addr 0x400
        if waddr < len(words):
            entry = words[waddr]
            tile_num = entry & 0x03FF
            pal = (entry >> 10) & 7
            print(f" T{tile_num:4d}p{pal}", end="")
    print()

print("\n--- BG3 Tilemap at VRAM $1000 (first 32 entries) ---")
for row in range(8):
    for col in range(16):
        waddr = 0x800 + row * 16 + col  # $1000 = word addr 0x800
        if waddr < len(words):
            entry = words[waddr]
            tile_num = entry & 0x03FF
            pal = (entry >> 10) & 7
            print(f" T{tile_num:4d}p{pal}", end="")
    print()

# Check tile data - look at first few 4bpp tiles at $0000
print("\n--- Sample 4bpp tile data at VRAM $0000 (8x8 tile) ---")
# 4bpp tile = 32 bytes (16 words) = 4 bitplanes of 8 bytes
for tile_idx in range(3):
    print(f"\nTile {tile_idx}:")
    for row in range(8):
        bp1_offset = tile_idx * 16 + row  # word offset for bitplane 1&2
        bp3_offset = tile_idx * 16 + 8 + row  # word offset for bitplane 3&4
        if bp1_offset < len(words) and bp3_offset < len(words):
            bp12 = words[bp1_offset]
            bp34 = words[bp3_offset]
            pixels = []
            for bit in range(7, -1, -1):
                p0 = (bp12 >> bit) & 1
                p1 = (bp12 >> (bit + 8)) & 1
                p2 = (bp34 >> bit) & 1
                p3 = (bp34 >> (bit + 8)) & 1
                color = p0 | (p1 << 1) | (p2 << 2) | (p3 << 3)
                pixels.append(color)
            print(f"  Row {row}: {''.join(str(p) for p in pixels)}")

# Check if tile data looks like zero or real data
print("\n--- VRAM data density check ---")
nonzero_words = sum(1 for w in words if w != 0)
print(f"Non-zero words in VRAM: {nonzero_words}/{len(words)} ({100*nonzero_words/len(words):.1f}%)")

# Check specific regions
regions = [
    ("BG1 tilemap $0000-$03FF", 0x000, 0x200),
    ("BG1 tilemap $0400-$07FF", 0x200, 0x200),
    ("BG2 tilemap $0800-$0BFF", 0x400, 0x200),
    ("BG3 tilemap $1000-$13FF", 0x800, 0x200),
    ("Tile data $0000-$1FFF", 0x0000, 0x1000),
    ("Tile data $2000-$3FFF", 0x1000, 0x1000),
    ("Tile data $4000-$5FFF", 0x2000, 0x1000),
    ("Tile data $6000-$7FFF", 0x3000, 0x1000),
]
print("\n--- VRAM region non-zero percentages ---")
for name, start, size in regions:
    region = words[start:start+size]
    nz = sum(1 for w in region if w != 0)
    print(f"  {name}: {nz}/{size} ({100*nz/size:.1f}%)")
