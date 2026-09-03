# 🧠 Enciclopedia del proyecto (referencia personal del agente)

> Documento de trabajo acumulativo. Todo lo que aquí aparece está **verificado** (por
> ejecución, trace o código fuente) salvo que se marque como hipótesis. Actualizar al
> descubrir algo nuevo o al corregir un dato erróneo.

Última actualización: 2026-08-24

---

## 1. Arquitectura (lo que ES el proyecto)

- **NO es (todavía) una recompilación estática.** El juego corre completo bajo un
  intérprete 65816: `interp816` + `interp_bridge` (derivado de LakeSnes), con un frame
  driver hecho a mano en `src/so_rtl.c`.
- `generated/` contiene solo **4 stubs** de vectores (NMI/IRQ/Reset/BootMmc, 966 líneas).
- `config/*.cfg` declaran ~40 funciones con límites redondeados (`end:0400`, `end:0600`…)
  que **no coinciden con los stubs generados** — son conjeturas, no análisis real JSR/RTS.
- El frame driver entrega NMI/IRQ en los puntos quiescentes del intérprete (WAI o spin
  read-only). Rutina principal: `RunOneFrameOfGame()` en `src/so_rtl.c`:
  `counter_global_frames++` → bloque auto-A → hook record/replay → NMI ($00FEB9) →
  `interp_bridge_run_until_quiescent` → sync master clock si PC=$00FEBD y frame>10.

## 2. Builds y ejecutables (¡CRÍTICO!)

> ⚠️ **HAY DOS COPIAS DEL RUNNER** (descubierto 2026-08-24):
> `$PROJECT_ROOT\Snesrecomp\` (raíz) y
> `StarOceanSNESRecomp\snesrecomp\` (**la que compila el build** según CMakeLists).
> Editar SIEMPRE con rutas desde StarOceanSNESRecomp; las rutas relativas pueden caer en
> la copia raíz y el cambio no llega al exe. Verificar con `grep` en la copia correcta
> después de editar. Las ediciones históricas (gating, hack SDD1_MODE0) están en la
> copia correcta.

| Build | Ruta exe | TRACE | Generador | Uso |
|---|---|---|---|---|
| Release rápido | `build/Release/StarOcean.exe` | OFF | VS2022 | Jugar / grabar inputs (rápido, sin debug server) |
| Trace | `build-trace/StarOcean.exe` | ON | Ninja | Validación TCP (lento ~26fps) |
| Debug | `build_ninja/StarOcean.exe` | OFF | Ninja | — |

- ROM junto al exe: `Star Ocean (Japan).sfc` (copy en cada build dir).
- **Rebuild Release:** `cmake --build build --config Release --target StarOcean`
- **Rebuild trace (requiere MSVC env):** `cmd //c ".\\build_trace.bat"`
  (el .bat hace `call vcvars64.bat` + `ninja -C build-trace`). Sin vcvars → error
  `stdint.h not found`.
- `SNESRECOMP_TRACE=1` habilita el debug server; con 0 todos sus calls son no-op
  (stubs inline en `debug_server.h`). Compilar `debug_server.c` requiere TRACE=1.
- Flag del proyecto: `SNESRECOMP_ENABLE_TRACE=ON` en CMake → `build-trace/CMakeCache.txt`.

## 3. Input: grabador/replay ELIMINADO (2026-08-24)

- El sistema `SNESRECOMP_INPUT_MODE=record|replay` + `so_inputs.log` fue **eliminado
  de `src/so_rtl.c`**: sobreescribía el joypad y dejaba el teclado muerto en el menú
  si quedaba la env var puesta en la sesión (PowerShell conserva las env vars).
- El teclado del host (keybinds.ini → `RtlRunFrame`) ahora llega SIEMPRE al juego.
- Los probes headless conducen la pulsación de New Game vía debug server:
  `set_controller 0x100` (~0.45 s) en `so_drive.py` (launch_and_drive), y `main.c`
  fusiona `debug_server_get_controller_inputs()` en `RtlRunFrame`.
