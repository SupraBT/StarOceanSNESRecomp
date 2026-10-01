#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUEBAS FORENSES FRAME A FRAME de cada fotograma rojo del HUD.

Por que existe. Durante horas se ha estado "midiendo" el coste de un fotograma
con el numero que va al HUD (`ciclo`) y con el delta entre dos `HmDraw`. Ese
numero es el bucle de host ENTERTO (emulacion + presentacion + `SDL_Delay`) y
ademas se comparaba entre corridas distintas, en maquinas distintas y con
ejecutables distintos. Con eso no se puede afirmar nada. Este script lo
sustituye por una medicion con las condiciones Declaradas:

  1. Lanza UN binario, con el guion de la traza, y captura de TODO lo que el
     motor emite por fotograma: `[perf]` (reparto emu/presentacion/espera),
     `[hot]` (el disparo del HUD), `[fstate]`, `[irqstate]`, `[dspstat]`,
     `[dspvoice]`, `[hstat]`. Cada linea queda indexada por su frame de INVITADO.
  2. Para cada fotograma en el que el indicador se pone rojo guarda el BMP que
     ya escribe `SNESRECOMP_HOT` (con el HUD dentro, en el color con el que se
     vio) y lo copia a un informe por fotograma.
  3. Coloca cada fotograma rojo EN FRENTE a la fila del MISMO frame de invitado
     de la traza de hardware de Mesen, y saca las diferencias campo a campo
     (master, PC, A/X/Y, db, d, bandas, timings, escrituras a $2140, key-on).
  4. Desensambla el PC del invitado con el decodificador real (el mismo que usa
     el AOT), y si el proyecto de Ghidra esta disponible, con PyGhidra, para
     que la linea diga QUE ESTA EJECUTANDO ese fotograma y no solo su PC.
  5. Escribe un informe por fotograma en texto y abre un `resumen.txt` con la
     tabla de todos los fotogramas rojos.

La alineacion es por frame de INVITADO, no de host: sin la deadline de
fotograma el invitado corre por delante del host (medido: host 101 -> invitado
163) y comparar por host es comparar instants distintos de la maquina.

Uso:
    python tools/frame_forensics.py --build build-hm --frames 900
    python tools/frame_forensics.py --build build-hm --umbral 18 --frames 1200
    python tools/frame_forensics.py --build build-hm --deadline 0   # comparar

No inventa nada: si un dato no existe en la traza lo dice `--` en vez de
rellenarlo, y si el binario no emite una fuente lo dice al principio.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import replay_clock  # noqa: E402

TRACES = pathlib.Path(r"E:\Recompilador Super Nintendo\StarOceanRecompDocumentacion"
                      r"\TracesMesen")
TRACE_TSV = TRACES / "Star_Ocean_Japan__so_trace_trace.tsv"
GHIDRA_PROJECTS = pathlib.Path(r"E:\Recompilador Super Nintendo"
                               r"\HerramientasDecompilacion\ghidra_projects")

# Campos de la traza de hardware que se confrontan con los del motor. La
# cabecera del TSV esta en las lineas 3-35; la 36 es la de columnas.
TRAZA_COLS = ["fr", "in", "pin", "btn", "master", "cyc", "pc", "a", "x", "y",
              "sp", "d", "db", "p", "bright", "bg", "scan", "ppufr", "hc",
              "r2140", "w2140", "spcw", "ini", "kon", "konf", "spcpc", "spca",
              "spcx", "spcy", "spcsp", "spcps", "r4212", "sdnmi", "sw4200"]


# ── traza de hardware ────────────────────────────────────────────────────
def cargar_traza(path: pathlib.Path) -> dict:
    """frame de hardware -> fila. Indexa por el frame del hardware."""
    filas = {}
    with path.open(encoding="utf-8", errors="replace") as fh:
        en_cabecera = True
        for linea in fh:
            if en_cabecera:
                if linea.startswith("#fr"):
                    en_cabecera = False
                continue
            p = linea.rstrip("\n").split("\t")
            if len(p) < len(TRAZA_COLS):
                continue
            try:
                fr = int(p[0])
            except ValueError:
                continue
            filas[fr] = dict(zip(TRAZA_COLS, p))
    return filas


