#!/usr/bin/env python3
"""Corrida de perfil del interprete que termina sola (histograma completo de PCs).

Por que existe: el histograma de PCs interpretados se volcaba SOLO al salir
(`atexit`), asi que obtenerlo exigia que un humano cerrase la ventana; y
lanzarlo a mano con `nohup env SNESRECOMP_REPLAY_CLOCK=...` es como se cuela el
error de reloj -- pasar `guest-master-clocks` (el texto que el motor IMPRIME) en
vez de `master` degrada a frames de host, la entrada aterriza en instantes de
invitado equivocados y el juego se queda clavado en el titulo con las estrellas.

Este lanzador usa `tools/replay_clock.py` (el reloj lo declara la cabecera del
guion), pone un deadline de frames de invitado (`SNESRECOMP_FRAME_DEADLINE`, que
hace salir al motor de forma ordenada) y activa el volcado del histograma
completo. Requiere un build con SNESRECOMP_INTERP_PROFILE (build-prof).

Uso:
    python tools/perfil_interp.py --frames 6000
    python tools/perfil_interp.py --frames 6000 --script mesen_master.txt
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
import replay_clock  # noqa: E402  (el reloj lo declara el guion)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="build-prof",
                    help="build con SNESRECOMP_INTERP_PROFILE (por defecto build-prof)")
    ap.add_argument("--script", default="mesen_master.txt",
                    help="guion de entrada en tools/input_scripts/ o ruta")
    ap.add_argument("--frames", type=int, default=6000,
                    help="frames de invitado antes de salir (deadline)")
    ap.add_argument("--out", default=None,
                    help="fichero del histograma (por defecto logs/h_full.txt)")
    ap.add_argument("--full-at", type=int, default=0,
                    help="volcar tambien en vivo al llegar a este frame (0 = solo al salir)")
    ap.add_argument("--no-turbo", action="store_true",
                    help="presentar frames (por defecto turbo sin presentar: solo vale para medir)")
    ap.add_argument("--timeout", type=int, default=3600)
    args = ap.parse_args()

    rel = ROOT / args.build / "Release"
    exe = rel / "StarOcean.exe"
    if not exe.exists():
        raise SystemExit("no existe %s" % exe)

    script = args.script
    if not os.path.exists(script):
        script = str(HERE / "input_scripts" / script)
    if not os.path.exists(script):
        raise SystemExit("no encuentro el guion de entrada: %s" % args.script)

    out = pathlib.Path(args.out) if args.out else rel / "logs" / "h_full.txt"
    out.parent.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    clock = replay_clock.apply(env, script)          # reloj del guion, no del log
    env["SNESRECOMP_INTERP_PROFILE_FULL"] = str(out)
    # OJO: la salida limpia es SNESRECOMP_EXIT_AT_FRAME, NO
    # SNESRECOMP_FRAME_DEADLINE -- esa ultima es el modelo de tiempo, y con
    # deadline > 0 el invitado cede el frame por deadline en vez de por
    # quiescencia y el DSP deja de tocar nada en toda la intro (ENCICLOPEDIA
    # 22.13). Un lanzador que confunda las dos no mide lo que dice medir.
    env["SNESRECOMP_EXIT_AT_FRAME"] = str(args.frames)
    if args.full_at:
        env["SNESRECOMP_INTERP_PROFILE_FULL_AT"] = str(args.full_at)
    if not args.no_turbo:
        env["SNESRECOMP_TURBO_PRESENT_EVERY"] = "0"

    log = rel / "logs" / "perfil_run.log"
    print("reloj del guion: %s" % clock)
    print("corriendo %s frames -> %s" % (args.frames, out))
    with open(log, "wb") as fh:
        p = subprocess.run([str(exe)], cwd=str(rel), env=env,
                           stdout=fh, stderr=subprocess.STDOUT, timeout=args.timeout)
    print("exit=%d  log=%s" % (p.returncode, log))
    if out.exists():
        lines = sum(1 for _ in open(out, encoding="utf-8", errors="replace"))
        print("histograma: %d PCs distintos en %s" % (lines, out))
    else:
        print("AVISO: no se genero el histograma (¿build sin SNESRECOMP_INTERP_PROFILE?)")
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
