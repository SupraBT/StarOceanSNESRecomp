# Ideas, hipotesis y cambios medidos que NO se aplicaron

Registro de trabajo siguiendo `PROTOCOLO.md`: todo lo que se probo y no paso la
puerta queda aqui con su evidencia. No es una lista de fracasos: es la memoria de
que se descarto y **por que**, para no volver a gastar horas y por si en otra zona
del emulador el dato resulta util.

Formato: que se probo, que se midio, por que no se aplico, donde podria servir.

---

## 2026-09-29 — Reloj del APU = reloj master del invitado *revertido*

**Que se probo.** En `rtl_sync_apu_frame_boundary()` (common_rtl.c, el que se
compila) cambiar el objetivo del APU de la rejilla de frames del host
(`snes_frame_counter * 357368 * NUM/DEN`) al reloj master del invitado
(`rtl_apu_guest_cycle()`), argumentando que el SPC700 y el 65816 derivan del mismo
cristal y que la rejilla de frames puede quedar por detras del ancla del APU.

**Que se midio.** `python tools/audio_health.py --frames 1400 --deadline=1` antes y
despues: **identico fallo** (6 segundos en silencio absoluto desde el 8, pico 2 en
adelante). Con la deadline en 0 tampoco cambia (16/18 segundos con musica).

**Por que no se aplico.** No arregla el fallo que se perseguia y toca un camino
delicado; sin evidencia a favor, se revierte (el arbol quedo con la formula
original).

**Donde podria servir.** Si algun dia se activa la deadline y aparece un desfase de
un frame entre el reloj del APU y el del CPU, esta es la primera palanca a mirar:
las dos formulas coinciden con `dgf=1` y divergen cuando el invitado cede antes de
tiempo.

---

## 2026-09-29 — Desacoplar el reloj del DSP del reloj de frames (NO probado, anotado)

**La idea.** Que el hilo de audio avance la parte DSP (nunca el SPC700) para que el
anillo no se quede seco cuando el host va por debajo de 60 fps.

**Por que NO se ha probado siquiera.** El motor lo prohibe a proposito ("the host
callback is a consumer only... allowing it to invent SPC cycles makes its wall-clock
schedule a second, competing emulation clock"). Convertiria el audio en
no determinista: `prod_audio` dejaria de ser 0 y el A/B byte-exacto y los replays
dejarian de valer. Con los arreglos de §22.12 el anillo ya no se queda seco, asi que
la idea queda sin caso de uso.

**Donde podria servir.** Solo en un cliente que acepte perder determinismo (un
visor de audio, o un modo "solo escuchar"). No en el runner de A/B.

---

## 2026-09-29 — `DisableFrameDelay=1` como causa del audio (descartado con datos)

**Que se probo.** Poner `DisableFrameDelay=0` en `build-dev` para igualarlo a los
builds limpios (era el unico fichero de configuracion distinto).

**Que se midio.** Con deadline: `DisableFrameDelay=1` -> 1137 muestras tiradas;
`=0` -> **4710**. Empeora. No era el pacing del bucle.

**Por que no se aplico.** No es la causa; se restauro el fichero del usuario tal cual.

**Donde podria servir.** Como recordatorio de que el pacing del host afecta a la
*distribucion* de los datos, no a la existencia del audio.

---

## 2026-09-29 — Sospechas de los fast-forwards como causa del silencio (descartado con datos)

**Que se probo.** Con la deadline activa, desactivar por separado los dos
fast-forwards: el de quiescencia (`SNESRECOMP_NO_QUIESCENT_FF=1`, puerta anadida
para el aislamiento) y el de vblank (`SNESRECOMP_NO_VBLANK_FF=1`).

**Que se midio.** `SNESRECOMP_PCM_DUMP` da el **mismo silencio** en las tres
configuraciones (0-13 s a pico 0, chasquido en f790, pico 2 despues). Es la deadline
en si.

**Por que no se aplico.** No eran la causa. La puerta de aislamiento se queda (tiene
coste cero y sirve para volver a separar las dos variables en el futuro).

**Donde podria servir.** El aislamiento por puerta del FF de quiescencia es
reutilizable para cualquier futura investigacion del modelo de frame.

---

## 2026-09-29 — Instrumentos que mintieron (anotado para no repetir)

* **Lectura truncada.** Una sonda de PCs con cap de salida de 240 lineas hizo leer
  "se ejecuta 1 vez" cuando eran 57/60. Mirar siempre el contador total.
* **Columnas desplazadas.** Trazas TSV antiguas omitían campos vacíos: un
  desplazamiento inventó un "el consumidor no consume" inexistente. Las sondas
  nuevas escriben 15 campos fijos siempre.
* **El numero de cabecera.** `RTL_AUDIO_NATIVE_RATE 32040.0 /* 1.024 MHz/32 */`: el
  comentario se contradecia con el valor (1.024 MHz/32 = 32000) y ese 0,3% de
  desajuste dejo el juego mudo. Un comentario que no cuadra con su constante es un
  bug esperando.
* **Trazas APU que no ven lo que parece.** `SNESRECOMP_APU_PORT_RW` solo registra
  62 accesos en toda la intro: los puertos del APU que pasa el puente del
  interprete no pasan por ese camino. Para "el invitado le habla al driver?" usar
  `PCHIT` (¿se ejecuta el tick?) y `DSPREG_TRACE_FILE` (¿escribe notas?).

---

## 2026-09-29 — Guiones de entrada sinteticos para la puerta A/B (retirados)

**Que se probo.** Crear guiones de pulsaciones inventados (`intro_start.txt`,
`campo_movimiento.txt`) para que la puerta A/B cubriera escenas con input: Start
periodicos, direcciones mantenidas y A.

**Que se midio.** El A/B pasaba y divergian de la corrida sin input desde el frame
901 (justo la primera pulsacion), o sea que cubrian codigo distinto... pero eso no
es lo mismo que **avanzar en el juego**. El usuario lo vio en vivo: el personaje se
quedaba pulsando A, subiendo y bajando, entrando en Continue y andando a derecha e
izquierda. Un machaque de botones no recorre el guion del juego, asi que no cubre
las escenas que interesan (menu de nombre, cinematica, campo real).

**Que se usa en su lugar.** La grabacion real de pulsaciones,
`tools/input_scripts/grabada.txt` (copiada de `build-dev/Release/rep_bueno.txt`):
cinco pulsaciones de A que recorren intro -> menu -> seleccion de nombre ->
cinematica, coincidiendo con
`StarOceanRecompDocumentacion/Secuencia pulsaciones trace.txt`. Aterrizajes
verificados con `SNESRECOMP_REPLAY_LOG=1` (f66 C8F428, f147 C38FA8, f209 C39069,
f270 C38FAD, f413 C2FCF8).

**Leccion para la puerta.** El baseline de una escena tiene que salir de una
grabacion real de una persona jugando, no de un guion inventado: lo segundo mide
que el emulador no se rompe, pero no que la escena ocurra.
