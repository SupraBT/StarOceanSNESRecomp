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
  **(2026-09-30: obsoleto.** `build_trace.bat` se eliminó de la raíz: el flag
  `SNESRECOMP_ENABLE_TRACE` ya no existe en las fuentes (0 coincidencias en
  `src/` y `snesrecomp/runner/src/`) y el árbol de builds es VS2022. La
  instrumentación vive hoy en `build-dev` y va por variables de entorno, ver
  §23.**)**
- `SNESRECOMP_TRACE=1` habilita el debug server; con 0 todos sus calls son no-op
  (stubs inline en `debug_server.h`). Compilar `debug_server.c` requiere TRACE=1.
- Flag del proyecto: `SNESRECOMP_ENABLE_TRACE=ON` en CMake → `build-trace/CMakeCache.txt`.
  **(2026-09-30: flag eliminado del motor; ver §23.)**

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
  **(2026-09-30: ambas eliminadas de la raíz junto con `analyze_ppu.py`,
  `decode_vram.py`, `vram_viewer.py`, `vram_visualizer.py`: nada en el árbol
  produce ya `ppu_dump.bin`, así que eran herramientas muertas. Recuperables con
  `git show <commit>^:<fichero>`. Lo vivo para lo mismo: `cosim/dump_ppu_cgram.py`
  y `tools/oracle_overlay.py`. Ver §23.)**
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

## 15. Intro: quién gobierna los fundidos y qué le falta al recomp (2026-09-28)

Investigación del 2º fundido de la intro (que en hardware avanza 1 nivel cada 4
frames) contra el oráculo de Mesen (`StarOceanRecompDocumentacion/mesen_oracle.tsv`).
Todo lo de aquí está **medido**, con los artefactos en `build-dev/Release/`.

### 15.1 El contador del invitado que gobierna las cadencias

En el ROM (HiROM; desensamblado con `tools/dis_range.py`):

* **`$E4` es el contador de frames del invitado**: `INC $E4` una vez por vblank en
  `CC:08B4`, `CC:1526`, `CC:19F8`, `CC:1CCA`, `CC:20C8`, `CC:2829` — es decir, un
  `INC` por cada uno de los ~6 bucles de escena del motor de cutscenes (banco
  `$CC`), cada uno terminando en `LDA $DA / STA $2100` + `INC $E4` + `JMP`.
* **La cadencia es `$E4 & N`**: hay 79 sitios `LDA $E4 / AND #$0003 / BNE`
  (y 17 con `&1`, 9 con `&7`). Ejemplos: `CC:0C53` (rampa de `$0D01` de BG1 VOFS
  cada 4 frames), `CC:1033` (modo 8 de fundido, CGRAM cada 4 frames),
  `CC:2766`. Es el mismo idioma que produce los ritmos 1/2/4/8 del oráculo.
* **Máquina de fundidos del motor**: `CC:0924` despacha `$0AFB` con la tabla de
  `CC:0953` → modo 6 = `CC:0B44` (`INC $DA`, 1 frame/nivel), modo 7 = `CC:0B57`
  (`DEC $DA`, 1 frame/nivel), modo 8 = `CC:1033` (`$E4&3` + fundido de CGRAM de
   32 pasos = 128 frames), modo 4 = `CC:0C0B` (fundido de CGRAM inverso).  El
  script alternativo `$0AF9` (tabla `CC:096D`) arranca esos modos (op 6/7 →
  modos 1 frame/nivel; op 8 → `CC:1026` = `$0AFD=#$20`, `$0AFB=8`).
* **`$DA` = sombra de inidisp**, aplicada por `LDA $DA / STA $2100` en 10 sitios
  (`C0:018F`, `C0:02BE`, `C0:213A`, `C1:0206`, `CC:088D`, `CC:151D`, `CC:19F5`,
  `CC:1CC7`, `CC:20C5`, `CC:280E`).
* **La biblioteca `C8:F4xx` es SIEMPRE 1 nivel por vblank**: `F497` (fade-in,
  `STA $2100` en `F4A3`), `F4AB` (blank N), `F4B7` (fade-out, `F4C5`+`F4CC`),
  `F4D0` (fade-in con pad, `F4DE`), `F4E9` (blank N con pad), `F4FA` (fade-out
  con pad, `F50A`).  Lo mismo en banco `$C0` (`C0:2126`, `C0:C4E9`, `C0:C48E`) y
  en banco `$CC` (`CC:0FAC`, `CC:0FCE`, `CC:0FE7`, `CC:1013`), todos con
  `JSL $C08496` = espera vblank de 1 frame (`C0:8496`).

Conclusión: **el fundido a 4 frames/nivel no puede salir de `C8:F4xx`**; sale de
un bucle del motor con puerta `$E4 & 3` sobre un valor que termina aplicándose a
`$2100` (o de un CGRAM fade del modo 8 con la misma máscara).

### 15.2 Lo que hace el recomp (medido)

Corrida `SNESRECOMP_FRAME_STATE=1 SNESRECOMP_INIDISP_TRACE=1` (400 frames):

* `E4=0000`, `AFB=00`, `AFD=0000` en **400/400** frames; `DA=80` constante.
* Watch de `$00E4`: **cero escrituras en banco 00** (solo aparecen 8 escrituras a
  `7F:00E4`, que es otra dirección de WRAM y de otro subsistema, `IPC=C04D6x`).
* Las 55 escrituras a `$2100` salen de `IPC=C8F4DE` (×30, las dos subidas) y
  `IPC=C8F4C5` (×15, la bajada) → **biblioteca `C8:F4xx`, 1 nivel/vblank**.
* El invitado nunca entra en el motor `$CC`: `$0D01` (que `CC:0C53` rampa cada 4
  frames) se queda en `FF`.

### 15.3 Overlay cuantitativo contra el oráculo

Los `master` de ambas corridas se alinean en `357368` ciclos/frame, así que la
comparación es en frames de invitado:

| evento                     | recomp (frame de invitado) | hardware (oráculo) |
|----------------------------|---------------------------|--------------------|
| fade-in 1 (01..0F)         | 132 → 146 (15)            | 416 → 430 (15)     |
| fade-out (0E..00+80)       | 277 → 291 (15)            | 703 → 717 (15)     |
| hueco (blank)              | 292 → 293 (**3**)          | 718 → 841 (**124**)|
| fade-in 2 (01..0F)         | 294 → 308 (15, 1/frame)   | 842 → 898 (**56**, 4/frame) |

* Fade-in 1 y fade-out: **idénticos** (1 frame/nivel en ambos).
* Fade-in 2: 15 frames vs 56 → **el recomp hace 4× demasiado rápido**.
* Distancia fade-in-1 → fade-out: recomp **145** frames, hardware **287**
  (= 100+32+140, las tres esperas del paso de la intro).
* Hueco: recomp **3** frames, hardware **124**.

Es decir: no es solo la cadencia; **la secuencia de esperas del invitado está
comprimida** (el invitado llega antes a cada estado).

### 15.4 Hipótesis refutadas (no volver a probarlas)

* **VFF (fast-forward de vblank)**: `SNESRECOMP_NO_VBLANK_FF=1` da resultados
  **byte-idénticos** (mismo `master` y mismos eventos) → el VFF no altera el
  tiempo del invitado.
* **Entrega de V-IRQ**: exactamente **1 IRQ por frame** de invitado en todo el
  tramo (`irq=` avanza de 1 en 1, `vTimer=0`), y el handshake `$D9` de batalla no
  se toca en la intro.
* **Gate `snes_frame_counter > 10` del VFF**: ya se había refutado (byte-idéntico).
* **NMI**: el oráculo nunca activa el bit 7 de `$4200`; `nmiEn=0` es correcto.

### 15.5 La anomalía grande: el canal APU está muerto tras el boot

Con la traza nueva `SNESRECOMP_APU_PORT_RW` (puertos `$2140-$2143`, con valor y
`master`) en 200 host frames (~300 frames de invitado):

* **290.662 accesos, TODOS en el host frame 3** (270.384 lecturas + 20.278
  escrituras; la última a `master=24.831.376` ≈ frame de invitado 70) → la subida
  del driver SPC del boot.
* **Cero accesos en los 197 host frames siguientes.**

Oráculo (cobertura fr411-11701, ver §15.8): **319.713 escrituras y 3.662.900
lecturas** a `$2140-$2143` (media ~28 escrituras y ~324 lecturas por frame); en
el arranque del fade-in-1 (fr411-415) ~**890 escrituras y ~8.270 lecturas por
frame**, y en el tramo del hueco/2º fundido ~230-440 escrituras y ~5.600
lecturas por frame (pico fr1709: 901/8.261).

