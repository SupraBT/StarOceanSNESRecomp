import re

trace_file = 'F:/Recompilador Super Nintendo/StarOceanTest2/Star Ocean (Japan)-trace.log'

# Track ALL $0F2/$0F3 writes
line_num = 0
current_addr = None
all_dsp_writes = []

with open(trace_file, 'r', errors='ignore') as f:
    for line in f:
        line_num += 1
        
        # Detect writes to $0f2
        if re.search(r'mov\s+\$0f2\b', line):
            m_imm = re.search(r'mov\s+\$0f2,\s*#\$([0-9a-fA-F]{2})', line)
            m_a = re.search(r'mov\s+\$0f2,\s*a\b', line)
            
            if m_imm:
                current_addr = int(m_imm.group(1), 16)
            elif m_a:
                m_reg = re.search(r'A:([0-9a-fA-F]{4})', line)
                if m_reg:
                    current_addr = int(m_reg.group(1), 16) & 0xFF
        
        # Detect writes to $0f3
        if re.search(r'mov\s+\$0f3\b', line) and current_addr is not None:
            m_imm = re.search(r'mov\s+\$0f3,\s*#\$([0-9a-fA-F]{2})', line)
            m_a = re.search(r'mov\s+\$0f3,\s*a\b', line)
            
            value = None
            if m_imm:
                value = int(m_imm.group(1), 16)
            elif m_a:
                m_reg = re.search(r'A:([0-9a-fA-F]{4})', line)
                if m_reg:
                    value = int(m_reg.group(1), 16) & 0xFF
            
            if value is not None:
                all_dsp_writes.append((line_num, current_addr, value))
        
        if line_num > 5100000:
            break

# Filter for KON writes where voice 5 (bit 5 = $20) is set
print(f"Total DSP writes tracked: {len(all_dsp_writes)}")
print()

# KON writes with voice 5 active
kon_voice5 = [(ln, addr, val) for ln, addr, val in all_dsp_writes if addr == 0x4C and (val & 0x20)]
print(f"KON writes with voice 5 (bit 5) set: {len(kon_voice5)}")
for i, (ln, addr, val) in enumerate(kon_voice5):
    voices = []
    for v in range(8):
        if val & (1 << v):
            voices.append(f"V{v}")
    print(f"  Line {ln}: KON=${val:02X} -> {', '.join(voices)}")

# All VOLR5 writes (direct or indirect)
print()
vol5_writes = [(ln, addr, val) for ln, addr, val in all_dsp_writes if addr == 0x29]
print(f"Direct VOLR5 ($29) writes: {len(vol5_writes)}")
for ln, addr, val in vol5_writes:
    print(f"  Line {ln}: VOLR5 = ${val:02X}")

# All ADSR1_5 writes
adsr1_writes = [(ln, addr, val) for ln, addr, val in all_dsp_writes if addr == 0x2D]
print(f"\nDirect ADSR1_5 ($2D) writes: {len(adsr1_writes)}")
for ln, addr, val in adsr1_writes:
    print(f"  Line {ln}: ADSR1_5 = ${val:02X}")

# All GAIN5 writes
gain5_writes = [(ln, addr, val) for ln, addr, val in all_dsp_writes if addr == 0x2F]
print(f"\nDirect GAIN5 ($2F) writes: {len(gain5_writes)}")
for ln, addr, val in gain5_writes:
    print(f"  Line {ln}: GAIN5 = ${val:02X}")

# All KON writes (non-zero)
print(f"\nAll non-zero KON writes: {len([x for x in all_dsp_writes if x[1] == 0x4C and x[2] != 0])}")
for ln, addr, val in all_dsp_writes:
    if addr == 0x4C and val != 0:
        voices = []
        for v in range(8):
            if val & (1 << v):
                voices.append(f"V{v}")
        print(f"  Line {ln}: KON=${val:02X} -> {', '.join(voices)}")

# All KOF writes
kof_writes = [(ln, addr, val) for ln, addr, val in all_dsp_writes if addr == 0x5C]
print(f"\nAll non-zero KOF writes: {len([x for x in kof_writes if x[2] != 0])}")
for ln, addr, val in kof_writes:
    if val != 0:
        voices = []
        for v in range(8):
            if val & (1 << v):
                voices.append(f"V{v}")
        print(f"  Line {ln}: KOF=${val:02X} -> {', '.join(voices)}")