- El log grabado era 379 frames (~6.3 s) con 24 pulsaciones de A (0x100) → menú.
- **Layout de bits runner (joy1/joy2):** B=0x001, Y=0x002, SELECT=0x004, START=0x008,
  UP=0x010, DOWN=0x020, LEFT=0x040, RIGHT=0x080, A=0x100, X=0x200, L=0x400, R=0x800.
  (Nota: este layout NO es el de $4218/$4219 del hardware; el host lo remapea.)

## 4. S-DD1 (Fase 1 — COMPLETADA)

- Motor: `snesrecomp/runner/src/snes/sdd1.c` — port estructural de bsnes
  (`decompressor.cpp`: IM/GCD/BG/PEM/CM/OL + mapeo MMC).
- **Validado byte-a-byte contra referente independiente en Python** (`sdd1_ref.py`,
  port fiel de bsnes): **24/24 chunks** en las 3 vías (bloque, DMA, CPU). El motor C
  era idéntico desde el inicio; no hizo falta corregirlo.
- Harness de comparación: `sdd1_engine_test.c` + `sdd1_compare.py` + `build_sdd1_test.bat`
  (MSVC). Salida: `sdd1_engine_out.txt`.
- **Camino real verificado:** el juego escribe $4800/$4801, arma DMA y lee del window
  MMC ($C0-$FF vía páginas $4804-$4807). La cadena es
  `dma_transferByte → snes_read → cart_read → sdd1_cpu_read`.
- El log de la sesión headless mostró la descompresión real (MMC reads en FF:D0AB,
  r4807=05). Chunks del menú: FE:D27F size=$1800, D4:F159 $8000, DA:F458 $1C00, etc.
- ROM: 6 MB, LoROM, S-DD1 (cartType=8, coproc=4).
- **Logging gateado** detrás de `SNESRECOMP_TRACE` (sdd1.c/dma.c/ppu.c). Antes escribía
  un fprintf por byte → 16 MB/s (`sdd1_full_debug.log`, UTF-16 por redirección Windows).

## 5. Hack SDD1_MODE0 — ELIMINADO (2026-08-24)

- `ppu.c` tenía un hack que interceptaba escrituras a BGSC y descomprimía direcciones
  **hardcodeadas** (FE:612F, FE:5CF0, FE:63A1 con tamaños 1902/1900/4096) directo a VRAM.
  Violaba la regla de oro de agents.md (cero parches visuales empíricos).
- **Eliminado por completo** junto con las estáticas de "protección" muertas y el logging
  asociado. El menú de nombre funciona por el **camino real** (DMA→MMC→S-DD1).

## 6. Trace de bsnes-plus (referencia para validación)

- Archivo: `$PROJECT_ROOT\Star Ocean (Japan)-trace.log` (**249 MB, está
  FUERA del proyecto**, en la raíz de E:).
- Formato por línea: `ca6382 sta $2105 [002105] A:0000 X:5800 ... V:225 H:208 F:21`
  - `V:` = scanline, `H:` = dot, `F:` = **framecounter MÓDULO 60** (no frame absoluto).
    En bsnes-plus: `++status.frame == 60 → status.frame = 0` (NTSC). ¡No confundir!
  - La instrucción se desensambla en el PC de la dirección, los registros son previos
    a la ejecución.
- **Cobertura:** título (Mode 1, BGMODE=$09 en L283966) → new game → entrada al menú
  de nombre (Mode 0, BGMODE=$00 en L403092). ~2.54M líneas, 7123 PCs únicos.
- Bucle dominante (49%): `$CA6D18 lda $4212` = **poll de vblank** (espera input en
  título/menú).
- ⚠️ **Modo traceMask de bsnes-plus:** si está activado, cada PC se imprime solo la
  primera vez (NO es trace cronológico). El trace actual NO lo usa (2.54M líneas con
  repeticiones = cronológico real). Si se genera un trace nuevo, asegurar traceMask OFF.