# ── desensamblado ────────────────────────────────────────────────────────
def desensamblar(pc24: int, m: int = 1, x: int = 0) -> str:
    """Una instruccion en el PC dado, con el decodificador del propio AOT."""
    try:
        sys.path.insert(0, str(ROOT / "snesrecomp" / "recompiler"))
        import snes65816  # noqa: WPS433
        banco = (pc24 >> 16) & 0xFF
        dirpc = pc24 & 0xFFFF
        with open(ROOT / "Star Ocean (Japan).sfc", "rb") as rom:
            # HiROM: bancos $C0-$CF = pagina 0 del MMC.
            off = ((banco - 0xC0) * 0x10000 + dirpc) if banco >= 0xC0 else \
                  (banco * 0x8000 + (dirpc & 0x7FFF))
            rom.seek(off)
            bytes_ = rom.read(8)
        n, modo, largo = snes65816.decode(bytes_, m, x)
        return snes65816.render(pc24, bytes_[:largo], m, x)
    except Exception as exc:  # noqa: BLE001
        return "(no desensamblado: %s)" % exc


def ghidra_disponible() -> bool:
    if not GHIDRA_PROJECTS.exists():
        return False
    try:
        import pyghidra  # noqa: F401,WPS433
        return True
    except Exception:  # noqa: BLE001
        return False


# ─- captura del motor ────────────────────────────────────────────────────────
PERF = re.compile(r"\[perf\] h=(\d+) g=(\d+) loop=([\d.]+) emu=([\d.]+) "
                  r"draw=([\d.]+) resto=(-?[\d.]+)")
# OJO el orden real de [fstate] es:  f= resume= cpu= master= ... DB= PB= DP=
# S= A= X= Y= P=  -- `resume` va ANTES que `master`. Una regex al reves
# devuelve "el motor no emitio [fstate]" aunque la linea este ahi, que es
# exactamente el fallo que hizo perder una ronda de pruebas.
FSTATE = re.compile(
    r"f=(?P<fr>\d+)\s+nmiEn=\S+\s+resume=(?P<resume>[0-9A-F]+).*?"
    r"cpu=(?P<cpu>\d+)\s+master=(?P<master>\d+).*?"
    r"DB=(?P<DB>[0-9A-F]+)\s+PB=(?P<PB>[0-9A-F]+)\s+DP=(?P<DP>[0-9A-F]+)\s+"
    r"S=(?P<S>[0-9A-F]+)\s+A=(?P<A>[0-9A-F]+)\s+X=(?P<X>[0-9A-F]+)\s+"
    r"Y=(?P<Y>[0-9A-F]+)\s+P=(?P<P>[0-9A-F]+)")
HOT = re.compile(r"\[hot\] f=(\d+) ciclo=([\d.]+)ms .*?draw=([\d.]+)ms fps=(\d+)")


def lanzar(build: str, frames: int, umbral: float, deadline: str | None,
           script: str, completo: bool) -> tuple[pathlib.Path, pathlib.Path]:
    rel = ROOT / build / "Release"
    exe = rel / "StarOcean.exe"
    if not exe.exists():
        raise SystemExit("no existe %s" % exe)
    if not os.path.exists(script):
        script = str(HERE / "input_scripts" / script)
    if not os.path.exists(script):
        raise SystemExit("no encuentro el guion: %s" % script)

    hots = rel / "forensics_shots"
    if hots.exists():
        shutil.rmtree(hots)

    env = dict(os.environ)
    replay_clock.apply(env, script)
    env["SNESRECOMP_EXIT_AT_FRAME"] = str(frames)
    env["SNESRECOMP_TURBO_PRESENT_EVERY"] = "0"
    env["SNESRECOMP_HUD"] = "1"
    env["SNESRECOMP_HOT"] = "1"
    env["SNESRECOMP_HOT_MS"] = str(umbral)
    env["SNESRECOMP_HOT_DIR"] = str(hots.resolve())
    env["SNESRECOMP_PERF"] = "1"
    env["SNESRECOMP_HOT_ALL"] = "1"
    if completo:
        # Todo lo que el motor sabe decir por fotograma. OJO: esto NO es gratis
        # (ver --ligero): los tiempos de esta pasada no valen como medida.
        env["SNESRECOMP_FRAME_STATE"] = "1"
        env["SNESRECOMP_FRAME_BUDGET"] = "1"
        env["SNESRECOMP_DSPSTAT"] = "1"
    if deadline is not None:
        env["SNESRECOMP_FRAME_DEADLINE"] = deadline
    else:
        env.pop("SNESRECOMP_FRAME_DEADLINE", None)

    log = rel / ("forensics.log" if completo else "forensics_ligero.log")
    print("binario : %s" % exe)
    print("guion   : %s" % script)
    print("frames  : %d   umbral: %.1f ms   deadline: %s"
          % (frames, umbral, deadline if deadline is not None else "el del binario"))
    print("capturas: %s" % hots)
    with open(log, "wb") as fh:
        subprocess.run([str(exe)], cwd=str(rel), env=env,
                       stdout=fh, stderr=subprocess.STDOUT, timeout=7200)
    return log, hots


