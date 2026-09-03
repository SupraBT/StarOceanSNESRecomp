#!/usr/bin/env python3
"""Byte-for-byte comparison: C S-DD1 engine vs the independent bsnes reference.

Usage:
  python sdd1_compare.py rom.sfc [engine_out.txt]

engine_out.txt is produced by sdd1_engine_test.exe (BLOCK/DMA/CPU lines).
For every line, the reference sdd1_ref.py decompresses the same chunk with
the same MMC registers and the outputs are compared.
"""

import subprocess
import sys

# name -> (addr24, size, r4804, r4805, r4806, r4807)
CASES = {
    "FFD0AB_0824": (0xFFD0AB, 0x0824, 0x00, 0x01, 0x04, 0x05),
    "FE612F_1902": (0xFE612F, 1902,    0x00, 0x01, 0x04, 0x05),
    "FE5CF0_1900": (0xFE5CF0, 1900,    0x00, 0x01, 0x04, 0x05),
    "FE63A1_4096": (0xFE63A1, 4096,    0x00, 0x01, 0x04, 0x05),
    "CD0001_4096": (0xCD0001, 4096,    0x00, 0x01, 0x02, 0x03),
    "CE0000_8192": (0xCE0000, 8192,    0x00, 0x01, 0x02, 0x03),
    "D00000_8192": (0xD00000, 8192,    0x00, 0x01, 0x02, 0x03),
    "F00000_8192": (0xF00000, 8192,    0x00, 0x01, 0x02, 0x03),
}


def ref_hex(rom, kind, addr, size, r4, r5, r6, r7):
    import os
    print("  [debug] cwd=%s kind=%s addr=%06X size=%d regs=%02X %02X %02X %02X rom=%d" % (
        os.getcwd(), kind, addr, size, r4, r5, r6, r7, os.path.getsize(rom)), file=sys.stderr)
    if kind == "BLOCK":
        args = ["python", "sdd1_ref.py", rom, "%06X" % addr, str(size),
                "%02X" % r4, "%02X" % r5, "%02X" % r6, "%02X" % r7]
    else:  # DMA / CPU -> same bsnes mcuRead streaming model
        args = ["python", "sdd1_ref.py", rom, "dma", "%06X" % addr, str(size),
                "01", "01", "%02X" % r4, "%02X" % r5, "%02X" % r6, "%02X" % r7]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr.strip()
    return r.stdout.strip().lower(), None


def main(argv):
    if len(argv) < 2:
        print("usage: python sdd1_compare.py rom.sfc [engine_out.txt]")
        return 1
    rom = argv[0]
    out_path = argv[1] if len(argv) > 1 else "sdd1_engine_out.txt"
    lines = open(out_path, encoding="utf-8", errors="replace").read().splitlines()

    n_ok = n_bad = 0
    i = 0
    while i < len(lines):
        parts = lines[i].split()
        if len(parts) < 3 or parts[0] not in ("BLOCK", "DMA", "CPU"):
            i += 1
            continue
        kind, name, count = parts[0], parts[1], parts[2]
        hex_line = lines[i + 1].strip().lower() if i + 1 < len(lines) else ""
        i += 2
        if name not in CASES:
            print("SKIP unknown case:", name)
            continue
        addr, size, r4, r5, r6, r7 = CASES[name]
        ref, err = ref_hex(rom, kind, addr, size, r4, r5, r6, r7)
        if err:
            print("FAIL %-12s %s (ref error: %s)" % (kind, name, err))
            n_bad += 1
            continue
        c_out = hex_line
        if c_out == ref:
            print("OK   %-12s %-12s bytes=%s" % (kind, name, count))
            n_ok += 1
        else:
            print("FAIL %-12s %-12s bytes=%s" % (kind, name, count))
            m = min(len(c_out), len(ref))
            first = next((k for k in range(m) if c_out[k] != ref[k]), None)
            if first is not None:
                print("      first diff at byte %d: C=%s ref=%s"
                      % (first // 2, c_out[first:first + 8], ref[first:first + 8]))
            else:
                print("      length differs: C=%d ref=%d" % (len(c_out), len(ref)))
            n_bad += 1

    print("\n%d matched, %d mismatched" % (n_ok, n_bad))
    return 0 if n_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
