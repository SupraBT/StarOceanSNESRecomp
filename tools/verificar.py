#!/usr/bin/env python3
"""Las tres pruebas del protocolo, en un comando.

PROTOCOLO.md exige, antes de dar por bueno cualquier cambio:

  1. Salud de audio: el juego SUENA (PCM real entregado al dispositivo).
  2. Rendimiento: la intro sostiene ~60 fps.
  3. A/B byte-exacto: `[fstate]` identico al baseline guardado.
  4. Determinismo: dos corridas identicas dan el mismo `[fstate]`.
  5. Turbo: acelerar el host (`SNESRECOMP_FORCE_TURBO=1`) no mueve al invitado.

Un cambio que *no* debe alterar el comportamiento tiene que pasar las tres. Un
cambio que SI lo altera a proposito (el modelo de frame, por ejemplo) exige
regenerar el baseline de forma deliberada con `--update-golden` y documentarlo.

Uso:
    python tools/verificar.py                    # las tres
    python tools/verificar.py --update-golden    # nuevo baseline (acto deliberado)
    python tools/verificar.py --deadline=1       # comprobar la otra configuracion
    python tools/verificar.py --only audio
"""
import argparse
import os
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REL = None

sys.path.insert(0, HERE)
import replay_clock  # noqa: E402  (reloj del guion: ver tools/replay_clock.py)


def safe(text):
    """Consola Windows en cp1252: los mensajes no pueden llevar no-ASCII."""
    return str(text).encode("ascii", "replace").decode("ascii")


def build_release(build):
    return os.path.join(ROOT, build, "Release")


def exe(build):
    return os.path.join(build_release(build), "StarOcean.exe")


SCRIPTS_DIR = os.path.join(HERE, "input_scripts")


def resolve_script(name):
    if not name:
        return None
    if os.path.exists(name):
        return os.path.abspath(name)
    cand = os.path.join(SCRIPTS_DIR, name)
    if os.path.exists(cand):
        return cand
    cand = os.path.join(SCRIPTS_DIR, name + ".txt")
    if os.path.exists(cand):
        return cand
    raise SystemExit("no encuentro el guion de entrada: %s" % name)


def env_for(deadline, script=None):
    e = dict(os.environ)
    if deadline is not None:
        e["SNESRECOMP_FRAME_DEADLINE"] = str(deadline)
    if script:
        # El guion declara su reloj en la cabecera (`# clock: master`). Una
        # grabacion de hardware NO se puede keyear al indice de frame: nuestro
        # invitado no va al mismo tiempo que el hardware en el mismo frame, y
        # las pulsaciones cortas se pierden (ver tools/replay_clock.py).
        replay_clock.apply(e, script)
    return e


def run_capture(build, args, timeout=600):
    """Ejecuta el emulador con EXIT_AT_FRAME y devuelve stderr."""
    p = subprocess.run([exe(build)], cwd=build_release(build), env=args,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                       timeout=timeout)
    return (p.stderr or b"").decode("utf-8", "replace")


# --------------------------------------------------------------------------
# 1. Audio
# --------------------------------------------------------------------------
def check_audio(build, deadline, frames, threshold=0.6, from_s=8, script=None):
    cmd = [sys.executable, os.path.join(HERE, "audio_health.py"),
           "--build", build, "--frames", str(frames),
           "--min-ratio", str(threshold)]
    if deadline is not None:
        cmd.append("--deadline=%s" % deadline)
    if script:
        cmd.append("--script=%s" % script)
    p = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=900)
    out = (p.stdout or b"").decode("utf-8", "replace")
    line = [l for l in out.splitlines() if l.startswith("[audio_health]")]
    return p.returncode == 0, (line[-1] if line else "sin salida")