⇒ En hardware el juego alimenta y sondea el motor de sonido **cada frame**
durante la intro; en el recomp, después del boot, **nunca más**.  Cualquier espera
del invitado que dependa del handshake con el SPC ("banca cargada", "driver
listo") se satisface al instante en el recomp: candidato principal a explicar la
compresión de §15.3 (incluido el hueco de 124 frames).

### 15.6 Herramientas nuevas (todas dev, coste cero si no se define la variable)

> Las tres primeras se añadieron en esta sesión; el resto ya existían.

```bash
# 1) Traza de PC por frame de INVITADO (snes.c): una línea por frontera de frame
SNESRECOMP_PC_LOG=pc_frame.log ./StarOcean.exe
#    gf=<frame invitado> hostf=<frame host> pc=<PC intérprete> resume=<PC puente> fn=<función AOT>

# 2) Traza de puertos APU $2140-$2143 (cpu_state.c, cpu_read8/16 + cpu_hw_log)
SNESRECOMP_APU_PORT_RW=apu_rw.log ./StarOcean.exe
#    f<hostf> R|W $21xx=VV master=<clk> <función AOT>

# 3) Escrituras a un rango de memoria con estado de CPU (ya existía)
SNESRECOMP_WLOG_ADDR="0083:0084:ram83.log" SNESRECOMP_WLOG_STATE=1 ./StarOcean.exe

# 4) Escrituras a $2100 con el PC que las hace (ya existía)
SNESRECOMP_INIDISP_TRACE=1 SNESRECOMP_FRAME_STATE=1 ./StarOcean.exe 2> err.log
```

### 15.7 Sonda de Mesen (`tools/mesen_intro_probe.lua`)

Pendiente de ejecutar por el usuario (no se puede lanzar Mesen desde el agente).

Responde en hardware lo que el recomp no puede contestarse solo:

* **exec callbacks** en las rutinas candidatas: `C8:F407/F41D/F497/F4AB/F4B7/
  F4C5/F4D0/F4D4/F4DE`, `CC:088B/08B4/0924/0B44/0B57/1033/104B`, `C0:212B/2141`,
  `C0:2AE0` → dice qué rutina escribe `$2100` en el 2º fundido y con qué
  frecuencia.
* **write callbacks** en `$2100`, `$DA`, `$E4/$E5`, `$0AF9/$0AFA`, `$0AFB/$0AFC`,
  `$0AFD/$0AFE` (valores por frame).
* **snapshot por frame** de `$E4/$E5/$DA/$0AFB/$0AFD` (leídos en `$00xx` y `$7Exx`)
  y de `PC/D/DB` (`emu.getCpuState()`), más `emu.getMasterClock()`.

Detalles de la API de esta build de MesenCE (aprendidos de `mesen_probe.log`, el
script anterior se perdió):

* No existe el global `memory` → usar `emu.addMemoryCallback(fn, type, memType,
  start, end)` con `memType = emu.memType.snesMemory (0)`; `emu.callbackType` y
  `emu.eventType` **no** están expuestos como tabla numérica: `write=1`,
  `read=0`, `exec=2`; `endFrame=3`, `startFrame=2`, `scriptEnded=5`.
* `emu.addEventCallback(fn, 3)` registra el fin de frame.
* Registros PPU (`$2100`) **sí** disparan en `snesMemory`; `snesRegister (20)` no.

### 15.8 Advertencias para la próxima comparación

* El `mesen_oracle.tsv` tiene **dos pasadas**: la 1ª cubre los frames 0-410
  (solo columnas `master`/`cpuCyc`) y la 2ª los frames **411-11701** con todas
  las sondas.  El motivo no es un savestate: el script antiguo hacía una
  *calibración* de ~400 frames (registraba sondas de prueba, contaba disparos y
  elegía `snesMemory` como memoria válida) **antes** de registrar las 17 sondas
  reales.  Consecuencia: **`inidisp`/`r4200`/`w2140` no existen antes del frame
  411**; "el hardware no toca la APU al principio" es un artefacto, no un dato.
  La sonda nueva (`tools/mesen_intro_probe.lua`) registra desde el frame 1.
* `master` del oráculo = `fr * 357368` exacto en **ambas** pasadas → el índice de
  frame es relativo al reset y sirve para alinear por `master`, pero la
  comparación fina debe hacerse por **transiciones** (`tools/oracle_overlay.py`),
  que compara *intervalos* (p.ej. `1.030` = mismo ritmo que el hardware).
* `oracle_overlay.py --oracle ... --recomp <log>` exige que el horizonte del
  recomp (`master` final) cubra los frames del oráculo que tienen datos (≥411):
  una corrida de 200 host frames termina en `master≈115M` (frame 322) y el
  overlay sale con `rows=0` — no es un fallo de la herramienta, hace falta una
  corrida más larga (p.ej. `SNESRECOMP_EXIT_AT_FRAME=1200`).
* `code_search` (ripgrep vendorizado) sigue roto: usar
  `StarOceanRecompDocumentacion/rg.exe` o `grep` del shell.
* `build-clean` intacto; `versionlimpiagithub` congelada; `StarOceanRecomp` no es
  repo git.

### 15.9 Causa raíz candidata y siguiente paso

El invitado del recomp llega al fade-in-1 en el frame **133** y el de hardware en
el **416**; los 283 frames de diferencia son **espera del invitado** (bucles de
vblank), no trabajo extra del recomp.  Dos mecanismos pueden colapsar esas
esperas de 283 frames a ~0, y ambos son medibles:

1. **SDD1**: si el juego arranca la descompresión de gráficos y sondea el estado
   hasta que termina, en hardware eso cuesta cientos de frames; en el recomp
   `sdd1.c` descomprime dentro de una llamada de host y la espera desaparece.
   Medir: callbacks de lectura `$4800-$4807` en la sonda de Mesen contra la
   misma ventana en el recomp.
2. **SPC/handshake**: hardware habla con `$2140-$2143` en cada frame del tramo
   (890 escrituras + 8.270 lecturas por frame en el arranque del fade-in-1); el
   recomp **no toca los puertos tras el boot** (§15.5).  Si el juego sincroniza
   el avance de la intro con "el SPC ya cargó X", esa espera también colapsa.
   Medir: comparar el tramo final del handshake del boot del recomp
   (`SNESRECOMP_APU_PORT_RW`) con el mismo tramo en Mesen (misma sonda, ahora
   desde el frame 1).

Hasta fijar cuál de las dos es: **no tocar el driver**.  Las hipótesis que ya se
probó y refutó están en §15.4, y el cambio de driver que se barajó antes
(entregar V-IRQ por frame de invitado) no es necesario: la entrega ya es 1/frame.

Cierre previsto: (a) ejecutar `mesen_intro_probe.lua` y comparar la cadencia de
`$E4/$DA/$0AFB` y las esperas por frame; (b) decidir si el trabajo pendiente es
el reloj del SDD1 (acreditar ciclos de guest por byte descomprimido), el
handshake del SPC, o la secuencia de pasos de la intro; (c) sólo entonces
cambiar el driver, con A/B byte-exacto contra el oráculo.

## 16. El frame oracle, el reloj por frame, el cuelgue del menú y herramientas (2026-09-28, tarde)

### 16.1 Cómo decide el runtime que un frame ha terminado (el «frame oracle»)

Star Ocean **no activa NMI nunca**: `nmiEn=0` en todas las líneas `[fstate]` y
`r4200` reconstruido = `21` (vIRQ + auto-joypad, sin bit 7). Por eso el borde de
frame del invitado no puede ser el NMI y lo decide un heurístico:

* `RunOneFrameOfGame` (`src/so_rtl.c`) define el frame invitado como
  `counter_global_frames++` → NMI si estuviera activo →
  `interp_bridge_run_until_quiescent` (modo auto-quiescente, `yield_pc =
  0xFFFFFFFE`), más dos casos especiales: `$00FEBD` (fuerza el haz a vblank si el
  invitado está en el vector IRQ) y el `$D9` de batalla.
* El detector de quiescencia (`interp_bridge.c`, bloque `if (auto_quiescent)`)
  compara el estado COMPLETO del invitado (pc, A/X/Y/SP/DP/DB/K, todas las
  banderas, `write_epoch` y `continuous_read_epoch`) y **cede el frame en cuanto
  ese estado se repite tres veces dentro de 256 pasos**. Es decir, el fin de
  frame es «tercer estado idéntico en un bucle apretado», no un borde de
  hardware.

Consecuencias, medidas:

* En juego normal el yield cae en el spin de vblank, de modo que **el frame del
  recomp es exactamente un frame de hardware**: en ventanas de 100 frames entre
  el 100 y el 1500, `master/frame = 357.368,0` exacto y `cpu/frame`
  59.216-59.540 frente a los 59.561 teóricos. **No hay inflación de reloj.** La
  cifra «380-464k master/frame» que se barajó antes era un error aritmético
  (dividir el contador acumulado, que arranca con ~33,6 M de offset porque el
  boot consume ~94 frames de tiempo de invitado en el frame 3).
* Pero un bucle estable que **no** sea el de vblank también cede el frame ahí
  mismo: el frame termina antes de tiempo y el runner sigue produciendo frames
  mientras el invitado sigue dentro de su espera. Ese es el aspecto exacto de
  «pantalla negra con los frames subiendo»: no es un cuelgue del emulador, es un
  invitado esperando algo que no llega mientras el runner avanza frames vacíos.
  Es la misma clase de fallo que el caso `$D9` de batalla ya documentado en
  `so_rtl.c` (allí se tapó con un caso especial; aquí se detecta con §16.3).

### 16.2 El experimento de cobro de ciclos de DMA queda OFF por defecto

`snes_writeReg` case `$420b` cobraba `iters*2` ciclos de CPU y `iters*2*6` de
master tras `dma_startDma`. Medido con `rep_menu2` (ventana + audio):

| métrica (frames de invitado) | con cobro | sin cobro | hardware |
|---|---|---|---|
| force-blank del menú | 319→504 = **185** | 382→504 = **123** | fr 718→841 = **124** |
| fade-in-1 → fade-out | — | **288** | **287** |

Era la **única** diferencia de comportamiento real entre `build-dev` y
`build-clean`: los 16 usos de `SNESRECOMP_CLEAN_BUILD` son log/medición (fase,
perfil AOT, `wait_if_paused`) salvo la colocación de `GetActiveControllers()`,
que es equivalente con el pad-marker apagado. Ahora está **OFF por defecto**;
`SNESRECOMP_DMA_CHARGE=1` lo reactiva solo para A/B. Sin él, las dos métricas
independientes caen a 1 frame del oráculo.

### 16.3 Herramientas nuevas

* `SNESRECOMP_HANG_GUARD[=base]` (+ `SNESRECOMP_HANG_FRAMES`, def. 600): un
  muestreo por frame invitado, sin hashing. Si la pantalla lleva N frames
  seguidos en force-blank **y** el invitado solo ha ejecutado ≤2 rutinas (pc de
  reanudación + función AOT) en toda la ventana, escribe `base.json` (informe
  completo vía `host_report_dump_json`, con volcado de WRAM/CPU) y `base.txt`
  (rutina, pila AOT, registros, pila del invitado, `$E4/$DA/$AFB/$AFD/$0B01`,
  puertos APU y el anillo de los últimos 96 frames). Verificado: con umbral 100
  dispara en el hueco legítimo y avisa «la pantalla volvió a la vida en el frame
  505»; con el 600 por defecto no dispara en ese hueco.
* `run_dev_forense.bat` (raíz del proyecto): lanza `build-dev` con ventana y
  audio y todas las sondas a `logs/` (estado por frame, PC por frame,
  `$0B00-$0B03`, fase y hang-guard). `run_dev_forense.bat apu` añade la traza del
  handshake SPC.
* `build-clean-test/Release/` (`SNESRECOMP_CLEAN_BUILD=ON`, fuentes actuales, con
  ROM, `SDL3.dll`, `config.ini` y `keybinds.ini` dentro) + `run_clean_ab.bat`:
  para el A/B «¿es el código dev o son las fuentes?» sin tocar `build-clean`.
  Verificado: resuelve la ROM por SHA-256 en 97 ms, `video=windows
  audio=wasapi`, 695 frames en 14 s y el informe al cerrar (`taskkill` sin `/F`
  cierra limpio y escribe `last_run_report.json`).
* **Regla de invocación (importante):** las corridas lanzadas desde shell deben
  pasar la ROM como PRIMER ARGUMENTO (`StarOcean.exe "Star Ocean (Japan).sfc"`).
  Así el arranque la resuelve por SHA-256 y no abre el launcher; sin argumento,
  si `rom.cfg` no apunta a un fichero válido, el launcher la pide a mano (dos
  corridas de validación del 2026-09-28 se quedaron esperando eso). Todos los
  `.bat` de la raíz ya lo hacen.

### 16.4 Boot: coste y pacing

* Reloj de pared, ventana + audio: hasta el frame 2 = 1,54 s; hasta el 100 =
  4,49 s; hasta el 400 = 10,0 s ⇒ ~30 ms/frame en juego (`[phase] emu=15,4 ms
  draw=13,5 ms => 34,6 FPS`). El boot hasta el frame 2 ≈ **1,2 s**.
* En tiempo de invitado el boot se concentra en el frame 3: de f=3 a f=4 el
  `master` avanza **23,57 M** = **66 frames** de invitado, con 290.662 accesos a
  `$2140-$2143` (20.278 escrituras ≈ 10 KB de subida al SPC) y ~3,87 M ciclos de
  CPU. El invitado factura ~393 ciclos por byte (hardware: ~30-40) porque
  sondea mientras espera, y el SPC avanza al ritmo del hilo de audio (ver el
  comentario del boot-watchdog en `common_cpu_infra.c`). En hardware esa subida
  cuesta ~10-20 ms de pared, no 1,2 s.

### 16.5 Estado de la petición vigente (cuelgue al dar New Game)

En repeticiones con ventana + audio y la MISMA entrada de `rep_menu2` el tramo
del menú **no** se queda colgado para siempre en ninguno de los dos modos de
cobro: es un force-blank de ~123 frames (≈3,6 s a 34,6 fps) que resuelve y entra
en código de escena (`E4` contando, `AFB=03`). Como el fallo real del usuario es
intermitente y depende de su entrada/estado, hay que capturar el estado
congelado: `run_dev_forense.bat` (logs + `hang_report`) y `last_run_report.json`
(volcado de WRAM/CPU al salir).

Nota de método: todas las corridas de esta sección son con **ventana y audio**.
El informe de la app lo prueba (`SDL init ok: video=windows audio=wasapi`,
`first audio callback (len=1280)`); el `video_driver: "(none)"` del JSON es solo
porque ese campo se consulta después de cerrar SDL.

### 16.6 Corrida buena del usuario (833 frames, input real, menú de nombre OK)

Secuencia de `inidisp` (frames de invitado, entre paréntesis `$E4`):
`5-19` fade-in 1 (01→0F, 1/frame) · `67-80` fade-out (0E→01, 1/frame) ·
`81-102` **hueco** · `107-163` fade-in lento (**4 frames/nivel**: 107=01,
111=02, 115=03 …, con `$E4` contando 0001,0005,0009…) · `271-278` fade-out ·
`315-324` · `416-424` · `547-561` · `692-706` · `708-722`.

Las **cadencias coinciden con hardware** (salida 1 nivel/frame, entrada lenta
4 frames/nivel: hardware fr 703-717 y 842-898).  La divergencia está en el
hueco: **22 frames en el recomp (81-102) frente a 124 en hardware (718-841)**.

Estructura del hueco medida en el oráculo contando accesos APU por frame:

| tramo hardware | frames | tráfico `$2140` |
|---|---|---|
| fr 718-779 | 62 | **cero** |
| fr 780-815 | 36 | 232-889 W / 1.990-8.893 R por frame |
| fr 820-841 | 22 | **cero** |

En el recomp, `logs/pc.log` del tramo 81-102 muestra `resume` en
`C04D62/C086BA/C086BE/C086C6/C086EB/C088xx/C085xx`: es el **bucle de subida al
SPC** (`C0:86BA`: `LDA $2140` / `CMP $2140` / handshake en el bit 7 de `$4A`,
escrituras a `$2141/$2142`, `INX INX INX`, `CPX $00`).  Es decir: la subida al
SPC **sí** ocurre fuera del boot (el «APU muerto» de §15.5 era solo la ventana
del boot), y lo que falta son los **~84 frames de esperas que no tocan el APU**
(62+22), la firma de una descompresión S-DD1 que en hardware se espera y en el
recomp (`sdd1.c`) se resuelve dentro de la llamada de host.  Hipótesis 1 de
§15.9, ahora cuantificada: el mismo trabajo cuesta 22 frames en el recomp y 124
en hardware.

Cierre pendiente (medido en parte en §17.2): contar lecturas de `$4800-$4807` y
`$4212` en hardware durante fr 718-779 con `tools/mesen_intro_probe.lua`; si ahí
no hay lecturas SDD1, la espera es otra (delays/bucles del invitado) y hay que
buscar su contador.

### 16.7 Lanzador forense: entrada reproducible

`run_dev_forense.bat` añade ahora `SNESRECOMP_INPUT_LOG=logs/input_manual.log`
(registrador pasivo, borra la sesión anterior al arrancar): cada partida jugada a
mano queda grabada por frame de invitado, de modo que un cuelgue se puede
repetir tal cual con `SNESRECOMP_REPLAY_FILE=logs/input_manual.log` (misma
clave: `snes_frame_counter`, que es como se graba).

## 17. El hueco de carga, medido por dentro (2026-09-28, noche)

### 17.1 Sonda nueva: lecturas de registro por frame (`SNESRECOMP_RDCOUNT`)

Los bucles de espera del invitado son **lecturas** («¿ya está listo?»), no
escrituras, así que ni `SNESRECOMP_WLOG_ADDR` ni la traza de puertos APU bastaban
para ver esperas sobre otros registros.  Añadida en `cpu_state.c`:

```
SNESRECOMP_RDCOUNT="4800-4807,4212-4213,2140-2143"   # rangos hex, hasta 6
SNESRECOMP_RDCOUNT_FILE=logs/rd_count.log           # opcional
```

Una línea por frame **solo si hubo accesos**:
`f<frame> master=<clk> <función AOT> $ADDR=<n>/<último valor> …`.  Los enganches
van en `cpu_read8`/`cpu_read16`, que es por donde lee **tanto el intérprete como
el código AOT** (el generado no llama a `ReadReg`: 651 usos de `cpu_read8` y 44
de `cpu_read16` en `generated/`, cero de `ReadReg`).  Coste cero sin la variable.

### 17.2 Estructura del hueco en el recomp (repetición fiel de la corrida del usuario)

`rep_bueno.txt` reproduce la corrida buena del usuario (gf y `inidisp` con ±1
frame).  Con la sonda puesta, el hueco `f82-f107` (26 frames de force blank) se
descompone así:

| frames | `$4212` | `$2140` | `$4800-$4807` |
|---|---|---|---|
| 60-66 | 103/frame | 0 | `$4806`/`$4807` 1/frame |
| 67-81 | 3/frame (fade-out, pad con A) | 0 | ídem |
| **82** | 0 | 4 | **`$4806` 02→04, `$4807` 03→05** |
| 83-102 | **0** | 1.262-55.402/frame | ídem (valor nuevo) |
| 103-107 | 0-2/frame | 0-2 | ídem |
| **104** | 10/frame | 0 | **`$4806` 04→02, `$4807` 05→03** |
| 107-… | 58/frame (fade-in lento) | 0 | vuelta al valor viejo |

Dos hechos nuevos y sólidos:

1. **El cambio de página MMC de la S-DD1 (`$4806`/`$4807`) abraza exactamente el
   hueco**: se cambia en `f82`, justo antes de la subida al SPC, y se restaura en
   `f104`.  Es la primera evidencia *dentro del recomp* de que el tramo es una
   carga de S-DD1 y no un simple delay.
2. El invitado del recomp **nunca lee `$4800`/`$4801`** (habilitación/estado del
   chip) en 950 frames: cero accesos.  Sondear el chip por `$4800-$4803` **no**
   es lo que llena los 62 + 22 frames de hardware; el candidato que queda es el
   acceso a la ventana MMC (`$4804-$4807`) y/o el tiempo de la propia DMA.

### 17.3 Refutado con A/B: la fast-forward de vblank no es la culpable

`SNESRECOMP_NO_VBLANK_FF=1` contra default, misma entrada (`rep_bueno`, 260
frames, ventana + audio): **timeline de transiciones de `inidisp` idéntica
byte a byte** (46 transiciones en ambos, hueco `f82-f107` = 26 frames en los dos
casos).  Igual que en §15.4, pero ahora en el escenario del menú.  No se toca el
driver.

### 17.4 Nota de aritmética: el hueco *no* es siempre de 26 frames

El mismo binario da huecos distintos según la corrida: `rep_bueno` (entrada real
parcial) → **26** frames; una corrida anterior con `rep_menu2` → **~123** frames
(≈ hardware 124).  Por eso cualquier comparación futura tiene que fijar primero
la corrida (misma entrada, misma ventana/audio) y solo entonces comparar.

### 17.5 Trampas reales de la sonda de Mesen (dos, ambas silenciosas)

La sonda no dejaba ninguna huella por **un error de sintaxis mío**:
`function(/*addr, value*/)` en la línea 310 — Lua no tiene comentarios `/* */`,
así que el fichero no compilaba y no se ejecutaba *nada* (ni el beacon inicial).
Lección: la primera línea ejecutable del script debe escribir en disco.

Segunda trampa, encontrada al extraer la documentación de la API que va
**incrustada en `Mesen.exe`**: el orden real es

```
emu.addMemoryCallback(callback, callbackType, startAddress,
                      endAddress=start, cpuType=snes, memType=snesMemory)
```

Pasar `memType` en la 3ª posición **no falla**: el enum 0 también es un `cpuType`
válido (`snes`), así que registra un rango equivocado en silencio.  La sonda
prueba ahora primero la forma de 4 argumentos y deja la de `memType`-tercero la
última.  Enums confirmados (orden documentado): `callbackType` read=0, write=1,
exec=2; `eventType` nmi=0, irq=1, startFrame=2, endFrame=3, reset=4,
scriptEnded=5; `memType.snesMemory=0`; `cpuType.snes=0`.

Otras firmas verificadas: `emu.stop(exitCode)`, `emu.getRomInfo()` →
`{name, path, fileSha1Hash}`, `emu.getScriptDataFolder()`, `emu.read(address,
memoryType)`.  Y dato de compatibilidad: el `Mesen.exe` del usuario (jun-2025,
70 MB, el del acceso directo) contiene la cadena `DD1` una vez; el S-DD1 entró en
Mesen-S 0.3.0, así que el oráculo **sí** emula el chip.

`tools/mesen_ping.lua` (nuevo) es la prueba mínima: escribe un beacon al cargarse
y una línea cada 60 frames.  Si el ping no deja rastro, el problema es el lanzado
del script, no el probe.

## 18. Boot de hardware desde el frame 1 y A/B contra el recomp (2026-09-29)

El usuario trajo `mesen_intro_probe.tsv` a `StarOceanRecompDocumentacion`.  Es la
primera traza **fiable** de la sonda: en `mesen_intro_probe_status.log` hay 4
sesiones y solo las dos últimas (`20:33:13` y `20:43:07`) usan la forma de
registro correcta `formas=1(...)`; las dos primeras (`2(...)`, con `memType` en
3ª posición) capturaban basura: por eso aparecían `ini=C8+F4+25+E0+…` (bytes de
ROM leídos como si fueran escrituras a $2100).  El TSV en disco es de la sesión
`20:43:07` (comprobado: `fr720 pc=000557` y `fr1200 E4=48` coinciden con las
líneas de progreso de esa sesión).

### 18.1 Orden de columnas del TSV (la cabecera miente; el código manda)

`mesen_intro_probe.lua:246-261` escribe `… ini x <fmt_rd()> <sombras>`:

| col | contenido real |
|---|---|
| 1-10 | `fr master pc D DB E4 E5 DA AFB AFD` (snapshots `emu.read`, **fiables**) |
| 11 `ini` | valores escritos a `$2100` por la CPU ese frame |
| 12 `x` | exec por dirección vigilada en ese frame |
| **13** | **LECTURAS** `r4800=…,r2140=…` (la cabecera la llama `writes`) |
| **14** | **sombras escritas** `DA=… E4=… AF9=…` (la cabecera la llama `reads`) |

La cabecera del propio `.lua` ya está corregida.  **Trampa medida:** los
callbacks de escritura a WRAM ($00DA/$00E4/$0AFB/$0AFD) solo se disparan de vez
en cuando (en 2000 frames: **2**), así que la columna 14 está infra-registrada y
no sirve para reconstruir la timeline; las columnas 1-10 (snapshot) sí.  Las
escrituras a *registros* ($2100, $2140-$2143) sí se capturan bien.

Otra limitación: `pc` es solo el PC de 16 bits, **sin banco**, así que
`pc=00053E` puede ser WRAM (`K=$00`) o ROM (`K=$C0`/`$C3`).  No sirve para
comparar PC contra el `resume` del recomp (que sí es de 24 bits).

### 18.2 Timeline de hardware, fr1..2000, desde reset y **sin input**

| tramo | frames | `DA` | `E4` | `AFB` | `AFD` | qué es |
|---|---|---|---|---|---|---|
| fr1-75 | 75 | 0F | BA | 01 | 004E | basura de arranque (WRAM sin inicializar) |
| fr76-85 | 10 | 00 | 00 | 01 | 004E | apagado |
| **fr86-818** | **733** | **80** | 00 | 00 | 0000 | **1ª carga S-DD1** (gráficos del logo Enix) |
| fr819-840 | 22 | 00 | 00 | 00 | B073 | negro, ya sin force blank |
| **fr841-900** | **60** | **01→0F** | 0→0x3B | 01→0x3C | B073 | **fundido de entrada: 4 frames por nivel** |
| fr901-1169 | 269 | 0F | 1/frame | 1/frame | B073 | logo Enix en pantalla |
| fr1170-1176 | 7 | 0F→01 (−2/frame) | congelado 0x48 | 8C | B073 | fundido de salida |
| fr1177-2000 | 824+ | 80 | **0x48 congelado** | **0x8C congelado** | B073 | 2ª carga S-DD1 (logo Triace) |

Reglas extraídas (todas verificadas con Python sobre las 2000 filas):

* **`DA = 1 + ($E4 >> 2)`** durante el fundido de entrada: `$E4` es un contador
  de **1 por vblank** y el brillo avanza **1 nivel cada 4 contadores**.  A
  fr897 `E4=0x38` (56) y `DA=0x0F` (15) → `1+56/4 = 15`. ✓
* `$E4` cuenta 1/frame desde fr842 y **se congela en 0x48 desde fr1169** (con el
  fundido de salida hecho con `DA`, no con `$E4`: por eso el fade-out no lo mueve).
* `$AFB` cuenta 1/frame desde fr841 y se congela en **0x8C** (~fr980).
  `$AFD` pasa a **0xB073** en fr820 y ya no cambia en 1400 frames.
* `$4212`: no estaba en los rangos vigilados (hueco de la sonda, ya añadido como
  `r4212`).  Sí se ve `$4800-$4807`: **2 lecturas por frame en 1881/2000
  frames** (último valor siempre `03`) → el invitado sondea la S-DD1 en *cada*
  frame, también durante las cargas.  `$2140-$2143` se sondea solo en ráfagas
  (fr11-76 arranque del SPC, fr405-415, fr778-815, fr1731-1741; ~330-450 frames
  entre ráfagas) y esas ráfagas coinciden **exactamente** con los tramos en que
  `D=$2100` (fr63-72, 408-414, 792-799, 801-804, 806-814, 1734-1740): el
  handshake con el SPC usa el truco del direct page en $2100.
* **La CPU escribe `$2100` solo 4 veces en 2000 frames** (fr2, fr76, fr86 con
  `80+0F+80`, fr1213), pese a que `DA` recorre **15 niveles**.  Es decir: los
  fundidos **no** salen por escrituras de CPU a `$2100` visibles al callback.
* Exec vigilado: la biblioteca `C8:F4xx` casi no se usa (C8:F407 en fr249/403/
  530-561/1414/1575/1729/1856-1864, y C8:F41D+F4D0+F4D4 una sola vez en fr415 y
  fr1741); **el motor de cutscenes del banco `$CC` no se ejecuta ni una vez** en
  2000 frames; `C0:2AE0` ejecuta 1 vez en fr818.

### 18.3 Qué es de verdad la biblioteca `C8:F4xx` (desensamblada)

`python tools/dis_range.py C8:F3F0 C8:F540` da el código real:

```
C8:F407  JSR $F407 = esperar 1 vblank exacto
             F40F: LDA $4212 / BMI F40F     ; espera bit7 = 1
             F414: LDA $4212 / BPL F414     ; espera bit7 = 0
C8:F41D  esperar 1 vblank + mirar el pad ($4218 → $C1)
             CLC = sin pulsación nueva,  SEC = hay pulsación nueva
C8:F497  fade-in  DE 1 NIVEL POR FRAME (JSR $F407)          → 15 frames
C8:F4AB  esperar A frames (no toca $2100)
C8:F4B7  fade-out DE 1 NIVEL POR FRAME y luego $2100=$80
C8:F4D0  fade-in  DE 1 NIVEL POR FRAME, abortable con el pad (JSR $F41D)
C8:F4E9  igual que F4D0 pero hacia abajo
```

Conclusión firme: **la biblioteca es 1 nivel/vblank**, así que el fundido lento
de hardware (4 frames por nivel, fr841-900) **no** es esa biblioteca: lo hace
código con la fórmula `DA = 1 + ($E4>>2)` (el PC de esos frames está en una
copia en RAM, 5 bytes, `$00053E..$000542`, que es `LDA $4212 / BPL` = la espera
de vblank; el paso del nivel va aparte).

### 18.4 A/B: recomp con `rep_bueno` y sin input, hasta el frame 2100

Corrida reproducible (log en `build-dev/Release/logs/fstate_rep_bueno_err.log`):

```
SNESRECOMP_REPLAY_FILE=rep_bueno.txt SNESRECOMP_FRAME_STATE=1
SNESRECOMP_EXIT_AT_FRAME=2100 SNESRECOMP_RDCOUNT="4800-4807,2140-2143,4212-4213"
```

Comparador: `python tools/ab_boot.py eventos|ventana|lecturas`.

**Lo que coincide** (y desmonta la conclusión estrella de §15.1):

* `$E4` cuenta **1 por frame** también en el recomp.
* **La fórmula es idéntica**: en el fundido del recomp `f107-f163`,
  `E4=0x01…0x38` y `DA = 1+(E4>>2)` (`E4=4→DA=2`, `E4=8→DA=3`, `E4=0x38→DA=0x0F`).
* Y el registro real `inidisp` avanza **1 nivel cada 4 frames** durante ese
  fundido.  El contador de cadencia **no está roto** en el recomp.
* `$4800-$4807`: **2 lecturas por frame** (una de `$4806`, una de `$4807`), el
  mismo ritmo que hardware; los valores `02/03` cambian a `04/05` en `f82-f103`
  y vuelven (hardware solo muestra el último valor del rango, `03`, constante).
* El *porqué* el hueco del recomp dura 26 frames y el de hardware 733 no es el
  sondeo: el invitado sondea en ambos casos 2 veces por frame; en el recomp el
  chip contesta «listo» de inmediato.  Es duración de la transferencia, no
  frecuencia de sondeo.

**Lo que diverge:**

| | hardware | recomp |
|---|---|---|
| 1er fundido de entrada | fr841-900, **4 frames/nivel** (60 frames) | f5-18, **1 nivel/frame** (14 frames) |
| rutina del 1er fundido | código propio (`DA=1+($E4>>2)`) | biblioteca `C8:F4D0` (1 nivel/vblank, abortable) |
| duración de la 1ª carga | **733** frames | ~18-26 frames |
| 2º fundido de entrada | — | f108-163, **4 frames/nivel** ✓ |
| `$4212` por frame | `103` (espera de vblank; oráculo viejo) | `103` (f11-66), 8460 (f4-10), 58 (f107-162) |

Es decir: el recomp **sí sabe** hacer el fundido a 4 frames/nivel (lo hace en su
2º fundido, byte a byte igual que hardware) pero en el **1º** entra por la rutina
de biblioteca de 1 nivel/frame.  La consecuencia observable para el usuario es la
misma que describía §15.1, pero la causa no es «el contador de cadencia» sino
**qué rutina de fundido elige el invitado**, y eso depende del estado que deja la
carga del S-DD1 (que en el recomp es 28× más corta).

### 18.5 Herramientas nuevas de esta sesión

`tools/intro_tsv.py` (analiza el TSV; `resumen|tramos|fades|ini|lecturas|ventana`),
`tools/ab_boot.py` (A/B hardware vs `[fstate]`), `tools/rd_profile.py` (perfil de
`rd_count.log`), `tools/lua_balance.py` (comprueba el balance de bloques Lua:
`function/if/for/while/do/repeat` contra `end/until`, la trampa que dejó la sonda
muda días).

## 19. Alineación por reloj de invitado y el estado real de la S-DD1 (2026-09-29)

### 19.1 El oráculo viejo NO era basura: su columna `inidisp` eran las escrituras a $2100

`mesen_oracle.tsv` son **dos pasadas concatenadas** (salto `fr 11788 -> 411`) de la
**misma** corrida determinista (mismo `master` en el mismo `fr`: fr820 =
292632288 en las dos).  La columna `inidisp` no es un snapshot del registro: son
los **valores escritos a $2100** ese frame (`80`, `00+80`, `81+01+00+00`...), y por
eso está vacía en los frames sin escritura.  Sosteniendo el último valor sale la
lineal temporal **real de pantalla** de hardware:

| tramo | frames | $2100 |
|---|---|---|
| fr416-430 | 15 | fade-in **a 1 nivel/frame** → 0F |
| fr431-702 | **272** | 0F (contenido) |
| fr703-716 | 14 | fade-out a 1 nivel/frame → 01 |
| fr717-841 | **125** | 80 (force blank) |
| fr842-897 | 56 | fade-in **a 4 frames/nivel** → 0F |
| fr898-1165 | **268** | 0F (contenido) |
| fr1166-1172 | 7 | fade-out a **2 niveles/frame** |
| fr1173-1212 | 40 | 80 |
| fr1213-…   |    | fade-in a **2 niveles/frame** |

Confirmado con el desensamblado: la fase de 272 = **240 + 32**, que es exactamente
el reproductor de logos `C8:F7xx` (`LDA #$0064 / JSR $F4E9` = 100 frames,
`LDA #$008C / JSR $F4E9` = 140, y su bucle de `LDA #$20` = 32).  O sea: el
"hueco de 124" de §15.1 era correcto, y la lectura del `$DA` de la traza nueva
(733 frames de 80) **no** es la línea de pantalla: `$DA` es la sombra que usa
*otra* ruta de fundido, no el registro.

### 19.2 La sonda nueva infra-captura las escrituras a $2100

`mesen_intro_probe.tsv` tiene `ini` (escrituras a $2100) en solo **4 frames**
(fr2, 76, 86 con `80+0F+80`, 1213), mientras el oráculo viejo sí captura las
rampas enteras.  Es decir: el callback de **escritura** a `$2100` de la sonda
nueva está roto, y el de **lectura** funciona.  Consecuencia práctica: para
$2100 vale el oráculo viejo; para `$DA/$E4/$0AFB/$0AFD` y las lecturas vale la
sonda nueva.  (Las lecturas de `$C1` y `$1E` en el recomp se hacen con
`SNESRECOMP_WLOG_ADDR`.)

### 19.3 El pad aborta las esperas temporizadas (`$1E` == 0 y `$4218` != 0)

Desensamblado de `C8:F41D` (usado por `F4D0`/`F4B7`/`F4E9`):

```
F425: LDA $4212 / BMI F425      ; espera vblank
F42A: LDA $4212 / BPL F42A      ; espera fin de vblank
F433: BIT $4212 / BNE F433      ; espera fin del auto-joypad
F43A: LDA $1E  / BNE F445       ; $1E != 0  -> CLC (NO aborta: protege el fundido)
F43E: LDA $4218 / STA $C1 / BNE F449   ; $4218 != 0 -> SEC (ABORTA: el juego
                                        ;            deja saltar logos con el pad)
```

Medido en el recomp con `SNESRECOMP_WLOG_ADDR=C1:C1` + `rep_bueno.txt`: en **f66**
`$C1 = 0x80` (o sea `$4218 = 0x80`) y `rep_bueno.txt` tiene `66 0100` = A pulsada.
**El recomp obedece al pad y salta el logo, como debe.**  Por eso la corrida con
`rep_bueno` parece "comprimir" las fases de contenido (49 frames frente a 272):
no es un fallo, es que mi A/B comparaba una corrida **con** pulsaciones contra un
hardware **sin** ellas.  Regla: para comparar fases usar la corrida **sin input**.

### 19.4 El método correcto de alineación: el reloj master

El recomp avanza **exactamente 357368 de master por frame** en régimen estable, el
mismo valor que hardware (`mesen_intro_probe.tsv`: fr810 -> fr811 =
357368).  Y el `master` de las dos trazas es comparable: el recomp alcanza
292632288 en **f739**, que en hardware es **fr820**.  Así que la alineación se
hace por reloj de invitado, no por índice de frame:

| evento | hardware (master) | recomp (master) | déficit |
|---|---|---|---|
| arranque de la 1ª carga | fr86 = 30.325.644 | f4 = 23.586.292 (66 frames en 1 host) | — |
| fin de carga / inicio fade-in | fr416 = 148.257.084 | f5 = 23.943.678 | **124,3M = 348 frames** |
| inicio de contenido 1 | fr431 = 153.616.764 | f19 = 28.922.812 | 124,7M = 349 |
| inicio fade-out 1 | fr703 = 250.813.540 | f150 = 75.762.020 | 175,1M = 490 |
| inicio force blank 1 | fr717 = 255.816.724 | f164 = 80.765.244 | 175,1M = 490 |
| inicio fade-in 2 | fr842 = 300.494.340 | f166 = 81.479.980 | 219,0M = 613 |
| inicio contenido 2 | fr898 = 320.506.840 | f180 = 86.482.532 | 234,0M = 655 |

El déficit **crece** en cada carga (348 -> 490 -> 613 -> 655 frames): no es un
offset constante, es tiempo que se pierde en **cada** transferencia.  El orden de
eventos y el tipo de cada fundido sí coinciden.

### 19.5 La S-DD1 no entrega ni un byte en el recomp (causa medida del déficit)

`sdd1_dma_get_byte` y la vía de lectura de CPU exigen `r4800 & r4801 & (1<<canal)`.
Medido con `SNESRECOMP_WLOG_ADDR=4800:4801` y sin input:

```
f3  00:4800=01   IPC=C8F974     <- hard enable
f3  00:4801=01   IPC=C8F99A     <- soft enable
f3  00:4800=00   IPC=C8F9A2     <- ...y se apaga
(no hay más escrituras en 120 frames)
```

`$4800` acaba en **00** y no se vuelve a tocar: **el chip queda deshabilitado y las
dos vías de descompresión no sirven ni un byte** (medido con el contador nuevo,
`SNESRECOMP_SDD1STATS`: 0 bytes en 120 frames).  El invitado sigue haciendo
read-modify-write de `$4806`/`$4807` (2 lecturas por frame, igual que hardware),
pero el chip no produce datos: los datos salen del ROM crudo por
`sdd1_mmc_read`.  En hardware, en cambio, `$4806`/`$4807` **se escriben**
(cambian de 02/03 a 04/05 al enmarcar el hueco), o sea que el invitado sí maneja
el chip.

Instrumento añadido (dev, coste cero sin la variable): `SNESRECOMP_SDD1STATS=<ruta>`
emite una línea por frame con los bytes entregados por cada vía
(`dma=`, `cpu=`, `total=`).  Es lo que convierte la tasa del chip en duración:
`ciclos-por-byte = ciclos de invitado medidos en hardware / bytes que el invitado
pide`.  Primera cifra de referencia: la 1ª carga de hardware dura 733 frames =
**261.949.280** ciclos de master.

### 19.6 Estado de las dos tareas

* **Tarea 1 (por qué el recomp elige otra rutina de fundido)**: mecanismo
  identificado —ambos lados usan las *dos* clases de fundido y en el mismo orden;
  el recomp hace el lento (`DA = 1 + ($E4>>2)`, 4 frames/nivel) con una rutina del
  banco **$C3** (`resume` C3:8F5E/C3:8FA8/C3:9083) en su 4º fundido, y usa la
  biblioteca `C8:F4xx` (1 nivel/vblank) en el 2º—, pero **el selector no está
  demostrado todavía**.  Con la carga arreglada (tarea 2) las dos trazas quedarán
alineadas 1:1 y el selector se verá con un simple diff.
* **Tarea 2 (duración de la S-DD1)**: causa demostrada y acotada (el chip no
  entrega bytes en el recomp), instrumento de medida en su sitio, y la constante
  a calibrar sale de 261.949.280 ciclos / bytes.  **Falta**: (a) decidir si el
  modelo correcto es costar la transferencia (la curva de déficit dice que sí) o
  mantener el chip "no listo" para que el bucle del invitado dé más vueltas;
  (b) leer el bucle de carga del invitado, que es quien convierte tiempo de chip
  en frames (los PC medidos: `C8:F41x/F42x` = esperas de vblank, `C0:4D5x` =
  descompresor propio, `C8:F5xx` = copias de tilemap, `C0:86xx` = arranque).  El
  camino se abre con `SNESRECOMP_SDD1STATS` para saber cuántos bytes por frame
  pide el invitado en cada tramo.

### 19.7 CORRECCIÓN (2026-09-29, noche): el hueco de carga NO es 28× más corto

`tools/ab_master.py` alinea las dos trazas por **reloj master** (357.368 por frame
en ambos lados) en vez de por índice de frame.  Con la alineación buena, la
conclusión de §19 cae: el recomp **sí** pasa ~730 frames de invitado dentro del
bucle de espera de vblank de la biblioteca `C8:F425/F428` —el mismo sitio que el
hardware—, no 22.  Lo que descolocaba el A/B era el arranque: el recomp ejecuta
~66 frames de invitado dentro de sus 4 primeros *host* frames, así que `f_recomp
!= fr_hardware` y toda tabla indexada por frame comparaba fases distintas.

Equivalencia medida (master → frame de invitado):

| master | gf | recomp | hardware |
|---|---|---|---|
| 23.586.292 | 66 | `f=4`, arranca aquí el reloj por frame | `fr66`: aún en boot |
| 30.325.644 | 85 | `f=23` | `fr86`: empieza la carga |
| 292.632.288 | 819 | `f=757` | `fr820`: fin de la carga |

Es decir: los dos pasan por `C8:F41x/F42x` durante la carga y durante el mismo
tramo de reloj.  **La duración de la transferencia S-DD1 no puede ser la causa
del desfase del fundido** y no hay que inventarle un modelo temporal al chip:
sería un parche heurístico sobre un hueco que no existe.

### 19.8 La divergencia real: el recomp ejecuta OTRA fase del programa

Lista de **escrituras reales a `$2100`** de los dos lados, alineada por master.
Hardware = 15.732 eventos únicos del oráculo viejo (`mesen_oracle.tsv`,
`fr416..11701`, la única fuente que captura bien el registro).  Recomp = 290
escrituras instrumentadas con `SNESRECOMP_INIDISP_TRACE=1` (900 frames).

HARDWARE (ritmo por frame, `delta` entre escrituras consecutivas de frames
seguidos):

| gf | fr | delta | valores |
|---|---|---|---|
| 415 | 416-430 | **+1** | 01→0F (subida rápida, 15 frames) |
| 431-702 | 431-702 | — | **272 frames sin escribir** (= 240 + 32) |
| 702-715 | 703-717 | **−1** | 0E→00, luego `80` |
| 716-841 | 718-842 | — | 126 frames (una sola escritura: `80` en fr777) |
| 841-898 | 842-898 | **+1 cada 4 frames** | 01,01,01,01,02,02,02,02,…0F (57 frames) |
| 899-1165 | 899-1165 | — | logo Enix (267 frames en `0F`) |
| 1165-1171 | 1166-1172 | **−2** | 0D→01 |
| 1172 | 1173 | — | `80` (2ª carga) |

RECOMP (por `pc` que escribe; el fichero es del run **sin input**):

| gf | f | pc | patrón |
|---|---|---|---|
| 66-80 | 4-18 | `C8F4DE` | **+1/frame** 01→0F |
| 81-210 | 19-148 | — | 130 frames de contenido |
| 211-225 | 149-163 | `C8F4C5` + `C8F4CC` | **−1/frame** 0E→00, luego `80` |
| 227-241 | 165-179 | `C8F4DE` | +1/frame otra vez |
| 242-361 | 180-299 | — | 120 frames |
| 362-376 | 300-314 | `C8F4C5` | −1/frame |
| … | | | **ciclo de ~145 gf que se repite** |
| (188 escrituras) | | `CC280E` | sincronización `LDA $DA / STA $2100` |

Dos diferencias independientes, ninguna de ellas de cadencia del contador:

1. **El recomp está en otra fase del programa.**  Hardware hace *un* ciclo
   rápido (subida 15 f) + 272 de contenido, y la subida **lenta** (4 f/nivel)
   es la del segundo fundido.  El recomp hace ciclos subida/bajada de 15 frames
   encadenados desde gf66, con fases de contenido de ~125.  No es que el
   invitado avance 4× rápido: es que **está ejecutando otro tramo del guion**
   (por eso §19 veía "el 4º fundido" del recomp donde hardware va por el 2º).
2. **El recomp arranca los fundidos ~350 gf antes** que hardware (gf66 vs
   gf416) mientras su `$DA` (sombra WRAM) ya vale `80`, es decir: mantiene la
   pantalla en blanco forzado en el *shadow* pero **no** en el registro real
   (escribe `0F` y lo deja ahí ~300 frames).  Hardware tiene `$2100=80` de
   fr86 a fr415.

### 19.9 RETRACTADO: el recomp SÍ sondea la S-DD1 una vez por frame

Esta sección afirmaba, con `SNESRECOMP_RDCOUNT="4800-4807,2140-2143,4212-4213"`
sobre el run sin input, que el recomp **nunca** lee `$4800-$4807` (0 en 2098
frames) mientras hardware lo lee 2/frame, y concluía que era divergencia de
flujo.  **Es falso: era un error de análisis mío, no del recomp.**  Dos fallos
encadenados del lado del analista:

1. **Parser.**  Busqué el campo con la subcadena `4800=` cuando el instrumento
   emite **una entrada por registro** (`$4806=1/02 $4807=1/03`), no un agregado
   del rango.  `grep -c 4806` sobre el mismo `rd_noinput.log` da **2096 líneas**:
   las lecturas estaban ahí desde el principio.
2. **Cap de visualización.**  La primera versión de la sonda de PCs (§19.13)
   imprimía solo 240 líneas; con `$C8F42A` consumiéndolas salían "1 acierto"
   para todo lo demás, y lo leí como "se ejecuta una vez".  Contaba bien pero
   imprimía mal: un instrumento con cap miente por omisión.

Medición correcta (build actual, `SNESRECOMP_RDCOUNT="4800-4807"`, 30 frames):

```
f4  master=23944466  $4806=1/02  $4807=1/03
f5  master=24301828  $4806=1/02  $4807=1/03
... 26/30 frames con exactamente las mismas dos lecturas
```

Es decir: **1 lectura de `$4806` + 1 de `$4807` por frame, valores 02 y 03** —
idéntico a hardware (2 lecturas/frame, último valor `03`, que es la página MMC
por defecto que el cargador restaura).  **No hay nada que arreglar aquí.**

Y la rutina que las hace está identificada: `C0:032D` es la **bomba por frame**,
que se ejecuta **una vez por frame** desde el handler de V-IRQ
(`C0:0251 JSR $032D`, dentro del handler que acaba en `RTI` en `C0:025E`), con
**DBR = $00** en el punto de la lectura, exactamente como hardware.  Su tail
incondicional en `C0:0387` es: guardar la página MMC actual (`LDA $4806`,
`LDA $4807`), ponerla a 4/5, y llamar a los descompresores (`JSR $03B4`,
`JSR $05E5`) según los flags de `$50`.  La bomba también es el tick del driver
de sonido (escribe `$2140-$2143` cuando hay comando pendiente en `$90`/`$91`).

**Consecuencia para §19.5**: la frase «el chip queda apagado y `sdd1_dma_init`
rechaza las sesiones» queda en entredicho — el camino por-frame del chip está
vivo.  Antes de volver a apoyarse en ella hay que re-medir las **escrituras** a
`$4800` con el mismo cuidado (el `WLOG_ADDR` usado entonces no cubre el camino de
registro: `wlog_addr_note` solo se llama en la rama WRAM, `cpu_state.c:607`).

### 19.10 Mapa completo de la biblioteca `C8:F4xx` (desensamblada)

```
C8:F407  esperar 1 vblank exacto (LDA $4212/BMI, LDA $4212/BPL)   [9 llamadas]
C8:F41D  esperar 1 vblank + mirar pad -> CLC sin pulsacion / SEC con pulsacion
         (solo si $1E==0);  el bucle caliente es F425(LDA $4212)/F428(BMI)
C8:F497  fade-in  1 nivel/vblank (STZ $00; INC A; STA $2100; CMP #$0F)  [2]
C8:F4AB  espera N vblanks: A -> $00, DEC $00 hasta 0 (sin pad)
C8:F4B7  fade-out 1 nivel/vblank 0F..00 y despues $2100=80          [6]
         cuerpo en F4C5 (STA $2100) / F4CC (LDA #$80; STA $2100)
C8:F4D0  fade-in  1 nivel/vblank ABORTABLE por pad, cuerpo en F4DE   [12]
         (JSR $F41D; BCS salir con SEC)
C8:F4E9  espera N vblank ABORTABLE (A=16 bits -> $00)                [4]
C8:F4FA  fade-out ABORTABLE
```

Confirmado: los PC que aparecen como `pc` en las escrituras del recomp
(`C8F4DE`, `C8F4C5`, `C8F4CC`) **no tienen llamada directa** en la ROM: son los
cuerpos de bucle de `F4B7` y `F4D0` alcanzados por caída.  Es decir, el recomp
usa el fade-in **abortable** (`F4D0`, 1 nivel/vblank) y el fade-out `F4B7`, y
completa los 15 niveles sin abortar: el pad no es la causa de la cadencia.

### 19.11 Herramientas nuevas de esta sesión

* `tools/ab_master.py` — A/B recomp↔hardware alineado por reloj master
  (`eventos` / `fases` / `ventana gf0 gf1`).  Es la única comparación válida.
* `tools/find_fade_calls.py` — lista todos los `JSR`/`JSL` de la ROM a un rango
  de la biblioteca (`python tools/find_fade_calls.py F400 F540`).
* `SNESRECOMP_INIDISP_TRACE=1` (ya existía, `ppu.c`) — escrituras reales a
  `$2100` con el PC: es el instrumento que faltaba para el lado recomp.
* **`SNESRECOMP_PCHIT="C0032D,C00387"`** (`interp816.c`, nuevo) — cuenta
  ejecuciones de pc24 exactos por el intérprete y las imprime con
  `frame=` y `DB=/DP=/S=` del invitado.  **Sin cap de impresión** (el cap fue
  justo el fallo de §19.9): cuenta siempre, y solo las *líneas* están
  acotadas; para saber el total hay que añadir un contador final si se necesita.
* **`DB`/`PB`/`DP`/`S` en la línea `[fstate]`** (`so_rtl.c`, nuevo) — sin esto
  no se puede distinguir «el invitado no lee el registro» de «lo lee con el
  banco de datos equivocado», porque un acceso absoluto con DB≠0 cae en
  WRAM/ROM y no pasa por `is_hw_reg`.  Hardware sostiene `DB=$00` en los 2000
  frames medidos; el recomp varía (00 645, C8 176, D7 32, 7F 18, C0 15, 7E 4
  en 900 frames) pero **en la bomba de la S-DD1 vale 00**, como hardware.

### 19.12 Estado revisado de las dos tareas

* **Tarea 1 (duración de la transferencia S-DD1)**: **no se implementa**, por dos
  motivos independientes ya medidos: (a) el A/B por reloj master muestra que el
  recomp gasta el mismo tiempo de invitado en el bucle de vblank que hardware, y
  (b) el sondeo por-frame del chip **ya ocurre** (1+1 lecturas de
  `$4806`/`$4807` por frame, valores 02/03, desde el V-IRQ).  No hay hueco que
  modelar: costar la transferencia sería un parche sobre algo que ya funciona.
* **Tarea 2 (más cobertura nativa / quitar trabajo al intérprete)**: las raíces
  AOT salen de `config/bankNN.cfg` (`func <name> <pc> end:<hex>`) y hoy son
  **6 bancos: 00, C0, C1, C2, C3, C9** (91 nodos / 75 raíces), y **casi todo
  está en `interp_tier_dispatch`**: `generated/bankc0_v2.c` y `bankc3_v2.c` no
  tienen ni una lectura emitida, solo despacho al intérprete.  Los bancos
  calientes de la intro —**C8** (biblioteca de fundidos + espera de vblank) y
  **CC** (motor de cutscenes, el que escribe `CC:280E`)— **no están ni listados**.
  El recompilador ya soporta *promoción por perfil* (`profile_promot` en
  `v2/codegen.py|decoder.py|emit_function.py`), así que el camino seguro es:
  perfil → añadir `func` a la cfg del banco → regenerar → build → A/B
  **byte-exacto** contra la huella WRAM de la build actual.  Los bancos C8/CC son
  los "delicados": ahí el intérprete define la frontera de frame (spin de
  sólo-lectura), y una función nativa mal delimitada cambia el modelo de frame,
  no sólo la velocidad.

### 19.13 Higiene de instrumentos (lección de esta sesión)

Tres mediciones de esta sesión resultaron falsas por el **instrumento**, no por
el sistema medido, y las tres costaron trabajo perdido:

1. `rd_noinput.log` «0 lecturas de `$4800-$4807`» → **regex equivocado** del
   analista (`4800=` en vez de `$4806=`).  Regla: antes de concluir "no ocurre",
   hacer `grep` de la **subcadena corta** en el fichero crudo.
2. «La bomba se ejecuta 1 vez» → **cap de 240 líneas** en la sonda de PCs.
   Regla: los contadores cuentan sin cap; solo la salida humana se acota, y hay
   que decir explícitamente que está acotada.
3. «El hueco de carga es 28× más corto» (§19) → **alinear por índice de frame**
   cuando el índice de los dos lados no empieza en el mismo sitio.  Regla ya
   escrita en §19.4: alinear por `master`.

### 19.14 Qué queda por medir (el bloqueo real)

La comparación de fundidos de §19.8 tiene un agujero que **no se puede tapar del
lado recomp**: el oráculo viejo (`mesen_oracle.tsv`), única fuente fiable de
escrituras a `$2100` en hardware, **empieza en fr411** (su primera pasada).  Y la
sonda nueva, que cubre fr1-2000, **infra-captura las escrituras a `$2100`** (4
eventos en 2000 frames frente a 16.090 del viejo).  Por tanto, del tramo
gf66-415 —justo donde el recomp arranca sus ciclos de fundido— **no hay traza de
hardware**.

### 19.15 Sonda v3: captura de `$2100` que se autodiagnostica (2026-09-29)

Diagnóstico del fallo: la sesión que grabó el TSV registró las escrituras con la
**forma 1** de `addMemoryCallback` (`cb, tipo, ini, fin`, defaults para
cpu/memType) y reportó `writes=8/8` — pero las **lecturas** con esa misma forma
sí disparan (1.973/2.000 frames) y las **escrituras** casi nunca (2 frames).  La
firma documentada en la API incrustada de `Mesen.exe` (extraída de
`F:\Recompilador Super Nintendo\Mesen\Mesen.exe`) es
`addMemoryCallback(callback, callbackType, startAddress, endAddress, cpuType,
memoryType)` con callback `(address, value)`, `read` llamado **después** de la
lectura y `write` **antes** de la escritura — no aclara el fallo, así que en vez
de suponer se mide dentro de la sonda.

`tools/mesen_intro_probe.lua` (v3) registra **tres vías en paralelo** y captura
`$2100` además por una cuarta independiente:

| vía | mecanismo |
|---|---|
| `m1` | callback de escritura, forma de 4 argumentos |
| `m6` | callback de escritura, forma de 6 argumentos explícita |
| `mMT` | callback de escritura, `memType` en 3ª posición |
| `x`  | **exec callbacks** en los **95 sitios de ROM** que almacenan en `$2100` (`STA`/`STX $2100` y `STA long`), leyendo el valor del acumulador |

La vía `x` no depende de la semántica de los callbacks de memoria: los exec
callbacks **están demostrados** en esta configuración (columna 12 del TSV viejo:
`C8F407=1` en 69 frames).  Los 95 sitios **no están escritos a mano**: los genera
`tools/gen_2100_sites.py` escaneando el ROM (79 `STA $2100`, 14 `STA long`,
2 `STX $2100`) y los injerta en el `.lua`.  Como control cruzado, los cuatro
sitios de boot del recomp (`C08088`, `C080D5`, `C081B4`, `C081B9` según
`SNESRECOMP_INIDISP_TRACE`) aparecen en esa tabla.

Además hay un **canario**: callback de escritura sobre la página de pila
(`$00:0100-$01FF`), que recibe escrituras constantemente.  Si el canario da 0,
ninguna captura de `$2100` por callbacks de memoria es creíble, y lo dice el
propio fichero de estado.

La columna 11 (`ini`) usa la primera fuente no vacía en orden de fiabilidad
`x > m6 > mMT > m1`, y la nueva columna 15 (`src`) lleva el desglose
(`x= pc= db= m1= m6= mMT= can1= can6=`).  **Todas las filas tienen 15 campos**
fijos: se dejó de omitir columnas vacías porque ese desplazamiento es justo lo
que hizo leer mal la traza anterior.

Corrida: `START_FRAME=1`, `END_FRAME=900`, salida `mesen_fades900.tsv` y
`mesen_fades900_status.log`.  Reglas: **una sola sonda cargada** y **no tocar el
pad** (aborta las esperas de `C8:F41D` y cambia el guion).

Herramientas de lectura:

* `tools/fades900.py <tsv>` — valida la autodiagnosis (qué vía trajo los datos,
  canario, `DB` de los almacenamientos) y emite los tramos de `$DA` con rangos
  de frames, en la misma forma que los ciclos del recomp.
* `SNESRECOMP_PROBE=<ruta> python tools/ab_master.py fases` — A/B por reloj master
  contra la traza nueva sin editar nada.
* `tools/lua_balance.py` — validador estático ampliado: además del balance de
  bloques, caza `/* */` y `//` de C, paréntesis/corchetes/llaves desbalanceados
  y caracteres no-ASCII (los dos `.lua` están ahora en ASCII puro).


## 20. Veredicto del A/B por reloj master sobre los fundidos (2026-09-29, tarde)

La traza `mesen_fades900.tsv` está **grabada** (900 filas, 15 campos todas) y
el A/B por reloj master ya está hecho.  Lector único: `tools/fades900.py`
(`--ab`).  Resumen de lo medido, en gf (frames de invitado, `master/357368`).

### 20.1 Fiabilidad de las columnas (leer esto antes que nada)

| columna | fiabilidad | motivo |
|---|---|---|
| `pc D DB E4 E5 DA AFB AFD` | **alta** | un `emu.read` por frame, sin callbacks |
| `ini` (11) | **nula** | el volcado de la vía `mMT` la tapa (`mMT=64` vs `m1=0`/`m6=0` por frame) |
| `x` (12), `wshadow` (13) | **baja** | los callbacks se registran por varias formas sobre el mismo PC/addr y **multiplican** |
| `src` (15) | informativa | los contadores `m1/m6/mMT/can` son acumulados y fiables como *prueba de disparo*, no como recuento |

Prueba dura de que la vía de escritura sigue rota: en `fr841..900` la columna
muestreada `$00DA` cambia **15 veces** (01..0F, 1 nivel cada 4 frames) y en
cambio la columna 14 (`wshadow`, callbacks de escritura sobre las sombras) sólo
registra **2 eventos en 900 frames** (`fr86: DA=80`, `fr841: DA=01 AF9=01 AFB=01`).
El canario de pila sí dispara (`can1=88015`), así que los callbacks de escritura
funcionan; lo que no funciona es la **atribución por frame**.  ⇒ Para juzgar
`$2100` en hardware hay que arreglar la sonda (§20.4).

### 20.2 Tramos de `$00DA` (sombras leídas por frame — dato fiable)

HARDWARE (sin input), 900 frames:

| fr | gf(master) | dur | `$00DA` | nota |
|---|---|---|---|---|
| 1..75 | 0..74 | 75 | `80` | |
| 76..85 | 75..84 | **10** | `00` | apagón corto (el recomp **no** lo hace) |
| 86..818 | 85..817 | 733 | `80` | carga; PC en `C8:F42x` (spin de vblank) |
| 819..840 | 818..839 | **22** | `00` | apagón antes del fundido (el recomp **no** lo hace); `$0AFD` pasa a `B073` en `fr820` |
| 841..900 | 840..899 | 60 | `01`..`0F` | 15 niveles × **4 frames**; `AFB=01..3C` (+1/frame); `E4=00..3B` (+1/frame) |

RECOMP (`fstate_noinput_err.log`, 2100 frames sin input):

| f | gf(master) | dur | `$00DA` | nota |
|---|---|---|---|---|
| 1..3 | 0 | 3 | `00` | boot |
| 4..711 | 66..791 | 708 | `80` | carga; `resume=C8:F42x` |
| 712..767 | 792..847 | 56 | `01`..`0E` | 15 niveles × **4 frames** |
| 768..2100 | 848..2180 | 1333 | `0F` | `AFB` se congela en `8C` al terminar |

**Identidad estructural, que no se había medido antes:** en los dos lados,
durante el fundido, `AFB = E4 + 1` exactamente y `DA = ceil(AFB/4)`.  Es decir el
guion de fundido es el mismo y la cadencia es idéntica.

### 20.3 Divergencias (esto es todo lo que difiere)

1. **gf 75..84** — hardware apaga `$00DA` 10 frames; el recomp mantiene `80`.
2. **gf 793..839** — el recomp empieza a fundir (`DA=01` en `f712` = gf 792)
   mientras hardware sigue en `80`.  Hardware no funde hasta **gf 840** (`fr841`).
3. **gf 818..839** — hardware hace su segundo apagón de 22 frames; el recomp ya
   está fundiendo (`DA=02..0C`).
4. Una vez que hardware empieza a fundir, ambos avanzan 4 frames por nivel, pero
   con ~47 gf de desfase fijo.

**Por qué el recomp llega 48 gf antes** (los 48 se descomponen):

* **32 gf**: los dos apagones cortos (10 + 22) que hardware ejecuta y el recomp
  no.  Es el hallazgo con consecuencias: el recomp **se salta el paso de apagar
  la pantalla** entre la carga y el fundido.
* **~16 gf**: el recomp consume **~2,4 % más de tiempo de invitado por frame
del host** durante la espera de carga.  Medido: de `f22` (gf 85) a `f712`
  (gf 792) pasan 690 frames de host y 707 gf ⇒ 1,0246 gf/host.  En el tramo de
  fundido la razón es exactamente 1,0 (de `f712` gf 792 a `f815` gf 896 = 103
  frames y 103 gf), así que no es un error de escala del reloj: es **el modelo de
  frontera de frame** el que deja pasar de más durante el bucle de espera.

### 20.4 Hipótesis refutadas por esta traza

* **"El recomp funde a 1 nivel/frame y hardware a 1 cada 4"**: **FALSO**.  Los
  dos son 15 niveles × 4 frames con `AFB=E4+1`.  El "1 nivel/frame" se había
deducido de `SNESRECOMP_INIDISP_TRACE` (escrituras crudas a `$2100`), que
  durante la carga cicla `C8F4DE` (01..0F) → `C8F4C5` (0E..00) → `C8F4CC` (80)
  cada ~150 frames.  Ese ciclo **no** mueve `$00DA` (por eso el shadow se queda
  en `80`), pero **tampoco es un artefacto del recomp**: los recuentos por sitio
  en hardware dicen lo mismo (la columna de sitios es fiable; la prueba de que
  no está multiplicada es `C8F4CC=3`, que no es múltiplo de nada):

  | sitio | hardware (900 fr) | recomp |
  |---|---|---|
  | `C8F4DE` (cuerpo del fade-in, `STA $2100`) | 45 = 3 segmentos × 15 niveles | 4 segmentos (3 rápidos + el lento final) |
  | `C8F4C5` (cuerpo del fade-out) | 45 = 3 segmentos × 15 niveles | 3 segmentos |
  | `C8F4CC` (fija `$2100=$80`) | 3 | 3 |
  | `CC280E` (aplicador por frame `LDA $DA/STA $2100`) | 59 | — |

  ⇒ El guion de fundidos de la carga **coincide**.  Lo que no coincide es el
  `$00DA` que los enmarca (§20.3).
* **"El recomp entra ~350 gf antes en el guion de fundidos"**: con la traza
  buena el adelanto es **48 gf (0,8 s)**, no 350.

### 20.5 El defecto real de la sonda v3 (y por qué `ini` era un volcado)

Dos fallos concretos, medidos sobre la propia traza y sobre el `.lua`:

1. **El reset de contadores estaba en `EV_STARTFRAME`, que en Mesen-SNES se
   dispara al *salir* de vblank.**  El juego escribe `$2100` **durante vblank**,
   así que `reset_frame_counters()` borraba del registro exactamente la ventana
   que se quería medir.  Consecuencia visible: los contadores `x`/`m6` del frame
   sólo recogen el trozo VISIBLE (de ahí los `C00230/C00387` de la IRQ), y
   `m6` acumula 161 disparos que nunca llegan a la fila.
2. **La "forma 4" de `addMemoryCallback` no es una variante válida.**
   `addMemoryCallback(cb, ctype, memType, start, end)` se interpreta como
   `(start=memType=0, end=$2100)`, o sea un callback sobre **todo**
   `$0000..$2100`.  Eso es lo que daba `mMT=251348` (≈279 disparos por frame) y
   hacía que `ini` fuese un volcado de escrituras de la RAM baja en vez del valor
   escrito a `$2100`.

Prueba cruzada de que las dos vías de byte único sí eran correctas: `m1=161` y
`m6=161`, y la suma de sitios de ROM da 152 (`59+45+45+3+1+1+1+1+1+1`).  161
escrituras a `$2100` en 900 frames.  Dato añadido de `m6=161`: **hardware sí
reescribe `$2100` unas 145 veces durante `fr86..818`**, o sea que el `$00DA=80` de
ese tramo es una sombra estancada, no el contenido real del registro.

### 20.6 Sonda v4 (aplicada, pendiente de una corrida)

En `tools/mesen_intro_probe.lua`:

1. **Fuera el reset en `EV_STARTFRAME`** (sólo se resetea después de escribir la
   fila, dentro de `on_end_frame`).
2. **Fuera la forma 4.**  La fuente de valor de `$2100` es sólo la forma 3
   (byte exacto, `$2100-$2100`); la forma 1 se conserva únicamente como
   contraste de rango sobre `$0000..$2100` (contadores `mA1`/`mA4`), nunca como
   valor.
3. `fmt_ini()` pasa a elegir entre `x > m6 > m1` (sin `mMT`).
4. **Salida nueva**: `mesen_fades900b.tsv` / `mesen_fades900b_status.log`, para
   que nadie mezcle esta corrida con la v3.

Lo que decide la corrida v4: el **valor** real de `$2100` en `fr76..85` y
`fr819..840` (los dos apagones que el recomp no hace) y si `$2100` en
`fr86..818` sigue el ciclo de `C8F4DE`/`C8F4C5` como ya se deduce del recuento
de sitios.  Si es así, lo único que queda por arreglar en el recomp son los
dos apagones y el sobrerrecorrido del ~2,4 %.


## 21. Sonda v4: el guion de fundidos COINCIDE; lo que falla es el reloj (2026-09-29, tarde-noche)

Corrida v4 en `mesen_fades900b.tsv` (900 filas, 15 campos, 161 escrituras a
`$2100` con sitio).  Comparador: `tools/fades_ab2100.py` (evento a evento contra
`SNESRECOMP_INIDISP_TRACE`).

### 21.1 La v4 funciona: `ini` ya es el valor real de $2100

Ejemplos literales de la traza, con el sitio de ROM que escribe:

| fr | sitio | valor | que es |
|---|---|---|---|
| 76 | `C08088` | `80` x2 | arranque del cargador |
| 86 | `C081B4` | `80`,`0F`,`80` | imagen del driver de sonido |
| 90..104 | `C8F4DE` | `01`..`0F` | **fade-in de 1 nivel/frame** |
| 235..249 | `C8F4C5` | `0E`..`00` | fade-out |
| 249 | `C8F4C5` | `80` | fuerza blank |
| 251..265 | `C8F4DE` | `01`..`0F` | fade-in |
| 386..400 | `C8F4C5` | `0E`..`00` + `80` | fade-out |
| 416..430 | `C8F4DE` | `01`..`0F` | fade-in |
| 703..717 | `C8F4C5` | `0E`..`00` + `80` | fade-out |
| 777 | `CC0E35` | `80` | blank final antes del fundido |
| 842..900 | `CC280E` | `01`..`0F` (4 frames/nivel) | fundido final de la intro |

Sitios de `$2100`: en las dos corridas el recuento es el de la tabla de §20.4 y
el canario da 87994.  `mA1` (contraste: escrituras en `$0000..$2100`) da 251328,
que es exactamente el `mMT` de la v3 ⇒ confirma que la forma 4 era un rango.

### 21.2 El guion es identico; solo fallan DOS esperas

Segmentos emparejados 1:1 (mismo sitio, mismo n):
`C8F4DE 01..0F n=15` ×3, `C8F4C5 0E..00 n=15` ×3, `80` tras cada fade-out,
`CC0E35`, y `CC280E` en 15 tramos de 4 frames.  Todo igual.

Huecos entre segmentos (frames de espera):

| hueco | hardware | recomp | delta |
|---|---|---|---|
| `C8F4DE`→`C8F4C5` | 131 | 131 | 0 |
| `C8F4C5`→`C8F4DE` | 2 | 2 | 0 |
| `C8F4DE`→`C8F4C5` | 121 | 121 | 0 |
| `C8F4C5`→`C8F4DE` | 16 | 11 | **-5** |
| `C8F4DE`→`C8F4C5` | 273 | 273 | 0 |
| **`C8F4C5`→`CC280E`** | **125** | **86** | **-39** |

⇒ El recomp ejecuta el **mismo guion** con la **misma cadencia**; se salta 44
frames de espera, 39 de ellos en el tramo final.

### 21.3 Que hace hardware en esos 39 frames (traza v4, columna `pc`)

La sonda imprime `%06X` de un PC de 16 bits, asi que **no hay banco**: los
digitos de delante son siempre `00`.  Lo util es el PC:

| fr | pc | que es |
|---|---|---|
| 777..779 | `0EB8`, `4D74` | salida del cargador |
| 780..791 | `86BA`..`86EF` | **bucle de subida del driver al SPC700**: lee `$7F:0000,X`, escribe `$2141`/`$2142`, handshake `CMP $002140 / BNE`, alterna `$4A`, `CPX $00 / BCC` |
| 792..814 | `892C`,`89A3`,…,`88E0` | resto de la transferencia |
| 815..818 | `242C`, `432F`, `F545`, `2654` (+`C02AE0`) | cierre |
| **819..840** | alterna `092x`-`096x` y `CE6x` | `C0:CE5F` es `LDA $08C3 / ASL / TAX / JSR ($CE6F,X)`: **despachador por frame del motor de sonido**.  `C0:0915+` es una tirada larga de handshakes `LDA $0021,X` / `LDA $40 / BPL` |
| 841+ | `0540` | ya en el bucle del fundido |

El recomp hace 780-791 en 12 gf **igual que hardware (12 frames)**, pero:
792-814 lo hace en 12 gf en vez de 23, 815-818 en ~2 en vez de 4, y la fase
**819-840 (22 frames) no existe**: salta del cierre directo al fundido.

### 21.4 La causa comun de §21.2 y del sobrerrecorrido: el reloj de invitado no se conserva

`SNESRECOMP_PC_LOG` da `gf` (fronteras de frame de invitado) y `hostf`.  Medido
(`tools/fades_ab2100.py --pclog`):

* Total del arranque a hostf 799: **880 gf / 799 host = 1,1014 gf/host**.
* Ventanas de 50 frames de host: **2,33** (hostf 3..52), **1,125** (303..352),
  **1,184** (653..702), **1,082** (703..752), y **1,000 exacto** en todas las
demas.
* Saltos concretos: hostf 4 → +66 gf; hostf 325 → +7 gf; hostf 701/702/705/708
  → +4/+7/+3/+3 gf.

Es decir: el recomp **no conserva el tiempo de invitado en los bucles de
espera**.  Se pasa (los +66/+7/+17 del arranque y del final de la carga) y se
queda corto (los 39 frames de §21.2).  Son las dos caras del mismo defecto, y
vive en la maquinaria de frontera de frame / `s_lle_quiescent_yield`, **no** en
el codigo de fundidos ni en las tablas `C8:F4xx`.

### 21.5 Palancas ya existentes probadas (A/B, resultado negativo)

Para no tocar nada a ciegas primero se movieron las palancas que ya trae el
motor.  Las tres dan **salida identica** (mismo `f=712`, `gf=793`, 880/799,
y mismo `E4`/`DA`/`AFB` al frame 800):

| palanca | valores | efecto |
|---|---|---|
| `SNESRECOMP_LLE_APU_FLUSH_THRESH` | 0 / 1024 / 8192 | ninguno |
| `SNESRECOMP_LLE_BOUNCE` | 0 / 1 | ninguno |

⇒ El flush pre-bounce de la APU **no** es la causa.  Quedan como sospechosos el
camino de `quiescent yield` y el FF de bucles de sondeo de `$4212`/`$2140`.

### 21.6 Herramientas nuevas

* `tools/fades_ab2100.py` — A/B evento a evento de `$2100` (hardware v4 vs
  `inidisp_trace.log`): segmentos con sitio y valor, emparejado 1:1, huecos
  entre segmentos, y tasa `gf/host` por ventana si se le pasa un `SNESRECOMP_PC_LOG`.
* `tools/fades900.py --ab` — A/B por reloj master de las columnas de RAM.


## 22. Conservación del tiempo de invitado: la deadline de frame (2026-09-29, madrugada)

### 22.1 El defecto: un frame de host no valía un frame de invitado

`interp_bridge_set_master_deadline()` existía desde el principio y lo consultan
tanto el puente como el código AOT generado, pero **nadie lo fijaba**: el
invitado corría "hasta quiescencia" sin más tope.  En los tramos que sí cambian
estado (los bucles de handshake de la subida del driver al SPC700) eso dejaba
que **un solo frame de host consumiera hasta 66 frames de invitado de un tirón**.

Medido con `SNESRECOMP_FRAME_BUDGET=1` (línea `[fbudget] f= dgf= dmaster= res0=
res1=` por frame de host), sin deadline:

| f | dgf | dmaster (frames) | res0 → res1 |
|---|---|---|---|
| 1..3 | 0 | 0,01 | 00F703 → (arranque) |
| 4 | **66** | 65,96 | 00F703 → C8F428 |
| 324 | **7** | 6,87 | C086BE → C08751 |
| 325 | 0 | 0,13 | C08751 → C8F425 |
| 701 | **4** | 4,81 | C086C4 → C08751 |
| 702 | **7** | 6,44 | C08751 → C08751 |
| 705 | **3** | 3,36 | C085CD → C08751 |
| 708 | **3** | 3,22 | C08751 → C08751 |

10 frames de host con `dgf != 1` (7 tras el arranque).  Con
`SNESRECOMP_FRAME_DEADLINE=1` (1 frame de invitado = 357368 ciclos master) sólo
quedan los **3 de arranque** (`dgf=0`), y el `dmaster` de todos los demás es
357350..357386, es decir exactamente un frame de invitado.

Efecto medido sobre el guion (`[fstate]`, primer `$00DA` de fundido):

| | frame de host del 1er fundido | `gf` correspondiente |
|---|---|---|
| hardware (Mesen, traza v4) | 841 | ~840 |
| recomp sin deadline | **712** | 792 |
| recomp con deadline | **791** | 788 |

El invitado **no** cambia de sitio en su propio reloj (792 vs 788 gf): lo que
cambia es que ahora tarda tantos frames de host como frames de invitado consume.

### 22.2 El guion de `$2100` COINCIDE, hueco a hueco

`tools/fades_ab2100.py` (con `--rc=`) empareja las escrituras a `$2100` de la
sonda v4 de hardware contra `SNESRECOMP_INIDISP_TRACE=1`.  Con la deadline
activa, los **30 segmentos** coinciden en sitio, valor y número de escrituras, y
los huecos entre segmentos son **idénticos uno a uno** salvo el último:

| tramo | hardware | recomp | Δ |
|---|---|---|---|
| `C8F4DE`→`C8F4C5` (1er fundido) | 131 | 131 | 0 |
| `C8F4C5`→`C8F4DE` | 2 | 2 | 0 |
| `C8F4DE`→`C8F4C5` (2º) | 121 | 121 | 0 |
| `C8F4C5`→`C8F4DE` | 16 | 16 | 0 |
| `C8F4DE`→`C8F4C5` (3º) | 273 | 273 | 0 |
| **`C8F4C5`→`CC280E`** | **125** | **95** | **−30** |
| arranque → `C08088` | 72 | 65 | −7 |
| `C08088` → `C8F4DE` | 14 | 2 | −12 |

Los tres fundidos (15 niveles × 4 frames cada uno, `C8F4DE` 01..0F / `C8F4C5`
0E..00, el `80` tras cada fade-out, `CC0E35`, y el fundido final `CC280E` a 4
frames por nivel) son **el mismo guion a la misma cadencia**.  Lo único que
queda son 49 frames de invitado (≈0,8 s) que el hardware se pasa esperando y el
recomp no.

### 22.3 Qué son esas tres esperas

* **`C08088`→`C8F4DE` (12 gf).**  Es el bucle principal del juego:
  `C0:81B4 LDA #$80 / STA $2100` + `C0:81B9 LDA #$0F / STA $2100`,
  `STA $4200=#$21` (vIRQ + auto-joypad), `CLI`, y luego despacho por la variable
  de modo `$00` con lectura de pad (`LDA $4218 / ORA $C1 / BIT #$1000`) y
  `JSL $C27EED`.  Hardware se queda 10 frames ahí (fr76-85, PC en
  `$8183/$82B3/$82ED/$8318`), el recomp 1.
* **`C8F4C5`→`CC280E` (30 gf).**  Hardware se pasa **22 frames (fr819-840)** en
  el transferencia al SPC700: `C0:0509` (despachador del bucle principal, que
  termina con `LDA $4A / EOR #$80 / STA $2140 / STA $4A`, el ping de frame al
  SPC) llamando a la tarea de copia de bytes `C0:09xx`
  (`LDA $001C,X / STA $42 / LDA $001B,X / STA $43 / LDA $40 / BPL`, con `X`
  descendente: un grupo de 3 bytes por frame, gateado por el espejo en RAM `$40`
  que actualiza el handler), junto con el tick del motor de sonido
  (`C0:CE4A DEC $08C3 / JSR $C675 / JSR $CE5F`, y `C0:CE5F` despacha por fase con
  `JSR ($CE6F,X)`).  En el recomp esa ventana no existe: su tráfico de puertos se
  corta en `f=787` y pasa directo a 3 frames de `C0441C`/`C8F54A`/`CC267E` antes
  del fundido.
* **arranque → `C08088` (7 gf).**  Ya contabilizado en §19/§20 (sobrerrecorrido
  del arranque).

### 22.4 El SPC responde 12 veces por frame donde hardware responde 1

Con `SNESRECOMP_APU_PORT_RW=logs/apu_rw_dl1.log` (una línea por acceso del SCPU a
`$2140-$2143`, con frame y valor):

| ventana | lecturas `$2140`/frame | alternancias `00`/`80` por frame |
|---|---|---|
| recomp f=759-769 (bucle `$86Cx`) | ~5800 | ~12 |
| recomp f=771-786 (subida) | ~8600 | ~12 |
| recomp f=788+ | 0 | — |

Hardware, en la traza v4 (`rdcnt`): `r2140=1990/01` en fr815 (≈6544 lecturas) y
**cero lecturas de `$2140` en fr819-840**, donde la espera va contra el espejo de
RAM `$40`.  O sea: en el recomp el intercambio se completa ~12 veces por frame;
en hardware, en la fase gateada por frame, **una vez por frame**.  El idioma del
handshake está en la ROM 33 veces (`AD 40 21 / CD 40 21 / D0 F8` = *LDA $2140 /
CMP $2140 / BNE*), es decir sondeo de "espera a que el puerto se estabilice".

### 22.5 Refutaciones y trampas de instrumento

* **`SNESRECOMP_APU_TOUCH_CYCLES` no sirve aquí.**  64 y 20 dan **salida
  idéntica** (mismo `f=791`, `gf=788`, `dgf=1` en todo).  El motivo está en
  `common_rtl.c`: esa palanca sólo escala el crédito sintético
  (`rtl_accumulate_apu_catchup`, +256 ciclos master por *touch*), mientras que el
  reloj real del SPC lo fijan `rtl_apu_guest_cycle()` /
  `rtl_sync_apu_frame_boundary()` con la razón verdadera
  `5632/118125 = 0,047678` (= 1,024 MHz / 21,477 MHz).  Con la deadline activa,
  el SPC queda por tanto **slave del reloj de invitado** y no del crédito
  sintético — que es justo lo que se quería.
* **El comentario del propio motor lo dice**: la sobre-acceleración del SPC en
  los handshakes ("boot/stage-load uploads measured 17-45x realtime") era un
  parche para el frame **sin tope** (con SPC a ritmo real, la subida de otro
  juego bloqueaba un frame más de 5 s y saltaba el watchdog).  Con la deadline
  ese bloqueo es imposible por construcción: un handshake que ocupa N frames de
  invitado cuesta N frames de host.  **Las dos piezas son complementarias.**
* Las escrituras `$2100` de `CC280E` que sobran tras el último valor (`0F`
  repetido cada frame) son del propio bucle: comparar contadores totales de
  escrituras entre corridas de distinta longitud da falsos positivos.

### 22.6 Estado

* `SNESRECOMP_FRAME_DEADLINE` **por defecto = 1,0** (`0` = comportamiento
  histórico ilimitado), y la deadline es **absoluta para todo el frame de host**
  (antes se recalculaba por vuelta del `guard`, lo que habría permitido hasta 8
  frames de invitado por frame de host en el camino del handshake de batalla
  `$C084B2/B4`).
* Determinismo comprobado: tres corridas idénticas (900 frames) dan **diff
  vacío** tanto en `[inidisp]` como en `[fstate]` (211 escrituras cada una).
* Corrida larga sin input, 2100 frames, todo `dgf=1` salvo los 3 de arranque, sin
  cuelgues; `gf = f − 3` exacto de punta a punta.
* Herramientas: `tools/fades_ab2100.py` gana `--rc=<log>` (acepta el stderr
  completo, no sólo un fichero de trazas) y la sección *alineación evento a
  evento*.
* **Lo que queda** (tarea abierta): por qué el invitado del recomp consume 49
  frames de invitado menos en las tres esperas de §22.3.  Candidato con
  mecanismo concreto: los handshakes están gateados por estado que **cambia una
  vez por frame** (el espejo `$40` que actualiza el handler) y en el recomp se
  resuelven varias veces por frame (12 intercambios/frame en `$2140`).  Medirlo
  hacia dentro exige contar por frame los accesos `$2140` de **ambos** lados (el
  lado SPC ya tiene contadores en `apu.c`: `g_spc_outport_value_counts`,
  `g_spc_recent_outport_writes`, `g_spc_pc_histogram`, hoy sólo expuestos por el
  servidor de depuración).

### 22.7 El fallo de audio con la deadline: el invitado ya no corre de más (2026-09-29)

Observado por el usuario en cuatro corridas consecutivas (10:47 falla, 10:48 va,
10:49 falla, 10:50 va) y **coincide exactamente con el A/B de la deadline**: el
diario `tier2_so_*.json` de cada corrida graba el frame del primer fundido, y se
alternan 1350 frames (= 791 + 559, deadline 1) con 1271 (= 712 + 559, deadline
0) mientras el tamaño del fichero alterna 26670 / 26586 bytes.

Mecanismo medido con `SNESRECOMP_AUDIO_STATS` (campos: `produced consumed dropped
dropped_audible drop_runs underflows consume_calls ring_fill
occupancy_highwater prod_cpu prod_audio`):

| | deadline 0 | deadline 1 |
|---|---|---|
| fps de host (1800 frames) | 53,6 | 46,4 |
| gf de invitado por frame de host | 1,101 | 1,000 |
| **ritmo de la máquina emulada** | **0,98× tiempo real** | **0,765× tiempo real** |
| `dropped` / `dropped_audible` / `drop_runs` | 0 / 0 / 0 | 392 / 186 / 3-4 |
| `underflows` | 102 (constante) | 277→673 (≈50/s) |
| `prod_audio` | 0 | 0 |

`RtlRenderAudio` es **consumidor puro** a propósito ("SPC state is guest-frame
driven by RtlAudioSyncFrame. The host callback is a consumer only"), y
`prod_audio=0` lo confirma: **nadie inventa ciclos de SPC desde el hilo de
audio**.  Por tanto el DSP/SPC avanza al ritmo de frames emulado.  A 46,4 fps de
host con 1,000 gf/host la máquina emulada va a 0,765× tiempo real → el DSP se
queda corto, el detector de deriva del motor dispara sus rampas de recuperación y
se oyen cortes.  El modelo viejo sonaba bien **porque corría el invitado un 10%
de más**: no era mérito del audio.

Corolario importante para el rendimiento: con la deadline el invitado consume
*de verdad* 357368 ciclos master por frame, incluidos los bucles de sondeo
(~8600 lecturas de `$2140` por frame).  Antes, el yield por quiescencia cerraba
muchos frames casi sin ejecutar ciclos mientras el contador de frames avanzaba
igual.  O sea: **parte del "60 fps" anterior era trabajo que no se hacía**.  La
cifra honesta hoy es ~46 fps en la intro con `build-dev`, y el objetivo de la
tarea 4 (quitar trabajo al intérprete) pasa a tener un número concreto que batir.

No hay pérdida de determinismo por el audio: tres corridas idénticas dan diff
vacío, y `prod_audio=0` en ambas configuraciones significa que el hilo de audio
no toca el SPC.

### 22.8 Reparto del coste por frame en la intro (2026-09-29)

Medido con reloj de pared restando la corrida de 900 a la de 1800 frames (así se
cancela el ~1,3 s de arranque de SDL+ROM).  `SNESRECOMP_FRAME_DEADLINE=0.001`
deja al invitado consumir ~357 ciclos master por frame en vez de 357368: sirve de
"sin trabajo de invitado" y separa el coste del núcleo del coste del invitado.

| config | tramo 900-1800 | fps equivalente |
|---|---|---|
| `FRAME_DEADLINE=1.0` (por defecto) | **21,79 ms/frame** | 45,9 |
| `FRAME_DEADLINE=0.001` (invitado sin ciclos) | **16,80 ms/frame** | 59,5 |
| `FRAME_DEADLINE=0` (histórico) | 16,82 ms/frame | 59,5 |

Dos conclusiones:

* El **suelo de `build-dev` es 16,8 ms/frame (59,5 fps) aun sin ejecutar el
  invitado**: render, audio y ventana.  Con eso, **ninguna optimización del
  emulador lleva `build-dev` a 60 fps**; para eso hace falta un build sin
  instrumentar o un render más barato.  (Y explica que el audio se degrade antes
  de tiempo: el umbral real de los ~58 fps está por debajo del suelo del build.)
* La deadline añade **+5,0 ms/frame** (21,79 vs 16,80) que son *ciclos del
  invitado que el modelo histórico se saltaba*: el yield por quiescencia cerraba
  el frame casi sin ejecutar.  En el tramo 1-900 el extra es +3,9 ms/frame.

Dónde está ese coste, en el código: con deadline activo, el bucle
auto-quiescente del puente (`interp_bridge.c:990`, `auto_quiescent &&
s_lle_master_deadline`) **no sale hasta alcanzar la deadline**, y la alcanza
ejecutando el bucle de espera **instrucción a instrucción**.  La optimización con
sentido es un *fast-forward de ciclos en quiescencia*: cuando el estado es
demostradamente estable (lectura pura, sin escrituras), avanzar `master_cycles`
hasta la deadline de una vez con el mismo `snes_sync_master_clock()` /
`cart_sync_coprocessors()` que ya usa cada instrucción, y devolver.  Conserva el
modelo de tiempo (la deadline se respeta), elimina el coste, y **puede además
mejorar la fidelidad**: en hardware la fase fr819-840 avanza *un paso de
handshake por frame* justamente porque espera un espejo de RAM que sólo cambia
en la frontera de frame.  Riesgo: cambia los valores que el invitado puede
observar *dentro* de un spin, así que hay que validarlo con el A/B de `$2100` y
con diff de `[fstate]`, no darlo por bueno porque sea más rápido.

### 22.9 Fast-forward de ciclos en quiescencia, y dónde está de verdad el coste (2026-09-29)

Implementado en `interp_bridge.c` (rama de quiescencia, la que pone
`s_lle_quiescent_yield = 1`): cuando hay deadline de frame y el estado de CPU/RAM
se ha repetido >=2 vueltas **sin lecturas de MMIO** (`continuous_read_epoch`
igual), ejecutar las vueltas restantes de un bucle que no puede salir hasta un
evento externo no puede cambiar nada, así que se **carga el tiempo**:
`master_cycles` hasta la deadline + `snes_sync_master_clock()` /
`cart_sync_coprocessors()`, igual que hacía cada instrucción.

Medido (tramo 900-1800 frames, intro + fondo de estrellas, `build-dev`):

| | ms/frame |
|---|---|
| deadline 1, sin fast-forward | 24,11 |
| deadline 1, **con** fast-forward | **23,05** |
| deadline 0 (histórico) | 17,85 |

Ganancia modesta (**−1,1 ms/frame**) y fidelidad intacta: primer fundido sigue en
el frame 791 y, con el contador de frames de invitado arreglado (§22.9.b),
`dgf = 1` en **los 899 frames** (antes el contador sólo avanzaba con
`SNESRECOMP_PC_LOG`, así que la sonda leía 0 y el modelo parecía peor de lo que
es).  Moraleja: los spins *estables* no eran el coste; el coste restante son los
**bucles de sondeo de MMIO**, que el propio detector excluye a propósito
(`continuous_read_epoch` cambia en cada lectura de registro) y que el invitado
ejecuta de verdad (~8600 lecturas de `$2140` por frame durante la subida).

### 22.9.b Arreglos de instrumento en este cambio

* `snes.c`: el contador de frames de invitado se lleva **siempre** (estaba dentro
  del `if (SNESRECOMP_PC_LOG)`), y se expone con `snes_guest_frame_count()`.
* `src/so_rtl.c`: repuesta la sonda `SNESRECOMP_FRAME_BUDGET` (línea `[fbudget]`
  por frame de host con `dgf`/`dmaster`/PC antes y después).

### 22.10 Dónde está el trabajo que falta para 60 fps (tarea 4)

El motor ya escribe un diario por corrida, `tier2_so_*.json`, con los sitios donde
el código AOT **cede el control al intérprete** (huecos de cobertura) y cuántas
veces cada uno salió "limpio" (`clean_hits` = el intérprete ejecutó el hueco y
volvió equilibrado ⇒ promocionable).  En la corrida de la intro (150 sitios):

| sitio | destino | clean_hits | qué es |
|---|---|---|---|
| `C0:024E` | `C0:02F6` | 1732 | cadena del handler de IRQ |
| `C0:0251` | `C0:032D` | 1732 | la "bomba" por-frame |
| `C0:0254` | `C0:1E64` | 1732 | continuación del handler |
| `C0:51B3` | `C0:51F3` | 1149 | bucle principal del juego |
| `C0:527A` | `C8:75CF` | 1149 | |
| `C8:75E0` | `C3:8BB7` | 1149 | motor de fundidos |
| `C8:7644` | `C5:035D` | 1149 | |
| `CC:270D/2715/2718` | `CC:29F3/2943/29C8` | 1010 | motor de cutscenes |
| `CC:278C/2790/2796/27FC` | `C0:5193`/`C3:8D3D`/`CC:0530`/`CC:0F21` | 1010 | idem |

Todas son rutas **por frame** (1732 ≈ 1800 frames): cada frame paga una vuelta
AOT→intérprete→AOT por cada una.  Promocionarlas (añadir `func` al `bankNN.cfg`
y **volver a pasar el recompilador v2**) es el trabajo que reduce de verdad el
coste del invitado, que es lo que la deadline destapa.  Ojo: `generated/*.c` son
ficheros pre-generados (09-28 16:39), **no** los regenera el build, así que la
promoción exige correr el recompilador y validar con diff byte-exacto, no sólo
recompilar.

### 22.11 El coste de la fidelidad era un FF desactivado, no el invitado (2026-09-29)

**El hallazgo.** La deadline de frame (que arreglo el modelo de tiempo, §22) estaba
APAGANDO sin querer toda la familia de fast-forwards de espera de vblank del motor.
En `interp_bridge.c` el guard de ese FF exigia `!s_lle_master_deadline`:

```c
if (auto_quiescent && g_snes && !in.i && !s_lle_master_deadline &&
    ((pc_before == 0xC8F425u || ... 0xC20B82u || ...))) {
```

El FF nacio cuando la deadline era codigo muerto (nadie llamaba a
`interp_bridge_set_master_deadline()`), asi que la incompatibilidad nunca se probo.
No existe: el destino del FF es el fin NATURAL de la espera (borde de vblank a
225*1364 ciclos, o fin de frame a 357368), siempre DENTRO del frame en curso, que es
justo el tramo que la deadline delimita. Mientras estaba apagado, la deadline obligaba
a ejecutar esos spins instruccion a instruccion.

Numero del coste, medido en la intro (`SNESRECOMP_PHASE_MS=1`):

| config | emu | draw | total | FPS |
|---|---|---|---|---|
| deadline 0 (historico, FF activo) | 2,0-8,6 ms | 12-14,7 ms* | 16,6 ms | 60,1 |
| deadline 1, FF apagado (hasta hoy) | **14,0-17,5 ms** | 1,7-4,0 ms | 17,1-21,5 ms | 46-58 |
| deadline 1, FF reactivado (ahora) | **1,8-7,3 ms** | 10,5-14,9 ms* | 16,6-18,2 ms | 55-60 |

\* cuando el frame entra en el presupuesto, el `draw` medido incluye la espera de
vsync en el present, por eso sube a ~12-14 ms: el total clavado en 16,6x ms es la
prueba de que el frame se entrega a 60,0 fps.

**El cambio (minimo y reversible).** Dos lineas en `interp_bridge.c`:
1. quitar `!s_lle_master_deadline` del guard del FF;
2. clamp: `if (s_lle_master_deadline && target > s_lle_master_deadline) target = 0;`
   El FF solo puede cargar tiempo DENTRO del frame; si su destino quedase mas alla
   de la deadline no se dispara y el spin se ejecuta normalmente (dgf = 1 intacto).

**Validacion A/B (protocolo byte-exacto).** Mismo binario, dos corridas sin input,
`SNESRECOMP_FRAME_STATE=1`, comparando la linea `[fstate]` (26 campos: PC, master,
cpu, inidisp, pad, r4200, irq/nmi, E4, DA, AFB, AFD, D01, DB, PB, DP, S):

| ventana | FF off (deadline 1) vs FF on (deadline 1) |
|---|---|
| 2100 frames | **byte-identicos** (2100/2100 lineas) |
| 3600 frames | **byte-identicos** (3600/3600 lineas) |

Y `dgf = 1` en **1799/1799** frames en las dos configuraciones
(`SNESRECOMP_FRAME_BUDGET=1`), o sea que el modelo de tiempo no se toca: el invitado
sigue consumiendo exactamente 357368 ciclos master por frame de host.

**Efecto en el audio (la consecuencia, no la causa).** `RtlRenderAudio` es consumidor
puro y el SPC/DSP avanzan con el reloj de frames emulado, asi que la maquina tiene que
correr a tiempo real para no dejar seco al DSP. Con la intro a 47-56 fps la maquina iba
a 0,78-0,93x y el detector de deriva del motor cortaba el sonido. Numeros
(`SNESRECOMP_AUDIO_STATS`, 1800 frames, mismo binario):

| | FF off | FF on |
|---|---|---|
| FPS de host (1800 fr) | 47,0 | **56,1** (60,1 en regimen) |
| `underflows` | 1519 | **104** |
| `dropped` / audibles / `drop_runs` | 643 / 233 / 3 | 3756 / 430 / 15 |
| `hiwater` / `prod_audio` | 8192 / 0 | 8192 / **0** |

`prod_audio = 0` en las dos: nadie inventa ciclos de SPC desde el hilo de audio, el
determinismo esta intacto. Tras el cambio, el unico evento audible que queda es **un
unico desbordamiento de 413 muestras (~9,5 ms) en 8 rachas, una sola vez por corrida
(unos 17 s tras el arranque)**, causado por un paron del consumidor de ~0,2 s: la
ocupacion salta 610 -> 7837 en un segundo (el productor sigue a 534/frame, luego el
consumidor paro), el anillo llega a 8192 y el rebose tira lo mas nuevo. Antes y despues
de ese instante: **cero descartes** durante el resto de la corrida. La ocupacion queda
drenando suavemente (3061 -> 2523) segun el servo, como esta disenado.

**Estado de los builds.** `build-dev` (instrumentado) y `build-clean-test` (el de
jugar) recompilados desde el fuente actual: los dos entregan 60 fps en regimen
(`[fps] 60 fps` en el heartbeat del clean). `build-clean` NO se ha tocado (referencia
congelada, sigue con el binario de 09-28 16:58). Logs de referencia:
`build-dev/Release/logs/{vff_on,vff_off}_3600.fstate`, `logs/{vff_on,vff_off}.log`,
`logs/aud_vff_{on,off}.log`, `logs/fb_vff_{on,off}.log` y
`build-clean-test/Release/logs/{aud_cleantest,fps_cleantest}.log`.

**Lo que queda pendiente y por que no lo he tocado.** El desbordamiento unico se
eliminaria con un *trim con fade* en el camino normal: el motor ya tiene la maquinaria
(`dsp_trimSamples` + `RTL_AUDIO_RECOVERY_RAMP`, hoy solo en el camino de turbo), y
aplicarla cuando la ocupacion pase de un umbral alto convertiria el rebose brusco
(click) en un recorte suave. No lo he hecho porque cambia el camino de audio que se usa
en juego normal y no puedo oirlo aqui: hay que medirlo con el contador de descartes
audibles y confirmarlo de oido, que es el protocolo que venimos siguiendo.

### 22.12 El audio: dos defectos de tasa, no de mezcla (2026-09-29)

**Sintoma.** En `build-clean`/`build-clean-test` (los builds de jugar) no se oia
nada, y en la ventana del logo (f757-789) habia un ruido y una caida a ~47 fps.
`build-dev` tampoco sonaba desde el cambio de deadline.

**Causa 1 — la tasa del consumidor no era la del productor.** El runner compila
`snesrecomp/runner/src/common_rtl.c` (no la copia `snes/`, ojo con eso: son dos
ficheros distintos y solo el primero entra en el enlace). Su revision del 28-09
19:47 paso la produccion a la fraccion exacta de hardware
(`RTL_APU_RATIO_NUM/DEN = 5632/118125` sobre `RTL_MASTER_CYCLES_PER_FRAME =
357368`, o sea **31.944 natives/s**), pero dejo el consumo declarado a mano:

```c
#define RTL_AUDIO_NATIVE_RATE 32040.0 /* SPC output rate: 1.024 MHz / 32 */
```

El comentario ya se contradecia (1.024 MHz / 32 = 32.000). Consecuencia: el
consumidor drenaba `32040 x servo` natives/s contra una produccion de 31.944/s,
o sea **-0,3% estructural**; el anillo del DSP se vaciaba, `need = span+2` no se
alcanzaba nunca y **`output_underflows` subia exactamente +60/s (una por
callback) durante toda la intro**: silencio, aunque el SPC estuviera produciendo
(`produced` crecia a 32.000/s y `prod_audio = 0`). El modelo antiguo sonaba solo
porque corria 1,101 frames de invitado por frame de host: el 10% de mas llenaba
el anillo. Era el defecto de §22, no merito del audio.

Arreglo (una constante): derivar `RTL_AUDIO_NATIVE_RATE` de las MISMAS constantes
del productor, para que las dos tasas no puedan volver a separarse.

**Causa 2 — el anillo no tenia colchon ni forma de recuperarlo.**
1. El dispositivo arranca pidiendo 534 natives cuando el anillo esta vacio (el
   invitado produce 534 por frame, asi que en el primer tiro no hay nada). Se
   pre-encolan 4 bloques (~67 ms, el objetivo del propio servo) de silencio en el
   `SDL_AudioStream`: el dispositivo tarda 67 ms en pedir, el invitado produce 4
   frames en ese tiempo y el anillo arranca lleno. **Es cola del host: no toca ni
   un ciclo del invitado.**
2. Los bursts de produccion (arranque: el anillo llego a ~5.500 con `prod/s =
   35.901`; logo: 7.610 con `prod/s = 40.293`) rebosaban los 8.192 natives porque
   el servo solo recupera al +-0,5% (165 natives/s). Ahora
   `rtl_sync_apu_frame_boundary()` recorta el exceso a 2x el objetivo
   (`dsp_trimSamples`, que existia sin usarse) descartando lo mas ANTIGUO de la
   cola -latencia pura- con la rampa de recuperacion del motor.

**Medido (`SNESRECOMP_AUDIO_STATS`, 1800 frames, mismo binario):**

| | antes | despues |
|---|---|---|
| `output_underflows` | 1.800 (60/s, todos) | **90** (solo los 2 primeros s) |
| `dropped` / audibles / `drop_runs` | 5.897 / 393 / 22 | **0 / 0 / 0** |
| colchon (`occupancy`) | 0-5.055 | ~1.800 estable |
| `hiwater` | 8.192 (tope) | 4.818 |
| `prod_audio` | 0 | **0** |

En `build-clean-test` (42 s): `dropped=0 audible=0`, colchon 1.855, y el heartbeat
de FPS da **60 fps** en 29 de 40 ventanas (59 en 5, 56/55/51/49 en las de
transicion).

**Validacion de que el invitado no se toca.** Mismo binario con y sin estos
cambios, 3600 frames sin input, `SNESRECOMP_FRAME_STATE=1`:
`logs/vff_on_3600.fstate` == `logs/vff_on_3600b.fstate`, **3600/3600 lineas
`[fstate]` byte-identicas**. La tasa y el recorte son del lado del host.

**Lo que queda (y es lo mismo que causa el hueco de fps).** La ventana f757-789
sigue costando `emu = 20-23 ms` (f788: 42 ms) contra 1,3 ms del resto de la
intro: son los 30 frames del handshake con el SPC700, donde el invitado ejecuta
**el 79% de sus instrucciones en 11 PCs de un unico bucle,
`$C0859D-$C085D0`** (perfilado con `-DSNESRECOMP_INTERP_PROFILE`, ver
`build-prof`). Es trabajo real del invitado, no un FF mal puesto: el bucle sondea
los puertos APU. Como el SPC de este motor solo avanza en la frontera de frame
(`apu_runToGuestCycle` por frame), dentro de un frame el valor leido no puede
cambiar, asi que ese bucle ES fast-forwardeable al mismo criterio que los spins
de `$4212` -la linea siguiente-: seria a la vez el fin del hueco de fps y la
causa de que el handshake avance un paso por frame como en hardware. Las dos
tareas que quedan: (a) ese FF, (b) AOT de `$C0859D-$C085D0` (necesita pasar el
recompilador v2, `generated/*.c` son pre-generados).

### 22.13 La deadline silenciaba la musica: el tick del driver vive en el V-IRQ (2026-09-29)

**Hallazgo, con evidencia directa.** Se anadio una sonda del PCM REAL que se
entrega al dispositivo (`SNESRECOMP_PCM_DUMP=<path>` en `FillAudioBuffer`: volca
los bytes exactos que van al dispositivo). Resultado en la intro:

| config | PCM entregado |
|---|---|
| `FRAME_DEADLINE=0` | silencio 0-6 s y **musica continua desde 7 s** (picos 2.000-4.500, rms ~700) |
| `FRAME_DEADLINE=1` | silencio 0-13 s, un unico chasquido (pico 7.748) en f790 y **pico 2** el resto |
| `FRAME_DEADLINE=0.5` / `0.25` | **pico 0 en todo** (ni el chasquido) |

No es entrega ni mezcla: el DSP emulado no suena. Y no lo causan los fast-forwards
- desactivando solo el de quiescencia (`SNESRECOMP_NO_QUIESCENT_FF=1`) y solo el de
vblank (`SNESRECOMP_NO_VBLANK_FF=1`) el silencio es identico. **Es la deadline en
si**, y es binario: basta 0,25 frames para silenciarlo todo, asi que no va de
"cuanto tiempo" sino de POR DONDE sale el frame.

**Mecanismo (encaja con lo ya medido).** Con deadline,
`interp_bridge_run_until_quiescent()` cede por RAMA DE DEADLINE en vez de por
QUIESCENCIA, y el tick del driver de sonido del juego vive en el handler de V-IRQ
por frame (`C0:032D`, la "bomba" por-frame de §19: la llama `C0:0251 JSR $032D`
desde el handler). El camino de quiescencia ya entrega el NMI/IRQ del frame al
invitado bloqueado (por eso existe `interp_bridge_lle_took_quiescent()`); el de
deadline no. Sin ese tick, el driver carga, toca la primera nota (el chasquido de
f790) y se queda mudo.

**Estado: la deadline NO se activa por defecto** (`SNESRECOMP_FRAME_DEADLINE`,
default 0 desde hoy) para no dejar el juego sin audio. La fidelidad del modelo de
tiempo y su A/B byte-exacto (§22) siguen intactos y disponibles con
`SNESRECOMP_FRAME_DEADLINE=1`; lo que falta para poder activarla por defecto es que
el camino de deadline entregue tambien el NMI/IRQ del frame como hace el de
quiescencia. Los arreglos de audio de §22.12 (tasa del consumidor, colchon inicial,
recorte de exceso) son independientes de la deadline y siguen activos; con la
deadline en 0 se miden `dropped=0 audible=0` y sin hambre del anillo.

**Instrumento nuevo y reutilizable:** `SNESRECOMP_PCM_DUMP=<path>` (S16LE
entrelazado al ritmo del dispositivo). Separa "el motor entrega silencio" de "el
motor entrega audio y no se oye", que es la pregunta que hizo perder tiempo antes.

#### 22.13.b Evidencia afinada y test de regresion

Dos sondas mas acotan donde se para la musica con la deadline (1200 frames,
mismo binario):

| sonda | `FRAME_DEADLINE=0` | `FRAME_DEADLINE=1` |
|---|---|---|
| escrituras a registros del DSP (`SNESRECOMP_DSPREG_TRACE_FILE`) | **8.848** | **142** |
| de ellas, key-on (`$4C`) | **205** | **1** |
| 1er tick del driver `$C0032D` (`SNESRECOMP_PCHIT`) | frame 4 | frame 69 |
| ritmo del tick tras arrancar | ~1/frame | ~1/frame |

O sea: el tick del driver **si** corre ~1x/frame en los dos modelos, y el DSP no
esta roto. Lo que cambia es que con la deadline el driver **deja de escribir notas**
(205 key-on -> 1): el secuenciador del SPC700 se para despues de la primera nota.
El siguiente paso ya no es el entregable de audio ni el DSP, es el reloj del APU
(`rtl_sync_apu_frame_boundary` / `apu_runToGuestCycle`): la sincronia por frame
(`snes_frame_counter * 17038`) y la sincronia por reloj master
(`rtl_apu_guest_cycle()`, que con la deadline llega al final del frame) pueden
quedar desfasadas un frame, y `apu_runToGuestCycle()` retorna sin ejecutar nada
cuando `guest_cycle < apu->portGuestAnchor`.

**Test de regresion: `tools/audio_health.py`.** Vuelca el PCM que se entrega al
dispositivo y falla si hay un segundo en silencio absoluto o si menos del 60% de
los segundos sonando tienen musica. Verificado en las dos direcciones:

```
python tools/audio_health.py                  # OK: 16/18 segundos con musica, ningun silencio absoluto
python tools/audio_health.py --deadline=1     # FALLO: 6 segundos en silencio absoluto desde el 8
```

Este test es la respuesta al fallo que costo horas: el motor tenia `dropped=0`,
`underflows` de arranque y anillo lleno, todos los contadores bien, y el juego
estaba mudo. Hay que ejecutarlo tras tocar el modelo de frame o el camino de audio.

### 22.14 Protocolo de trabajo y sus herramientas (2026-09-29)

Acordado con el usuario: **nada de conjeturas ni hipotesis**. Si aparece algo, se
prueba, se corroboran los datos, y solo se aplica si pasa la comparativa A/B
byte-exacto; si no la pasa, se anota por si sirve en otra zona y se sigue con el
siguiente error.

* **`PROTOCOLO.md`** — el ciclo paso a paso (medir el sintoma con el instrumento
  correcto, hipotesis falsable, un experimento por hipotesis, la puerta A/B, y
  aplicar-o-anotar) y la lista de trampas que ya nos han costado tiempo.
* **`DESCARTADAS.md`** — registro de lo probado y no aplicado, con la evidencia:
  el reloj del APU siguiendo el master (revertido, no arregla el silencio), el
  desacoplo del reloj del DSP (descartado por determinismo), `DisableFrameDelay`
  (empeora con datos), los fast-forwards como causa del silencio (no lo eran), y
  los instrumentos que mintieron.
* **`tools/verificar.py`** — las tres pruebas en un comando:
  `audio` (PCM real entregado al dispositivo), `fps` (mediana en regimen >= 58) y
  `ab` (`[fstate]` contra el baseline guardado en
  `build-dev/Release/logs/golden_fstate.log`). Sale 1 si algo falla. Acepta
  `--only audio,ab`, `--deadline=N` y `--update-golden` (regenerar el baseline es un
  acto deliberado: significa "este cambio SI debe alterar el comportamiento").
* **`tools/audio_health.py`** — el detector de silencio, validado en las dos
  direcciones: pasa con el default y **falla** con `--deadline=1`.

Estado medido con `python tools/verificar.py` sobre el arbol actual
(deadline por defecto = 0):

```
[PASA ] audio            OK: 26/29 segundos con musica (90%) desde el 8, ningun silencio absoluto
[PASA ] fps              mediana 60.0 fps en regimen (52-60), minima 52.2
[PASA ] A/B byte-exacto  2100/2100 frames byte-identicos al baseline
```

Y el mismo comando con `--deadline=1 --only audio,ab` **falla las dos**: la que
delata el fallo de §22.13 y la que confirma que activar la deadline SI cambia el
comportamiento (frame 1: master=357368 con deadline, 4360 sin ella).

## 22.15 Instrumento nuevo: grabadora de partida en Mesen (`tools/mesen_so_trace.lua`)

**Por qué (29/09, cierre de jornada).** El usuario tenia razon en dos cosas que
habia que dejar por escrito:

1. **Las pruebas con "grabacion" eran cortisimas.** El guion que yo estaba usando
   como partida grabada (`build-dev/Release/rep_bueno.txt`, copiado a
   `tools/input_scripts/grabada.txt`) dura **425 frames**: cinco pulsaciones de A
   (f66, f147, f209, f270, f413) y se acaba justo cuando empieza la cinematica.
   Con esa entrada, cualquier prueba de audio corta **antes** de que la musica
   continua arranque, y por eso el resultado no decia nada de la parte que se oye.
2. **Existe una partida grabada larga y no la estaba usando**:
   `run-trace/replay_3_peleas.txt`, **23.435 frames (~390 s, 6,5 min)** desde
   f424, con las pulsaciones que describia el usuario: A (235 veces), Arriba
   (0x10), Abajo (0x20), Izquierda (0x40), Derecha (0x80) y combinaciones
   (0x60 abajo+izquierda, 0x110 A+arriba, 0x190 A+arriba+derecha...). Es la que
   recorre menu -> Continue -> seleccion de nombre -> cinematica -> juego.

**Que se ha hecho.** Un script de Mesen que graba la partida *mientras se juega*
y vuelca tres ficheros, para no depender de capturas manuales ni de guiones
inventados:

| fichero | contenido |
|---|---|
| `<rom>_trace.tsv` | 34 columnas, una fila por frame: pad (mascara + botones), estado de CPU y SPC700, PPU, handshake APU, `$2100`, key-on acumulado, bucle caliente `$C0859D-$C085D0`, `$4212`, NMI y `$4200` |
| `<rom>_events.tsv` | un evento por linea: escrituras a `$2100`/`$4200`, puertos del APU desde CPU y desde SPC, escrituras al DSP (`$F2`/`$F3`) con el registro y **key-on**, sombras WRAM, NMI/IRQ |
| `<rom>_replay.txt` | **solo pulsaciones**, `"<frame> <mascara>"` en el orden `$4218`, es decir el mismo formato que `SNESRECOMP_REPLAY_FILE`: se puede meter tal cual en el motor |

El valor de la mascara es el mismo que usa el motor (b0=B b1=Y b2=Sel b3=Start
b4=Up b5=Down b6=Left b7=Right b8=A b9=X b10=L b11=R), asi que la partida del
usuario se puede reproducir en el recomp frame a frame y comparar con lo grabado
en Mesen: es la referencia que faltaba para el A/B con input real.

**API: verificada, no supuesta.** Se comprobo en dos fuentes: el fuente de
Mesen-S (`Core/LuaApi.cpp`) y la **referencia de API JSON incrustada en el
`Mesen.exe` del usuario** (la de su build exacta): `eventType` = nmi 0, irq 1,
startFrame 2, **endFrame 3**, reset 4, scriptEnded 5, inputPolled 6;
`cpuType.snes`/`spc`; `memType.snesMemory`/`spcMemory`;
`addMemoryCallback(callback, callbackType, start, end, cpuType, memType)`;
`getInput(port, subPort)`, `getCpuState(cpuType)`, `getMasterClock()`,
`getCpuCycleCount(cpuType)`, `stop(exitCode)`.

**Dos defectos que se corrigieron antes de entregarlo** (por eso conviene
revisar antes de escribir codigo nuevo):

* los hooks del SPC **no pueden** usar la forma de `addMemoryCallback` sin
  `cpuType`: `$00F2/$00F3` en banco 0 son WRAM, asi que habrian dado "key-on"
  falsos a mansalva. Ahora el SPC va siempre con `cpuType` explicito (y con una
  variante de diagnostico registrada aparte, `alt_spcw`/`alt_dspw`, para detectar
  si la forma canonica no dispara en esa build: el log lo avisa);
* `emu.stop()` **cierra el emulador** (es del modo `--testRunner`), asi que no se
  llama al terminar salvo que se ponga `PARAR_AL_TERMINAR = true`.

Ademas el script se autodiagnostica: vuelca las claves reales de `getState()`,
vigila que el desfase con el contador de frames del PPU no cambie, y avisa si la
grabacion no empezo en el arranque (ese replay no se alinearia con el motor).

**Lo que NO esta hecho todavia** (para manana): la puerta `tools/verificar.py`
sigue apuntando a la entrada de 425 frames. Hay que pasarla a la partida larga
(`run-trace/replay_3_peleas.txt`) y regenerar su baseline A/B de forma
deliberada: la ventana de la cinematica (donde arranca la musica continua) queda
fuera de la entrada actual, que es exactamente el motivo por el que las pruebas
de audio de §22.12/§22.13 no cubrian lo que el usuario oia.

Los ficheros que produce el script se guardan con la ROM; el usuario los ha
centralizado en `StarOceanRecompDocumentacion/TracesMesen`.

## 22.16 Turbo utilizable: aceleracion del host sin tocar al invitado (2026-09-29)

### Que habia

`Turbo = Tab` existia desde siempre (`config.ini`, `kKeys_Turbo`,
`g_turbo`), pero su unico efecto era cambiar la espera de fin de frame por
`SDL_Delay(1)`. Y no servia de nada: el present (`SDL_RenderPresent` con
`vsync=true` en `SnesRenderer_Init`) bloquea hasta el refresco de pantalla, asi
que el frame seguia costando 16,7 ms de reloj de pared aunque se quitase la
espera. Turbo sobre el papel, ~1x en la practica.

### Que hace ahora (`src/main.c`)

1. **Sin pacing en turbo.** El frame de turbo no espera nada (ni deadline de 60
   Hz ni `SDL_Delay(1)`): el bucle corre tan rapido como el host pueda. El hilo
   de audio drena por su cuenta y el pump de eventos se hace en cada vuelta, asi
   que no se queda nada sin atender.
2. **Present elidido** en los frames de turbo salvo uno de cada N
   (`SNESRECOMP_TURBO_PRESENT_EVERY`, por defecto 16; 0 = ninguno). El elidido es
   solo el lock de la textura, el memcpy y el `RenderPresent`.
   **NO se toca `SoDrawPpuFrame`**: esa funcion no es cosmetica -hace el HDMA
   linea a linea y entrega el vIRQ de raster/vblank que el juego espera- y por eso
   el invitado sigue viendo el frame entero. Es la misma particion que hace el
   host MMX (`disableRender`, `runner/src/desktop/mmx23_host_main.inc:1642`).
3. **Control sin teclado** (dev, inerte sin variables):

   | variable | efecto |
   |---|---|
   | `SNESRECOMP_FORCE_TURBO=1` | turbo en todos los frames |
   | `SNESRECOMP_TURBO_BURST=a,n` | turbo solo en los frames de invitado `[a, a+n)` |
   | `SNESRECOMP_TURBO_PRESENT_EVERY=N` | 1 present cada N frames de turbo (0 = ninguno) |

   La ventana del burst va sobre el **contador de frames de invitado**
   (`snes_frame_counter`), el mismo reloj que el fichero de replay y los logs
   `[fstate]`/`[fps]`: se puede pasar a toda velocidad un prefijo ya revisado y
   mirar a tempo normal los frames que interesan **en la misma corrida**.
4. `RtlAudioSetFastForward(g_turbo)` por frame: activa el camino de trim/rampa
   que el motor ya tenia para turbo (§22.12), de modo que soltar turbo no deja el
   audio descolgado.

### Medido (misma maquina, `build-dev`)

Intro sin input, hasta el frame 900:

| config | reloj de pared | por frame | vel. relativa |
|---|---|---|---|
| normal | 18,79 s | 20,9 ms | 1,00x |
| turbo con `SDL_Delay(1)` (antes) | 9,14 s | 10,2 ms | 2,06x |
| **turbo sin pacing (ahora)** | **7,73 s** | **8,6 ms** | **2,43x** |

`SNESRECOMP_TURBO_PRESENT_EVERY` = 16 / 32 / 0 da 7,74 / 7,79 / 7,66 s: con la
cola de presents vacia el vsync no llega a bloquear, asi que el present no era el
coste. El limite es el coste real del invitado (`emu` 1,4-13,4 ms/frame en la
intro, `draw` 1,2-2,8 ms): turbo no puede ser 10x en un recompilador CPU-bound.

Partida larga (`run-trace/replay_3_peleas.txt`), hasta el frame 2400:

| config | reloj de pared | vel. relativa |
|---|---|---|
| normal | 44,56 s | 1,00x |
| burst `0,2000` (83% del tramo) | 22,70 s | 1,96x |
| turbo total | 15,57 s | **2,86x** |

### Prueba de que turbo es inocuo para el invitado

Turbo cambia solo el ritmo del **host**; el invitado sigue ejecutando un frame
por vuelta. Comprobado con la puerta A/B (que compara la linea `[fstate]`
completa: master, registros de CPU/SPC, PPU, contadores de handshake):

| corrida | contra | resultado |
|---|---|---|
| `SNESRECOMP_FORCE_TURBO=1`, 1200 frames sin input | baseline sin turbo | **1200/1200 byte-identicos** |
| turbo durante 2000 de 2400 frames con replay largo | misma corrida sin turbo | **2400/2400 byte-identicos** |
| determinismo (dos corridas turbo) | - | 900/900 identicos |

Y el audio sobrevive al turbo: con `TURBO_BURST=0,600` y luego tempo normal, el
PCM entregado al dispositivo da 16/16 segundos con musica (100%) desde el segundo
8, sin silencio absoluto -el camino de trim/rampa de §22.12 hace su trabajo-.
Durante el turbo el sonido no sirve para escuchar (el dispositivo drena a 1x
mientras el invitado produce casi 3x): turbo es para avanzar, no para oir.

### Uso

```bash
# a mano: mantener Tab (config.ini: Turbo = Tab)

# automatizado: pasar a toda velocidad el prefijo ya revisado y pararse en el tramo util
SNESRECOMP_REPLAY_FILE=run-trace/replay_3_peleas.txt \
SNESRECOMP_REPLAY_UP_PAUSE_MS=0 \
SNESRECOMP_TURBO_BURST=0,2000 \
SNESRECOMP_EXIT_AT_FRAME=2400 ./StarOcean.exe
```

`build-dev` y `build-clean-test` (el que se juega) estan recompilados con esto;
`build-clean` sigue intacto como referencia congelada.

Nota de metodo: la prueba `fps` de la puerta es sensible a la carga de la
maquina. Una corrida completa dio mediana 57,7 fps (umbral 58) con el sistema
ocupado y 60,2-60,2 fps al repetirla en solitario; antes de dar un fallo de fps
por real, repetirla con la maquina tranquila.

## 23. Limpieza de la raiz del arbol (2026-09-30)

Motivo: la raiz mezclaba herramientas de la epoca del hack (`build/` + Ninja,
`deps/SDL2-*`) con las del flujo actual (VS2022, `build-dev`, `tools/verificar.py`).
Criterio aplicado fichero a fichero: **se queda solo si un documento vivo
(README, `docs/*.md`) o el propio motor lo cita Y ademas puede correr contra
artefactos que este arbol todavia produce.**

Eliminados, rastreados (recuperables con `git show <commit>^:<fichero>`):

| fichero | por que |
|---|---|
| `_check.py`, `_check2.py` | sondas GDI de ventana (brillo / "¿esta congelado?"). Sustituidas por `SNESRECOMP_FRAME_STATE` + `tools/verificar.py`; sin referencias en ningun documento. |
| `analyze_ppu.py`, `decode_vram.py`, `vram_viewer.py`, `vram_visualizer.py` | leen `ppu_dump.bin`; ningun componente del arbol lo escribe ya. |
| `render_bg.py`, `render_mode0.py` | idem (`build/saves/ppu_dump.bin`), y §9 ya marcaba sus supuestos de tilemap como de la epoca del hack. |
| `test_vram.py` | simulador de juguete de la etapa S-DD1: no mide nada real. |
| `trace_mode_trajectory.py`, `validate_drive.py` | `import so_drive`, modulo que no existe (estaba en `.gitignore` y ya no esta): rotos de origen. |
| `build_msvc.bat` | configura Ninja + SDL2 mingw (`deps/SDL2-2.30.5/x86_64-w64-mingw32`), ruta que no existe; el flujo es VS2022 + SDL3. |
| `build_trace.bat` | `ninja -C build-trace`; `SNESRECOMP_ENABLE_TRACE` ya no existe en las fuentes. |

Basura de configure local, ignorada (borrada sin rastro en git): `CMakeCache.txt`
+ `CMakeFiles/` — un configure in-source con generador **Visual Studio 18 2026** y
`SNESRECOMP_SDL_BACKEND=SDL2`, ajeno a los `build-*/` reales —, `_bd.log` y
`build-clean-test-build.log` (logs de MSBuild), `logs_cfg_audit.txt` (configure que
falla: sin SDL2) y `logs_cfg_prof.txt`.

Se quedan, con motivo: `sdd1_ref.py` + `sdd1_compare.py` (oraculo independiente
del S-DD1; `snesrecomp/runner/src/snes/ppu.c:2480` los cita como la validacion
byte-exacta del motor) y `sdd1_engine_test.c`; `run_dev_forense.bat` y
`run_clean_ab.bat` (lanzadores forense y A/B documentados en §16, con todas sus
variables de entorno todavia vivas en el host — y estan en `.gitignore`, asi que
borrarlos no seria recuperable); `SO_jap_ROM_layout.txt` (referencia obligatoria
de `agents.md`).

Fuera del alcance pedido (extensión distinta; señalados, no tocados):
`build.ps1` y `build.sh`, plantilla del motor que compila la "static library" del
flujo antiguo (`cmake -B build -G Ninja`) — el README apunta a
`tools/regenerate_aot.ps1` y a cmake directo con VS2022.

## 24. Revision externa (`HerramientasDecompilacion`) y trazas nuevas de Mesen (2026-09-30)

Revision, no aceptacion: aqui queda **que esta verificado y que no**, medido por
nosotros contra la ROM y contra los TSV, para no construir encima de una
conclusion que no se sostiene.

### 24.1 Lo que el HANDOFF acierta (verificado byte a byte)

ROM de `StarOceanRecomp/`: 6.291.456 B, sha1 `A616EE34…EF8D` (el mismo que
declara el replay de Mesen). Los cinco puntos de su §1.2 y §3 comprobados
contra los bytes del fichero:

| afirmacion | comprobacion |
| :--- | :--- |
| cabecera en `0x007FC0` con titulo `Star Ocean` | ✓ |
| unico `JML $C00000` en `0x007EB9` (= NMI `$00:FEB9`) | ✓ `5C 00 00 C0` |
| vector IRQ `$00:FEBD` -> `JML $C00221` | ✓ `5C 21 02 C0` (y **coincide con `config/bankC0.cfg`**, que ya llamaba `IrqHandler` a `0221`) |
| `$C0:0000` = offset `0x000000` (MMC del S-DD1: 4 paginas de 1 MB en `$C0-$FF`; `$C6:2D95` = `0x062D95`) | ✓ coherente con el comentario de `bankC0.cfg`; la regla `offset = (banco-0xC0)<<16` para `$C0-$CC` |
| `FUN_c00221` 3 salidas y terminadores en `025E/02AF/02D5` | ✓ los tres son `40` (RTI) |
| `FUN_c08a5b` termina en `8C36`; `FUN_c05193` en `51C5`; `C8:0790` en `807AE`; `C8:07AF` en `807B3`; `C6:2D95` en `62DAD` | ✓ `60`/`6B`/`6B`/`6B`/`6B` |

Su `analisis/c0_bloques.json` es lo mas valioso del lote: **bloques con final
medido y su terminador** (`["8812","8C36","8C37",455,732522,"RTS"]`,
`["5193","51C5","51C6",27,115177,"RTL"]`, `["0221","025E","025F",33,35442,"RTI"]`…)
y `c0_freq.json` con la frecuencia por direccion. Eso si es material para
rehacer `bankC0.cfg` (que hoy declara 19 funciones con finales redondeados
`0400/0600/0800…`, todas sin medir).

### 24.2 Lo que no se sostiene (dos afirmaciones)

* **`FUN_c003b4` `03B4-0451`, "157 bytes"**: el byte `0x450` es `37` y el
  `0x451` es `A9`; **ninguno es RTS/RTL/RTI**, y su propio `c0_bloques.json` no
  tiene bloque empezando en `03B4` (si tiene `0387-03B3` con RTS). De las cinco
  funciones medidas, esta es la unica sin terminar de verificar.
* **`$C0:5151` es "duplicado exacto" de `$C0:5193`**: **falso**. Se comparan los
  bytes: `5151` empieza con un envoltorio `E0 73 B8 D0 DC AB 28 6B`
  (`CPX #$73 … RTL` en `5158`); el cuerpo arranca en `5159` y coincide con
  `5193` solo en **8 bytes** (el prologo `08 8B E2 20 A9 7E 48 AB` = `PHP PHB`
  / `SEP #$20` / `LDA #$7E` / `PHA` / `PLB`); desde ahi el resto son 10/58
  bytes iguales. Son **dos rutinas hermanas con el mismo prologo y constantes
  ajustadas** (p. ej. `F0 12` vs `F0 11`), no copias identicas: sirve para
  elegir donde cortar, no como "una se mide y se replica".
* Su §1.1 avisa de que `$C6` no aparece en 2,4 M instrucciones de `$C0` — pero
  **se contradice con `MASTER_StarOcean_Knowledge.md`** (mismo lote, 2 h antes),
  que da `$C2` 54,3 % y `$C6` 18,7 % como los dos bancos dominantes. Las dos no
  pueden ser verdad. Las trazas que tenemos **no lo resuelven**: el TSV de
eventos solo guarda E/S de registros (kinds `w214x`, `sd2100`, `keyon`…), **no
  instrucciones ejecutadas**. Para zanjarlo hace falta nuestro propio
  instrumento: un contador por banco en el puente (cada cuerpo AOT ya se
despacha por banco y el interprete conoce `K:PC`). Nada de eso existe hoy
  (`grep` de `per_bank|bank_exec|by_bank` en el motor: 0).

### 24.3 Nota legal sobre `analisis/`

`c0_uniq.json` y `c0_lines.txt` (32 MB, 2.436.154 lineas) son **bytes de la ROM
cruspuestos** (contenido del cartucho). No pueden entrar al repo `StarOceanSNESRecomp`
ni a `generated/`: solo las estadisticas (`c0_freq.json`, `c0_bloques.json`) son
publicables.

### 24.4 Las trazas de Mesen: el replay sirve, las columnas de estado NO

`TracesMesen` = 2 sesiones; la buena es la 2.a (13:43:56 -> 14:01:36, `fr=29560`,
`kon=28295`, sin el aviso de reset que aborted la 1.a). Contenido:

| fichero | estado |
| :--- | :--- |
| `*_replay.txt` | **util** ya: 488 pulsaciones, `fr 1173…29327`, mascara en orden `$4218`, cabecera `# replay para el motor recomp` = formato de `SNESRECOMP_REPLAY_FILE`. Es el input largo que faltaba (8 min, con musica: `kon` crece de 0 a 28.294). |
| `*_trace.tsv` | 29.560 filas × 34 columnas. **Vivas**: `fr in pin btn master cyc pc a x y sp r2140 w2140 spcw ini kon konf spc* r4212 hc sw4200`. **Muertas**: `bright bg scan ppufr p db` = `0`/`00` en **las 29.560 filas** (INIDISP no puede ser 0 con el juego en pantalla). |
| `*_events.tsv` | 1,46 M de eventos de **E/S de registros** (no hay eventos de instruccion). |
| `*_trace_status.log` | la sesion, el flag de reset y el volcado de claves de `getState()` que se hizo para depurar lo anterior. |

**Prueba de que las columnas de estado estan muertas** (invariante falsable:
`bright` debe ser el ultimo valor escrito a `$2100` del frame): hay 17.247
frames con `ini=80+0F` y **`bright=0` en todos ellos**. Mientras eso no se
arregle, cualquier conclusion que use INIDISP/BGMODE/scanline/`p`/`dbr` de este
trace mide ceros. El script (`tools/mesen_so_trace.lua`) lee
`ppu.screenBrightness`, `ppu.bgMode`, `ppu.scanline`, `ppu.frameCount` con
`nz(g(ppu, …), 0)`, y las claves que existen de verdad en `getState()` (volcado
en el `.log`) son `cpu.ps`, `cpu.dbr`, `ppu.screenBrightness`…; hay ademas dos
nombres mal en las columnas de CPU (`p` y `db` en vez de `ps` y `dbr`). Tambien
la **numeracion del comentario de cabecera esta desplazada una columna** desde
`p`/`bright` (`# 14 bright` cuando `bright` es la 15 en la fila de cabecera).

Donde si cruza con nosotros: la columna **`hc`** (instrucciones en
`$C0859D-$C085D0`) da **261.614 instrucciones en 284 frames**, con picos de
18.612 (fr=83), 17.575 (fr=11.578), 15.928 (fr=28.311)… y `fr=1` con NMI a 0
para los primeros 18.035 frames. Es el **mismo bucle caliente** que medimos el
29-09 en el recomp (~25.000 instrucciones interpretadas/frame en el hueco del
logo): el trabajo es real del invitado, no una lentitud nuestra, y la palanca
correcta sigue siendo llevarlo a AOT. El `sdnmi` (NMIs por frame) es `0` en
18.157 frames y `1` en 11.403, con **una sola corrida de 18.035**: eso no cuadra
con un juego a 60 fps con musica sonando, asi que **ni `sdnmi` ni su corrida se
deben usar** hasta que el instrumento se revalide. **Hipotesis ya confirmada en
§25.2 para esa corrida: el juego lleva NMI deshabilitada a proposito**
(`[fstate] r4200=21`, bit 7 a 0, `nmiEn=0`, con V-IRQ activa `vIrq=1`) y espera
el vblank sondeando `$4212`, asi que `sdnmi=0` puede ser correcto. El PC del
trace (`pc`) NO se puede comparar contra nuestro `resume=` por indice de frame:
los dos relojes no van juntos (ver §25).

## 25. Un guion de entrada de hardware va keyeado al RELOJ, no al frame (2026-09-30)

### 25.1 El sintoma que lo destapo

Tres corridas guiadas por `TracesMesen/..._replay.txt` (`build-prof` 15:59 y
16:01, `build-dev` con sondas 16:03) mostraban en la ventana la partida
**parada en el menu de seleccion de nombre**; la de 16:01 sin musica (iba en
turbo, que por diseño no se escucha) y la de 16:03 con musica. El usuario lo
leyo, con razon, como "se atasca ahi". **No es el juego: es el fichero.**

### 25.2 Medido (mismo build, mismo tramo de 4.000 frames de invitado)

| | keyeado al indice de frame (`replay.txt`) | keyeado al master (`mesen_master.txt`) |
| :--- | :--- | :--- |
| frames con `pad!=0` entregados | **9** | **14** (los 14 que hay en la grabacion) |
| primera pulsacion (A, fr=1173 = master `419.139.852`) | **no llega al invitado** | aterriza en host f=1093 con key `419.194.234`: **+54.382 master ≈ 7 ms** |
| desfase de relojes en fr=1170 | nuestro invitado va **+27.710.032 master (≈2,4 s) adelantado** | el keyeo lo absorbe |
| estado final en f=4.000 | `resume=C2FCA0`, AFB=8C, E4=005D (aparcado) | `resume=C62D9F`, PB=`$C6`, AFB=30-35 |
| resultado | menu quieto | **la partida avanza, con musica** |

Causa: nuestro invitado **no** va al mismo tiempo que el hardware en el mismo
indice de frame (el boot se comprime y a fr=4.000 vamos ~2 % por delante:
`master` 1.458.061.454 vs 1.429.413.536). Y la clave del replay se muestrea una
vez por frame de host, asi que una pulsacion de 4-5 frames de invitado (60-80 ms)
cae en otro instante del juego o fuera de la ventana. Dos sintomas que parecian
uno: el `r4200=21` (`nmiEn=0`, con `vIrq=1`) que se ve en el `[fstate]` explica
tambien el `sdnmi=0` de la traza de Mesen (§24.4).

### 25.3 El arreglo, ya en el repo

* `tools/replay_clock.py` — el guion **declara su reloj** en la cabecera
  (`# clock: master`) y `verificar.py` / `audio_health.py` lo aplican solos. Un
guion sin directiva se sigue keyeando al frame, como `grabada.txt`.
* `tools/mesen_replay_por_reloj.py` — convierte el `*_trace.tsv` de Mesen en un
guion keyeado a `master`/`cpu`/`frame`. Reproduce **byte a byte** los eventos que
funcionaron.
* `tools/input_scripts/mesen_master.txt` — la sesion completa de Mesen: 29.560
frames, **11.664 con pulsacion**, 489 eventos de cambio, primera clave 306.900 y
ultima 10.480.422.216.
* Puerta: `python tools/verificar.py --script=mesen_master.txt` → audio PASA
(`16 s con musica de 25 s`, sin silencio absoluto) y **A/B 2.100/2.100
byte-identico** contra su baseline propio (`build-dev/Release/logs/`
`golden_fstate_mesen_master.log`, local como los demas).

### 25.4 El desfase de relojes NO es un error de ritmo (medido 2026-09-30)

La duda razonable era: si a fr=4.000 vamos ~2 % por delante, ¿corremos el juego
rapido? La respuesta, medida sobre la corrida master-keyeada de `build-dev`
(4.000 frames) contra el trace, es **no**:

* **Avance de reloj por frame** en regimen (f>=1000, 3.000 frames): **mediana
  357.368 master**, valor mas frecuente 357.368 (568 veces) y **2.991 de 3.000**
  en el rango 350k-400k. Hardware: `1364 x 262 = 357.368`; Mesen da mediana
  357.366 con solo dos valores distintos. **El frame dura lo que el de
  hardware.** El jitter del borde es +-1 dot (valores 357.356-357.380) porque el
  borde lo marca la entrega del vblank/IRQ, no un contador de linea.
* Lo que si hay es **7 frames "lote"** (0,49-2,65 M) y **3 frames "cortos"**
  (42.992-256.454), siempre pegados unos a otros: f=1690 (2,46 M) + f=1691
  (42.992); el racimo f=2021-2028 (2,65 / 0,50 / 1,73 / 0,50 / 1,20 / 0,77 M)
  con f=2023 (256k) y f=2028 (250k) en medio. Son los tramos de carga (boot y
  S-DD1): el borde del frame de host **no esta clavado en el vblank**, lo marca
  donde el motor decide ceder (quiescencia/deadline).
* **Exceso neto de ese tramo: +6.789.974 master** (lotes +7.312.440, cortos
  -522.466) ~ **+19 frames de hardware** que el indice no cuenta.
* El desfase total es **escalonado**, no lineal: +22,2 M ya en fr=4 (boot),
  +24,0 M en fr=500, +28,6 M en fr=1000, +30,4 M en fr=2000, +35,4 M en fr=3000
  y plano hasta fr=4000 = **+99 frames de hardware ~1,65 s**. En fr=1173 (la
  pulsacion de New Game) ya ibamos ~62 frames por delante: eso es exactamente
  por lo que la entrada caia en otro instante del juego (§25.2).

Consecuencias: (1) para keyear entradas o comparar contra hardware la clave
valida es el **reloj de invitado**, no el indice de frame (ya esta asi en la
puerta, §25.3); (2) el desfase se concentra en los **caminos de fast-forward**
(quiescencia/deadline), que son los conservadores: no es un bug de timing de CPU,
es el borde del frame; (3) no afecta al ritmo percibido (mediana exacta) ni al
audio (la tasa se deriva del productor, §22.12).

### 25.5 Lo que deja abierto
* El cuelgue **manual** e intermitente del §16.5 sigue sin explicacion: alli la
  entrada era a mano, no un replay, asi que el keyeo no lo cubre.
* Si el borde del frame deberia clavarse en el vblank del invitado (en lugar de
  ceder donde la quiescencia lo permita) es una decision de diseño, no un bug
  medido: el efecto esta acotado a los tramos de carga y no toca el ritmo.
* Cualquier conclusion sacada de corridas guiadas por un guion keyeado al frame
  (incluidas las de §16) es sospechosa y hay que **repetirla con el reloj**.

## 26. Reparto real del trabajo interpretado, por banco (2026-09-30)

Instrumento: `build-prof` (`SNESRECOMP_INTERP_PROFILE`, imprime la tabla por
banco al salir) + `tools/input_scripts/mesen_master.txt` (reloj de invitado) +
`SNESRECOMP_TURBO_BURST=0,29330` para que quepa en tiempo. El turbo no toca al
invitado (es justo lo que comprueba la prueba `turbo` de la puerta), asi que la
tabla vale. **29.331 frames = la sesion completa de Mesen. Total 164.462.778
pasos interpretados (5.607 por frame).**

| banco | PCs distintos | pasos LLE | % | acumulado |
| :--- | ---: | ---: | ---: | ---: |
| `$C3` | 3.939 | 56.575.298 | 34,4% | 34,4% |
| `$C6` | 5.440 | 53.856.107 | 32,7% | 67,1% |
| `$C0` | 6.656 | 22.842.731 | 13,9% | 81,0% |
| `$C2` | 9.036 | 12.996.603 | 7,9% | 88,9% |
| `$CC` | 4.395 | 6.990.091 | 4,3% | 93,2% |
| `$C8` | 2.767 | 6.648.460 | 4,0% | 97,2% |
| `$CB` | 883 | 2.265.077 | 1,4% | 98,6% |
| `$C1` | 4.777 | 820.797 | 0,5% | 99,1% |
| `$C9` | 2.220 | 374.879 | 0,2% | 99,3% |
| `$C4` | 267 | 342.484 | 0,2% | 99,5% |
| `$C5` | 218 | 273.706 | 0,2% | 99,7% |
| `$CA` | 4.355 | 238.415 | 0,1% | 99,9% |
| `$C7` | 516 | 196.071 | 0,1% | 100,0% |
| `$00` | 167 | 42.059 | 0,0% | 100,0% |

**Lectura:** `$C3` y `$C6` solos son **dos tercios** del trabajo interpretado; con
`$C0` y `$C2`, el **88,9 %**. Los dos bancos que el HANDOFF externo ponia como
prioridad (`$C8`, `$CC`) son el **8,3 %**.

**Unidad que cuenta:** esto son *pasos del interprete* (codigo LLE), no
ejecucion total. Los bancos con `.cfg` (`00 C0 C1 C2 C3 C9`) tienen parte de su
codigo ya en AOT y **no aparece aqui**; los que no tienen `.cfg`
(`C4`-`C8`, `CA`-`CC`) aparecen enteros. Por eso `$C6` (54 M) es el candidato
numero uno: esta **entero** en el interprete. Y el trabajo real de `$C3` es
mayor que los 56,6 M que se ven.

### 26.1 Contra los dos documentos externos (mismos datos, otra conclusion)

| banco | HANDOFF | MASTER | medido ahora (sesion completa) |
| :--- | ---: | ---: | ---: |
| `$C6` | "no aparece" | 18,7 % | **32,7 % (53,9 M)** |
| `$C3` | 1,0 M (~5 %) | 14,0 % | **34,4 % (56,6 M)** |
| `$C2` | 115 K | 54,3 % | 7,9 % (13,0 M; parcial, tiene AOT) |
| `$C8`+`$CC` | 15,2 M, "88 % del juego" | 3,8 % + 0,6 % | 13,6 M, **8,3 %** |

Los dos se equivocan en la misma direccion: **infravaloran `$C3` y `$C6`** y
sobrevalorar lo que ellos señalaron. La unica cifra que acierta es el `$C8` 3,8 %
del MASTER (medido: 4,0 %). No es cuestion de que un documento gane: **ninguno de
los dos se puede usar para priorizar**, y ahora hay tabla propia.

**Prioridad por datos:** 1) `$C6` (54 M, entero en LLE), 2) `$C3` (56,6 M LLE +
lo que ya va por AOT), 3) `$C0` (22,8 M), 4) `$C2` (13,0 M). Los "PCs distintos"
son el tamano del trabajo por banco (`$C2` 9.036, `$C0` 6.656, `$C6` 5.440...).

