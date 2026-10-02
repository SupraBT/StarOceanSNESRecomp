# Log de eventos por bajón de FPS (`evlog`)

Instrumento de diagnóstico. Cuando el HUD se pone rojo, deja un fichero de texto
con el estado de los fotogramas de alrededor del bajón. Fuera de un bajón no
escribe nada.

## Qué problema resuelve

El contador de FPS solo se refresca una vez por segundo y el del título de la
ventana no guarda histórico. Cuando algo tarda 300 ms en el fotograma 412, a
simple vista no queda rastro de qué pasó ni de qué había justo antes. El HUD
dentro de la imagen lo hace visible, pero se pierde en cuanto pasan unos
frames. Este módulo lo convierte en un fichero.

## Uso

```bash
SNESRECOMP_EVLOG=1 ./StarOcean.exe "Star Ocean (Japan).sfc"
```

Sale un directorio `evlogs/` con un fichero por evento: `evlogs/f000385.log`.

| variable | por defecto | para qué |
|---|---|---|
| `SNESRECOMP_EVLOG` | apagado | activa el registro |
| `SNESRECOMP_HOT_MS` | 18 | umbral del rojo, en ms. **El mismo que ya usa el HUD y `[hot]`** |
| `SNESRECOMP_EVLOG_DIR` | `evlogs` | dónde escribir |
| `SNESRECOMP_EVLOG_PRE` | 5 | fotogramas de histórico **antes** del bajón |
| `SNESRECOMP_EVLOG_TAIL` | 2 | fotogramas que se siguen escribiendo tras recuperarse |
| `SNESRECOMP_EVLOG_CSV` | apagado | formato CSV en vez de columnas alineadas |
| `SNESRECOMP_EVLOG_MAX` | 64 | tope de ficheros por sesión (deja de abrir, no borra) |

El umbral **no se recalcula**: el módulo recibe del HUD el mismo booleano
`ciclo > s_hot_ms` que decide el color. Si el HUD salió rojo, hay log. No pueden
discrepar.

## Formato

Una línea por fotograma. Dos formatos, mismo contenido:

- **Columnas alineadas** (por defecto): `f=381 loop=381 C=16.71ms emu=... | ...`.
  Se lee de un vistazo y se parte con `cut` o `grep`.
- **CSV** (`SNESRECOMP_EVLOG_CSV=1`): 48 columnas con nombre. La primera línea
  del fichero es la cabecera.

Los dos llevan encima un bloque de comentarios `#` que explica cada columna.

## Columnas

| grupo | campos |
|---|---|
| tiempos de host | `C` (ciclo), `emu`, `draw`, `sdd1`, FPS |
| relojes | `master` (g_cpu.master_cycles), `mesenCycEst`, `dMaster`, `dSpc`, `spcCyc`, `PC` |
| temporizadores | `T0`/`T1`/`T2` = target/divider/counter/enabled del SPC700 |
| E/S `$2140-$2143` | `in` (lo que ve el SPC), `out` (lo que escribe el SPC), `w` (último byte del invitado), `cnt` (bytes acumulados por puerto), `q` (cola pendiente) |
| bucle principal | `spcRd` (lecturas del SPC), `dspW` (escrituras SPC→DSP), `apuSync` |

## Cómo enfrentarlo con Mesen

La columna que interesa es **`dMaster`**: los ciclos maestro que consumió el
invitado en ese fotograma. En hardware son exactamente **357.368 por
fotograma**, así que la comparación es directa contra la columna de avance por
frame del TSV de Mesen. `dSpc` es laequivalenta para el SPC700: **17.088 por
fotograma** (1,024 MHz / 60 Hz).

`mesenCycEst` (`master + 48766`) convierte al `Cycle:` de la traza por
instrucción. Va con dos avisos, y los dos importan:

