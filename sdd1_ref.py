#!/usr/bin/env python3
"""Independent reference implementation of the S-DD1 decompressor.

Faithful port of bsnes's `sfc/coprocessor/sdd1/decompressor.cpp` and
`sdd1.cpp` (mmcRead / mcuRead), by Andreas Naive / byuu.  Used to validate
the C engine in `snesrecomp/runner/src/snes/sdd1.c` byte-for-byte on real
Star Ocean ROM chunks.

Usage:
    python sdd1_ref.py rom.sfc addr_hex out_bytes [r4804 r4805 r4806 r4807]
      - addr_hex: 24-bit MMC-window address of the compressed chunk
        (e.g. FF00AB means bank $FF:00AB; the MMC page regs decide the
        linear ROM offset)
      - out_bytes: number of decompressed bytes to produce
      - r4804..r4807: MMC page register values (default 0 1 2 3)
    Writes the decompressed bytes to stdout as hex.

A second mode replicates bsnes's mcuRead streaming DMA semantics
(address match + per-read byte delivery) so the C DMA path can be
compared against the exact bsnes model:

    python sdd1_ref.py rom.sfc dma addr_hex out_bytes [r4800 r4801 r4804 r4805 r4806 r4807]
"""

import sys

RUN_COUNT = [
    0x00, 0x00, 0x01, 0x00, 0x03, 0x01, 0x02, 0x00,
    0x07, 0x03, 0x05, 0x01, 0x06, 0x02, 0x04, 0x00,
    0x0f, 0x07, 0x0b, 0x03, 0x0d, 0x05, 0x09, 0x01,
    0x0e, 0x06, 0x0a, 0x02, 0x0c, 0x04, 0x08, 0x00,
    0x1f, 0x0f, 0x17, 0x07, 0x1b, 0x0b, 0x13, 0x03,
    0x1d, 0x0d, 0x15, 0x05, 0x19, 0x09, 0x11, 0x01,
    0x1e, 0x0e, 0x16, 0x06, 0x1a, 0x0a, 0x12, 0x02,
    0x1c, 0x0c, 0x14, 0x04, 0x18, 0x08, 0x10, 0x00,
    0x3f, 0x1f, 0x2f, 0x0f, 0x37, 0x17, 0x27, 0x07,
    0x3b, 0x1b, 0x2b, 0x0b, 0x33, 0x13, 0x23, 0x03,
    0x3d, 0x1d, 0x2d, 0x0d, 0x35, 0x15, 0x25, 0x05,
    0x39, 0x19, 0x29, 0x09, 0x31, 0x11, 0x21, 0x01,
    0x3e, 0x1e, 0x2e, 0x0e, 0x36, 0x16, 0x26, 0x06,
    0x3a, 0x1a, 0x2a, 0x0a, 0x32, 0x12, 0x22, 0x02,
    0x3c, 0x1c, 0x2c, 0x0c, 0x34, 0x14, 0x24, 0x04,
    0x38, 0x18, 0x28, 0x08, 0x30, 0x10, 0x20, 0x00,
    0x7f, 0x3f, 0x5f, 0x1f, 0x6f, 0x2f, 0x4f, 0x0f,
    0x77, 0x37, 0x57, 0x17, 0x67, 0x27, 0x47, 0x07,
    0x7b, 0x3b, 0x5b, 0x1b, 0x6b, 0x2b, 0x4b, 0x0b,
    0x73, 0x33, 0x53, 0x13, 0x63, 0x23, 0x43, 0x03,
    0x7d, 0x3d, 0x5d, 0x1d, 0x6d, 0x2d, 0x4d, 0x0d,
    0x75, 0x35, 0x55, 0x15, 0x65, 0x25, 0x45, 0x05,
    0x79, 0x39, 0x59, 0x19, 0x69, 0x29, 0x49, 0x09,
    0x71, 0x31, 0x51, 0x11, 0x61, 0x21, 0x41, 0x01,
    0x7e, 0x3e, 0x5e, 0x1e, 0x6e, 0x2e, 0x4e, 0x0e,
    0x76, 0x36, 0x56, 0x16, 0x66, 0x26, 0x46, 0x06,
    0x7a, 0x3a, 0x5a, 0x1a, 0x6a, 0x2a, 0x4a, 0x0a,
    0x72, 0x32, 0x52, 0x12, 0x62, 0x22, 0x42, 0x02,
    0x7c, 0x3c, 0x5c, 0x1c, 0x6c, 0x2c, 0x4c, 0x0c,
    0x74, 0x34, 0x54, 0x14, 0x64, 0x24, 0x44, 0x04,
    0x78, 0x38, 0x58, 0x18, 0x68, 0x28, 0x48, 0x08,
    0x70, 0x30, 0x50, 0x10, 0x60, 0x20, 0x40, 0x00,
]

