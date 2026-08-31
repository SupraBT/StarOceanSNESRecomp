import re

path = r'E:\Recompilador Super Nintendo\Star Ocean (Japan)-trace.log'
writes = []
with open(path, 'rb') as f:
    for i, line in enumerate(f):
        if b'2105' in line:
            m = re.search(rb'([0-9a-f]{6}) (sta|stz)\s+\$2105\s+\[002105\] A:([0-9a-f]{4})', line)
            if m:
                fm = re.search(rb'V:(\d+) H:(\d+) F:(\d+)', line)
                writes.append((i, m.group(1).decode(), m.group(2).decode(), m.group(3).decode(),
                               (fm.group(1).decode() if fm else '?'),
                               (fm.group(2).decode() if fm else '?'),
                               (fm.group(3).decode() if fm else '?')))
print('Escrituras BGMODE $2105 (%d):' % len(writes))
for w in writes:
    print('  L%d: %s %s $2105 A=%s V=%s H=%s F=%s' % w)