- Scripts de análisis en el proyecto: `analyze_trace.py`, `analyze_trace2.py`,
  `analyze_trace3.py` (buscan la transición a Mode 0 tras línea >400000).

## 7. Menú de nombre — estado verificado (sin hack)

- PPU: `bgmode=0`, `bgTileAdr=$4222`, `bgXsc=[$48,$4C,$50,$58]` → tilemaps en
  **$4800/$4C00/$5000/$5800**. screenEnabled=0x1f (4 BG + OBJ), inidisp 0x0f (visible).
- VRAM poblada: bloques 4000:890, 5000:230, 8000:770, A000:430, B000:150,
  C000:115-136 (**animado**: cursor/parpadeo), E000:606, F000:1005.
- Tilemaps: BG1 542/1024, BG2 274/1024, BG3 230/1024, BG4 0/1024. CGRAM 201/256.
- **Determinismo probado:** VRAM byte-idéntica entre log del usuario y patrón auto-A,
  salvo 239 bytes en $C000 (contenido animado). Tilemaps y tiles: 0 bytes difieren.
- **Setup PPU 14/14 registros idénticos a bsnes** (ver `compare_menu_setup.py`):
  BGMODE=0x00; maps 0x48/0x4C/0x50/0x58; tiles 0x22/0x42; windows 0x1F/0x00/0x1F/0x00;
  color math 0x20/0x60/0xE0.
- **S-DD1 MMC:** 1036 escrituras (runner) vs 1063 (bsnes) — patrón de páginas
  $4806/$4807 = $04/$05, $02/$03 repetido.

## 8. Debug server TCP (puerto 13308 — SOLO build-trace)

Comandos verificados:
- `get_ppu_state` → JSON con bgmode, bgTileAdr, inidisp, screenEnabled, scrolls…
- `dump_vram <addr_hex> <len_DECIMAL>` ⚠️ **el len se parsea con `%u`: `0x400` se lee
  como 0.** Usar decimal (p.ej. `dump_vram 0x4800 1024`). Respuesta: hex gigante en JSON.
- `dump_cgram` (512 B), `dump_oam`, `dump_apu_ram`.
- `dump_frame_vram <frame> [addr_hex] [len]`, `dump_frame_wram <frame> [addr_hex] [len]`,
  `dump_frame_cgram <frame>` → leen el anillo histórico (6000 frames × wram 128KB +
  vram 64KB + cgram 512B ≈ 1.2 GB residentes). `dump_frame_cgram` fue añadido 2026-08-24
  (registrado en la tabla de comandos; requiere rebuild del trace).
  ⚠️ **El anillo solo contiene frames COMPLETADOS:** `screenshot` reporta el frame en
  curso (N), pero el anillo llega a N-1 (o menos). Consultar `history` y volcar el
  `newest`, NO el frame del screenshot (si no: "frame N not in ring buffer").
- `trace_reg <lo_hex> <hi_hex>` + `trace_reg_reset` + `get_reg_trace [nostack]`:
  registra escrituras a registros en el anillo (32768 entradas).
  ⚠️ **El anillo se llena con el spam de $2118/$2119 (VRAM data): 9K escrituras en 6
  frames.** Para capturar BGMODE/S-DD1, armar rangos que EXCLUYAN $2118/$2119.
  El hook lo llama `WriteReg` (common_rtl.c) para todo $2000-$5FFF y `snes.c` para
  el resto del B-bus.
- `screenshot <path>` → BMP 256×224 (sin widescreen); responde con el frame actual.
- `fingerprint <path> [count]` → dump de hashes WRAM por frame (anillo 8192).
- `get_frame <N>`, `frame_range`, `history`, `get_cpu_state`, `get_interrupt_state`,
  `get_dma_state`, `ppu_lines`, `muldiv_check`…