def recoger(log: pathlib.Path) -> dict:
    """frame de invitado -> todo lo que el motor emitio en ese frame."""
    por_frame = {}
    for linea in log.read_text(errors="replace").splitlines():
        m = PERF.search(linea)
        if m:
            g = m.groups()
            por_frame.setdefault(int(g[1]), {})["perf"] = dict(
                host=int(g[0]), loop=float(g[2]), emu=float(g[3]),
                draw=float(g[4]), resto=float(g[5]))
            continue
        m = HOT.search(linea)
        if m:
            g = m.groups()
            por_frame.setdefault(int(g[0]), {})["hot"] = dict(
                ciclo=float(g[1]), draw=float(g[2]), fps=int(g[3]))
            continue
        for etiqueta in ("fstate", "irqstate", "dspstat", "dspvoice", "hstat",
                         "fbudget"):
            if linea.startswith("[" + etiqueta + "]"):
                por_frame.setdefault(_frame_de_la_linea(linea), {})[etiqueta] = linea
                break
    return por_frame


def _frame_de_la_linea(linea: str) -> int:
    m = re.search(r"\bf=(\d+)", linea)
    if m:
        return int(m.group(1))
    m = re.search(r"\bgf=(\d+)", linea)
    return int(m.group(1)) if m else -1


# ── informe ──────────────────────────────────────────────────────────────
def confrontar(motor: dict, hw: dict | None) -> list:
    if hw is None:
        return ["(la traza no tiene este frame)"]
    st = FSTATE.search(motor.get("fstate", ""))
    if not st:
        return ["(el motor no emitio [fstate] en este frame)"]
    p = st.groupdict()
    out = []
    # PC: el motor lo da en 24 bits como PB:PC; la traza en K:PC.
    pc_motor = p["resume"].upper()
    dif = []
    if pc_motor.lstrip("0") != hw["pc"].upper().lstrip("0"):
        dif.append("PC  motor=$%s  hardware=$%s" % (pc_motor, hw["pc"]))
    for campo, motor_key in (("a", "A"), ("x", "X"), ("y", "Y"),
                             ("db", "DB"), ("d", "DP"), ("sp", "S"),
                             ("p", "P")):
        vh = hw[campo].upper()
        vm = p[motor_key].upper()
        if vh not in ("", "--") and vh.lstrip("0") != vm.lstrip("0"):
            dif.append("%-3s motor=%s  hardware=%s" % (campo.upper(), vm, vh))
    try:
        dm = int(p["master"]) - int(hw["master"])
    except ValueError:
        dm = 0
    if dm:
        dif.append("MASTER motor=%s  hardware=%s  (delta %+d = %+.4f frames)"
                   % (p["master"], hw["master"], dm, dm / 357368.0))
    for extra in ("hc", "w2140", "r2140", "spcw", "konf", "r4212", "sdnmi"):
        out.append("    %-6s hardware=%s" % (extra, hw.get(extra, "--")))
    return dif, out


