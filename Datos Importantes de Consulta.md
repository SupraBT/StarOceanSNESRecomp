# Datos Importantes de Consulta — Star Ocean Recomp

> Documento de referencia rápida del proyecto. Condensa lo esencial de
> `SO_jap_ROM_layout.txt` (mapa de la ROM) y de las webs recopiladas en
> `..Webs de interés.txt`. Lo detallado vive en los originales; esto es para
> consultar sin releer 3.000 líneas.
>
> Creado: 2026-09-03. Estado: datos verificados contra la ROM salvo donde se indica.

---

## 1. La ROM de un vistazo

| Dato | Valor |
|---|---|
| Juego | Star Ocean (Japón) |
| Fichero | `Star Ocean (Japan).sfc` |
| Tamaño | 6.291.456 bytes = 48 Mbit (6 MB) |
| Cabecera | LoROM, en `$7FC0` (título: `Star Ocean`) |
| Mapper byte | `0x32` (LoROM + ExRAM según cabecera) |
| ROM size byte | `0x0D` |
| SRAM | `0x03` (512 Kbit según tabla estándar) |
| Coprocesador | **S-DD1** (descompresión de gráficos por hardware) |
| Código ejecutable | Bancos **`$C0`–`$CC`** (según `SO_jap_ROM_layout.txt`) |

> ⚠️ La etiqueta del fichero dice que el código ejecutable vive en `$C0-$CC`.
> Nuestro recompilador declara hoy bancos `00, C0, C1, C2, C3, C9` en
> `config/*.cfg`. Eso significa que **parte del rango C0-CC (C4-C8, CA-CC) es
> código que aún se ejecuta por el intérprete LLE** — candidatos naturales para
> futura cobertura AOT.

---

## 2. Mapa de la ROM — visión general

El layout contiene **dos pasadas de anotación** sobre el mismo fichero:

1. **Pasada por bancos SNES `$C0`–`$FF`** (líneas 1–~2218): clasificación
   gruesa (S-DD1 chunks / tilesets / LZ / texto).
2. **Pasada física por bancos `$40`–`$5F` → SNES `$E0`–`$FF`** (desde ~línea
   2227 al final): mucho más detallada, identifica bloques de sample SPC700
   numerados (0–589), chunks LZ, paletas y transferencias a VRAM.

