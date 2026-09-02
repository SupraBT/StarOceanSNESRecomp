# Star Ocean (Japan) — SNES Native Recompilation

Native recompilation port of **Star Ocean (Japan)** for SNES, built with
[snesrecomp](https://github.com/mstan/snesrecomp). The S-DD1/SPC boot path
restores the original developer's runtime behavior needed to get past the
black screen.

**Status:** Boots, intro, menus, cinematics, maps, combat — playable without crashes.

## Prerequisites

- **Authentic Star Ocean (Japan) ROM** — unmodified, not translated or patched.
  - SHA-1: `A616EE3466256482BC0ADC11F1FDA7C30E66EF8D`
  - Put it at the repo root as `Star Ocean (Japan).sfc`
- **CMake** ≥ 3.20
- **SDL2** (or SDL3 with `-DSNESRECOMP_SDL_BACKEND=SDL3`)
- **MSVC 2022** (Windows) or **clang/gcc** (macOS/Linux)
- **Rust toolchain** (only if regenerating AOT output)

## Quick Build

### Windows (PowerShell)

```powershell
git clone --recurse-submodules https://github.com/SupraBT/StarOceanSNESRecomp.git
cd StarOceanSNESRecomp

# Place your authentic ROM here:
# cp "E:\path\to\Star Ocean (Japan).sfc" .

.\build.ps1
```

### macOS / Linux

```bash
git clone --recurse-submodules https://github.com/SupraBT/StarOceanSNESRecomp.git
cd StarOceanSNESRecomp

# Place your authentic ROM here:
# cp /path/to/"Star Ocean (Japan).sfc" .

sh build.sh
```

The output binary is `build/Release/StarOcean.exe` (Windows) or `build/StarOcean` (Linux/macOS).

## Regenerating AOT Output

The `generated/` directory is gitignored because it is derived from copyrighted
ROM data. If you need to regenerate it (e.g. after updating config/):

```powershell
.\tools\regenerate_aot.ps1 -RomPath ".\Star Ocean (Japan).sfc"
```

This builds the Rust native analyzer and runs the v2 emit pipeline. Requires
the Rust toolchain (`rustup`).

## Project Structure

```
├── CMakeLists.txt          # Build system
├── config/                 # Bank configs + function declarations
│   ├── bank00.cfg
│   ├── bankC0.cfg … bankC9.cfg
│   └── funcs.h
├── src/                    # Game-specific runtime
│   ├── main.c
│   ├── so_rtl.c            # Star Ocean RTL hooks
│   ├── so_cpu_infra.c      # CPU infrastructure
│   ├── so_spc_player.c     # SPC audio player
│   └── state_file.c        # Save/load state support
├── tools/
│   └── regenerate_aot.ps1  # Headless AOT regeneration
└── snesrecomp/             # snesrecomp framework (submodule)
```

## How It Works

snesrecomp statically recompiles SNES 65816 code into native C at build time.
The `config/` directory declares function boundaries and indirect-dispatch
tables. The recompiler emits C source into `generated/`, which the build
compiles alongside the SNES hardware model (PPU, APU, DMA, S-DD1) provided
by the snesrecomp runner.

Sensitive boot/interrupt boundaries (SPC700 IPL handshake, NMI waits) remain
in the interpreter (LLE) to avoid hangs. Everything else is promoted to AOT
native code for performance.

## License

See `snesrecomp/LICENSE` for the snesrecomp framework license.
Star Ocean is © SQUARE (now Square Enix). You must supply your own ROM.
