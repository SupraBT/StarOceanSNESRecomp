# Star Ocean Recomp — AI Handoff Document (LEER PRIMERO / READ FIRST)

> **Para cualquier IA que continúe este proyecto:** lee este documento COMPLETO antes de
> tocar código. Es el registro vivo del estado actual, los bugs abiertos y — lo más
> importante — las **invariantes que NO se deben romper** (una IA arreglando una cosa no
> debe romper lo que otra ya arregló). Cuando hagas un cambio relevante, actualiza la
> sección correspondiente y añade una fila al Changelog (abajo).
>
> *This is the living handoff document. Read order: HANDOFF.md → docs/ARCHITECTURE.md
> (ROM layout & engine) → docs/ENCYCLOPEDIA.md (tooling, BSV converter) →
> docs/PERF_REPORT.md (performance, partly stale — see §5).*

**Última actualización:** 2026-08-30 · **Builds:** `1.Release/` = versión ESTABLE (NO tocar; exe 449024B md5 `3f026ac1`, generated minimal 57 AOT). `2.Beta/` = versión de pruebas (exe md5 `81a1ef66`, C3 + 4 FF + intro paso-48 + guard VFF campo `$C2:0B82/0B87` + MC_LOG + POLL-GATE del intérprete, bit-exacto — ver §4.11, § PASO 1b, § POLL-GATE). Los exe tienen rutas hardcoded a `build/Release` y `build-beta/Release` respectivamente (rom.cfg).

---

## 1. Estado del proyecto de un vistazo

| Área | Estado |
|---|---|
| Recompilación AOT | ~98-99% cobertura; 587+ funciones AOT en `config/bankC*.cfg`, código en `generated/` |
| Juego | Arranca, intro, menús, cinemáticas, mapas, combate — **jugar sin crash** |
| **⚠️ Regeneración del `generated/`** | **PELIGRO**: regenerar en bloque con `v2_emit.py` produce AOT que se CUELGA en boot (handshake IPL SPC700 `$C0850C` esperando `$BBAA` en `$2140`, y waits de NMI `$00:F6DD-F6FE` como AOT sin deadline). El `generated/` actual = minimal (57 AOT, 5 archivos: bank00/bankc0/bankc1/dispatch/stubs) que SÍ funciona. Backup en `build-cosim/backup_gen_minimal/`. Ver §4.4. |
| **Cosimulación Track-B (bsnes)** | ✅ Funciona — `so_cosim` + `drive_bsnesplus` (bsnes-plus accuracy via libsnes) + `cosim_trackb.py`. Valida el boot del minimal: **frame 0 diverge de bsnes en solo 1 byte de WRAM** (`$1F5`), VRAM/CGRAM/S-DD1 idénticos. Ver §4.4. **Diagnosticó el fondo negro del puente (§4.1)**: CGRAM byte-idéntico a bsnes tras el fix MMC S-DD1. |
| **Bug 1: fondo negro del puente** | **ABIERTO** — causa raíz localizada (buffer de paleta WRAM $7E:D873 se borra y no se recarga). Ver §4.1 |
| **Bug 2: música** | **ABIERTO** — no suena en menú/intro (a veces se arregla tras loadstate). Ver §4.2 |
| **Bug 3: 60 FPS estables** | **PARCIALMENTE RESUELTO (2.Beta)** — fast-forward del spin de vblank: título a 82 FPS. Quedan zonas de transición S-DD1/lógica a 9-41 FPS. Ver §4.3 |
| Savestate/loadstate | Funciona (F9/F10 + TCP) — formato L3SN + chunk CpuSnapshot. Ver §6 |
| Paquete standalone | `StarOceanRecomp-win-1.0/` (exe + DLLs + config) |

## 2. Layout del repositorio

```
StarOceanTest2/
├── build/                    # Build MSVC (Visual Studio 18 2026), Release
│   └── Release/StarOcean.exe # Ejecutable (cwd del juego = build/Release/)
├── generated/                # Código AOT generado (bank00_v2.c, bankc0_v2.c, ...)
├── config/bankC*.cfg         # Tablas AOT (función por banco) — CURADAS A MANO + tier2
├── snesrecomp/runner/src/    # Núcleo del runner (C):
│   ├── snes/ppu.c            # Renderer PPU (new) + CGRAM ($2121/$2122) — ver §7
│   ├── snes/ppu_legacy.c     # Renderer legacy (comparación/diagnóstico)
│   ├── snes/dma.c            # Motor DMA (log DMA_CGRAM gated por env)
│   ├── snes/sdd1.c           # S-DD1: LRU cache + dual-worker threads
│   ├── snes/interp816.c      # Intérprete 65816 (LLE)
│   ├── snes/interp_bridge.c  # Puente AOT<->LLE (resume PC, abandonos)
│   ├── snes/snes.c           # Bus, WRAM ($2180), saveload
│   ├── cpu_state.c/.h        # cpu_write8/16 — log SNESRECOMP_WRITE_WATCH aquí
│   ├── debug_server.c        # TCP 13308 — comandos de diagnóstico/control
│   ├── common_rtl.c/.h       # RtlSaveLoad, APU lock, IndirWriteByte/Word
│   └── common_cpu_infra.c    # g_last_recomp_func, abandonos LLE
├── snesrecomp-tool/          # Herramienta recompiladora (generador AOT, cfg_loader...)
├── cosim/                    # Scripts Python de diagnóstico/cosimulación (ver §8)
├── src/                      # so_rtl.c etc. (código recompilado/rtl del juego)
├── docs/                     # ARCHITECTURE.md, ENCYCLOPEDIA.md, PERF_REPORT.md, HANDOFF.md
└── build-cosim/              # Artefactos de diagnóstico (logs, .st, .bmp, grabaciones)
```

## 3. Build y ejecución

```bash
# Configurar (una vez): MSVC + SDL3
cd build && cmake .. -G "Visual Studio 18 2026" -A x64 -DSNESRECOMP_ENABLE_TRACE=ON -DSDL3_DIR=E:/SDL3

# Compilar
cd build && cmake --build . --config Release

# Ejecutar (el juego escribe archivos relativos a build/Release/)
cd build/Release && ./StarOcean.exe
```

- **TRACE=ON** (depuración): habilita rings de cpu_trace, interp_cap, etc. **Ralentiza el juego**.
- **TRACE=OFF**: Release final listo para jugar / empaquetar.
- El debug server escucha en **TCP 127.0.0.1:13308** (`cosim/semantic_cosim.py:35`).

## 4. Bugs abiertos — DIAGNÓSTICO ACTUAL

### 4.1 Fondo negro del puente (cinemática) — CAUSA RAÍZ DEFINITIVA + FIX (2026-08-27)

**Escena:** primer puente de mando (normal, azul, "HIRO YUKI"), justo después del
subtítulo con el número 346. En la grabación `build-cosim/grabacion_inputs.txt`:
Up en frame 2803 → transición; frame 3187 = puente asentado.

**✅ RESUELTO en 2.Beta y 1.Release (fix MMC S-DD1 en `snesrecomp/runner/src/snes/cart.c`).**
Confirmado visualmente por el usuario (2026-08-27): el puente, la casa y TODOS los
fondos de la zona jugable se ven correctamente, con música sonando. Aplicado a
1.Release (exe nuevo md5 `3f026ac1`, recompilado desde build-release2 con SOLO el
fix de cart.c — los logs de diagnóstico de dma.c/sdd1.c fueron revertidos antes).
Backups: `build-cosim/StarOcean_1Release_OLD_20260827_1213.exe` (el exe release
anterior, md5 `4b27b861`) y `build-cosim/StarOcean_beta_OLD_before_mmc_fix.exe`
(el 2.Beta previo).

**Causa raíz (aplicada con Track-B vs bsnes-plus accuracy):**
- La paleta del puente se carga por DMA desde ROM **`FD:5419` (banco S-DD1, adr < 0x8000)**
  directamente a CGRAM (f=2963: `[DMA_CH0] mode=0 bAdr=$22 src=FD:5419 size=$00E0`).
- La VRAM/WRAM staging son **100% idénticas** a bsnes. Lo que divergía era el CGRAM:
  runner 106 colores vs bsnes 207 → paleta a medias → fondo negro.
- El S-DD1 NO descomprime ese DMA (r4800/r4801 = 0 en ese momento, igual en bsnes —
  el juego arma la sesión solo para los DMAs de VRAM, luego limpia `$4800=$00`).
- **El bug:** en bsnes, `SDD1::read()` SIEMPRE enruta las lecturas de bancos $C0-$FF
  por el MMC (páginas r4804-r4807): `cartrom.read(mmc[(addr>>20)&3] + (addr&0xFFFFF))`.
  El runner caía a `cart_readLorom` → mapeo LoROM equivocado. Para `FD:5419`:
  - MMC:  `0x3D5419` (correcto — el CGRAM de bsnes coincide 188/224 bytes con esto)
  - LoROM: `0x1ED419` (lo que leía el runner — solo 8/224 coinciden)
- Para `adr >= 0x8000` el MMC con páginas por defecto (0,1,2,3) da el MISMO offset que
  LoROM — por eso los tiles se veían bien y solo la paleta (adr < 0x8000) fallaba.

**Fix (1 línea en `cart.c`):** para `CART_SDD1`, las lecturas con `bank >= 0xc0` pasan
por `sdd1_mmc_read()` (páginas $4804-$4807) en vez de `cart_readLorom()`, igual que
bsnes. Cubre CPU-reads y DMA-reads (el DMA va por `snes_read` → `cart_read`).

**Verificación exhaustiva (cosim):**
- CGRAM del puente asentado A@3141 vs B@3164: **512/512 bytes idénticos** (antes 106 vs
  207 colores). A@3150 vs B@3173: 512/512. Colores 117 = 117, rango 0x1-0x7f.
- Boot intacto: frames 0-59 WRAM+CGRAM **0 diffs** vs el build anterior.
- Frame renderizado del puente (so_cosim + `--final-frame-dump`): **93% de píxeles no
  negros** en todas las regiones (antes: negro).
- 2.Beta real: ventana con título + FPS 32, SDL audio wasapi init OK, primer callback
  recibido, frames avanzando por el camino correcto, sin cuelgue.

**⚠️ Hipótesis anterior descartada:** la teoría de "WRAM $D873 borrada por un bucle LLE"
(abajo) NO se cumple — la cosimulación mostró `$D873`/`$D900` (staging real) 100%
idénticos entre runner y bsnes. El mecanismo real era el MMC del S-DD1.

**Historial de la hipótesis descartada (referencia):**
- **Lo descartado (verificado):** registros PPU idénticos entre puentes (mode=1, BG1,
  tilemap 0x7800, ventanas 0xfd). Tiles/mapa en VRAM correctos. El fix del modelo CGRAM
  (ver §7) es correcto pero no era la causa.
- **Mecanismo (traza antigua de `SNESRECOMP_WRITE_WATCH=0xD873`):** un bucle LLE borraba
  `$7E:D873` con ceros en 2111-2112 y el DMA copiaba ceros. **DESCARTADO** por Track-B:
  WRAM $D873/D900 idéntica entre A y B.
- **Otra pista falsa:** `$210B/$210C` (base de tiledata) parecía "la mitad" (A=0410 vs
  B=0820) — era un **bug de exportación de bsnes-plus** (`mmio_w210b` usa `<< 13`/`<< 9`
  en vez de `<< 12`/`<< 8`); el valor crudo del registro es el mismo en ambos lados.

**Instrumentación usada:** `SNESRECOMP_WRITE_WATCH`, `SNESRECOMP_DMA_DEBUG`, `SNESRECOMP_SDD1_DEBUG`
(logs `[SDD1_WRITE]`, `[DMA_CH0]`, `[DMA_CGRAM]`, `[SDD1_DMA]` con frame), analizadores
`cosim/analyze_bridge_*.py`, y la comparación CGRAM vs ROM cruda (MMC vs LoROM).

### 4.2 Música no suena en menú/intro — RESUELTO (2026-08-27)

- **CERRADO por confirmación del usuario:** la música suena correctamente en el menú y
  durante el juego en el 1.Release actualizado (con el fix MMC de §4.1).
- Nota histórica: el síntoma antiguo (audio desincronizado a 50-60 FPS, "se arreglaba"
  tras un loadstate) no se reproduce en el build actual. Se atribuye a la combinación
  del generated minimal + el pacing APU existente; ya no es un bug abierto.

### 4.4 Cosimulación y el cuelgue del boot (2026-08-27)

**Contexto:** la sesión intentó regenerar `generated/` desde journals tier2 para más AOT
(49 FPS vs 31). Todo generated regenerado (151-452 AOT) se colgaba en boot:
- Waits de NMI `$00:F6DD-F6FE` emitidos como AOT sin `s_lle_master_deadline` (nadie llama
  `interp_bridge_set_master_deadline`) → spin infinito. Fix aplicado y VÁLIDO: `force_lle`
  en `config/bank00.cfg` para la región F6DD-F6FE (el minimal nunca los emitía AOT).
- Handshake IPL SPC700 `$C0850C` (`CMP $2140 / BNE` esperando `$BBAA`): el boot llegaba ahí
  sin haber escrito nunca a `$2140` (`apu_runToGuestCycle` no avanza si `portTimeValid=false`,
  que solo se activa con un write CPU a $2140). Se forzó `force_lle` de la zona C0:8xxx en
  `config/bankC0.cfg` (VÁLIDO) pero el cuelgue persistió con generated regenerados.
- **RESOLUCIÓN PRÁCTICA:** restaurar el generated minimal (57 AOT) de `<alt-worktree>`
  (también en `build-cosim/backup_gen_minimal/`). Con él, 2.Beta arranca y corre (34 FPS,
  imagen, audio init OK). **1.Release nunca se tocó.**

**Cosimulación (infra reconstruida en F:, todo en `build-cosim/`):**
- `build_cosim.bat` reconfigurado limpio apuntando a F: (`build-cosim-reconf.bat`).
  El CMakeCache anterior apuntaba a E: y fallaba con "manifest dirty" (timestamps).
- Track-B: `drive_bsnesplus.exe <rom> --frames N --state-out <bin>` (necesita `snes.dll`
  junto al exe) + `so_cosim.exe <rom> --frames N --state-out <bin>`
  (con `SNES_COSIM_OFF=1 SNES_COSIM_AUDIO=1`) + `python tools/cosim_trackb.py --a ... --b ...`.
  Resultado: el boot del minimal es casi byte-idéntico a bsnes (frame 0: 1 byte WRAM `$1F5`;
  diverge masivamente en frame 10+ por el modelo de frame driver — yield-en-quiescencia vs
  driver H/V exacto, ~100x menos mcyc/frame; documentado en ENCICLOPEDIA §12).
- Track-A (so_cosim vs so_cosim_ref, hashes por subsistema incl. apu/dsp/spc): la 1ª
  divergencia en cp2 es el MISMO modelo de frame driver (A: 6.222 mcyc vs B: 714.680 mcyc,
  S=01F4/P=27 vs S=01F4/P=26), NO un bug de código CPU. El APU/SPC700 NO está en el record
  Track-B — Track-A sí lo compara (COSIM_SUB_APU/SPC/DSP).
- Savestate de bsnes real: `build-cosim/intro_101648_state.bst` (formato BSTC, NO compatible
  con L3SN — sería necesario un conversor para usarlo como bootstrap post-boot).
- Backups: `so_cosim_OLD_aug25.exe`, `so_cosim_ref_OLD_aug24.exe`.

### 4.3 60 FPS estables (oscila 50-60)

**ACTUALIZADO (2026-08-27): fast-forward del spin de vblank implementado en 2.Beta.**

- **Causa raíz del FPS bajo (medida real, no estimada):** el bucle principal de Star Ocean
  (`$C8:F425` `LDA $4212 / BMI` = espera de fin de vblank, y `$C8:F42A` `LDA $4212 / BPL`
  = espera de inicio de vblank) es un **spin puro de beam** que cubre ~todo el frame:
  ~8.500 iteraciones/frame (17.000 opcodes interpretados, 42 master/iteración: LDA $4212
  = 24 master + branch tomado = 18). El intérprete gastaba 20-28ms/frame en él.
- **Fix en `snesrecomp/runner/src/snes/interp_bridge.c`** (bloque `vblank-spin
  fast-forward`, activo por defecto, desactivable con `SNESRECOMP_NO_VBLANK_FF=1`):
  - Fase F42A (display activo, vPos 1..224): salta el beam al primer read >= (225,0);
    el LDA lee bit7=1 y cae a la lógica del frame. Salto ~305.300 master.
  - Fase F425 (vblank, vPos 225..261): salta al inicio de la iteración que cruza el
    wrap; el IRQ (vTimer=0) corta y hace yield en el punto exacto. Salto ~45.700 master.
  - Avance del beam path-independent (una sola `snes_sync_master_clock` == suma de las
    per-opcode) + SPC alimentado en chunks bajo el cap de `snes_catchupApu` (10k ciclos
    SPC/llamada — un flush único de 305k master se truncaba y el SPC quedaba 14.546
    ciclos detrás, rompiendo los handshakes de puertos APU en la lógica del frame).
  - Guards: ventana de boot (frames > 10), h-IRQ, línea v-IRQ dentro del rango saltado,
    deadline armado, y verificación del opcode real (0xAD 0x12 0x42 vía MMC).
- **Validación cosim A/B (mismo binario, FF on vs off):** 600/600 frames byte-idénticos
  (CPU regs, beam hPos/vPos, flags, timers, WRAM 128KB, VRAM 64KB, CGRAM).
- **BUG DE DOBLE CONTEO APU (2026-08-27, corregido):** el FF saltaba el master clock
  ANTES de flushear el SPC; `bridge_apu_flush` termina con `rtl_sync_apu_to_cpu_locked`
  que re-ancla al guest cycle del master YA saltado → el primer chunk tira el SPC al
  full-skip y el segundo chunk avanza OTRA VEZ (overshoot medido = 5.598 ciclos SPC =
  117.074 master = el segundo chunk de 305.298). El déficit se creaba en frame 325
  (título→intro) y rompía handshakes APU en frame 688 (zona batalla). **Fix: flushear
  el SPC en chunks ANTES de `cpu->master_cycles = target`** (el re-ancla va al guest
  pre-salto → no-op; el catchup suma exactamente skip*kInterpApuPerMaster).
- **Validación A/B con portClock (la que faltaba):** el state record de `so_cosim` NO
  incluye el portClock del SPC (por eso la validación de 600 frames lo pasó). Con
  `SNESRECOMP_YIELD_LOG=1` (apu= por frame): **850/850 states + 847/847 portClock
  idénticos** (frame 325: ON=6757587 == OFF=6757587).
- **Medición real en 2.Beta (SNESRECOMP_PHASE_MS=1):** título emu=2.65ms -> **82.6 FPS**
  (antes 20-28ms / 43-51 FPS); zona batalla 9 -> **31.6 FPS**. El spin ya no es el cuello
  de botella.
- **Mapa COMPLETO de spins $4212 del recorrido (hotlog 2026-08-27, ver §10):** hay
  MÁS copias de la misma rutina de espera SIN cubrir: título ($CA:6D13/6D18), intro
  ($C2:0B51/0B57 — **variante LDA long 0xAF**, branch en pc+4), texto ($C2:DB39/DB3E),
  zona texto ($C6:18D1/18D6). Pantallas de texto miden **8.5 FPS con $C2:DBxx al 68%**
  (spin puro de beam, ver §10.1).
- `docs/PERF_REPORT.md` sigue PARCIALMENTE DESACTUALIZADO (no refleja el fast-forward).

## 5. Invariantes críticas — "NO ROMPER"

> Cada una de estas líneas es el resultado de un bug que otra sesión ya pagó. **Si tu
> cambio toca una de estas zonas, léela dos veces.**

1. **Modelo CGRAM ($2121/$2122/$213B)**: usar el modelo hardware byte-direccionado
   (`cgramByteAddr`, paridad en bit 0, máscara 0x7f, incremento por byte). **No revertir**
   al modelo de flag `cgramSecondWrite` (ver §7). Un intento previo de "bloquear ceros"
   causó bucle infinito y está comentado.
2. **Savestate L3SN**: el chunk `CpuSnapshot` (g_cpu, resume PC del bridge, frame counter)
   es OBLIGATORIO — el blob `snes_saveload` no guarda el CpuState del recompilador. Sin él,
   F9/F10 y `save_state`/`load_state` cargan registros viejos. `cgramByteAddr` NO se
   serializa (derivado en load: `cgramPointer << 1`).
3. **S-DD1**: cache LRU + dual-worker threads con mutex. **El fallback síncrono NO se puede
   eliminar** (rompe la integridad del DMA a VRAM). El worker solo ayuda si termina antes
   de la primera petición del DMA.
4. **Debug server**: las copias WRAM/VRAM del ring solo cuando hay cliente TCP conectado
   (gating) — sin esto el FPS cae por las copias de 196KB/frame.
5. **PPU**: el renderer activo es `ppu.c` (new). `ppu_legacy.c` sirve para comparar.
   Si tocas el compositor, compara ambos antes de commitear.
6. **AOT / bank cfgs**: `config/bankC*.cfg` son CURADOS (manual + tier2). **No regenerarlos
   en bloque**: un cambio de dispatch table ya regresó el rendimiento y se revirtió.
7. **Windows / procesos**: el juego NO se cierra solo. Todo script de prueba debe hacer
   `taskkill //F //IM StarOcean.exe` (PowerShell: `Stop-Process`) en un bloque `finally`.
   El usuario se queja si quedan ventanas abiertas.
8. **Instrumentación**: el log `SNESRECOMP_WRITE_WATCH` vive en `cpu_write8/16`
   (cpu_state.c) + camino DMA (`snes.c` case 0x80). El bloque `#ifdef SNES_COSIM` NO está
   compilado en la build normal — no confiar en él. El ring de cpu_trace puede estar vacío
   en Release aunque la ring esté asignada.
9. **Escenas**: el puente de alarma ≠ puente normal (paletas distintas). Nunca comparar
   paletas entre escenas distintas para validar un fix.
10. **Rutas relativas**: el juego corre con cwd=`build/Release/` — los logs con ruta
    relativa se escriben ahí, no en la raíz del proyecto. Usar rutas absolutas en scripts.

## 6. Savestate / loadstate

- **F9** guarda en `saves/snapshot.st` (crea el dir si falta — verificado), **F10** carga.
- **TCP**: `save_state <path>` / `load_state <path>` (deferidos al frame boundary vía
  `dbgs_set_pending_file`, consumidos por `debug_server_flush_pending_file` en el main loop).