**Lo que falta para cerrar el reparto:** la mitad AOT. Cada bloque AOT llama a
`cpu_trace_block(cpu, pc24)` al entrar (existe ya en el motor), asi que un
contador por banco ahi —y, mejor, atribuir el delta de `master_cycles` a ese
punto— da la tabla complementaria. Sin eso solo se ve la parte interpretada.

### 26.2 La corrida larga iba a 1x: los sintomas de audio y de partida SON reales

Correccion de una conclusion mia. La corrida del 2026-09-30 16:13 se lanzo con
`SNESRECOMP_TURBO_BURST=0,29330` y `TURBO_PRESENT_EVERY=0`, y **no hubo turbo**:
el proceso arranco ~16:13:30 y el volcado se escribio a las 16:21:20, o sea
**470 s para 29.331 frames = 62 fps**, y el usuario la vio a velocidad normal. La
hipotesis "lo distorsiona el turbo" era falsa.

Causa medida: **`build-prof/Release/StarOcean.exe` era de las 2026-09-29 12:14**,
anterior a `src/main.c` (09-29 15:02, donde vive el turbo) y a los cambios de
motor de las 15:58 (`interp_bridge.c`, `common_rtl.c`). Un binario no ejecuta el
codigo que no existia cuando se compilo: **los `SNESRECOMP_TURBO_*` de esa corrida
fueron inertes** (por eso tambien la ventana se veia avanzar pese a
`TURBO_PRESENT_EVERY=0`). Leccion de metodo: **antes de leer una variable de
entorno como evidencia, comparar la fecha del exe con la de la fuente**; el log
no lo dice. El binario ya esta recompilado (2026-09-30 16:25).