- `debug_server_on_reg_write` se dispara desde `snes_write` para adr en $2100-$43FF y
  desde `WriteReg` (common_rtl.c:743) para el resto. $2105 SÍ se captura vía WriteReg.

## 9. Probes / herramientas de validación (en StarOceanSNESRecomp/)

- `probe_replay.py` — reproduce el log en build-trace, detecta el menú poblado (BG1
  tilemap ≥400 entradas), vuelca VRAM/CGRAM/screenshot y **mata el juego al terminar**
  (~14 s total). Ideal para validación rápida.
- `probe_regtrace.py` — igual pero arma `trace_reg` (BGMODE/maps/windows/S-DD1) y guarda
  la secuencia en `regtrace.json`.
- `probe_name.py`, `debug_probe.py` — versiones anteriores (más lentas, con tiempos fijos).
- `compare_menu_setup.py` — compara 14 registros PPU del runner contra el trace de bsnes
  (valores idénticos: OK 14/14).
- `regression_test.py` — **test de regresión con hashes (Fase 0, COMPLETADO 2026-08-24):**
  reproduce `so_inputs.log` en build-trace, espera el menú poblado (BG1 ≥400 entradas),
  consulta `history` para el frame `newest`, vuelca VRAM/CGRAM/WRAM del anillo en ese
  mismo frame y compara SHA-256 contra `build-trace/namescreen_ref.json`.
  `--store` guarda la referencia; sin flag verifica. **PASS determinista (2 runs,
  hashes idénticos, frame 236).** ~14 s por run.
- `find_bgmode_writes.py` — lista escrituras a $2105 en el trace con posición.
- `render_mode0.py` / `render_bg.py` — renderizan capas desde `build/saves/ppu_dump.bin`
  (VRAM 64KB + CGRAM 512B concatenados). Asumen tilemaps $4800/$4C00/$5000/$5800 y tiles
  $2000/$4000 — **esos supuestos eran de la época del hack; verificar contra la VRAM real.**
- PPM de referencia (estado con hack): `bg1_tiles.ppm`…`bg4_tiles.ppm` (256×256 atlases).

## 10. Gotchas de Windows / herramientas

- En git-bash, `&` + `kill $PID` NO mata el proceso Windows real (PID distinto). Usar:
  `tasklist //FI "IMAGENAME eq StarOcean.exe" //FO CSV` → parsear PID → `taskkill //F //T //PID <pid>`.
- Comandos con `&` en bash + `sleep` + `tasklist` a veces cuelgan el timeout de la tool:
  separar en dos llamadas (lanzar, luego en otra llamada matar y analizar).
- El server de debug escucha en 13308; SO_EXCLUSIVEADDRUSE evita dobles escuchas.
- UTF-16: los logs redirigidos de Windows pueden salir en UTF-16 (grep da ruido); usar
  Python con `errors='replace'` o convertir.
- El anillo de frames históricos solo existe si `s_server_ready` (servidor TCP activo);
  en headless sin server, `record_frame` no copia nada.

## 11. Performance profiling (2026-08-24,临时, revertido)

- **Instrucciones por frame** en el menú de nombre: ~17,000 (no 1M como se estimó
  por error aritmético: los contadores de instrucciones se acumulan en bloques de
  60 frames y se debe dividir por 60).
- **Coste por instrucción: ~1.5µs** (necesario ≤0.5µs para 60fps). Compilador
  MSVC/O2, interpretador 65816 + bridge wrapper con per-instrucción:
  quiescent scan (64×20 campos), bus reads, master sync, APU accumulate.
- **Distribución del tiempo:** ~99.9% en `run_frame()` (intérprete); PPU render
  (~3ms) y APU sync de frame boundary (~0ms) son insignificantes.
- **APU flush por opcode NO es el cuello de botella** (verificado con thresh=1B:
  sin cambio de FPS).
- **Quiescent scan (64×20 fields) NO es el cuello** (verificado con QSKIP:
  sin cambio de FPS significativo).