- **Formato**: magic `L3SN` + version + blob `snes_saveload` (incl. PPU v2 con cgramPointer)
  + chunk `CpuSnapshot`. Tras load: `sync_g_cpu_to_snes_cpu()`.
- Los `.bst` de bsnes-plus/otros emuladores **NO son compatibles** (magic BSTC, específicos
  del motor) — solo referencia.
- Estados reproducibles usados en diagnóstico: `bridge-2600.st` / `bridge-4900.st`
  (generados con `make_bridge_state.py`; pueden regenerarse si se borran).

## 7. Cambios recientes importantes (resumen)

| Fecha | Zona | Cambio | Estado |
|---|---|---|---|
| 2026-08-26 | `ppu.c` $2121/$2122/$213B | Modelo CGRAM hardware byte-direccionado (`cgramByteAddr` uint16 0-511, paridad bit 0, `& 0x7f`); migración en `ppu_saveload`; eliminado TEMP DIAG | **VÁLIDO** (no rompe nada; no resolvió el fondo negro) |
| 2026-08-26 | `cpu_state.c`, `snes.c` | Log `SNESRECOMP_WRITE_WATCH` siempre compilado (env-gated) para [ADDR, ADDR+0x40) en cpu_write8/16 y DMA→WRAM | VÁLIDO (diagnóstico) |
| 2026-08-26 | `dma.c` | Trace `[DMA_CGRAM]` frame-filtrado (`SNESRECOMP_DMA_FRAME_FROM`), cap 400 | VÁLIDO (diagnóstico) |
| previo | `sdd1.c/.h` | LRU cache + dual-worker SDL3 + pre-fetch lookahead | VÁLIDO (perf) |
| previo | `debug_server.c` | Gating de copias WRAM/VRAM cuando no hay cliente TCP | VÁLIDO (perf) |
| previo | interp_bridge fast-path | Fast-path de 10 opcodes → **REVERTIDO** (pantalla negra) | REVERTIDO |
| previo | MMC mapping fix | 587 variantes AOT (offset ROM corregido para la ROM de 8MB mirrored) | VÁLIDO |
| 2026-08-28 | `interp_bridge.c` | Intro FF `$C2:0B51/57` paso 48 (LDA-long 0xAF), §4.9; validado A/B 3050 frames §4.11 | **VÁLIDO** (en 2.Beta) |
| 2026-08-28 | docs | §4.11 (validación final 2.Beta) + §12 (grabación nueva + plan) | VÁLIDO (doc) |

## 8. Herramientas de diagnóstico (cosim/)

- **DebugClient** (`cosim/semantic_cosim.py`): `frame()`, `controller(mask)`, `cmd(...)`,
  `cgram()`, `vram()`, `wram()`, `screenshot(path)`, `ppu()`. Puerto 13308.
- **Grabación de inputs** (vía fiable/verificada): reproducir en el recomp con
  `SNESRECOMP_INPUT_LOG=<path>` → `live_inputs.log` (formato `frame hexmask`),
  que es como se obtuvo `build-cosim/grabacion_inputs.txt`. NO existe un parser
  `.bsv → hexmask` validado (ver NOTA al final de §12.2). `grabacion_inputs.txt`
  es formato `frame mask_hex` (bits: 0x100=A, 0x010=Up...). Marcadores Up:
  2803 (puente malo), 3187, 4313 (planeta), 5108 (puente alarma).
- **Scripts clave**:
  - `make_bridge_state.py <frame>` — replay → savestate reproducible.
  - `from_state_capture.py <frame>` — load state → captura PPU/CGRAM/VRAM.
  - `validate_cgram_fix.py` — conteo de paleta BG1 en frames 2650/3187/5108 (regresión).
  - `trace_dma_cgram.py <target> <log> [frame_from]` — trace DMA→CGRAM (necesita
    `SNESRECOMP_DMA_DEBUG=1`).
  - `watch_wram_d873.py` — watch de WRAM D873 (depende de la ring de cpu_trace; si la ring
    está vacía, usar `SNESRECOMP_WRITE_WATCH` en su lugar).
  - `bsv_profiler_v2.py` — profiling con replay del .bsv real de la partida del usuario
    (llegó a 46.559 frames ≈ 13 min a ~323 fps de emulación).
  - `diag_bg1.py`, `diag_cgram.py`, `dump_wram_at.py`, `timeline_cgram.py`, `live_capture.py`.
  - `build-cosim/grabar_hasta_casa_dialogos.bat` (2026-08-30) — graba input-log NATIVO
    en el recomp (2.Beta, exe 47a44e7a) desde cold-boot hasta donde se juegue; destino
    `2.Beta/replay_casa_dialogos.txt`. Es la via determinista para medir el campo
    (el replay de bsnes desincroniza). No usa savestate (evita el bug de musica).
  - `cosim/harness_so.c` — tope de eventos `--input` subido 64→256 (2026-08-30).

**Env vars útiles**: `SNESRECOMP_DMA_DEBUG`, `SNESRECOMP_DMA_FRAME_FROM`,
`SNESRECOMP_WRITE_WATCH` (+ `_LOG`), `SNESRECOMP_FPS`, `SNESRECOMP_LAYER_MASK`,
`SNESRECOMP_ENABLE_TRACE` (CMake).

## 9. Protocolo de actualización de este documento

**Regla para cualquier IA que trabaje aquí:**

1. Antes de tocar código en una zona de las §5/§7, relee esas secciones.
2. Tras un cambio que afecte a: bugs abiertos (§4), invariantes (§5), savestate (§6),
   formato/renderer/audio/perf, o que añada una herramienta → **actualiza este documento**
   (estado del bug, fila en el Changelog §7, o entrada en §8).
3. Si `ARCHITECTURE.md` / `PERF_REPORT.md` quedan desactualizados por tu cambio,
   corrígelos o añade una nota de "stale" en lugar de dejar datos falsos.
4. Commits: mensaje con prefijo de tipo (`diag:`, `perf:`, `fix:`) — ver `git log`.
5. **Cierra el juego al terminar tus pruebas** (invariante §5.7).

## 10. PLAN PRÓXIMA SESIÓN: 60 FPS estables SIN romper el audio (2026-08-27)

> Objetivo: cerrar el §4.3 (60 FPS estables) con la metodología que ya funciona:
> **datos primero (hotlog/sampler/phase), A/B cosim con portClock, solo después tocar
> 2.Beta. 1.Release NO SE TOCA.** El usuario valida la música por oído en cada fase.

### 10.0 Estado actual (medido en el recorrido completo: boot→título→intro→texto, con
la grabación `build-cosim/grabacion_inputs.txt` reproducida en 2.Beta vía
`SNESRECOMP_REPLAY_FILE`):

| Frames (ventana de 120) | FPS | PC dominante | Qué es |
|---|---|---|---|
| 1-480 | 11-15 | $C0:8597/84AA, $C0:8871/86F5/89FB | Boot + título (S-DD1 real + spins sin cubrir) |
| 241-360 | 10.8 | $CA:6D99/$C2:0B55 | Título → intro (spins $CA:6D13/18 + $C2:0B51/57) |
| 361-480 | 12.6 | $C2:0B57 99% | **Intro: spin LDA-long sin cubrir** |
| 481-1080 | 62-86 | $C8:F4xx | FF ya cubierto (bien) |
| 1081-2160 | 17-44 | $C0:86F5/89FD, $C3:9xxx | Cinemática (S-DD1 + lógica real) |
| 2161-2760 | 70-132 | $CC:08xx | FF de batalla ya cubierto (bien) |
| 2761-3000 | 15-28 | $C3:9461, $C0:4DF8, $C2:DB2C | Rampa al texto (1ª pulsación Up 2803) |
| 3001-4080 | **8.1-8.7** | **$C2:DB30/DBD8/DBDE 67-73%** | **Texto: spin $C2:DB39/DB3E sin cubrir** |
| 4081+ | 35 | $C2:DBD8 | Fin de escena |

### 10.1 Mapa COMPLETO de spins $4212 (hotlog `SNESRECOMP_HOTLOG=1`, enumerado en el
recorrido hasta frame 3350):

| Par (BMI=fin vblank / BPL=inicio) | Variante | Zona | FF actual | Acción |
|---|---|---|---|---|
| $C8:F40F / $C8:F414 | AD (abs) | main loop entrada larga | ✓ cubierto | — |
| $C8:F425 / $C8:F42A | AD | main loop entrada corta | ✓ cubierto | — |
| $CC:0538 / $CC:053D | AD | batalla variante A | ✓ cubierto | — |
| $CC:054E / $CC:0553 | AD | batalla variante B | ✓ cubierto | — |
| **$CA:6D13 / $CA:6D18** | AD | título | ✗ | **AÑADIR** |
| **$C2:0B51 / $C2:0B57** | **AF (LDA long $004212)** | intro | ✗ | **AÑADIR + soportar 0xAF** |
| **$C2:DB39 / $C2:DB3E** | AD | texto | ✗ | **AÑADIR** |
| **$C6:18D1 / $C6:18D6** | AD | zona texto | ✗ | **AÑADIR** |
| $00:F6E1, $C0:849E, $C0:8060, $CA:6D62 | AD (single poll, boot) | boot/título | ✗ | menor, NO prioridad |

Detalles de la rutina de texto ($C2:DBxx, trace `SNESRECOMP_DBTRACE=1`): la rutina
empieza en $C2:DB20 (JSL $C60886, JSL $C80922, JSL $C2DB33), y el wait es:
`$C2:DB33: LDX #0; STX $2102; $C2:DB39: LDA $4212; BMI -5; $C2:DB3E: LDA $4212;
BPL -5` — spin doble idéntico al main loop. Después apaga la pantalla ($2100=0x80) y
hace el volcado OAM/CGRAM/DMA (trabajo real, una vez por frame).

### 10.2 FASE A — Extender el fast-forward (cambios en `interp_bridge.c`)

1. **Generalizar la detección de la variante LDA-long (0xAF)**: op 0xAD → branch en
   pc+3; op 0xAF (`AF 12 42 00`) → operandos 12 42 en +1/+2, branch en **+4**. La fase
   sigue por el opcode del branch (0x30=BMI fin vblank, 0x10=BPL inicio).
2. **Añadir los 4 pares** a la lista del FF: $CA:6D13/6D18, $C2:0B51/0B57, $C2:DB39/3E,
   $C6:18D1/D6. Mantener los guards existentes (boot >10, hIRQ, vIRQ en rango, deadline,
   verificación de opcode vía MMC).
3. **CRÍTICO — orden del flush APU**: el SPC se alimenta en chunks bajo el cap de 10k
   ANTES de `cpu->master_cycles = target` (lección del §4.3: el re-ancla de
   `rtl_sync_apu_to_cpu_locked` al master ya saltado produce doble conteo).
4. **Validación A/B obligatoria (mismo binario, FF on vs off)**:
   - `SNESRECOMP_YIELD_LOG=1` en ambos → comparar **apu= portClock frame a frame** (el
     state record de `so_cosim` NO lo incluye — es la lección del bug de 5.598 ciclos).
   - `ab_diff.py` sobre los `--state-out` → 0 frames divergentes.
   - Cobertura: 1.200+ frames con la grabación (título 100-330, intro 330-2800,
     texto 2800-4200). Comando A/B: `run_ab8.py` con `--frames 4200` y los `--input`
     de la grabación (ver §8).
5. **Medir en 2.Beta**: `SNESRECOMP_PHASE_MS=1` + `SNESRECOMP_REPLAY_FILE=...` +
   `SNESRECOMP_REPLAY_UP_PAUSE_MS=2500`. Objetivo: texto 8.5 → >50 FPS; intro 12.6 → >60.
6. **El usuario confirma la música por oído** (título, intro, texto). NO avanzar sin esa
   confirmación.

### 10.3 FASE B — Re-medir los cuellos de botella restantes (tras A)

Con el texto ya rápido, repetir `analyze_route.py` (ventanas de 120 frames con top-PC)
sobre el recorrido completo. Quedará:
- **S-DD1 real**: $C0:8871/86F5/89FB (transformación: DEC A / BRA / BPL — trabajo real
  no skippeable) en boot y transiciones pesadas (17-38 FPS).
- **Lógica de cinemática $C3:9xxx** (17-38 FPS).
- **Frame work $C8:F94A/F884** (sampler del boot).
Verificar también el **artefacto del sampler**: atribuye $C2:DB30 como dominante cuando
el spin real está en DB39/3E (muestrea 1-de-8 en el PC del yield) — documentar si
persiste, no afecta al fix (la A/B es la verdad).

### 10.4 FASE C — S-DD1 (el siguiente bloque grande)

- Revisar si la caché LRU + dual-worker SDL3 + pre-fetch (§5.3) están ACTIVOS en 2.Beta
  (puede que se hayan perdido en el cambio de unidad E:→F:). Medir hit-rate.
- Si el camino S-DD1 está interpretado en los bucles $C0:86F5/8876/89FB: considerar
  AOT de la transformación o caché de bloques descomprimidos (los 26% medidos antes).
- Validación: A/B + portClock; el S-DD1 no toca el SPC, riesgo de audio bajo, pero igual
  el usuario confirma.

### 10.5 FASE D — Frame pacing y audio (invariante)

- La música la mantiene el SPC en su propia línea de tiempo (RTL_APU_CYCLES_PER_FRAME
  = 17088/frame; el FF avanza el SPC en chunks exactos — verificado por portClock).
- Si tras A/B/C algún frame baja de 60: medir con PHASE_MS y decidir entre más FF
  (otros spins), S-DD1, o AOT de la lógica — NUNCA saltarse trabajo real sin A/B.
- No tocar `snes_catchupApu` ni el cap de 10k (lección aprendida dos veces).

### 10.7 FASE E — Pantalla negra al entrar en batalla (informado por el usuario 2026-08-27)

**Síntoma:** al abrir el escenario de lucha, la pantalla se queda NEGRA pero la
música carga y suena. El usuario ampliará la grabación de pulsaciones para entrar
en una batalla real y poder reproducirla.

**Diagnóstico preliminar (sin tocar nada):** música OK ⇒ APU/SPC + lógica del juego
funcionan; pantalla negra ⇒ falla la carga/RENDER del fondo de batalla — la misma
familia que el fix del puente (S-DD1 MMC window en cart.c, ver §7). Hipótesis a
verificar con cosim (misma metodología que los fondos):

1. **S-DD1 en la entrada de batalla**: ¿el DMA de descompresión del fondo de batalla
   pasa por el MMC ($4804-$4807) y resuelve mal la dirección (como FD:5419 del puente)?
   Comparar con bsnes el estado S-DD1 (r4800/r4801, offsets) y VRAM/CGRAM en los frames
   de transición a batalla.
2. **Modo de vídeo de la batalla**: Star Ocean usa un modo especial (campo Mode 7 /
   arena). Verificar el registro $2105 (mode) y los layer masks que el renderer recibe
   en la entrada de batalla — ¿el recomp renderiza capas que el modo de batalla no
   configura, o falta una capa?
3. **Carga del fondo por DMA** (battle BG load): trazar el DMA→VRAM en la transición
   (existe `trace_dma_cgram.py` / `SNESRECOMP_DMA_DEBUG`).

**Procedimiento cuando el usuario entregue la grabación ampliada:**
1. Reproducir con `SNESRECOMP_REPLAY_FILE` hasta la batalla; confirmar pantalla negra.
2. Cosim A/B vs bsnes (Track B oracle): primer frame de divergencia en PPU/VRAM/CGRAM
   en la transición a batalla → localizar la causa exacta (como se hizo con el puente).
3. Fix + A/B + portClock + confirmación visual/auditiva del usuario. 1.Release congelado.

### 10.6 Metodología obligatoria (reglas de la sesión)

1. **1.Release congelado** (no se compila ni se copia nada a `1.Release/`).
2. Todo cambio → primero A/B cosim (states + **portClock**), luego 2.Beta.
3. Instrumentación nueva siempre env-gated (`SNESRECOMP_HOTLOG`, `SNESRECOMP_DBTRACE`,
   `SNESRECOMP_YIELD_LOG`, `SNESRECOMP_PHASE_MS`) y retirada al terminar la fase.
4. Después de cada fase: actualizar §4.3/§7 de este documento.
5. **Cerrar el juego al terminar** (invariante §5.7).
6. Herramientas re-creadas esta sesión (se perdieron con E:): `SNESRECOMP_REPLAY_FILE`
   (+ `SNESRECOMP_REPLAY_UP_PAUSE_MS`) en main.c; scripts `run_ab8.py`, `run_hot.py`,
   `run_db.py`, `analyze_route.py`, `add_replay.py` en build-cosim/. Botones de la
   grabación (descifrados): orden real = Up,Down,Left,Right,Select,Start,A,B,X,Y,L,R →
   **0x100=A, 0x010=Up** (no lo que decía el comentario viejo).

## 11. Sincronización de carpetas externas (2026-08-27)

Se actualizaron dos carpetas hermanas con el estado validado de **1.Release**
(fondos correctos + audio, SIN el fast-forward de 2.Beta):

