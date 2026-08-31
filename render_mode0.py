#!/usr/bin/env python3
"""Render BG layers from ppu_dump.bin using correct Mode 0 palette mapping."""
import struct, sys

with open("build/saves/ppu_dump.bin", "rb") as f:
    data = f.read()

# Parse VRAM (32768 uint16 words = 65536 bytes)
vram = struct.unpack("<32768H", data[:0x10000])
# Parse CGRAM (256 uint16 words = 512 bytes)
cgram = struct.unpack("<256H", data[0x10000:0x10000+0x200])

def snes15_to_rgb(c):
    r = min(((c & 0x1f) * 255) // 31, 255)
    g = min((((c>>5) & 0x1f) * 255) // 31, 255)
    b = min((((c>>10) & 0x1f) * 255) // 31, 255)
    return (r, g, b)

# Mode 0 layout: bgTileAdr=$4222
# BG1/BG2 tiles @ $2000 (4bpp), BG3 tiles @ $2000 (2bpp), BG4 tiles @ $4000 (2bpp)
# BG1 tilemap @ $4800, BG2 @ $4C00, BG3 @ $5000, BG4 @ $5800
tilemaps = {1: 0x4800, 2: 0x4C00, 3: 0x5000, 4: 0x5800}
tile_bases = {1: 0x2000, 2: 0x2000, 3: 0x2000, 4: 0x4000}
bpp = {1: 4, 2: 4, 3: 2, 4: 2}

# Mode 0 palette mapping (after & 0xff truncation in compositing):
# BG1: cgram[0-127], BG2: cgram[128-255], BG3: cgram[0-31], BG4: cgram[128-159]
pal_base = {1: 0, 2: 0x80, 3: 0, 4: 0x80}

def read_4bpp_tile(vram, base_addr, tile_num):
    addr = (base_addr + tile_num * 16) & 0x7FFF
    pixels = [[0]*8 for _ in range(8)]
    for row in range(8):
        w0 = vram[(addr + row) & 0x7FFF]
        w1 = vram[(addr + 8 + row) & 0x7FFF]
        for col in range(8):
            bit = 7 - col
            p = ((w0>>bit)&1) | (((w0>>(bit+8))&1)<<1) | (((w1>>bit)&1)<<2) | (((w1>>(bit+8))&1)<<3)
            pixels[row][col] = p
    return pixels

def read_2bpp_tile(vram, base_addr, tile_num):
    addr = (base_addr + tile_num * 8) & 0x7FFF
    pixels = [[0]*8 for _ in range(8)]
    for row in range(8):
        w = vram[(addr + row) & 0x7FFF]
        for col in range(8):
            bit = 7 - col
            p = ((w>>bit)&1) | (((w>>(bit+8))&1)<<1)
            pixels[row][col] = p
    return pixels

# Check how many non-zero tiles each BG has
print("=== Tile data analysis ===")
for bg in [1,2,3,4]:
    base = tile_bases[bg]
    b = bpp[bg]
    words_per_tile = 16 if b == 4 else 8
    nz_tiles = 0
    for t in range(512):
        addr = base + t * words_per_tile
        has_data = False
        for w in range(words_per_tile):
            if vram[(addr + w) & 0x7FFF] != 0:
                has_data = True
                break
        if has_data:
            nz_tiles += 1
    print(f"  BG{bg} ({b}bpp) @{base:04X}: {nz_tiles} non-zero tiles out of 512")

# Check which tiles the tilemaps actually reference
print("\n=== Tilemap → tile analysis ===")
for bg in [1,2,3,4]:
    tm = tilemaps[bg]
    b = bpp[bg]
    base = tile_bases[bg]
    words_per_tile = 16 if b == 4 else 8
    referenced = set()
    for i in range(1024):
        entry = vram[(tm + i) & 0x7FFF]
        if entry == 0:
            continue
        tile_num = entry & 0x3FF
        referenced.add(tile_num)
    
    nz_in_ref = 0
    empty_in_ref = 0
    for t in sorted(referenced):
        addr = base + t * words_per_tile
        has_data = any(vram[(addr+w) & 0x7FFF] != 0 for w in range(words_per_tile))
        if has_data:
            nz_in_ref += 1
        else:
            empty_in_ref += 1
    
    print(f"  BG{bg}: {len(referenced)} unique tiles referenced, {nz_in_ref} have data, {empty_in_ref} EMPTY")

# Render BG2 as it has the most data
print("\n=== Rendering BG2 as PPM ===")
img = [[(0,0,0)]*256 for _ in range(224)]
for ty in range(32):
    for tx in range(32):
        entry = vram[(tilemaps[2] + ty*32 + tx) & 0x7FFF]
        if entry == 0:
            continue
        tile_num = entry & 0x3FF
        pal = (entry >> 10) & 7
        hflip = bool(entry & 0x4000)
        vflip = bool(entry & 0x8000)
        
        pixels = read_4bpp_tile(vram, tile_bases[2], tile_num)
        cgram_base = pal_base[2] + pal * 16
        
        for py in range(8):
            for px in range(8):
                src_px = px if not hflip else 7-px
                src_py = py if not vflip else 7-py
                p = pixels[src_py][src_px]
                if p == 0:
                    continue
                ci = cgram_base + p
                color = snes15_to_rgb(cgram[ci & 0xFF]) if ci < 256 else (255,0,255)
                sx = (tx*8 + px) % 256
                sy = (ty*8 + py) % 224
                img[sy][sx] = color

with open("bg2_mode0.ppm", "wb") as f:
    f.write(f"P6\n256 224\n255\n".encode())
    for row in img:
        for r,g,b in row:
            f.write(bytes([r,g,b]))
print("  -> bg2_mode0.ppm")
print("\nDone! Open bg2_mode0.ppm to see what BG2 looks like with current VRAM data.")
