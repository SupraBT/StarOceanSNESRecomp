#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lanza un build con el HUD y el disparador de captura en rojo, y para solo.

Sirve para recoger datos de las zonas calientes sin intervencion humana: cada
fotograma que supera SNESRECOMP_HOT_MS (18 ms) deja un BMP en
SNESRECOMP_HOT_DIR y una linea [hot] en el log.

Uso:
    python tools/hm_hot_run.py --build build-hm --frames 4000
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
import replay_clock  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="build-hm")
    ap.add_argument("--script", default="mesen_master.txt")
    ap.add_argument("--frames", type=int, default=1200)
    ap.add_argument("--hot-ms", type=float, default=18.0)
    ap.add_argument("--dir", default="hotshots")
    ap.add_argument("--bounce", type=int, default=1)
    ap.add_argument("--log", default="")
    args = ap.parse_args()

    rel = ROOT / args.build / "Release"
    exe = rel / "StarOcean.exe"
    if not exe.exists():
        raise SystemExit("no existe %s" % exe)

    script = args.script
    if not os.path.exists(script):
        script = str(HERE / "input_scripts" / script)
    if not os.path.exists(script):
        raise SystemExit("no encuentro el guion: %s" % args.script)

    env = dict(os.environ)
    clock = replay_clock.apply(env, script)
    env["SNESRECOMP_HUD"] = "1"
    env["SNESRECOMP_HOT"] = "1"
    env["SNESRECOMP_HOT_MS"] = str(args.hot_ms)
    env["SNESRECOMP_HOT_DIR"] = str((rel / args.dir).resolve())
    env["SNESRECOMP_EXIT_AT_FRAME"] = str(args.frames)
    env["SNESRECOMP_LLE_BOUNCE"] = str(args.bounce)
    env["SNESRECOMP_TURBO_PRESENT_EVERY"] = "0"
    env.setdefault("SNESRECOMP_PHASE_MS", "")

    log = pathlib.Path(args.log) if args.log else (rel / "hot.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    print("reloj=%s  frames=%d  umbral=%.1fms  log=%s"
          % (clock, args.frames, args.hot_ms, log))
    with open(log, "wb") as fh:
        rc = subprocess.run([str(exe)], cwd=str(rel), env=env,
                            stdout=fh, stderr=subprocess.STDOUT,
                            timeout=7200).returncode
    shots = sorted((rel / args.dir).glob("f*.bmp"))
    print("rc=%d  capturas=%d  -> %s" % (rc, len(shots), rel / args.dir))
    for line in log.read_text(errors="replace").splitlines():
        if line.startswith("[hot]"):
            print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