- **`$PROJECT_ROOT\StarOceanSNESRecomp\`** (fuente): `git archive HEAD`
  (base commit ccc523c = 1.Release equivalente) + overlay de los fixes validados:
  - `snesrecomp/runner/src/snes/cart.c` — fix MMC/S-DD1 (fondos del puente)
  - `snesrecomp/runner/src/common_rtl.c/.h` — `rtl_apu_pace_check` (audio en AOT)
  - `config/bank00.cfg` + `config/bankC0.cfg` — `force_lle` de boot (estabilidad)
  - Verificado: sin fast-forward (0), con MMC fix (1), APU pacing (1), replay (0).
- **`$PROJECT_ROOT\StarOceanRecomp-win-1.0\`** (paquete):
  - `StarOcean.exe` = el exe validado de 1.Release (el original del upstream queda
    como `StarOceanSNESRecomp.exe`)
  - `config.ini`, `keybinds.ini`, `rom.cfg` (apuntando a F:), tier2 jsons de 1.Release
  - **Probado: boot OK, imagen + audio WASAPI OK, frame 1200 sin errores.**

**PENDIENTE próxima sesión:** el `generated/` de StarOceanSNESRecomp NO se regeneró —
los `force_lle` nuevos solo surten efecto al regenerar el AOT desde las configs nuevas
(v2_emit.py + ROM). Verificar que el árbol compila de cero antes de usarlo como base.
El fast-forward de 2.Beta NO está en estas carpetas (se añadirá cuando la Fase A del
§10 pase la validación, si el usuario lo decide).

### 4.5 FF extendido — BUG ENCONTRADO Y CORREGIDO (2026-08-28)

**Intento:** extender el fast-forward a 4 pares adicionales de spin ($CA:6D13/18, $C2:0B51/57,
$C2:DB39/3E, $C6:18D1/D6) para cubrir título, intro, texto y zona texto.

**Resultado:** A/B cosim reveló que los4 pares nuevos causan divergencia REAL de estado
(re-producido 2026-08-28 con instrumentación `SNESRECOMP_VFF_LOG` y
`SNESRECOMP_WRITE_WATCH=0x1E5`, no solo hPos):
- Frames 0-283: byte-idénticos ✅
- Frame 284: primer disparo del FF en un sitio intermedio (intro `$C2:0B57`, v=138
  campo activo). hPos diverge (state record 202 vs 190) pero WRAM/CPU siguen idénticos.
- Frame 286: **ESCRITURA DIVERGENTE de $7E:01E5** — `OFF=0x20 ON=0x22` y bandera P
  (0x20/0x22). WRAM comienza a divergir de forma persistente; wratham 308+ diverge.
- **CAUSA RAÍZ (contrastada con writewatch, NO el target/redondeo):** los waits
  intermedios $CA/$C2/$C6 **NO son spins puros**. Contienen trabajo real por-frame
  entreverado: la variable de animación/estado `$7E:01E5` se escribe desde dos PCs
  dentro del wait (`pc=C8:2923` → 0x00 y `pc=CB:0924` → 0x7E, alternando). El FF
  salta el beam y OmitE ese trabajo, descorriendo el estado del juego desde el
  frame 286. (El writewatch muestra `$01E5` escribirse en TODOS los frames; es un
  state-machine/task counter del juego, no un contador del spin.)
- **Descartado (experimento A/B):** cambiar el redondeo a `master_cycles` (`42*u`
  → delta exacto) rompe el BOOT desde frame 11 — el redondeo a 42 es crítico para
  la alineación del beam de $C8. La divergencia no es el redondeo.

**Fix:** revertidos los4 pares nuevos. FF solo cubre los8 PCs originales:
$C8:F425/F42A/F40F/F414, $CC:0538/053D/054E/0553. LDA-long (0xAF) se detecta
pero no se usa (ningún PC original lo requiere).

**Validación A/B:** sin los4 pares, con la instrumentación env-gated
(SNESRECOMP_VFF_LOG + write-watch) activada: **850 frames = IDENTICAL** (0
divergencias CPU/WRAM/VRAM/CGRAM). 2.Beta no se tocó.

**Conclusión de diseño (importante):** el fast-forward del beam solo es seguro
**si el wait es el ÚLTIMO bloque del frame** (los spins $C8/$CC del main/battle
loop yield al wrap con el hijo del frame driver, y todo el frame que sigue es el
NMI del siguiente frame). Los waits intermedios (título/intro/texto) NO se pueden
fast-forwardear así: adelantan el master y omiten trabajo real que actualiza
variables de estado ($7E:01E5), descorriendo el juego a partir del primer cruce.

**Coste de rendimiento que esto implica:** título/intro/texto siguen a 8-13 FPS
(el wait $C2:DBxx girando el spin interpretado). La vía correcta para acelerarlos
NO es FF del beam sino **AOT de esas rutinas** (correr spin+trabajo en código
nativo, N veces más rápido, sin tocar el master) — ver §10 FASE C. Oráculo:
`ab_diff` ON-vs-OFF sobre los states observables; bsnes no sirve aquí (divergencia
del modelo de frame driver desde frame ~10, documentado en §4.4).

### 4.6 FASE 2b — VFF del spin puro del texto $C2:DB39/3E (2026-08-28)

**Contexto** (§10 FASE C AOT): el AOT del banco $C2 (rutina $C2:DB33-E04A,
recompilado con `v2_regen --banks c2`, mapeo MMC byte-exacto) es **bit-exacto**
en el vuelco completo (PC-watch: DB33/DB43/DBE8/DE89/DF1F/E023 con master idéntico
al LLE puro en frames 3019-3021), y WRAM completa + $7E:01E5 idénticas en TODOS
los frames. Pero **el cruce de frame 3021→3022 diverge en fase (−276 máster,
hPos 660 vs LLE 384)**. Probadas y descartadas: (a) AOT completo del vuelco, (b)
VFF+AOT del vuelco (entry DB48) — ambas divergen en el MISMO frame 3021 con el
mismo +276. El desfase es intrínseco al vuelco AOT (que avanza el máster sin
sincronizar el beam PPU a cada escritura), no al spin.

**Fix que SÍ funciona:** fast-forward **solo del spin puro** del texto. Los bytes
reales en 0x2DB39/0x2DB3E son `AD 12 42 30 FB` / `AD 12 42 10 FB` = `LDA $4212`
+ `BMI/BPL` (spin puro SIN trabajo por-iteración, a diferencia de los waits
$CA/$C2:0B51/$C6). Se añadieron `0xC2DB39` y `0xC2DB3E` a la lista del VFF del
bridge (que ya redondea el máster a 42 mpq y alinea al boundary del frame). El
vuelco ($C2:DB43-E04A) queda en LLE puro.

**Validación A/B (oráculo ON-vs-OFF con `SNESRECOMP_NO_VBLANK_FF=1`):**
**3050 frames = 0 divergencias** (boot + main loop + battle + título + intro +
texto). Bit-exacto. Lecturas de $4212 en la zona texto caen de 1.640.693 a
1.293.940 (−347K), y el VFF dispara C2DB3E saltando ~240K ciclos/frame.

**Rendimiento medido (so_cosim, tramo 0-3400 frames):** 181.6s → 161.6s wall
(−11%), concentrado en los ~100 frames de texto (el spin DB39 es ~68% del tiempo
de texto). En 2.Beta esto se traduce en subir el texto de ~8 a ~12-13 FPS (mismo
mecanismo que el FF de los 8 PCs).

**Estado:** cambio en `interp_bridge.c` (lista VFF + guardas), compilado en
so_cosim y en **2.Beta** (2.Beta/StarOcean.exe regenerado). 1.Release intacto.
AOT del banco C2 REVERTIDO (diverge en cruce de frame); `config/bankC2.cfg`
eliminado; `generated/` minimal restaurado.

### 4.7 VFF extendido — $CA título + $C6 zona texto validados; intro descartada (2026-08-28)

**Re-evaluación individual de los 4 pares que el revert de §4.5 descartó juntos.**
El C2-DB39/3E ya estaba validado (§4.6). Se probaron los demás UNO A UNO con el
mismo oráculo A/B (ON vs `SNESRECOMP_NO_VBLANK_FF=1`, 3050 frames):

| Par | Zona | Veredicto | Evidencia |
|---|---|---|---|
| `$C2:DB39/3E` | texto | ✅ bit-exacto | §4.6, 0 divergencias |
| `$CA:6D13/18` | título (new game/continue) | ✅ bit-exacto | 0 divergencias, 35 fires (frames 241-360) |
| `$C6:18D1/D6` | zona texto | ✅ bit-exacto | 0 divergencias, 6 fires |
| `$C2:0B51/57` | intro (LDA-long 0xAF) | ❌ diverge f284 | hPos 194 vs 206, 2765/3050 divergentes |

**Conclusión:** el único culpable del revert de §4.5 era la intro `$C2:0B51/57`
(dispara en v=138 campo activo con trabajo real en el wait). Los otros tres son
spins puros y el FF es seguro. Integrados en 2.Beta: texto+título+zona texto a
60 FPS en sus waits (el límite restante es el vuelco LLE y la animación real).

**Intro $C2:0B51/57:** permanece LLE (no fast-forwardeable). Opción futura:
separar el spin puro de la animación real que hay en su wait (writewatch mostró
$7E:01E5 desde C8:2923/CB:0924 en ese tramo).

### 4.8 Intro $C2:0B51/57 — diagnóstico y veredicto LLE (2026-08-28)

**Estructura (desensamblado, off=0x20B51):** `LDA $421200 / BMI -5` (espera fin
de vblank) + `LDA $421200 / BPL -5` (espera inicio de vblank) + `RTL`. Es un
**spin de vblank puro y aislado** — NO contiene trabajo real dentro (ningún PC de
la intro escribe $01E5/OAM/DMA).

**Por qué el FF diverge (writewatch 0x1E5, 2092 escrituras ON vs OFF):** los
VALORES de $01E5 coinciden al 100%; solo 3 escrituras difieren en PC, TODAS en
el banco $CA (título): f285 `ca6d16` vs `ca6d13`, f286 `ca642f` vs `ca6430`,
f310 `ca5cbe` vs `ca5cb9`. El FF de la intro salta desde **campo activo
(v=138)** al vblank-start, adelantando el master ~118K ciclos; ese adelanto
desfasa la fase en que el scheduler ejecuta el trabajo real del título (que
escribe $01E5 y $420C/$2100 tras su propio spin CA:6D13). El título NO
re-sincroniza al vblank siguiente (su vuelco es sensible a la fase), a
diferencia de C2/CA/C6 cuyos waits son el último bloque o re-sincronizan.

**Veredicto:** el patrón "VFF del sub-spin puro + trabajo en LLE" NO aplica:
el trabajo no está dentro del spin de la intro (está en otra tarea del
scheduler), así que no hay nada que separar. La intro permanece en LLE
(8-13 FPS en su tramo). El coste es aceptable (tramo breve de la intro).

**Estado de 2.Beta (20:04):** FF integrados = texto C2-DB39/3E, título
CA-6D13/18, zona texto C6-18D1/D6. Intro sin FF. Menú de nombre medido por el
usuario: 25-26 FPS (era 11 con solo C2). Título: sigue limitado por su vuelco
LLE + animación (30-40). 1.Release intacto.

### 4.9 INTRO $C2:0B51/57 — FF VALIDADO con paso 48 (2026-08-28)

**Reintento tras §4.8** (que la dejó en LLE): se midió con PC-watch fino el
master de salida del spin en f284 (el frame que divergía):

| | master de salida (C20B5D) | intra (mod 357368) | Δ |
|---|---|---|---|
| OFF (LLE puro) | 128602096 | 306984 | — |
| ON (FF con mpq-42, §4.7) | 128602066 | 306954 | **−30** |
| ON (FF con paso 48) | 128602096 | 306984 | **0** ✅ |

**Causa raíz:** el spin de la intro es la variante **LDA-long (0xAF)**; su
iteración (LDA long $4212 + branch) cuesta **48 ciclos de master** (medido:
lecturas $4212 en intra 306894→306942 = +48), no 42 como los LDA-abs
validados (C8/CC/DB/6D/18). El FF redondeaba al múltiplo de 42 desde el
master actual → aterrizaba 30 ciclos antes de la lectura que el LLE hace al
detectar el borde de vblank; ese desfase desplazaba la fase del trabajo real
del título (writewatch §4.8: ca6d13→ca6d16).

**Fix:** en `interp_bridge.c`, el target del VFF usa `step = is_long ? 48 : 42`.
Los spins LDA-abs validados conservan su paso 42; solo la variante 0xAF (la
intro) usa 48.

**Validación:** A/B ON-vs-OFF completo, **3050 frames, 0 divergencias**
(boot + main loop + battle + título + intro + texto; incluye f284 que antes
divergía). Integrado en 2.Beta. Los 3 FF previos (C2-DB39/3E, CA-6D13/18,
C6-18D1/D6) intactos; 1.Release intacto.

**Nota perfilado de pantallas (frames reales del usuario, contador fNNNN en
el título de la ventana):** Enix f4 (10 FPS, S-DD1 C0:8500 58%), Tri-Ace
f151 (60 FPS), VRSS f331 (10 FPS, C2:0B51 51%), DUET f444 (56 FPS, C2:0B51
97%). El coste restante del logo/menú es el handshake SPC + descompresión
S-DD1 en LLE (C0:8000-C0:8500), no el vuelco.

### 4.10 Boot/Enix — desglose del coste y veredicto LLE (2026-08-28)

**Medición aislada y limpia (ventana 0-100 frames, cosim):** baseline de 200
frames sin probes = 27.6s, con APUPROF = 25.1s. El flush APU acumula 939 ms
host-time en la ventana 0-100 (~14s) = **~7%**. La hipótesis del flush como
cuello de botella queda **REFUTADA**: el 93% restante son las instrucciones
LLE del handshake SPC.

**Perfil 256B de la ventana:** $C0:8500 = 58% (handshake SPC: upload IPL
`CMP $2140/BNE` + `STA $2140-2143`, ~705K accesos APU en LLE por `force_lle
0xC08500`), $C0:8400 = 10% (secuenciador flags), $C8:F400 = 10% (main loop,
ya FF), resto = drivers SPC. NO hay hot spot de descompresión S-DD1 aquí
(8 DMAs `src=C0:8000` no son el coste dominante).

**S-DD1 cache LRU + dual-worker (§5.3, §7 marcado VÁLIDO-perf): NO está en el
checkout.** `snesrecomp/runner/src/snes/sdd1.c` (953 líneas) es solo el
fallback síncrono (sin `SDL_CreateThread`/worker/LRU/pre-fetch); no se
encontró en ningún `.c/.h`. Se perdió en el cambio E:→F: (o nunca se commitió
al bucket que viajó).

**Veredicto (fase-safe):** el handshake SPC no es acelerable sin romper la
cadencia APU que `force_lle 0xC08500` garantiza: (1) VFF no aplica (no es un
wait de vblank $4212, es un poll que debe sync con el SPC por iteración para
el upload IPL); (2) AOT del handshake rompería la cadencia por acceso (por
eso `force_lle`). Ademásel boot/Enix es TRANSITORIO (frames 0-100, ~2s) y NO

es pantalla objetivo de 60fps. **Se deja como está**

**CONFIRMACION a nivel de codigo (2026-08-30, sesion boot->menu nombre):**
el mecanismo exacto que bloquea el AOT del handshake queda probado en el
fuente: `RtlRunFrame` fija `g_apu_frame_time_valid=true` al inicio de frame
(common_rtl.c:446), y con ese timeline activo toda lectura de puerto APU va por
`rtl_sync_apu_to_cpu_locked` -> `apu_runToGuestCycle`, que hace early-return si
`!portTimeValid` (apu.c:137). `portTimeValid` solo se activa con una ESCRITURA
al puerto (`apu_schedulePortWrite`, apu.c:89-92). En el boot el juego polla
`$2140` esperando `$AA/$BB` ANTES de escribir nada -> en AOT el SPC nunca
avanza (early-return constante) -> por eso `force_lle 0xC08500`. El tier LLE no
se cuelga porque su ruta es distinta: acumula `s_apu_pending_master` y hace
flush periodico por `snes_catchupApu` con la relacion fija guest->SPC
(`kInterpApuPerMaster`), no por el timeline. Reinicia/verifica el HANDOFF 4.10,
que tenia el veredicto correcto; esta es la confirmacion mecanica. **Se deja
como está (LLE), sin tocar la cadencia APU.** Reimplementar la caché dual-worker S-DD1 (trabajo grande y de
riesgo, HANDOFF §5.3 item 3) solo beneficia pantallas que SÍ descomprimen
gráfico (logo/menú de juego), no el boot — futuro candidato, no bloqueante
para 60fps.

### 4.11 VALIDACIÓN FINAL del 2.Beta actual (2026-08-28, cierre de sesión)

**A/B de confirmación con el binario limpio de `build-cosim/so_cosim.exe`**
(ninja reconstruido: "no work to do" = exe al día con `interp_bridge.c`
limpio, ambos 21:57). Doble carrera, único cambio = gate del FF:

| Run | Frames | Wall | ENV |
|---|---|---|---|
| ON | 3050 | 229.4s | (FF activo por defecto) |
| OFF | 3050 | 469.4s | `SNESRECOMP_NO_VBLANK_FF=1` |

**`ab_diff.py` (196K-record por frame incl. CPU/WRAM/VRAM/CGRAM/beam):**
```
records: 3050  differing frames: 0
CPU reg diffs: 0 · WRAM: 0 · VRAM: 0 · CGRAM: 0
VERDICT: IDENTICAL
```
Cubre boot + main loop + batalla + título + intro + texto. Los 4 FF + la
intro a paso 48 quedan **bit-exactos** en el binario limpio. Iterables
temporales (`valab_*.bin/.log`, `_validate_ab.py`) borrados al terminar.

**1.Release confirmado INTACTO:** `1.Release/StarOcean.exe` = 449024 B,
Aug 27 18:41, md5 `3f026ac1` (coincide con §4.1). Backups presentes.

**Sin instrumentación residual:** `grep` de SPINWATCH/apup_/PCPROF en el
runner = 0 coincidencias. Solo restan los 4 FF + intro en la lista VFF.

## 12. GRABACIÓN de inputs NUEVA + PLAN próxima sesión (2026-08-28)

**✔️ ESTADO ACTUALIZADO (el .bsv SÍ está en el workspace):** la "caminata"
nueva está en la raíz del proyecto:
`$PROJECT_ROOT\StarOceanTest2\Star Ocean (Japan)-20260828-173819.bsv`
(557598 B, grabada hoy 17:39 con Record Movie y Reset System). Desarrollo:
edificios nuevos, diálogos, 3 batallas, salida del pueblo a zona nueva y
savestate (guardar partida).

**⚠️ Análisis de bytes del `.bsv`:** magic `BSV1` + firma `BSTC...Performance`
incrustada; el grueso del archivo (~0x2000-0x75000) es **estado serializado
(savestate/state-data: tablas paleta, tiles 5x7, bloques de estado)**, no un
stream de joypad. Solo hay bytes sueltos no-cero dispersos y una cola enorme
de ceros desde el último no-cero (0x7557e). Conclusión: es un **BSV1 con el
savestate incrustado**, NO un movie limpio de inputs. Para reproducirlo con
fidelidad hace falta el parser de bsnes-plus (no invertirlo a mano o se
desincroniza). **Vía fiable:** usar el propio `cosim/drive_bsnesplus` del
checkout para reproducir el movie y volcar los inputs reales a un log
CONFIABLE (p.ej. comparar contra el byte-stream cuando drive_bsnesplus se
ejecta headless), o re-grabar en bsnes-plus sin "Reset System" (movie limpio
de inputs). No inventar un conversor byte-guesser que pueda corromper la
reproducción de la partida (rompería el A/B).

**Cómo se convierte .bsv → replay (pipeline objetivo):** la 2.Beta consume un
archivo `frame hexmask` por línea vía `SNESRECOMP_REPLAY_FILE=<path>`
(`grabacion_inputs.txt` es el ejemplo: `2803 00000010` = Up press,
`2805 00000000` = release; bits: `0x100=A`, `0x010=Up`). **No hay
`bsv_to_inputs.py` en el checkout** (se perdió con E:→F:). La grabación vieja
`grabacion_inputs.txt` (Aug 26, solo ~20 eventos hasta frame 5112) sigue
disponible como referencia del formato.

**✔️ DECISIÓN del usuario (2026-08-28):** re-grabar la caminata en bsnes-plus
solo con `Movie ▸ Record Movie` (SIN "Reset System"/"Restart") para que el
`.bsv` salga con cabecera limpia de inputs y convertirlo al formato de la beta
sin riesgo. Aclaración del usuario: la caminata nueva **NO lleva los Up de
cambio de escena** (eso ya está en `grabacion_inputs.txt`, la otra, que SÍ los
tiene y llega al frame 5112, puente alarma). Son complementarias: la vieja
sirve para localizar cortes de pantalla con Up; la nueva cubre más juego
(edificios, diálogos, batallas, guardado) para perfilar más zonas.

Pendiente del usuario: pasarme la ruta (o copiar a `build-cosim/`) del `.bsv`
re-grabado sin Reset System.

**Diagnóstico externo pendiente:** el usuario subió un vídeo de la beta a
YouTube y Gemini le devolverá mañana un análisis de vídeo (fotogramas → FPS
real por pantalla) para contrastar con nuestros perfiles. Con su diagnóstico
podremos correlacionar el FPS visual con las ventanas del profiler.

---

### 12.1 PLAN próxima sesión (orden recomendado, todo bajo A/B + portClock;
1.Release congelado)

**PASO 0 — Esperar el reporte de rendimiento del usuario de la beta actual**
(4 FF + intro a paso 48). Confirmar por oído: música en título/menú/intro
texto. No tocar nada hasta ese reporte.

**PASO 1 — Conseguir la grabación nueva (bloqueante para el perfilado real):**
pedir al usuario la ruta del `.bsv`/movie nuevo, copiarla a `build-cosim/` y
re-escribir el conversor `.bsv → frame-mask` si falta (parseo BSV1 +
detección de cambios por frame). Referencia: `grabacion_inputs.txt`.

**PASO 2 — Reproducir la partida nueva y perfilar por ventana de frames** con
`SNESRECOMP_HOTLOG`/sampler y el contador de frames del título de la ventana
(`fNNNNN | NN FPS`, ya integrado). Localizar con qué
eventos las pantallas nuevas (edificios, diálogos, 3 batallas, salida del
pueblo, guardado) y medir FPS real en cada una.

**PASO 3 — Aplicar el desglose §4.10 a cada pantalla nueva** (SPC handshake
vs S-DD1 vs vuelco vs animación) con el profiler 256B; decidir por ventana
si el límite es un spin cubrible (FF), S-DD1, o vuelco/animación LLE.

**PASO 4 — Los DOS grandes pendientes de rendimiento (fuera de 60fps ->
objetivo):**
1. **Caché LRU + dual-worker S-DD1** (HANDOFF §5.3, perdida en E:→F:):
   buscar en backups/commits el `sdd1.c` con threads; si no aparece,
   considerar reimplementar (pre-compile de bloques + worker SDL3). Beneficia
   logo/menú/pantallas que descomprimen gráfico (S-DD1 en LLE = 26%+
   del coste de esas pantallas). No afecta al boot (sin descompresión ahí).
2. **AOT del vuelco C2** (texto): el AOT entrenado es bit-exacto dentro del
   vuelco pero diverge en el cruce de frame 3021→3022 (−276 máster) por el
   master sin sincronizar al boundary — si Gemini/el profiler confirman que
   el texto/el menú siguen siendo el cuello, retomar la alineación del cruce.

**PASO 5 — Validación de cada aceleración:** A/B completo (3050+ frames)
con `ab_diff` + portClock extrínseco (`SNESRECOMP_YIELD_LOG`), meterlo en
2.Beta solo tras 0 divergencias, y el usuario confirma por oído + vídeo.
Nunca tocar 1.Release.

**Regla de oro de todos los cambios:** (1) 1.Release congelado; (2) primer
A/B cosim (states + portClock), luego 2.Beta; (3) instrumentación env-gated
y retirada al cerrar la fase; (4) actualizar §4.3/§7 tras cada fase;
(5) cerrar el juego al terminar.

---

### 12.2 ESTADO de las grabaciones (confirmado en disco) y decisión de uso

**Hay TRES archivos de partida, NINGUNO borrado:**
1. **`build-cosim/grabacion_inputs.txt`** (288 B) = la **MARCADA**, con los
   4 Up de cambio de escena (`2803` puente 1, `3187` puente 2 "el bueno",
   `4313` planeta, `5108` puente alarma), hasta frame `5112`. Ya en formato
   `frame hexmask`, reproducible hoy.
2. **`Star Ocean (Japan)-20260828-173819.bsv`** (557 KB, hoy) = la **NUEVA**
   SIN marcadores (pasa menú → intro, pero no tiene Up de escena). Tiene el
   savestate incrustado (por "Record Movie and Reset System").
3. **`Star Ocean (Japan) [Traducida Castellano]-20260825-101648.bsv`**
   (1.5 MB) = la más antigua, de la traducción.

**⚠️ HALLAZGO (2026-08-28) — la caminata nueva está TRUNCADA en los inputs:**
el `.bsv` de la nueva (2) está dominado por el savestate incrustado (por
"Record Movie and Reset System"): desglose de no-cero → `0x4000-0x20000` =
114K, `0x20000-0x40000` = 66K, `0x40000-0x60000` = 37K (todo estado); pero
`0x60000-0x75557f` (donde irían los inputs) solo tiene **40 bytes no-cero**, y
`0x7557f → final` = **cola de 76.960 bytes de ceros**. Conclusión: la
grabación larga (con las batallas) **NO se volcó completa al archivo** — solo
quedó el savestate + un puñado de inputs; la segunda mitad (batallas y
después) está ausente. Por eso al llegar a la casa de Rodax "deja de
funcionar": es el corte real de los inputs.

**Además:** `cosim/drive_bsnesplus` NO reproduce `.bsv` movies — su interfaz es
`--input start:duration:hexmask` desde CLI (para el cosim Track-B), no lee
archivos `.bsv`. No usar como extractor. Un parser a mano del `.bsv` con
savestate incrustado es arriesgado (desincroniza → rompe el A/B).

La vía fiable para tener la caminata larga es **re-grabarla con SOLO Record
Movie (sin Reset System), jugada entera pulsando A en los diálogos**.

**HALLAZGO DEFINITIVO del formato (2026-08-28, sesión 2 — cierra el caso):**
tenía fuentes del serializador en disco (`$PROJECT_ROOT
Nintendo/bsnes-plus-master/bsnes/ui-qt/movie/movie.{cpp,hpp}`: cabecera 16B
`BSV1`+ver{LE}+crc{LE}+state.size{LE} + savestate + stream de 2 bytes/frame
con bit order `JoypadID` B=0,Y=1,SEL=2,STA=3,Up=4,Dn=5,Lf=6,Rt=7,A=8,X=9,L=10,
R=11). Verificado empíricamente en 23:29 y 17:39: la cabecera es válida
(`BSV1` ver=15 crc=0xb3f89242, la misma ROM), PERO el tail tras
`16+state.size` NO es un stream de inputs — es mayoritariamente ceros y la
cola final es **100% ceros puros** (61.439 y 76.959 bytes, 0 no-cero). Los
`0x0001`/`0x0100` (A/B) dispersos caen en **residuos mod-64 VARIABLES** según
el archivo (23/24, 55/56 en 23:29; 29/30, 45/46, 61/62 en 17:39) — sin un K
fijo — y siempre en pares A+B a 0x40 de distancia: son **datos serializados
dentro del savestate**, NO la secuencia de joypad por frame. **Veredicto:** el
repo `bsnes-plus-master` del disco es de una versión DISTINTA a la que generó
estos `.bsv` (su serializador no coincide); adivinar offsets sería un parser
falso que rompería el A/B. **Vía correcta (la que el usuario sugiere):**
conseguir la fuente/diseño EXACTO del serializador de bsnes-plus que escribió
destos `.bsv` (p.ej. un documento/explicación de cómo funciona la grabación
en esa versión), y solo entonces construir el convertidor con garantías. Hasta
tenerlo, la vía de trabajo es el **input-log en vivo**
(`SNESRECOMP_INPUT_LOG` → `live_inputs.log`, como la marcada);
`build-cosim/grabar_input_log.bat` la lanza jugando en 2.Beta. NOTA: el bit
order `JoypadID` SÍ quedaría validado si se llega a leer un stream real. El
archivo `cosim/bsv_to_inputs.py` queda como borrador marcado "NO VALIDADO".
1.Release intacto (md5 `3f026ac1`), E: sin tocar.

**PRUEBAS COMPLETAS (sesión 2 — cierra el caso del `.bsv`):** tras TRES
comprobaciones independientes, los `.bsv` de la versión de bsnes-plus del
usuario NO guardan un flujo de input por frame en ninguna forma probada: (1)
stride 64 + byte +24 (descartado: 255-256 valores, firma de savestate); (2)
layout movie.cpp 2-byte tras savestate (descartado: cola final **100% ceros
puros** en los 3 archivos: 61.439 / 76.959 y 1.5MB→cola ceros, 0 no-cero);
(3) barrido contiguo de 2-byte válidos (el mayor run de 213KB = 106K frames
tiene solo **207 no-cero**: `0x00ff` en los frames iniciales = bits bajos
todos a 1 = **datos de estado**, y un `0x0100` (=A) **repetido a intervalos
exactos de 32 frames** en 23:29 (35923, 35955, 36087...) = **periodicidad
estructural del blob**, no pulsación; en 17:39 solo `0x0040`(x2) + `0x0100`
(x40) igualmente a paso 32). Los aparentes A/B caen siempre en residuos
mod-64 VARIABLES → son datos serializados del savestate incrustado, no el
joypad por frame. **Conclusión definitiva:** el serializador de la versión
que generó estos `.bsv` NO coincide con `movie.cpp` del repo (ni con ningún
layout estándar probado). NO se construye extractor adivinado (rompería el
A/B). La vía real queda en el **documento del formato exacto** que comenta el
usuario, o en el **input-log en vivo** `SNESRECOMP_INPUT_LOG`.

**DECISIÓN del usuario (2026-08-28):** "según las necesites escoges una u
otra" — la marcada (1) para localizar cambios de escena con Up; la nueva (2)
para perfilar más zonas (edificios, diálogos, batallas, guardado).

**Verificado que el enlazamiento funciona:** se lanzó la 2.Beta desde
`F:/.../StarOceanTest2/2.Beta/` con `SNESRECOMP_REPLAY_FILE=...grabacion_inputs.txt`
y el log mostró `[replay] loaded 20 input entries, 4 UP pause frames` —
el juego reprodujo la marcada automáticamente hasta el frame 5112 (puente
alarma). El mecanismo `SNESRECOMP_REPLAY_FILE` está operativo.

### 12.3 PLAN EXHAUSTIVO de la próxima sesión (2026-08-29)

> Contexto previo: el usuario percibe la 2.Beta más lenta que 1.Release en
> el tramo general pese a llevar los 4 FF. La investigación solo-análisis no
> encontró disparidad de build (beta y release2 ambos VS17 /O2 NDEBUG con los
> mismos flags y fuentes); la hipótesis más sólida es el **coste residual del
> hot-loop**: el guard del VFF en `interp_bridge.c` evalúa 14 comparaciones
> de `pc_before` por opcode LLE (8 originales + 4 FF nuevos + intro, =14).
> Ver §4.11 (validación) y plan abajo (PASO 3.4).

**OBJETIVO:** cerrar los 60fps estables; reiterado, 1.Release NO se toca.

**PASO 0 — Estado de entrada (checklist matutino):**
- Cerrar cualquier `StarOcean.exe`/`so_cosim.exe` vivo (invariante §5.7).
- Confirmar 1.Release intacto (md5 `3f026ac1`).
- Confirmar la beta en `2.Beta/` (md5 `8ed1ba74`).
- Comprobar el diagnóstico de vídeo de Gemini (si el usuario lo comparte).

**PASO 1 — Conseguir el `.bsv` de la partida nueva en formato limpio**
(bloqueante para perfilar la caminata):
- 1a. PEDIR al usuario el `.bsv` re-grabado SOLO con Record Movie (sin Reset
     System). Si lo entrega, el movie trae cabecera limpia de inputs.
- 1b. Si no lo re-graba, extraer los inputs de la caminata nueva actual
     (`...20260828-173819.bsv`) con `cosim/drive_bsnesplus` (disponible:
     456KB exe + snes.dll) reproducido headless, volcando los joypads a un
     log fiable. NO inventar un parser byte-guesser (riesgo de desincronizar
     la reproducción y romper el A/B).
- 1c. Convertir a formato `frame hexmask` (igual que grabacion_inputs.txt),
     guardar como `build-cosim/caminata_nueva_inputs.txt`.

**PASO 2 — Perfilar la partida nueva por ventanas** (cuando esté el replay):
- Reproducir en so_cosim con `SNESRECOMP_HOTLOG` + sampler y el contador de
  frames (`fNNNNN | NN FPS`, ya integrado).
- Obtener del usuario los frames reales de cada fase (o del vídeo/OCR):
  edificios, diálogos, 3 batallas, salida del pueblo, guardado.
- Desglose §4.10 por ventana (SPC handshake vs S-DD1 vs vuelco vs animación)
  con el profiler 256B.

**PASO 3 — Aceleraciones candidatas (por orden de impacto → esfuerzo):**
- 3.1 **Reducir el coste residual del hot-loop del VFF** (afecta a TODAS las
     pantallas LLE, no solo spins): optimizar el guard para que NO evalúe
     las 14 `pc_before ==` por opcode cuando no aplica. Ideas: enrutar por
     un check de página/salto rápido, o un tabla hash de PCs, o extraer el
     chequeo a una función inline que corto-ciruncuite por `in.k` (banco).
     Validar con A/B y medir FPS ganancia. IRÍA SOLO A LA BETA.
- 3.2 **Caché LRU + dual-worker S-DD1** (§5.3, perdida en E:→F:): buscar
     `sdd1.c` con threads en backups/commits; si no, reimplementar
     (pre-compile de bloques + worker SDL3). Beneficia logo/menú/pantallas
     que descomprimen gráfico.
- 3.3 **AOT del vuelco C2** (texto): retomar la alineación del cruce de
     frame 3021→3022 (−276 máster) si el texto sigue siendo cuello.
- 3.4 Verificar que la beta no arrastra ninguna instrumentación activa por
     defecto que la frene frente a release (ya descartado en main.c, pero
     re-confirmar el runner completo antes de tocar 3.1).

**PASO 4 — Validación de cada cambio:** A/B completo (3050+ frames) con
`ab_diff` + portClock extrínseco (`SNESRECOMP_YIELD_LOG`), 0 divergencias
antes de tocar 2.Beta; usuario confirma por oído + vídeo tras cada beta.

**PASO 5 — Cierre:** limpiar instrumentación/temporales, cerrar el juego,
actualizar §4.3/§7/§12, y verificar 1.Release intacto.

**Regla de oro:** (1) 1.Release congelado, jamás recompilar ni sobreescribir
su exe; (2) primer A/B cosim, luego 2.Beta; (3) instrumentación env-gated y
retirada al cerrar cada fase; (4) actualizar HANDOFF tras cada cambio;
(5) cerrar el juego al terminar.


### 12.4 EXTRACTOR .smv → frame hexmask VALIDADO (2026-08-29)

**Vía nueva y definitiva para inputs: snes9x + .smv** (sustituye al .bsv de
bsnes-plus, cuyo layout no era parseable).

**Herramienta:** `build-cosim/smv_to_inputs.py` — lee cabecera SMV (magic
`SMV\x1a`, ver LE, frame count, ctrl mask, movie_opts, offsets), verifica el
flag reset-anchored (`movie_opts` bit0=1 = boot en frío; bit0=0 = quicksave =
NO usar, desincroniza), y emite `frame hexmask` en el formato de
`grabacion_inputs.txt` (solo cambios; mask en bit order JoypadID).

**BIT ORDER REAL (validado contra fuente `F:/.../snes9x/snes9x.h` líneas
99-108, SNES_*_MASK — NO usar el doc de TASVideos, que está equivocado para
esta versión):** el movie guarda `joypad[].buttons` con:
- bit 15 = B, 14 = Y, 13 = Sel, 12 = Start, 11 = Up, 10 = Dn, 9 = Lft,
  8 = Rgt, 7 = A, 6 = X, 5 = L, 4 = R (bits 0-3 reservados).
- Mapeo a JoypadID recomp: B→0, Y→1, Sel→2, Start→3, Up→4, Dn→5, Lft→6,
  Rgt→7, A→8, X→9, L→10, R→11. Valores observados en el .smv real:
  0x0800=Up, 0x0400=Dn, 0x0200=Lft, 0x0100=Rgt, 0x0080=A, 0x1000=Start,
  0x8000=B, 0x4000=Y.

**Validado con `Star Ocean (Japan).smv` (1828 frames, reset-anchored):**
1828 frames extraídos (coincide header), 0 valores con bits reservados,
distribución coherente (A, 4 direcciones ×2, combos A+B, Start). Primeras
pulsaciones: A en f388/501/572/643/778 (confirmar menús), direcciones
f1066-f1301, A+B f1403+, Start f1473.

**Cómo grabar (usuario):** abrir la ROM en snes9x y pulsar Record SIN tocar
nada (o Reset justo antes) → el movie sale reset-anchored y el frame 0
coincide con el boot en frío de la beta. NO cargar savestates ni pausar
antes de grabar. El exe de snes9x está en `$PROJECT_ROOT
Nintendo/snes9x-1.63-1615-cf95f09-win32-x64` (y la fuente en `F:/.../snes9x`).

**Pendiente:** grabar la caminata larga completa en snes9x desde boot,
convertir con smv_to_inputs.py y validar con A/B que la beta reproduce la
ruta (hasta batallas) sin desincronizar. 1.Release intacto, E: sin tocar.

### 12.5 SESIÓN 2026-08-29 (noche) — CAMINATA LARGA EN SMV, estado para mañana

**Logro del día:** vía de inputs resuelta de forma definitiva. El .bsv de
bsnes-plus NO era parseable (layout desconocido, savestate incrustado); la
vía real es **snes9x + .smv** con `build-cosim/smv_to_inputs.py` (validado
contra la fuente `F:/.../snes9x/snes9x.h` líneas 99-108 — bit order real:
B=bit15, Y=14, Sel=13, Start=12, Up=11, Dn=10, Lft=9, Rgt=8, A=7, X=6, L=5,
R=4; NO usar el doc de TASVideos, está equivocado para esta versión).

**Caminata larga grabada por el usuario:** `Star Ocean (Japan).smv` (109KB,
54319 frames ≈ 15 min, reset-anchored ✓). Convertida a
`build-cosim/caminata_larga.txt` (912 líneas frame hexmask, copiada también
a `2.Beta/replay_caminata_larga.txt`). Llega hasta FUERA DEL POBLADO con 3
batallas. Final: X (f53222) → Lft (f53399) → A×3 (f53439/53522/53583) →
B×2 (f53641/53805); 501 frames idle tras la última B.

**Prueba en 2.Beta:** se lanzó con `SNESRECOMP_REPLAY_FILE=
2.Beta/replay_caminata_larga.txt`. `[replay] loaded 912 input entries, 61 UP
pause frames`. El usuario aceleró con Tab (turbo, NO desincroniza — Tab no
está en keybinds, solo activa g_turbo en main.c:575/1454). **La beta avanzó
hasta la cinemática y el usuario la cerró para dormir** (proceso cerrado).
Queda pendiente: verificar hasta dónde llegó sin desincronizar y completar
la validación de la caminata (batallas).

**Keybinds beta (para referencia):** A=X, B=Z, X=S, Y=A, L=C, R=V,
Start=Return, Select=RightShift, direcciones=flechas, Turbo=Tab.

**Nota importante para mañana:** la beta pausa 1500ms tras cada pulsación
de Up (`SNESRECOMP_REPLAY_UP_PAUSE_MS`), y esta caminata tiene 61 Ups → la
reproducción sin turbo es lenta. Se puede bajar con
`SNESRECOMP_REPLAY_UP_PAUSE_MS=0` si hace falta. El turbo (Tab) es seguro.

**Pendientes:** (1) validar la caminata larga hasta las batallas en la beta
sin desincronizar; (2) si va bien, integrar el flujo smv→hexmask en la
rutina de pruebas; (3) seguir con el plan de FPS (hot-loop VFF guard). 
1.Release intacto, E: sin tocar.

### 12.6 PLAN DE MAÑANA (2026-08-30) — PRIORIDAD: REPLAY COMPLETO CON MONITORIZACIÓN

**ORDEN DE TRABAJO (decisión del usuario):**

**PASO 1 (prioridad absoluta) — Replay completo de la caminata con
monitorización para descifrar las batallas:**
- Relanzar la 2.Beta con `SNESRECOMP_REPLAY_FILE=2.Beta/replay_caminata_larga.txt`
  (54319 frames, caminata hasta fuera del poblado con 3 batallas).
- Con `SNESRECOMP_REPLAY_UP_PAUSE_MS=0` para no perder tiempo en las 61
  pausas de Up (o turbo con Tab, seguro: no desincroniza).
- **Herramientas de monitorización a activar durante el replay:** capturar
  el estado en cada batalla — log de DMA/CPU (`[DMA_TRIG]`, `[CPU_W]` ya
  activos en el log), fases de pantalla (beam/hPos), y si hace falta
  instrumentar en `interp_bridge.c`/runner (env-gated) los puntos de
  entrada/salida de la rutina de batalla (PCs de la zona de combate del
  banco C0/C2/C8 que ya están delimitados) para ver cómo se comporta el
  spin de la batalla y si diverge.
- **Objetivo:** descifrar CÓMO funcionan las batallas en el recomp — si el
  spin/wait de combate corre en LLE sin divergir, si el VFF de los 8 PCs
  cubre algún wait de batalla, y si hay trabajo real entrelazado que cause
  el fallo (pantalla negra en batalla, reportado antes).
- **Criterio de corte:** si el replay completo se vuelve un lío (divergencias
  tempranas, instrumentación enorme, batallas que rompen), ABANDONAR este
  hilo y pasar al PASO 2 (regla del usuario).

**PASO 2 (si el paso 1 es un lío) — Estabilizar el framerate:**
- Retomar el perfil del hot-loop: el guard del VFF en `interp_bridge.c`
  evalúa 14 comparaciones; evaluar simplificación/enrutado por tabla para
  recuperar FPS en la 2.Beta sin tocar la fase del beam.
- Metodología: A/B cosim (ab_diff) primero, luego integrar en 2.Beta;
  1.Release congelado; instrumentación env-gated y retirada al cerrar.

**Recordatorio de estado:** la caminata está convertida y validada en
formato; `smv_to_inputs.py` listo y documentado. La beta avanzó anoche
hasta la cinemática sin problemas aparentes (cerrada por el usuario).
1.Release intacto (md5 3f026ac1), E: sin tocar.

### 12.7 SESIÓN 2026-08-29 (mañana) — BUG PANTALLA NEGRA EN BATALLA + ANÁLISIS NMI

**Objetivo de la sesión:** investigar por qué la batalla muestra pantalla negra
con solo música en la 2.Beta, usando la caminata larga (54319 frames).

#### 12.7.1 Ejecución del replay con captura de pantalla

Se lanzó la 2.Beta con `SNESRECOMP_REPLAY_FILE=2.Beta/replay_caminata_larga.txt`
y `SNESRECOMP_REPLAY_UP_PAUSE_MS=0`. Se creó script de captura de pantalla
(`capture_battle.ps1`) que guarda PNGs cada 3 segundos.

**Resultados:**
- Replay completo: 673+ capturas PNG, juego vivo (PID 12276, 84MB RAM)
- **Freeze temporal en f20462** ("no responde" en Windows) — el juego se
  recuperó solo al cabo de unos segundos
- El juego continuó hasta f46257+ a **60 FPS estables**
- **Pantalla NEGRA persistente durante toda la batalla** — el usuario confirmó
  ver solo el título de ventana + fondo negro + música sonando
- Solo 2 capturas <10KB (f471/f474 = 7.4KB, transiciones tempranas); todas
  las demás >50KB (ventana con contenido — pero el PPU muestra negro)

#### 12.7.2 Análisis del NMI handler del ROM

El NMI handler está en CPU `$00:FEB9` (file offset 0x80B9 con 512B header).
Desensamblado completo:

```
$FEB9: STZ $420A / STZ $4207 / STZ $4208  ; Limpiar timers
$FEC2: SEP #$20 / LDA #$01 / STA $4200     ; AJR=1, NMI=0
$FEC9: SEI / STZ $4200                       ; Deshabilitar todo
$FECD: STZ $420B / STZ $420C                 ; Limpiar DMA/HDMA
$FED3: LDA #$80 / STA $2100                  ; *** FORCED BLANK ON ***
$FED8: STA $2133 / LDA #$09 / STA $2105     ; Configurar PPU
      ... (BG mode, tilemaps, screen enable) ...