1. La calibración se midió en una ventana concreta, no es universal.
2. **El índice de fotograma no es una coordenada compartida** entre el motor
   (arranque HLE) y el hardware (reset de Mesen). Por eso el log lleva `f=` y
   `loop=` por separado, para que alinear sea una decisión explícita.

## Advertencia conocida: la columna `sdd1` no es tiempo de pared

Viene de `sdd1_prof_ms`, que convierte un contador **TSC** (`__rdtsc`) a
milisegundos con el factor de `QueryPerformanceFrequency`. En una máquina
virtual esos dos relojes no están sincronizados y el factor no vale: medido en
este equipo, un fotograma de **84 ms de pared** sale con `sdd1=275 ms`.

Sirve como indicador **relativo** de cuándo hay descompresión, no como coste.
Para el coste real están `C` y `emu`, que sí salen de
`SDL_GetPerformanceCounter`. La advertencia está escrita en la cabecera de cada
fichero para que no haya que recordar esto.

## Rendimiento

Apagado, el coste es una llamada por fotograma que consulta un `static` y
vuelve. Además la consulta del perfil de S-DD1 (que sí cuesta) solo se hace si
el log o `[perf]` están activos: antes de este cambio solo ocurría con `[perf]`.

En build limpio (`SNESRECOMP_CLEAN_BUILD=ON`) el módulo **no se compila**:
`EvLogEnabled()` devuelve 0 y el resto es un stub, siguiendo la convención del
proyecto de sacar fuera los monitores de desarrollo. Verificado: el binario de
`build-rel` no contiene ni una cadena `SNESRECOMP_EVLOG`.

## Un ejemplo real

Sin turbo, 500 fotogramas, umbral 12 ms. El fotograma 69 tardó 84 ms:

```
f=68  C= 14.59ms emu= 13.02 dSpc=17071  | in=1D0C3775 out=01000000 dspW=47
f=69  C= 84.38ms emu= 78.75 dSpc=34118  | in=0B4B3775 out=81010000 dspW=55
f=70  C=  5.70ms emu=  1.38 dSpc=17038  | in=0B4B3775 out=81010000 dspW=58
```

`dSpc=34118` es exactamente el doble de lo normal: en ese fotograma el SPC
hizo trabajo de dos frames. `emu=78.75` contra `C=84.38` sitúa el coste dentro
de la emulación, no en el dibujado ni en la presentación.

## Cuidado con el turbo al medir audio

Las mediciones de audio **no** sirven en `SNESRECOMP_FORCE_TURBO=1`: en turbo el
bucle vaTan rápido como puede y el callback de audio no recibe servicio igual,
así que la música no suena. Para reproducir una escena con sonido, sin turbo.

La diferencia de reparto es grande y visible en `[perf]`:

| | turbo | sin turbo |
|---|---|---|
| `loop` | ~9 ms | ~16,6 ms |
| `emu` | ~9 ms | ~1,4 ms |
| `resto` | ~0 | ~14 ms (espera de vsync) |

Lo que **sí** es independiente del turbo es el estado del invitado. Comparando
las dos formas de ejecución sobre la misma ventana, el estado del SPC700 sale
casi idéntico (`ticks` 302→310 frente a 302→309, `dspW` congelado en 824 en
ambos, mismos cinco PCs de sondeo de `$FD`, 677 lecturas con `val=01` frente a
640). Las conclusiones de §22.29 no dependían del turbo.

## Ficheros

- `src/evlog.h`, `src/evlog.c` — el módulo.
- `src/main.c` — enganche en `HmDraw()`, y el delta de S-DD1 ahora se calcula
  una vez y lo comparten `[perf]` y el log.
- `snesrecomp/runner/src/snes/apu.c` — `g_apu_last_port_w[]` y
  `g_apu_port_wcount[]`: el último byte que el invitado entregó en cada
  `$2140-$2143` y cuántos van. Se anotan **en el punto de entrega**, porque
  muestrearlos una vez por fotograma no serviría: entre dos muestras el invitado
  puede escribir cientos de veces.
