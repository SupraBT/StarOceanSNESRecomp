#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analiza mesen_intro_probe.tsv (hardware real, 2000 frames desde el arranque).

Mapeo REAL de columnas (el codigo de mesen_intro_probe.lua:246-261 manda; la
cabecera del fichero tiene las dos ultimas etiquetas intercambiadas):

   1 fr      numero de frame (1-based)
   2 master  master clock del SNES en emu.getMasterClock()
   3 pc      PC de la CPU en el limite de frame
   4 D       registro D (direct page)
   5 DB      banco de datos
   6 E4      $00:E4  (contador de frames del invitado)
   7 E5      $00:E5
   8 DA      $00:DA  (sombra de INIDISP)
   9 AFB     $00:AFB
  10 AFD     $00:AFD|AFE (word)
  11 ini     lista de valores escritos a $2100 en ese frame ("80" / "80+0F+80")
  12 x       contadores de exec por direccion vigilada
  13 LECTURAS  r4800=<n>/<v>,r2140=<n>/<v>   (etiquetada "writes" en la cabecera)
  14 SOMBRAS   "DA=.. E4=.. AF9=.. AFB=.. AFD=.."  (etiquetada "reads")

Uso:
  python intro_tsv.py resumen
  python intro_tsv.py tramos
  python intro_tsv.py ventana <a> <b>
  python intro_tsv.py fades
  python intro_tsv.py ini
  python intro_tsv.py lecturas
  python intro_tsv.py diff <fichero_del_recomp.tsv>   (compara timeline)