$FF0B: PHB / LDA #$70 / PHA / PLB           ; DB = $70
$FF10: LDA $7E00 / CMP #$94 / BEQ +7
$FF16: JSL $C0:CA16                          ; *** Game update (NMI callback) ***
$FF1A: JSR $8319                             ; Post-update processing
$FF20: (table lookup + JSL $C0:8594)         ; Sprite/OAM update
      ... (más subrutinas) ...
$FFB4: LDA #$80 / STA $2100                  ; *** FORCED BLANK ON (2ª vez) ***
$FFB9: LDA #$0F / STA $2100                  ; *** FORCED BLANK CLEAR! ***
      ... (más subrutinas post-clear) ...
$FF6A: RTI                                   ; Retorno del NMI
```

**Hallazgo clave:** el handler SÍ limpia forced blank ($0F) en $FFB9, ANTES
del RTI en $FF6A. Hay ~10 subrutinas entre el clear y el RTI.

#### 12.7.3 Análisis del frame driver (so_rtl.c)

`RunOneFrameOfGame()` en `src/so_rtl.c:52`:

```c
void RunOneFrameOfGame(void) {
  g_snes->inNmi = true;           // ← NMI se activa CADA frame
  if (g_snes->nmiEnabled) {       // ← Solo si el juego habilitó NMI
    cpu_push_interrupt_frame(&g_cpu);
    interp_bridge_run_interrupt(&g_cpu, 0x00FEB9);  // NMI handler
    g_cpu.S = saved_S;
  }
  // ... run game code until yield ...
}
```

Después, `SoDrawPpuFrame()` renderiza 225 líneas leyendo `ppu->inidisp`.
Si `inidisp & 0x80` (forced blank), la línea se renderiza negra (`memset 0`).

**Flujo del frame:**
1. NMI handler → forced blank ON → game update ($C0:CA16) → subrutinas
2. NMI handler → forced blank OFF ($0F) → más subrutinas → RTI
3. Game code continua hasta yield
4. `SoDrawPpuFrame()` renderiza con el estado actual de `inidisp`

Si `inidisp` es $0F al llegar a `SoDrawPpuFrame`, la imagen se ve.
Si es $80, pantalla negra.

#### 12.7.4 Escrituras a $2100 en el ROM

| Tipo | Count | Banks |
|---|---|---|
| Forced blank ON ($80) | 46 | $00, $01, $C2, $C4 |
| Forced blank OFF ($0F) | 6 | $00, $01 |
| Otras ($01-$0E) | 27 | varios |

Las 6 instancias de clear NO tienen callers directos por JSR/JSL — se hacen
vía el NMI handler (dispatch indirecto).

#### 12.7.5 Datos del log durante la batalla

```
[so_rtl] frame 36000 nmiEn=1 resume=$C04D80
[so_rtl] frame 37800 nmiEn=1 resume=$C04D76
```

`nmiEn=1` confirma que el juego SÍ tiene NMI habilitado durante la batalla.
El `resume=$C04Dxx` indica que la CPU está en el banco $C0 (código del juego),
no en un loop del NMI handler.

#### 12.7.6 Estado de los fast-forwards (10 integrados en 2.Beta)

| PC | Zona | Paso | Estado |
|---|---|---|---|
| `$C8:F425/F42A` | Main loop entrada corta | 42 | ✅ |
| `$C8:F40F/F414` | Main loop entrada larga | 42 | ✅ |
| `$CC:0538/053D` | Batalla variante A | 42 | ✅ |
| `$CC:054E/0553` | Batalla variante B | 42 | ✅ |
| `$C2:DB39/3E` | Texto (spin puro) | 42 | ✅ |
| `$CA:6D13/18` | Título (new game/continue) | 42 | ✅ |
| `$C6:18D1/D6` | Zona texto | 42 | ✅ |
| `$C2:0B51/57` | Intro (LDA-long 0xAF) | 48 | ✅ |

Todos validados A/B: 3050 frames, 0 divergencias. Bit-exacto.

#### 12.7.7 HIPÓTESIS para la pantalla negra en batalla

**H1: El NMI handler se ejecuta pero algo DESPUÉS del clear ($FFB9) vuelve
a poner forced blank ($80).** Hay ~10 subrutinas entre $FFB9 y $FF6A (RTI).
Si alguna de ellas escribe $2100=$80, el clear se pierde.

**H2: El recomp no ejecuta el NMI handler completo.** Si `interp_bridge_run_interrupt`
se detiene antes del RTI (por yield/abandono), el forced blank ON ($FED3)
queda activo y el clear ($FFB9) nunca se ejecuta.

**H3: El juego deshabilita NMI durante la batalla.** Si `$4200` se escribe
con bit 7=0 durante la batalla, `nmiEnabled=false` y el handler no corre.
Pero el log muestra `nmiEn=1` en frames 36000+, así que esto solo aplicaría
en frames intermedios.

**H4: Timing del forced blank.** En la SNES real, el NMI handler corre
durante vblank (scanlines 225-261). El forced blank se pone al inicio del
NMI y se limpia al final. En el recomp, el NMI corre al INICIO del frame
(antes de `SoDrawPpuFrame`). Si el juego espera a vblank para poner/limpiar
forced blank, el recomp podría estar ejecutando las escrituras en el momento
equivocado del beam.

**Prioridad:** H2 es la más fácil de verificar (añadir log en el recomp
para ver si el NMI handler llega al RTI). H1 requiere desensamblar las
subrutinas entre $FFB9-$FF6A. H4 requiere cambiar el frame driver (riesgo
alto).

#### 12.7.8 Plan actualizado para alcanzar paridad SNES

**FASE A — Resolver pantalla negra en batalla (PRIORIDAD):**
1. Verificar H2: añadir log temporal en `interp_bridge_run_interrupt` para
   confirmar que el NMI handler alcanza el RTI en cada frame durante la batalla
2. Si H2 confirmado: investigar por qué el handler se detiene antes del RTI
3. Si H2 descartado: verificar H1 desensamblando las subrutinas $FFB9-$FF6A
4. Si H1/H2 descartados: investigar H4 (timing del forced blank)
5. **Todos los cambios se prueban en 2.Beta; 1.Release NO se toca**

**FASE B — Estabilizar framerate (después de FASE A):**
1. Hot-loop VFF: optimizar las 14 comparaciones en `interp_bridge.c`
2. Restaurar S-DD1 dual-worker + LRU cache (si se localiza en E:)
3. AOT incremental por banco (si el drift de frame se resuelve)

**FASE C — Paridad 100% SNES (futuro):**
1. Frame driver compatible con bsnes (Timing perfecto)
2. Verificación cosim completa (3050+ frames bit-exacto)
3. Validación visual frame a frame vs bsnes-plus


#### 12.7.9 HALLAZGO NUEVO (2026-08-29) — dispatch NMI/IRQ y causa raíz del negro

**Estado del dispatch (generated/dispatch_v2.c) — verificado hoy:**

| PC | Función | Modo M1X1 | Interpretación |
|---|---|---|---|
| `$00:FEB9` | `NmiTrampoline_*` | AOT | JML $C0:0000 (4 ciclos) → tail-call |
| `$C0:0000` | `NmiHandler_M1X1` | **STUB VACÍO** (solo RecompStackPush/Pop + RETURN_NORMAL, cero instrucciones del juego) | ← PROBLEMA |
| `$00:FEBD` | `IrqTrampoline_*` | AOT | JML $C0:0221 |
| `$C0:0221` | `IrqHandler` | **NULL → LLE (correcto)** | ok |

**Conclusión de los vectores reales (ROM Star Ocean (Japan).sfc, 6MB):**
- RESET=$00:FEC1, NMI=$00:FEB9 (`5C 00 00 C0`=JML $C0:0000), IRQ=$00:FEBD (`5C 21 02 C0`=JML $C0:0221).
- El cfg de bankC0.cfg YA declara que los handlers NMI/IRQ "deben correr bajo el
  intérprete" (porque el JML del vector no se resuelve), pero el emisor AOT-compiló
  el NMI como **stub vacío** y el dispatch lo enruta ahí.

**Evidencia en runtime (2.Beta/battle_trace.log, run de la batalla):**
- Antes de batalla `fstate` muestra `nmiEn=0 inidisp=0F` (campo visible).
- f20466/67: el juego pone `nmiEn=1` + `$2100=$80` (forced blank ON) — NMI.
- f20468+ SIN NINGUNA escritura a $2100; `inidisp=80` permanentemente (ya no hay
  `[inidisp]` lines). Música sigue, 60 FPS de lógica, pantalla NEGRA.
- El IRQ handler real ($C0:0221) contiene `LDA $DA / STA $2100` (restaura brillo)
  en $C0:02BC, pero NO se invoca: el juego usa NMI en batalla, y el NMI handler
  AOT no ejecuta el clear.

**CAUSA RAÍZ:** en batalla el juego habilita NMI; el frame driver llama
`interp_bridge_run_interrupt(0x00FEB9)` → dispatch → `NmiTrampoline` → stub vacío
→ el handler NMI real (que copia WRAM `$DA` → `$2100` cada vblank) nunca corre;
el forced blank ON de la transición (f20467) queda clavado → negro permanente.

**Fix candidato (SOLO 2.Beta):** `force_lle 0xC00000` en config/bankC0.cfg (igual
que los 14 del boot) para que el NMI handler corra bajo el intérprete con el mapeo
MMC **runtime** correcto (páginas 0,1,4,5; no los defaults 0,1,2,3 que usa el emisor).
Fase-safe, no toca el beam. VALIDAR con A/B 3050 frames antes de integrar.

**Nota mapeo MMC (importante):** el emisor (snes65816.py rom_offset) usa páginas
estáticas `SDD1_MMC_DEFAULT_PAGES=(0,1,2,3)`, pero el runner usa registros RUNTIME
$4804-$4807. build-cosim/sdd1-trace.log muestra en runtime `r4804=00 r4805=01
r4806=04 r4807=05`. Los bancos $C0-$DF coinciden (páginas 0,1) pero los bancos
$E0-$FF NO: el emisor los leería del offset equivocado. Cualquier re-emión que toque
$E0-$FF (o la re-generación del handler) debe respetar el mapeo runtime, no el default.

**Referencia externa útil (anotada, NO incorporada):** repo `etroimcasso/Snaggletooth`
rama `ci/snes-ipl-and-blargg` — core SNES clean-room MIT. Docs relevantes para futuras
validaciones de timing/audio: `spc700-cpu.md`, `apu-machine.md` (IPL/handshake SPC700),
`s-dsp-behavior.md` (dónde la doc pública del S-DSP es errónea/incompleta), y la sección
"SNES machine" (contadores de vídeo, NMI vblank, IRQ H/V-timer). No es dependencia; es
referencia de comportamiento hardware.

**PRÓXIMO:** recibir trace de bsnes-plus del usuario de la entrada a batalla (writes a
$2100 + $4200 + VTIMER + PCs) para confirmar empíricamente que el NMI handler es quien
restaura $2100, antes de aplicar el force_lle.

**SUPERADO — CAUSA RAÍZ REAL (2026-08-29, trace bsnes de la batalla):**
NO es el NMI. En batalla el juego usa **IRQ de vblank**: el handler IRQ ($C0:0221,
LLE correcto) escribe VTIMER=258 ($4209/$420A desde $C0:02E9) y en la línea V:258
restaura brillo `LDA $DA / STA $2100` ($C0:02BC, $DA=$0F) — mientras que en V:216
pone forced blank ON ($C0:02E2, $2100=$80). El frame driver de so_rtl.c SOLO entrega
IRQ en las líneas 0-224 (`for i=0..224; if i==trigger`), así que la IRQ de V:258
(nunca alcanzada) se pierde → brillo nunca restaurado → negro permanente.

**FIX APLICADO (2.Beta, so_rtl.c):** (1) en SoDrawPpuFrame, si vIrqEnabled y
vTimer>224, entregar la IRQ de vblank tras el bucle de render (beam posicionado en
vTimer vía snes_sync_master_clock); (2) si el LLE cede en el spin $D9 ($C084AE,
LDA $D9/BNE/BEQ, que espera el ciclo del IRQ), entregar la IRQ de forced blank ahí
mismo y REANUDAR el LLE para que el spin complete y la tarea de frame (fade-in
$CC:0B44, $DA++) corra. El ciclo VTIMER 216↔258 solo aparece en batalla; el campo
no lo toca.

**VALIDACIÓN: A/B 3050 frames IDENTICAL** (campo/intro/texto bit-exactos, 0
divergencias). **Validación en vivo de batalla (replay largo, f20466+): inidisp=0F
de forma continua (70+ frames verificados), resume progresa por el motor de batalla
(C5037F, C62D98, C7070D...), USUARIO CONFIRMA QUE VE LA BATALLA EN PANTALLA.**
El negro en batalla queda RESUELTO. FPS en batalla ~6-7 (otra tarea, no bloqueante
para la corrección).

1.Release: INTACTO (md5 3f026ac1, no se toca). Todas las pruebas en 2.Beta.

**SOURCE DEL REPLAY (crítico): la caminata larga se grabó en bsnes-plus, no con el recomp.  Los input-logs no son intercambiables: bsnes-plus usa el driver H/V exacto y el recomp el driver yield-en-quiescencia (divergen ~desde frame 10 por diseño).  Un log grabado en bsnes-plus aplicado al recomp desalinea las pulsaciones desde ~frame 10 -> personaje fuera de ruta y NPC descolocados: NO es fallo del fix IRQ ni grabación corrupta, es motor distinto.  La marcada que sí era bit-exact se grabó EN el recomp (SNESRECOMP_INPUT_LOG).  Desde esto, la caminata validada se graba en el recomp con build-cosim/grabar_input_log_NUEVA.bat (exe 15:54, frio frame 0, destinos replay_caminata_NUEVA.txt).

**PERFIL DEL TITULO (2026-08-29, trace bsnes f17-627 + VFF headless):** el spin del menu $CC053D/$CA6D18 domina ~42% del tiempo HARDWARE pero YA esta en el guard del VFF (interp_bridge.c:837/845). Medicion headless (so_cosim, 2500f, VFF_LOG): 1 fire VFF/frame en el titulo, cada uno salta ~261K ciclos (73% del frame, v=33->225). El piso real es ~96K ciclos/frame de trabajo LLE (vblank + vuelco + animacion estrellas + DMA). El limite del titulo NO es el spin: es el trabajo LLE restante. Acelerar exige AOT de rutinas del menu con validacion A/B fase-safe. vff_title_2500f.log guardado.

**PERFIL LLE DEL TITULO — DESGLOSE (2026-08-29, trace bsnes f281-627, hotzones):** el trabajo LLE del menu se concentra en UNA sola rutina: **$C3:8F5E-$C3:90FE = 70,8% del trabajo real** ($C3:8Fxx 42,85% + $C3:90xx 27,94%). Es el **animador de estrellas** del fondo del titulo: bucle que por cada estrella calcula posicion con RNG ($14, ROR/LSR), usa el multiplicador hardware $4202/$4203 (vía JSR $ADAC/$AD6E — determinista) y escribe al buffer OAM-buffer $00,X (STA $00,X/$02,X), con RTS final en $90FE y salida temprana JMP $8D93. Callers: JSR $8F61 desde bank23:3FA1 (dispatcher) y JSR $8F5E desde bank3D:0095.
**Phase-safety verificada byte a byte: NO hay accesos absolutos a registros PPU/APU ($21xx/$42xx) en todo el rango $C3:8F5E-90FE** (patrones 8D/AD/9D/BD/99/B9 xx 21|42: 0 hits). Solo pagina cero/RAM + multiplicador HW. A diferencia del C2 (que contenía LDA $4212 en el spin), esta rutina NO lee el beam → **candidato AOT phase-safe**.
**Veredicto AOT titulo:** emitir SOLO la funcion $C3:8F5E-90FE (cfg por funcion, v2_regen --banks c3 preserva bank00/c0/c1/dispatch/unresolved por digest) → validar A/B 3050 frames + tramo titulo f700-2500 → medir FPS. Si diverge, declarar fallida y revertir (patron C2). Herramientas en build-cosim/: trace_hotzones.py, title_lle_split.py, disasm_starfield.py.
**CORRECCION AL HISTORIAL (2026-08-29): NO existe caché LRU/dual-worker en sdd1.c** — ni en F: ni en E: (diff: F: solo anade el bloque debug SNESRECOMP_MMC_MAP env-gated). El dato previo de 'caché LRU + dual-worker perdidos al cambiar E:→F:' era erroneo: nunca estuvo en el codigo. El coste S-DD1 del campo (7-8 FPS) es la descompresion por bloque por frame, y acelerarla requeriría AÑADIR una cache de bloques (nueva, no restauracion) con validacion A/B estricta.

**FASE 1 AOT BANCO C3 — RESULTADO (2026-08-29):** se emitió la funcion de estrellas del titulo como AOT y se midio. DETALLES:
- (a) **Mapeo real corregido**: el trace de bsnes se grabo con la ROM TRADUCIDA al castellano (parche al-vuelo, E:\...Traducida Castellano.sfc), que inserta bytes en el prologo y desplaza la rutina **+3 bytes**. El hotzone del trace ($C3:8F61+) corresponde en la ROM original a **$C3:8F50-$C3:910D** (prologo M16 $C3:8F50 LDA #$0001/STA $32; bucle $C3:8F5E LDA $0000,Y; loop-back JMP $8F5E en 9083/908C; salida JMP $8D93; RTL en $C3:910D; tabla lookup 910E+). Sin accesos $21xx; escribe $004800 (S-DD1, determinista). PARA FUTUROS TRACES traducidos: PCs calientes = +3 respecto a la original.
- (b) **A/B ON-vs-OFF: 3050 frames IDENTICAL (0 divergencias)** — incluye boot+logos+titulo (f-700-3050). El AOT del C3 es BU-EXACTO. Baseline OFF = so_cosim_clean.exe, ON = so_cosim_c3_on.exe.
- (c) **Instrumental gap**: la ruta `--banks` de v2_regen NO emitia `g_ram_routine_guards[]` (el runner lo exige; link LNK2001). FIX en snesrecomp-tool/tools/v2_regen.py:_emit_dispatch_table: ahora emite sentinel-only (sin ram_routines en los cfg). so_cosim y build-beta linkean.
- (d) **Integracion 2.Beta**: cmake -S . -B build-beta (re-glob generated/*.c, estaba sin bankc3_v2.c -> LNK1120) + build-beta-rebuild.bat. 2.Beta/StarOcean.exe md5 8f717052 -> **47a44e7a**, contiene simbolo StarField (grep -c=1). 1.Release INTACTO (3f026ac1).
- (e) **MEDIDA FPS TITULO (veredicto): SIN GANANCIA.** 2.Beta windowed: 30-35 FPS con C3 (f1133-f3194, muestreo 5x) vs 31-37 FPS sin C3 (f5197-f6703, medicion previa). Dentro del ruido -> **el animador de estrellas NO es el cuello de botella real del titulo**. Mi perfil por conteo de instrucciones del trace de bsnes sobre-atribuyo % de ciclos-hardware a host-time del recomp. CONCLUSION: el limite del titulo esta en el trabajo LLE de vblank/vuelco/DMA/per-frame, no en la rutina de estrellas. La via correcta es un perfil de HOST-TIME del recomp (Release so_cosim headless con reloj, NO mas traces de bsnes).
- (f) **Mantener el C3 emitido**: es BU-EXACTO y no cuesta nada (solo se ejecuta cuando el dispatch lo alcanza). Se conserva; no aporta al titulo pero puede ayudar donde esa rutina SI domine host-time. si en el futuro se confirma con host-time-profile, se revisa.
- (g) **CONFIRMACION VISUAL DEL USUARIO (2026-08-29):** con la 2.Beta (C3 integrado) ve en el titulo **25-31 FPS**, y al pulsar A para mostrar New Game/Continue/Sound **baja a 23 estables**. Coincide con la medida windowed (30-35). El bajon a 23 al renderizar las opciones del menu apunta a un coste de transicion especifico (render opciones + marco), no al fondo de estrellas ni al spin. Refuerza: el cuello real es vblank/vuelco/DMA per-frame, y hay una componente extra al pintar el menu.
- Archivos: config/bankC3.cfg, generated/bankc3_v2.c + dispatch_v2.c (regenerados), snesrecomp-tool/tools/v2_regen.py (fix guards), build-cosim/bench_c3.py + ab_c3.py + ab_diff.py. HERAMIENTA clave restante: perfil de host-time del recomp (Release cosim) — esa es la prioridad para el titulo Y el campo.

**CONFIRMACION DEL USUARIO (2026-08-29, jugando la 2.Beta con C3):** boot ~8s; logos 60 con bajones; menu titulo 38/39; New Game/Continue 24/29; menu nombre 29/33 (antes 11); intro 60 con rascadas en logos de empresas; puente 25/30 (antes 11); CAMPO (casa de Ronx) 10/11 (antes 7-8). -> **EL C3 MEJORA EL CAMPO y el puente**: el auto-promote del banco C3 incluyo 12 funciones mas (multiplicaciones/calculo $ADAC/$AD6E/$917C) que el campo y la cinematica usan para posicion/logica. Primer AOT con ganancia medida en juego.

**CONTABILIDAD HOST-TIME CERRADA (2026-08-29, cosim RELEASE headless, SNES_COSIM_OFF=1, 900 frames boot, ~40ms/frame):**
- interp_bridge_run_until_quiescent (trabajo CPU del frame: AOT+LLE+driver): **~24-30 ms/frame (dominante)**
- SoDrawPpuFrame (render 225 lineas ppu_runLine + 8 HDMA/linea + IRQ raster + vblank-IRQ): **~10.5 ms/frame**
- APU flush (bridge_apu_flush): ~1.6-2.7 ms/frame (2M llamadas)
- rtl_sync_apu_to_cpu_locked (polls $2140 en AOT): ~0.44 ms/frame (2.66M llamadas)
- DMA: ~0.15 ms/frame (949K bytes); S-DD1: ~0.05 ms/frame (139 bloques, 98 B/frame — NEGLIGIBLE, NO es el cuello ni en boot ni titulo); RtlApuWrite: ~0.01 ms/frame; apu boundary: ~0.01 ms/frame
- pasos interpretados: ~1-1.3K/frame (intérprete casi ocioso; el boot corre en AOT bank00/C0)
- **El cosim es ~3.5-4.6x mas lento que la beta windowed** (el cosim corre flat-out sin sleep; la beta hace 60fps). Escalando: beta boot ~11ms/frame, titulo ~26ms/frame, campo ~100ms/frame.
- VEREDICTO: los dos cuellos son (1) el trabajo CPU del frame (AOT del driver del juego, NO pasos LLE, NO S-DD1, NO APU) y (2) el render PPU por linea (ppu_runLine). El campo NO es Mode 7 (Star Ocean usa Mode 1 en campo; sus DMA son WRAM->VRAM 2KB, no S-DD1).
- Vias: (a) optimizar ppu_runLine / el vuelco PPU (ayuda titulo Y campo); (b) reducir el coste bridgeq (perfil de la region AOT del frame; el VFF ya cubre spins, el resto es trabajo real). Instrumentacion: macro SNESRECOMP_INTERP_PROFILE (solo cosim) en interp_bridge.c (histograma PCs + contadores), sdd1.c, dma.c, common_rtl.c (RtlApuWrite/rtl_sync_apu_to_cpu_locked/rtl_sync_apu_frame_boundary), src/so_rtl.c (SoDrawPpuFrame/RunOneFrameOfGame), cosim/harness_so.c (volcados). build-cosim-release/so_cosim.exe = cosim Release instrumentado. El campo necesita medicion propia con un input-log grabado EN el recomp (grabar_input_log_NUEVA.bat) una vez el framerate lo permita.

## PLAN MAÑANA (2026-08-30) — PARIDAD FPS CON SNES (REENCUADRADO: el premio es el runtime, no el AOT)

METODOLOGIA (la misma que arreglo los fondos negros + combates: nada se aprueba sin contrastar):
1. Medir baseline bit-exacto de la zona a tocar (A/B frames, 0 divergencias) ANTES de tocar codigo.
2. Cambio MINIMO, invariante a pixeles / invariante de fase, sin tocar 1.Release, pruebas en 2.Beta.
3. A/B completo (3050+ frames) = 0 divergencias de estado (CPU/WRAM/VRAM/CGRAM).
4. Validacion VISUAL: capturas antes/despues de cada pantalla afectada (titulo, campo, batalla) identicas.
5. Medir FPS delante/detras en la zona.
6. Divergencia o rompe boot/titulo/campo/batalla -> REVERTIR, diagnosticar, reintentar. Nunca integrar a medias.
7. Solo integrar en 2.Beta si pasa TODO. 1.Release INTACTO (md5 3f026ac1).

LECCION CLAVE de la noche: la brecha campo 34 (1.Release) vs 10 (2.Beta) NO es por alcance AOT (ambas enlazan 00/C0/C1 y 2.Beta solo anade C3, que mejora). 1.Release es rapido PORQUE es el runtime del 27 ago que hace MENOS trabajo correcto (por eso las batallas no muestran imagen). El objetivo NO es imitar 1.Release recortando trabajo: es hacer rapido el runtime CORRECTO de 2.Beta sin perder batallas. Los ~34fps de 1.Release valen como cota superior orientativa, no como meta ciega.

PASO 1 (HECHO hoy 2026-08-30 — ver seccion 'RESULTADO DE ESTA SESION' arriba) — ATRIBUIR la regresion campo: veredicto = el coste del campo es el INTERPRETE LLE del codigo real del campo (bancos C2/C8/CA, interp816_runOpcode ~5.3µs/paso en cosim) + el volcado PPU (23.7 ms/frame). DESCARTADO: quiescent-scan (12%), fetch (1%), fix IRQ/vblank (no se dispara en campo), VFF, APU flush, S-DD1. El arranque de 10s = handshake SPC asíncrono (1.28M pasos LLE esperando la respuesta real de la APU).
   Test 1a (descartado) — el fix IRQ/vblank de batallas NO se dispara en campo (gate por vIrqEnabled+VTIMER 225-261 correcto); no puede explicar la brecha.
   PASO 1 HECHO (ver § RESULTADO, sección FASE P0): el AOT de la rutina más caliente del campo ($C2:FC-FE, blit de tiles) NO es viable phase-safe — escribe DMA $420B (FE2D/FE8C) y tiene tail-calls; igual que el C2, la fase rompería. El siguiente objetivo de impacto real es el RENDER PPU (23.7 ms/frame en campo, fase-safe de optimizar): perfilar SoDrawPpuFrame/ppu_runLine por fase y reducir el coste del volcado sin cambiar salida ni avance de beam.
   Test 1b — VFF/FF guards ON vs OFF en campo: debe AHORRAR; si cuesta, se optimiza el guard (reducir la evaluacion por instr).
   Test 1c — APU flush / descompresion S-DD1 campo: re-confirmar con input-log nativo que no son el coste (ya 0.05ms en boot/titulo; campo puede diferir) -> si lo fueran, es la via de cache de bloques.
   Test 1d — render PPU (PpuDrawBackgrounds) campo: culpable probable junto al fix IRQ; perfil fino por fase (tile fetch vs colormath vs sprites).
   VERDICTO del PASO 1 -> define el blanco exacto de optimizacion del PASO 2 (con numeros, no con intuicion).

PASO 2 (despues) — OPTIMIZAR EL CULPABLE identificado, invariante a pixeles/fase:
   - Si fix IRQ/vblank: reducir el trabajo redundante del blank/IRQ por frame (mantener batallas).
   - Si PPU render: cacheo de tiles/paletas por linea, evitar refetch, reducir colormath redundante.
   - Si bridgeq solo-AOT: ver si queda rutina fase-safe AOT-eable (patron C3) o si es el driver.
   PASOS: (b) perfil fino; (c) cambio minimo sin cambiar salida; (d) A/B 3050f + tramo campo/batalla; (e) capturas antes/despues; (f) FPS; (g) integrar 2.Beta solo si 0 divergencias. Revertir si rompe algo.

PASO 3 — MEDICION FIABLE DEL CAMPO (habilita 1a-1d): grabar input-log NATIVO en el recomp (grabar_input_log_NUEVA.bat, cold-boot frame 0) hasta el campo, para A/B deterministico del coste de campo (el replay bsnes desincroniza del recorrido real por driver distinto y no vale como oracle; ver MARCADOR abajo). Establecer el A/B del tramo de la casa de Ronx (7-11fps) como referencia.

PASO 4 — PENDIENTES de mas bajo nivel (no bloquear): glitch PPU f49500 (bordes sprites agua/arbol/tejado), guardar/cargar del juego (bloqueo al cargar), save/loadstate del emulador (historial de romper musica) — con la misma metodologia cuando el FPS del campo este estabilizado.

## RE-PERFIL DEL CAMPO TRAS EL GUARD 0B82/87 (2026-08-30) — siguiente cuello identificado

**Método**: exe `af9e4f5e`, walkthrough casa (replay_casa_dialogos, f92-f16516) con `SNESRECOMP_PHASE_MS=1` (muestreo por-PC exacto 4096 buckets ya en la beta). Agregué los últimos 55 dumps de top-PCs (~7.13M muestras) que cubren el campo f9600+. Juego cerrado, temporales limpiados.

**Top PCs del campo (agregado, % del LLE muestreado):**
- **`$C084B2` (2.89%) + `$C084B4` (3.30%) = 6.19%** — el par `LDA $00D9; BEQ -4` : **spin puro de espera sobre un flag de RAM** dentro de la rutina `$C0:84A3-B7`. NINGÚN guard lo cubre. (El 0B82 en el source de interp_bridge es Otra cosa: este es `$00D9`, memoria, no `$4212`.)
- `$C084A3` (0.54%) + `$C084A6` (1.51%) = **2.05%** — el poll `LDA $4212; BPL -5` (espera de inicio de vblank) de la MISMA rutina, arriba de los D9. Familia idéntica a los guards vblank ya validados (C8/CC/DB/0B82).
- `$C20B87`+`$C20B8A` = **4.24%** — residual del spin ya guardado (antes del guard era ~75%; el guard saltó la mayoría pero no todas las entradas).
- Familia `$C62D95-A9` (bucle scheduler del campo, ~10 PCs cada ~0.5-0.6%) ≈ **5.7%** — trabajo real (LDA $0000/X + BPL + DEC/BNE sobre contador), NO spin puro → candidato a AOT pero repartido y con JSR indirecto (perfil del blit C2:FC que tumbó el AOT).
- Familia `$C80790-A0` (~10 PCs) ≈ **3.7%** — bucle de espera con `SBC $0040; … BPL -5` en banco C8, semi-wait con trabajo.

**VEREDICTO de atribución (con números):** el siguiente cuello PUNTUAL más grande del campo es **la rutina de espera `$C0:84A3-B7`** (~8.24% combinado: 84A3+84A6+84B2+84B4).

***EXPERIMENTO HECHO Y REVERTIDO (2026-08-30):** añadí el guard VFF para el poll vblank `$C084A3/A6` (misma familia que 0B82) y lo validé completo (A/B cosim 10600f IDENTICAL + A/B masters a nivel-juego 15208f, campo f9600-f15208, 0 divergencias). PERO la verdad del terreno: **el guard es INERTE en el campo** — VFF_LOG mostró 0 fires de 84A3 en el campo (las 7307 entries son TODAS del frame 3, boot). Causa: el wait `$C0:84A3-B7` del campo corre en contexto **NO-quiescente** (dentro del trabajo del frame vía run_interrupt, yield_pc=0), mientras el guard VFF vive en la rama `auto_quiescent` (yield_pc=0xFFFFFFFE). El A/B dio idéntico porque el guard no se alcanza, no por correcto. **REVERTIDO** (no integro cambios sin ganancia): fuente restaurado (0B82 sí, 84A3 no), 2.Beta recompilado (exe `fe00b0c6`, funcionalmente = al validado `af9e4f5e`), 1.Release intacto. Lección: el perfil por-PC del juego muestra pasos interpretados que NO todos pasan por el guard; solo los waits que corren en auto_quiescent son VFF-eables (por eso 0B87 sí, 84A3 no).

***PROPUESTO como siguiente blanco (PASO 2 puntual), NO implementado**: el `$D9`-spin (84AE-84B4) es trabajo cooperativo del scheduler (no beam-wait) → NO VFF-eable sin romper fase. La vía que queda para el campo es (a) atacar el render PPU (fase-safe, 10-17ms en juego) o (b) AOT de una rutina real del campo con el patrón C3, exigiendo que sea phase-safe (sin DMA/tail-calls).    El scheduler C6:2D (trabajo, JSR indirecto) tiene riesgo tipo C2.*

## EXPERIMENTO AOTF — Estrella del título por fall-through: mecanismo OK, emisión CON BUG DE CICLOS (2026-08-30, REVERTIDO)

**Objetivo:** la rutina de estrellas `$C3:8F50-90FE` (LA rutina del menú de título, f700-f2500+) está emitida en AOT C3 (validada "bit-exacta" en FASE 1) PERO se entra por fall-through desde el bucle padre LLE (`8F4F: INY`), y el único bounce del bridge es por JSR/JSL (`is_call`) — así que **nunca disparaba**. Añadí un bounce por fall-through (SNESRECOMP_AOT_FALLTHROUGH) con ABI hrv=0 (`cpu_dispatch_pc`) + consumo del sentinela de unwind, y la variante M0X1 aliada al body M0X0 (el body es mode-adaptativo en X).

**Diagnóstico diferencial (logs de entrada/post + llegada del intérprete a 8F50/CC2794, ambos runs):** estado de entrada IDÉNTICO (master 79676518, registros iguales; hasta f146 los runs son byte a byte iguales). El unwind a `$CC2794` (dispatcher MMX) sale con los registros CPU IGUALES al LLE (A=6C00 X=0 Y=18E2 S=01FC DB=00). **PERO el cuerpo llega a CC2794 con 79741360 master vs LLE 79747046 = DÉFICIT DE 5686 master_cycles por pasada de estrellas.** Ese déficit de contabilidad de ciclos desalinea el beam → hPos diverge (max 1318) → y todo lo dependiente del timing diverge (CPU reg + WRAM desde f147). A/B cosim 3050f DIVERGED desde f147 (1595 frames).

**Lección clave (para NO repetir):** el "A/B validado" del C3 (FASE 1) NUNCA ejecutó el body de la estrella (fall-through no bounces) — solo validó las 12 funciones C3 alcanzadas por JSR. La estrella es una emisión que nunca se había ejecutado y su contabilidad de ciclos por bloque (cycles += N) es corta en ~5686 ciclos/pasada. El MECANISMO de bounce (hrv=0 + unwind) está demostrado correcto; el bloqueo es un BUG DEL EMISOR v2 en la contabilidad de ciclos del body. No es un bloque puntual (déficit acumulado) → no parche por encima (pisaría el intérprete).

**Además:** el cfg afirmaba un `JSR indirecto ($20E2,X)` en 8DDF — era un desensamblado desalineado; los bytes reales de 8DD0-8DE4 son `TXA/CLC/ADC #$1D/STA $BE/LDA $14,X/STA $FC/SEP #$20/STZ $20/...` (no hay JSR indirecto ahí).