Consecuencia: esos sintomas son estado del invitado y son fallos de verdad:

* la melodia se carga a medias y suena mal, y despues de la cinematica no hay
  musica;
* dialogos y SFX suenan en la cinematica y en la primera pelea; los de los
  **cofres no**;
* la partida se va por otro camino tras los cofres y **el personaje se queda
  clavado** al acabar la primera pelea. Ojo a la distincion: **los frames siguen
  contando** (el motor avanza y ejecuta codigo), asi que no es el cuelgue por
  force-blank que vigila `SNESRECOMP_HANG_GUARD`; es un estado de partida del que
  no sale, y pide volcado de estado + comparacion por reloj contra el trace.

El unico dato de audio limpio hasta ahora es el de la puerta con este mismo guion
y sin turbo: `16 s con musica de 25 s` (§25.3), que solo cubre los primeros ~25 s
(intro y menu), no la cinematica ni los cofres. **Siguiente medicion**: correr con
`SNESRECOMP_DSPREG_TRACE_FILE` (escrituras al DSP en la linea de tiempo del
invitado, incluido KON) y comparar por reloj contra los eventos `keyon`/`sdsp_*` y
la columna `kon` del trace de Mesen: si los key-on cuadran, el fallo esta en la
sintesis o en la entrega; si faltan, el driver del invitado ya se desvio.