"""
import sys, os, re

TSV = r"E:\Experimento Hermes\Documentacion\TracesMesen\mesen_intro_probe.tsv"

NCOLS = 14


def hx(s):
    if s is None or s == "":
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return int(s, 16)
    except ValueError:
        try:
            return int(s)
        except ValueError:
            return None


def parse_list(s):
    """'80+0F+80' -> [0x80,0x0F,0x80]"""
    if not s:
        return []
    out = []
    for p in s.split("+"):
        v = hx(p)
        if v is not None:
            out.append(v)
    return out


def parse_reads(s):
    """'r4800=2/03,r2140=396/6B' -> {'r4800': (2,0x03), ...}"""
    d = {}
    if not s:
        return d
    for p in s.split(","):
        p = p.strip()
        if not p or "=" not in p:
            continue
        k, v = p.split("=", 1)
        k = k.strip()
        if "/" in v:
            n, val = v.split("/", 1)
        else:
            n, val = v, "0"
        try:
            n = int(n)
        except ValueError:
            continue
        d[k] = (n, hx(val) or 0)
    return d


def parse_shadows(s):
    """'DA=.. E4=.. AF9=.. AFB=.. AFD=..' -> {'DA':[..], ...}"""
    d = {}
    if not s:
        return d
    for p in s.split():
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        d[k.strip()] = parse_list(v)
    return d


class Row(object):
    __slots__ = ("fr", "master", "pc", "d", "db", "e4", "e5", "da", "afb",
                 "afd", "ini", "x", "reads", "shadows", "raw")

    def __repr__(self):
        return "<fr=%d pc=%s E4=%s DA=%s AFB=%s ini=%s rd=%s sh=%s>" % (
            self.fr, self.raw[2], self.e4, self.da, self.afb,
            self.ini, self.reads, self.shadows)


def load(path=TSV):
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            c = line.split("\t")
            r = Row()
            r.raw = c
            r.fr = int(c[0])
            r.master = int(c[1]) if c[1] else None
            r.pc = c[2]
            r.d = hx(c[3])
            r.db = hx(c[4])
            r.e4 = hx(c[5])
            r.e5 = hx(c[6])
            r.da = hx(c[7])
            r.afb = hx(c[8])
            r.afd = hx(c[9])
            r.ini = parse_list(c[10] if len(c) > 10 else "")
            r.x = c[11] if len(c) > 11 else ""
            r.reads = parse_reads(c[12] if len(c) > 12 else "")
            r.shadows = parse_shadows(c[13] if len(c) > 13 else "")
            rows.append(r)
    return rows


def by_frame(rows):
    return {r.fr: r for r in rows}


def get(d, fr, key):
    r = d.get(fr)
    return getattr(r, key) if r else None


# ---------------------------------------------------------------- comandos

def cmd_resumen(rows):
    print("frames=%d  fr[%d..%d]" % (len(rows), rows[0].fr, rows[-1].fr))
    print()
    for k in ("e4", "e5", "da", "afb", "afd", "d", "db"):
        vals = {}
        for r in rows:
            vals[getattr(r, k)] = vals.get(getattr(r, k), 0) + 1
        top = sorted(vals.items(), key=lambda kv: -kv[1])[:8]
        print("%-5s valores distintos=%3d  top: %s" % (
            k, len(vals),
            " ".join("%s:%d" % ("%04X" % v if v > 255 else "%02X" % v, n)
                     for v, n in top)))
    print()
    nshadow = sum(1 for r in rows if r.shadows)
    nini = sum(1 for r in rows if r.ini)
    nreads = sum(1 for r in rows if r.reads)
    n4800 = sum(1 for r in rows if "r4800" in r.reads)
    n2140 = sum(1 for r in rows if "r2140" in r.reads)
    print("frames con ini($2100)=%d  con sombras=%d  con lecturas=%d (r4800=%d r2140=%d)"
          % (nini, nshadow, nreads, n4800, n2140))
    print("frames con escritura a sombras:")
    for r in rows:
        if r.shadows:
            print("   fr%-5d %s" % (r.fr, r.raw[13]))


def _fmt_reads(r):
    if not r.reads:
        return ""
    return " ".join("%s=%d/%02X" % (k, v[0], v[1]) for k, v in sorted(r.reads.items()))


def _fmt_shadows(r):
    if not r.shadows:
        return ""
    return " ".join("%s=%s" % (k, "+".join("%02X" % v for v in vs))
                    for k, vs in r.shadows.items())


def cmd_ventana(rows, a, b):
    for r in rows:
        if a <= r.fr <= b:
            print("fr%-5d m=%-11s pc=%s D=%s DB=%s E4=%02X E5=%02X DA=%02X "
                  "AFB=%02X AFD=%04X ini=%-12s x=%-24s rd=%-34s sh=%s" % (
                      r.fr, r.master, r.pc, "%04X" % r.d, "%02X" % r.db,
                      r.e4, r.e5, r.da, r.afb, r.afd,
                      "+".join("%02X" % v for v in r.ini), r.x,
                      _fmt_reads(r), _fmt_shadows(r)))


def cmd_tramos(rows):
    """Tramos contiguos con el mismo (DA, AFB, E5) - 'la foto de video'."""
    prev = None
    start = None
    for r in rows:
        key = (r.da, r.afb, r.e5, r.afd)
        if key != prev:
            if prev is not None:
                print("fr %-5d..%-5d  (%4d)  DA=%02X AFB=%02X E5=%02X AFD=%04X" % (
                    start, r.fr - 1, r.fr - start, prev[0], prev[1], prev[2], prev[3]))
            prev = key
            start = r.fr
    print("fr %-5d..%-5d  (%4d)  DA=%02X AFB=%02X E5=%02X AFD=%04X" % (
        start, rows[-1].fr, rows[-1].fr - start + 1, prev[0], prev[1], prev[2], prev[3]))


def cmd_fades(rows):
    """Localiza cambios de DA y mide la rampa (cuantos frames por nivel)."""
    print("=== cambios de DA ($00:DA, sombra de INIDISP) ===")
    prev = None
    for r in rows:
        if r.da != prev:
            print("fr%-5d DA=%02X (venia de %s) pc=%s E4=%02X AFB=%02X" % (
                r.fr, r.da, "??" if prev is None else "%02X" % prev,
                r.pc, r.e4, r.afb))
            prev = r.da
    print()
    print("=== rampas: secuencias de DA monótonas ===")
    i = 0
    n = len(rows)
    while i < n:
        j = i
        while j + 1 < n and rows[j + 1].da != rows[i].da:
            j += 1
        if j > i:
            seq = rows[i:j + 1]
            d = seq[1].da - seq[0].da if len(seq) > 1 else 0
            step = 1
            if len(seq) > 2:
                step = (seq[-1].da - seq[0].da)
                step = step / float(len(seq) - 1)
            print("fr %-5d..%-5d  %2d frames  DA %02X -> %02X  (paso medio %.3f/frame)" % (
                seq[0].fr, seq[-1].fr, len(seq), seq[0].da, seq[-1].da, step))
        i = j + 1


def cmd_ini(rows):
    print("=== frames con escritura a $2100 (INIDISP) ===")
    for r in rows:
        if r.ini:
            print("fr%-5d ini=%s  DA=%02X AFB=%02X E4=%02X pc=%s x=%s" % (
                r.fr, "+".join("%02X" % v for v in r.ini), r.da, r.afb, r.e4, r.pc, r.x))


def cmd_lecturas(rows):
    """Perfil de lecturas por frame (esperas del invitado)."""
    print("=== lecturas por frame: resumen por rangos ===")
    for key in ("r4800", "r2140", "r2138"):
        seq = [(r.fr, r.reads[key][0], r.reads[key][1])
               for r in rows if key in r.reads]
        if not seq:
            print("%s: sin datos" % key)
            continue
        n = [x[1] for x in seq]
        print("%s: frames con dato=%d  min=%d max=%d  1os=%s" % (
            key, len(seq), min(n), max(n), seq[:3]))
        # tramos con valor estable de conteo
        prevc = None
        start = None
        cnt = 0
        for fr, c, v in seq:
            if abs(c - (prevc or 0)) > max(2, (prevc or 0) * 0.05):
                if prevc is not None and cnt > 4:
                    print("   fr %-5d..%-5d (%4d)  n~%-7d v=%02X" % (
                        start, fr - 1, cnt, prevc, prevv))
                prevc = c
                start = fr
                cnt = 0
            prevv = v
            cnt += 1
        if prevc is not None:
            print("   fr %-5d..%-5d (%4d)  n~%-7d v=%02X" % (
                start, seq[-1][0], cnt, prevc, prevv))


def cmd_diff(rows, other):
    """Compara el timeline de hardware contra otro TSV con el mismo formato."""
    print("(no implementado todavia: %s)" % other)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        cmd_resumen(load())
        return
    cmd = sys.argv[1]
    path = TSV
    if cmd == "ventana":
        rows = load(path)
        cmd_ventana(rows, int(sys.argv[2]), int(sys.argv[3]))
        return
    if cmd == "diff":
        cmd_diff(load(path), sys.argv[2])
        return
    rows = load(path)
    fn = {"resumen": cmd_resumen, "tramos": cmd_tramos, "fades": cmd_fades,
          "ini": cmd_ini, "lecturas": cmd_lecturas}[cmd]
    fn(rows)


if __name__ == "__main__":
    main()