**REVERTIDO limpio:** dispatch_v2.c restaurado del backup (md5 910921a), interp_bridge.c sin el bounce ni el diag (0 residuos AOTF), cosim reconstruido limpio (17:44). **2.Beta INTACTA (`fe00b0c6`), 1.Release INTACTA (`3f026ac1`).** Temporales (ab_aotf_*.bin/.log, ~1.2GB) borrados. No se tocó build-beta ni el exe de la beta.

**Estado del AOT de la estrella:** bloqueado hasta que se arregle la contabilidad de ciclos del emisor para `$C3:8F50-90FE`. La vía correcta es (a) regenerar el body con el emisor corregido (exigir A/B del body de la estrella EJECUTADO, no solo emitido) o (b) localizar el/los bloque(s) que infra-suman ciclos en bankc3_v2.c por bissección (checkpoints en L_8F80/L_9000/L_9093 vs LLE) y corregirlos a mano.

## PIVOTE (2026-08-30) — Objetivo 60 FPS en el tramo arranque→menú: la palanca GLOBAL es el coste del intérprete

Con el AOT de la estrella bloqueado en un bug del emisor, el cuello global del tramo sigue siendo el **coste LLE por paso** (`interp816_runOpcode`, ~5.3µs/paso en cosim, ~1.3µs en beta). Afecta a TODO el tramo: el HANDOFF previo ya atribuyó el arranque lento al handshake SPC (frame 3 = 1.28M pasos LLE de `LDA $2140/BNE`), el título a ~4568 pasos LLE/frame, el menú de nombre a trabajo LLE repartido. El experimento de atribución (SESION 2026-08-30) mostró que `interp816_runOpcode` = ~85% del coste por paso y que NO es el wrapper del bridge (quiescent-scan 12%, sync beam ~0%, fetch ~1%, ring ~10%). La vía de mayor impacto para 60 FPS = reducir el coste intrínseco del intérprete (mejora arranque + título + menú a la vez), no una pantalla aislada.

