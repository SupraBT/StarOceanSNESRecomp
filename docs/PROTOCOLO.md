# Protocolo de trabajo (acordado 2026-09-29)

Regla única: **nada de conjeturas ni hipótesis**. Si aparece algo, se hacen pruebas,
se corroboran datos, y sólo se aplica si pasa la comparativa A/B byte-exacto. Si no
la pasa, **se anota en `DESCARTADAS.md`** por si sirve en otra zona, y se continúa
con el siguiente error.

## El ciclo, paso a paso

1. **Medir el sintoma antes de tocar nada.** Con un instrumento que mire lo que de
   verdad importa. Si el sintoma es "no se oye", el instrumento es el PCM que sale
   al dispositivo (`SNESRECOMP_PCM_DUMP`), *no* los contadores del motor: el
   2026-09-29 el juego estaba mudo con `dropped=0` y `underflows` de arranque.
2. **Escribir la hipótesis como una predicción falsable.** "Si es X, entonces
   mediré Y". Sin prediccion no hay prueba, hay opinion.
3. **Un experimento por hipótesis**, con el resto de variables fijas y el mismo
   binario o dos binarios que sólo difieran en el cambio.
4. **Corroborar con datos** (tabla antes/despues, no impresiones).
5. **La puerta: A/B byte-exacto.** Si el cambio *no* debe alterar el
   comportamiento, tiene que dar `[fstate]` y `$2100` identicos. Si el cambio *si*
   debe alterarlo (el modelo de frame, por ejemplo), se valida contra la traza de
   hardware/emulador de referencia y se documenta el nuevo baseline.
6. **Aplicar o anotar.** Si pasa, se aplica y se documenta en `ENCICLOPEDIA.md`. Si
   no pasa, se revierte **y se anota en `DESCARTADAS.md`** con la evidencia.

## Comandos

```bash
# La puerta completa de un cambio (audio + fps + A/B + determinismo + turbo):
python tools/verificar.py

# Turbo (aceleracion del host) para pasar rapido el tramo ya revisado:
#   Tab                        a mano (config.ini: Turbo = Tab)
#   SNESRECOMP_FORCE_TURBO=1   todo el rato (soak)
#   SNESRECOMP_TURBO_BURST=a,n solo los frames de invitado [a, a+n)
# Turbo NO toca al invitado (el test `turbo` de la puerta lo exige) pero tampoco
# sirve para escuchar: el dispositivo drena a 1x mientras el invitado va a ~3x.

# Sólo el audio (con y sin deadline):
python tools/audio_health.py
python tools/audio_health.py --deadline=1

# NOTA (2026-10-02): el golden se regenero con --update-golden porque el
# commit 2d7244a (2026-09-30) anadio el sufijo `A= X= Y= P=` al [fstate] y el
# baseline era del 29 13:01. Verificado ANTES de regenerar: los 26 campos
# antiguos eran byte-identicos en los 2100 frames (diff vacio tras quitar el
# sufijo), o sea cambio de FORMATO, no de comportamiento.

# A/B byte-exacto de dos configuraciones cualquiera:
#   dev build + SNESRECOMP_FRAME_STATE=1 -> fichero de lineas [fstate] -> diff
SNESRECOMP_EXIT_AT_FRAME=2100 SNESRECOMP_FRAME_STATE=1 ./StarOcean.exe 2>f1.log
SNESRECOMP_EXIT_AT_FRAME=2100 SNESRECOMP_FRAME_STATE=1 SNESRECOMP_X=1 ./StarOcean.exe 2>f2.log
grep '^\[fstate\]' f1.log > a.fstate; grep '^\[fstate\]' f2.log > b.fstate
diff a.fstate b.fstate        # vacio = pasa

# Instrumentos de verdad (todos env-gated, coste cero si no se usan):
#   SNESRECOMP_PCM_DUMP=<pcm>        PCM real entregado al dispositivo (S16LE)
#   SNESRECOMP_AUDIO_STATS=1|<path>  contadores del anillo por segundo
#   SNESRECOMP_DSPREG_TRACE_FILE=<p> escrituras a registros del DSP (key-on!)
#   SNESRECOMP_PCHIT=C0032D,...      cuantas veces se ejecuta un pc24 exacto
#   SNESRECOMP_FRAME_STATE=1         [fstate] por frame (26 campos)
#   SNESRECOMP_FRAME_BUDGET=1        dgf/dmaster por frame de host
#   SNESRECOMP_PHASE_MS=1            reparto emu/draw por ventana
#   SNESRECOMP_SLOWFRAME_MS=<ms>     frames individuales caros
#   SNESRECOMP_FORCE_TURBO=1         turbo en todos los frames (ver ENCICLOPEDIA #22.16)
#   SNESRECOMP_TURBO_BURST=<a>,<n>   turbo solo en los frames [a, a+n)
#   SNESRECOMP_TURBO_PRESENT_EVERY=N 1 present cada N frames de turbo (0 = ninguno)
```

## Reglas que ya nos han costado tiempo (no repetir)

* **Mirar el fichero que se compila.** `snesrecomp/runner/src/common_rtl.c` es el
  que entra en el enlace; `snesrecomp/runner/src/snes/common_rtl.c` **no**. Son
  distintos.
* **Leer el contador total, no la lista truncada.** Un cap de salida de 240 lineas
  hizo leer "se ejecuta 1 vez" cuando eran 57/60.
* **Cuidado con las columnas.** Un volcado con columnas desplazadas invento un
  "no hay consumo" que no existia. Las sondas nuevas escriben campos fijos.
* **Verificar el instrumento antes de creer el dato.** El detector de silencio de
  `audio_health.py` se valida en las dos direcciones (`--deadline=1` debe fallar).
* **Un cambio sin A/B no es un cambio, es una apuesta.** Y si se revierte, se anota.
