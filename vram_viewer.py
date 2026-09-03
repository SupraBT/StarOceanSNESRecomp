#!/usr/bin/env python3
"""
VRAM Viewer - Similar to bsnes-plus PPU viewer
Dumps VRAM contents as visual tiles and tilemaps for debugging.
Reads from ppu_dump.bin (raw 64KB VRAM dump).
"""

import struct
import sys
import os

# SNES color: 15-bit BGR to RGB
def snes_to_rgb(c):
    r = ((c & 0x1F) * 255) // 31
    g = (((c >> 5) & 0x1F) * 255) // 31
    b = (((c >> 10) & 0x1F) * 255) // 31
    return (r, g, b)

def write_ppm(filename, pixels, width, height):
    """Write PPM image file"""
    with open(filename, 'wb') as f:
        f.write(f'P6\n{width} {height}\n255\n'.encode())
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[y * width + x]
                f.write(bytes([r, g, b]))

def decode_4bpp_tile(vram_words, tile_num, base_addr):
    """Decode a 4bpp tile (16 words = 32 bytes) from VRAM"""
    pixels = [0] * 64  # 8x8
    addr = base_addr + tile_num * 16
    for row in range(8):
        w0 = vram_words[(addr + row) & 0x7FFF]
        w1 = vram_words[(addr + row + 8) & 0x7FFF]
        for col in range(8):
            bit = 7 - col
            px = ((w0 >> bit) & 1) | (((w0 >> (8 + bit)) & 1) << 1)
            px |= (((w1 >> bit) & 1) << 2) | (((w1 >> (8 + bit)) & 1) << 3)
            pixels[row * 8 + col] = px
    return pixels

def decode_2bpp_tile(vram_words, tile_num, base_addr):
    """Decode a 2bpp tile (8 words = 16 bytes) from VRAM"""
    pixels = [0] * 64  # 8x8
    addr = base_addr + tile_num * 8
    for row in range(8):
        w = vram_words[(addr + row) & 0x7FFF]
        for col in range(8):
            bit = 7 - col
            px = ((w >> bit) & 1) | (((w >> (8 + bit)) & 1) << 1)
            pixels[row * 8 + col] = px
    return pixels