> ⚠️ Entre pasadas hay etiquetas contradictorias para la misma zona alta de la
> ROM (p. ej. `$E0` = "S-DD1 data chunk" en la pasada 1, pero "SPC700 sample
> block 528 + S-DD1 chunk + samples" en la pasada 2). La pasada 2 (física) es
> la más fina y fiable para la zona de audio. Ante duda: verificar bytes.

### Resumen por rangos

| Rango SNES | Contenido principal |
|---|---|
| `$C0`–`$CC` | **Código ejecutable** (el que recompilamos) |
| `$CD`–`$E3` | Gráficos S-DD1 (sprite tilesets + data chunks), algunos chunks LZ |
| `$E4`–`$E8` | **Datos de evento y texto comprimidos LZ** (punteros en `$E40000`) |
| `$E9`–`$F8` | Más chunks S-DD1 / LZ / tilesets |
| `$F9`–`$FF` (≈ físicos `$49`–`$5F`) | **Samples SPC700** (audio), chunks LZ, paletas, fuente |
| `$FF` | Fuente japonesa 1BPP, config de escenas LZ, paletas |

---

## 3. Puntos de consulta rápida (lookup)

### Código / tablas indexadas desde código

| Dirección | Qué es |
|---|---|
| `$DC243A-$DC29D9` | Tabla de datos indexada desde `$C9:E4DC`, `$C9:E57B`, `$C9:E5F8` |
| `$DDE888-$DEEA27` | Tabla de datos indexada desde `$C9:E35B` |
| `$DE78BF-$DE79FE` | Tabla de datos indexada desde `$C9:DCD4` |
| `$DEBED5-$DEBF64` | Datos transferidos a VRAM `$45A0` desde `$C0:2402` |
| `$E40000-$E40233` | **Tabla de punteros** a datos de evento/texto de escenas |

### Texto

| Dirección | Qué es |
|---|---|
| `$D70000-$D7254A` | Nombres de armas, armaduras, objetos y enemigos |
| `$D7254B-$D74287` | Descripciones de armas, armaduras y objetos |
| `$FE63A1-$FEA2DF` | Texto de descripciones de habilidades (LZ) |
| `$E40234+` | Eventos y diálogos del juego (LZ) |
| `$DBA078-$DBA819` | **Fuente 8×8 1BPP comprimida S-DD1** (la usada en pantalla) |
| `$FF0000-$FFC7FF` | Fuente japonesa 1BPP (la de la intro/menús) |

### Paletas

| Dirección | Qué es |
|---|---|
| `$D7DE00-$D7FFFF` | Color data para paletas |
| `$FB4F3C-$FB533B`, `$FC4AF3-$FC4C72` | Palette color data |
| Varias en `$FD`/`$FE` (p. ej. `$FEF1C9+`, `$FFF000-$FFFFFF`) | Palette color data (la pasada física las numera) |

### Audio (SPC700)

| Dato | Valor |
|---|---|
| Zona principal | Bancos SNES `$F9`–`$FE` = físicos `$49`–`$5E` |
| Bloques | Muestras BRR numeradas 0–589 (la pasada física da rango exacto de cada una) |
| Código SPC700 | Chunk LZ en `$E3227D-$E344D0` (etiquetado "SPC700 code") |
| Formato | BRR 8-bit + envolventes S-DSP (ver sección 5: fullsnes/Snaggletooth) |

### Curiosidades / zonas raras

| Dirección | Qué es |
|---|---|
| `$D91F49-$D91F87` | Datos sin usar (único "unused" marcado en C0-FF) |
| `$FAA57C-$FAA597`, `$FB4935-$FB4B38`, `$FD8A9F-$FD8B6B` | Tilesets/datos S-DD1 sin usar (pasada física) |
| `$FFC800-$FFED2E` | Configuración de escenas comprimida LZ |

> Un patrón repetido: los datos se reparten entre **S-DD1** (gráficos) y **LZ**
> (texto/eventos/menús). Ambos requieren descompresión en runtime; el pump
> S-DD1 y el pump de subida SPC700 (`$C0:8A5B`/`$C0:887F`, handshake puerto
> `$2140`) son ya conocidos en el proyecto (ver `docs/HANDOFF.md`).

---

## 4. Webs de interés — qué aporta cada una

Fuente: `..Webs de interés.txt`. Todas se revisaron (2026-09-03).

### Emuladores / referencia de hardware

1. **https://problemkaputt.de/fullsnes.txt** — *Fullsnes* (nocash). La
   referencia canónica de hardware SNES en texto plano: registros PPU/DMA/APU,
   timing por ciclo, mapa de memoria, SPC700/S-DSP. Es el "spec" definitivo
   para validar decisiones de ciclos del recompilador.
2. **https://github.com/ares-emulator/ares** — Emulador multi-sistema enfocado
   en precisión (descendiente de higan/bsnes). Código legible, buen modelo de
   referencia para comportamiento exacto de PPU/CPU/APU.
3. **https://github.com/SourMesen/Mesen2** — Emulador multi-sistema (NES, SNES,
   GB…). Archivo histórico ~v2.1.1; el desarrollo actual vive en
   `nesdev-org/MesenCE`. Útil como emulador de depuración (traces, breakpoints)
   para contrastar nuestro runtime. **GPLv3** — solo consulta, no copiar código.
4. **https://github.com/etroimcasso/Snaggletooth** — VM SNES (5A22 + SPC700)
   **clean-room, licencia MIT**: núcleo SPC700 completo (256 opcodes,
   ciclo a ciclo), APU completa, S-DSP feature-complete, CPU 65816 completa;
   falta la PPU renderizadora. Su SPC700/DSP es una referencia de precisión de
   audio y sus vectores de test validan opcodes. Ya hicimos un estudio
   comparativo (ver `SNAGGLETOOTH_FINDINGS.md` en el fork).
5. **https://wiki.superfamicom.org/** — Wiki de desarrollo SNES: documentación
   de hardware (65816, mapa de memoria, open bus, DMA/HDMA, SPC700, BRR,
   N-SPC) y documentos por juego (incluye página de **Star Ocean**). Muy útil
   para resolver dudas de hardware concretas.
