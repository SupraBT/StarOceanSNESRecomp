"""
Correct analysis: Voice 5 registers are at $50-$57, NOT $28-$2F.
$28-$2F are Voice 2 registers.
"""
import struct

def dump_voice_regs(data, label):
    print(f"\n=== {label} ===")
    for ch in range(8):
        base = ch * 16
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
        attack_rate = adsr1 & 0x0F
        decay_rate = (adsr1 >> 4) & 0x07
        sustain_level = ((adsr2 >> 5) + 1) * 0x100
        sustain_rate = adsr2 & 0x1F
        
        gain_mode = gain >> 5 if (gain & 0x80) else -1  # -1 = direct
        gain_val = gain & 0x7F
        
        print(f"  V{ch}: VOLL=${voll:02X} VOLR=${volr:02X} PITCH=${pitchh:02X}{pitchl:02X} "
              f"SRCN=${srcn:02X} ADSR1=${adsr1:02X} ADSR2=${adsr2:02X} GAIN=${gain:02X} "
              f"ENVX=${envx:02X} OUTX=${outx:02X}"
              f"{' [ADSR]' if adsr_enabled else '[GAIN]'}"
              f" ATK={attack_rate} D={decay_rate} SL=${sustain_level:03X} SR={sustain_rate}")

# Read both SPC dumps
with open('F:/StarOceanRecompRAID/run-trace/spc_f10050.bin', 'rb') as f:
    data1 = f.read()
with open('F:/StarOceanRecompRAID/run-trace/spc_f10200.bin', 'rb') as f:
    data2 = f.read()

print(f"Dump 1 size: {len(data1)} bytes")
print(f"Dump 2 size: {len(data2)} bytes")

dump_voice_regs(data1, "Frame ~10050 (before beep)")
dump_voice_regs(data2, "Frame ~10200 (during/after beep)")

# Focus on voice 5 differences
print("\n=== Voice 5 DIFFERENCES (f10200 vs f10050) ===")
base5 = 5 * 16
reg_names = ['VOLL', 'VOLR', 'PITCHL', 'PITCHH', 'SRCN', 'ADSR1', 'ADSR2', 'GAIN', 'ENVX', 'OUTX']
for i in range(16):
    if i < len(reg_names):
        name = reg_names[i]
    else:
        name = f"R{i:02X}"
    v1 = data1[base5 + i]
    v2 = data2[base5 + i]
    if v1 != v2:
        print(f"  ${base5+i:02X} {name}: ${v1:02X} -> ${v2:02X}  {'*** CHANGED ***'}")
    else:
        print(f"  ${base5+i:02X} {name}: ${v1:02X} (same)")

# Also check voice 2 (where $28-$2F registers actually are)
print("\n=== Voice 2 (registers $20-$2F) DIFFERENCES ===")
base2 = 2 * 16
for i in range(16):
    if i < len(reg_names):
        name = reg_names[i]
    else:
        name = f"R{i:02X}"
    v1 = data1[base2 + i]
    v2 = data2[base2 + i]
    if v1 != v2:
        print(f"  ${base2+i:02X} {name}: ${v1:02X} -> ${v2:02X}  {'*** CHANGED ***'}")

# Check all voices that changed
print("\n=== ALL changed registers between dumps ===")
for addr in range(min(len(data1), len(data2))):
    if data1[addr] != data2[addr]:
        ch = addr >> 4
        offset = addr & 0x0F
        if offset < len(reg_names):
            name = reg_names[offset]
        else:
            name = f"R{offset:02X}"
        print(f"  ${addr:02X} V{ch}.{name}: ${data1[addr]:02X} -> ${data2[addr]:02X}")