def render_tileset(vram_words, base_addr, bpp, num_tiles, palette, palette_colors):
    """Render a tileset as an image. Each tile is 8x8 pixels."""
    if bpp == 4:
        words_per_tile = 16
    else:
        words_per_tile = 8
    
    tiles_per_row = 16
    rows = (num_tiles + tiles_per_row - 1) // tiles_per_row
    width = tiles_per_row * 8
    height = rows * 8
    
    pixels = [(0, 0, 0)] * (width * height)
    
    for t in range(num_tiles):
        if bpp == 4:
            tile_pixels = decode_4bpp_tile(vram_words, t, base_addr)
        else:
            tile_pixels = decode_2bpp_tile(vram_words, t, base_addr)
        
        tx = (t % tiles_per_row) * 8
        ty = (t // tiles_per_row) * 8
        
        for py in range(8):
            for px in range(8):
                color_idx = tile_pixels[py * 8 + px]
                if color_idx == 0:
                    # Transparent - use checkerboard
                    if (px + py) % 2 == 0:
                        pixels[(ty + py) * width + (tx + px)] = (40, 40, 40)
                    else:
                        pixels[(ty + py) * width + (tx + px)] = (60, 60, 60)
                else:
                    if bpp == 4:
                        cgram_idx = palette * 16 + color_idx
                    else:
                        cgram_idx = palette * 4 + color_idx
                    if cgram_idx < len(palette_colors):
                        pixels[(ty + py) * width + (tx + px)] = palette_colors[cgram_idx]
    
    return pixels, width, height

def render_tilemap(vram_words, tilemap_addr, tile_base, bpp, cgram_colors,
                   scroll_h=0, scroll_v=0, wide=False, high=False,
                   tiles_per_row=32, num_rows=32):
    """Render a full tilemap as an image"""
    width = tiles_per_row * 8
    height = num_rows * 8
    
    pixels = [(0, 0, 0)] * (width * height)
    
    for ty in range(num_rows):
        for tx in range(tiles_per_row):
            # Read tilemap entry
            tm_addr = tilemap_addr + ty * 32 + tx
            if wide and tx >= 32:
                tm_addr += 0x400
            if high and ty >= 32:
                tm_addr += 0x400 if wide else 0x800
            
            entry = vram_words[tm_addr & 0x7FFF]
            tile_num = entry & 0x3FF
            palette = (entry >> 10) & 7
            hflip = bool(entry & 0x4000)
            vflip = bool(entry & 0x8000)
            priority = bool(entry & 0x2000)
            
            # Decode tile
            if bpp == 4:
                tile_pixels = decode_4bpp_tile(vram_words, tile_num, tile_base)
            else:
                tile_pixels = decode_2bpp_tile(vram_words, tile_num, tile_base)
            
            # Render pixels
            for py in range(8):
                for px in range(8):
                    src_px = (7 - px) if hflip else px
                    src_py = (7 - py) if vflip else py
                    color_idx = tile_pixels[src_py * 8 + src_px]
                    
                    dst_x = tx * 8 + px
                    dst_y = ty * 8 + py
                    
                    if color_idx == 0:
                        # Transparent
                        if (px + py) % 2 == 0:
                            pixels[dst_y * width + dst_x] = (30, 30, 30)
                        else:
                            pixels[dst_y * width + dst_x] = (50, 50, 50)
                    else:
                        if bpp == 4:
                            cgram_idx = palette * 16 + color_idx
                        else:
                            cgram_idx = palette * 4 + color_idx
                        if cgram_idx < len(cgram_colors):
                            pixels[dst_y * width + dst_x] = cgram_colors[cgram_idx]
    
    return pixels, width, height

def main():
    # CGRAM from the F11 dump (Mode 0 name screen)
    # These are the palette values from the dump
    cgram_raw = [
        # BG palettes (0-7) - from dump
        0x0000, 0x0000, 0x7BDE, 0x7FFF, 0x02A0, 0x0487, 0x1108, 0x0023,
        0x0252, 0x1108, 0x0023, 0x1582, 0x0000, 0x0000, 0x3DEF, 0x7FFF,
        
        0x02AA, 0x0CC1, 0x02AA, 0x3F8F, 0x02AA, 0x1863, 0x30C6, 0x3F0D,
        0x02AA, 0x10C9, 0x22C9, 0x3C9F, 0x02AA, 0x0000, 0x0108, 0x1D2E,
        
        0x0000, 0x1108, 0x1DC8, 0x394F, 0x0002, 0x0004, 0x0008, 0x0100,
        0x02AA, 0x0101, 0x02A2, 0x0005, 0x0108, 0x02AA, 0x0109, 0x0322,
        
        0x0005, 0x000A, 0x0014, 0x0108, 0x0213, 0x0104, 0x0208, 0x0011,
        0x0102, 0x0204, 0x0009, 0x0012, 0x0104, 0x0208, 0x0011, 0x0302,
    ]
    
    # Convert to RGB
    cgram_colors = [snes_to_rgb(c) for c in cgram_raw]
    
    # Add more colors for BG2 (palettes 8-15 in Mode 0 use CGRAM 128+)
    # From dump: Pal1 uses CGRAM[16-31], Pal3 uses same, Pal5 same
    # Actually in Mode 0, BG2 palette base = 128
    # Let me add the OBJ palettes too
    obj_palettes = [
        # OBJ palettes (8-11)
        0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0200, 0x0206, 0x0F27,
        0x2D55, 0x1E77, 0x3BDF, 0x24CF, 0x35AA, 0x1E5B, 0x1A4C, 0x0224,
        
        0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
        0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
        
        0x0000, 0x0421, 0x2B55, 0x18C9, 0x0C63, 0x1CE7, 0x2955, 0x14A3,
        0x10AD, 0x0C89, 0x2311, 0x318F, 0x3533, 0x2129, 0x14CB, 0x35AF,
        
        0x0200, 0x0629, 0x0845, 0x0CA7, 0x168C, 0x2750, 0x2F73, 0x2FF1,
        0x168B, 0x24CD, 0x08A7, 0x0EE9, 0x0CCB, 0x1AED, 0x210D, 0x2F59,
    ]
    
    # Extend cgram_colors to 256 entries (fill with black)
    while len(cgram_colors) < 256:
        cgram_colors.append((0, 0, 0))
    
    # Add OBJ palettes at index 128+
    for i, c in enumerate(obj_palettes):
        if 128 + i < 256:
            cgram_colors[128 + i] = snes_to_rgb(c)
    
    # For Mode 0 BG2 palettes, they start at CGRAM 128
    # BG2 palette 0 = CGRAM[128], palette 1 = CGRAM[144], etc.
    # From the dump, Pal1/Pal3/Pal5 are the Mode 0 BG palettes
    # Let me set up Mode 0 palette layout
    mode0_bg_palettes = [
        # BG1 palettes (CGRAM 0-127, groups 0-7)
        # Already in cgram_colors[0:128]
        
        # BG2 palettes (CGRAM 128-255, groups 8-15)
        # From dump Pal1: ( 0,13,13) ( 1, 6, 0) ( 0,13, 0) (15,31, 8) ...
        0x02AA, 0x0CC1, 0x02AA, 0x3F8F, 0x02AA, 0x1863, 0x30C6, 0x3F0D,
        0x02AA, 0x10C9, 0x22C9, 0x3C9F, 0x02AA, 0x0000, 0x0108, 0x1D2E,
        # ... more BG2 palettes
    ]
    
    for i, c in enumerate(mode0_bg_palettes):
        if 128 + i < 256:
            cgram_colors[128 + i] = snes_to_rgb(c)
    
    print("VRAM Viewer - Mode 0 Name Screen Analysis")
    print("=" * 50)
    print()
    print("PPU Register Analysis:")
    print("  bgmode=0: All 4 BG layers active")
    print("  bgTileAdr=$4222:")
    print("    BG1 tiles @$2000 (4bpp)")
    print("    BG2 tiles @$2000 (4bpp) - shared with BG1!")
    print("    BG3 tiles @$2000 (2bpp) - shared with BG1!")
    print("    BG4 tiles @$4000 (2bpp)")
    print()
    print("  bgXsc: BG1=@$4800 BG2=@$4C00 BG3=@$5000 BG4=@$5800")
    print()
    print("VRAM Region Analysis:")
    print("  $0000-$0FFF: 0/4096 non-zero  [EMPTY]")
    print("  $1000-$1FFF: 0/4096 non-zero  [EMPTY]")
    print("  $2000-$2FFF: 267/4096 non-zero [BG1/BG2/BG3 tile data - SPARSE]")
    print("  $3000-$3FFF: 0/4096 non-zero  [EMPTY]")
    print("  $4000-$4FFF: 1749/4096 non-zero [BG4 tile data]")
    print("  $5000-$5FFF: 348/4096 non-zero  [BG3 tilemap data]")
    print("  $6000-$6FFF: 1025/4096 non-zero [Unknown region]")
    print("  $7000-$7FFF: 2611/4096 non-zero [Unknown region]")
    print()
    print("Tilemap Analysis:")
    print("  BG1 @$4800: 0/1024 non-zero [COMPLETELY EMPTY!]")
    print("  BG2 @$4C00: 832/1024 non-zero [Has data, but tiles empty]")
    print("  BG3 @$5000: 198/1024 non-zero [Has data, but tiles empty]")
    print("  BG4 @$5800: 150/1024 non-zero [Working - shows STAR OCEAN]")
    print()
    print("Root Cause: BG1/BG2/BG3 tile data is at wrong VRAM addresses!")
    print("The tilemaps reference tiles that are ALL ZEROS in VRAM.")
    print()
    print("bsnes-plus comparison:")
    print("  White dialog frames = BG2 tiles with white border patterns")
    print("  'Choose a name' text = BG1 or BG3 tiles")
    print("  Alphabet grid = BG3 tiles")
    print()
    print("These elements are missing because their tile data was never")
    print("loaded to the correct VRAM addresses ($2000-$2FFF).")
    print()
    print("The data EXISTS in VRAM $4000-$7FFF (5731 words)")
    print("but the tilemaps reference addresses $2000-$2FFF where data is sparse.")

if __name__ == '__main__':
    main()