### 26.3 Aviso sobre esta misma tabla

La tabla de §26 se midio con ese `build-prof` de las 12:14, o sea **con el motor
anterior a los cambios de las 15:58**. El reparto por banco no deberia moverse
(esos cambios tocan caminos de fast-forward y de audio, no que codigo se ejecuta),
pero **no esta verificado**: hay que repetir la corrida con el binario recompilado
antes de usar la tabla para priorizar AOT.

## 27. La entrada del replay se entregaba UN FRAME TARDE (2026-09-30)

### 27.1 El instrumento: alinear por reloj e interrogar al pad

El trace de Mesen trae, por frame, la mascara del pad, el master absoluto del
invitado, el PC, los registros de la CPU y el banco de datos
(`*_trace.tsv`, leyenda en sus 13 primeras lineas). Nuestro `[fstate]` imprime
`master`, `pad`, `PB`, `DB`, `resume`... en cada frontera de frame, asi que los
dos lados se pueden alinear **por reloj master** (`tools/divergencia_mesen.py`),
que es exacto, en vez de por indice de frame (§25).

Comprobado antes de sacar conclusiones:

* la columna `in` y la columna `pin` son **identicas en las 29.560 filas**, o sea
  Mesen no cambia el pad a mitad de frame: `in(fr)` es lo que el juego vio
  durante el frame `fr`;
