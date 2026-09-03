#!/usr/bin/env python3
"""Decode VRAM dump into visual representation of tiles and tilemaps."""
import struct, sys, os

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "ppu_dump.bin")
if len(sys.argv) > 1:
    path = sys.argv[1]

with open(path, "rb") as f:
    data = f.read()

vram = data[:0x10000]  # 64KB VRAM
cgram = data[0x10000:0x100200]  # 512B CGRAM

words = struct.unpack_from(f"<{len(vram)//2}H", vram)

# PPU state from dump
bgmode = 0
bgXsc = [0x48, 0x4C, 0x50, 0x58]
bgTileAdr = 0x4222

def get_tilemap_addr(layer):
    return (bgXsc[layer] & 0xfc) << 8

def get_tile_addr(layer):
    return ((bgTileAdr >> (layer * 4)) & 0xf) << 12

def snes_color_to_rgb(lo, hi):
    c = lo | (hi << 8)
    r5 = c & 0x1F
    g5 = (c >> 5) & 0x1F
    b5 = (c >> 10) & 0x1F
    return ((r5 << 3) | (r5 >> 2), (g5 << 3) | (g5 >> 2), (b5 << 3) | (b5 >> 2))

def decode_4bpp_tile(word_data, palette_idx, cgram_data):
    """Decode a 4bpp tile (32 bytes = 16 words) to 8x8 pixels."""
    pixels = []
    for row in range(8):
        bp12 = word_data[row]      # bitplanes 1-2
        bp34 = word_data[row + 8]  # bitplanes 3-4
        row_pixels = []
        for bit in range(7, -1, -1):
            p0 = (bp12 >> bit) & 1
            p1 = (bp12 >> (bit + 8)) & 1
            p2 = (bp34 >> bit) & 1
            p3 = (bp34 >> (bit + 8)) & 1
            color_idx = p0 | (p1 << 1) | (p2 << 2) | (p3 << 3)
            cgram_offset = palette_idx * 16 + color_idx
            if cgram_offset * 2 + 1 < len(cgram_data):
                lo = cgram_data[cgram_offset * 2]
                hi = cgram_data[cgram_offset * 2 + 1]
                row_pixels.append(snes_color_to_rgb(lo, hi))
            else:
                row_pixels.append((0, 0, 0))
        pixels.append(row_pixels)
    return pixels

def decode_2bpp_tile(word_data, palette_idx, cgram_data):
    """Decode a 2bpp tile (16 bytes = 8 words) to 8x8 pixels."""
    pixels = []
    for row in range(8):
        bp1 = word_data[row]       # bitplanes 1-2
        row_pixels = []
        for bit in range(7, -1, -1):
            p0 = (bp1 >> bit) & 1
            p1 = (bp1 >> (bit + 8)) & 1
            color_idx = p0 | (p1 << 1)
            cgram_offset = palette_idx * 4 + color_idx
            if cgram_offset * 2 + 1 < len(cgram_data):
                lo = cgram_data[cgram_offset * 2]
                hi = cgram_data[cgram_offset * 2 + 1]
                row_pixels.append(snes_color_to_rgb(lo, hi))
            else:
                row_pixels.append((0, 0, 0))
        pixels.append(row_pixels)
    return pixels

# Write PPM images for each BG layer
for layer in range(4):
    tm_addr = get_tilemap_addr(layer)
    td_addr = get_tile_addr(layer)
    is_2bpp = layer >= 2  # BG3/BG4 are 2bpp in Mode 0
    
    print(f"\n=== BG{layer+1}: tilemap @ ${tm_addr:04X}, tiles @ ${td_addr:04X}, {'2bpp' if is_2bpp else '4bpp'} ===")
    
    # Read tilemap (32x32 tiles = 1024 words)
    # Render as 256x256 pixel image (32 tiles * 8 pixels)
    img = [[(0,0,0)] * 256 for _ in range(256)]
    
    tiles_used = set()
    for ty in range(32):
        for tx in range(32):
            tm_word_idx = tm_addr + ty * 32 + tx
            if tm_word_idx >= len(words):
                continue
            entry = words[tm_word_idx]
            if entry == 0:
                continue
            
            tile_num = entry & 0x03FF
            palette = (entry >> 10) & 7
            hflip = (entry >> 14) & 1
            vflip = (entry >> 15) & 1
            
            tiles_used.add(tile_num)
            
            if is_2bpp:
                tile_word_off = td_addr + tile_num * 8  # 8 words per 2bpp tile
                if tile_word_off + 8 > len(words):
                    continue
                tile_data = words[tile_word_off:tile_word_off + 8]
                pixels = decode_2bpp_tile(tile_data, palette, cgram)
            else:
                tile_word_off = td_addr + tile_num * 16  # 16 words per 4bpp tile
                if tile_word_off + 16 > len(words):
                    continue
                tile_data = words[tile_word_off:tile_word_off + 16]
                pixels = decode_4bpp_tile(tile_data, palette, cgram)
            
            # Copy to image
            for py in range(8):
                for px in range(8):
                    sx = tx * 8 + (7 - px if hflip else px)
                    sy = ty * 8 + (7 - py if vflip else py)
                    if 0 <= sx < 256 and 0 <= sy < 256:
                        img[sy][sx] = pixels[py][px]
    
    # Write PPM
    ppm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"bg{layer+1}_tiles.ppm")
    with open(ppm_path, "wb") as f:
        f.write(f"P6\n256 256\n255\n".encode())
        for row in img:
            for r, g, b in row:
                f.write(bytes([r, g, b]))
    
    print(f"  Tiles used: {len(tiles_used)} unique")
    print(f"  Tile range: {min(tiles_used) if tiles_used else 0}-{max(tiles_used) if tiles_used else 0}")
    print(f"  Saved: {ppm_path}")
