#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Lee la traza de la sonda v3 (mesen_fades900.tsv, 15 columnas) y la compara
con el recomp alineando por RELOJ MASTER.

El indice de frame NO es comparable entre los dos lados: el recomp quema ~66
frames de invitado antes de su primer limite de frame real, asi que f_recomp
!= fr_hardware.  `master` (357368 por frame de invitado en ambos) si lo es.

Columnas (1-based) del TSV: 1 fr, 2 master, 3 pc, 4 D, 5 DB, 6 E4, 7 E5, 8 DA,
9 AFB, 10 AFD, 11 ini, 12 x, 13 rdcnt, 14 wshadow, 15 src.

AVISO DE FIABILIDAD (leccion de la corrida del 29-sep):
  * Las columnas MUESTREADAS por frame (pc, D, DB, E4, E5, DA, AFB, AFD) son
    fiables: salen de `emu.read` una vez por frame.
  * `ini` (col 11) NO es el valor escrito a $2100: la via `mMT` (memType como
    3er argumento) dispara sobre un RANGO de memoria y volcado entero, y tapa
    el byte del registro.  La via byte-a-byte (m1/m6) solo registro 161
    eventos.  Para juzgar $2100 en hardware hay que arreglar la sonda.
  * `x` (col 12) y `wshadow` (col 13) cuentan ejecuciones/escrituras de
    callbacks registrados VARIAS veces (form 1 y form 3 y memType), asi que
    multiplican.  No usarlos como recuento absoluto.

Uso:
  python tools/fades900.py                        # autodiagnostico + tramos
  python tools/fades900.py --ab                   # tabla A/B por reloj master
  python tools/fades900.py --todos                # todo
