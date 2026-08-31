# Snaggletooth x Star Ocean Recompiler - Comparative Findings

> **Document purpose:** Technical findings from analyzing the Snaggletooth
> documentation (etroimcasso/Snaggletooth, ci/snes-ipl-and-blargg/docs)
> against our Star Ocean SNES recompilation project.
>
> **Project:** StarOceanTest2 - static recompilation of Star Ocean (Japan)
> targeting native C/C++, with 65816 interpreter, S-DD1 decompression,
> PPU renderer, and SPC700 audio subsystem.

**Date:** 2026-08-29

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [What Snaggletooth Is and What It Is Not](#2-what-snaggletooth-is)
3. [65816 CPU Core: Confirmation and Timing Divergence](#3-65816-cpu-core)
4. [APU / SPC700: Architecture Match and Gaps](#4-apu-spc700)
5. [S-DSP: Sample-Exact Reference We Do Not Have Yet](#5-s-dsp)
6. [DMA / HDMA: Validated Against Our Own Fix](#6-dma-hdma)
7. [PPU: Where We Go Beyond Snaggletooth](#7-ppu)
8. [Specific Star Ocean Findings](#8-star-ocean-findings)
9. [Actionable Recommendations](#9-recommendations)
10. [Appendix: Document Inventory](#10-appendix)

---

## 1. Executive Summary

Snaggletooth is a clean-room, MIT-licensed SNES virtual machine (5A22 + SPC700)
with cycle-exact documentation across 8 markdown files. Our Star Ocean
recompilation project shares the same hardware target but approaches it from
the opposite direction: converting a real 6MB LoROM game with S-DD1 coprocessor
to native C/C++.

**Key results:**

- **Bus model and cycle costs align.** Memory speeds (fast=6, slow=8, extra-slow=12
  master cycles) match what our cosim framework validated against bsnes-plus.
- **DMA/HDMA behavior confirmed.** Our 8-channel HDMA fix is consistent with the spec.
- **APU architecture is the same.** Our SPC700 core, timer system, and communication
  ports follow the same model, though Snaggletooth is more precisely tested.
- **DSP is our biggest gap.** Snaggletooth documents the S-DSP pipeline sample-by-sample
  with hardware-proven corrections to published docs. Our DSP produces correct audio
  but has not been validated at sample-exact granularity.
- **PPU is where we exceed Snaggletooth.** Snaggletooth explicitly does not render.
  Our ppu.c handles modes 0-7 with priority/z-buffer and HDMA per-scanline effects.
- **S-DD1 coprocessor is unique to us.** Snaggletooth does not model coprocessors.
  Our sdd1.c is validated byte-for-byte (24/24 chunks).

---

## 2. What Snaggletooth Is and What It Is Not

Snaggletooth is an embeddable SNES machine, not an emulator. It has:

- **65816 CPU core** -- cycle-stepped interpreter over abstract SnesBus concept,
  all 256 opcodes, full emulation/native mode, every dummy read documented.
- **APU machine** -- SPC700 core (all 256 opcodes) in 64KB RAM, register overlay,
  3 timers, communication ports, boot-ROM window.
- **S-DSP** -- BRR decode, Gaussian interpolation, ADSR/GAIN envelopes, echo
  delay line with 8-tap FIR, noise generator, pitch modulation.
- **SNES machine** -- LoROM memory map, clock, video counters, NMI/IRQ,
  multiply/divide, PPU register file (no rendering), DMA/HDMA.
- **Tools** -- SPC700 disassembler (trace-based), SPC render tool (.spc to WAV).

**What it does NOT have:**
- PPU renderer (no pixel output)
- Cartridge coprocessors (S-DD1, SA-1, SuperFX, DSP-1, etc.)
- Cycle-exact trace of a specific game
- Static recompilation infrastructure

---

## 3. 65816 CPU Core: Confirmation and Timing Divergence

### 3.1 What Snaggletooth Documents

| Rule | Snaggletooth | Our Project |
|------|-------------|-------------|
| 16-bit access costs one extra cycle vs 8-bit | Documented | Modeled in interp816 |
| Direct-page non-zero low byte adds one cycle | Documented | Modeled |
| Page-crossing cycle on indexed reads (8-bit index only) | Documented | Modeled |
| REP settles status on the last cycle (runs under old widths) | Documented | Verified via cosim |
| Emulation mode RMW middle cycle writes the old byte | Documented | Modeled |
| Open bus behavior for unmapped addresses | Documented | Partial |

### 3.2 Timing Divergence Found in Cosim

Our cosim framework (Track A: so_cosim vs so_cosim_ref) detected that
the A-side and B-side interpreters diverge on hPos after ~64 opcodes.
Root cause: our interp816 bridge counts internal cycles as 6x (fast rate)
while the reference uses 8x slowROM for ROM accesses. This 2-cycle drift
per ROM access accumulates over ~100 instructions, shifting hPos by ~600
dots, which changes the branch at vblank poll /usr/bin/bash0:F6F5.

Snaggletooth confirms ROM region speed depends on MEMSEL (20D):
- MEMSEL clear (power-on default) = slow (8 master cycles)
- MEMSEL set = fast (6 master cycles)

### 3.3 Implications

Cosmetic for the current build but fatal for cycle-exact recompilation.
Snaggletooth per-instruction cycle tables provide the reference needed to
audit our bridge timing.

---

## 4. APU / SPC700: Architecture Match and Gaps

### 4.1 Boot ROM Window

Snaggletooth offers three modes: IPL stub (default, runs upload handshake),
custom boot ROM (64-byte real dump for test ROMs), or no boot (host loads
driver directly). Our project uses HLE (apu_waitForTransferReady +
apu_finishHleTransfer). Works for Star Ocean since it never verifies boot
ROM bytes.

### 4.2 Timer System

3-stage architecture: Stage 1 (master counter, fixed tick slots), Stage 2
(8-bit counter to TARGET), Stage 3 (4-bit output, cleared on read).
Critical: ticks align to DSP sample frame slots (Timer 2: every 16 cycles;
Timers 0/1: every 128 cycles).

Our Timer struct uses a simpler model. Sufficient for Star Ocean (Timer 0
at 128-cycle base), but Timer 2 slot alignment matters for other games.

### 4.3 Communication Ports

Same model: 8 latches, double-buffered. We add a timestamped port queue
(portQueue) mapping guest APU cycles to host audio time for multi-threaded
CPU/SPC execution.

---

## 5. S-DSP: Sample-Exact Reference We Do Not Have Yet

### 5.1 Corrections to Published Documentation

| Correction | Published Says | Hardware Does |
|-----------|---------------|---------------|
| Attack ends at fixed E0 | fullsnes | Switches when candidate leaves 11-bit range |
| Decay sustain boundary from ADSR2 | Both docs | Under GAIN mode reads GAIN bits 7-5 (garbage) |
| Bent-Increase ref clipped to 11 bits | Both docs | Unclipped; 12+ bits of precision matter |
| Key-on produces 5 silent samples | Both docs | 6 silent samples (apply-before-update order) |
| 128kHz ceiling is step cap | fullsnes | Position clamp at FFF, not step cap |
| Soft reset shields key-on sample | Undocumented | FLG.7 pulse on KON consumption = KON wins |

### 5.2 Our DSP Status

Implemented: BRR decode (4 filters), Gaussian interpolation, ADSR+GAIN,
echo/FIR, noise LFSR, key-on/off, pitch modulation.

Not verified: envelope apply-before-update order, key-on walk/hold logic,
intra-sample 32-slot schedule, Bent-Increase unclipped reference, soft-reset
shield. Impact for Star Ocean: low (standard ADSR, no rapid re-keying).

---

## 6. DMA / HDMA: Validated Against Our Own Fix

### 6.1 Snaggletooth Specification

- 8 transfer patterns (0-7) with specific B-bus offsets
- 8 master cycles per byte regardless of region
- CPU halted during DMA, lowest channel first
- Byte count 0 = 65536 bytes
- DMA bank fixed within bank, never crosses
- DMA cannot reach A-bus registers (100-1FF, 000-1FF, etc.)
- HDMA table: line-count byte (/usr/bin/bash0=stop, /usr/bin/bash1-0=write+wait, 1-=repeat)
- HDMA re-initializes every frame, deactivates at vblank

### 6.2 Our Fix (2026-08-24)

Star Ocean name menu uses 8 HDMA channels; we only had channels 5-7:
- CH1 (mode=3, bAdr=1): CGRAM address+data per scanline (color gradient)
- CH2 (mode=2, bAdr=2): BG4SC per scanline (tilemap base change)

All 8 channels now initialized. Regression test PASS (hashes identical frame 236).

---

## 7. PPU: Where We Go Beyond Snaggletooth

Snaggletooth: 'There is no rendering PPU, but the register file that feeds
one is here so a program can fill video memory and a host can read what it drew.'

Our ppu.c: complete renderer with Modes 0-7, z-buffer priority system
(BG4-0 fix: 0x0300 to 0x0900), BG1-BG4 tiles, HDMA per-scanline effects,
OAM sprites, color math, forced blank, Mode 7 affine.

Documented VRAM prefetch (first read returns same word twice) should be
verified in our PPU.

---

## 8. Specific Star Ocean Findings

### 8.1 S-DD1 Coprocessor

6MB LoROM with S-DD1 decompression. Our sdd1.c: IM/GCD/BG/PEM/CM/OL +
MMC page mapping (804-807). Validated: **24/24 chunks matched**
across 3 paths (block, DMA, CPU window read). This is unique to our project.

### 8.2 Game-Specific Timing

- Vblank poll at /usr/bin/bash0:F6F5 (49% of trace): LDA 212 = branch
- Mode 1 (gameplay) to Mode 0 (name menu) at V=225 (vblank)
- 14/14 PPU registers identical to bsnes (compare_menu_setup.py)
- 14/14 register write timing at same V-position (compare_timing_vh.py)

### 8.3 Deterministic Execution

Regression test proves frame-exact determinism: VRAM/CGRAM/WRAM hashes
byte-identical across runs. Reference: frame 236, ~14s per run.

### 8.4 bsnes Libretro Finding

Our runner produces more faithful output than bsnes libretro for Star Ocean.
bsnes libretro gets stuck at :F419 without NMI or VRAM writes. Our
runner correctly loads tiles via S-DD1 DMA. bsnes-plus accuracy build
remains our oracle reference.

---

## 9. Actionable Recommendations

### High Priority
1. Audit interp816 cycle costs against Snaggletooth tables (resolve hPos drift)
2. Verify VRAM prefetch behavior (first read returns same word twice)
3. Verify DMA cannot reach A-bus registers (correctness for general SNES)

### Medium Priority
4. Implement DSP intra-sample 32-slot schedule (diagnostic quality)
5. Extract real SPC700 IPL boot ROM from .spc dump (replace HLE)
6. Validate SPC700 opcode timing against SingleStepTests vectors

### Low Priority
7. Envelope apply-before-update verification test
8. Key-on walk/hold logic (needed for general SPC compat)
9. SPC render tool (.spc to WAV) for audio debugging

---

## 10. Appendix: Snaggletooth Document Inventory

| File | Topic | Relevance |
|------|-------|-----------|
| snes-machine.md | SNES machine: memory map, clocks, DMA/HDMA | High - validates bus model |
| 65816-cpu.md | CPU core: all opcodes, cycle-by-cycle | High - interp816 audit reference |
| apu-machine.md | APU: SPC700, timers, ports, boot-ROM | High - confirms APU architecture |
| spc700-cpu.md | SPC700: all 256 opcodes, cycle-by-cycle | High - spc.c validation reference |
| dsp.md | S-DSP: full pipeline, BRR, Gaussian, echo | Critical - biggest validation gap |
| s-dsp-behavior.md | Hardware corrections (Blargg test ROMs) | Critical - corrects fullsnes/Anomie |
| spc-rendering.md | .spc dump to WAV rendering tool | Medium - diagnostic tool |
| spc700-disassembler.md | Trace-based SPC700 disassembler | Low - SPC driver analysis |
| spc700-assembly.md | SPC700 assembly dialect | Low - SPC driver patches |

---

*Generated by analyzing Snaggletooth docs (ci/snes-ipl-and-blargg branch,
August 2026) cross-referenced with StarOceanTest2 source, cosim results,
and ENCICLOPEDIA.md.*
