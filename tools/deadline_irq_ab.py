#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A/B de la deadline de fotograma contra la entrega de NMI/IRQ.

 corre el mismo build dos veces (deadline 0 y deadline 1) con
SNESRECOMP_FRAME_STATE=1 y compara por fotograma:

  irq=  g_interp_irq_entries   (entradas al handler de IRQ)
  nmi=  g_interp_nmi_entries   (entradas al handler de NMI)
  E1=   $00E1, contador de ticks del handler de V-IRQ (C0:024C), que es
        donde vive el tick del driver de sonido del juego (C0:032D)

asi se ve, sin suponer nada, si con deadline el handler de V-IRQ sigue
entrando o si de verdad se deja de entregar.

Uso:
    python tools/deadline_irq_ab.py --build build-hm --frames 900
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


def run(rel: pathlib.Path, exe: pathlib.Path, script: str, frames: int,
        deadline: str, tag: str) -> pathlib.Path:
    env = dict(os.environ)
    replay_clock.apply(env, script)
    env["SNESRECOMP_EXIT_AT_FRAME"] = str(frames)
    env["SNESRECOMP_LLE_BOUNCE"] = "1"
    env["SNESRECOMP_TURBO_PRESENT_EVERY"] = "0"
    env["SNESRECOMP_FRAME_STATE"] = "1"
    env["SNESRECOMP_FRAME_BUDGET"] = "1"
    env["SNESRECOMP_ENABLE_AUDIO"] = "0"
    if deadline:
        env["SNESRECOMP_FRAME_DEADLINE"] = deadline
    else:
        env.pop("SNESRECOMP_FRAME_DEADLINE", None)
    log = rel / ("irqab_%s.log" % tag)
    with open(log, "wb") as fh:
        subprocess.run([str(exe)], cwd=str(rel), env=env,
                       stdout=fh, stderr=subprocess.STDOUT, timeout=7200)
    return log


def parse(log: pathlib.Path):
    """f -> (irq, nmi, E1, dgf, dmaster)"""
    out = {}
    for line in log.read_text(errors="replace").splitlines():
        if line.startswith("[fstate]"):
            d = {}
            for kv in line.split()[1:]:
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    d[k] = v
            f = int(d.get("f", -1))
            if f >= 0:
                out[f] = (d.get("irq"), d.get("nmi"), d.get("E1"),
                          d.get("master"))
        elif line.startswith("[irqstate]"):
            d = {}
            for kv in line.split()[1:]:
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    d[k] = v
            f = int(d.get("f", -1))
            if f in out:
                out[f] = out[f][:2] + (d.get("E1"), out[f][3])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="build-hm")
    ap.add_argument("--script", default="mesen_master.txt")
    ap.add_argument("--frames", type=int, default=900)
    ap.add_argument("--deadline", default="1")
    ap.add_argument("--cada", type=int, default=50)
    args = ap.parse_args()

    rel = ROOT / args.build / "Release"
    exe = rel / "StarOcean.exe"
    if not exe.exists():
        raise SystemExit("no existe %s" % exe)
    script = args.script
    if not os.path.exists(script):
        script = str(HERE / "input_scripts" / script)

    la = run(rel, exe, script, args.frames, "", "A")
    lb = run(rel, exe, script, args.frames, args.deadline, "B")
    A, B = parse(la), parse(lb)
    print("A=sin deadline   B=SNESRECOMP_FRAME_DEADLINE=%s   frames=%d"
          % (args.deadline, args.frames))
    print("  f |      A: irq  nmi  E1  master |      B: irq  nmi  E1  master")
    for f in range(args.cada, args.frames + 1, args.cada):
        a, b = A.get(f), B.get(f)
        if not a or not b:
            continue
        print("%4d | %14s %4s %4s %12s | %14s %4s %4s %12s"
              % (f, a[0], a[1], a[2], a[3], b[0], b[1], b[2], b[3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())