* en regimen, nuestro master por frame avanza exactamente 357.368 ciclos
  (1364 x 262), y nuestra frontera de frame cae entre +50.900 y +52.800 ciclos
  (0,14-0,15 de frame) **despues** de la de Mesen: el residuo es siempre
  positivo, asi que nuestra frontera esta siempre por detras del inicio del frame
  de hardware.

Primera medida: la mascara de A que hardware tiene en los frames **1173-1177**
(el `New Game`) la entregabamos en **1174-1178**: misma duracion, un frame tarde.
El aparato de filtraciones, sin embargo, se mide con correlacion cruzada sobre
las 29.560 muestras (`tools/divergencia_mesen.py`), no con un caso suelto:

| desplazamiento `s` (comparamos nuestro pad contra `in(fr+s)`) | frames de cambio acertados |
|---|---|
| `s=-1` | **890/890 (100,00 %)** |
| `s=0` | 443/890 (49,78 %) |
| `s=+1` | 1/890 (0,11 %) |

`s=-1` perfecto significa que **la mascara que presentabamos durante el frame
`fr` era la que hardware tenia en `fr-1`**: toda transicion entraba un frame
tarde. Es un desplazamiento *sistematico*, no ruido de borde.

### 27.2 Mecanismo, que es una cuestion de semantica de la clave

El motor elige la mascara del frame que **va a ejecutar** leyendo el master **al
inicio** de ese frame (`replay_key_now()` + `replay_mask_for_key()` en
`src/main.c`, antes de `RunOneFrameOfGame`). Como los frames son contiguos en el
reloj, el inicio del frame `fr` de hardware es exactamente `M(fr-1)`, el master
del **frame anterior**. Pero `tools/mesen_replay_por_reloj.py` keyeaba cada
evento al master del frame **en que se observo el cambio**, que es el **final**
de ese frame (`M(fr)`): la clave queda dentro del frame siguiente, y la mascara
solo entra en vigor un frame despues. Medio frame de desfase de semantica se
materializa en un frame entero de retraso porque nos sobra 0,15 de frame de
residuo.

Arreglo: la clave de un evento es el reloj del **inicio** del frame en que la
mascara es valida, o sea el del frame anterior
(`mesen_replay_por_reloj.py --clave frame-start`, ahora por defecto; el
comportamiento viejo queda como `--clave frame-end` para reproducir guiones ya
validados). Verificado **sin recompilar**, simulando el cargador del motor sobre
el log que ya existia (`--simular`):

| guion | `s=0` | `s=-1` |
|---|---|---|
| viejo (`frame-end`) | 443/890 (49,78 %) | 890/890 (100,00 %) |
| nuevo (`frame-start`) | **890/890 (100,00 %)** | 443/890 (49,78 %) |

Que la simulacion del guion viejo reproduzca exactamente el fallo medido es la
validacion del simulador: predice 100 % en `s=0` para el guion nuevo.

### 27.3 Por que esto explica "el personaje se queda clavado"

En un recorrido guiado a mano, cada pulsacion y cada suelta entran un frame
tarde; el invitado recorre un poco mas de lo que debia en cada giro y acaba
contra una pared o fuera de la casilla que dispara el evento (el puente, la
puerta, el cofre). El motor sigue corriendo y **los frames siguen contando**
—justo lo que reporto el usuario— pero la partida ya no es la grabada. No es un
cuelgue por force-blank ni un bucle infinito: es **deriva de estado por entrada
desplazada**.

Corolario de metodo: con `s=+1` el acuerdo es del 0,11 %, o sea el pad correcto
no aparece en ningun vecino. Un desfase de entrada de un frame no se detecta
"mirando si el boton llega": hay que correlacionar contra hardware frame a frame.

### 27.4 Lo que NO arregla

El pad se entrega ahora en el frame correcto, pero eso no toca la sintesis de
audio ni la entrega: los sintomas de melodia a medias y de SFX de cofre
ausentes (§26.2) siguen abiertos y hay que medirlos con la comparacion de
key-on por reloj (`SNESRECOMP_DSPREG_TRACE_FILE` contra `keyon`/`kon` del
trace), sabiendo que el trace de DSP registra **cambios del espejo** y hardware
cuenta **escrituras al registro**, asi que hace falta un contador a nivel de
escritura en el motor para que la comparacion sea valida.

## 28. Fase 0: el build actual NO es byte-exacto contra LLE puro (2026-09-30)

### 28.1 La palanca y por que hacia falta una medicion nueva

