# StarOceanRecompRAID — build reproducible

Repo publicado del proyecto Star Ocean (Japan) recompilado. Layout tipo
`forkStarOcean` + toolchain v2 vendorizado (este proyecto usa el runner como
submodulo y el recompilador como carpeta propia, no dentro del submodulo).

## Estructura

```
CMakeLists.txt          build del exe (opcion SNESRECOMP_CLEAN_BUILD para exe limpio)
config/                 perfiles AOT (bank*.cfg) + funcs.h  -> entrada del generador
src/                    codigo host del juego (main, so_rtl, spc player, state_file...)
snesrecomp/             SUBMODULO: runner del framework @ SupraBT/snesrecomp (commit con SPCFF/CCFF/PUMPFF + gating clean-build)
snesrecomp-tool/        toolchain v2 vendorizado (v2_emit.py + recompiler + analizador nativo recompiler-rs)
generated/              SALIDA del generador (NO se commitea; se regenera con tools/regenerate_aot.ps1 + ROM)
docs/                   notas de submódulo y de esta build
```

## Prerrequisitos

- Windows + Visual Studio 2022 (MSVC) + CMake.
- Python 3 y Rust/cargo (solo para regenerar `generated/`; el analizador nativo
  `snesrecomp-tool/recompiler-rs` se compila con cargo).
- ROM original Star Ocean (Japan) — sha1 `A616EE3466256482BC0ADC11F1FDA7C30E66EF8D`
  (no se commitea; el exe la necesita en runtime via `rom.cfg`).
- SDL3 dev (en este repo de trabajo: `deps/SDL3-3.2.4`; pasar `-DSDL3_DIR=...`).

## Regenerar AOT (solo si no existe `generated/` o cambiaste `config/`)

```powershell
git submodule update --init --recursive
.\tools\regenerate_aot.ps1 -RomPath ".\Star Ocean (Japan).sfc" -InPlace
```

## Compilar el exe limpio (2.Beta-equivalente)

```powershell
cmake -S . -B build-raid -G "Visual Studio 17 2022" `
      -DSNESRECOMP_CLEAN_BUILD=ON -DSNESRECOMP_SDL_BACKEND=SDL3 `
      -DSDL3_DIR="F:\...\deps\SDL3-3.2.4\cmake"
cmake --build build-raid --config Release
```

Estado validado (2026-09-03):

- Runner `snesrecomp` @ `3cfd609` — SPCFF/CCFF/PUMPFF + D9FF: la caminata
  completa (f1→23700) es **byte-exacta** vs LLE puro (0 frames difieren,
  master final 8593935250) y elimina los parones de la aldea (f10770:
  193→~61ms) y la zona de cofres.
- Exe limpio de referencia (`SNESRECOMP_CLEAN_BUILD=ON`, SDL3): md5
  `b205015e52fd9b186decd56ee60df571` (2.Beta local).
- `generated/` es derivado del ROM: el árbol publicado (config + tool) puede
  regenerarlo; tras regenerar, validar con A/B byte-exacto (ver
  `Datos Importantes de Consulta.md`).