# --------------------------------------------------------------------------
# 2. Rendimiento
# --------------------------------------------------------------------------
def check_fps(build, deadline, frames):
    e = env_for(deadline)
    e["SNESRECOMP_EXIT_AT_FRAME"] = str(frames)
    e["SNESRECOMP_PHASE_MS"] = "1"
    e["SNESRECOMP_PHASE_INTERVAL"] = "200"
    err = run_capture(build, e)
    fps = []
    for line in err.splitlines():
        if not line.startswith("[phase]"):
            continue
        if "FPS" not in line:
            continue
        try:
            fps.append(float(line.split("->")[1].split("FPS")[0].strip()))
        except (IndexError, ValueError):
            pass
    if not fps:
        return False, "no hay ninguna ventana [phase] (¿falta el instrumentado?)"
    # La primera ventana incluye el arranque (SDL + carga de ROM); se juzga el
    # regimen, que es lo que el usuario percibe.
    steady = fps[len(fps) // 4:] or fps
    med = statistics.median(steady)
    worst = min(steady)
    ok = med >= 58.0
    return ok, ("mediana %.1f fps en regimen (%.0f-%.0f), minima %.1f"
                % (med, min(steady), max(steady), worst))


# --------------------------------------------------------------------------
# 3. A/B byte-exacto del [fstate]
# --------------------------------------------------------------------------
def fstate_lines(build, deadline, frames, script=None, extra=None):
    e = env_for(deadline, script)
    e["SNESRECOMP_EXIT_AT_FRAME"] = str(frames)
    e["SNESRECOMP_FRAME_STATE"] = "1"
    if extra:
        e.update(extra)
    err = run_capture(build, e)
    return [l for l in err.splitlines() if l.startswith("[fstate]")]


def golden_path(build, script=None):
    name = "golden_fstate%s.log" % (
        "_" + os.path.splitext(os.path.basename(script))[0] if script else "")
    return os.path.join(build_release(build), "logs", name)


def check_ab(build, deadline, frames, update, script=None):
    lines = fstate_lines(build, deadline, frames, script)
    gp = golden_path(build, script)
    if update:
        os.makedirs(os.path.dirname(gp), exist_ok=True)
        with open(gp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        return True, "baseline REGENERADO: %d frames -> %s" % (len(lines), gp)
    if not os.path.exists(gp):
        return False, ("no hay baseline en %s; crealo con --update-golden "
                       "(acto deliberado)" % gp)
    with open(gp, encoding="utf-8") as fh:
        gold = fh.read().splitlines()
    # Se compara el PREFIJO comun: pedir 1200 frames contra un baseline de 2100
    # es un A/B legitimo de esos 1200. La diferencia de longitud se informa para
    # que no pase desapercibido que el baseline cubre mas tramo.
    n = min(len(lines), len(gold))
    if n == 0:
        return False, "no hay frames que comparar"
    bad = [i for i in range(n) if lines[i] != gold[i]]
    nota = ("" if len(lines) == len(gold)
            else " (comparados %d de %d frames del baseline)" % (n, len(gold)))
    if bad:
        i = bad[0]
        return False, ("%d/%d frames difieren%s; primero en el frame %d:\n"
                       "      ahora:    %s\n      baseline: %s"
                       % (len(bad), n, nota, i + 1, lines[i][:140],
                          gold[i][:140]))
    return True, "%d/%d frames byte-identicos al baseline%s" % (n, n, nota)


# --------------------------------------------------------------------------
# 4. Determinismo
# --------------------------------------------------------------------------
def check_determinism(build, deadline, frames, update):
    """Misma configuracion dos veces: el [fstate] tiene que ser identico.

    Es la base de todo lo demas: si el emulador no fuese determinista, ningun
    A/B byte-exacto significaria nada (dos corridas distintas darian diferencias
    que no vienen del cambio que se esta midiendo).
    """
    a = fstate_lines(build, deadline, frames)
    b = fstate_lines(build, deadline, frames)
    if len(a) != len(b):
        return False, ("dos corridas identicas dan %d y %d frames"
                       % (len(a), len(b)))
    bad = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    if bad:
        i = bad[0]
        return False, ("NO determinista: %d/%d frames difieren entre dos corridas "
                       "identicas; primero en el frame %d:\n"
                       "      corrida A: %s\n      corrida B: %s"
                       % (len(bad), len(a), i + 1, a[i][:140], b[i][:140]))
    return True, "dos corridas identicas: %d/%d frames identicos" % (len(a), len(a))


# --------------------------------------------------------------------------
# 5. Turbo es del host, no del invitado
# --------------------------------------------------------------------------
def check_turbo_neutral(build, deadline, frames, script=None):
    """Turbo solo cambia el ritmo del host: el [fstate] no puede moverse.

    Es la propiedad que hace utilizable el turbo para analisis (avanzar rapido el
    tramo ya revisado de un trace): si alterase al invitado, todo lo medido a
    velocidad dejaria de valer. Se compara contra la MISMA corrida con
    SNESRECOMP_FORCE_TURBO=1, no contra el baseline (asi sigue valiendo aunque el
    baseline se regenere).
    """
    normal = fstate_lines(build, deadline, frames, script)
    turbo = fstate_lines(build, deadline, frames, script,
                         extra={"SNESRECOMP_FORCE_TURBO": "1"})
    n = min(len(normal), len(turbo))
    if n == 0:
        return False, "no hay frames que comparar"
    bad = [i for i in range(n) if normal[i] != turbo[i]]
    if bad:
        i = bad[0]
        return False, ("turbo MUEVE al invitado: %d/%d frames difieren; primero en "
                       "el frame %d:\n      normal: %s\n      turbo:  %s"
                       % (len(bad), n, i + 1, normal[i][:140], turbo[i][:140]))
    return True, "turbo no altera al invitado: %d/%d frames identicos" % (n, n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="build-dev")
    ap.add_argument("--frames", type=int, default=2100)
    ap.add_argument("--fps-frames", type=int, default=1200)
    ap.add_argument("--deadline", default=None)
    ap.add_argument("--update-golden", action="store_true")
    ap.add_argument("--det-frames", type=int, default=900,
                    help="frames para la prueba de determinismo")
    ap.add_argument("--script", default=None,
                    help="guion de entrada del motor (tools/input_scripts/<nombre>); "
                         "su baseline es golden_fstate_<nombre>.log")
    ap.add_argument("--only", default=None,
                    help="pruebas separadas por comas: audio,fps,ab,det,turbo "
                         "(por defecto, todas)")
    ap.add_argument("--turbo-frames", type=int, default=1200,
                    help="frames para la prueba de neutralidad del turbo")
    args = ap.parse_args()
    only = None
    if args.only:
        only = {s.strip() for s in args.only.split(",") if s.strip()}
        invalid = only - {"audio", "fps", "ab", "det", "turbo"}
        if invalid:
            print("pruebas desconocidas: %s" % ", ".join(sorted(invalid)))
            return 2

    if not os.path.exists(exe(args.build)):
        print("no encuentro %s" % exe(args.build))
        return 2

    args.script = resolve_script(args.script)
    print("== verificar: build=%s deadline=%s frames=%d guion=%s =="
          % (args.build, args.deadline if args.deadline is not None else "(default)",
             args.frames,
             os.path.basename(args.script) if args.script else "(sin input)"))
    results = []
    if only is None or "audio" in only:
        # Con guion real (menu/name/cinematica) los tramos callados son
        # legitimos del juego: se exige "ningun silencio absoluto", no "mayoria
        # con musica". Sin guion (intro en attract) si se exige la mayoria.
        th = 0.0 if args.script else 0.6
        ok, msg = check_audio(args.build, args.deadline, args.frames,
                              threshold=th, script=args.script)
        if args.script:
            msg = msg + " [con guion %s]" % os.path.basename(args.script)
        results.append(("audio", ok, msg))
    if only is None or "fps" in only:
        ok, msg = check_fps(args.build, args.deadline, args.fps_frames)
        results.append(("fps", ok, msg))
    if only is None or "ab" in only:
        ok, msg = check_ab(args.build, args.deadline, args.frames,
                           args.update_golden, args.script)
        if args.script:
            msg = msg + " [guion %s]" % os.path.basename(args.script)
        results.append(("A/B byte-exacto", ok, msg))
    if (only is None or "det" in only) and not args.update_golden:
        ok, msg = check_determinism(args.build, args.deadline, args.det_frames,
                                    args.update_golden)
        results.append(("determinismo", ok, msg))
    if (only is None or "turbo" in only) and not args.update_golden:
        ok, msg = check_turbo_neutral(args.build, args.deadline, args.turbo_frames,
                                      args.script)
        results.append(("turbo", ok, msg))

    print()
    failed = 0
    for name, ok, msg in results:
        print(safe("  [%s] %-16s %s" % ("PASA " if ok else "FALLA", name, msg)))
        if not ok:
            failed += 1
    print()
    if failed:
        print("RESULTADO: %d prueba(s) fallan. No aplicar sin resolverlo "
              "(PROTOCOLO.md)." % failed)
        return 1
    print("RESULTADO: todo pasa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
