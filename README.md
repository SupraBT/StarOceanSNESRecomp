# Star Ocean (Japan) — SNES Recompilation

A native, playable reimplementation of **Star Ocean** (Super Famicom, 1996,
tri-Ace / Enix) built with **static recompilation**: the game's 65816 code is
translated ahead-of-time to C and compiled into a native Windows executable,
while uncovered code runs through a precise LLE interpreter bridge.

> ⚠️ This repository contains **no ROM and no ROM-derived assets**. You must
> supply your own original dump of *Star Ocean (Japan)* to build and run the
> game. See [Legal](#legal).

## Status

The port is playable end-to-end for the early game and is under active
development:

- Intro, ship, village (field), chests and the first battles run with music and
  sound, gamepad or keyboard input, at (near) 60 FPS.
- The recompiled core is **deterministic**: every change is validated with an
  A/B harness that replays a recorded 23,700-frame session and compares
  per-frame master-cycle counts against the pure LLE interpreter. The current
  baseline is byte-exact (0 / 23,700 frames differ).
- Performance work includes cycle-accurate fast paths for SPC-upload and APU
  spin loops (`SPCFF` / `CCFF` / `PUMPFF`), which removed the worst village
  load stalls (e.g. ~193 ms → ~61 ms on the heaviest frame).

Known gaps and the development roadmap are tracked in
[`docs/BUILD.md`](docs/BUILD.md) and `Datos Importantes de Consulta.md`
(Spanish, internal reference).

## How it works

```
config/  (bank profiles + funcs.h)          snesrecomp/  (framework submodule)
         \                                        /
          +-- ROM (not in repo) --> generated/*.c (AOT banks)
                                           |
                           CMakeLists.txt + snesrecomp/runner
                                           |
                                        StarOcean.exe
```

- `snesrecomp/` — the full framework (runner + AOT generator + native analyzer),
  pinned as a git submodule to
  [SupraBT/snesrecomp](https://github.com/SupraBT/snesrecomp) (a customized
  fork of [mstan/snesrecomp](https://github.com/mstan/snesrecomp)) at the
  commit carrying the Star Ocean spin fast-paths and the clean-build gating.
- `generated/` — **not committed**. It is produced from your ROM by the
  regeneration script (see below) and contains translated code only.

## Repository layout

```
CMakeLists.txt            Executable build (SNESRECOMP_CLEAN_BUILD for release)
config/                   AOT profiles (bank*.cfg) + funcs.h  → generator input
src/                      Game host (main, so_rtl, SPC player, state file, …)
snesrecomp/               Framework submodule (runner + toolchain + analyzer)
tools/regenerate_aot.ps1  Regenerates generated/ from your ROM
docs/                     Submodule notes + build/reproducibility notes
```

## Requirements

| Tool | Needed for |
| --- | --- |
| Windows 10/11 + Visual Studio 2022 (MSVC) | building the executable |
| CMake | building |
| SDL3 development files | building (pass `-DSDL3_DIR=…`) |
| Python 3 + Rust/cargo | only if you need to **regenerate** `generated/` |
| Original *Star Ocean (Japan)* ROM | regeneration **and** running |

## Build (quick start)

```powershell
# 1. Clone with submodules
git clone --recursive https://github.com/SupraBT/StarOceanSNESRecomp.git
cd StarOceanSNESRecomp
git submodule update --init --recursive

# 2. Configure (Release build without dev instrumentation)
cmake -S . -B build -G "Visual Studio 17 2022" `
      -DSNESRECOMP_CLEAN_BUILD=ON -DSNESRECOMP_SDL_BACKEND=SDL3 `
      -DSDL3_DIR="<path-to>\SDL3-3.2.4\cmake"

# 3. Build
cmake --build build --config Release
```

`SNESRECOMP_CLEAN_BUILD=ON` compiles out all dev monitoring (loggers, frame
markers, trace hooks) for a production executable. Omit it if you want the
instrumented development build.

### First-time setup of `generated/` (requires your ROM)

`generated/` is empty after a fresh clone. Put your original *Star Ocean
(Japan)* ROM in the repository root and run:

```powershell
.\tools\regenerate_aot.ps1 -RomPath ".\Star Ocean (Japan).sfc" -InPlace
```

The script verifies the ROM SHA-1 against the expected authentic dump
(`A616EE3466256482BC0ADC11F1FDA7C30E66EF8D`) and refuses obviously patched or
renamed dumps.

### Run

Put the ROM next to `StarOcean.exe` and create a `rom.cfg` file containing the
ROM file name (or full path). Launch the executable; gamepad and keyboard are
both supported (see `keybinds.ini` once generated).

## Reproducibility

The published source tree is byte-identical to the working tree of the
validated build (see the A/B result above). One caveat is documented in
[`docs/BUILD.md`](docs/BUILD.md): regenerating `generated/` with the *current*
generator produces a state that is not yet byte-exact against the validated
snapshot (the generator gained new LLE-yield guards after the snapshot was
taken). Revalidation of the regeneration recipe is the next open item.

## Acknowledgments

- [mstan/snesrecomp](https://github.com/mstan/snesrecomp) — the SNES
  recompilation framework this project builds on.
- [mstan](https://github.com/mstan)'s snesrecomp-tool — AOT generator.
- The recompilation community (n64recomp lineage) for the underlying
  recompiler techniques.

## Legal

Star Ocean is a registered trademark of its respective owners (tri-Ace /
Enix). This project is an unofficial, non-commercial reimplementation created
for study and preservation. It contains no copyrighted game assets: no ROM,
no graphics, audio, or text extracted from the cartridge — only original code
and documentation. To build or run it you must provide your own legally
obtained dump of the original game. If you redistribute builds, do not
include the ROM.

The repository itself carries no license yet; reach out if you intend to reuse
the code.