## PASO 1b HECHO (2026-08-30) — VFF guard $C2:0B82/0B87 en el campo: ~2x de FPS en campo, bit-exacto

**Descubrimiento**: el perfil por-PC exacto del JUEGO (muestreo 4096 buckets pc24 en interp816.c, env-gated) en el campo f9600+ mostró el wait de vblank **`$C2:0B87` (41.6%) + `$C2:0B8A` (33.2%) = ~75% del LLE del campo** corriendo interpretado. Era una SEGUNDA copia del spin `LDA $4212; BMI/BPL` (step 42, familia C8/CC/DB/6D/18) en 0B82-0B8B, que **no tenía guard** (solo 0B51/57 lo tenían, y esos son el wait de la intro, no el del campo). El `MainWindowTitle` confirmó el efecto: el PC-watch llegó a marcar 8.4fps con la instrumentación puesta; con este guard saltando el spin, el FPS de campo sube a ~14-16 (aun con el VFF_LOG de diagnóstico activo, que añade overhead de logging).

**Cambio (mínimo, phase-safe, validado)**: añadido `|| pc_before == 0xC20B82u || pc_before == 0xC20B87u` a la lista de guards VFF en `interp_bridge.c` (rama auto_quiescent), detecta variante LDA-abs (0xAD $4212, branch en pc+3, step 42). Misma categoría que los validados; el 0B82/87 del campo NO es frame-last (a diferencia del 0B51/57 de la intro que se descartó), así que es phase-safe igual que C8/CC/DB/6D/18.

**Validación completa (regla de oro):**
1. A/B cosim (10600 frames, boot+logo+titulo+intro+campo): **0 divergencias** (ab_diff.py sobre ab_a.bin[VFF ON] vs ab_b.bin[NO_VBLANK_FF]). Los state-outs pesan 2.09GB cada uno.
2. A/B a nivel-juego (el nexo): se añadió `SNESRECOMP_MC_LOG=1` a main.c (env-gated, vuelca `[mc] frame N master=...` tras RtlRunFrame) para comparar los master_cycles por frame reales con VFF ON vs `SNESRECOMP_NO_VBLANK_FF=1`. **13239 frames comunes: 0 divergencias en masters**; el tramo campo f9600-f13831 (3640 frames) idéntico. Esto prueba el guard NO cambia la fase del beam en el campo real (con audio), que es lo que el A/B cosim no puede probar (el cosim sin audio no alcanzó el guard — 0 fires — porque su estado diverge del juego). Se limpiaron los state-outs y logs temporales de Temp.
3. VFF_LOG confirmó que 0B82/0B87 disparan en el campo: fire f11590/f11591/f11592 pc=C20B87 con skip d=210798/211638/211932 master → ~211K master por fire, v=69/70 (vblank).
4. FPS medido en ventana (MainWindowTitle), campo en la casa de Ronx: **~14-16 FPS** con C3+guard 0B82 (comparado con ~10-11 con solo C3 y ~7-8 con el runtime previo). Mejora de ~2x sobre el runtime sin guard; el segundo ~2x del campo queda para el PASO 2.

**Estado**: 2.Beta/StarOcean.exe = af9e4f5e (build-beta 12:50 con el guard 0B82/87 + MC_LOG + muestreo por PC + fix PPU). 1.Release INTACTO (md5 3f026ac1). Instrumentación de diagnóstico (muestreo por PC, PPU split) toda env-gated; el juego no la compila salvo SNES_COSIM/profilers. Herramientas nuevas en build-cosim/: `ab_diff_detail.py` (diff de campo exacto por sección/registro, validado con byte mutado sintético), `so_coverage.py` (parser de cobertura [interp_profile] por banco). El guard queda integrado y validado.

**Lección**: el perfil del cosim (sin audio) NO representa el juego real — su estado de campo diverge (91 vs ~12.4K pasos/frame) y el guard nuevo no dispara ahí. La única validación fiable para un cambio de campo es A/B a nivel-juego con MC_LOG (masters por frame reales), exactamente lo que se hizo aquí. El siguiente objetivo (PASO 2) sigue siendo el render PPU del campo (23.7 ms en cosim; en el juego el draw era ~10-17ms vs emu 100-120ms, así que el intérprete sigue dominando el campo aun con el guard 0B82/87 — el siguiente es atacar el resto del LLE del campo o el driver AOT).

§ RESULTADO DE ESTA SESION (atribución del CAMPO, 2026-08-30 tras recibir la grabación nativa):
   Input-log nativo recibido (2.Beta/replay_casa_dialogos.txt, 139 eventos f92-f16516; valida: 57xA en cola post-pelea + Up largo final). Conversor revisitado: replay_to_inputs.py imprimía la máscara en DECIMAL pero el harness la parsea en HEX (%x) -> 0x100 salía 256/0x256; CORREGIDO y regenerado build-cosim/casa_inputs.txt. El harness NO carga savestates; medición = reproducir 10600 frames desde frio (tope eventos subido 64->256).
   ATRIBUCIÓN del campo (cosim, 10600 frames): bridgeq 39.7 ms/frame (LLE ~4.5K pasos), ppu 23.7 ms/frame (SoDrawPpuFrame), apu 4.3 ms/frame, sdd1/dma <0.5 ms. Total ~66 ms/frame en cosim (~15 FPS headless). El campo NO activa vIRQ en rango vblank (solo 4 writes IRQ_v=1, del boot) -> el fix IRQ/vblank de batallas NO se dispara en campo (gate correcto; descarta Test 1a como coste del campo).
   EXPERIMENTOS de atribución del coste LLE (toggles env, solos): quiescent-scan ~12% (0.9µs/paso); fast-fetch WRAM/ROM directo ~1%; sync_interp_to_cpu+cosim_insn ~0%; snes_sync_master_clock por instrucción ~0%; per-instruction ring (SNES_COSIM) ~10%. interp816_runOpcode = ~85% del coste por paso (~5.3µs/paso en cosim) -> el coste es INTRÍNSECO al core interpretador, no al wrapper del bridge. Ref (mismo core, APU síncrona): 9 frames en 0.9s vs bridge ~12s, PERO hace ~100x MENOS pasos (su APU responde al instante; el bridge espera el handshake SPC real del boot: 1.28M instrucciones LLE asíncronas → el arranque de 10s es ese poll, no un wrapper lento).
   VEREDICTO: en el campo, el cuello es (1) el coste del intérprete LLE al ejecutar el código real del campo (bancos C2/C8/CA, ~4.5K pasos/frame) y (2) el volcado PPU (23.7 ms). El scan/VFF/fetch NO son el problema. La vía fase-safe de mayor impacto = AOT por-función de las rutinas calientes del campo (patrón C3, que ya demostró ganar), NO optimizar el wrapper. Nota: la beta real no compila SNES_COSIM (sin ring/cosim_insn), así que su LLE es más rápido que el cosim mide; el ppu (23.7 ms) es coste real independiente de la instrumentación.

   FASE P0 (AOT del campo, 2026-08-30): perfil RESTRINGIDO al campo (f9600-f10600, run detached con INTERP_PROFILE_START=9600 sobre el input-log nativo, dump por pasos) — top calientes del campo:
     - $C2:FD1B-FD75 (blit/update de tiles del campo, ~28K pasos/PC x ~35 PCs ≈ 900 pasos/frame = ~20% del LLE) — la MÁS caliente.
     - $CA5B07 + $CA59D8-E4 (delay-loop por software TXA/CLC/ADC/TAX, ~320 pasos/frame) y $CA6D62-67 (scheduler, ~93/frame).
     - $C2:FE80-FEA3 (~25000/frame).
   VEREDICTO de viabilidad AOT: la rutina más caliente ($C2:FC-FE) NO es candidato limpio tipo C3: (a) hace escrituras de DMA habilitación `STA $420B` en FE2D y FE8C → riesgo de divergencia de fase (mismo tipo que tumbó el AOT del C2); (b) estructura entrelazada con tail-calls (`JMP $FC81`/`$FD80`) y una subrutina interna JSR $FDF0; (c) JSL indirectos (dispatcher $E8:0095, $20E2C8). El campo — a diferencia del título — NO tiene una 'estrella de cálculo puro' phase-safe: su trabajo caliente interactúa con el beam/DMA. NO se emitió AOT para el campo (avoidar cuelgue/divergencia). Vía real siguiente = el volcado PPU (23.7 ms, render, optimizable fase-safe) o el delay-loop $CA5B07 (puro, pero bajo impacto ~320 pasos/frame). Todo revertido/quedó limpio: 1.Release 3f026ac1 y 2.Beta 47a44e7a intactos, sin gateway en el código, temporales borrados.
   Todos los gates de diagnóstico fueron REVERTIDOS (código limpio); 1.Release 3f026ac1 y 2.Beta 47a44e7a intactos.

HERRAMIENTAS LISTAS (de hoy): build-cosim-release/so_cosim.exe = cosim Release con SNESRECOMP_INTERP_PROFILE (histograma PCs + contadores sdd1/dma/apu/apuw/apub/apus/ppu/bridgeq + frame_timing por frame con ms+steps). build-cosim/ab_c3.py = A/B ON/OFF. build-cosim/bench_c3.py. build-cosim/replay_to_inputs.py = convertir frame-hexmask a --input. Backup AOT completo en _backup_aot_full/ (2.Beta 47a44e7a + generated/ con c3). 2.Beta actual = C3 AOT integrado (md5 47a44e7a), 1.Release = 3f026ac1 (INTACTA).

MARCADOR DE DESYNC del replay: la escena de la madre de Ratix levantandolo (donde el usuario noto que "se fue todo a la porra") confirma que el replay de bsnes desincroniza del recorrido real por el driver de frames distinto, NO por un bug del emulador. Para A/B del campo hay que usar input-log grabado EN el recomp.

## TEST DE ATRIBUCION 34-vs-10 FPS EN CAMPO (2026-08-29, noche) — REENCUADRA EL PLAN

PREMISA: "recortar el AOT a 00/C0/C1 como 1.Release recupera los 34 FPS del campo". RESULTADO: FALSA.

DATOS DUROS (A/A de alcance AOT real, por vcxproj):
- 1.Release (build-release2): enlaza SOLO bank00/c0/c1 + dispatch + stubs -> campo 34 FPS (sin batallas).
- 2.Beta (build-beta, exe 47a44e7a): enlaza bank00/c0/c1/c3 + dispatch + stubs -> campo 10 FPS (con batallas).
- El STABLE scare de "13 bancos C2-C8/CA-CC" era FALSO: esos objs (del 27 ago) son HURRFANOS en build-beta (el vcxproj del 29 20:10 reconfig de glob generado solo lista 00/c0/c1/c3; no se enlazan). La 2.Beta actual NO ejecuta AOT amplio.

CONCLUSION: la brecha 34 vs 10 NO la explica el alcance AOT (delta real = solo C3, y C3 MEJORO el campo de 7->10). Recortar AOT a minimal devolveria a ~7-8 FPS (peor). No se monta beta recortada: iria contra los datos.

REENCUADRE: 1.Release va rapido PORQUE es el runtime del 27 ago que hace MENOS trabajo correcto (por eso las batallas no muestran imagen). 2.Beta anadio el fix IRQ/vblank/forced-blank + correctness que ES el coste por frame. Misma arquitectura y alcance AOT; la diferencia vive en el RUNTIME (fix IRQ batallas, FF/VFF guards, APU flush, render).
- PROXIMO EXPERIMENTO CORRECTO (dia siguiente): test controlado en 2.Beta que APAGUE el fix IRQ/vblank de batallas (comportamiento estilo 1.Release) y mida el campo headless. Si sube a ~34 -> ese fix es el coste, y se optimiza (solo forzar blank cuando haga falta / batching) en lugar de revertir (mantener batallas correctas). NO recortar AOT.
- Hecho esta noche: backup completo en _backup_aot_full/ (2.Beta exe 47a44e7a + generated/ con c3). 1.Release INTACTA (3f026ac1). generated/ y 2.Beta sin tocar.

## FASE 1 (2026-08-30 tarde) — Medir el coste por opcode del intérprete en el tramo menú/título: VEREDICTO = el switch NO es el cuello

**Nueva herramienta añadida:** `SNESRECOMP_INTERP_OPCODE_HIST=1` en interp816.c
mide host-ns DENTRO de `interp816_doOpcode` muestreando 1/64 (probe
env-gated, ~0 coste si no está; dump vía `interp816_opcode_hist_dump()`,
enganchada en src/main.c bajo SNESRECOMP_PHASE_MS y en cosim/harness_so.c).

**Datos duros (beta windowed, replay menú corto caminata_menu_principal, f700-f2700):**
- `emu=36ms/frame`, `draw=3.5ms`, ~25 FPS. El intérprete LLE domina el emu
  (~4568 insns/frame; PHASE_MS sampled ~68.5k por bloque de 120 = ~571/frame x8).
- PERO `doOpcode` (el switch) mide SOLO ~1ms/frame muestreado(1/64) ->
  **el switch NO es el cuello del menú.** Se desmiente la premisa "~85% en
  el switch" del diagnóstico previo.
- Hotspot dentro del switch cuando SÍ pesa (cinemática f6000-7900): las
  ESCRITURAS. STA abs/long/dp (8D/9F/85/64) cuestan 9-33us DE MEDIA frente
  a lecturas triviales (A5/B9/BD/D0 alt = 0.2-0.5us). Ratio 20-60x.