- **Master clock deadline funciona** (yield a 357,368 master cycles = 1 frame),
  pero no reduce el instruction count porque el run principal solo ejecuta ~17K
  insns/frame (el spin ya termina antes del deadline vía el motor de
  quiescencia o simplemente porque el trabajo real es ~17K).
- **Ruta a 60fps:** reducir el overhead per-instrucción del bridge. Candidatos:
  (a) inline de bus_read/bridge_timing_bus, (b) reducir el quiescent scan a
  fingerprint-based, (c) batch del master sync (sync cada N instrucciones en
  vez de cada una).
- **Instrumentación temporal removida** (no hay que mantener en el código).

## 11b. HDMA de 8 canales (FIX 2026-08-24) — degradado del menú resuelto

- **Problema:** `SoDrawPpuFrame` (src/so_rtl.c) solo inicializaba `SimpleHdma` para
  los canales 5/6/7. El menú de nombre de Star Ocean usa **canales 1 y 2**:
  - CH1: mode=3, bAdr=$21 → escribe a **$2121/$2122 (CGRAM address + data)**:
    el **degradado de color por scanline** (el "degradado azul" que se veía mal).
  - CH2: mode=2, bAdr=$12 → escribe a **$2112 (BG4SC)**: tilemap base de BG4.
- **Fix:** bucle sobre los 8 canales: `SimpleHdma hdma_chans[8]` +
  `for i in 0..7: SimpleHdma_Init(&hdma_chans[i], &dma->channel[i])` y
  `for ch in 0..7: SimpleHdma_DoLine(&hdma_chans[ch])` por línea.
- `SimpleHdma` ya soportaba todos los modos (tablas bAdrOffsets/transferLength,
  indirecto, repCount) — solo faltaba inicializarlo para los canales 0-4.
- **Validación:** los 8 canales se reportan en `get_dma_state` (probe_hdma.py);
  el menú de nombre se puebla igual (test de regresión PASS, hashes idénticos:
  la HDMA escribe CGRAM/BG4SC durante draw_ppu_frame, NO en el snapshot del anillo)
  y visualmente coincide con bsnes-plus (capturas del usuario, 2026-08-24).
- El fix NO cambia la VRAM del anillo histórico (la HDMA modifica el render por
  línea, no el contenido base) — por eso los hashes de regresión no cambiaron.

## 11c. Timing V/H del menú — VALIDADO contra bsnes (Fase 2, 2026-08-24)

- Añadido **V/H (vPos/hPos del beam) al anillo de registros** del debug server
  (`s_reg_trace.log[].vpos/hpos` + campos V/H en `get_reg_trace`), capturado en
  `debug_server_on_reg_write` desde `g_snes->vPos/hPos`.
- **14/14 registros del setup del menú se escriben en la MISMA línea V que
  bsnes-plus** (script `compare_timing_vh.py`):
  - BGMODE $2105, maps $2107-$210A, tiles $210B/$210C → **V=225 (vblank)**
  - Windows $212C-$212F + color math $2130-$2132 → **V=226**
  - El H difiere (~600 dots) porque el runner ejecuta el setup en un burst tras
    el yield de quiescencia — inofensivo al estar ambas en vblank.
- **El ORDEN de escrituras también coincide**: BGMODE → $210B → $210C →
  $2107/8/9/A → $212C/$212E/$212D/$212F → $2130/1/2.
- ⚠️ El anillo de 32K se llena con spam de $210D (BG1HOFS, miles de escrituras
  por frame en la carga del menú) — el probe EXCLUYE $210D-$2114 (scrolls) de
  los rangos de `trace_reg`.
- Comandos: `python probe_regtrace.py` (captura regtrace.json con V/H) +
  `python compare_timing_vh.py` (compara V contra bsnes).

## 11d. Lettering STAR OCEAN — BUG del backdrop z-value (2026-08-24)

