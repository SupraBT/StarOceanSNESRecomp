#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Puerta A/B byte-exacta, lanzada entera y sin intervencion humana.

Por que existe: la puerta de exactitud del proyecto es ``tools/ab_lle.py`` (mismo
binario y mismo guion con ``SNESRECOMP_LLE_BOUNCE=1`` [AOT] y ``=0`` [interprete
puro], comparando ``[fstate]`` linea a linea), pero lanzarla a mano obligaba a
recordar el reloj del guion, el deadline de salida y los nombres de los logs -- y
equivocar cualquiera de los tres produce una corrida que no mide lo que dice
medir (ver ENCICLOPEDIA: pasar el texto del log como reloj degrada a frames de
host y el juego se queda en el titulo).

Este lanzador hace las dos corridas del MISMO exe con el MISMO guion, las deja en
``<build>/Release/logs/`` y llama a la comparacion.

Uso:
    python tools/ab_run.py --build build-ab --frames 6000
    python tools/ab_run.py --build build-ab --frames 6000 --etiqueta fixpy

Requiere un build con SNESRECOMP_FRAME_STATE (build-dev o cualquiera de
diagnostico). El build LIMPIO (SNESRECOMP_CLEAN_BUILD) no emite ``[fstate]`` y no
sirve para esta puerta.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import replay_clock  # noqa: E402  (el reloj lo declara la cabecera del guion)


def _run(exe: pathlib.Path, rel: pathlib.Path, script: str, frames: int,
         bounce: int, log: pathlib.Path) -> int:
    env = dict(os.environ)
    clock = replay_clock.apply(env, script)
    env["SNESRECOMP_FRAME_STATE"] = "1"
    # La salida limpia es EXIT_AT_FRAME; FRAME_DEADLINE es el modelo de tiempo y
    # con deadline > 0 el invitado cede por deadline y el DSP deja de sonar.
    env["SNESRECOMP_EXIT_AT_FRAME"] = str(frames)
    env["SNESRECOMP_LLE_BOUNCE"] = str(bounce)
    env["SNESRECOMP_TURBO_PRESENT_EVERY"] = "0"
    print("  clock=%s  LLE_BOUNCE=%d  -> %s" % (clock, bounce, log))
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "wb") as fh:
        p = subprocess.run([str(exe)], cwd=str(rel), env=env,
                           stdout=fh, stderr=subprocess.STDOUT, timeout=7200)
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="build-dev")
    ap.add_argument("--script", default="mesen_master.txt")
    ap.add_argument("--frames", type=int, default=6000)
    ap.add_argument("--etiqueta", default="ab", help="prefijo de los logs")
    args = ap.parse_args()

    rel = ROOT / args.build / "Release"
    exe = rel / "StarOcean.exe"
    if not exe.exists():
        raise SystemExit("no existe %s (compile ese build primero)" % exe)

    script = args.script
    if not os.path.exists(script):
        script = str(HERE / "input_scripts" / script)
    if not os.path.exists(script):
        raise SystemExit("no encuentro el guion de entrada: %s" % args.script)

    log_dir = rel / "logs"
    a = log_dir / ("%s_aot.log" % args.etiqueta)
    b = log_dir / ("%s_lle.log" % args.etiqueta)

    print("corrida A (AOT, LLE_BOUNCE=1):")
    rc_a = _run(exe, rel, script, args.frames, 1, a)
    print("corrida B (interprete puro, LLE_BOUNCE=0):")
    rc_b = _run(exe, rel, script, args.frames, 0, b)

    print("\ncomparando con tools/ab_lle.py ...")
    cmp_rc = subprocess.run(
        [sys.executable, str(HERE / "ab_lle.py"), "--a", str(a), "--b", str(b)],
        cwd=str(ROOT)).returncode
    print("\nrc: A=%d B=%d comparacion=%d" % (rc_a, rc_b, cmp_rc))
    return cmp_rc


if __name__ == "__main__":
    sys.exit(main())
