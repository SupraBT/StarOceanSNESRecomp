#!/usr/bin/env python3
"""Render BG layers from PPU dump as images for comparison with bsnes."""
import struct, sys

with open("build/saves/ppu_dump.bin", "rb") as f:
    data = f.read()

# Parse dump
vram = struct.unpack("<32768H", data[:0x10000])
cgram_words = struct.unpack("<256H", data[0x10000:0x10000+0x200])

# Parse extended dump after CGRAM
offset = 0x10000 + 0x200
regs = {}
reg_names = ['inidisp','obsel','bgmode','mosaic','bgXsc0','bgXsc1','bgXsc2','bgXsc3',
             'bgTileAdr','bg12nba','vramInc','vramRemap',
             'h0','v0','h1','v1','h2','v2','h3','v3',
             'tm','ts','cgwsel','cgadsub','fixedLo','fixedHi','windowsel']
for name in reg_names:
    if offset < len(data):
        regs[name] = data[offset]
        offset += 1

print("=== PPU Registers ===")
print(f"  bgmode={regs.get('bgmode',0)} (Mode {(regs.get('bgmode',0))&7})")
print(f"  bgTileAdr=${regs.get('bgTileAdr',0):04X}")
print(f"  bg12nba=${regs.get('bg12nba',0):04X}")
print(f"  bgXsc=[${regs.get('bgXsc0',0):02X},${regs.get('bgXsc1',0):02X},${regs.get('bgXsc2',0):02X},${regs.get('bgXsc3',0):02X}]")
print(f"  TM=${regs.get('tm',0):02X} TS=${regs.get('ts',0):02X}")
print(f"  CGWSEL=${regs.get('cgwsel',0):02X} CGADSUB=${regs.get('cgadsub',0):02X}")

# Mode 1 VRAM layout from bgTileAdr
bgmode = regs.get('bgmode', 0) & 7
btilelo = regs.get('bgTileAdr', 0) & 0xf
btilehi = (regs.get('bgTileAdr', 0) >> 4) & 0xf

# bgXsc register values
bg12nba = regs.get('bg12nba', 0) | (regs.get('bgTileAdr', 0) << 8)

# Calculate tile data addresses from bgTileAdr low nibble
# In Mode 1: BG1 and BG2 are 4bpp, BG3 is 2bpp
# bgTileAdr bits:
#   bits 0-3: BG1/BG2 tile data (0=4KB, 1=8KB, etc)
#   bits 4-7: BG3/BG4 tile data
tile_base = [0, 0, 0, 0]
if bgmode == 1:
    # BG1/BG2 tile address from low nibble of bgTileAdr
    if btilelo <= 3:
        tile_base[0] = 0  # BG1 always starts at 0
        tile_base[1] = (btilelo + 1) * 0x1000  # BG2 offset
    else:
        tile_base[0] = ((btilelo & 3)) * 0x1000
        tile_base[1] = ((btilelo & 3) + 1) * 0x1000
    # BG3 tile address from high nibble
    tile_base[2] = ((btilehi & 3)) * 0x1000

# BG tilemap addresses from bgXsc
sc_base = [0, 0, 0, 0]
for i in range(4):
    sc_reg = [regs.get('bgXsc0',0), regs.get('bgXsc1',0), regs.get('bgXsc2',0), regs.get('bgXsc3',0)][i]
    sc_base[i] = (sc_reg & 0x3) * 0x0400  # bits 0-1 = base
    if sc_reg & 0x80:  # bit 7 = high bit for 4-screen
        pass  # skip for now

print(f"\n=== VRAM Layout (from registers) ===")
print(f"  BG1: tilemap @${sc_base[0]:04X} tiles @${tile_base[0]:04X}")
print(f"  BG2: tilemap @${sc_base[1]:04X} tiles @${tile_base[1]:04X}")
print(f"  BG3: tilemap @${sc_base[2]:04X} tiles @${tile_base[2]:04X}")

# SNES 15-bit to RGB
def snes_to_rgb(c):
    r = (c & 0x1f) * 8
    g = ((c >> 5) & 0x1f) * 8
    b = ((c >> 10) & 0x1f) * 8
    return (min(r,255), min(g,255), min(b,255))

# Render a 4bpp tile at VRAM address
def render_tile_4bpp(vram, addr):
    """Return 8x8 pixels as list of 4-bit palette indices"""
    pixels = [[0]*8 for _ in range(8)]
    for row in range(8):
        w0 = vram[(addr + row) & 0x7fff]
        w1 = vram[(addr + 8 + row) & 0x7fff]
        for col in range(8):
            bit = 7 - col
            p = ((w0 >> bit) & 1) | (((w0 >> (bit+8)) & 1) << 1) | \
                (((w1 >> bit) & 1) << 2) | (((w1 >> (bit+8)) & 1) << 3)
            pixels[row][col] = p
    return pixels

# Render a 2bpp tile at VRAM address  
def render_tile_2bpp(vram, addr):
    """Return 8x8 pixels as list of 2-bit palette indices"""
    pixels = [[0]*8 for _ in range(8)]
    for row in range(8):
        w = vram[(addr + row) & 0x7fff]
        for col in range(8):
            bit = 7 - col
            p = ((w >> bit) & 1) | (((w >> (bit+8)) & 1) << 1)
            pixels[row][col] = p
    return pixels

