"""Check what's in the SPC dump - find the DSP register offset."""
import struct

with open('F:/StarOceanRecompRAID/run-trace/spc_f10050.bin', 'rb') as f:
    data = f.read()

print(f"Total size: {len(data)} bytes")
print(f"First 32 bytes: {' '.join(f'{b:02X}' for b in data[:32])}")
print(f"Bytes at 65536-65568: {' '.join(f'{b:02X}' for b in data[65536:65568])}")
print()

# Check if DSP registers are at the start
# Voice 0 should have some non-zero values if music is playing
print("Check offset 0 (if DSP at start):")
for ch in range(8):
    base = ch * 16
    print(f"  V{ch}: {' '.join(f'{data[base+i]:02X}' for i in range(10))}")

# Check if DSP registers are at offset 65536
print("\nCheck offset 65536 (if DSP at end):")
for ch in range(8):
    base = 65536 + ch * 16
    end = min(base + 10, len(data))
    print(f"  V{ch}: {' '.join(f'{data[i]:02X}' for i in range(base, end))}")

# Look for patterns: Voice 0 VOLL should be between $00 and $7F typically
# Check what's at the "global" registers (master volume, FLG, etc.)
# Global registers in DSP: $0C (MVOLL), $1C (MVOLR), $6C (FLG), $7C (ENDx)
print("\nGlobal registers at offset 0:")
for addr in [0x0C, 0x1C, 0x2C, 0x3C, 0x4C, 0x5C, 0x6C, 0x7C]:
    print(f"  ${addr:02X}: ${data[addr]:02X}")

print("\nGlobal registers at offset 65536:")
for addr in [0x0C, 0x1C, 0x2C, 0x3C, 0x4C, 0x5C, 0x6C, 0x7C]:
    pos = 65536 + addr
    if pos < len(data):
        print(f"  ${addr:02X}: ${data[pos]:02X}")
