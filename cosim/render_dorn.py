#!/usr/bin/env python3
"""Render the Dorn house scene from VRAM/CGRAM binary dumps.

Uses the same SNES PPU register state from the snapshot to produce
a software-rendered 256x224 image for visual comparison against the
debug server screenshot and the user's reference image.

Mode 1 layers:
  BG1: 4bpp, BG1SC=0x78 (word $3C00), tiles from BG12NBA lo=0x04→word $2000
  BG2: 4bpp, BG2SC=0x7C (word $3E00), tiles from BG12NBA hi→word $4000
  BG3: 4bpp, BG3SC=0x58 (word $2C00), tiles from BG34NBA lo=0x10→word $0000
  BG4: 2bpp, BG4SC=0x58 (word $2C00), tiles from BG34NBA hi→word $2000
  OBJ: 4bpp, from OBSSEL base

VRAM dump is byte-addressed over uint16[]: word N = bytes [2N, 2N+1].
"""
from __future__ import annotations

import json
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "build-cosim" / "semantic-dorn-final"
OUT = CAPTURE / "rendered_dorn.png"


def snes15_to_rgb(word: int) -> tuple[int, int, int]:
    r = (word & 0x1F) << 3
    g = ((word >> 5) & 0x1F) << 3
    b = ((word >> 10) & 0x1F) << 3
    return r, g, b


def load_vram(path: Path) -> list[int]:
    """Load VRAM dump as list of 16-bit words (byte-addressed)."""
    data = path.read_bytes()
    words = []
    for i in range(0, len(data) - 1, 2):
        words.append(data[i] | (data[i + 1] << 8))
    return words


def load_cgram(path: Path) -> list[tuple[int, int, int]]:
    """Load CGRAM dump as list of RGB tuples."""
    data = path.read_bytes()
    colors = []
    for i in range(0, len(data) - 1, 2):
        word = data[i] | (data[i + 1] << 8)
        colors.append(snes15_to_rgb(word))
    # Pad to 256
    while len(colors) < 256:
        colors.append((0, 0, 0))
    return colors


def decode_tile_4bpp(vram: list[int], tile_word_addr: int) -> list[list[int]]:
    """Decode one 8x8 4bpp tile from VRAM word address. Returns 8 rows of 8 pixel indices."""
    tile = []
    for row in range(8):
        bp0 = vram[tile_word_addr + row]
        bp1 = vram[tile_word_addr + 8 + row]
        bp2 = vram[tile_word_addr + 16 + row]
        bp3 = vram[tile_word_addr + 24 + row]
        pixels = []
        for bit in range(7, -1, -1):
            idx = ((bp0 >> bit) & 1) | \
                  (((bp1 >> bit) & 1) << 1) | \
                  (((bp2 >> bit) & 1) << 2) | \
                  (((bp3 >> bit) & 1) << 3)
            pixels.append(idx)
        tile.append(pixels)
    return tile


def decode_tile_2bpp(vram: list[int], tile_word_addr: int) -> list[list[int]]:
    """Decode one 8x8 2bpp tile from VRAM word address."""
    tile = []
    for row in range(8):
        bp0 = vram[tile_word_addr + row]
        bp1 = vram[tile_word_addr + 8 + row]
        pixels = []
        for bit in range(7, -1, -1):
            idx = ((bp0 >> bit) & 1) | (((bp1 >> bit) & 1) << 1)
            pixels.append(idx)
        tile.append(pixels)
    return tile