# (codeNumber, nextIfMps, nextIfLps)
EVOLUTION = [
    (0, 25, 25), (0, 2, 1), (0, 3, 1), (0, 4, 2), (0, 5, 3),
    (1, 6, 4), (1, 7, 5), (1, 8, 6), (1, 9, 7),
    (2, 10, 8), (2, 11, 9), (2, 12, 10), (2, 13, 11),
    (3, 14, 12), (3, 15, 13), (3, 16, 14), (3, 17, 15),
    (4, 18, 16), (4, 19, 17),
    (5, 20, 18), (5, 21, 19),
    (6, 22, 20), (6, 23, 21),
    (7, 24, 22), (7, 24, 23),
    (0, 26, 1), (1, 27, 2), (2, 28, 4), (3, 29, 8),
    (4, 30, 12), (5, 31, 16), (6, 32, 18), (7, 24, 22),
]


class Sdd1:
    def __init__(self, rom):
        self.rom = rom
        self.r4800 = 0x00
        self.r4801 = 0x00
        self.r4804 = 0x00
        self.r4805 = 0x01
        self.r4806 = 0x02
        self.r4807 = 0x03

    def mmc_read(self, addr):
        """bsnes SDD1::mmcRead — pure function of the 24-bit address."""
        page = [self.r4804, self.r4805, self.r4806, self.r4807][(addr >> 20) & 3]
        off = ((page & 0x0f) << 20) | (addr & 0x0fffff)
        return self.rom[off]


class Decompressor:
    """Port of bsnes Decompressor: IM, GCD, BG[8], PEM, CM, OL."""

    def __init__(self, sdd1):
        self.s = sdd1
        # IM
        self.offset = 0
        self.bit_count = 0
        # BG (one per codeNumber 0..7)
        self.mps_count = [0] * 8
        self.lps_index = [0] * 8
        # PEM
        self.context_status = [0] * 32
        self.context_mps = [0] * 32
        # CM
        self.bitplanes_info = 0
        self.context_bits_info = 0
        self.bit_number = 0
        self.prev_plane_bits = [0] * 8
        self.cur_plane = 0
        # OL
        self.r0 = 0x01
        self.r1 = 0
        self.r2 = 0

    # --- IM ---
    def get_codeword(self, code_len):
        codeword = (self.s.mmc_read(self.offset) << self.bit_count) & 0xff
        self.bit_count += 1
        if codeword & 0x80:
            codeword |= self.s.mmc_read(self.offset + 1) >> (9 - self.bit_count)
            self.bit_count += code_len
        if self.bit_count & 0x08:
            self.offset += 1
            self.bit_count &= 0x07
        return codeword & 0xff

    # --- GCD ---
    def get_run_count(self, code_num):
        codeword = self.get_codeword(code_num)
        if codeword & 0x80:
            return 1, RUN_COUNT[codeword >> (code_num ^ 0x07)]
        return 0, 1 << code_num

    # --- BG ---
    def bg_get_bit(self, code_num):
        if not (self.mps_count[code_num] or self.lps_index[code_num]):
            self.lps_index[code_num], self.mps_count[code_num] = \
                self.get_run_count(code_num)
        if self.mps_count[code_num]:
            bit = 0
            self.mps_count[code_num] -= 1
        else:
            bit = 1
            self.lps_index[code_num] = 0
        end_of_run = not (self.mps_count[code_num] or self.lps_index[code_num])
        return bit, end_of_run

    # --- PEM ---
    def pem_get_bit(self, context):
        status = self.context_status[context]
        mps = self.context_mps[context]
        code_num, next_mps, next_lps = EVOLUTION[status]
        bit, end_of_run = self.bg_get_bit(code_num)
        if end_of_run:
            if bit:
                if not (status & 0xfe):
                    self.context_mps[context] ^= 0x01
                self.context_status[context] = next_lps
            else:
                self.context_status[context] = next_mps
        return bit ^ mps

    # --- CM ---
    def cm_get_bit(self):
        if self.bitplanes_info == 0x00:
            self.cur_plane ^= 0x01
        elif self.bitplanes_info == 0x40:
            self.cur_plane ^= 0x01
            if not (self.bit_number & 0x7f):
                self.cur_plane = (self.cur_plane + 2) & 0x07
        elif self.bitplanes_info == 0x80:
            self.cur_plane ^= 0x01
            if not (self.bit_number & 0x7f):
                self.cur_plane ^= 0x02
        elif self.bitplanes_info == 0xc0:
            self.cur_plane = self.bit_number & 0x07

        context_bits = self.prev_plane_bits[self.cur_plane]
        context = (self.cur_plane & 0x01) << 4
        if self.context_bits_info == 0x00:
            context |= ((context_bits & 0x01c0) >> 5) | (context_bits & 0x0001)
        elif self.context_bits_info == 0x10:
            context |= ((context_bits & 0x0180) >> 5) | (context_bits & 0x0001)
        elif self.context_bits_info == 0x20:
            context |= ((context_bits & 0x00c0) >> 5) | (context_bits & 0x0001)
        elif self.context_bits_info == 0x30:
            context |= ((context_bits & 0x0180) >> 5) | (context_bits & 0x0003)

        bit = self.pem_get_bit(context)
        self.prev_plane_bits[self.cur_plane] = ((context_bits << 1) | bit) & 0xffff
        self.bit_number += 1
        return bit

    # --- OL ---
    def ol_decompress(self):
        if self.bitplanes_info in (0x00, 0x40, 0x80):
            if self.r0 == 0:
                self.r0 = 0xff
                return self.r2
            r0 = 0x80
            r1 = 0
            r2 = 0
            while r0:
                if self.cm_get_bit():
                    r1 |= r0
                if self.cm_get_bit():
                    r2 |= r0
                r0 >>= 1
            self.r0 = r0  # 0
            self.r1 = r1
            self.r2 = r2
            return r1
        # 0xc0
        r0 = 0x01
        r1 = 0
        while r0:
            if self.cm_get_bit():
                r1 |= r0
            r0 = (r0 << 1) & 0xff
        self.r0 = 0
        return r1

    # --- init (bsnes Decompressor::init + Decompressor::read) ---
    def init(self, offset):
        self.offset = offset
        self.bit_count = 4
        self.mps_count = [0] * 8
        self.lps_index = [0] * 8
        self.context_status = [0] * 32
        self.context_mps = [0] * 32
        self.bitplanes_info = self.s.mmc_read(offset) & 0xc0
        self.context_bits_info = self.s.mmc_read(offset) & 0x30
        self.bit_number = 0
        self.prev_plane_bits = [0] * 8
        if self.bitplanes_info == 0x00:
            self.cur_plane = 1
        elif self.bitplanes_info == 0x40:
            self.cur_plane = 7
        elif self.bitplanes_info == 0x80:
            self.cur_plane = 3
        self.r0 = 0x01
        self.r1 = 0
        self.r2 = 0

    def read(self):
        return self.ol_decompress()


