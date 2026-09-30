#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Salud del audio con una configuracion arbitraria, en una linea por segundo.

Corre el build con SNESRECOMP_PCM_DUMP, lee el PCM entregado al dispositivo y
muestra pico/rms por segundo. Sirve para discriminar, con el MISMO binario,
que parte del modelo de fotograma deja de sonar (deadline, fast-forward de
quiescencia, filtro del escaneo de spin, ...).

Uso:
    python tools/pcm_health.py --build build-hm --frames 560
    python tools/pcm_health.py --build build-hm --env SNESRECOMP_FRAME_DEADLINE=1
"""
from __future__ import annotations

import argparse
import os
import pathlib
import struct
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
RATE = 32040


def run(rel: pathlib.Path, frames: int, env_extra: dict, script: str | None,
        log: pathlib.Path) -> pathlib.Path:
    pcm = pathlib.Path(tempfile.gettempdir()) / "so_pcm_health.pcm"
    if pcm.exists():
        pcm.unlink()
    env = dict(os.environ)
    env["SNESRECOMP_PCM_DUMP"] = str(pcm)
    env["SNESRECOMP_EXIT_AT_FRAME"] = str(frames)
    env["SNESRECOMP_LLE_BOUNCE"] = "1"
    env["SNESRECOMP_TURBO_PRESENT_EVERY"] = "0"
    if script:
        sys.path.insert(0, str(HERE))
        import replay_clock
        replay_clock.apply(env, script)
    env.update(env_extra)
    with open(log, "wb") as fh:
        subprocess.run([str(rel / "StarOcean.exe")], cwd=str(rel), env=env,
                       stdout=fh, stderr=subprocess.STDOUT, timeout=7200)
    return pcm


def seconds(pcm_path: pathlib.Path, rate: int = RATE):
    raw = pcm_path.read_bytes() if pcm_path.exists() else b""
    n = len(raw) // 4
    if n == 0:
        return []
    samples = struct.unpack("<%dh" % (n * 2), raw[:n * 4])
    out = []
    for s in range(n // rate):
        seg = samples[s * rate * 2:(s + 1) * rate * 2]
        out.append((max(abs(x) for x in seg),
                    (sum(x * x for x in seg) / len(seg)) ** 0.5))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="build-hm")
    ap.add_argument("--frames", type=int, default=560)
    ap.add_argument("--env", action="append", default=[],
                    help="VAR=valor (repetible)")
    ap.add_argument("--script", default="mesen_master.txt")
    ap.add_argument("--tag", default="pcm")
    args = ap.parse_args()

    rel = ROOT / args.build / "Release"
    script = str(HERE / "input_scripts" / args.script)
    if not os.path.exists(script):
        script = ""
    extra = dict(kv.split("=", 1) for kv in args.env)

    pcm = run(rel, args.frames, extra, script, rel / ("%s.log" % args.tag))
    secs = seconds(pcm)
    print("env=%s  ->  %d s de PCM" % (extra or "(base)", len(secs)))
    for s, (peak, rms) in enumerate(secs):
        flag = "SILENCIO" if peak == 0 else ("bajo" if rms < 20 else "audio")
        print("  %2ds peak=%6d rms=%8.1f %s" % (s, peak, rms, flag))
    return 0


if __name__ == "__main__":
    sys.exit(main())