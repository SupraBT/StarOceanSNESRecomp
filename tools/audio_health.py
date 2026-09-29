#!/usr/bin/env python3
"""Salud del audio: ?el juego SUENA de verdad?

Por que existe
--------------
El 2026-09-29 el juego se quedo MUDO sin que ningun contador del motor se quejara:
`produced`, `consumed`, `dropped` y `underflows` estaban todos perfectos (anillo
lleno, sin hambre, sin descartes) y sin embargo el DSP emulado no tocaba nada. Se
perdieron horas porque se medía todo MENOS lo que sale por el altavoz. Este test
mide exactamente eso: vuelca (`SNESRECOMP_PCM_DUMP`, ver ENCICLOPEDIA #22.13) el
PCM que `FillAudioBuffer` entrega al dispositivo y comprueba que hay señal donde
tiene que haberla.

Uso
---
    python tools/audio_health.py                # build-dev, deadline por defecto
    python tools/audio_health.py --deadline=1   # espera reproducir el fallo
    python tools/audio_health.py --expect-audio-from=8

Sale con 0 si la salud pasa, 1 si no. Pensado para correr tras tocar el modelo de
frame, el camino de audio o los fast-forwards.
"""
import argparse
import os
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def build_dir(explicit):
    if explicit:
        return explicit
    # build-dev es el instrumentado: tiene SNESRECOMP_EXIT_AT_FRAME y la sonda
    # PCM, y es el que usa el protocolo A/B.
    for name in ("build-dev", "build-audit", "build-clean-test"):
        d = os.path.join(ROOT, name, "Release")
        if os.path.exists(os.path.join(d, "StarOcean.exe")):
            return name
    raise SystemExit("no encuentro ningun build con StarOcean.exe")


def run(bdir, deadline, frames, script=None):
    exe = os.path.join(ROOT, bdir, "Release", "StarOcean.exe")
    pcm = os.path.join(tempfile.gettempdir(), "so_audio_health.pcm")
    if os.path.exists(pcm):
        os.remove(pcm)
    env = dict(os.environ)
    env["SNESRECOMP_PCM_DUMP"] = pcm
    env["SNESRECOMP_EXIT_AT_FRAME"] = str(frames)
    if deadline is not None:
        env["SNESRECOMP_FRAME_DEADLINE"] = str(deadline)
    if script:
        # Mismo input que el A/B: el audio tiene que sonar tambien mientras se
        # navega (el fallo de §22.13 se cebaba justo con el driver de sonido).
        env["SNESRECOMP_REPLAY_FILE"] = script
        env["SNESRECOMP_REPLAY_UP_PAUSE_MS"] = "0"
    run_env = env
    proc = subprocess.run([exe], cwd=os.path.join(ROOT, bdir, "Release"),
                          env=run_env, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, timeout=600)
    del proc
    return pcm


def seconds(pcm_path, rate=32040):
    with open(pcm_path, "rb") as fh:
        raw = fh.read()
    n = len(raw) // 4
    if n == 0:
        return []
    samples = struct.unpack("<%dh" % (n * 2), raw[:n * 4])
    out = []
    for s in range(n // rate):
        seg = samples[s * rate * 2:(s + 1) * rate * 2]
        peak = max(abs(x) for x in seg)
        rms = (sum(x * x for x in seg) / len(seg)) ** 0.5
        out.append((peak, rms))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default=None,
                    help="directorio de build (por defecto build-dev)")
    ap.add_argument("--deadline", default=None,
                    help="valor de SNESRECOMP_FRAME_DEADLINE a probar")
    ap.add_argument("--frames", type=int, default=1800)
    ap.add_argument("--expect-audio-from", type=int, default=8,
                    help="segundo a partir del cual DEBE haber senal")
    ap.add_argument("--min-peak", type=int, default=1000,
                    help="pico minimo para considerar que hay musica")
    ap.add_argument("--min-ratio", type=float, default=0.6,
                    help="fraccion minima de segundos con musica tras el inicio")
    ap.add_argument("--script", default=None,
                    help="guion de entrada del motor (SNESRECOMP_REPLAY_FILE)")
    args = ap.parse_args()

    bdir = build_dir(args.build)
    print("[audio_health] build=%s deadline=%s frames=%d"
          % (bdir, args.deadline if args.deadline is not None else "(default)",
             args.frames))
    try:
        pcm = run(bdir, args.deadline, args.frames, args.script)
    except subprocess.TimeoutExpired:
        print("FALLO: el emulador no termino; ?se colgo?")
        return 1

    secs = seconds(pcm)
    if not secs:
        print("FALLO: el volcado PCM esta vacio (no salio audio del motor)")
        return 1

    print("[audio_health] %d segundos de PCM entregado al dispositivo"
          % len(secs))
    problems = []
    total = 0
    with_music = 0
    for s, (peak, rms) in enumerate(secs):
        flag = "SILENCIO" if peak == 0 else ("bajo" if rms < 20 else "audio")
        if s % 5 == 0 or (peak == 0 and s >= args.expect_audio_from):
            print("  %2ds peak=%6d rms=%8.1f %s" % (s, peak, rms, flag))
        if s < args.expect_audio_from:
            continue
        total += 1
        # Silencio ABSOLUTO campa donde campa: el DSP no esta sonando. Este es
        # el sintoma exacto del fallo de #22.13 y no tiene excepcion legitima.
        if peak == 0:
            problems.append("segundo %d en silencio absoluto" % s)
        # Un tramo flojo aislado si es legitimo (la intro baja de nivel antes del
        # logo). Lo que no puede pasar es que la mayoria del tramo este bajo.
        if peak >= args.min_peak:
            with_music += 1

    if problems:
        print("[audio_health] FALLO: %d segundos en silencio absoluto desde "
              "el %d: %s" % (len(problems), args.expect_audio_from,
                              ", ".join(problems[:6])))
        print("[audio_health] (esto es exactamente el fallo de ENCICLOPEDIA #22.13: el motor produce y entrega, pero el DSP no suena)")
        return 1

    ratio = (with_music / total) if total else 0.0
    if ratio < args.min_ratio:
        print("[audio_health] FALLO: solo %d/%d segundos con musica (%.0f%% < "
              "%.0f%%) desde el segundo %d"
              % (with_music, total, 100.0 * ratio, 100.0 * args.min_ratio,
                 args.expect_audio_from))
        return 1

    if args.min_ratio <= 0.0:
        # Escenario con input (menu, seleccion de nombre, cinematica): los
        # tramos callados son legitimos del juego, asi que lo unico que se exige
        # es que NO haya silencio absoluto, que es el sintoma del fallo de
        # ENCICLOPEDIA #22.13.
        print("[audio_health] OK: ningun silencio absoluto en %d segundos "
              "(%d con musica; el resto son tramos callados legitimos)"
              % (total, with_music))
        return 0

    print("[audio_health] OK: %d/%d segundos con musica (%.0f%%) desde el "
          "segundo %d, ningun silencio absoluto"
          % (with_music, total, 100.0 * ratio, args.expect_audio_from))
    return 0


if __name__ == "__main__":
    sys.exit(main())