La puerta A/B de `tools/verificar.py` compara una corrida contra **su propio
baseline**, asi que no puede ver que el camino AOT difiera del interpretado: las
dos corridas serian igual de divergentes y el A/B pasaria. La referencia de
exactitud del proyecto es el **interprete puro**, y el motor ya trae la palanca:
`SNESRECOMP_LLE_BOUNCE=0` desactiva el salto a los cuerpos AOT ("interpret-
everything behavior (A/B differential lever)" en `interp_bridge.c`), con el
criterio escrito alli mismo: *bounced (=1) vs interpreted (=0) must be
guest-state bit-exact; any persistent split is a recompiler bug*.

Experimento (`tools/ab_lle.py`): mismo binario (`build-dev`), mismo guion
(`tools/input_scripts/mesen_master.txt`, 490 eventos keyeados al reloj, el
arreglo de §27), 6.000 frames, con y sin bounce, en turbo y sin presentar
(`SNESRECOMP_FORCE_TURBO=1 SNESRECOMP_TURBO_PRESENT_EVERY=0`, o sea **ventana
en negro a proposito**: en esa configuracion no se juzga imagen ni sonido).

### 28.2 Resultado: primer frame distinto = `f=1687`

| campo | primer frame distinto |
|---|---|
| `cpu` / `master` (reloj) | **f=1687** |
| `resume` (PC muestreado) | f=1688 |
| `S` | f=1994 |
| `DB` | f=5533 |
| `PB` | f=5821 |
| `nmiEn`, `inidisp`, `pad`, `r4200`, `hIrq`, `vIrq`, `irq`, `nmi`, `vTimer`, `E4`, `DA`, `AFB`, `AFD`, `D01`, `DP` | identicos en los 6.000 |

En `f=1687` la diferencia es de **3 ciclos de CPU / 14 de master**, y aparece en
la zona `$C086xx` — el mismo bucle de handshake con la APU cuyo tramo caliente es
`$C0859D-$C085D0` (§26). El `resume` distinto (`C086BE` vs `C086C4`) es
consecuencia: el muestreo cae unos ciclos antes en el mismo bucle, no en otra
rutina.

**La deriva esta acotada, no crece**: delta de master entre ambos lados, en los
6.000 frames, `min = -48`, `max = +230`, mediana 0 (0,00013 de frame), y **en
ningun frame** el delta llega a un frame (0/6.000 con `|delta| > 357.368`). Los
campos de partida aguantan hasta `f=1993`, y `S`/`DB`/`PB` ahi tambien son
muestreos a distinto punto del mismo flujo. Reparto: 4.312/6.000 frames (71,9 %)
con reloj distinto y 1.656/6.000 (27,6 %) con `resume` distinto.

### 28.3 Conclusion

* Con el criterio estricto del proyecto (byte-exacto) **el build actual NO
  reproduce LLE puro: primer frame distinto `f=1687`**. La documentacion de
  `docs/BUILD.md` ya avisaba de la deriva del generador con otra medida
  (exe-regenerado vs baseline validado: 21.628/23.700 frames distintos desde
  `f1033`, -369.682 masters al final = 0,004 %); esta es la medida directa
  AOT-vs-LLE en el mismo binario y localiza el origen en el contaje de ciclos
  del handshake con la APU, no en la logica de partida.
* Lo que **si** queda descartado: que el AOT cambie el estado de partida o el
  numero de NMI/IRQ dentro de esos 6.000 frames. La discrepancia es de
  contabilidad de ciclos en un tramo concreto.
* Consecuencia para el plan de §4/§7: promover bancos no puede apoyarse en la
  puerta A/B actual. La puerta necesita el A/B **contra LLE** (`tools/ab_lle.py`)
  y la deriva del generador hay que cerrarla **antes** de ampliar cobertura.
* Pendiente de repetir sin turbo (aqui turbo es neutral para el invitado, ya
  validado 1.200/1.200 y 2.400/2.400) y de medir lo mismo con el `generated/`
  archivado en `StarOceanRecomp-legacy-2026-09-29/generated/` (bankc0 14 KB y
  bankc3 1 KB frente a los 502 KB y 55 KB actuales): eso separa "maquinaria AOT
  del motor" de "bancos nuevos mal promocionados".

## 30. Oraculo de progreso por el flujo de la APU, y la trampa del trace sin buffer

### 30.1 Dos intentos fallidos antes de dar con el observable

1. **PC del invitado**: no existe. `CpuState` no guarda PC (el codigo AOT usa
   control de flujo nativo y el LLE solo publica su punto de reanudacion), y el
   `g_dispatch_log` del motor solo registra transferencias indirectas.
2. **Registros de CPU por frame** (§29, `DESCARTADAS.md`): medido, inutilizables
   (A coincide en el 0,2 %) porque manda el instante de muestreo.

El observable que si vale es el **flujo del CPU a los puertos de la APU**
(`$2140-$2143`). Lo produce el driver de sonido del juego, que es esclavo de la
logica de partida: cambia cuando la partida cambia de escena, de musica o dispara
un SFX. Ademas es un observable **acumulativo** (cuenta de escrituras por frame y
secuencia de valores), inmune al desfase de borde de frame.

Instrumentos: el motor ya trae `SNESRECOMP_APU_PORT_RW=<ruta>` (cada lectura y
escritura del CPU al puerto, con frame de invitado y master) y el trace de Mesen
trae el mismo flujo del lado hardware en `*_events.tsv` (`src=cpu`, `kind=w214x`,
con `fr`, `master`, `addr`, `val`) mas el conteo por frame en las columnas
`r2140`/`w2140` del `*_trace.tsv`. El comparador es `tools/oraculo_apu.py`.

### 30.2 Trampa medida: el trace sin buffer hace que el invitado se arrastre

`SNESRECOMP_APU_PORT_RW` escribia con `setvbuf(_IONBF)`. En el arranque, el IPL
polea `$2140` miles de veces por frame, asi que eso es un `write()` del sistema
por linea: medido, **3.348 lineas/s y 3 frames de invitado en 25 s**. En pantalla
eso es una ventana negra con el contador clavado en `f2`, que parece un cuelgue y
no lo es. Arreglado en `cpu_state.c`: buffer de bloque de 1 MB, volcado una vez
por frame, y filtros `SNESRECOMP_APU_PORT_RW_W` / `_R` (0 apaga cada sentido) y
`SNESRECOMP_APU_PORT_RW_FROM=<frame>`. Con buffer y solo escrituras: **2.861
frames en 22 s**, la velocidad normal del motor.

## 31. Los parones y el bloqueo del puente son codigo INTERPRETADO caliente (2026-09-30)

Medido con `SNESRECOMP_PHASE_MS=1` (coste por intervalo) y el muestreador de PCs
calientes, en la sesion completa de Mesen con la entrada keyeada al reloj.

**Coste por frame:** el primer intervalo del arranque (subida del SPC/S-DD1) es
`emu=81,66 ms` (12 FPS); en regimen sano `emu=3,00 ms` (236 FPS). El tramo de
**estado bloqueado** se sostiene en `emu=12,5-13,7 ms` (61-66 FPS) — cuatro veces
el coste sano. Entre medias hay picos puntuales (27,21 ms en un intervalo), que
son los parones que se ven.

**Donde se va:** el bloque de PCs calientes del tramo bloqueado es

| PCs | muestras | banco | AOT |
|---|---|---|---|
| `$C62D95-$C62DA9` | ~1,0-1,4 % cada uno (~11 % el bloque) | `$C6` | **ninguno** |
| `$C0516C-$C0518E` | ~0,7 % cada uno | `$C0` | parcial |

Los dos bucles son codigo del invitado y estan **enteros en el interprete**: el
banco `$C6` no tiene ni una linea de C generado (§26: 40,0 M pasos LLE, el
segundo mayor del reparto) y el tramo `$C0518x` de `$C0` no esta cubierto por su
cfg. Es decir, el bloqueo del puente no es un fallo de logica de partida: es el
juego esperando en un bucle que interpretamos a ~0,9 M instrucciones/s mientras
el resto del frame ya va en C. La palanca correcta es la Fase 2 del plan AOT
(promocionar `$C6`, empezando por `$C62D95-$C62DA9`), no tocar el motor.

Corolario de metodo: `SNESRECOMP_FRAME_STATE` y `SNESRECOMP_PHASE_MS` juntos
localizan un atasco sin necesidad de saber el frame: el coste por frame dice
*cuando* y el muestreador de PCs dice *donde*.

## 32. Lista de trabajo AOT a partir del manifiesto del generador (2026-09-30)

### 32.1 Ghidra: estado real y regla de uso

Headless si funciona en esta maquina, con dos trampas ya resueltas:

* la extension SNES esta instalada DOS veces (en la instalacion y en la carpeta
  de usuario de Ghidra) y Ghidra aborta con "Multiple modules collided with same
  name". No hay que borrar nada: se aisla con `APPDATA=<dir sin espacios>` para
  el proceso hijo (en Windows el directorio de usuario sale de APPDATA, no de
  `user.home`; y `user.home` ademas se parte por palabras porque `VMARG_LIST` va
  sin comillas, asi que una ruta con espacios rompe el classpath).
* JDK: no hay `java` en el PATH pero si
  `C:\Program Files\Eclipse Adoptium\jdk-25.0.4.101-hotspot`; se pasa por
  `JAVA_HOME` y `analyzeHeadless` arranca.
* **El scripting Java no compila** en este montaje (`JavaScriptProvider` lanza
  ClassNotFoundException sin error de compilacion visible). PyGhidra viene como
  wheel en `Ghidra/Features/PyGhidra/dist`, sin instalar; usarlo exige decidir
  aparte la instalacion de ese paquete. **Bloqueo conocido.**

Regla de uso acordada (aviso del agente anterior, confirmado): **no mandar a
Ghidra descompilar bancos enteros**; su analisis lineal inventa funciones y eso
seria basura metida en el cfg. Ghidra aporta *estructura* (codigo vs datos,
limites, destinos de llamada y tablas de salto) y esa estructura se **cruza
siempre con lo que se ha medido que se ejecuta** antes de tocar un cfg.

### 32.2 Lo que ya dice el generador, y que no estabamos usando

`generated/program_manifest.json` (formato v3) trae, por nodo: entrada
(`pc24` + estado `m/x`), `min_pc24`/`max_pc24`, `instruction_count`,
`disposition` y **`reasons`**. Valores reales de `disposition`: `aot_eligible`
(tiene cuerpo en C) y `lle_only` (se queda en el interprete).

99 nodos, 75 raices. Motivos agrupados de los `lle_only`: `unproven_call` 32
nodos (6.917 instrucciones), `truncated_call_continuation` 10 (2.212),
`has_lle_indirect_edge` 2 (1.306), `cop` 4 (506), `brk` 21 (254),
`structural_poison` 22 (491). Cada uno es un bloqueo **concreto y arreglable en
el recompilador**, no una impresion: el de mas evidencia es `C00221-C002F3` (el
manejador de IRQ, 280 instrucciones y **188 de 29.560 frames muestreados**),
`lle_only` por `truncated_call_continuation` y `unproven_call_at_C0024E_to_C002F6`.

### 32.3 Medida de cobertura (`tools/trabajo_aot.py`)

Cruce de los 748 PCs distintos que se ven en el trace de hardware (una muestra
por frame, 29.560) contra los rangos de los nodos:

* **99,0 % de las muestras caen fuera de cualquier nodo**, y solo el 5,1 % del
  banco `C3` cae dentro de codigo con C generado;
* el codigo donde el juego **espera** cada frame (justo lo que pagamos en el
  interprete) esta en bancos que no tienen ni cfg: `C2` (18.067 muestras), `CC`
  (5.731), `C0` (2.544), `C1` (1.467), `C8` (1.244), `C6` (241);
* **seis bancos sin ningun cfg**: `C1`, `C6`, `C7`, `C8`, `CA`, `CB`, `CC` (el
  bucle del paron del puente, `$C62D95-$C62DA9`, esta en `C6`: no es que falte
  una funcion, es que el banco entero no esta declarado).

Cautela de lectura: 748 PCs es la *muestra de frontera de frame* (donde el
invitado espera), no todo el codigo ejecutado (nuestro perfil vio 44.788 PCs
distintos y no los vuelca completos: solo imprime los 60 primeros). Para la
lista completa hay que volcar el histograma entero del perfil; esta medido lo que
se puede medir hoy.

## 33. El cfg NO es lo que sostiene el AOT: cobertura medida y semillas que no
convierten nada (2026-09-30)

### 33.1 Instrumento: el histograma completo ya termina solo

`interp_hist_dump` se disparaba solo desde `atexit`, asi que obtener el
histograma exigia que **un humano cerrase la ventana**. Ahora hay ademas
`SNESRECOMP_INTERP_PROFILE_FULL_AT=<frame>`: vuelca UNA vez al alcanzar ese frame
de invitado sin cortar la ejecucion (idempotente con el de salida).

`tools/perfil_interp.py --frames N` lanza la corrida como se debe: reloj del
guion por `tools/replay_clock.py`, turbo sin presentar, y
`SNESRECOMP_EXIT_AT_FRAME=N` para que **el motor salga solo** y el `atexit`
vuelque. Medido: 6.000 frames -> 21.297 PCs distintos, **20.741.683 pasos
interpretados**, sin intervencion humana. Es la fuente correcta para ordenar la
lista de trabajo (cubre todo el codigo interpretado, no una muestra de frontera
de frame como el trace de hardware). `tools/trabajo_aot.py --hist <fichero>` la
consume.

Dos trampas de entorno, las dos silenciosas y las dos ya cerradas:

* **`SNESRECOMP_REPLAY_CLOCK` no es la cadena que el motor imprime.** El cargador
  solo entendia `cpu`/`master`; pasar `guest-master-clocks` (el texto del mensaje
  de log) degradaba a **frames de host**, la entrada aterrizaba en instantes de
  invitado equivocados y el juego se quedaba clavado en el titulo con las
  estrellas. Ahora acepta tambien esos nombres y con cualquier otro **aborta**
  (`exit(2)`) en vez de adivinar.
* **`SNESRECOMP_FRAME_DEADLINE` NO es una salida**: es el modelo de tiempo, y con
  deadline > 0 el invitado cede el frame por deadline en vez de por quiescencia y
  el DSP deja de tocar nada (§22.13). La salida limpia es
  `SNESRECOMP_EXIT_AT_FRAME`. Un lanzador que confunda ambas no mide lo que dice
  medir.

### 33.2 Reparto del trabajo interpretado (6.000 frames, 20,74 M pasos)

| banco | pasos | % |
|---|---:|---:|
| `C3` | 7.551.079 | **36,4 %** |
| `C0` | 6.082.604 | **29,3 %** |
| `C6` | 4.185.800 | **20,2 %** |
| `C2` | 997.185 | 4,8 % |
| `C8` | 730.547 | 3,5 % |
| `CC` | 477.963 | 2,3 % |
| `CA` · `CB` · `C9` | 638.569 | 3,1 % |
| `C5` · `C4` · `C7` · `C1` · `00` | 77.118 | 0,4 % |

Tres bancos son el **85,9 %** del trabajo. Los seis sin ningun cfg declarado
(`C1`, `C6`, `C7`, `C8`, `CA`, `CB`, `CC`) suman el 31 %.

### 33.3 Cobertura real del AOT: 0,36 % (cfg) vs 10,20 % (manifiesto en disco)

Cruzando el histograma con los rangos `min_pc24..max_pc24` de los nodos:

| manifiesto | nodos | `aot_eligible` | pasos dentro de C | en `lle_only` | **sin nodo** |
|---|---:|---:|---:|---:|---:|
| `generated/` (en disco) | 99 | 67 | 10,20 % | 31,67 % | 58,13 % |
| **regenerado hoy con el MISMO cfg** | 91 | 47 | **0,36 %** | 0,22 % | **99,42 %** |

La diferencia no es del cfg: es que **el generador actual no reproduce el
`generated/` de disco** (la deriva que ya avisaba `docs/BUILD.md`, §28). El mismo
arranque `C38F50` decodifica **442 instrucciones** en el manifiesto guardado y
**3** en el regenerado; `C00221` (IRQ) decodifica 280 y **0**. En el regenerado la
decodificacion se corta por `has_lle_suppressed_call_edge` /
`truncated_call_continuation`. Conclusion operativa: **la cobertura que creiamos
tener no esta demostrada por el toolchain actual**, y la puerta A/B de hoy no
puede verlo porque se compara consigo misma (§28).

### 33.4 El cfg de `$C0` es relleno inventado

`bankC0.cfg` declara 20 funciones de exactamente `0x200` en `0x200`
(`NmiHandler 0000 end:0221`, `Sdd1Init 0400 end:0600`, `SpcUpload 0600 end:0800`,
... `NmiComplete 2600 end:2800`). Eso no es un mapa de nada: es el motivo de que
"18 de las 19 funciones declaradas no se ejecuten nunca" (§32.2). El codigo que
`C0` ejecuta de verdad, segun el mapa de bloques de Ghidra del agente anterior,
esta en `84B8-8C37` (732.522, 663.446 y 406.040 ejecuciones) mas `0221-025E` (el
IRQ real, que acaba en `RTI`), y **no esta declarado**. Regla: un cfg se genera a
partir de evidencia (bloques medidos), no se escribe a ojo.

### 33.5 Resultado NEGATIVO: 20 semillas de cfg no convierten ningun nodo

Hipotesis: los motivos `unproven_call_at_<site>_to_<target>_m?x?` son
*declaraciones que faltan*, y el parser de cfg acepta `func NOMBRE <pc>` **sin
`end:`** (decodifica hasta el terminador), asi que declarar esos 20 destinos
como raices deberia probar su salida y desbloquear al llamante.

Se implemento (`tools/aot_seeds.py`: 20 destinos -> 12 en `00`, 5 en `C0`, 3 en
`C3`) y se midio contra el cfg pristino en la misma corrida:

* **0 nodos pasan a `aot_eligible`** y 0 regresan;
* +29 nodos nuevos (6 elegibles) que cubren **125.160 pasos = 0,6 %**;
* la cobertura dentro de C no se mueve: 74.993 pasos en ambos casos.

Mecanismo: los nodos que importan no estan bloqueados solo por el callee
desconocido. El nodo que mas trabajo interpretado acumula de toda la sesion,
`C38F50` (39.356 pasos, `C3`), es `lle_only` por
`has_lle_suppressed_call_edge` + `truncated_call_continuation`; el IRQ
`C00221` por `empty_decode`; y los de `00` por `cop`/`brk` = **datos
decodificados como codigo**. Conclusion: **el cfg no es la palanca**. La palanca
son los bloqueos estructurales del analizador (`has_lle_suppressed_call_edge`,
`truncated_call_continuation`, `structural_poison`) y la deriva del generador.
Las semillas se retiraron (`config/` queda pristino): no demuestran ganancia y
cambiar el `generated/` sin puerta A/B es exactamente lo que §28 prohibe.

### 33.6 Herramientas dejadas

| herramienta | para que |
|---|---|
| `tools/perfil_interp.py` | corrida de perfil que termina sola y vuelca el histograma |
| `tools/trabajo_aot.py --hist` | lista de trabajo ordenada por trabajo interpretado |
| `tools/aot_seeds.py` | semillas de cfg desde los `unproven_call` (util cuando el analizador sepa probar salidas) |

## 34. El artefacto AOT del arbol no es reproducible, y `force_lle` clava el banco
caliente al interprete (2026-09-30)

### 34.1 Cual de los dos artefactos es cual (medido)

Al regenerar con el toolchain comprometido y el cfg del repo salen **91 nodos,
47 `aot_eligible`, `bankc0_v2.c` = 14.201 B, `bankc3_v2.c` = 1.130 B**. Eso es
**identico, byte a byte, al snapshot archivado**
`StarOceanRecomp-legacy-2026-09-29/generated/` (mismos tamanos, mismos 91 nodos,
mismas 47 elegibles). Es decir: **el toolchain de hoy reproduce el baseline
validado**.

Lo que hay en el arbol es otra cosa: **99 nodos, 67 elegibles,
`bankc0_v2.c` = 502.461 B, `bankc3_v2.c` = 54.754 B**. Y no se reproduce con
ninguna entrada del repo:

| entrada | nodos | elegibles |
|---|---:|---:|
| emision de hoy, cfg del repo, backend nativo | 91 | 47 |
| idem, backend **python** | 91 | 48 |
| idem **sin** `--cfg-roots` | 10 | 10 |
| idem, 3 pasadas seguidas (¿punto fijo?) | 91 | 47 (identicas) |
| **`generated/` versionado** | **99** | **67** |

Descartado como causa: la cache por digest (3 pasadas identicas), el ROM (sha1
correcto `A616EE34...`), la emision python vs nativa (91 vs 91 nodos) y `config/`
(sin commits desde `e112a58`, 2026-09-03). `generated/` se versiono en el commit
`9208252` (2026-09-28 17:13), **anterior** a `b3423a5` ("AOT v2", 2026-09-29
15:42) del submodulo. Conclusion: el artefacto del arbol es **anterior al
toolchain actual y no verificable**; el validado si lo es.

### 34.2 La causa de que `$C0` no tenga C: 14 lineas `force_lle`

`bankC0.cfg` declara 14 `force_lle` cuyos valores (`824E`, `8289`, `8319`,
`8496`, `84B8`, `8500`, `8594`, `8598`, `85FE`, `878C`, `87B7`, `8812`, `887F`,
`8A5B`) son **los arranques de los bloques calientes del driver S-DD1**. Aislado
por familias de directivas, con el mismo cfg de bloques medidos:

| cfg de `$C0` | nodos | elegibles | pasos interpretados cubiertos por C | cobertura |
|---|---:|---:|---:|---:|
| el inventado del repo (20 rangos de 0x200) | 91 | 47 | 74.993 | 0,36 % |
| **desde bloques medidos (mapa de Ghidra)** | 46 | 21 | **510.510** | **2,46 % (6,8x)** |
| + los 27 `exclude_range` | 45 | 21 | 510.510 | 2,46 % (inocentes) |
| + los 14 **`force_lle`** | 34 | 11 | 24.345 | **0,12 %** |

Y no es sutil: con `force_lle` el C emitido para `$C0` son **20 envoltorios que
hacen `interp_tier_dispatch`** (14.731 B), mientras que el cfg medido emite
cuerpos reales (`Ghidra_84B8`, `Ghidra_8594`, `Ghidra_85FE`, `Ghidra_878C`,
`bank_C0_85CC`..., 75.857 B). Es decir, el banco `$C0` entero -- **29,3 % del
trabajo interpretado, el NMI, el IRQ y el driver del S-DD1**, y el sitio donde el
juego espera cada frame -- no tiene ni una linea de C.

Comprobacion cruzada de que no es un problema de mapeo ni de datos: los bytes de
`ROM[0x0221]` son `78 8B 0B C2 30 DA 5A 48 A9 00 00 5B E2 20 48 AB AD 11 42 ...`
(65816 real: `SEI/PHB/PHD/REP #30/...`) con **RTI en `$025E`**, que es exactamente
el bloque que Ghidra midio (`0221-025E`, 33 instrucciones, 35.442 ejecuciones).
El mapeo lineal es correcto; el que no decodifica es el cfg.

### 34.3 Nexo medido con el audio

* zona del manejador de IRQ y el tick del driver (`C00221-C004FF`): **431.583
  pasos = 2,1 % de TODO el trabajo interpretado** (7,1 % del banco). Es donde 19
  situa el tick del driver de sonido, `C0:032D`;
* los tres bloques que `force_lle` clava (`84B8`, `8594`, `8812`): **8,7 % del
  trabajo total**.

Prediccion falsable, para no volver a "parchear el audio": quitar esos
`force_lle` (arreglando antes la razon por la que se pusieron) **tiene que**
cambiar el comportamiento del driver de sonido. Eso se prueba con la puerta A/B
y el volcado de PCM, no escuchando.

### 34.4 Como no repetir esto

* `tools/cfg_desde_bloques.py`: genera un cfg de banco desde bloques medidos y
  **avisa** del coste de conservar `force_lle` (2,46 % -> 0,12 % en `$C0`).
* `tools/perfil_interp.py` + `tools/trabajo_aot.py --hist`: cobertura medida.
* Regla: **ningun artefacto AOT sin poder regenerarlo desde el repo**. Si no se
  reproduce con las entradas versionadas, no es un baseline: es una foto.

## 35. La exactitud es una propiedad DEL ARTEFACTO AOT, y la receta que sube la
cobertura al 51 % sin romperla (2026-09-30)

### 35.1 El A/B contra el interprete puro distingue los tres artefactos

Mismo binario (`build-dev`), misma palanca (`SNESRECOMP_LLE_BOUNCE=1` AOT vs `=0`
interprete puro), mismo guion keyeado al reloj, 6000 frames, sin presentar:

| artefacto AOT | C de `$C0` | A/B byte-exacto |
|---|---|---|
| validado (`legacy-2026-09-29`) | 14,2 KB (stubs) | **identico 6000/6000** |
| bloques medidos de Ghidra para `$C0` | 75,9 KB (cuerpos reales) | **identico 6000/6000** |
| el del arbol (1,39 MB) | 502,5 KB inventados | **NO: primer diff `f=1687`** |

Lectura: la divergencia AOT-vs-LLE **no es del motor, es del artefacto**. Meter C
de `$C0` codigo real no la rompe; el artefacto que hay en el arbol si, y es el
unico que no se puede regenerar (34.1). Consecuencia practica: **la puerta para
cualquier expansion AOT es `tools/ab_lle.py`**, y se corre en 4 minutos.

### 35.2 Lo que NO funciona (dos intentos, con numeros)

| via | resultado |
|---|---|
| destinos sin cuerpo del manifiesto (`tools/aot_seeds.py`) | **0** nodos convertidos (33.5) |
| PCs mas calientes del histograma como entradas | 0,36 % -> **0,59 %** |

El segundo caso merece el diagnostico: un PC caliente del histograma es una
*mitad de funcion* (el cuerpo de un bucle de espera), y el analizador no puede
emitir C para un cuerpo que empieza a mitad: `$C6` (4,2 M pasos, 20,2 % del
total) apenas se movio. Lo que funciona en `$C0` es el **inicio de funcion**.

### 35.3 La receta que funciona: destino de llamada x ejecucion

`tools/cfg_entradas_llamada.py`: escanear la pagina 0 del MMC (bancos `$C0-$CF`,
`ROM[0:0x100000]`) buscando operandos de `JSR`/`JMP` (mismo banco) y
`JSL`/`JML` (banco explicito), y quedarse solo con los destinos cuyo PC **se
ejecuta** en el histograma (eso es lo que quita los falsos positivos de datos que
se leen como opcode). Sin `end:`, el analizador descubre la extension.

| | nodos | elegibles | pasos interpretados dentro de C | sin nodo |
|---|---:|---:|---:|---:|
| base (validado) | 91 | 47 | 74.993 (0,36 %) | 99,42 % |
| **+ entradas de llamada en `C2..CC`** | **1.271** | **200** | **10.646.992 (51,33 %)** | **30,94 %** |

Y el A/B con ese artefacto: **identico 6000/6000 frames**, `master` final igual
(2.179.587.442). Es decir, **142x mas trabajo en C manteniendo la exactitud**.

### 35.4 Lo que falta antes de adoptarlo como artefacto del arbol

1. Los 8 cfg nuevos (`config/bankC4/C5/C6/C7/C8/CA/CB/CC.cfg`) ya estan en el
   repo: la regeneracion es reproducible.
2. Los 6000 frames cubren intro + menu de nombres + primer campo. **Falta el
   replay largo (23.590 frames)**: la escena que no se ejecuta no se valida.
3. No se ha sustituido `generated/`: cambiarlo es un acto deliberado, con el A/B
   largo delante. El artefacto generado esta en `out/aot-calls/`.

### 35.5 Nota operativa de PyGhidra (instalado hoy)

PyGhidra 3.1.0 quedo en el venv de Ghidra
(`%APPDATA%/ghidra/ghidra_12.1.4_PUBLIC/venv`). **Ojo con la trampa 32.1**: el
parche de "aislar `APPDATA`" para esquivar la extension SNES duplicada **rompe
PyGhidra** (el venv vive bajo el APPDATA real). Para usar PyGhidra hay que
arreglar la extension duplicada, no aislar el APPDATA. Hace falta tambien
`JAVA_HOME` (Adoptium 25) ademas de `GHIDRA_INSTALL_DIR`; con eso,
`tools/ghidra_desasm.py` desensambla un rango de ROM y es la forma barata de
leer un bucle concreto.

## 36. El toolchain es CIEGO a la mitad baja de los bancos `$C0-$FF` (2026-09-30)

### 36.1 El sintoma: el codigo mas caliente del juego no se puede decodificar

El bloqueo de la caminata no es un cuelgue -- el juego sigue funcionando, lo que
diverge es el estado -- y **no es cobertura**: con el artefacto del 53,7 % de
trabajo en C se bloquea igual. Lo que si aparecio al mirar el codigo caliente:

* `$C62D95` (102.830 pasos interpretados en 6000 frames) esta **SIN NODO**, y los
destinos de llamada que el escaneo vio cerca (`$C62D45`, `$C62DAE`, `$C62DCD`)
salen del analizador con **0 instrucciones** (`empty_decode`);
* `tools/ghidra_desasm.py` sobre `ROM[0x62D45..]` da codigo 65816 perfecto:
`PHP PHB SEP #$20 LDA #$7E PHA PLB` ... o sea **el despachador de objetos por
frame**: recorre 0x40 ranuras de 0x40 bytes desde `$7E:2000` y por cada ranura
cuyo flag tiene el bit 15 llama a `JSR $2DAE`. Es el codigo que mueve al
personaje;
* el IRQ/NMI (`$C0:0221`, verificado a mano: `SEI/PHB/PHD/REP #$30` con `RTI` en
  `$025E`) tambien sale `empty_decode`.

### 36.2 La causa

`rom.rs::is_rom_address` aplicaba la regla LoROM "solo `$8000-$FFFF` es ROM" a
TODO banco, pero en Star Ocean los bancos `$C0-$FF` son la **ventana MMC del
S-DD1** (`sdd1_mmc_linear` en el runner): los **64 KB completos** son ROM, de una
pagina de 1 MB elegida por `$4804-$4807`. El *calculo* de offset ya era correcto
(`((bank & 0x3F) << 16) | addr`, que para `$C6:2D45` da 0x62D45); lo que estaba
mal era la **validez**.

Firma que confirma el diagnostico sin mirar el codigo: **todos** los bloques del
mapa de Ghidra del agente anterior estan en la mitad alta (`84B8`, `8594`,
`862A`, `8812`, `8812`, `0221`...) salvo `0221`, y todo lo que decodifica bien en
el manifiesto tambien (`C0:84B8`, `C3:8F50`). La mitad baja era invisible.

### 36.3 Estado del arreglo

* **Rust (`rom.rs`): arreglado.** `is_rom_address` devuelve `true` para
  `$C0-$FF` y `lorom_offset` resuelve la ventana a la pagina 0 (antes ademas
  **paniqueaba**: `addr $0000 not in LoROM range`). `cargo build` limpio.
* **Falta el emisor Python**: mantiene su propria ventana LoROM
  (`codegen.py:195` `offset = canon_bank * 0x8000 + (pc - 0x8000)`,
  `wrapper_autoroute.py:95` `bank_start = lorom_offset(bank, 0x8000)`), asi que el
  test del despachador sigue emitiendo 446 bytes vacios. Ese es el siguiente
  cambio, y sin el no se puede medir la ganancia real.
  **RESUELTO en §37.1** (el bloqueo real era la puerta `pc >= $8000` del propio
  `decoder.py`, no `rom_offset`); §37.2/§37.3 tienen la cobertura y la puerta A/B.

### 36.4 Lo que NO explica, y el instrumento que falta

El arreglo es una palanca de **cobertura**, no la causa de la divergencia: el AOT
es byte-exacto contra el interprete puro, asi que meter ese codigo en C no
cambiaria la caminata. Para localizar la divergencia (el personaje anda distinto)
se necesita comparar el **estado del invitado** frame a frame, y ahi el trace de
Mesen **no llega**: trae PC, registros y banco de datos por frame, pero **no
WRAM**. El estado que manda aqui es la **tabla de objetos** (`$7E:2000`, 0x40
ranuras de 0x40 bytes segun 36.1).
Instrumento pedido (regla 3 de AGENTS.md): un trace de Mesen que registre, por
frame del tramo de la caminata, la palabra de flags y la posicion de la ranura
del jugador (`$7E:20xx`) -- con eso se localiza el frame exacto en que nuestra
caminata se separa de la grabada y se desensambla *ese* codigo.

## 37. La ventana MMC arreglada en el emisor: lo que destapa, la cobertura honesta y la carga del S-DD1 medida (2026-09-30)

### 37.1 El emisor Python ya no es ciego (y por que el arreglo era mas grande de lo que parecia)

Al hacer el cambio del §36.3 sobre el emisor Python aparece el bloqueo real, que
no estaba en `rom_offset` sino **en el decodificador**: `v2/decoder.py` tenia
`if not (0x8000 <= pc <= 0xFFFF): continue` en el bucle de trabajo, asi que
cualquier PC por debajo de `$8000` se saltaba *aunque el offset fuera correcto*.
Era el mismo error que `is_rom_address` en Rust, dos capas mas abajo, y el
unico que impedia materializar el despachador. Cambios:

* `snes65816.py::rom_offset` / `::is_rom_address`: bancos `$C0-$FF` resuelven a
  `((bank & 0x3F) << 16) | addr` (ROM lineal, pagina 0) y son ROM en todo su
  rango;
* `v2/decoder.py`: nuevo `_pc_is_rom(bank, pc)` (acepta `< $8000` en `$C0-$FF`)
  en los tres puntos que filtraban por PC;
* `v2/codegen.py::_is_invalid_lorom_call_target`: para `$C0-$FF` solo aplica el
  limite de tamano de ROM, no la regla `pc >= $8000`;
* `v2/pha_rts_autoroute.py::_rom_offset_lorom`: misma ventana.

**Verificacion byte a byte** (no por cobertura):
`$C0:84B8` -> fichero `0x0084B8` = `08 E2 20 A9 04 8F 06 48` (`PHP; SEP #$20;
LDA #$04; STA $4806` = escritura del registro de pagina del MMC -> **codigo
real**); `$C6:2D45` -> `0x062D45` = `08 8B E2 20 A9 7E 48 AB` (`PHP PHB SEP
LDA #$7E PHA PLB`, el despachador de objetos). Y el intérprete **ya mapeaba
igual**: `sdd1_reset` pone `r4804..r4807 = 0,1,2,3`, asi que la ventana es la
identidad `((bank-0xC0)<<16)|addr`. Antes decodificador e intérprete resolvian
`$C0:84B8` a offsets **distintos** (lo que ya avisaba §36). Ahora coinciden.
375/375 tests del toolchain en verde.

### 37.2 La cobertura del 53,7 % estaba INFLADA por el decodificado erroneo

Con el arreglo, el mismo artefacto se mide con `tools/trabajo_aot.py --hist`:

| backend | nodos AOT | cobertura de pasos |
|---|---|---|
| nativo | 442 | **19,6 %** |
| python | 815 | **42,4 %** |
| union (sin arreglo) | — | 53,7 % |

La contradiccion es aparente: la metrica cuenta un PC como "cubierto" cuando cae
**dentro del rango `[min_pc24, max_pc24]` de un nodo AOT**, y el decodificado con
bytes erroneos producia nodos con rangos anchisimos que atravesaban los PCs
calientes sin ejecutar el codigo correcto (banco `$C3`: 90,1 % "cubierto" con
cuerpos malos; el banco `$C6` daba 0 %). Con los bytes correctos, `$C6`/`$C8`/
`$C5`/`$C1` suben a **100 %** y `$C3` cae a 4 %: el 53,7 % era un artefacto de
la metrica, no trabajo real. Leccion: **la cobertura por rango no es evidencia de
que el AOT se ejecute**; la unica evidencia es la puerta A/B.

### 37.3 El artefacto arreglado NO es byte-exacto (y por que)

`tools/ab_run.py` (nuevo: lanza las dos corridas del MISMO exe, `LLE_BOUNCE=1` y
`=0`, con el reloj del guion) sobre `build-ab` (artefacto con el arreglo, backend
python, 6000 frames):

* **divergencia en el frame 5**: `resume=C8F425` (AOT) vs `C8F428` (LLE),
  `cpu +3` / `master -18`. No es ruido de muestreo: los artefactos validados
  daban `resume` identico 6000/6000.
* **cuelgue del lado AOT en el frame 3665**: pila `bank_C0_0F72_M1X0` <-
  `bank_C0_03B4_M1X0` <- `bank_C0_032D_M1X0`, SEH `0xC0000008`, direccion
  salvaje. Son rutinas de la **mitad baja de `$C0`** (`$032D` = tick del
  driver con el handshake `$2140`; `$0F72` = bucle de copia `LDA $40; BMI`;
  `$03B4` = despacho por `$64`). El artefacto del arbol **no las tiene** (0
  apariciones en `generated/bankc0_v2.c`), porque el bug las hacia invisibles.

Conclusion de ingenieria: el arreglo es **necesario** (el emisor leia bytes
equivocados en todo `$C0-$FF`) pero **destapa codigo que nunca se habia emitido
como AOT** y que aun no esta validado. **No adoptar** todavia ni el artefacto del
arbol ni el arreglado; la puerta A/B manda.

### 37.4 La carga del S-DD1, medida por bytes (no por duracion)

El runner ya trae el instrumento: `SNESRECOMP_SDD1STATS=1` (una linea por frame
con actividad, bytes servidos por DMA y por lectura directa). Corrida de 1500
frames con el guion de hardware:

```
f3      dma=2084   ...   f163  dma=6144   f316  dma=768   f317 dma=896
f708    dma=47456  ...   f1149 dma=512    f1154 dma=3802  f1168 dma=15600
f1172   dma=2048   ...   f1173+ dma=256 (streaming por frame)
```

La **primera carga (2084 bytes) se sirve ENTERA dentro del frame 3**; la segunda
(47.456 bytes) tambien en **un** frame. Eso **no sostiene** la hipotesis del
"28x" de §18.4 (que salia de 733/26 y asumia una tasa constante por byte): un
estrangulamiento por byte que diera 733 frames para 2084 bytes implicaria ~0,35
frames/byte, y entonces los 47.456 bytes tardarian ~16.600 frames, no uno. La
entrega es **a rachas**, y por tanto la duracion de la carga **no** se explica
solo por la tasa del chip. Queda como pregunta abierta que mide exactamente el
hueco de hardware (¿espera del invitado a vblank?, ¿una pantalla de carga?) --
y no como una causa confirmada de la divergencia de la caminata.

## §38. La tabla de objetos: instrumento fiable y donde vive el jugador

### 38.1 El volcado tiene que leer WRAM en crudo, no `cpu_read8`

El primer instrumento (`SNESRECOMP_FRAME_OBJTABLE`) volcaba las ranuras con
`cpu_read8(&g_cpu, 0x7E, addr)`. Eso **altera la corrida que intenta observar**:
`cpu_read8` fija `open_bus` y llama a `cart_note_cpu_bus`, y con 64 ranuras por
frame (4 KB) el juego cae por otro camino. Medido: con **64 ranuras** la tabla
salia **entera a cero** durante toda la caminata; con **1 ranura** estaba viva y
moviendose. La conclusion es la trampa clasica del observador que perturba.

Arreglo: leer `g_cpu.ram[(base + b) & 0x1FFFFu]` directamente (WRAM = `$7E`/`$7F`
lineal), sin latchear `open_bus` ni notificar el bus. Con eso el volcado es
**libre de efectos secundarios** y las 64 ranuras se pueden mirar a la vez.

### 38.2 El jugador es la ranura 0 de la tabla de `$7E:2000`

Con el dump limpio, en el tramo de la caminata guiada y con 64 ranuras:

* **12 ranuras activas**: `00 01 02 20 21 22 30 31 32 3D 3E 3F` (el resto a cero);
* la **ranura 0** es el jugador: sus bytes de posicion cambian cada frame
  mientras hay entrada direccional, y se quedan fijos (salvo el byte 0 de
  animacion, que cicla `88 -> 8E -> CE`) cuando el pad esta neutro;
* el byte 0 de la ranura es el **indice de fotograma** del sprite (`88`/`8C`/
  `8E`/`CE`), no una bandera.

Es decir: el despachador `$C62D95` (32.1) recorre 0x40 ranuras de 0x40 bytes
desde `$7E:2000` **incluida la del jugador**, y la tabla **no** esta vacia en la
caminata — el "todo a cero" era el instrumento, no el juego.

### 38.3 La caminata guiada esta en los frames ~14.838-15.945

Sale del propio guion de entrada (tramo de entrada direccional sostenida), no de
mirar el juego. Es la ventana en la que hay que comparar AOT contra interprete
puro cuando la puerta A/B no sea byte-exacta global: `ab_run.py` cubre 6000
frames, asi que la caminata **no** entra en esa pasada y hace falta una corrida
acotada a `f>=14000` para verla.

### 38.4 Estado del arbol (nada publicado)

Commits **locales**, sin push, en `so-mmc-window` (submodulo) y en la rama de
trabajo (padre):

| repo | commit | contenido |
|---|---|---|
| `snesrecomp` | `782dbce` | ventana MMC en el emisor Python (4 ficheros) |
| padre | `34eee91` | `generated/` (union) + `tools/ab_run.py` |
| padre | `6a0a02e` | `bankC0.cfg`, `so_rtl.c`, `ENCICLOPEDIA.md`, puntero del submodulo |

`generated/` sigue siendo el artefacto de la **union**, que **si pasa** la puerta
A/B (identico 6000/6000). El artefacto con el arreglo MMC vive en `out/gen-ab`
(ignorado) y **no** se instala: ya no cuelga (§37.3 se curo con `force_lle` sobre
la familia de puertos `$2140-$2143` de la mitad baja de `$C0`), pero queda una
**deriva de ~2 ciclos de CPU por frame** (`d_cpu` crece ~11.550 a frame 6000,
`d_master` dentro de +-10). Mientras esa deriva no sea cero, no es byte-exacto y
no se publica ni se adopta.

Tambien: `generated/` en el arbol es la union, pero `out/gen-ab` es el arreglado;
**no** confundir cual exe esta usando cual build dir.


## ESCANEO DE SPIN DEL INTÉRPRETE: EL PICO DE 90-250 ms NO ERA EL S-DD1

(2026-09-30, rama de la COPIA `E:/Experimento Hermes`. Instrumentado con
`SNESRECOMP_HOTSTAT=1`, que imprime `[hstat]` por fotograma.)

### Lo que se sospechaba y NO era

El fotograma lento se sospechaba a la zona de codificación; el S-DD1
quedó **descartado por medición**: el contador `sdd1_prof_ms` da **0,00 ms** en
f702 y f708, y `sdd1_sync()` es literalmente un `no-op` (`snes/apu.c`: no
necesita reloj, el S-DD1 avanza con la lectura del bus). El coste del
descompresor no puede aparecer ahí. Tampoco era el dibujado (1,3-2,9 ms de
90-250 ms), ni el DMA (0,00 ms), ni el hilo de audio: con `EnableAudio=0`
verificado (`audio=0` parseado y **cero** líneas de "first audio callback") el
pico sigue ahí (114/152/89 ms).

### Lo que sí era

`bridgeq` (el puente de interpretación entero) = **100 % de `emu`** en los
picos. El invitado ejecuta, instrucción a instrucción, el handshake del
SPC700 de `$C0:8598`:

    $C0:859D  SEI
    $C0:859E  LDA $002140      ; lee el puerto de salida del SPC700
    $C0:85A2  CMP $002140      ; compara con OTRA lectura inmediata
    $C0:85A6  BNE $859D        ; espera a que el SPC700 deje de cambiarlo

13 ciclos de CPU por vuelta (2+4+4+3). f702 da **125.922 opcodes** y 55.535
lecturas de `$2140`. En hardware esa espera es de microsegundos; aquí la paga
el intérprete, y por eso el fotograma cuesta 100-250 ms de host.

### El cuello real: el detector de spin

Reparto medido de f702 (audio apagado, `[hstat]`):

    bucle del interprete, total      189,59 ms
      dentro de interp816_runOpcode   79,61 ms
      lecturas al puerto APU          28,17 ms   (504 ns por lectura)
      resto (bookkeeping del bucle)   81,81 ms   <-- 647 ns POR INSTRUCCION

647 ns de "resto" por opcode es imposible para un intérprete normal (~50 ns).
El culpable es el detector de quiescencia: en **cada** instrucción rellena un
`QuiescentState` y recorre un anillo de 64 ranuras comparando 17 campos. Peor:
el filtro `steps-old->step<=256` **no filtra nada**, porque la ranura se
escribe en `qring[steps & 63]`, o sea que ninguna entrada tiene más de 63
pasos de antigüedad. Siempre comparaba las 64.

### El arreglo: pre-filtro exacto por generación de épocas

La igualdad completa exige que `write_epoch` **y** `continuous_read_epoch`
coincidan, y ambos son monótonos. Luego una ranura escrita antes del último
cambio de esas épocas **no puede coincidir**. Se guarda el step del último
cambio (`q_floor`) y solo se recorre el arco de ranuras reciente, en **orden
ascendente de índice** para que el primer ganador sea el mismo que antes.
Encima, una clave de 64 bits sobre campos que la igualdad ya exige acts como
pre-filtro conservador.

Medido (mismo binario, `SNESRECOMP_QSCAN_FILTER` alternado, audio apagado,
3 corridas alternadas para que la deriva del host no juegue a favor):

    fotograma   original            parche
    f702        188-202 ms bucle    124-130 ms      resto 81-88 -> 30-31 ms
    f705        114-115 ms bucle     75 ms          resto 56-57 -> 19-21 ms
    f708        100-101 ms bucle     70-71 ms       resto 47 -> 17-20 ms

    media de emu 5,02 ms -> 3,97 ms  (-21 %)
    peor frame visible: f705 108 ms -> 66 ms, f708 89 ms -> 63 ms

**Exactitud: 1200 fotogramas de `[fstate]` bit a bit idénticos con el filtro
puesto y quitado, en 3 corridas.** El filtro no puede cambiar la decisión del
detector: si la clave difiere, la comparación completa también fallaría.

### Dos trampas de medicion que costaron tiempo (anotadas para no repetirlas)

1. **Este host tiene deriva grande entre corridas**: el mismo fotograma con
   estado de invitado identico midio 152 ms en una corrida y 250 ms en otra.
   Una sola medicion por configuracion NO vale. Hay que alternar A/B/A/B y
   comparar.
2. **El ternario de las variables de entorno se puede invertir en silencio.**
   `(_e && _e[0] && _e[0] != '0') ? 1 : 0` significa "activado"; puesto al
   reves (`? 0 : 1`) el flag `=0` activa la funcion y `=1` la desactiva, y
   los resultados salen **invertidos** sin ningun sintoma. Pasó dos veces
   (`SNESRECOMP_NO_QSCAN` y `SNESRECOMP_QSCAN_FILTER`) y en ambas la primera
   conclusion fue la contraria de la buena.
3. **El tamano de ventana NO era la causa.** Escala 1, 2 y 3 dan el mismo
   atasco; una primera corrida con escala 3 que no se atascó era ruido y
   produjo una correlacion falsa.

### 22.16 El audio con la deadline: lo que se ha descartado de mas, y donde esta el atasco (2026-09-30)

Sesion dedicada al audio con `SNESRECOMP_FRAME_DEADLINE=1` (§22.13), que es el
UNICO bloqueo que queda para activar la deadline por defecto. La deadline es lo
unico que arregla los tres bajones de fotograma del usuario (arranque, tercer
logo, transicion al fondo estrellado), asi que cerrarla aqui desbloquea eso.

**Lo que la deadline SI cambia, medido fotograma a fotograma** (`tools/fdiff.py`,
`[fstate]` A vs B, 900 fotogramas): el reloj del invitado es IDENTICO salvo en
**6 fotogramas de 900** — `f4` (el invitado se come 23.570.058 ciclos master de
golpe en vez de 357.368: ese es el congelamiento de arranque), `f324`, `f701`,
`f702`, `f705` y `f708` (1,1-2,4 M de golpe cada uno: el tercer logo y la
transicion al fondo estrellado). Los tres sintomas del usuario estan ahi
dentro. En los otros 894 fotogramas `master`, `irq`, `nmi`, `E1`, `D8`, `F7` y
`resume` dan lo mismo. Los motivos de cesion del LLE tambien son los mismos en
regimen permanente: `yIrq=1 yDL=0 yQuiesc=0 yWai=0` por fotograma en los dos
modelos (`g_yield_*` en `interp_bridge.c`).

**Descartes de hoy, todos con contador, ninguno con suposiciones:**

| hipotesis | como se midio | resultado |
|---|---|---|
| Tope de 10.000 ciclos/call en `snes_catchupApu` estrangula al SPC | `g_apu_cycles_offered` vs `g_apu_cycles_run` | **FALSO**: 17.039 ofrecidos = 17.039 ejecutados, 0 perdidos, en los dos |
| El invitado no entrega sus escrituras a `$2140` | `g_apu_port_writes` por frame | **FALSO**: 38.774 escrituras en los DOS modelos, cola siempre a 0, 0 descartadas |
| La cesion por deadline rompe la sincronia APU↔CPU | `SNESRECOMP_APU_REAL_CLOCK=1` (reloj real en vez de `snes_frame_counter*357368`) | **FALSO**: identico. Y ya estaba en `DESCARTADAS.md` del 2026-09-29: no volver a proponerlo |
| El fast-forward de quiescents se come el audio | `SNESRECOMP_NO_QUIESCENT_FF=1` | **FALSO**: silencio igual |

**El sintoma, aislado por el lado correcto.** La pregunta "el motor entrega
silencio" era la equivocada: el DSP ** produce muestras pero son todas
ceros**. `dsp_ring_energy()` (nuevo, `SNESRECOMP_DSPSTAT=1`):

| | `DEADLINE=0` | `DEADLINE=1` |
|---|---|---|
| primer frame con energia en el anillo | f328 | **ninguno, 0 de 624** |
| energia en ese instante | 1.906.694 | 0 |

Y el volcado del estado del DSP **en el MISMO instante de reloj de invitado**
(`portClock=6876014`, `SNESRECOMP_DSP_DUMP_AT`) dice por que:

```
DEADLINE=0  echoVol=32/32 fir=7F/0000...  c0=08/FF c1=07/FF c2=06/FF c3=03/FF
DEADLINE=1  echoVol=-32/32 fir=7F/0000...  c0=00/00  c1=00/00  c2=00/00  c3=00/00
```

Los volumenes de canal del DSP **nunca se programan** con la deadline. O sea:
el motor de sonido nunca arranca, no es que arranque y suene bajo.

**El dato mas nuevo y el que mejor acota el atasco:** el punto de reanudacion al
final de cada fotograma de host (`resume` del `[fstate]`):

```
DEADLINE=0   C8F428 x277  C8F425 x207  C8F40F x14  C8F412 x17  C085A6 x0
DEADLINE=1   C8F428 x236  C8F425 x178  C8F40F x15  C8F412 x16  C085A6 x23
```

Con la deadline el invitado se queda **23 fotogramas de host parado dentro de
`$C085A6`**, que es el spin del handshake con el motor de sonido
(`$C0859D SEI / LDA $002140 / CMP $002140 / BNE $C0859D`, el `HOT_LO` que ya
vigilaba `tools/mesen_so_trace.lua`). **Sin deadline, 0 veces.** El invited no
cede nunca a mitad de ese spin porque en el arranque se come 66 fotogramas de
invitado de golpe y el handshake se resuelve dentro de ese ataco; con la
deadline el handshake se estira y el invitado queda esperando.

Esto NO explica todavia por que el motor no arranca, pero acota el problema a un
solo sitio: **la interaccion entre la cesion por deadline y el spin del
handshake de sonido `$C0859D`**. No es el APU, no es el DSP, no es el SPC, no es
el invitado.

**Lo que hace falta para cerrarlo (no se puede decidir sin esto).** El trace de
`tools/mesen_so_trace.lua` (el grabador YA existe y el ROM esta en
`F:\Recompilador Super Nintendo\Mesen\Star Ocean (Japan).sfc`), con dos preguntas
separadas que la medicion actual no puede distinguir:

1. En hardware, ¿el handshake `$C0859D` bloquea al invitado **23 fotogramas**
   seguidos, o se resuelve siempre de golpe? Si en hardware es un bloque corto,
   la cesion por deadline estaPartiendo el spin por un sitio que el hardware no
   parte, y el arreglo es de la cesion, no del audio.
2. En hardware, ¿en que **fotograma de invitado** empieza a sonar la musica de
   la intro? Con `DEADLINE=0` el primer tick de `$C0032D` cae en el frame de
   host 4 y con `DEADLINE=1` en el 69: en reloj de invitado **es el mismo**
   (~70), porque sin deadline el invitado va 66 fotogramas por delante. Toda la
   comparacion de audio que se ha hecho hasta ahora es en **tiempo de host**, y
   por eso no puede separar "la musica llega tarde" de "la musica no llega".

**Instrumentos nuevos (todos.env-gated, coste cero si no se activan):
`SNESRECOMP_DSPSTAT=1` (energia del anillo y estado del DSP por fotograma),
`SNESRECOMP_DSP_DUMP_AT=<portClock>` (volcado del DSP en un instante de reloj
de invitado), `g_yield_*` (motivo de cesion del LLE), `spcOfrecido/Ejecutado/
Perdido` y `pWrite/pCola/pColaMax/pDesc` en `[hstat]`.
Herramientas: `tools/deadline_irq_ab.py`, `tools/fdiff.py`, `tools/pcm_health.py`.**


### 22.17 EL TRACE DE MESEN ESTABA EN DISCO: con la deadline el modelo es EXACTO, y el fallo esta en el IPL del SPC700 (2026-09-30)

Los ficheros estaban en `E:\Recompilador Super Nintendo\StarOceanRecompDocumentacion\TracesMesen`
(`*_events.tsv` 56 MB, `*_trace.tsv`, `*_replay.txt`). 29.560 fotogramas de
hardware. El input coincide con el que usa el motor (`mesen_master.txt` esta
derivado de ESTA traza, y no hay pulsaciones antes del fotograma 1171), asi que
la comparacion de la intro es valida.

**1. La deadline NO rompe el audio: lo hace CORREGIR.** Escrituras del
invitado a `$2140-$2143`, por bloques de 50 fotogramas:

| | f1-50 | f51-100 | f101-400 |
|---|---|---|---|
| hardware (Mesen) | 22.002 | 9.318 | 0 |
| **motor con deadline** | **22.002** | **9.312** | 0 |
| motor sin deadline | 31.314 | 0 | 0 (+7.460 en f301) |

Con la deadline la subida del motor de sonido coincide con hardware practicamente
byte a byte (31.314 contra 31.320: **6 escrituras de diferencia en 31.320**). Sin
deadline el invitado se come las dos tandas de golpe en el f2 y se adelanta 7.460
escrituras que en hardware no existen todavia. **Esto valida el modelo de tiempo
de la deadline y refuta de raiz la explicacion de §22.13** ("la deadline no
entrega el NMI/IRQ del frame"), que era una conjetura sin dato.

**2. Lo que el hardware hace y el motor no.** Escrituras del SPC al DSP
(`$F2`/`$F3`), por bloques de 50 fotogramas:

| | f1-50 | f50-99 | f100-149 | f150-199 | f200-249 | f250-299 | f300-349 |
|---|---|---|---|---|---|---|---|
| hardware | 11 | 78 | 123 | 123 | 120 | 123 | 123 |
| motor | 138 | 8 | **0** | **0** | **0** | **0** | ~0 |

En hardware el SPC700, una vez subido el motor, **tira solo**: 2,46 escrituras al
DSP por fotograma, para siempre. En el motor **se para en seco en el f50** y no
vuelve a escribir. Por eso el DSP nunca se programa (volumenes de canal a cero,
`§22.16`) y suena a silencio.

**3. El IPL del SPC700 es el culpable, y aqui esta el dato duro.** Columna
`spcpc` del trace (PC del SPC700):

```
hardware:  f1..f26  spcPC=$00EF      f27..  spcPC=$00FB   <- ya esta en el motor subido
motor:     f1..f19  spcPC=$FFC6/$FFCF/$FFE2/$FFDA  (ROM del IPL)   f25.. spcPC=$391B
```

En hardware el SPC700 pasa del IPL al programa subido **dentro del primer
fotograma**. En el motor **se queda 19 fotogramas en el IPL** y luego salta a
`$391B`, mientras hardware ejecuta `$00EF`. Son las dos mitades del mismo bug: el
IPL no ve la peticion de arranque a tiempo y ademas aterriza en la direccion
equivocada.

**4. Y el spin que el hardware NUNCA ejecuta.** Columna `hc` (instrucciones en
el bucle caliente `$C0859D-$C085D0`), **0 en los 400 fotogramas del hardware**,
maximo 0. En el motor con deadline, el invitado acaba **23 fotogramas de host
dentro de ese spin** (`resume=$C085A6`). Ese spin es la espera del handshake
con el IPL: si el IPL tarda 19 fotogramas, el invitado se queda esperando en
una direccion en la que el hardware no llega a estar. Las dos sintomas
(`$C085A6` y el audio mudo) son la misma causa.

**5. Descartado de paso: el temporizador del SPC700 NO va mal.** El codigo
divide cada 128 ciclos (timer 0/1) y cada 16 (timer 2), o sea 8 kHz y 64 kHz, que
es exactamente lo que dice la especificacion (superfamicom.org SPC700 Reference,
emudev). Hipotesis formulada, comprobada contra la referencia y **descartada**
antes de tocar nada. El timer 0 marca ~0,8 tik por fotograma, y su PC recorre
$391B, $1A61, $0BD6, $19F2, $0958, $09C9, $0A30... con normalidad: **el SPC700
no esta colgado, esta trabajando en el sitio equivocado.**

**Donde queda el arreglo.** En `RtlUploadSpcImageFromDpInternal()`
(`common_rtl.c:1296`, rama `ipl_phase`): ahi se hace
`g_snes->apu->spc->pc = final_pc` con `sp = 0xef`. Dos cosas a verificar con
dato: (a) por que el IPL no consume la peticion de arranque hasta el f19, y (b)
de donde sale `final_pc = $391B` cuando hardware entra por `$00EF`. Todo lo demas
- la deadline, el reloj del APU, el SPC, el DSP, la cola de puertos - queda
descartado con contadores.

### 22.18 Sonda compacta de referencia (`tools/mesen_so_probe.lua`) (2026-09-30)

La grabadora anterior (`mesen_so_trace.lua`) transcribe TODO: una linea por
acceso. Para la intro son 1,45 M de lineas y **56 MB**, de los que el 95% es el
mismo dato repetido (702.846 escrituras a `$2140`, una a una). Es ilegible y
ademas **no reachaba**: de §22.17 salio que lo que hacia falta no estaba
grabado (el PC del SPC700 fotograma a fotograma, los contadores de timer, el
estado del DSP, y una huella de WRAM para saber el primer fotograma de
divergencia).

**El principio: resumir, no transcribir.** Un flujo de alta densidad se resume
por fotograma con dos numeros: **cuantas** y un **digest** del contenido. El
digest no deja ver que bytes fueron, pero si deja **probar** que dos corridas
son identicas byte a byte, que es la pregunta que se hace el 90% de las veces al
comparar hardware contra motor. Ocupa 30 bytes en vez de 3.000. Lo que si cambia
de verdad (un fundido, un key-on, un reset) se escribe como evento, pero
**solo cuando cambia** respecto al valor anterior. Y se anade lo que faltaba.

**Cinco ficheros, ~120 bytes por fotograma:**

| fichero | una fila por | que lleva |
|---|---|---|
| `<rom>_frames.tsv` | fotograma | reloj de invitado, PC, a/x/y/sp/d/db/p, PPU, pad, NMI/IRQ, fundidos, y el **recuento en 7 zonas de codigo vigiladas** |
| `<rom>_audio.tsv` | fotograma | puertos del CPU al APU, puertos del SPC, escrituras al DSP con su registro, **key-on**, digests de ambos flujos, **PC y registros del SPC700**, **los tres timers**, ocupacion del anillo, huella de la RAM del SPC |
| `<rom>_fp.tsv` | 20 fotogramas | huella de WRAM y de la RAM del SPC: **el primer fotograma exacto de divergencia** |
| `<rom>_events.tsv` | transicion | solo cuando el valor cambia; detalle byte a byte dentro de la ventana `VERBOSE_DESDE..VERBOSE_HASTA` |
| `<rom>_replay.txt` | cambio de pad | pulsaciones en **reloj de invitado**, listo para `SNESRECOMP_REPLAY_FILE` |

Tamano: **47 KB para 400 fotogramas, 3,5 MB para 29.560** (la traza vieja: 60 MB).
Para la intro, 2000 fotogramas son 234 KB.

**Las zonas vigiladas** (`RANGOS`, configurables) son la respuesta directa a
"donde se fue el tiempo" yinclude el hallazgo de §22.17: `$C0859D-$C085D0`
(spin del IPL, el que hardware nunca ejecuta), `$C084AE-$C084B4` (espera del
latch `$D9`), `$C00221-$C00260` (handler de V-IRQ), `$C0032D` (tick por
fotograma del driver de sonido), `$C08751`, `$C08F94` y `$00F400-$00F43F`
(estado del motor de sonido en WRAM).

**Defensas incorporadas, aprendidas de los fallos anteriores:**

1. **CANARIO**: un callback de escritura sobre la pagina de pila (`$00:0100-$01FF`),
   que recibe miles de escrituras por fotograma. Si da 0, los callbacks de
   escritura no disparan en esa build y **todo lo que dependa de ellos es
   mentira**: el log lo avisa. Ese fallo hizo que la sonda anterior perdiera el
   98% de las escrituras a `$2100` sin que nada lo dijera.
2. **`readMemory` con los argumentos en el orden correcto**: el orden no esta
   verificado en esta maquina, asi que se prueban las dos formas y se recuerda
   la que funciona. Adivinarlo daria huellas del bus equivocado.
3. **Los hooks del SPC llevan SIEMPRE `cpuType` explicito**: sin el, caen en el
   bus de la CPU, donde `$00F2/$00F3` son WRAM y no el DSP, y salen key-on falsos.
4. **Un valor ausente se imprime como `-`, no como hex**: `-1 % 16 = 15` en Lua,
   asi que imprimir un campo inexistente en hexadecimal daria `FFFFFFFF`, que es
   indistinguible de un valor real. Es exactamente el tipo de dato creible y
   falso que hay que evitar.
5. **Digest con multiplicador 65599, no el 16777619 del FNV-1a canonico**: el
   producto cabe en las 53 bits de un double de Lua y no se pierde precision.
6. **Las huellas de WRAM van espaciadas** (`HUELLAS_CADA`, 20 por defecto): son
   8.192 lecturas por toma, y subirlas a 1 mete el coste de Lua dentro de la
   emulacion y falsea las medidas de tiempo.

**Validador: `tools/check_lua.py`.** No hay Lua en esta maquina, asi que un error
de sintaxis solo apareceria cuando el usuario ejecuta el script en Mesen, con la
sesion a medias. Este script comprueba el equilibrio de bloques y de
 parenteses distinguiendo codigo de cadenas y comentarios. **Calibrado contra
los dos scripts antiguos que si funcionan: cero falsos positivos.** (El
calibrado fue necesario: la primera version se comia los saltos de linea, asi
que todos los numeros de linea valian 1 y el diagnostico era inservible, y
acusaba de 30 errores a un fichero correcto.)

**Lo que este script NO hace, y no disimula:** no comprueba el ARRANQUE del motor
de sonido mas alla de las columnas de audio; para eso habria que enganchar el
contador de instrucciones del SPC por region, que es lo siguiente que haria falta.

### 22.19 CORRECCION a §22.17.3: el IPL del SPC700 NO es el culpable (2026-09-30, noche)

**El punto 3 de §22.17 estaba mal y se retira.** Alli se afirmo que en hardware
el SPC700 estaba en `$00EF` desde el f1 y que el motor se quedaba 19 fotogramas
en el IPL. **Era un error de columna**: en `*_trace.tsv` la columna 30 es
`spcsp` (la PILA del SPC700), no el PC. El PC real es la **columna 26**.

Leida la columna correcta:

```
hardware: f1..f26  spcPC=00FFC5..00FFFD  sp=EF      f27.. spcPC=00391B  sp=FB
motor:    f1..f24  spcPC=00FFC6..00FFF3  sp=EF      f25.. spcPC=00391B  sp=FB
```

**El motor coincide con hardware casi fotograma a fotograma**: los dos estan en
el IPL (`$FFxx`) durante el arranque, los dos saltan a `$391B` en el f25-27, y
los dos cambian la pila de `$EF` a `$FB`. El array `bootRom[0x40]` de `apu.c`
es ademas **byte a byte identico al IPL de bsnes**, asi que tampoco ahi hay nada.
**El IPL queda exonerado.** La lesson: antes de comparar una columna de un TSV
hay que imprimir sus PRIMERAS filas una a una y numerarlas. Cuesto 20 minutos y
estaba a punto de "arreglar" una linea de codigo que era correcta.

**Lo que sigue en pie de §22.17 (todo medido, nada retirado):**

1. La **deadline hace que la subida del motor de sonido coincida con hardware**
   (22.002 contra 22.002, y 9.312 contra 9.318). El modelo de tiempo es correcto.
2. El **invitado acaba 23 fotogramas de host dentro del spin `$C0859D`**, y en
   hardware ese bucle se ejecuta **0 veces en los 400 primeros fotogramas**
   (columna `hc`). Esto es lo mas fuerte que hay ahora mismo.
3. El **SPC700 deja de escribir al DSP en el f49** (138 escrituras en f1-49,
   8 en f50-99, 0 a partir de ahi) mientras hardware **sigue a 2,46 por
   fotograma para siempre**. El codigo es el mismo y los puertos reciben lo
   mismo, asi que el motor se queda parado por algo que no llega.
4. El `RtlUploadSpcImageFromDpInternal()` **no se llama nunca** en este juego
   (instrumentado y sin una sola salida): el `final_pc` y la rama `ipl_phase`
   que §22.17 señalaba son CODIGO MUERTO aqui. La subida la hace el IPL real
   emulado, byte a byte por los puertos, y se ve funcionando en el log.

**Siguiente paso concreto:** el invitado espera en `$C0859D` algo que en hardware
ya esta. Lo que hay que mirar es el estado del SPC en el instante en que el
invitado entra en ese spin y que no ocurre en hardware: RAM del SPC, puertos de
entrada y el estado del BRAM del DSP. Con eso deberia caer.

### 22.20 La capa de configuracion del DSP es IDENTICA a hardware (2026-09-30, noche)

Instrumentado el SPC700 por dentro (puertos de salida, escrituras a $F2/$F3) y
comparado con el trace de hardware. Se cae otra hipotesis y se acota mucho mas.

**1. EL SPC700 NO SE PARA (retira §22.17.3).** Escrituras del SPC por
fotograma, nuestro motor (con deadline) contra hardware:

| bloque | puertos del SPC (motor / hw) | escrituras al DSP (motor / hw) |
|---|---|---|
| f1-50 | **220 / 220** | 0 / 0,2 |
| f51-100 | **62 / 62** | 2 / 1,6 |
| f101-350 | **3 / 3,2** | 2 / 2,46 |

Empiezan igual y siguen igual. El motor de sonido **funciona al ritmo
correcto**, siempre. La afirmacion de §22.17 de que "deja de escribir al DSP en
el f49" era **FALSA**: venia de un contador (`SNESRECOMP_DSPREG_TRACE_FILE`) que
solo registra el cambio de valor, asi que "0 escrituras" queria decir "0
cambios de valor", que no es lo mismo. **Regla: un contador que filtra no cuenta
accesos, cuenta cambios, y las dos cosas se confunden con facilidad.**

**2. EL REGISTRO DEL DSP ES IDENTICO, REGISTRO A REGISTRO.** Con
`tools/dsp_regs_hardware.py` se reconstruye el registro del DSP de hardware a
partir de las lineas `sdsp_data` del trace y se compara con el del motor:

```
frame 120 y frame 380:
  registros que hardware escribe y el motor no ...... 0
  mismos registros con VALOR distinto ............... 0
  hardware escribe 21 registros; el motor, ademas, 107 (que no le hacen falta)
```

Los 21 registros que hardware programa ($0C,$0D,$0F,$1C,$1F,$2C,$2D,$2F,$3C,
$3D,$3F,$4D,$4F,$5C,$5D,$5F,$6C,$6D,$6F,$7D,$7F) estan en el motor **con el
mismo valor exacto**, tanto a los 120 como a los 380 fotogramas. La
configuracion del DSP (ADSR, pagina DIR, buffer de eco, retardo de eco) esta
**bien**.

**3. Luego el silencio NO es del registro: es de los DATOS.** Si el registro
coincide y aun asi la salida es cero, lo unico que queda es que el secuenciador
no encuentra muestras: el BRAM que lee el DSP (la RAM del SPC), la pagina DIR
con su extension de direccion ($2F/$3F), o el propio mezclador/`mute`. Los
datos de la subida llegan bien (22.002 escrituras, §22.17), asi que el
sospechoso es COMO se leen, no si llegaron.

Herramienta nueva: **`tools/dsp_regs_hardware.py`** reconstruye el registro del
DSP de hardware desde el trace y lo compara con el del motor, registro a
registro y valor a valor, en el fotograma que se le pida. Convierte 56 MB de
eventos en una tabla de 21 numeros que se puede mirar de un vistazo.

**Estado honesto:** el IPL y el registro del DSP quedan descartados con datos.
El problema es el camino de los DATOS de audio dentro del emulador, que es una
capa distinta y no se ha tocado.
