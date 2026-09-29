#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A/B hardware (mesen_intro_probe.tsv) contra recomp (log [fstate]).

El log [fstate] lo emite src/so_rtl.c (SNESRECOMP_FRAME_STATE=1):
  [fstate] f=<gf> nmiEn=.. resume=<pc24> inidisp=<reg $2100 real> cpu=.. master=..
           pad=.. r4200=.. hIrq=.. vIrq=.. irq=.. nmi=.. vTimer=..
           E4=<word $00E4> DA=<byte $00DA> AFB=<byte $0AFB> AFD=<word $0AFD> D01=<byte $0D01>

El TSV de hardware trae: fr master pc(16 bits, sin banco) D DB E4 E5 DA AFB AFD
ini($2100 escritas por CPU) x(exec vigilados) col13=LECTURAS col14=SOMBRAS.

Uso:
  python ab_boot.py eventos [fichero_fstate]
  python ab_boot.py ventana <a> <b> [fichero_fstate]
  python ab_boot.py lecturas [fichero_fstate]
"""
import re, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intro_tsv as T

FSTATE = r"E:\Recompilador Super Nintendo\StarOceanRecomp\build-dev\Release\logs\fstate_rep_bueno_err.log"

PAT = re.compile(
    r"\[fstate\] f=(\d+) nmiEn=(\d+) resume=(\S+) inidisp=(\S+) cpu=(\d+) "
    r"master=(\d+) pad=(\S+) r4200=(\S+) hIrq=(\d+) vIrq=(\d+) irq=(\d+) "
    r"nmi=(\d+) vTimer=(\d+) E4=(\S+) DA=(\S+) AFB=(\S+) AFD=(\S+) D01=(\S+)")


class R(object):
    pass


def load_recomp(path):
    rows = []
    for line in open(path, errors="replace"):
        m = PAT.search(line)
        if not m:
            continue
        r = R()
        r.f = int(m.group(1))
        r.inidisp = m.group(4)
        r.pad = m.group(7)
        r.r4200 = m.group(8)
        r.irq = int(m.group(11))
        r.nmi = int(m.group(12))
        r.resume = m.group(3)
        r.e4 = int(m.group(14), 16)
        r.da = int(m.group(15), 16)
        r.afb = int(m.group(16), 16)
        r.afd = int(m.group(17), 16)
        r.d01 = int(m.group(18), 16)
        rows.append(r)
    return rows


def events(rows, keys, tag):
    """Cambios de las claves dadas. keys = [(nombre, fn)]"""
    print("=== eventos %s ===" % tag)
    prev = None
    for r in rows:
        cur = tuple(fn(r) for _, fn in keys)
        if cur != prev:
            fr = getattr(r, "fr", None)
            if fr is None:
                fr = r.f
            print("  %-6s %s" % ("fr%d" % fr,
                                 " ".join("%s=%s" % (n, fn(r)) for n, fn in keys)))
            prev = cur


def cmd_eventos(hw, rc):
    print("--- HARDWARE: fr1..%d (%d frames, sin input) ---" % (hw[-1].fr, len(hw)))
    events(hw, [("DA", lambda r: "%02X" % r.da), ("E4", lambda r: "%02X" % r.e4),
                ("AFB", lambda r: "%02X" % r.afb), ("AFD", lambda r: "%04X" % r.afd),
                ("D", lambda r: "%04X" % r.d)], "hardware")
    print()
    print("--- RECOMP: f1..%d (%d frames, input=%s) ---" % (rc[-1].f, len(rc),
                                                            os.path.basename(FSTATE)))
    events(rc, [("inidisp", lambda r: r.inidisp), ("E4", lambda r: "%04X" % r.e4),
                ("DA", lambda r: "%02X" % r.da), ("AFB", lambda r: "%02X" % r.afb),
                ("AFD", lambda r: "%04X" % r.afd), ("D01", lambda r: "%02X" % r.d01)],
           "recomp")


def cmd_ventana(hw, rc, a, b):
    hwd = {r.fr: r for r in hw}
    rcd = {r.f: r for r in rc}
    for f in range(a, b + 1):
        h = hwd.get(f)
        c = rcd.get(f)
        left = ("fr%-5d pc=%s D=%04X E4=%02X E5=%02X DA=%02X AFB=%02X AFD=%04X"
                % (f, h.pc, h.d, h.e4, h.e5, h.da, h.afb, h.afd)) if h else "fr%-5d -" % f
        right = ("rc pc=%s ini=%s E4=%04X DA=%02X AFB=%02X AFD=%04X D01=%02X"
                 % (c.resume, c.inidisp, c.e4, c.da, c.afb, c.afd, c.d01)) if c else "-"
        print("%s   |   %s" % (left, right))


def cmd_lecturas(hw, rc):
    print("=== HW: lecturas por frame ($4800-$4807 / $2140-$2143 / $2138-$213F) ===")
    run = []
    for r in hw:
        s = " ".join("%s=%d/%02X" % (k, v[0], v[1])
                     for k, v in sorted(r.reads.items()))
        if s:
            run.append((r.fr, s))
    # resumir: solo cambios de patrón
    prev = None
    for fr, s in run:
        if s != prev:
            print("  fr%-5d %s" % (fr, s))
            prev = s
    print("  (%d frames con datos)" % len(run))


def main():
    global FSTATE
    hw = T.load()
    args = sys.argv[1:]
    cmd = args[0] if args else "eventos"
    if args and args[-1].endswith(".log"):
        FSTATE = args[-1]
        args = args[:-1]
    rc = load_recomp(FSTATE)
    if not rc:
        print("sin datos de recomp en %s" % FSTATE)
        return
    if cmd == "eventos":
        cmd_eventos(hw, rc)
    elif cmd == "ventana":
        cmd_ventana(hw, rc, int(args[1]), int(args[2]))
    elif cmd == "lecturas":
        cmd_lecturas(hw, rc)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