- Ruta de escritura por WRAM (cpu_write8, cpu_state.c:437) ejecuta 5-6x
  más bookkeeping que la lectura: cart_note_cpu_bus + open_bus + wlog_note +
  wlog_addr_note + hook stage-window + cpu_trace_wram_write_check (main + ring
  WRAM 1M) + reverse-debug. Pero la mayor parte está env-gated o es barata;
  el coste real lo domina el work MMIO/PPU de escribir registros
  (WriteReg->PPU) cuando la rutina blit/dma, no el shim.

**Conclusión metodológica (NO se integró nada):**
- El menú va a 25 FPS porque corre LLE (~4568 insns) y el coste está REPARTIDO
  en el bucle del bridge (overhead por opcode: sync interp<->cpu, poll-
  detection pre-opcode con 2-5 bridge_bus_read SIEMPRE aunque el poll está
  gateado por `yield_pc && !auto_quiescent`), NO en un caso concreto del switch.
- No hay un hotspot de switch único y fase-safe para optimizar: las escrituras
  caras son trabajo MMIO/PPU real (necesario), y reducir el overhead del bucle
  tocando el pre-opcode es arriesgado (puede romper la bit-exactitud del
  vblank/beam). Según la metodología (no integrar sin ganancia medida y sin
  divergencia), se NO integra ni en 2.Beta ni en 1.Release.
- Siguiente vía real para el tramo: (a) AOT por-función de las rutinas LLE
  calientes del menú (patrón C3 validado, elastic: el AOT correcto elimina el
  overhead del bucle por opcode sin tocarlo), o (b) Perfilado/Optimización del
  render PPU (draw=3.5ms del menú). La herramienta queda lista para usarla en
  (a).

## FASE A (2026-08-30 tarde) — AOT del menú por-función: abortado a tiempo (banco C2 NO delimitable a mano)

**Datos de perfil del menú (PHASE_MS, tramo f700-4271, 43 bloques):**
- Familia dominante: `$C2:FDxx` / `$C2:FExx` (blit tiles) = **40.5%**, seguida de
  C08 (21.5%, = handshake SPC del boot, inflada por wall-time lento ~8s/frame),
  CA6 (scheduler, 10%), C8F (6%), C38/C39 (star-field/ayuda).
- Top PCs exactos banco C2 del menú: `$C2:FC8C-FCBF` (~7.4k muestras, blit
  mapa) y `$C2:FD1E-FEA3` (~450/frame, blit tiles). Ninguno está emitido en
  generated/ (solo C0/C1/C3/00).

**Por qué NO se emitió AOT del C2 (decisión metodológica):**
- Desensamblado a mano de `$C2:FC70-FCC0` = es una **TABLA DE DATOS** (palabras
  0000/BE05/07B7/...), no código recto; los hot-PCs FC8C-FCBF son accesos a
  tabla desde otra rutina, NO una función con frontera delimitable a mano.
- Búsqueda en toda la ROM: **NO hay JSR/JSL directos a `$C2:FC8C`** (entra vía
  tabla/puntero). Delimitar la frontera por conjetura = exactamente el error
  que ya colgó el boot con el banco C2 (handshake SPC/waits NMI como AOT).
- `v2_regen --banks c2` activa autopromote sobre un banco con historial de
  cuelgue y toca el camino del boot. Riesgo de romper 2.Beta sin ganancia
  medida garantizable. **No se disparó.**
- **Fase-safety confirmada solo de forma parcial** por decoder propio; el único
  AOT del menú con precedente validado es el C3 (estrella), cuya emisión por
  función es el patrón correcto, pero requiere frontera exacta conocida desde
  el caller real (scheduler CA6), no adivinada.

**Vías seguras pendientes (para la siguiente sesión / otra IA):**
1. Delimitar el blit `$C2:FD1E`/`$C2:FC8C` por el caller real trazando desde
   scheduler CA6 (no por offset), y emitir SOLO ese tramo con v2_regen
   manteniendo el resto; validar A/B 3050 frames + tramo menú.
2. Alternativa más barata: el histograma (SNESRECOMP_INTERP_OPCODE_HIST) ya
   muestra que las ESCRITURAS (STA abs/long/dp) dominan el coste dentro del
   switch y cuestan 20-60x las lecturas; medir si el cuello es la ruta
   cpu_write8 con un parche de coste-fase-safe (no semántico).
3. Re-perfilar el render PPU (draw=3.5ms del menú) para Fase B.

**Estado:** 2.Beta intacta (fe00b0c6), 1.Release intacta (3f026ac1). Herramientas
nuevas: SNESRECOMP_INTERP_OPCODE_HIST (per-opcode host-ms, env-gated, dump vía
PHASE_MS y harness). No se recompiló nada nuevo en esta Fase A.

## EXPERIMENTO RUTA DE ESCRITURA (2026-08-30 noche) — fast-path WRAM: DIVERGE, REVERTIDO (lección: el coste de escritura es contabilidad de ciclos, no bookkeeping)

Plan propuesto (usuario): gatear hooks de debug en la ruta de escritura WRAM
(cpu_trace_wram_write_check, wlog, checks APU) para acelerar el menú. Se
implementó como fast-path env-gated en bridge_bus_write que saltaba TODO el
bookkeeping para escrituras en ventana WRAM canónica (cpu_wram_offset>=0).

**Resultado de la medición (beta windowed, menú f700-5100, mismo tramo A/B):**
- Baseline emu~36ms; fastpath emu~29ms -> **-7ms/frame (~20%)** aparente.
- PERO A/B cosim 700 frames: **DIVERGE desde f0** (hPos 0x0c01 vs 0x9400),
  225 frames CPU-reg diffs, 578 WRAM, 13 VRAM, 3 CGRAM.

**Causa raíz (fuente, interp_bridge.c:155-158 y 1483-1518):**
`bridge_timing_bus()` NO es bookkeeping: con `s_interp_bus_timing_active=1`
cada read/write acumula `s_interp_bus_master += region_speed(adr)` y al final
cada opcode ese master se suma a `master_cycles` (fase del beam). Saltarlo en
las escrituras WRAM desalinea el beam desde el arranque (hPos diff 1068).

**Conclusión:** la ganancia aparente del fastpath venía casi toda de saltar la
CONTABILIDAD DE CICLOS LLE (intocable sin romper bit-exactitud); lo que queda
ahorrable (g_interp_bridge_write_epoch++ + 2-3 checks APU + env-diag) es
~despreciable y ya está gateado (wlog por g_wlog_active, watch por
g_wram_watch_any=0). **El plan de gatear hooks NO es viable**; descartado con
números. Se revirtió el fastpath (fuente limpio, cosim+beta reconstruidos).
Los ~7ms medidos explican el 20-60x de escritura vs lectura del histograma:
las escrituras cargan region_speed por cada byte (timing real), no hay
overhead eliminable ahí. La única vía que elimina el coste de verdad es AOT
de la rutina (patrón C3) o aceptar el coste LLE.

## POLL-GATE DEL INTÉRPRETE (2026-08-30 noche) — VALIDADO E INTEGRADO en 2.Beta: −0.48ms/frame en menú, bit-exacto

**Cambio (interp_bridge.c):** la detección pre-opcode de polls cooperativos
(secondary poll / CMP-BEQ / joypad-wait) leía los bytes de instrucción
(pc_before, pc_before+3) con `bridge_bus_read` en CADA opcode interpretado.
Las tres comprobaciones que los consumen exigen `yield_pc && !auto_quiescent`,
que nunca se cumple en un run whole-program auto-quiescent (yield_pc=0xFFFFFFFE
via interp_bridge_run_until_quiescent): esas 2 lecturas ROM por opcode eran
overhead puro (y además bump-eaban el dynamic-read epoch S-DD1, que solo
alimenta el checkpoint de pacing SPC). Ahora las lecturas se hacen solo si
`yield_pc && !auto_quiescent` (modo yield dirigido, inalterado).
Opt-out de validación: `SNESRECOMP_NO_POLLGATE=1` restaura el comportamiento
antiguo (para A/B).

**Por qué es phase-safe (verificado en el fuente):** las lecturas ocurren
FUERA de la ventana `s_interp_bus_timing_active` (que solo se abre dentro de
interp816_runOpcode, líneas ~1467-1479), así que nunca acumularon
`s_interp_bus_master` → no tocan master_cycles ni la fase del beam (lección
aprendida del EXPERIMENTO RUTA DE ESCRITURA). Los epochs que sí bump-eaban
(continuous_read_epoch, dynamic_progress_epoch) solo alimentan heurísticas
consistentes entre iteraciones (qring captura antes de las lecturas; el
checkpoint 1528 sigue disparando por write_epoch en los handshakes SPC).

**Validación A/B (cosim, ab_pollgate.py):**
- 700 frames (boot+logos+título): **0 divergencias** (CPU/WRAM/VRAM/CGRAM 0).
- 3050 frames (boot+logos+título+menú): **records 3050, differing 0 — IDENTICAL**.

**Ganancia medida (beta windowed, caminata_menu_principal, bloques 10-43 del
mismo rango de frames, mismo exe con/sin NO_POLLGATE):**
- old (sin gate): emu medio 35.32ms · new (gate): 34.84ms → **−0.48ms (−1.4%)**,
  consistente en todos los bloques del menú de nombre.

**Estado:** integrado en 2.Beta (md5 `81a1ef66`, antes `fe00b0c6`). 1.Release
intacta (`3f026ac1`). Smoke test: replay corto → f1627, 24 FPS, cierre limpio.
Herramienta nueva: `build-cosim/ab_pollgate.py` (A/B env-gated).

**Lectura honesta:** es la única palanca fase-safe encontrada del overhead del
bucle LLE; es pequeña (−1.4% en el menú) pero gratis y validada. NO es el salto
a 60 FPS: el cuello sigue siendo el bucle LLE (el switch mide ~1ms/frame, el
resto de emu=35ms es el overhead del bucle: syncs + qring + contabilidad).
Siguiente candidato medido pendiente: el escaneo qring de detección de
quiescencia (hasta 64×18 compares por opcode en auto-quiescent) —
optimizable con pre-filtro de hash sin cambiar el resultado del match
(bit-exacto por construcción), pendiente de medir y A/B.

## AOT DEL BLIT DEL MENÚ $C2:FC43 — EMITIDO, DIVERGE POR CICLOS, REVERTIDO (2026-08-30 noche)

**Objetivo:** AOT por-función del blit de tiles del menú (40.5% del trabajo
interpretado del menú) con el patrón C3 validado.

**Hallazgos que desbloquearon la emisión (herramienta nueva SNESRECOMP_C2WATCH=1,
PC-watch env-gated en interp_bridge.c que loguea los bytes ejecutados + registros
MMC r4804-07 en el rango C2:FC40-FF00):**
1. **El entry real es $C2:FC43, NO FC70** (que es tabla de datos — por eso el
   intento previo de la Fase A decodificó basura). El watch capturó el flujo:
   FC43 prólogo (LDA #$08; STA $4300; LDA #$80; STA $4301 = setup DMA canal 0;
   STZ $29; REP #$20) → JSR $FEE5 (copia, RTS en $FEFE) → FC81-FCBF (volcado de
   mapa) → FD1E-FD7B (blit de coords) → JMP $FC81 (bucle por objeto).
2. **Mapeo MMC confirmado**: los selectores del runner `(addr24>>20)&3` y del
   emisor `(bank>>4)&3` son IDÉNTICOS (= bank>>4); banco C2 → ventana 0 →
   página 0 (r4804-07 en defaults 00 01 02 03). El runtime ejecutó en C2:FC43
   los bytes `A9 08 8F 00 43 00` que coinciden con el ROM en 0x02FC43 —
   emisor y runner usan el mismo mapeo (mi sospecha previa de divergencia de
   mapeo era un error aritmético mío: `addr24>>20 != (addr24>>16)&0xFF`).
3. **El codegen emite el setup DMA correctamente**: `cpu_write8(cpu,0x00,0x4300,...)`
   (MMIO con side-effects, patrón C3). El emisor aceptó `func BlitMenuTiles
   FC43 end:FF00 entry_mx:1,0` y auto-promovió 8 sub-rutinas (FDF0, FEE5, ...).

**Resultado A/B (ab_c2.py, so_cosim_prec2 vs so_cosim_c2, 3050 frames, marcada):**
**DIVERGED** — hPos diffs en 2725 frames (max 1342), vPos en 66 (max 13), CPU
reg en 360 frames, WRAM en 698. Primera divergencia en f308: **CPU idéntica,
pero hPos difiere 24 ciclos (AOT por detrás)** y 1 byte WRAM (0x04160: BF vs 00)
como consecuencia (flag del juego dependiente del beam).

**Diagnóstico:** desajuste de CONTABILIDAD DE CICLOS del AOT vs LLE (el AOT
sub-carga ~24 master cycles por invocación del blit). No es corrupción de
estado (CPU idéntica en f308). Candidatos (no aislados): (a) las escrituras
MMIO $4300/$4301 — el LLE cobra `cpu_pace_cycles` + WriteReg que el bloque AOT
(`cycles += N * (g_memsel?6:8)`) no cubre; (b) el frame empujado del JSR
(retorno site+2 vs site+3 real). Nota: TODOS los JSR del C3 también empujan
site+2 y el C3 validó — el frame empujado es solo fallback LLE, red herring
para el retorno AOT-a-AOT.

**Decisión (metodología):** REVERTIDO limpio — generated/ restaurado (sin
bankc2_v2.c, dispatch del backup), cosim y beta reconstruidos, 2.Beta sigue en
`81a1ef66` (poll-gate validado), 1.Release `3f026ac1` intacta. Liberados ~1.4GB
de bins A/B viejos.

**Vía siguiente (si se retoma):** aislar la instrucción exacta del desajuste de
ciclos con un A/B instrumentado (comparar master_cycles por instrucción del
blit LLE vs AOT — el AOTF de la estrella ya dejó el patrón de diagnóstico), y
decidir si es arreglable en el modelo de ciclos del emisor (riesgo medio) o si
el blit C2 se queda en LLE. La herramienta C2WATCH queda disponible (env-gated,
0 coste apagada) para cualquier trabajo futuro del banco C2.

## CAUSA RAÍZ DEL DESAJUSTE DE CICLOS AOT, PROBADA AL CICLO + DESCUBRIMIENTO: EL AOT C3 ES CÓDIGO MUERTO (2026-08-31 madrugada)

Retomando la vía de arriba con el A/B instrumentado: **la causa raíz quedó
aislada y probada al ciclo exacto**, y de paso se descubrió que el AOT de la
estrella (C3) **nunca se ejecuta** — su "A/B 3050 IDENTICAL" de la FASE 1 fue
VACUO. Instrumentación nueva: `SNESRECOMP_CYC_WATCH=lo-hi` (interp_bridge.c,
env-gated, 0 coste apagada) loguea por instrucción interpretada
`[cyc] f= pc op cyc bus_xfers bus_master internal master_delta`.

**1) EL MODELO LLE ES POR-TRANSFERENCIA; EL EMISOR COBRA PLANO POR BLOQUE.
   Déficit exacto = Σ(region_speed − S) por transferencia de datos.**
- LLE (interp_bridge): master por instrucción = `Σ region_speed(transferencia) +
  internal×6`, con region_speed: ROM fast=6 / WRAM=8 / XSlow $4000-41FF=12 /
  internal=6. Verificado al ciclo: RTL = 6(fetch)+24(3 pops WRAM a 8)+12(2
  internal) = 42 ✓.
- AOT (emitter): el bloque cobra UN solo rate `cpu->cycles += C; cpu->master_cycles
  += C×(g_memsel?6:8)`. Los accessors cpu_read8/write8 NO pacean master_cycles
  (cpu_pace_cycles solo incrementa un contador de diagnóstico) → el cargo plano
  es el ÚNICO avance de master del AOT.
- Déficit por instrucción = Σ_transfers(region_speed − S). Para bloques fast-ROM
  (S=6): exactamente **2 master por transferencia WRAM/stack** (8−6). Verificado
  en los 273 bloques del blit C2 (deficit = 2×#WRAM-transfers, 0 impares, 0
  negativos) y en el C3 (ops DP 85/A5/A6/66: −4/exec = 2 bytes WRAM × 2).
- Caso concreto L_FC43 (f308, primera divergencia): LLE=162 vs AOT=156 → déficit
  6 = STZ $29 (1 write WRAM, +2) + JSR (2 pushes stack, +4). Total del blit
  sobre f308-339: −125,398 master. Herramientas: build-cosim/cyc_compare.py,
  cyc_validate.py, cyc_summary.py (análisis del log CYC_WATCH vs cargos AOT).

**2) EL AOT C3 (estrella del título) NUNCA DISPARA — SU VALIDACIÓN FUE VACUA.**
- El bridge solo entra en AOT por JSR/JSL (paired-call bounce) o stop-PC
  (intercept solo en modo task-resume; el main loop no pasa stop_pcs).
  "JMP arrivals are never bounced" (comentario del propio bridge).
- La ROM tiene **CERO JSR/JSL a $C3:8F50**; la única referencia es un
  `JMP $8F50` (4C 50 8F) en ROM 0x332223 = CPU **$C3:2223**, un wrapper
  tail-call (los bytes siguientes 0x332226 son tabla de datos, no código).
- Consecuencia: en cosim Y en 2.Beta la estrella corre 100% LLE interpretada;
  el A/B C3 (clean vs c3_on, 3050 IDENTICAL) comparó dos runs que NUNCA
  ejecutaron el cuerpo AOT → no validó nada. La ganancia de FPS del C3 nunca
  existió (por eso nunca se midió). El CYC_WATCH lo confirma: el rango
  $C3:8F50+ aparece ejecutado por el intérprete.
- **La vía de desbloqueo del título:** $C3:2223 es JSR'd desde $C3:AA3A (ROM
  0x33aa3a, dentro del banco). Si $C3:2223 se añade a la dispatch table y el
  emisor encadena el `JMP $8F50` como goto al cuerpo StarField ya emitido, la
  cadena completa correría AOT (JSR→2223→goto→8F50→RTS). Requiere PRIMERO el
  fix de ciclos (si no, divergiría igual que el C2).

**3) PRÓXIMO PASO (recomendado, en orden):** (a) arreglar el modelo de cargos
   del emisor (emit_function.py): descomponer el cargo de bloque en
   `master += Σfetch×S_expr + Σinternal×6` y pacear cada acceso de datos con
   region_speed en runtime (accessors paced, solo en el AOT; el LLE sigue por
   su propio contador → sin doble cobro); (b) re-emitir SOLO el C2 con el
   modelo nuevo (bancos restantes byte-idénticos por digest) y A/B 3050 frames
   → si IDENTICAL, medir FPS del menú e integrar en 2.Beta; (c) extender al
   C3 vía entry $C3:2223 para atacar el título. 1.Release (3f026ac1) y 2.Beta
   (81a1ef66) siguen intactas; generated/ limpio (C2 revertido).

Nota de higiene: se eliminó una referencia rota `g_interp_total_steps` en
cosim/harness_so.c (bloque dev SNESRECOMP_FRAME_TIMING que nunca compiló).

## SESION 2026-08-30 (manana) — PASO 1 ATRIBUCION: campo bloqueado, boot atribuido, delay-loop descubierto

METODOLOGIA cumplida: solo medidas sobre so_cosim Release instrumentado (build-cosim-release/so_cosim.exe, SNESRECOMP_INTERP_PROFILE + SNESRECOMP_FRAME_TIMING), sin tocar 1.Release (md5 3f026ac1 intacto) ni 2.Beta (47a44e7a intacto).

1) ARRANQUE LENTO ATRIBUIDO (nuevo, corrige la narrativa previa): el boot de ~8s es UN SOLO FRAME (f3 = 8.44s host). Desglose f3 (diferencia de contadores runs --frames 3 vs 4):
   - bridgeq (interp_bridge_run_until_quiescent, trabajo CPU AOT del frame): +8.77s  <- DOMINANTE
   - apu flush (bridge_apu_flush): +0.44s; apus (rtl_sync_apu_to_cpu_locked, polls $2140): +0.12s; dma: +0.10s; sdd1: +0.001s; ppu: +0.003s.
   - 0 pasos de interprete (0 LLE): f3 corre TODO en AOT. NO es SPC upload (apu=0.44s), NO es S-DD1 (0.001s). Es ejecucion AOT de una rutina de boot (candidato: handshake/descompresion inline en bankC0 AOT). Necesita perfil AOT por-funcion para localizar la rutina exacta (la instrumentacion actual solo mide interp PCs).
2) TEST 1a (toggle fix IRQ/vblank) — NO EJECUTABLE en campo: el fix de so_rtl.c solo se dispara con vIrqEnabled && vTimer en [225,261] (ciclo 216<->258 de batalla). El campo/titulo no lo toca; el toggle daria NULL por construccion. El plan lo tenia como primer test; queda re-encuadrado abajo.
3) CAMPO — MEDICION BLOQUEADA (razones concretas, verificadas hoy):
   (a) El replay de bsnes desincroniza del recorrido real: ejecutando el cosim hasta f12200 con field_inputs.txt, el juego queda ATASCADO desde ~f9000 en un DELAY-LOOP por software en $CA:5B07 (patron TXA/CLC/ADC #imm/BPL/TAX/SEP #20/PLA/DEC A/BNE -0x1E = contador desde la pila; NO lee $4212 -> NO cubierto por el VFF). resume=$CA5B07 durante miles de frames -> no llega al campo real. (El usuario confirma: campo = fin de cinematica ~f10500 en SU partida; en el replay desync no se alcanza.)
   (b) Llegar al campo por simulacion completa cuesta ~11+ min por run en cosim (timeout de la herramienta = 600s; el run f12200 no termino). Imposible hacer A/B de varios toggles asi.
   (c) Savestate/loadstate: el usuario advierte que corrompe la musica (chasquido al empezar melodias). Para medidas de host-time CPU/PPU es tolerable, pero para A/B de estado NO es oracle fiable.
   CONCLUSION: para medir el campo hace falta (opcion 1) input-log NATIVO grabado en el recomp (PASO 3 del plan; bloqueado por 7-10fps jugables) o (opcion 2) savestate L3SN tomado en 2.Beta en el campo (via debug server save_state) + soporte --state-in en el harness cosim (pendiente de implementar; reutiliza RtlSaveLoad del runner).
4) HALLAZGO NUEVO — delay-loops por software: el bucle $CA:5B07 (y similares) es un patron de espera basado en contador (sin $4212). Si el campo real pasa tiempo en delay-loops asi, el VFF actual no los cubre y serian un coste LLE puro. Hipotesis a verificar con datos de campo real; un fast-forward de delay-loop seria phase-sensitive (igual riesgo que C2:0B51) -> validar A/B antes.
5) FIX DE HERRAMIENTA (dev-only, cosim/harness_so.c): tope de eventos --input subido de 64 a 256 (field_inputs.txt tiene 159; con 64 el parseo fallaba a partir del evento 65). Recompilado build-cosim-release (solo cosim; 2.Beta/1.Release no se tocan).
6) TASA COSIM medida: ~23.6 fps flat-out hasta f2000 (boot); frames post-boot 6-60ms; el run f12200 NO cabe en el timeout de 600s de la herramienta. Para runs largos: dividir o usar savestate.

