import re

trace_file = 'F:/Recompilador Super Nintendo/StarOceanTest2/Star Ocean (Japan)-trace.log'

# Track DSP address/data register pairs
# Pattern: write to $0f2 (address), then write to $0f3 (data)
dsp_state = {}  # track current register being addressed
dsp_writes = []
line_num = 0
current_addr = None

with open(trace_file, 'r', errors='ignore') as f:
    for line in f:
        line_num += 1
        
        # Detect writes to $0f2 (DSP address register) 
        # Could be: mov $0f2, #XX / mov $0f2, a / mov $0f2, $XX
        if re.search(r'mov\s+\$0f2\b', line):
            # Extract the value being written
            # Immediate: mov $0f2, #$XX
            m_imm = re.search(r'mov\s+\$0f2,\s*#\$([0-9a-fA-F]{2})', line)
            # Register: mov $0f2, a (value is in A)
            m_a = re.search(r'mov\s+\$0f2,\s*a\b', line)
            
            if m_imm:
                current_addr = int(m_imm.group(1), 16)
            elif m_a:
                # Extract A value from the register state at end of line
                m_reg = re.search(r'A:([0-9a-fA-F]{4})', line)
                if m_reg:
                    current_addr = int(m_reg.group(1), 16) & 0xFF
        
        # Detect writes to $0f3 (DSP data register)
        if re.search(r'mov\s+\$0f3\b', line) and current_addr is not None:
            # Extract the value being written
            m_imm = re.search(r'mov\s+\$0f3,\s*#\$([0-9a-fA-F]{2})', line)
            m_a = re.search(r'mov\s+\$0f3,\s*a\b', line)
            m_ind = re.search(r'mov\s+\$0f3,\s*\$([0-9a-fA-F]{2})', line)
            
            value = None
            if m_imm:
                value = int(m_imm.group(1), 16)
            elif m_a:
                m_reg = re.search(r'A:([0-9a-fA-F]{4})', line)
                if m_reg:
                    value = int(m_reg.group(1), 16) & 0xFF
            elif m_ind:
                # This reads from SPC RAM, we can't easily resolve
                pass
            
            if value is not None:
                # Voice 5 registers: $28-$2F
                if 0x28 <= current_addr <= 0x2F:
                    reg_names = {
                        0x28: 'VOLL5', 0x29: 'VOLR5', 0x2A: 'PITCH5L', 0x2B: 'PITCH5H',
                        0x2C: 'SRCN5', 0x2D: 'ADSR1_5', 0x2E: 'ADSR2_5', 0x2F: 'GAIN5'
                    }
                    dsp_writes.append((line_num, current_addr, value, reg_names.get(current_addr, f'${current_addr:02X}'), line.strip()))
                # KON/KOF
                elif current_addr in (0x4C, 0x5C):
                    reg_names = {0x4C: 'KON', 0x5C: 'KOF'}
                    dsp_writes.append((line_num, current_addr, value, reg_names[current_addr], line.strip()))
        
        if line_num > 5100000:
            break

print(f'Found {len(dsp_writes)} relevant DSP writes')
print()
for i, (ln, addr, val, name, line) in enumerate(dsp_writes):
    print(f'{i+1}. Line {ln} [{name}] = ${val:02X}: {line}')