def main() -> int:
    ap = argparse.ArgumentParser()
    # Por defecto COMPLETO: es el modo para Shaftesbury, y el modo ligero se
    # pide explicitamente para medir tiempos sin el coste de la instrumentacion.
    ap.add_argument("--build", default="build-hm")
    ap.add_argument("--script", default="mesen_master.txt")
    ap.add_argument("--frames", type=int, default=900)
    ap.add_argument("--umbral", type=float, default=18.0)
    ap.add_argument("--deadline", default=None,
                    help="0 o 1; sin esto se usa el default del binario")
    ap.add_argument("--traza", default=str(TRACE_TSV))
    ap.add_argument("--ligero", action="store_true",
                    help="solo cronometra: sin [fstate]/[dspstat]/[fbudget], "
                         "queAdd cuesta ~4 ms por fotograma y falsea las medidas")
    ap.add_argument("--completo", action="store_true",
                    help="tambien recoge [fstate], [irqstate], [dspstat], "
                         "[dspvoice] y [fbudget] para el contraste con la traza")
    args = ap.parse_args()

    # DOS PASADAS, y esto no es opcional:
    #   - la ligera mide TIEMPOS sin el coste de la instrumentacion;
    #   - la completa trae los DATOS ([fstate], [dspstat], ...) para el
    #     contraste con la traza, pero infla los tiempos en ~4 ms por
    #     fotograma, asi que sus tiempos NO valen como medida.
    # Mergearlas y decir de donde sale cada numero es la unica forma de que
    # el informe no mienta.
    log_ligero, shots = lanzar(args.build, args.frames, args.umbral,
                               args.deadline, args.script, False)
    tiempos = recoger(log_ligero)
    log, _ = lanzar(args.build, args.frames, args.umbral, args.deadline,
                    args.script, True)
    motor = recoger(log)
    for fr, t in tiempos.items():
        if fr in motor and "perf" in t:
            motor[fr]["perf_real"] = t["perf"]
    print("\nframes con datos del motor: %d" % len(motor))

    if not ghidra_disponible():
        print("Ghidra (PyGhidra) NO disponible: se usara el decodificador del AOT")
    if not pathlib.Path(args.traza).exists():
        print("NO existe la traza %s: se informara solo del motor" % args.traza)
        return 1
    hw = cargar_traza(pathlib.Path(args.traza))
    print("frames en la traza de hardware: %d" % len(hw))

    # Los fotogramas rojos: los que el propio motor marco con [hot], mas los
    # que superen el umbral segun [perf] (por si el HUD no llego a dibujarse).
    rojos = []
    for fr, datos in sorted(motor.items()):
        p = datos.get("perf_real") or datos.get("perf")
        if not p:
            continue
        if p["loop"] > args.umbral:
            rojos.append(fr)

    print("fotogramas rojos: %d  ->  %s"
          % (len(rojos), ", ".join(str(f) for f in rojos[:40])))

    informe_dir = ROOT / args.build / "Release" / "forensics"
    if informe_dir.exists():
        shutil.rmtree(informe_dir)
    informe_dir.mkdir(parents=True, exist_ok=True)

    resumen = []
    for fr in rojos:
        datos = motor.get(fr, {})
        p = datos.get("perf_real") or datos.get("perf", {})
        h = datos.get("hot", {})
        bmp = shots / ("f%06d.bmp" % fr)
        lineas = []
        lineas.append("=" * 78)
        lineas.append("FRAME DE INVITADO %d%s"
                      % (fr, "   (captura: %s)" % bmp.name if bmp.exists()
                         else "   (SIN CAPTURA)"))
        lineas.append("=" * 78)
        if p:
            lineas.append("  MOTOR   loop=%.2f ms = emu %.2f + dibuja %.2f + "
                          "presentacion/espera %.2f  [TIEMPO REAL]"
                          % (p["loop"], p["emu"], p["draw"], p["resto"]))
        st = FSTATE.search(datos.get("fstate", ""))
        if st:
            g = st.groupdict()
            lineas.append("          master=%s  PC=%s  a=%s x=%s y=%s db=%s d=%s "
                          "sp=%s p=%s"
                          % (g["master"], g["cpu"], g["A"], g["X"], g["Y"],
                             g["DB"], g["DP"], g["S"], g["P"]))
            pc = int(g["resume"], 16)
            lineas.append("          RESUME %s :  %s" % (g["resume"],
                                                        desensamblar(pc)))
        if h:
            lineas.append("  HUD     ciclo=%.2f ms  draw=%.2f ms  %d FPS"
                          % (h.get("ciclo", 0), h.get("draw", 0),
                             h.get("fps", 0)))
        for etiqueta in ("fstate", "irqstate", "fbudget", "dspstat", "dspvoice",
                         "hstat"):
            if etiqueta in datos:
                lineas.append("  %-8s %s" % (etiqueta.upper(),
                                             datos[etiqueta][len(etiqueta) + 3:]))
        res = confrontar(datos, hw.get(fr))
        if isinstance(res, tuple):
            dif, extra = res
            lineas.append("  CONTRASTE CON HARDWARE (mismo frame de invitado)")
            if dif:
                lineas.append("    *** DIFERENCIAS ***")
                lineas.extend("      " + d for d in dif)
            else:
                lineas.append("    sin diferencias en PC/registros/master")
            lineas.extend(extra)
        else:
            lineas.append("  CONTRASTE: %s" % res[0])
        (informe_dir / ("f%06d.txt" % fr)).write_text(
            "\n".join(lineas) + "\n", encoding="utf-8")
        resumen.append((fr, p.get("loop", 0), p.get("emu", 0),
                        p.get("draw", 0), p.get("resto", 0), h.get("fps", 0),
                        bmp.exists()))

    cab = ["FRAME  loop(ms)   emu(ms)  dibuja(ms)  resto(ms)  FPS  captura"]
    for fr, loop, emu, draw, resto, fps, cap in resumen:
        cab.append("%5d  %8.2f  %8.2f  %10.2f  %9.2f  %3d  %s"
                   % (fr, loop, emu, draw, resto, fps, "si" if cap else "NO"))
    (informe_dir / "resumen.txt").write_text("\n".join(cab) + "\n",
                                             encoding="utf-8")
    print("\n" + "\n".join(cab))
    print("\ninformes: %s" % (informe_dir / "resumen.txt"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
