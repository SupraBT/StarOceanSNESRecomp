#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A/B EVENTO-A-EVENTO de las escrituras a $2100: hardware (sonda v4) vs recomp.

Es el comparador que resuelve la pregunta "quien funde y a que ritmo" sin
depender de la sombra $00DA (que en hardware se queda estancada en $80 durante
toda la carga) ni del indice de frame (que no es comparable entre los dos lados).

Lado hardware : mesen_fades900b.tsv (sonda v4).  La columna 11 (`ini`) lleva el
                valor escrito LEIDO DEL ACUMULADOR en el sitio de ROM, y la
                columna 15 lleva `pc=<sitio>`.  Es la unica fuente fiable de
                "que se escribio": la via mMT de la v3 era un volcado de rango.
Lado recomp   : build-dev/Release/logs/inidisp_trace.log  (SNESRECOMP_INIDISP_TRACE=1)
                lineas `[inidisp] f=<frame> pc=<sitio> val=<byte>` (f = frame-1
                respecto a la linea [fstate], porque se registra ANTES de la
                escritura).

Ademas, si se le pasa un SNESRECOMP_PC_LOG, calcula la tasa gf/host por ventana:
es la medida que localiza donde el recomp consume mas de un frame de invitado
por frame de host (el sobrerrecorrido).

Uso:
  python tools/fades_ab2100.py [traza_v4.tsv] [--pclog logs/pc.log]
