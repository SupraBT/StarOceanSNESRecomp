#!/usr/bin/env python3
#
#   *** NO VALIDADO / LAYOUT NO CONFIRMADO — NO USAR para generar inputs de A/B. ***
#   El modelo "stride 64 + joypad en byte +24" se verifico de forma cruzada como
#   INCORRECTO para estos .bsv: las lecturas de +24/+25 presentan 255-256 valores
#   distintos (firma de savestate denso, no de joypad, que tiene <=16). Los
#   "0x01" vistos al inicio eran un artefacto del savestate, NO un stream de
#   botones. Usar este conversor produciria inputs falsos y romperia el A/B.
#   La via fiable verificada es el input-log en vivo (SNESRECOMP_INPUT_LOG /
#   live_inputs.log -> grabacion_inputs.txt), no el parseo del .bsv.
#   Este archivo se conserva como borrador, NO como herramienta funcional.
#
"""
bsv_to_inputs.py — [NO VALIDADO] intento de conversion bsnes-plus BSV1 -> frame hexmask.

VER HDR: el layout (stride 64 / joypad en +24) QUEDO DESCARTADO por diagnostico
(firma distinct=256 = savestate). NO producir inputs con esto.
"""

Output (frame hexmask):
  "frame  hexmask\n" per line, only on pad-mask *changes*:
      108 00000100
      116 00000000
  This matches build-cosim/grabacion_inputs.txt and SNESRECOMP_REPLAY_FILE.

USAGE:
  python bsv_to_inputs.py <input.bsv> [output.txt]
"""

import sys, os

STRIDE = 64
IP = 0x18          # joypad byte offset within slot (+24)
MIN_HELD = 3       # consecutive identical non-zero bytes => a held button

# recomp mask bit order: B=0x001 Y=0x002 Select=0x004 Start=0x008 Up=0x010
# Down=0x020 Left=0x040 Right=0x080 A=0x100 X=0x200 L=0x400 R=0x800
# bsnes serialized low byte (bits): B0 Y1 Select2 Start3 Up4 Down5 Left6 Right7
def bsnes_b0_to_mask(b0):
    m = 0
    if b0 & 0x01: m |= 0x001
    if b0 & 0x02: m |= 0x002
    if b0 & 0x04: m |= 0x004
    if b0 & 0x08: m |= 0x008
    if b0 & 0x10: m |= 0x010
    if b0 & 0x20: m |= 0x020
    if b0 & 0x40: m |= 0x040
    if b0 & 0x80: m |= 0x080
    return m


def scan(path):
    d = open(path, 'rb').read()
    n = len(d)
    # For every candidate (off-0x18)%64==0, read b0 and b1.
    samples = []  # (slot, off, b0, b1)
    for i in range(0x4000, n - STRIDE):
        if (i - IP) % STRIDE == 0:
            slot = (i - IP) // STRIDE
            b0 = d[i]
            b1 = d[i + 1] if i + 1 < n else 0
            if b0 != 0 or b1 != 0:
                samples.append((slot, b0, b1))
    samples.sort()
    return d, n, samples


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    inp = sys.argv[1]
    outp = sys.argv[2] if len(sys.argv) > 2 else None
    d, n, samples = scan(inp)
    print('file: %s (%d bytes), candidate joypad slots: %d' % (os.path.basename(inp), n, len(samples)))

    # Find contiguous runs in SLOT space where b0 is constant non-zero (held key).
    # Walk samples; a run is consecutive-slots with same b0.
    if not samples:
        print('no samples'); return
    runs = []
    cur = [samples[0]]
    for s, b0, b1 in samples[1:]:
        if s == cur[-1][0] + 1 and b0 == cur[-1][1]:
            cur.append((s, b0, b1))
        else:
            if len(cur) >= MIN_HELD and cur[0][1] != 0:
                runs.append(cur)
            cur = [(s, b0, b1)]
    if len(cur) >= MIN_HELD and cur[0][1] != 0:
        runs.append(cur)

    print('held-runs (>=%d consecutive identical joypad bytes): %d' % (MIN_HELD, len(runs)))
    if runs:
        bylen = sorted(runs, key=len, reverse=True)
        for r in bylen[:12]:
            print('  held run value=0x%02x slots[%d..%d] len=%d off=0x%x'
                  % (r[0][1], r[0][0], r[-1][0], len(r), r[0][0]*STRIDE+IP))
        # choose the stream region spanned by the longest held run
        best = bylen[0]
    else:
        # fallback: no held runs -> maybe only brief taps; pick the densest cluster
        print('WARN: no held runs; will use the widest span of any joypad slots')
        best = None

    # Emit events over a contiguous window [lo,hi] that contains the chosen run.
    # We expand to the whole contiguous-slot extent around it (including idle slots).
    if best is not None:
        lo = best[0][0]
        hi = best[-1][0]
        # expand lo/hi a little to include leading idle frames before first press
        # (but don't overshoot into savestate). Use the full contiguous extent of
        # all candidate slots that lie within a guard margin around the run.
        # Simpler: take lo = first slot of the run minus held-run idle gap is
        # unknown, so leave lo/hi as the run and note frames start there.
        # Emit events from lo..hi reading b0 every slot (idle slots = b0 0).
        print('stream window: slots[%d..%d]' % (lo, hi))
        by = {}
        for s, b0, b1 in samples:
            if lo <= s <= hi:
                by[s] = b0
        events = []
        prev = 0
        for sl in range(lo, hi + 1):
            b0 = by.get(sl, 0)
            m = bsnes_b0_to_mask(b0)
            if m != prev:
                events.append((sl, m))
                prev = m
        print('emitted %d change events' % len(events))
        for (sl, m) in events[:30]:
            print('  %d %08x' % (sl, m))
        if outp:
            with open(outp, 'w') as f:
                for (sl, m) in events:
                    f.write('%d %08x\n' % (sl, m))
            print('wrote %s' % outp)


if __name__ == '__main__':
    main()