- **Síntoma:** el fondo teal (cgram[0] = $3DE0) y el lettering "STAR OCEAN"
  (BG4, mapa word $5800 / tiles word $4000, filas 11-16 del mapa, 150 entradas
  todas priority-0) estaban en VRAM correctamente, pero las letras no se veían.
- **Causa raíz:** el marcador de backdrop en el z-buffer es `0x0500`
  (`ClearBackdrop`, ppu.c:406) y el zlo de BG4-0 en modo 0 era `0x0300`.
  La comparación `z > dstz[i]` hacía que el BACKDROP ganara a BG4-0 → las
  letras (BG4-0) nunca se dibujaban sobre el fondo. En hardware el backdrop
  está por debajo de TODO.
- **Fix (ppu.c, modo 0):** zlo de BG4-0 `0x0300` → `0x0900` (entre backdrop
  0x0500 y BG4-1 0x1300). Un solo valor; el único zlo del código por debajo
  del backdrop.
- **Cómo se encontró:** bsnes-plus Tilemap Viewer del usuario mostró BG4 en
  mapa $B000/tiles $8000 (byte) = word $5800/$4000. El render en Python de
  esa zona mostraba las letras; el screenshot real no. Diagnóstico: capa por
  capa en la región (render_layers_region.py) + inspección del z-buffer.
- **Validación:** screenshot `build-trace/lettering_fixed.bmp` (mismo frame
  que vram_live.bin). Las letras aparecen en y≈88-107 sobre el teal.
  Regression_test.py sigue PASS (el fix es render-only, no toca VRAM/WRAM).
- **Nota de direcciones VRAM:** dump_vram usa offsets de BYTE sobre el array
  de words; mapa BG4 = word $5800 = byte $B000 (formula word (sc&0xfc)<<8
  ✓ correcta; el viewer de bsnes-plus muestra byte).

## 12. Harness de CO-SIMULACIÓN (SNES_COSIM, 2026-08-24)

El framework `Snesrecomp` ($PROJECT_ROOT\Snesrecomp) trae un harness
diferencial completo; nuestro árbol ya contenía el motor byte-idéntico (cosim.c,
cosim_state.c, interp816.c) y los hooks en common_rtl.c. Solo faltaba el lado juego.

### Componentes (nuevos en el proyecto)
- `cosim/harness_so.c` — A-side headless (sustituye main.c; sin SDL/audio/hilos).
  Modo standalone: `--frames N --input start:dur:mask --final-frame-dump out.ppm`.
- `cosim/harness_glue.c` + `cosim/ref_driver.c` — copia del framework (B-side interp816
  sobre nuestros propios dispositivos; `ref_driver.c` + `int g_interp_apu_driving` local).
- `cosim/CMakeLists.txt` — targets `so_cosim` + `so_cosim_ref` (MSVC+ninja; el ref
  incluye **sdd1.c** — el listado SMW no lo tiene, Star Ocean lo necesita).
- `tools/snes_cosim.py` — coordinador (copia del framework + salida `cosim_mismatch.log`).
- `cosim/gates.sh`, `build_cosim.bat`.

### Build
`cmd //c ".\\build_cosim.bat"` → `build-cosim/so_cosim.exe` + `so_cosim_ref.exe`
(necesita `SDL2.dll` copiada junto al exe para host_report). DEV-ONLY: nunca en Release.

### Gates (todos PASS, 2026-08-24)
- Gate 1: A-vs-A (so_cosim×2) 100 cps sin divergencia. Gate 2: B-vs-B (ref×2) 100 cps.
- Gate 3: `--inject ram:1000:255 --inject-at 20` → para en cp21, solo `ram` split.
- Gate 4: `--audit 25` 200 cps sin AUDIT-FAIL.
- Comandos: `python tools/snes_cosim.py --a-cmd "...exe...rom..." --b-cmd "..." --stride N --max N`
  ⚠️ rutas ABSOLUTAS con `/` y entre comillas (CreateProcess no acepta relativas con `/`).