def render_bg(vram: list[int], cgram: list[tuple[int, int, int]],
              sc_word: int, tile_base_word: int, pal_offset: int,
              hscroll: int, vscroll: int, bpp: int = 4,
              w: int = 256, h: int = 224, big: bool = False) -> list[list[tuple[int, int, int]]]:
    """Render a BG layer. Returns h x w RGB pixels."""
    screen = [[(0, 0, 0)] * w for _ in range(h)]
    tile_w = 16 if big else 8
    # 32x32 or 32x64 tilemap
    map_words = 1024  # 32x32
    decode_fn = decode_tile_4bpp if bpp == 4 else decode_tile_2bpp

    for ty in range(h // tile_w + 2):
        for tx in range(w // tile_w + 2):
            # Screen address in tilemap
            map_idx = ((ty & 31) * 32 + (tx & 31)) & (map_words - 1)
            entry = vram[sc_word + map_idx]
            tile_num = entry & 0x3FF
            pal_num = (entry >> 10) & 7
            flip_h = bool(entry & (1 << 14))
            flip_v = bool(entry & (1 << 15))

            tile_addr = tile_base_word + tile_num * (16 if bpp == 4 else 8)
            if tile_addr + 32 > len(vram):
                continue
            tile = decode_fn(vram, tile_addr)

            for py in range(tile_w):
                for px in range(tile_w):
                    sx = tx * tile_w + px - (hscroll & (w - 1))
                    sy = ty * tile_w + py - (vscroll & 0x3FF)
                    if sx < 0 or sx >= w or sy < 0 or sy >= h:
                        continue
                    tpx = (7 - px) if flip_h else px
                    tpy = (tile_w - 1 - py) if flip_v else py
                    if tpy >= len(tile) or tpx >= len(tile[0]):
                        continue
                    idx = tile[tpy][tpx]
                    if idx == 0:
                        continue  # transparent
                    color_idx = pal_offset + pal_num * (16 if bpp == 4 else 4) + idx
                    if color_idx < len(cgram):
                        screen[sy][sx] = cgram[color_idx]
    return screen


def main():
    frame = 20110
    vram_path = CAPTURE / f"capture_{frame:06d}_vram.bin"
    cgram_path = CAPTURE / f"capture_{frame:06d}_cgram.bin"
    json_path = CAPTURE / f"capture_{frame:06d}.json"

    if not vram_path.exists():
        print(f"VRAM not found: {vram_path}")
        sys.exit(1)

    with open(json_path) as f:
        data = json.load(f)
    ppu = data["ppu"]

    vram = load_vram(vram_path)
    cgram = load_cgram(cgram_path)

    # Parse PPU registers
    sc_vals = [int(x, 16) for x in ppu["bgXsc"]]
    bgsc = [(sc >> 2) & 0x3F for sc in sc_vals]  # word address >> 8 = (sc & 0x3FC) << 8
    # BGSC register: bits 7-2 = SC value; word addr = SC * $0400
    bgsc_word = [((sc >> 2) & 0x3F) * 0x400 for sc in sc_vals]

    tile_adr = int(ppu["bgTileAdr"], 16)
    bg12nba = tile_adr & 0xFF
    bg34nba = (tile_adr >> 8) & 0xFF
    # SNES NBA register: each 4-bit field * $2000 = tile base BYTE address
    # VRAM dump is byte-addressed but loaded as words: word_addr = byte_addr / 2
    # BG12NBA (0x210B): lo=nibble0=BG1, hi=nibble1=BG2
    # BG34NBA (0x210C): lo=nibble0=BG3, hi=nibble1=BG4
    bg1_tiles = ((bg12nba & 0x0F) * 0x2000) // 2
    bg2_tiles = (((bg12nba >> 4) & 0x0F) * 0x2000) // 2
    bg3_tiles = ((bg34nba & 0x0F) * 0x2000) // 2
    bg4_tiles = (((bg34nba >> 4) & 0x0F) * 0x2000) // 2

    hscroll = ppu["hScroll"]
    vscroll = ppu["vScroll"]

    print(f"Frame: {frame}")
    print(f"BG1SC word: {bgsc_word[0]:#06x}, tiles: {bg1_tiles:#06x}")
    print(f"BG2SC word: {bgsc_word[1]:#06x}, tiles: {bg2_tiles:#06x}")
    print(f"BG3SC word: {bgsc_word[2]:#06x}, tiles: {bg3_tiles:#06x}")
    print(f"BG4SC word: {bgsc_word[3]:#06x}, tiles: {bg4_tiles:#06x}")
    print(f"hScroll: {hscroll}")
    print(f"vScroll: {vscroll}")

    # Render each layer
    bg1 = render_bg(vram, cgram, bgsc_word[0], bg1_tiles, 0,
                    hscroll[0], vscroll[0], bpp=4)
    bg2 = render_bg(vram, cgram, bgsc_word[1], bg2_tiles, 128,
                    hscroll[1], vscroll[1], bpp=4)
    bg3 = render_bg(vram, cgram, bgsc_word[2], bg3_tiles, 0,
                    hscroll[2], vscroll[2], bpp=4)

    # Composite: BG1 -> BG2 -> BG3 (simplified, no priority)
    from PIL import Image
    img = Image.new("RGB", (256, 224), (0, 0, 0))
    pixels = img.load()

    # BG1 first
    for y in range(224):
        for x in range(256):
            r, g, b = bg1[y][x]
            if r or g or b:
                pixels[x, y] = (r, g, b)

    # BG2 on top
    for y in range(224):
        for x in range(256):
            r, g, b = bg2[y][x]
            if r or g or b:
                pixels[x, y] = (r, g, b)

    # BG3 on top (dialogue box)
    for y in range(224):
        for x in range(256):
            r, g, b = bg3[y][x]
            if r or g or b:
                pixels[x, y] = (r, g, b)

    img.save(OUT)
    print(f"\nSaved rendered image: {OUT}")

    # Also save individual layers for inspection
    for name, layer in [("bg1", bg1), ("bg2", bg2), ("bg3", bg3)]:
        layer_img = Image.new("RGB", (256, 224), (0, 0, 0))
        lp = layer_img.load()
        for y in range(224):
            for x in range(256):
                r, g, b = layer[y][x]
                if r or g or b:
                    lp[x, y] = (r, g, b)
        layer_img.save(CAPTURE / f"rendered_{name}.png")
        print(f"  Layer {name}: saved")


if __name__ == "__main__":
    main()