def decompress_block(sdd1, addr, out_bytes):
    d = Decompressor(sdd1)
    d.init(addr)
    out = bytearray()
    for _ in range(out_bytes):
        out.append(d.read())
    return bytes(out)


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 1
    rom_path = argv[0]
    mode = argv[1]
    if mode == "dma":
        # dma addr out_bytes [r4800 r4801 r4804 r4805 r4806 r4807]
        addr = int(argv[2], 16)
        out_bytes = int(argv[3])
        regs = [int(x, 16) for x in argv[4:10]]
        if len(regs) < 6:
            regs = [0x00, 0x01, 0x00, 0x01, 0x02, 0x03][:6]
        r4800, r4801, r4804, r4805, r4806, r4807 = regs
        rom = open(rom_path, "rb").read()
        s = Sdd1(rom)
        s.r4800, s.r4801 = r4800, r4801
        s.r4804, s.r4805, s.r4806, s.r4807 = r4804, r4805, r4806, r4807
        # bsnes mcuRead model: streaming, one channel, address match, size countdown
        d = Decompressor(s)
        d.init(addr)
        size = out_bytes
        out = bytearray()
        for _ in range(out_bytes):
            out.append(d.read())
            size -= 1
            if size == 0:
                break
        sys.stdout.write(out.hex())
        return 0
    else:
        # addr out_bytes [r4804 r4805 r4806 r4807]
        addr = int(mode, 16)
        out_bytes = int(argv[2])
        regs = [int(x, 16) for x in argv[3:7]]
        if len(regs) < 4:
            regs = [0x00, 0x01, 0x02, 0x03]
        r4804, r4805, r4806, r4807 = regs
        rom = open(rom_path, "rb").read()
        s = Sdd1(rom)
        s.r4804, s.r4805, s.r4806, s.r4807 = r4804, r4805, r4806, r4807
        out = decompress_block(s, addr, out_bytes)
        sys.stdout.write(out.hex())
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
