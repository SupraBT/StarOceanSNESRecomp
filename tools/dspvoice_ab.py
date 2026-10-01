#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A/B del estado de la CAPA DE VOCES del DSP con y sin deadline de frame.

Por que existe: con SNESRECOMP_FRAME_DEADLINE=1 el anillo del DSP sale entero a
cero (dsp_ring_energy()=0 durante 624 frames), y sin deadline empieza a sonar en
f328.  El調節 del tiempo esta validado, el problema es la senal.  Este lanzador
corre las dos configuraciones con el MISMO guion y el MISMO reloj, yAlignment
imprime las lineas [dspvoice] de los frames que elijamos para ver en que punto
se pierde: BRAM vacio, BRR a cero, ganancia 0, volumen maestro 0 o mute.
"""
from __future__ import annotations
import argparse, os, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import replay_clock  # noqa: E402


def run(rel, script, frames, deadline, log):
    env = dict(os.environ)
    replay_clock.apply(env, script)
    env["SNESRECOMP_EXIT_AT_FRAME"] = str(frames)
    env["SNESRECOMP_LLE_BOUNCE"] = "0"
    env["SNESRECOMP_TURBO_PRESENT_EVERY"] = "0"
    env["SNESRECOMP_DSPSTAT"] = "1"
    env["SNESRECOMP_FRAME_DEADLINE"] = str(deadline)
    env.pop("SNESRECOMP_HOT", None)
    env.pop("SNESRECOMP_HUD", None)
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "wb") as fh:
        subprocess.run([str(rel / "StarOcean.exe")], cwd=str(rel), env=env,
                       stdout=fh, stderr=subprocess.STDOUT, timeout=7200)
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="build-hm")
    ap.add_argument("--script", default="mesen_master.txt")
    ap.add_argument("--frames", type=int, default=360)
    ap.add_argument("--pick", default="40,120,200,260,300,320,328,340,355")
    args = ap.parse_args()

    rel = ROOT / args.build / "Release"
    script = args.script
    if not os.path.exists(script):
        script = str(HERE / "input_scripts" / script)

    pick = [int(x) for x in args.pick.split(",")]
    logs = {}
    for dl in (0, 1):
        tag = "dl0" if dl == 0 else "dl1"
        logs[dl] = run(rel, script, args.frames, dl,
                       rel / "logs" / ("dspvoice_%s.log" % tag))
        print("=== deadline=%d -> %s" % (dl, logs[dl]))

    for dl in (0, 1):
        print("\n########## SNESRECOMP_FRAME_DEADLINE=%d ##########" % dl)
        cur = None
        for line in logs[dl].read_text(errors="replace").splitlines():
            if line.startswith("[dspvoice]"):
                cur = int(line.split()[1].split("=")[1])
            if line.startswith("[dspvoice]") and cur in pick:
                print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