"""
import collections, os, re, sys

FSTATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                      "build-dev", "Release", "logs")
DEFAULT_HW = r"E:\Recompilador Super Nintendo\StarOceanRecompDocumentacion\mesen_fades900b.tsv"
DEFAULT_RC = os.path.join(FSTATE, "inidisp_trace.log")


def load_hw(path):
    """Eventos (frame, valor, sitio) de la traza v4."""
    ev = []
    for ln in open(path, errors="replace"):
        ln = ln.rstrip("\r\n")
        if not ln or ln.startswith("#"):
            continue
        c = ln.split("\t")
        if len(c) < 15:
            continue
        m = re.search(r"pc=([0-9A-F]{6})", c[14])
        site = m.group(1) if m else "?"
        for v in [x for x in c[10].split("+") if x]:
            ev.append((int(c[0]), int(v, 16), site))
    return ev


def load_recomp(path):
    ev = []
    for ln in open(path, errors="replace"):
        m = re.match(r"\[inidisp\] f=(\d+) pc=([0-9A-F]+) val=([0-9A-F]+)", ln.strip())
        if m:
            ev.append((int(m.group(1)), int(m.group(3), 16), m.group(2)))
    return ev


def segmentos(ev):
    """Agrupa escrituras consecutivas del mismo sitio con paso monotono
    constante en una 'rampa' (fade-in / fade-out) o en un 'mantenimiento'
    (mismo valor repetido)."""
    segs = []
    cur = None
    for f, v, site in ev:
        if cur and cur["site"] == site:
            d = v - cur["v1"]
            if cur["paso"] is None and abs(d) <= 1:
                cur["paso"] = d
            if d == (cur["paso"] or 0):
                cur["f1"] = f; cur["v1"] = v; cur["n"] += 1
                continue
        if cur:
            segs.append(cur)
        cur = dict(site=site, f0=f, f1=f, v0=v, v1=v, paso=None, n=1)
    if cur:
        segs.append(cur)
    return segs


def imprime_segs(segs, titulo):
    print("=== %s (%d segmentos) ===" % (titulo, len(segs)))
    print("  %-13s %-4s %-8s %-9s %s" % ("frames", "n", "valores", "paso", "sitio"))
    for s in segs:
        print("  %5d..%-5d %-4d %02X..%02X  %-9s %s"
              % (s["f0"], s["f1"], s["n"], s["v0"], s["v1"],
                 s["paso"] if s["paso"] is not None else "?",
                 s["site"] if s["site"] != "?" else "(memoria)"))
    print()


def compara(sh, sr):
    """Empareja segmentos por orden (ignorando los de un solo evento)."""
    print("=== comparacion por orden de segmentos ===")
    print("  #   %-38s | %-38s | dur hw/rc" % ("HARDWARE", "RECOMP"))
    i = j = 0
    k = 0
    while i < len(sh) or j < len(sr):
        a = sh[i] if i < len(sh) else None
        b = sr[j] if j < len(sr) else None
        if a and a["n"] < 2 and a["site"] == "?":       # escrituras sueltas de arranque
            i += 1; continue
        if b and b["n"] < 2 and b["site"].startswith("00"):
            j += 1; continue
        def txt(x):
            if not x:
                return "-"
            return "%s %02X..%02X n=%d" % (x["site"], x["v0"], x["v1"], x["n"])
        dur = ""
        if a and b:
            dur = "%d/%d" % (a["n"], b["n"])
        print("  %-3d %-38s | %-38s | %s" % (k, txt(a), txt(b), dur))
        i += 1; j += 1; k += 1
    print()
    print("  Lectura: si las dos columnas tienen el mismo sitio y el mismo n,")
    print("  los dos lados funden igual.  La diferencia esta en los HUECOS entre")
    print("  segmentos (frames de espera), no dentro de ellos.")


def huecos(segs, etiqueta):
    print("=== huecos entre segmentos -- %s ===" % etiqueta)
    prev = None
    for s in segs:
        if s["n"] < 2:
            continue
        if prev is not None:
            print("  %s -> %s : %d frames" % (prev["site"], s["site"], s["f0"] - prev["f1"]))
        prev = s
    print()


def tasa_gh(pclog):
    rows = []
    for ln in open(pclog, errors="replace"):
        m = re.match(r"gf=(\d+) hostf=(\d+) pc=([0-9A-F]+) resume=([0-9A-F]+)", ln.strip())
        if m:
            rows.append((int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)))
    if not rows:
        print("pclog vacio: %s" % pclog); return
    print("=== tasa gf/hostf (%s) ===" % os.path.basename(pclog))
    print("  gf %d..%d   hostf %d..%d   TOTAL %.4f gf/host"
          % (rows[0][0], rows[-1][0], rows[0][1], rows[-1][1],
             rows[-1][0] / float(rows[-1][1])))
    per = collections.OrderedDict()
    for gf, hf, pc, res in rows:
        per.setdefault(hf, gf)
    hs = sorted(per)
    print("  frames de host donde entra MAS de un frame de invitado:")
    prev = None
    for h in hs:
        if prev is not None and per[h] - prev > 1:
            print("     hostf %5d -> gf %5d (avanza %d gf)" % (h, per[h], per[h] - prev))
        prev = per[h]
    print("  ventanas de 50 frames de host:")
    for h0 in range(hs[0], hs[-1] + 1, 50):
        a = [per[h] for h in hs if h0 <= h < h0 + 50]
        if len(a) > 1:
            print("     hostf %4d..%-4d : %.3f gf/host" % (h0, h0 + 49, (a[-1] - a[0]) / float(len(a) - 1)))
    print()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pclog = None
    for a in sys.argv[1:]:
        if a.startswith("--pclog="):
            pclog = a.split("=", 1)[1]
    hw_path = args[0] if args else DEFAULT_HW
    if not os.path.exists(hw_path):
        print("no existe la traza v4: %s" % hw_path); sys.exit(1)
    hw = load_hw(hw_path)
    print("hardware: %s  (%d escrituras a $2100)" % (hw_path, len(hw)))
    sh = segmentos(hw)
    imprime_segs(sh, "HARDWARE $2100")
    if os.path.exists(DEFAULT_RC):
        rc = load_recomp(DEFAULT_RC)
        print("recomp:   %s  (%d escrituras a $2100)" % (DEFAULT_RC, len(rc)))
        sr = segmentos(rc)
        imprime_segs(sr, "RECOMP $2100")
        compara(sh, sr)
        huecos(sh, "HARDWARE")
        huecos(sr, "RECOMP")
    else:
        print("(falta %s: corre el recomp con SNESRECOMP_INIDISP_TRACE=1)" % DEFAULT_RC)
    if pclog:
        tasa_gh(pclog)
