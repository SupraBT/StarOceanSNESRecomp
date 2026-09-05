"""
SPC file format: DSP registers are at offset 0x10100 (65792), not 0.
Previous analysis was reading APU RAM, which is wrong!
"""
import struct

def dump_dsp(data, offset, label):
    print(f"\n=== {label} (offset 0x{offset:X}) ===")
    reg_names = ['VOLL', 'VOLR', 'PITCHL', 'PITCHH', 'SRCN', 'ADSR1', 'ADSR2', 'GAIN', 'ENVX', 'OUTX']
    for ch in range(8):
        base = offset + ch * 16
        voll = data[base]
        volr = data[base + 1]
        pitchl = data[base + 2]
        pitchh = data[base + 3]
        srcn = data[base + 4]
        adsr1 = data[base + 5]
        adsr2 = data[base + 6]
        gain = data[base + 7]
        envx = data[base + 8]
        outx = data[base + 9]
        
        adsr_enabled = bool(adsr1 & 0x80)
        gain_direct = not adsr_enabled and (gain & 0x80) == 0
        
        print(f"  V{ch}: VOLL=${voll:02X} VOLR=${volr:02X} PITCH=${pitchh:02X}{pitchl:02X} "
              f"SRCN=${srcn:02X} ADSR1=${adsr1:02X} ADSR2=${adsr2:02X} GAIN=${gain:02X} "
              f"ENVX=${envx:02X} OUTX=${outx:02X}"
              f" {'[ADSR]' if adsr_enabled else '[GAIN]'}")

# Read both SPC dumps
with open('F:/StarOceanRecompRAID/run-trace/spc_f10050.bin', 'rb') as f:
    data1 = f.read()
with open('F:/StarOceanRecompRAID/run-trace/spc_f10200.bin', 'rb') as f:
    data2 = f.read()

# SPC file format: DSP at offset 0x10100
DSP_OFFSET = 0x10100

dump_dsp(data1, DSP_OFFSET, "Frame ~10050 (before beep)")
dump_dsp(data2, DSP_OFFSET, "Frame ~10200 (during/after beep)")

# Focus on differences in voices 0-7
print("\n=== DSP Register DIFFERENCES (voices 0-7 only) ===")
reg_names = ['VOLL', 'VOLR', 'PITCHL', 'PITCHH', 'SRCN', 'ADSR1', 'ADSR2', 'GAIN', 'ENVX', 'OUTX']
for ch in range(8):
    base1 = DSP_OFFSET + ch * 16
    base2 = DSP_OFFSET + ch * 16
    changes = []
    for i in range(10):
        v1 = data1[base1 + i]
        v2 = data2[base2 + i]
        if v1 != v2:
            changes.append(f"  {reg_names[i]}: ${v1:02X} -> ${v2:02X}")
    if changes:
        print(f"\n  Voice {ch} CHANGED:")
        for c in changes:
            print(c)

# Also check global registers
print("\n=== Global Register DIFFERENCES ===")
globals_names = {
    0x0C: 'MVOLL', 0x1C: 'MVOLR', 0x2C: 'EVOLL', 0x3C: 'EVOLR',
    0x4C: 'KON', 0x5C: 'KOF', 0x6C: 'FLG', 0x7C: 'ENDx',
    0x0D: 'EFB', 0x1D: '0x1D', 0x2D: 'PMON', 0x3D: 'NON', 0x4D: 'EON',
    0x5D: 'DIR', 0x6D: 'ESA', 0x7D: 'EDL'
}
for addr in range(0x80):
    v1 = data1[DSP_OFFSET + addr]
    v2 = data2[DSP_OFFSET + addr]
    if v1 != v2:
        name = globals_names.get(addr, f'R{addr:02X}')
        print(f"  ${addr:02X} {name}: ${v1:02X} -> ${v2:02X}")
