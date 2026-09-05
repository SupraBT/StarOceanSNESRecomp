#!/usr/bin/env python3
"""Inspect the freeze sweep SPC dumps: verify they are distinct moments and show
per-voice DSP registers (correct SPC offset 0x10100)."""
import os, struct

WORK = r"F:\StarOceanRecompRAID\run-trace"
files = sorted(f for f in os.listdir(WORK) if f.startswith("sweep_f") and f.endswith(".bin"))
print("sweep files:", len(files))

def dsp_regs(path):
    d = open(path, "rb").read()
    assert d[:4] == b"SNES", (path, d[:16])
    return d[0x10100:0x10100 + 128]

def voice_state(regs, v):
    base = v * 0x10
    voll, volr = regs[base], regs[base + 1]
    pitch = regs[base + 2] | (regs[base + 3] << 8)
    srcn = regs[base + 4]
    adsr0 = regs[base + 5]
    gain = regs[base + 7]
    envx = regs[base + 8] & 0x7f if False else regs[base + 8]
    outx = regs[base + 9]
    return voll, volr, pitch & 0x3fff, srcn, adsr0, gain, envx, outx

for f in files:
    regs = dsp_regs(os.path.join(WORK, f))
    # global regs: MVOL L=0x0c, MVOL R=0x1c, KON=0x4c, KOF=0x5c, FLG=0x6c, ENDX=0x7c
    mvl, mvr = regs[0x0c], regs[0x1c]
    print("\n== %s  mvol L=%02x R=%02x" % (f, mvl, mvr))
    for v in range(8):
        voll, volr, pitch, srcn, adsr0, gain, envx, outx = voice_state(regs, v)
        print("  v%d  volL=%02x volR=%02x pitch=%04x srcn=%02x adsr0=%02x gain=%02x envx=%02x outx=%02x"
              % (v, voll, volr, pitch, srcn, adsr0, gain, envx, outx))