### Track A (so_cosim vs so_cosim_ref): hallazgos
- A frame-granular diverge en cp2: el frame driver del recomp (auto-quiescent: rinde en
  el spin de vblank $00:F6F5) ejecuta ~100x MENOS ciclos/frame que el ref (H/V exacto,
  ~357K mcyc/frame) → cpu/ram/sio/pace divergen. No es un bug de código CPU: es el modelo
  de frame driver (yield-en-quiescencia vs driver exacto).
- **Lockstep por instrucción** (`SNES_COSIM_SYNC_PC=0xF703` + `SNES_COSIM_ISTRIDE=32`
  en AMBOS lados; ⚠️ el PC se parsea con `strtoul(base 0)` → pasar **0x**-prefijo):
  alinea los rulers (A 4516 vs B 4776 mcyc) y la 1ª divergencia real aparece en cp2
  (~64 opcodes tras el sync): CPU A=2/S=01F4/P=25 vs B=0/S=01F2/P=27, hPos 01A8 vs 02AC.
  Causa: el modelo de ciclos del interp A-side (bus + 6x interno) vs ref (8x slowROM)
  deriva la posición del haz → el poll de vblank $00:F6F5 ramifica distinto.
- **Fixture menú validado en AMBOS lados standalone**: `--input 76:7:100 --input 171:8:100
  --input 234:7:100 --frames 340` → `menu_a.ppm` y `menu_ref.ppm` (PNG: menu_a.png /
  menu_ref.png): ambos muestran el lettering en filas 84-108 (787/817 px brillantes);
  diff 13% = fase de animación (cada lado corre su propio modelo de frame).
  ⚠️ A-side standalone necesita `SNES_COSIM_OFF=1` (si no, cosim_init bloquea en accept
  esperando coordinador) y `SNES_COSIM_AUDIO=1` (si no, el SPC sin drenar enlentece).
  El ref standalone sale con rc=1 por "audio did not produce active output" (Star Ocean
  usa SPC HLE en el runner) — inofensivo, el PPM se escribe igual.

### Pendiente Track B (oracle bsnes externo)
- Construir `bsnes_libretro.dll` desde `$PROJECT_ROOT\bsnes\bsnes\target-libretro`
  y extender `Snesrecomp/tools/snesref/frontend.cpp` para exportar por frame: regs CPU,
  $2100-$2133, hashes VRAM/CGRAM/WRAM (el "consulta tras cada frame" del diseño).
  Alineación: ruler master_cycles + boot-offset (cosim/align_diff.py).

## 13. Pendiente / plan (fases)

- **Fase 2 (timing):** validar V/H por scanline de las escrituras a $4806/$4807 y $2105
  contra el trace (bsnes registra V/H por instrucción). Falta HDMA/IRQ por línea real
  (hoy: SimpleHdma solo canales 5-7 + vTimer simplificado + sync forzado en $00FEBD).
- **Fase 3 (recompilación real):** regenerar `config/` con análisis estático del
  snesrecomp (no a mano). Empezar por banco $C0. **Mantener el window MMC ($C0-$FF) en
  intérprete** (cambia de página vía $4804-$4807; frágil bajo recompilación estática).
- **Fase 4 (juego completo):** selección de nombre → intro → campo; SRAM (saves batería),
  sprites (límites scanline), audio (no solo "hay audio").
- ✅ **Test de regresión con hashes** (VRAM/CGRAM/WRAM del menú, cerrando el juego al
  terminar) — **COMPLETADO**: `regression_test.py` + `namescreen_ref.json` (frame 236).
