#!/usr/bin/env python3
"""
VRAM Visualizer - Reads ppu_dump.bin and creates tile/tilemap images.
Mode 0 specific: BG1/BG2 = 4bpp, BG3/BG4 = 2bpp.
"""

import struct
import sys
import os
import zlib

def snes_to_rgb(c):
    r = ((c & 0x1F) * 255) // 31
    g = (((c >> 5) & 0x1F) * 255) // 31
    b = (((c >> 10) & 0x1F) * 255) // 31
    return (r, g, b)

def write_ppm(filename, pixels, width, height):
    with open(filename, 'wb') as f:
        f.write(f'P6\n{width} {height}\n255\n'.encode())
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[y * width + x]
                f.write(bytes([r, g, b]))

def decode_4bpp_tile(vram_words, tile_num, base_addr):
    pixels = [0] * 64
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
    pixels = [0] * 64
    addr = base_addr + tile_num * 8
    for row in range(8):
        w = vram_words[(addr + row) & 0x7FFF]
        for col in range(8):
            bit = 7 - col
            px = ((w >> bit) & 1) | (((w >> (8 + bit)) & 1) << 1)
            pixels[row * 8 + col] = px
    return pixels

def render_tileset(vram_words, base_addr, bpp, num_tiles, cgram_colors, outfile):
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
                    if (px + py) % 2 == 0:
                        pixels[(ty + py) * width + (tx + px)] = (40, 40, 40)
                    else:
                        pixels[(ty + py) * width + (tx + px)] = (60, 60, 60)
                else:
                    if bpp == 4:
                        # Mode 0: each layer has its own palette bank
                        # This function is called per-layer, palette already offset
                        cgram_idx = color_idx  # palette already in cgram_colors
                    else:
                        cgram_idx = color_idx
                    if cgram_idx < len(cgram_colors):
                        pixels[(ty + py) * width + (tx + px)] = cgram_colors[cgram_idx]
    
    write_ppm(outfile, pixels, width, height)
    print(f"  Written: {outfile} ({width}x{height})")