"""
import os, re, sys

MASTER_PER_FRAME = 357368

PROBE = os.environ.get(
    "SNESRECOMP_PROBE",
    r"E:\Recompilador Super Nintendo\StarOceanRecompDocumentacion\mesen_fades900.tsv")
FSTATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                      "build-dev", "Release", "logs", "fstate_noinput_err.log")


def gf(master):
    return master / float(MASTER_PER_FRAME)


# ---------------------------------------------------------------- lectores

def load_hw(path):
    rows = []
    for ln in open(path, errors="replace"):
        ln = ln.rstrip("\r\n")
        if not ln or ln.startswith("#"):
            continue
        c = ln.split("\t")
        while len(c) < 15:
            c.append("")
        try:
            fr = int(c[0]); master = int(c[1])
        except ValueError:
            continue
        rows.append(dict(fr=fr, m=master, pc=c[2], DB=c[4], E4=c[5], E5=c[6],
                         DA=c[7], AFB=c[8], AFD=c[9], ini=c[10], x=c[11],
                         rdcnt=c[12], wsh=c[13], src=c[14]))
    # fr1 trae `master` sin inicializar (basura): el reloj arranca en fr2
    if len(rows) > 1 and rows[0]["m"] > 4 * MASTER_PER_FRAME:
        rows[0]["m"] = rows[1]["m"]
    return rows


def load_rc(path):
    rows = []
    if not os.path.exists(path):
        return rows
    for ln in open(path, errors="replace"):
        if "[fstate]" not in ln:
            continue
        d = dict(re.findall(r"(\w+)=(\S+)", ln.split("[fstate]")[1]))
        rows.append(dict(f=int(d["f"]), m=int(d["master"]), res=d["resume"],
                         ini=d["inidisp"], E4=d["E4"], DA=d["DA"],
                         AFB=d["AFB"], AFD=d["AFD"]))
    return rows


# ------------------------------------------------------------- utilitarios

def tramos(rows, kf, km, kda, extra):
    """Tramos consecutivos con el mismo $00DA."""
    out = []
    run = None
    for r in rows:
        if run and run["da"] == r[kda]:
            run["f1"] = r[kf]; run["m1"] = r[km]; run["x1"] = r[extra]
        else:
            if run:
                out.append(run)
            run = dict(da=r[kda], f0=r[kf], f1=r[kf], m0=r[km], m1=r[km],
                       x0=r[extra], x1=r[extra])
    if run:
        out.append(run)
    return out


# -------------------------------------------------------------- informes

def src_stats(rows):
    print("=== autodiagnostico de la sonda (fr1..%d) ===" % rows[-1]["fr"])
    con_da = sum(1 for r in rows if r["DA"] != "00")
    print("  filas=%d  filas con $00DA != 00: %d" % (len(rows), con_da))
    fuentes = {"m1": 0, "m6": 0, "mMT": 0}
    can = {}
    for r in rows:
        for k, v in re.findall(r"(m1|m6|mMT|can\d)=(\d+)", r["src"]):
            if k in fuentes:
                fuentes[k] = int(v)
            else:
                can[k] = int(v)
    print("  ultimas cuentas de $2100 por memoria -> m1=%d m6=%d mMT=%d"
          % (fuentes["m1"], fuentes["m6"], fuentes["mMT"]))
    print("  canario de pila -> %s"
          % (", ".join("%s=%d" % (k, v) for k, v in sorted(can.items())) or "-"))
    if fuentes["mMT"] > 20 * max(1, fuentes["m1"]):
        print("  OJO: mMT (memType como 3er arg) dispara sobre un RANGO y volcado")
        print("       entero (mMT=%d vs m1=%d).  La columna `ini` es ese volcado,"
              % (fuentes["mMT"], fuentes["m1"]))
        print("       NO el valor escrito a $2100.  No usar `ini` como verdad.")
    wsh = [(r["fr"], r["wsh"]) for r in rows if r["wsh"]]
    print("  notas de sombra (col 14 wshadow): %d  %s"
          % (len(wsh), wsh[:6] or "-"))
    xs = {}
    for r in rows:
        for k, v in re.findall(r"([0-9A-F]{6})=(\d+)", r["x"]):
            xs[k] = max(xs.get(k, 0), int(v))
    print("  sitios exec vistos en la col 12 (`x`): %s"
          % (", ".join("%s" % k for k in sorted(xs)) or "-"))
    print()


def informe_tramos(rows, kf, km, kda, extra, etiqueta, afd=None, ini=None):
    print("=== tramos de $00DA -- %s ===" % etiqueta)
    print("  %-11s %-17s %-6s %-4s %-11s" %
          ("frame", "gf(master)", "dur", "DA", "AFB (ini..fin)"))
    prev_fin_gf = None
    for r in tramos(rows, kf, km, kda, extra):
        n = r["f1"] - r["f0"] + 1
        g0, g1 = gf(r["m0"]), gf(r["m1"])
        hueco = ""
        if prev_fin_gf is not None and g0 - prev_fin_gf > 1.5:
            hueco = "   <-- hueco de %.0f gf sin muestrear" % (g0 - prev_fin_gf)
        prev_fin_gf = g1
        print("  %-11s %7.1f..%-7.1f %-6d %-4s %s..%s"
              % ("%s..%s" % (r["f0"], r["f1"]), g0, g1, n, r["da"],
                 r["x0"], r["x1"]))
    print()


def ab(rows_hw, rows_rc, paso=1):
    """Tabla lado a lado alineada por reloj master.

    Solo imprime las filas donde $00DA CAMBIA en alguno de los dos lados: la
    tabla completa son cientos de lineas redundantes.
    """
    print("=== A/B por reloj master (solo cambios de $00DA, paso %d gf) ===" % paso)
    print("  %-9s | %-28s | %-38s" %
          ("gf(master)", "HARDWARE fr: DA/AFB/E4/AFD",
           "RECOMP f: DA/AFB/E4/AFD [inidisp]"))
    print("  " + "-" * 86)
    hi = ri = 0
    m = 0
    prev = None
    lim = min(rows_hw[-1]["m"], rows_rc[-1]["m"])
    while m <= lim:
        while hi + 1 < len(rows_hw) and rows_hw[hi + 1]["m"] <= m:
            hi += 1
        while ri + 1 < len(rows_rc) and rows_rc[ri + 1]["m"] <= m:
            ri += 1
        h, r = rows_hw[hi], rows_rc[ri]
        par = (h["DA"], r["DA"])
        if par != prev:
            marca = "" if h["DA"] == r["DA"] else "  <-- DIVERGE"
            print("  %-9.1f | fr%-5d %-2s/%s/%-4s/%-4s | f%-5d %-2s/%s/%-4s/%-4s [%s]%s"
                  % (gf(m), h["fr"], h["DA"], h["AFB"], h["E4"], h["AFD"],
                     r["f"], r["DA"], r["AFB"], r["E4"], r["AFD"], r["ini"], marca))
            prev = par
        m += paso * MASTER_PER_FRAME
    print()


def primera_divergencia(rows_hw, rows_rc):
    """Primer gf con $00DA distinto entre los dos lados."""
    print("=== primera divergencia de $00DA ===")
    hi = ri = 0
    m = 0
    lim = min(rows_hw[-1]["m"], rows_rc[-1]["m"])
    while m <= lim:
        while hi + 1 < len(rows_hw) and rows_hw[hi + 1]["m"] <= m:
            hi += 1
        while ri + 1 < len(rows_rc) and rows_rc[ri + 1]["m"] <= m:
            ri += 1
        h, r = rows_hw[hi], rows_rc[ri]
        if h["DA"] != r["DA"]:
            print("  gf %.1f  (master %d)" % (gf(m), m))
            print("    hardware fr%-5d pc=%s DA=%s AFB=%s E4=%s AFD=%s"
                  % (h["fr"], h["pc"], h["DA"], h["AFB"], h["E4"], h["AFD"]))
            print("    recomp   f%-5d      DA=%s AFB=%s E4=%s AFD=%s inidisp=%s resume=%s"
                  % (r["f"], r["DA"], r["AFB"], r["E4"], r["AFD"], r["ini"], r["res"]))
            return
        m += MASTER_PER_FRAME
    print("  ninguna en el rango comun")
    print()


if __name__ == "__main__":
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else PROBE
    if not os.path.exists(path):
        print("no existe la traza: %s" % path)
        sys.exit(1)
    hw = load_hw(path)
    print("traza hardware: %s" % path)
    print("filas=%d  fr %d..%d  gf %.1f..%.1f"
          % (len(hw), hw[0]["fr"], hw[-1]["fr"], gf(hw[0]["m"]), gf(hw[-1]["m"])))
    print()
    src_stats(hw)
    informe_tramos(hw, "fr", "m", "DA", "AFB", "HARDWARE (sin input, fr1..%d)" % hw[-1]["fr"])

    rc = load_rc(FSTATE)
    if rc:
        print("traza recomp: %s (%d frames, gf %.1f..%.1f)"
              % (os.path.relpath(FSTATE), len(rc), gf(rc[0]["m"]), gf(rc[-1]["m"])))
        print()
        informe_tramos(rc, "f", "m", "DA", "AFB", "RECOMP (sin input)")
    if rc and ("--ab" in flags or "--todos" in flags):
        print("NOTA: el recomp no tiene muestra valida antes de gf %.1f (quema ~66"
              " frames de invitado antes de su primer limite de frame)."
              % gf(rc[0]["m"] if rc[0]["f"] > 1 else rc[3]["m"]))
        print()
        ab(hw, rc)
        primera_divergencia(hw, rc)
