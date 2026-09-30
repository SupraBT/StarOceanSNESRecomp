#!/usr/bin/env python3
"""Con que reloj se keyea un guion de entrada (lo comparten la puerta y el audio).

Un guion de entrada es '<clave> <mascara hex>' por linea. La clave puede ser el
indice de frame de invitado (por defecto), los ciclos de CPU del invitado
(`cpu`) o el master clock del invitado (`master`); el motor lo elige con
SNESRECOMP_REPLAY_CLOCK.

Por que existe este modulo: el indice de frame NO es una clave fiable para una
grabacion hecha en hardware. Medido el 2026-09-30 con la sesion de Mesen
(TracesMesen, 29.560 frames): a la altura del frame 1170 nuestro invitado
llevaba ~27 M de master de ventaja sobre el de hardware, asi que la pulsacion de
A grabada en el frame 1173 aterrizaba en otro instante del juego; el menu de
seleccion de nombre se quedaba quieto y parecia colgado (y solo 9 de los 14
frames con A de ese tramo llegaban al invitado). La misma grabacion keyeada al
master mete esa pulsacion a 54.382 ciclos (~7 ms) del instante grabado, y la
partida sigue.

El guion declara su reloj en la cabecera, para que `--script <nombre>` acierte
solo:

    # clock: master

Lo escribe tools/mesen_replay_por_reloj.py al convertir un trace de Mesen.
"""
import os

VALID = ("master", "cpu", "frame")


def clock_for(path):
    """Lee la directiva `# clock: ...` de la cabecera del guion (None si no hay)."""
    if not path:
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for _ in range(12):
                line = fh.readline()
                if not line:
                    break
                text = line.strip().lstrip("#").strip().lower()
                if text.startswith("clock:"):
                    value = text.split(":", 1)[1].strip()
                    return value if value in VALID else None
    except OSError:
        return None
    return None


def apply(env, path):
    """Deja `env` listo para reproducir `path` con el reloj que declara.

    Devuelve el reloj aplicado ('frame' si el guion no declara ninguno). La pausa
    tras cada Up se anula: es reloj de pared y solo alarga la corrida.
    """
    env["SNESRECOMP_REPLAY_FILE"] = path
    env["SNESRECOMP_REPLAY_UP_PAUSE_MS"] = "0"
    clock = clock_for(path)
    if clock and clock != "frame":
        env["SNESRECOMP_REPLAY_CLOCK"] = clock
    else:
        # Que no se cuele un reloj heredado del entorno del que llama.
        env.pop("SNESRECOMP_REPLAY_CLOCK", None)
        clock = "frame"
    return clock


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        print("%s -> %s" % (os.path.basename(arg), clock_for(arg) or "frame"))