# Render a BG layer
def render_bg(vram, cgram_words, tm_base, tile_base, bpp, palette_offset, scroll_h, scroll_v):
    """Render a 32x32 tilemap into a 256x256 image"""
    img = [[(0,0,0)]*256 for _ in range(224)]
    
    for ty in range(32):
        for tx in range(32):
            # Read tilemap entry
            tm_addr = (tm_base + ty * 32 + tx) & 0x7fff
            entry = vram[tm_addr]
            
            if entry == 0:
                continue  # transparent
            
            tile_num = entry & 0x3ff
            pal_num = (entry >> 10) & 7
            hflip = bool(entry & 0x4000)
            vflip = bool(entry & 0x8000)
            prio = bool(entry & 0x2000)
            
            # Calculate tile VRAM address
            if bpp == 4:
                tile_addr = (tile_base + tile_num * 16) & 0x7fff
                tile_pixels = render_tile_4bpp(vram, tile_addr)
            else:
                tile_addr = (tile_base + tile_num * 8) & 0x7fff
                tile_pixels = render_tile_2bpp(vram, tile_addr)
            
            # Apply palette and draw
            cgram_base = palette_offset + pal_num * (16 if bpp == 4 else 8)
            
            for py in range(8):
                for px in range(8):
                    src_px = px if not hflip else (7 - px)
                    src_py = py if not vflip else (7 - py)
                    p = tile_pixels[src_py][src_px]
                    if p == 0:
                        continue  # transparent
                    
                    cgram_idx = cgram_base + p
                    if cgram_idx < 256:
                        color = snes_to_rgb(cgram_words[cgram_idx])
                    else:
                        color = (255, 0, 255)  # magenta = error
                    
                    screen_x = tx * 8 + px - (scroll_h & 0x1ff)
                    screen_y = ty * 8 + py - (scroll_v & 0x1ff)
                    
                    # Wrap
                    screen_x %= 256
                    screen_y %= 256
                    
                    if 0 <= screen_x < 256 and 0 <= screen_y < 224:
                        img[screen_y][screen_x] = color
    
    return img

def write_ppm(img, filename):
    with open(filename, "wb") as f:
        h = len(img)
        w = len(img[0])
        f.write(f"P6\n{w} {h}\n255\n".encode())
        for row in img:
            for r, g, b in row:
                f.write(bytes([r, g, b]))

# Get scroll values
h0 = regs.get('h0', 0) | (regs.get('bgXsc0', 0) << 8)  # Wrong - need proper 16-bit
v0 = regs.get('v0', 0)

# Actually the scroll values are after the register bytes
# Let me re-read from the dump
offset = 0x10000 + 0x200 + len(reg_names)
scroll_data = data[offset:offset+8]
hscrolls = [0,0,0,0]
vscrolls = [0,0,0,0]
for i in range(4):
    hscrolls[i] = struct.unpack("<H", scroll_data[i*2:i*2+2])[0] & 0x1ff
offset += 8
scroll_data2 = data[offset:offset+8]
for i in range(4):
    vscrolls[i] = struct.unpack("<H", scroll_data2[i*2:i*2+2])[0] & 0x3ff

print(f"  HScroll: {hscrolls}")
print(f"  VScroll: {vscrolls}")

# Try different VRAM layouts and render
# From the dump, we know:
# bgmode=0 at dump time, but PPU_MODE showed mode=1 during rendering
# The game likely uses Mode 1 with different tile addresses

# Let me try rendering with the ACTUAL dump values
print("\n=== Rendering BG layers ===")

# Mode 1: BG1=4bpp, BG2=4bpp, BG3=2bpp
# From bgTileAdr=$4222 in Mode 0 dump:
# But during Mode 1 rendering, bgTileAdr was $0400

# Try Mode 1 layout: bgTileAdr=$0400
m1_tile_base = [0, 0x1000, 0x4000, 0]
m1_tm_base = [0x7800, 0x7C00, 0x7400, 0x5800]  # from dump

# Try rendering BG1 with Mode 1 z values
# In Mode 1: BG1 uses palette at CGRAM[0-127]
print("Rendering BG1 (4bpp, palette at CGRAM[0])...")
bg1_img = render_bg(vram, cgram_words, m1_tm_base[0], m1_tile_base[0], 4, 0, hscrolls[0], vscrolls[0])
write_ppm(bg1_img, "bg1_mode1.ppm")
print("  -> bg1_mode1.ppm")

print("Rendering BG2 (4bpp, palette at CGRAM[0])...")
bg2_img = render_bg(vram, cgram_words, m1_tm_base[1], m1_tile_base[1], 4, 0, hscrolls[1], vscrolls[1])
write_ppm(bg2_img, "bg2_mode1.ppm")
print("  -> bg2_mode1.ppm")

print("Rendering BG3 (2bpp, palette at CGRAM[0])...")
bg3_img = render_bg(vram, cgram_words, m1_tm_base[2], m1_tile_base[2], 2, 0, hscrolls[2], vscrolls[2])
write_ppm(bg3_img, "bg3_mode1.ppm")
print("  -> bg3_mode1.ppm")

# Also try with different tile base addresses
# From bgTileAdr=$0400 in Mode 1:
# Low nibble $0: BG1/BG2 at $0000/$1000
# High nibble $4: BG3 at $4000

# Print some sample CGRAM entries for debugging
print("\n=== CGRAM palette analysis ===")
for pal in range(8):
    colors = [snes_to_rgb(cgram_words[pal*16 + i]) for i in range(16)]
    print(f"  Pal{pal}: {colors[:4]}")

print("\nDone! Open the .ppm files to compare with bsnes.")
