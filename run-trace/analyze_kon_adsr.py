import re

trace_file = 'F:/Recompilador Super Nintendo/StarOceanTest2/Star Ocean (Japan)-trace.log'

# Also check ADSR/GAIN for voice 5 and all KON writes
reg_names = {
    '28': 'VOLL5', '29': 'VOLR5', '2a': 'PITCH5L', '2b': 'PITCH5H',
    '2c': 'SRCN5', '2d': 'ADSR1_5', '2e': 'ADSR2_5', '2f': 'GAIN5',
    '4c': 'KON', '5c': 'KOF'
}
target_regs = set(reg_names.keys())

writes = []
line_num = 0

with open(trace_file, 'r', errors='ignore') as f:
    for line in f:
        line_num += 1
        if '0f2' in line and '#$' in line:
            match = re.search(r'#\$([0-9a-fA-F]{2})', line)
            if match:
                reg = match.group(1).lower()
                if reg in target_regs:
                    writes.append((line_num, reg, line.strip()))
        
        if line_num > 2000000:
            break

# Show only non-SRCN5 writes (the interesting ones)
print(f'Total writes to target regs: {len(writes)}')
print(f'\n--- Non-SRCN5 writes (KON, KOF, ADSR, GAIN, VOL) ---')
for i, (ln, reg, line) in enumerate(writes):
    if reg != '2c':  # Skip SRCN5 (the pitch modulation loop)
        print(f'{i+1}. Line {ln} [{reg_names.get(reg, reg)}]: {line}')
