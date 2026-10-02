#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A/B recomp vs hardware alineado por RELOJ MASTER (unica magnitud comun).

El indice de frame no es comparable: el recomp ejecuta ~66 frames de invitado
antes de su primer limite de frame real, asi que f_recomp != fr_hardware.
`master` (357368 por frame en ambos) si lo es.

Hardware : mesen_intro_probe.tsv
           fr master pc D DB E4 E5 DA AFB AFD ini <col11> <col12=lecturas> <col13=escrituras>
Recomp   : logs/fstate_noinput_err.log  (lineas `[fstate] ...`)

Uso:
  python ab_master.py eventos     -> lista de cambios de DA/AFB/E4 en ambos lados
  python ab_master.py fases       -> resumen por tramos (master)
  python ab_master.py ventana M0 M1
"""
import re, sys, os

# Ruta de la traza de hardware.  Se puede apuntar a otra (p.ej. la nueva de
# 15 columnas) sin editar el fichero:
#   SNESRECOMP_PROBE="...\mesen_fades900.tsv" python tools/ab_master.py fases
PROBE = os.environ.get(
    "SNESRECOMP_PROBE",
    r"E:\Experimento Hermes\Documentacion\TracesMesen\mesen_intro_probe.tsv")
FSTATE = os.path.join(os.path.dirname(__file__), "..", "build-dev", "Release", "logs",
                      "fstate_noinput_err.log")

MASTER_PER_FRAME = 357368


def load_hw():
    out = []
    for ln in open(PROBE, errors="replace"):
        ln = ln.rstrip("\r\n")
        if not ln or ln.startswith("#"):
            continue
        c = ln.split("\t")
        if len(c) < 11:
            continue
        try:
            fr = int(c[0]); master = int(c[1])
        except ValueError:
            continue
        reads = c[12] if len(c) > 12 else ""
        out.append(dict(fr=fr, master=master, pc=c[2], E4=c[5], E5=c[6],
                        DA=c[7], AFB=c[8], AFD=c[9], ini=c[10], reads=reads))
    return out


def load_rc():
    out = []
    for ln in open(FSTATE, errors="replace"):
        if "[fstate]" not in ln:
            continue
        d = dict(re.findall(r"(\w+)=(\S+)", ln.split("[fstate]")[1]))
        out.append(dict(f=int(d["f"]), master=int(d["master"]), resume=d.get("resume", "?"),
                        E4=d.get("E4", "?"), DA=d.get("DA", "?"), AFB=d.get("AFB", "?"),
                        AFD=d.get("AFD", "?"), ini=d.get("inidisp", "?")))
    return out


def guestframe(master):
    return master / float(MASTER_PER_FRAME)


def events(rows, key, label, maxn=40):
    print("--- %s: cambios de %s ---" % (label, key))
    prev = None
    for r in rows:
        v = r[key]
        if v != prev:
            print("  %-9.2f gf  %s %s=%s" % (guestframe(r["master"]),
                  ("fr%-5d" % r["fr"]) if "fr" in r else ("f%-5d" % r["f"]), key, v))
            prev = v
    print()


def compare(hw, rc):
    """Tabla side-by-side muestreada cada 16 frames de invitado."""
    print("%-9s | %-22s | %-30s" % ("gf(master)", "HARDWARE fr:DA/AFB/E4/ini", "RECOMP f:DA/AFB/E4/ini"))
    print("-" * 70)
    step = 16 * MASTER_PER_FRAME
    m = 0
    hi = 0
    ri = 0
    while m <= 800 * MASTER_PER_FRAME:
        while hi + 1 < len(hw) and hw[hi + 1]["master"] <= m: hi += 1
        while ri + 1 < len(rc) and rc[ri + 1]["master"] <= m: ri += 1
        h, r = hw[hi], rc[ri]
        print("%-9.1f | fr%-5d %s/%s/%-5s/%-4s | f%-5d %s/%s/%-5s/%-4s" % (
            m / float(MASTER_PER_FRAME), h["fr"], h["DA"], h["AFB"], h["E4"], h["ini"],
            r["f"], r["DA"], r["AFB"], r["E4"], r["ini"]))
        m += step


def window(hw, rc, m0, m1):
    print("ventana master %.2f..%.2f gf" % (guestframe(m0), guestframe(m1)))
    print("%-9s %-6s %-6s %-5s %-5s | %-6s %-6s %-5s %-5s | %-8s %-8s" %
          ("gf", "fr", "DA", "AFB", "E4", "f", "DA", "AFB", "E4", "resume", "pc"))
    hi = ri = 0
    m = m0
    while m <= m1:
        while hi + 1 < len(hw) and hw[hi + 1]["master"] <= m: hi += 1
        while ri + 1 < len(rc) and rc[ri + 1]["master"] <= m: ri += 1
        h, r = hw[hi], rc[ri]
        print("%-9.2f %-6d %-6s %-5s %-5s | %-6d %-6s %-5s %-5s | %-8s %-8s" % (
            m / float(MASTER_PER_FRAME), h["fr"], h["DA"], h["AFB"], h["E4"],
            r["f"], r["DA"], r["AFB"], r["E4"], r["resume"], h["pc"]))
        m += 4 * MASTER_PER_FRAME


if __name__ == "__main__":
    hw = load_hw(); rc = load_rc()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "eventos"
    print("hw filas=%d (master %.1f..%.1f gf)  recomp filas=%d (master %.1f..%.1f gf)"
          % (len(hw), guestframe(hw[0]["master"]), guestframe(hw[-1]["master"]),
             len(rc), guestframe(rc[0]["master"]), guestframe(rc[-1]["master"])))
    print()
    if cmd == "eventos":
        events(hw, "DA", "HARDWARE")
        events(rc, "DA", "RECOMP")
        events(hw, "AFB", "HARDWARE")
        events(rc, "AFB", "RECOMP")
    elif cmd == "fases":
        compare(hw, rc)
    elif cmd == "ventana":
        window(hw, rc, int(float(sys.argv[2]) * MASTER_PER_FRAME),
               int(float(sys.argv[3]) * MASTER_PER_FRAME))
