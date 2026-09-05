# StarOceanRecompRAID — build reproducible

Repo publicado del proyecto Star Ocean (Japan) recompilado. El framework
completo (runner + toolchain v2) vive en el submódulo `snesrecomp/` (fork
`SupraBT/snesrecomp`). No hay copias vendorizadas separadas.

## Estructura

```
CMakeLists.txt          build del exe (opcion SNESRECOMP_CLEAN_BUILD para exe limpio)
config/                 perfiles AOT (bank*.cfg) + funcs.h  -> entrada del generador
src/                    codigo host del juego (main, so_rtl, spc player, state_file...)
snesrecomp/             SUBMODULO: framework completo (runner + toolchain v2 + recompiler-rs)
                        @ SupraBT/snesrecomp (commit con SPCFF/CCFF/PUMPFF + gating clean-build)
generated/              SALIDA del generador (NO se commitea; se regenera con tools/regenerate_aot.ps1 + ROM)
docs/                   notas de submódulo y de esta build
```

## Prerrequisitos

- Windows + Visual Studio 2022 (MSVC) + CMake.
- Python 3 y Rust/cargo (solo para regenerar `generated/`; el analizador nativo
  `snesrecomp/recompiler-rs` se compila con cargo).
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
      -DSDL3_DIR="<ruta-local>\SDL3-3.2.4\cmake"
cmake --build build-raid --config Release
```

Estado validado (2026-09-03):

- Runner `snesrecomp` @ `3cfd609` — SPCFF/CCFF/PUMPFF + D9FF: la caminata
  completa (f1→23700) es **byte-exacta** vs LLE puro (0 frames difieren,
  master final 8593935250) y elimina los parones de la aldea (f10770:
  193→~61ms) y la zona de cofres.
- Exe limpio de referencia (`SNESRECOMP_CLEAN_BUILD=ON`, SDL3): md5
  `b205015e52fd9b186decd56ee60df571` (2.Beta local).

## ⚠️ Reproducibilidad de `generated/` (verificado 2026-09-03)

El exe validado b205015e se construyó con el `generated/` local (snapshot del
2026-09-02 16:33, bancos 00/C0/C1/C3). **Regenerar hoy desde `config/` +
`snesrecomp/` NO reproduce ese snapshot**:

- el emitter actual (tool v2, con cambios de codegen/decoder posteriores al
  snapshot) añade guards LLE (`interp_bridge_lle_master_deadline_reached`,
  `WatchdogCheck`, etc.) a los bancos emitidos, y
- `config/bankC2.cfg` + `config/bankC9.cfg` (perfiles experimentales: blit de
  menú / seeds estáticos sin validar byte-exacto) activan 2 bancos AOT
  (bankc2/bankc9) ausentes del snapshot validado.

A/B real (exe dev regenerado vs línea base validada `afull.log`, replay de la
caminata f1→23700): **21628/23700 frames difieren desde f1033; delta final
−369.682 masters (~0.004 %)** → el estado regenerado NO es byte-exacto.

**Acción pendiente antes de afirmar reproducibilidad desde clon limpio:**
revalidar el estado regenerado (A/B byte-exacto vs LLE) o restaurar el
estado pre-deriva del tool/config que produjo el snapshot validado. El
exe 2.Beta (b205015e) sigue siendo el artefacto validado de referencia.