ESTADO FINAL: 1.Release 3f026ac1 y 2.Beta 47a44e7a INTACTOS. generated/ sin tocar. Instrumentacion cosim solo (build-cosim-release). Siguiente paso del plan (a decidir con el usuario): obtener datos reales del campo — input-log nativo o savestate beta en campo + --state-in en cosim.

## ATRIBUCION DEL FRAME 3 DEL BOOT (2026-08-30) — EL ARRANQUE DE ~8s ES CPU LLE PURA

Solo diagnostico (sin tocar 1.Release ni 2.Beta; md5 intactos). Herramienta: so_cosim Release instrumentado (build-cosim-release) + 3 instrumentos NUEVOS (todo cosim-only, macro SNESRECOMP_INTERP_PROFILE, cero coste en 2.Beta/1.Release):
   (a) aotprof (common_cpu_infra.c, env SNESRECOMP_AOT_PROF): atribuye host-time por FUNCION AOT via hooks RecompStackPush/Pop.
   (b) muestreador por PC del interp (interp_bridge.c, env SNESRECOMP_INTERP_MS_PROF): cada 256 pasos atribuye host-time al PC actual.
   (c) rate log (env SNESRECOMP_INTERP_RATE_LOG): cada 8192 pasos imprime paso/pc/master/ms -> ns por paso.
   (d) FIX de contador: g_interp_total_steps ahora cuenta TODOS los opcodes (antes solo el bail por step-cap -> infravaloraba el boot como '0 pasos').

NUMEROS (run de 9 frames, dominado por frame 3):
- frame 3 (s_frames 3): host 8.4-9.5s; master delta = 23,571,900 (~66 frames de juego en UN frame = espera larga del boot); PASOS LLE = 1,284,953. NO es AOT: el contador viejo (0 pasos) estaba roto.
- Desglose por PC (host-time, muestreador cada 256 pasos):
    $C084FB/FC  DEY;BNE delay-loop (65,536 iteraciones fijas)  4,520 ms  (44.6%)
    $00F703     wait NMI banco 00 (región F6DD-F6FE)           2,894 ms  (28.6%, operación gigante atribuida ahí)
    $C08881     BPL -4 flag-wait                               2,066 ms  (20.4%)
    $C8F425/28  main loop (spin ya FF)                           561 ms  ( 5.5%)
- Tasa por paso (rate log): codigo normal 0.4-0.6 us/paso; DEY loop estable 6.1-7.0 us/paso; PRIMER bloque del DEY 351 us/paso (2.877s / 8192 pasos); bloque $00FEBD (vector IRQ) 714 us/paso (5.857s / 8192 pasos, master casi congelado).
- Control de instrumentacion: perfil OFF 10.24s vs ON 10.17s -> la instrumentacion NO es el coste; los us/paso son reales del wrapper del bridge.
- Referencia decisiva: so_cosim_ref (mismo core interp816, sin wrapper de bridge) hace los mismos 9 frames en 0.87s vs ~10.2s del bridge = 11.7x MÁS LENTO el camino del bridge.
- Contadores por componente en f3 (todos despreciables): APU flush 0.44s; SPC (apu_cycle, nuevo contador apucyc) 0.20s; DMA 0.10s; S-DD1 0.001s; avance de beam O(scanlines) microsegundos.

DEDUCCION: el arranque de ~8s es CPU LLE pura en los loops de espera del boot (delay-loop DEY $C084FB/FC, spins BPL $C08881, wait NMI/IRQ $00FEBD) ejecutados por el intérprete del bridge con overhead de 6-700 us/paso en los tramos lentos (vs 0.4-0.6 us/paso del codigo normal). NO es subida SPC (0.2s), NO es S-DD1 (0.001s), NO es DMA (0.1s), NO es AOT. El wrapper per-opcode del bridge (quiescent-scan 64x20, fetch bridge_bus_read multiples, checks VFF/polls) es el coste dominante.

VIAS FUTURAS (NO implementadas; solo diagnóstico, requieren A/B 3050 frames + capturas antes de tocar 2.Beta):
  1. AOT de las rutinas delay-loop/spin del boot ($C084FB/FC, $C08881) — fase-sensitive (adelantan master), mismo riesgo que C2:0B51; validar A/B antes.
  2. Reducir el overhead per-paso del wrapper interp (quiescent scan, fetches repetidos) — aceleraria TODAS las zonas LLE (titulo, intro, texto, campo), no solo el boot.
  3. Perfil fino del bloque $00FEBD/IRQ (714 us/paso) — candidato a optimizacion puntual del camino IRQ.
  4. El frame 3 avanza 66 frames de juego en un frame: evaluar si ese wait puede trocearse/adelantarse sin romper fase (igual que VFF pero para wait sin $4212).

Evidencia guardada: build-cosim-release/pctime9.log (per-PC ms) y rate9.log (ns/paso). Instrumentacion nueva queda en el build cosim (dev-only); 2.Beta/1.Release no la compilan.

**REFERENCIA CAMPO (2026-08-30, grabacion nativa en curso 2.Beta/replay_casa_dialogos.txt):** el usuario confirma que ~f9600 el rendimiento baja a 10fps = inicio del campo (fin de cinematica). Cuando la grabacion termine (avisara), convertir con replay_to_inputs.py, reproducir en so_cosim hasta f9600+ y aplicar rate-log + muestreador por PC + contadores (bridgeq/ppu/apucyc/apus) para atribuir el coste del campo. Logo Star Ocean (bajon) ~f2000-2100 en la intro como referencia secundaria.

## SESION 2026-08-31 (madrugada) — FIX DEL MODELO DE CARGOS DEL EMISOR (C2): ESTADO PARA MAÑANA

Objetivo del encargo: corregir el modelo de cargos del emisor (opción (a) de la
sección anterior) y cerrar el A/B del C2. **ESTADO: implementado y validado en
f308-339 (el blit C2 ya es exacto al ciclo), pero el A/B completo 3050 frames
sigue DIVERGIENDO en f778 con un residual puro de −2 master (hPos 188 vs 190,
todo lo demás idéntico) cuya causa NO está cerrada.** No integrar todavía.

**Cambios en disco (todos en el emisor + runtime AOT; 1.Release 3f026ac1 y
2.Beta 81a1ef66 INTACTAS, no reconstruidas):**
1. `snesrecomp-tool/recompiler/snes_cycles.py`: nuevo `_WRITE_INDEXED_OPS`
   {0x91,0x99,0x9D,0x9E,0x1E,0x3E,0x5E,0x7E,0xDE,0xFE} (stores+RMW en
   abs,X/abs,Y/(dp),Y). `xwrite_add()` = +1 estático cuando x=0 (el LLE cobra
   `!xf || page-cross` en escrituras; con índice de 16 bits es incondicional).
   `xcross_add()` REESCRITO: ahora devuelve 1 SOLO para write-indexed (el
   page-cross runtime con x=1); las LECTURAS ya no cobran page-cross (el LLE
   `interp816_adrAbx/adrAby(write=false)` NUNCA lo cobra — verificado contra la
   tabla `cyclesPerOpcode` y el log CYC_WATCH).
2. `snesrecomp-tool/recompiler/v2/emit_function.py`: `_dynamic_charge_lines`
   emite el page-cross solo para write-indexed con x_flag==1; con x=0 va
   plegado al const del bloque. Comentarios actualizados.
3. `snesrecomp/runner/src/snes/snes_cycles.h` regenerado (misma autoridad;
   nadie lo incluye — solo referencia).
4. Lado C (sesión previa, ya validado): `cpu_state.c/h` accessors paced
   `cpu_read8/16_paced`, `cpu_write8/16_paced` (pacean master_cycles con
   `cpu_region_speed`) + `SNESRECOMP_PACELOG` (env-gated); `interp_bridge.c`
   delega en `cpu_region_speed`; `cpu_trace.c` log `[aotblk]` (compilado fuera,
   `SNESRECOMP_TRACE=0`).

**Verificación con números:**
- Modelo contra el LLE: STA abs,Y m0x0 = 7 ✓ (5 base + 1 m0 + 1 indexed);
  m1x0 = 6 ✓; LDA abs,X m0x0 = 5 sin page-cross ✓; INC abs,X m1x0 = 8 ✓;
  epílogo FEE5: const 15 ciclos → master = (15−4)×6 + 5×(S−6) = 66 + paced 32
  = 98 = LLE exacto (antes 92, el −6 de la divergencia).
- A/B 3050 (OFF so_cosim_off_new 22:07 vs ON so_cosim_on_new2 23:24):
  ANTES: divergía f311 (hPos −6, luego CPU/WRAM). AHORA: f308-777 LIMPIOS
  (hPos idéntico frame a frame, scan de TODOS los campos), primera diferencia
  = f778 hPos 188 vs 190 (−2 master), todo lo demás ok, y en f786 ya cascada
  completa (CPU/WRAM).
- El C2 AOT NO se ejecuta en f778: CYC_WATCH (OFF) no muestra ninguna
  instrucción $C2 en f778; PACELOG (ON) solo muestra accesos paced en
  f308-338. Los streams [CPU_W] de ON y OFF son idénticos (18 líneas).
  CONCLUSIÓN PARCIAL: el −2 de f778 NO es un disparo AOT directo en ese
  frame; es un efecto diferido de la ejecución AOT de f308-339 (offset de
  master absorbido por el yield-en-quiescencia en los límites de frame y que
  aflora cuando el punto de quiescencia coincide con un evento sensible al
  beam ~f778) — hipótesis a CONFIRMAR.

**Causa exacta del −6 que ya se cerró** (documentar para no repetir): el
epílogo del FEE5 sub-cobraba STA abs,Y m0 (6 vs 7 ciclos del LLE) = −6 master;
el bucle lo enmascaraba porque la LDA abs,X con X≥0x100 sobre-cobraba +6
(page-cross de lectura que el LLE no cobra). Ambos corregidos.

**Artifacts y backups:** generated/bankc2_v2.c = modelo NUEVO (restaurado);
build-cosim/backup_bankc2_oldmodel.c (modelo viejo, 252455 B) y
backup_bankc2_newmodel.c (nuevo, 246831 B); exes: so_cosim_off_new.exe (OFF,
22:07 — POSIBLEMENTE STALE: cpu_state.c sin pacelog), so_cosim_on_new2.exe
(ON modelo nuevo, 23:24), so_cosim_on_oldmodel2.exe (ON modelo viejo, 23:43).
Scripts: build-cosim/ab_c2_new2.py (A/B 3050), ab_on_old_vs_new.py,
hpos_scan.py, full_scan.py, run_cycw_f778.py, run_pace_f778.py.
Build: build-cosim/_tmp_build_cosim.bat (vcvars 2022 + ninja).

**Próximo paso para cerrar el C2 (orden):**
1. Descartar el exe OFF stale: reconstruir OFF fresco (generated/ sin
   bankc2_v2.c + dispatch sin entradas C2 — el dispatch actual referencia
   símbolos bank_C2_*, hay que filtrarlo) y repetir el A/B. Si f778 desaparece
   → el C2 está CORREGIDO y el problema era el OFF viejo.
2. Si f778 persiste: instrumentar el punto de quiescencia de f778 (el frame
   driver decide el fin de frame; verificar si el −2 viene de que el AOT de
   f308-339 deja `apuCatchupCycles`/beam con un residuo que solo aflora en
   f778). Comparar master_cycles TOTAL del run (no solo hPos) — el registro
   de state-out NO guarda master; añadir un campo o log per-frame.
3. Cuando el A/B 3050 sea IDENTICAL: medir FPS del menú ON vs OFF, e integrar
   en 2.Beta SOLO si hay ganancia demostrada y 0 divergencias. No ampliar a
   otros bancos ni al C3 hasta que C2 cierre.

## PLAN SAVESTATE/LOADSTATE 100% FUNCIONAL (2026-08-31, PARA CUANDO SE CIERREN LOS FPS)

**Motivación:** las simulaciones de 16K frames (~11 min por run en cosim) no
son viables para iterar. Necesitamos cargar partida rápido (savestate) para
saltar al campo/batalla en segundos, con la MISMA metodología contrastada:
bit-exacto, 0 divergencias, y SIN romper nada (la música se rompía antes con
chasquidos al empezar melodías).

**Infraestructura existente (verificada hoy en el código):**
- `RtlSaveSnapshot/RtlLoadSnapshot` (common_rtl.c:567/591): cabecera
  MAGIC+VERSION (RTL_SAV_VERSION, hoy v7), `RtlApuLock()` alrededor del
  volcado, `snes_saveload(g_snes, sli)` serializa cpu+apu+dma+ppu+cart+
  tail(Snes: hPos..apuCatchupCycles)+WRAM+ramAdr+joypad.
- Hooks por juego: `state_save_extra`/`state_load_extra` (chunk v5+, hoy NULL
  en src/so_cpu_infra.c) y `on_state_loaded` (reconciliación post-load del
  estado host: fibras, scheduler HLE — hoy NULL).
- Entradas: teclas F5/F8 en main.c (kSaveLoad), debug server `save_state
  <file>` / `load_state <file>` (debug_server.c:3828/3937) con `state_file.c`.
- Cosim: `--state-out` YA existe (se usa en el A/B); falta `--state-in` para
  arrancar desde un snapshot (parcialmente cubierto por RtlLoadSnapshot).

**CAUSA RAÍZ PROBABLE del chasquido de música (a confirmar con A/B, no asumir):**
1. El APU/SPC se serializa con `apu_saveload`, pero el AUDIO en el host corre
   en un hilo aparte (`RtlRenderAudio` cicla el SPC en bulk, ~17k ciclos por
   callback). Si el snapshot no incluye la posición del anillo de audio host
   (buffers ya mezclados / samples pendientes), tras el load el hilo de audio
   reanuda desde un punto arbitrario → gap/click. Verificar si el snapshot
   guarda el estado del anillo y el `apuCatchupCycles` fraccionario.
2. Los hooks por juego (task-slot/resume contexts del motor de Star Ocean)
   están NULL: si el motor del juego guarda punteros/task-slots en RAM y el
   recomp tiene contexto host asociado, falta la reconstrucción.
3. `g_snes->beamMasterLast = g_cpu.master_cycles` tras el load es la ÚNICA
   reconciliación de beam; verificar si la fase del frame (hPos/vPos/IRQ
   pendientes) queda consistente con la del momento del save (el snapshot
   guarda hPos/vPos del tail — bien).

**PLAN (metodología contrastada, nada se aprueba sin A/B):**
1. **Diagnóstico controlado del chasquido (PRIMERO, sin tocar código):**
   reproducir en 2.Beta: arrancar → llegar a música → save → load → escuchar.
   Instrumentar con `AUDIO_TRACE` (audio_trace_set_producer existe) para
   capturar el stream APU antes/después del load y comparar byte a byte dónde
   se corta/desfasa el audio. Localizar el subsistema (anillo host vs SPC vs
   catchup) con números.
2. **Completitud del snapshot:** auditar `apu_saveload` (¿SPC700 completo:
   registros, RAM 64KB, DSP 128 regs, timers, puertos $2140-43?) y el anillo
   de audio host; añadir lo que falte con versionado (subir RTL_SAV_VERSION
   con layout nuevo + compat de lectura de viejos, como ya hace snes_saveload
   con ≤5/≥7).
3. **Alineación de frame:** garantizar que save/load SOLO ocurre en límite de
   frame (quiescencia), nunca a mitad de DMA/IRQ/catchup APU. El debug server
   ya lo hace "from the main thread" — verificar y documentar la garantía.
4. **Hooks por juego:** i
`state_save_extra`/`state_load_extra`/`on_state_loaded` para Star Ocean si el diagnóstico muestra que el motor
necesita reconstruir contexto host (task-slots del scheduler, etc.).
5. **A/B de validación del savestate:** con el cosim: (a) correr N frames
   recto → snapshot en M → load → correr hasta N; (b) comparar los dos runs
   frame a frame con ab_diff: TODOS los campos (cpu/dev/ppu/wram/vram/cgram)
   deben ser IDENTICAL desde M hasta N (0 divergencias). (c) repetir con el
   snapshot tomado en puntos distintos (boot, título, campo, batalla,
   transición de batalla). Esto exige `--state-in` en el harness.
6. **A/B de audio:** comparar el stream APU capturado (AUDIO_TRACE) en el run
   recto vs el run con save/load: muestras idénticas (o, si el audio no es
   determinista por diseño del hilo, acotar el artefacto a <un buffer y
   documentarlo). El chasquido = divergencia del stream.
7. **Integración:** `--state-in <file>` en cosim para saltar directo al campo
   (el A/B de campo deja de costar 11 min), y atajo de teclado/CLI en 2.Beta
   para save/load rápido. NO tocar 1.Release; todo en 2.Beta/cosim.
8. **Validación final:** con el savestate en el campo + el input-log nativo,
   re-ejecutar la batería A/B de FPS/campo; confirmar que la música suena
   limpia (escucha del usuario) y que los combates funcionan tras cargar.

**Referencias:** bsnes-plus usa savestates L3SN (cabecera 16B + estado
hardware completo); el HANDOFF menciona "savestate L3SN tomado en 2.Beta".
NO es necesario importar el formato de bsnes — la infraestructura RtlSaveLoad
ya cubre el estado del guest; el trabajo es completitud + hooks + validación
A/B. En su momento se decidió NO usar savestates como oracle del cosim
porque corrompían la música (§ SESIÓN 2026-08-30 mañana, punto 3c) — ESE es
exactamente el bug que este plan cierra.

## SESION 2026-08-31 (mañana) — CIERRE DEL C2 + FIX getenv EN HOT PATH: 2.9x en el intérprete, VALIDADO

**Veredicto C2 (cerrado, revertido):** reconstruí OFF y ON frescos desde los
mismos fuentes (descartando el OFF stale sospechoso) y el A/B 3050 sigue
DIVERGED en f778 (hPos −2, cascada real a CPU/WRAM en f786). PACELOG
confirma: el AOT C2 SOLO dispara en f308-338 (logos del boot), 0 accesos en
f770-800 — es el efecto diferido de fase que predijo el HANDOFF, NO un cargo
mal contado (el modelo de cargos quedó corregido: el −6 del epílogo FEE5
desapareció). DECISIÓN: el C2 no es bit-exacto y solo toca los logos (no el
título/menú-nombre que queremos), así que se REVIRTIÓ la emisión
(generated/ = estado pre-C2 restaurado desde build-cosim/backup_gen_pre_c2:
C3/StarField intacto, sin bankc2_v2.c, dispatch sin entradas C2). Los fixes
del modelo de cargos en snes_cycles.py/emit_function.py se conservan
(inofensivos, correctos). La 2.Beta ANTIGUA (81a1ef66) ya no llevaba C2.

**HALLAZGO + FIX: getenv() en el hot path del intérprete (CAUSA del 52% del
host-time en el tramo objetivo).** Con SNESRECOMP_INTERP_OPCODE_HIST sobre
2600 frames (boot→título→menú-nombre, so_cosim_reverted):
- ANTES: totalhost_ns=223.4ms; op=9F (STA abs.long) 11000ns/op (29.9%), la
  familia de stores (85/8D/95/9D/9F) ~52% del host-time. Asimetría 10x
  STA vs LDA (1.9µs) con el MISMO modo de direccionamiento.
- CAUSA: interp816_runOpcode llamaba getenv("SNESRECOMP_PHASE_MS") en CADA
  instrucción y bridge_bus_write getenv("SNESRECOMP_APU_PORT_DIAG") en CADA
  escritura (bridge_bus_read no tenía ninguno) → getenv() de MSVC recorre
  el bloque de entorno completo (~µs). Host-time PURO, 0 ciclos guest.
- FIX (2 sitios, patrón static lazy-init ya usado en el repo): cachear el
  env en static int. Bit-idéntico por construcción.
- DESPUÉS: totalhost_ns=77.6ms (**2.9x**); op=9F 11000→1059ns/op; stores
  ~52%→~21%. A/B 3050 frames pre-vs-post-fix (mismo generated): **IDENTICAL,
  0 divergencias** (ab_gef_pre/post.bin, ab_diff.py).

**Integrado en 2.Beta y medido en vivo:** 2.Beta/StarOcean.exe reconstruida
(md5 6402619e, build-beta+copy, 1.Release 3f026ac1 INTACTA). Con el replay
caminata_larga_combates.txt: f3719 (intro) = **55 FPS** (antes 20-38),
f14795 (campo) = **60 FPS** (antes 10-16 con guard 0B82/87), f17946 (batalla)
= 40 FPS. El tramo objetivo arranque→título→menú-nombre ya va fluido.

**Estado del exe y generated:** 2.Beta=6402619e (fix getenv, sin C2),
1.Release=3f026ac1, generated/ = pre-C2 (7 archivos, sin bankc2),
build-cosim/so_cosim_reverted.exe (pre-C2 sin fix), so_cosim_getenvfix.exe
(pre-C2 con fix, exe de referencia del A/B). Scripts nuevos:
build-cosim/{patch_phase_ms.py, patch_apu_diag.py, ab_getenvfix.py,
strip_c2_dispatch.py, restore_on_dispatch.py, build_off_manual.bat,
build_on_fresh.bat, build_cosim_revert.bat, build_getenvfix.bat,
build_beta_getenvfix.bat}.

**PRÓXIMO PASO (tramo objetivo a 60 FPS constantes):** tras el fix getenv, el
intérprete bajó 2.9x pero quedan otros getenv en caminos calientes
(bridge entry wlog_state_sync en interp_bridge.c:835, per-bridge-entry — aún
no cacheado), y los cuellos restantes del histograma (op=8D STA abs 9781ns,
op=8E STX abs 6721ns — ver si son writes HW/APU con sync). Medir el nuevo
top del intérprete con OPCODE_HIST tras el fix (ya hecho: A5 14.4%, 8D 9.3%,
9F 8.3%, B9 8.2%) y atacar el siguiente con la misma metodología (medir →
cambiar mínimo bit-exacto → A/B → medir). Después, savestate (plan §PLAN
SAVESTATE abajo).