6. **https://sneslab.net/wiki/Special:AllPages** — Wiki con tutoriales y
   artículos de SNES (SA-1, HDMA, registros PPU, widescreen…). Complementa la
   wiki anterior, orientado a hacking de ROMs.

### Proyectos hermanos de recompilación (patrones a seguir)

7. **https://github.com/Cellenseres/Lufia2SNESRecomp** — Recompilación nativa
   de Lufia II con **snesrecomp**. Muy útil como plantilla de estructura:
   `recomp/` (CFG de control-flow), `src/` (host + runtime), submodule
   `lib/snesrecomp-platform` (renderer), lanzador con SDL/OpenGL, saves.
   Demuestra un juego completo (intro, título, gameplay, batallas, audio,
   input, guardado) sobre el mismo framework que usamos.
8. **https://github.com/brainWave4/ffv_snesrecomp** — Recompilación de FFV (J)
   con snesrecomp. Genera el código recompilado en `generated/` a partir de la
   ROM y lo empaqueta como **librería estática** (`snesrecomp_game`), dejando
   los límites de funciones y el dispatch indirecto como declaraciones en
   `config/`. Ilustra el flujo *generar → compilar → integrar con el runner*.
   ⚠️ Aviso legal del propio repo: `generated/` deriva de la ROM (copyright) —
   **no redistribuir**.
9. **https://github.com/DerrickGold/ar-recomp** — Port nativo de ActRaiser
   (SNES USA) construido sobre tu propia ROM: widescreen, efectos, saves,
   menú de ajustes y manual en el juego. Ejemplo de *producto final pulido*
   sobre un recompilador SNES, con docs de RE del juego original bajo MIT.
10. **https://github.com/elliotttate/DKC1Recomp** — Recompilación estática de
    DKC1 (USA v1.0) con **widescreen nativo y herramientas de depuración
    deterministas** (replays, capturas por frame, profiler JSONL, pacing).
    Excelente referencia metodológica: `docs/BRINGUP.md` (bitácora de
    bring-up), `docs/HOST_PACING.md` (reloj del host, recuperación de
    stalls). Usa un fork de snesrecomp **anclado** (pinned).

---

## 5. Lecciones aplicables al proyecto

- **El intérprete no es el destino**: los proyectos 7–10 demuestran que la
  meta es AOT completo + runner; nuestro runtime ya es funcional y el cuello
  hoy es el coste de las zonas LLE (spins SPC no cubiertos, pumps S-DD1/SPC).
- **Todo cambio se valida con A/B bit-exacto** (masters por frame), como ya
  hacemos con la caminata de 23.700 frames y el protocolo MC_LOG.
- **Documentación como producto**: DKC1Recomp y ar-recomp muestran que llevar
  un `docs/` con bitácora, hashes y gates de release es lo que hace un repo
  público creíble (relevante para nuestra limpieza final en
  `F:\StarOceanRecompRAID`).
- **Licencias**: ares/Mesen son GPL — solo referencia. Snaggletooth es MIT
  (usable). El código de snesrecomp que ya usamos mantiene su propia licencia.
- **Donde buscar en la ROM**: código en C0-CC; texto/eventos LZ en E4-E8
  (tabla de punteros en `$E40000`); nombres/descripciones en `$D7`; fuentes en
  `$DB` (S-DD1 1BPP) y `$FF` (japonesa); audio SPC700 en `$F9-$FF` con
  bloques BRR numerados por la pasada física del layout.

---

## 6. Fuentes y archivos relacionados

- `SO_jap_ROM_layout.txt` (3.057 líneas) — mapa completo de la ROM.
- `..Webs de interés.txt` — lista de URLs (sección 4).
- `docs/HANDOFF.md` — bitácora técnica del proyecto (bugs, fixes, validaciones).
- `docs/PLAN_20260901.md`, `docs/SUBMODULE_SETUP.md` — plan y setup.
- Fork de referencia: `F:\forkStarOcean` (PR1, pristino) — estructura y docs
  (`ENCICLOPEDIA.md`, `SNAGGLETOOTH_FINDINGS.md`, `BUILD_INFO.md`).
- Destino de la versión limpia para GitHub: `F:\StarOceanRecompRAID`.
