#!/usr/bin/env python3
"""Track-B comparator: recomp (so_cosim --state-out) vs bsnes oracle.

Diffs per-frame CPU/PPU/S-DD1/WRAM/VRAM/CGRAM snapshots. Halts at the first
trusted divergence and writes cosim_mismatch.log with the exact offsets and
values (same contract as the Track-A coordinator).

Usage:
  cosim_trackb.py --a <recomp.bin> --b <bsnes.bin> [--stats] [--out <log>]

Layout (little-endian, shared with bsnes state_snapshot.hpp / harness_so.c):
  header 'SOCO' u32 version u32 recordSize u32
  record: u32 frame | cpu 18B | dev 16B | ppu 66B | u64 ppuValid | sdd1 6B |
          wram 0x20000B | vram 0x10000B | cgram 0x200B
  recordSize = 197238
"""
import struct
import sys

MAGIC = b"SOCO"
REC_SIZE = 4 + 18 + 16 + 66 + 8 + 6 + 0x20000 + 0x10000 + 0x200

CPU_O = 4
DEV_O = CPU_O + 18
PPU_O = DEV_O + 16
MASK_O = PPU_O + 66
SDD1_O = MASK_O + 8
WRAM_O = SDD1_O + 6
VRAM_O = WRAM_O + 0x20000
CGRAM_O = VRAM_O + 0x10000

PPU_FIELDS = [
    (0, "inidisp"), (1, "obsel"), (2, "oamaddl"), (3, "oamaddh"),
    (4, "bgmode"), (5, "mosaic"),
    (6, "bgXsc[0]"), (7, "bgXsc[1]"), (8, "bgXsc[2]"), (9, "bgXsc[3]"),
    (10, "bgTileAdr"), (12, "m7sel"), (13, "setini"),
]
for i in range(4):
    PPU_FIELDS.append((14 + 2 * i, "hScroll[%d]" % i))
for i in range(4):
    PPU_FIELDS.append((22 + 2 * i, "vScroll[%d]" % i))
M7_NAMES = ["a", "b", "c", "d", "x", "y", "h", "v"]
for i in range(8):
    PPU_FIELDS.append((30 + 2 * i, "m7%s" % M7_NAMES[i]))
PPU_FIELDS += [
    (46, "fixedColor"), (48, "cgadsub"), (49, "cgwsel"),
    (50, "screenEnabled[0]"), (51, "screenEnabled[1]"),
    (52, "window1left"), (53, "window1right"),
    (54, "window2left"), (55, "window2right"),
    (56, "wbgobjlog"), (58, "vramPointer"),
]
PPU_LABEL = {}
for off, name in PPU_FIELDS:
    PPU_LABEL[off] = name


def u16(buf, o):
    return struct.unpack_from("<H", buf, o)[0]


def u32(buf, o):
    return struct.unpack_from("<I", buf, o)[0]


def u64(buf, o):
    return struct.unpack_from("<Q", buf, o)[0]


def parse_record(buf):
    rec = {
        "frame": u32(buf, CPU_O - 4),
        "cpu": buf[CPU_O:DEV_O],
        "dev": buf[DEV_O:PPU_O],
        "ppu": buf[PPU_O:MASK_O],
        "mask": u64(buf, MASK_O),
        "sdd1": buf[SDD1_O:WRAM_O],
        "wram": buf[WRAM_O:VRAM_O],
        "vram": buf[VRAM_O:CGRAM_O],
        "cgram": buf[CGRAM_O:REC_SIZE],
    }
    return rec


def first_diff(a, b):
    """First differing byte index in equal-length bytes, or None."""
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return None


def diff_count(a, b):
    n = min(len(a), len(b))
    return sum(1 for i in range(n) if a[i] != b[i])