def render_tilemap(vram_words, tilemap_addr, tile_base, bpp, cgram_colors, outfile, wide=False, high=False):
    tiles_per_row = 64 if wide else 32
    num_rows = 32
    width = tiles_per_row * 8
    height = num_rows * 8
    
    pixels = [(0, 0, 0)] * (width * height)
    
    non_zero = 0
    for ty in range(num_rows):
        for tx in range(tiles_per_row):
            tm_addr = tilemap_addr + (ty & 31) * 32 + (tx & 31)
            if tx >= 32 and wide:
                tm_addr += 0x400
            if ty >= 32 and high:
                tm_addr += 0x800 if wide else 0x400
            
            entry = vram_words[tm_addr & 0x7FFF]
            if entry == 0:
                # Draw checkerboard for empty
                for py in range(8):
                    for px in range(8):
                        c = (30, 30, 30) if (px//4 + py//4) % 2 == 0 else (20, 20, 20)
                        pixels[(ty * 8 + py) * width + (tx * 8 + px)] = c
                continue
            
            non_zero += 1
            tile_num = entry & 0x3FF
            palette = (entry >> 10) & 7
            hflip = bool(entry & 0x4000)
            vflip = bool(entry & 0x8000)
            
            if bpp == 4:
                tile_pixels = decode_4bpp_tile(vram_words, tile_num, tile_base)
            else:
                tile_pixels = decode_2bpp_tile(vram_words, tile_num, tile_base)
            
            for py in range(8):
                for px in range(8):
                    src_px = (7 - px) if hflip else px
                    src_py = (7 - py) if vflip else py
                    color_idx = tile_pixels[src_py * 8 + src_px]
                    
                    dst_x = tx * 8 + px
                    dst_y = ty * 8 + py
                    
                    if color_idx == 0:
                        pixels[dst_y * width + dst_x] = (30, 30, 30)
                    else:
                        if bpp == 4:
                            cgram_idx = palette * 16 + color_idx
                        else:
                            cgram_idx = palette * 4 + color_idx
                        if cgram_idx < len(cgram_colors):
                            pixels[dst_y * width + dst_x] = cgram_colors[cgram_idx]
    
    print(f"  Tilemap non-zero entries: {non_zero}/{tiles_per_row * num_rows}")
    write_ppm(outfile, pixels, width, height)
    print(f"  Written: {outfile} ({width}x{height})")

def main():
    dump_path = sys.argv[1] if len(sys.argv) > 1 else "ppu_dump.bin"
    
    if not os.path.exists(dump_path):
        print(f"File not found: {dump_path}")
        return
    
    size = os.path.getsize(dump_path)
    print(f"Reading {dump_path} ({size} bytes)")
    
    with open(dump_path, 'rb') as f:
        data = f.read()
    
    # The dump contains VRAM as 16-bit LE words
    # 66048 bytes = 33024 words (but VRAM is 32768 words = 65536 bytes)
    # The extra 512 bytes might be CGRAM or other data
    # Let's use the first 65536 bytes as VRAM
    if size >= 65536:
        vram_data = data[:65536]
    else:
        vram_data = data
    
    # Convert to 16-bit words (little-endian)
    vram_words = []
    for i in range(0, len(vram_data) - 1, 2):
        vram_words.append(struct.unpack('<H', vram_data[i:i+2])[0])
    
    # Pad to 32768 words
    while len(vram_words) < 32768:
        vram_words.append(0)
    
    print(f"VRAM: {len(vram_words)} words")
    
    # Count non-zero per 4KB region
    print("\nVRAM regions:")
    for i in range(8):
        base = i * 2048  # 4KB = 2048 words
        end = base + 2048
        nz = sum(1 for w in vram_words[base:end] if w != 0)
        print(f"  ${base*2:04X}-${(end-1)*2:04X}: {nz}/4096 non-zero")
    
    # Mode 0 CGRAM (simplified - use black/white for now)
    cgram_colors = [(0,0,0)] * 256
    
    # Try to find CGRAM in the dump (after VRAM)
    if size > 65536:
        cgram_data = data[65536:min(size, 65536 + 512)]
        for i in range(0, len(cgram_data) - 1, 2):
            if i // 2 < 256:
                cgram_colors[i // 2] = snes_to_rgb(struct.unpack('<H', cgram_data[i:i+2])[0])
        print(f"Loaded CGRAM: {len(cgram_data)} bytes")
    
    print("\n=== Mode 0 Name Screen ===")
    print("BG1: 4bpp tiles @$2000, tilemap @$4800")
    print("BG2: 4bpp tiles @$2000, tilemap @$4C00")
    print("BG3: 2bpp tiles @$2000, tilemap @$5000")
    print("BG4: 2bpp tiles @$4000, tilemap @$5800")
    
    print("\nRendering tilesets...")
    
    # BG1 tileset (4bpp, palette 0-7 at CGRAM 0-127)
    bg1_colors = cgram_colors[:128]
    render_tileset(vram_words, 0x1000, 4, 256, bg1_colors, "bg1_tiles_4bpp.ppm")
    
    # BG4 tileset (2bpp, palette 0-7 at CGRAM 0-31 for Mode 0)
    # In Mode 0, BG4 uses CGRAM[0-31] with palette offset
    bg4_colors = cgram_colors[:32]
    render_tileset(vram_words, 0x2000, 2, 256, bg4_colors, "bg4_tiles_2bpp.ppm")
    
    print("\nRendering tilemaps...")
    
    # BG1 tilemap (4bpp)
    render_tilemap(vram_words, 0x2400, 0x1000, 4, bg1_colors, "bg1_tilemap.ppm")
    
    # BG2 tilemap (4bpp)
    render_tilemap(vram_words, 0x2600, 0x1000, 4, bg1_colors, "bg2_tilemap.ppm")
    
    # BG3 tilemap (2bpp)
    render_tilemap(vram_words, 0x2800, 0x1000, 2, bg4_colors, "bg3_tilemap.ppm")
    
    # BG4 tilemap (2bpp)
    render_tilemap(vram_words, 0x2C00, 0x2000, 2, bg4_colors, "bg4_tilemap.ppm")
    
    print("\n=== Analysis ===")
    print("Open the .ppm files with any image viewer to see the results.")
    print("Compare with bsnes-plus PPU viewer for the correct rendering.")

if __name__ == '__main__':
    main()