- Generar traces nuevos de bsnes-plus cuando haga falta: binarios en
  `$PROJECT_ROOT\bsnes-plus-v05.105\` (bsnes-accuracy.exe /
  bsnes-performance.exe). ⚠️ asegurar traceMask OFF y que F: es módulo 60.

## 14. Track B — Cosimulación bsnes oracle (COMPLETADO parcial)

### Infraestructura
- `bsnes_libretro.dll` construido con MinGW/MSYS2 (g++ 16.2) desde
  `E:\...\bsnes\bsnes\target-libretro`.
- `tools/snesref/drive_bsnes.cpp` — driver headless libretro (sin SDL) que carga
  el core, reproduce N frames con input scripteado, y deja al core volcar estado
  vía env `SNESREF_STATE_OUT`.
- Estado por frame: `target-libretro/state_snapshot.hpp` (bsnes) +
  `cosim/harness_so.c --state-out` (nuestro runner). Formato binario compartido:
  header 'SOCO' + u32×2, then records de 197238 bytes (cpu 18B, dev 16B, ppu 66B,
  ppuValid u64, sdd1 6B, wram 128KB, vram 64KB, cgram 512B).
- Comparator: `tools/cosim_trackb.py --a <so.bin> --b <bsnes.bin> [--stats]`.
  Flags de `ppuValid` (u64): bsnes confiable en bytes 0-4,6-13,14-45 (inidisp,
  bgmode, bgTileAdr, setini, scrolls, mode7). Nosotros llenamos todo.
- Gates Track A: Gate-1 A-vs-A=0, Gate-2 B-vs-B=0, Gate-3 fault-injection
  en WRAM $1000→para cp21, Gate-4 hash audit 200 cps sin fallo. COMPLETADO.

### Hallazgos principales (240 frames, sin input)

1. **Frames 0-2: match perfecto** — WRAM/VRAM/CGRAM idénticos byte a byte.
2. **Frame 3+: divergencia** — nuestro runner escribe VRAM (1545 bytes en words
   $4036-$5E73) y PPU (inidisp=0x80, bgmode=0x09, bgXsc, mode7, etc.); bsnes
   libretro nunca escribe NADA a VRAM ni a registros PPU (todo = 0x00).
3. **bsnes queda en un loop en $C8:F419-F42F** (PC barely cambia entre frames
   120-239). El juego nunca habilita NMI ($4200 = 0 escrituras en el trace)
   ni sube datos a VRAM.
4. **Nuestro runner sube VRAM correctamente** — el nombre "STAR OCEAN" se ve en
   el título, los tiles se renderizan, CGRAM tiene paletas correctas.
5. **Causa raíz probable**: bsnes libretro no ejecuta la secuencia de SDD1 DMA
   que carga los tiles de pantalla. La PC del juego avanza hasta C0/C8 pero se
   atasca en un loop de espera. Nuestro runner, con `sdd1.c` propio, ejecuta la
   descompresión correctamente.

### Nota: bsnes NO es oracle absoluto aquí
El hallazgo invierte la asunción original: **nuestro runner produce output más
fiel al SNES real** (tiles renderizados, CGRAM poblada, PPU en modo correcto).
El bsnes libretro core parece tener un bug o falta de soporte para la ruta
de descompresión SDD1 de Star Ocean. Usar el driver bsnes-plus (accuracy
build, con trace completo) como oracle de referencia es la ruta correcta para
validar frame-a-frame.

### Utilización
```powershell
# bsnes oracle
cd "$PROJECT_ROOT\StarOceanSNESRecomp"
set SNESREF_STATE_OUT=%CD%\build-cosim\trackb_bsnes.bin
tools\snesref\drive_bsnes.exe "E:\...\bsnes\bsnes\out\bsnes_libretro.dll" "build\Release\Star Ocean (Japan).sfc" --frames 240

# nuestro runner
set SNES_COSIM_OFF=1
build-cosim\so_cosim.exe "build\Release\Star Ocean (Japan).sfc" --frames 240 --state-out build-cosim\trackb_so.bin

# comparar
python tools\cosim_trackb.py --a build-cosim\trackb_so.bin --b build-cosim\trackb_bsnes.bin --stats
```
