#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lanza el juego con el HUD y el disparador de captura, para jugar y marcar
las zonas calientes a ojo.

Que hace:
  - HUD dentro de la imagen (arriba a la izquierda): F<frame> C<ms de ciclo>
    D<ms de dibujo> <n>FPS. En ROJO cuando el fotograma pasa de 18 ms, que es
    exactamente el bajon que se ve.
  - Cada vez que un fotograma se pone rojo guarda una captura BMP de ese
    fotograma (ya con el HUD dentro) en build-hm/Release/hotshots/, y escribe
    una linea [hot] con frame, ms, dibujo y fps.
  - Con SNESRECOMP_PHASE_MS=1 tambien escribe el desglose emu/draw.

Uso:
    python tools/jugar_con_hot.py                  # normal, hasta que cierres
    python tools/jugar_con_hot.py --frames 2000    # para y saca el resumen
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="build-hm")
    ap.add_argument("--frames", type=int, default=0,
                    help="0 = jugar hasta que se cierre la ventana")
    ap.add_argument("--hot-ms", type=float, default=18.0,
                    help="umbral de rojo en ms de ciclo por fotograma")
    ap.add_argument("--dir", default="hotshots")
    args = ap.parse_args()

    rel = ROOT / args.build / "Release"
    exe = rel / "StarOcean.exe"
    if not exe.exists():
        raise SystemExit("no existe %s" % exe)

    env = dict(os.environ)
    env["SNESRECOMP_HUD"] = "1"
    env["SNESRECOMP_HOT"] = "1"
    env["SNESRECOMP_HOT_MS"] = str(args.hot_ms)
    env["SNESRECOMP_HOT_DIR"] = str((rel / args.dir).resolve())
    env["SNESRECOMP_PHASE_MS"] = "1"
    if args.frames:
        env["SNESRECOMP_EXIT_AT_FRAME"] = str(args.frames)

    log = rel / "jugando.log"
    shots = rel / args.dir
    print("jugando.  HUD y capturas automaticas activados.")
    print("  capturas de fotogramas lentos -> %s" % shots)
    print("  log                         -> %s" % log)
    print("  cierralo cuando quieras; las capturas se quedan para revisarlas.")
    with open(log, "wb") as fh:
        rc = subprocess.run([str(exe)], cwd=str(rel), env=env,
                            stdout=fh, stderr=subprocess.STDOUT).returncode

    n = len(list(shots.glob("f*.bmp"))) if shots.exists() else 0
    print("\nrc=%d  fotogramas lentos capturados: %d" % (rc, n))
    lines = [l for l in log.read_text(errors="replace").splitlines()
             if l.startswith("[hot]")]
    for l in lines[-40:]:
        print("  " + l.replace(str(rel), ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())