def describe(ra, rb):
    lines = []
    ppu = ra["ppu"]
    ppu_b = rb["ppu"]
    mask = ra["mask"] & rb["mask"]
    for off in range(66):
        if not (mask >> off) & 1:
            continue
        if ppu[off] != ppu_b[off]:
            label = PPU_LABEL.get(off, "ppu[%d]" % off)
            lines.append("  PPU %-18s A=%02X B=%02X" % (label, ppu[off], ppu_b[off]))
    if ra["sdd1"] != rb["sdd1"]:
        i = first_diff(ra["sdd1"], rb["sdd1"])
        lines.append("  SDD1 r%02X: A=%02X B=%02X"
                     % (0x4800 + i, ra["sdd1"][i], rb["sdd1"][i]))
    i = first_diff(ra["wram"], rb["wram"])
    if i is not None:
        lines.append("  WRAM $%05X: A=%02X B=%02X" % (i, ra["wram"][i], rb["wram"][i]))
    i = first_diff(ra["vram"], rb["vram"])
    if i is not None:
        lines.append("  VRAM word $%04X: A=%04X B=%04X"
                     % (i // 2, u16(ra["vram"], i & ~1), u16(rb["vram"], i & ~1)))
    i = first_diff(ra["cgram"], rb["cgram"])
    if i is not None:
        lines.append("  CGRAM $%03X: A=%04X B=%04X"
                     % (i // 2, u16(ra["cgram"], i & ~1), u16(rb["cgram"], i & ~1)))
    if not lines:
        # informational only (cpu/dev) — report the biggest cpu delta
        i = first_diff(ra["cpu"], rb["cpu"])
        if i is not None:
            lines.append("  CPU regs differ (informational; not halt): byte %d A=%02X B=%02X"
                         % (i, ra["cpu"][i], rb["cpu"][i]))
    return lines


def main():
    argv = sys.argv[1:]
    path_a = path_b = out_log = None
    stats = False
    i = 0
    while i < len(argv):
        if argv[i] == "--a" and i + 1 < len(argv):
            path_a = argv[i + 1]; i += 2
        elif argv[i] == "--b" and i + 1 < len(argv):
            path_b = argv[i + 1]; i += 2
        elif argv[i] == "--out" and i + 1 < len(argv):
            out_log = argv[i + 1]; i += 2
        elif argv[i] == "--stats":
            stats = True; i += 1
        else:
            print("usage: cosim_trackb.py --a <a.bin> --b <b.bin> [--stats] [--out <log>]")
            return 2
    if not path_a or not path_b:
        print("usage: cosim_trackb.py --a <a.bin> --b <b.bin> [--stats] [--out <log>]")
        return 2
    if not out_log:
        out_log = "cosim_mismatch.log"

    fa = open(path_a, "rb")
    fb = open(path_b, "rb")
    if fa.read(4) != MAGIC or fb.read(4) != MAGIC:
        print("bad magic (not a Track-B state file?)")
        return 2
    va, rsa = struct.unpack("<II", fa.read(8))
    vb, rsb = struct.unpack("<II", fb.read(8))
    if va != 1 or vb != 1 or rsa != REC_SIZE or rsb != REC_SIZE:
        print("version/recordSize mismatch: A=(%d,%d) B=(%d,%d)" % (va, rsa, vb, rsb))
        return 2

    report = []
    n = 0
    max_diff = 0
    while True:
        ba = fa.read(REC_SIZE)
        bb = fb.read(REC_SIZE)
        if not ba and not bb:
            break
        if not ba or not bb:
            report.append("frame %d: one side ended early (A=%d B=%d bytes left)"
                          % (n, len(ba), len(bb)))
            break
        ra = parse_record(ba)
        rb = parse_record(bb)
        if ra["frame"] != rb["frame"]:
            report.append("frame index drift: A=%d B=%d" % (ra["frame"], rb["frame"]))
            break
        # informational (never halts): cpu, dev hPos/vPos
        if ra["dev"][:4] != rb["dev"][:4]:
            report.append("frame %d: dev hPos/vPos A=%04X/%04X B=%04X/%04X (informational)"
                          % (n, u16(ra["dev"], 0), u16(ra["dev"], 2),
                             u16(rb["dev"], 0), u16(rb["dev"], 2)))
        # trusted halting comparisons
        lines = describe(ra, rb)
        if lines:
            if stats:
                d = diff_count(ra["wram"], rb["wram"]) + diff_count(ra["vram"], rb["vram"]) \
                    + diff_count(ra["cgram"], rb["cgram"])
                max_diff = max(max_diff, d)
                if n % 10 == 0:
                    report.append("frame %d: diffs=%d" % (n, d))
                n += 1
                continue
            report.append("=== FIRST DIVERGENCE at frame %d === (A=%s B=%s)"
                          % (n, path_a, path_b))
            report.extend(lines)
            report.append("")
            report.append("frame %d: ppu mask A=%016X B=%016X (compared bits: %016X)"
                          % (n, ra["mask"], rb["mask"], ra["mask"] & rb["mask"]))
            report.append("frame %d: sdd1 A=%s B=%s"
                          % (n, ra["sdd1"].hex(), rb["sdd1"].hex()))
            report.append("frame %d: cpu  A=%s" % (n, ra["cpu"].hex()))
            report.append("frame %d: cpu  B=%s" % (n, rb["cpu"].hex()))
            report.append("frame %d: dev  A=%s" % (n, ra["dev"].hex()))
            report.append("frame %d: dev  B=%s" % (n, rb["dev"].hex()))
            report.append("frame %d: ppu  A=%s" % (n, ra["ppu"].hex()))
            report.append("frame %d: ppu  B=%s" % (n, rb["ppu"].hex()))
            report.append("")
            report.append("wram diff bytes: %d  vram diff bytes: %d  cgram diff bytes: %d"
                          % (diff_count(ra["wram"], rb["wram"]),
                             diff_count(ra["vram"], rb["vram"]),
                             diff_count(ra["cgram"], rb["cgram"])))
            with open(out_log, "w") as f:
                f.write("\n".join(report) + "\n")
            print("\n".join(report))
            print("\n[mismatch] wrote %s" % out_log)
            return 1
        n += 1

    if stats:
        report.append("stats: %d frames compared, max combined diff = %d" % (n, max_diff))
    report.append("PASS: %d frames matched (trusted fields byte-identical)" % n)
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
