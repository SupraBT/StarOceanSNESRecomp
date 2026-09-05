import re
import sys

trace_file = 'F:/Recompilador Super Nintendo/StarOceanTest2/Star Ocean (Japan)-trace.log'

# Voice 5 DSP registers
reg_names = {
    '28': 'VOLL5', '29': 'VOLR5', '2a': 'PITCH5L', '2b': 'PITCH5H',
    '2c': 'SRCN5', '2d': 'ADSR1_5', '2e': 'ADSR2_5', '2f': 'GAIN5'
}
target_regs = set(reg_names.keys())

voice5_writes = []
line_num = 0

with open(trace_file, 'r', errors='ignore') as f:
    for line in f:
        line_num += 1
        # Look for mov $0f2, #$XX where XX is a voice 5 register
        if '0f2' in line and '#$' in line:
            match = re.search(r'#\$([0-9a-fA-F]{2})', line)
            if match:
                reg = match.group(1).lower()
                if reg in target_regs:
                    voice5_writes.append((line_num, reg, line.strip()))
        
        if line_num > 5000000:
            break

print(f'Found {len(voice5_writes)} Voice 5 register writes in first {line_num} lines')
for i, (ln, reg, line) in enumerate(voice5_writes):
    print(f'{i+1}. Line {ln} [{reg_names.get(reg, reg)}]: {line}')
