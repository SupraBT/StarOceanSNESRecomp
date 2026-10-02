#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compara la traza de EVENTOS del recompilador con la de Mesen, linea a linea.

Por que existe. Todo lo anterior comparaba AGREGADOS por fotograma: una fila
de la traza de Mesen contra una linea `[fstate]`. Un agregado esconde todo lo
que ocurre ENTRE dos fotogramas, y entre fotogramas es donde viven los puertos
de audio, que es justo lo que se llevaba horas buscando. Con dos trazas de
eventos en el MISMO formato se puede alinear una a una y decir "el evento N es
el mismo en los dos lados y aqui diverge", que si es una verdad con parte de
los dos lados.

El motor emite su traza con `SNESRECOMP_TRACE_EVENTS=<fichero>` y escribe
exactamente el formato de la sonda de Mesen:

    fr <TAB> master <TAB> src <TAB> kind <TAB> addr <TAB> val <TAB> nota

`fr` y `master` son el frame y el reloj del INVITADO, no los de host.

Como se alinean. Las dos trazas no tienen por que tener los mismos eventos: el
invitado puede escribir un handshake que el hardware no emite, o al reves. Por
eso la comparacion es una alineacion de secuencia (estilo difflib) y no una
comparacion posicional a pelo. Cada bloque de la alineacion se informa con el
frame de INVITADO de cada lado, que es la coordenada util.

Uso:
    python tools/trace_diff.py --motor build-hm/Release/events_motor.tsv \\
        --mesen <events.tsv> --hasta 200
    python tools/trace_diff.py --motor ... --mesen ... --kinds w214x,sdsp_data
"""
from __future__ import annotations

import argparse
import collections
import difflib
import pathlib
import re

MESEN = pathlib.Path(r"E:\Experimento Hermes\Documentacion"
                     r"\TracesMesen\Star_Ocean_Japan__so_trace_events.tsv")
REG = re.compile(r"reg=([0-9A-Fa-f]+)")


def cargar(path: pathlib.Path, hasta: int, kinds: set[str] | None) -> list:
    """[(fr, master, src, kind, addr, val, nota)] en orden de fichero."""
    ev = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for linea in fh:
            if linea.startswith("#"):
                continue
            p = linea.rstrip("\n").split("\t")
            if len(p) < 6:
                continue
            try:
                fr = int(p[0])
            except ValueError:
                continue
            if fr > hasta:
                break
            if kinds and p[3] not in kinds:
                continue
            ev.append((fr, p[1], p[2], p[3], p[4].upper(), p[5].upper(),
                       p[6] if len(p) > 6 else ""))
    return ev


def clave(ev) -> str:
    """Lo que tiene que COINCIDIR. `fr` y `master` no entran: se comparan
    aparte, porque son la coordenada y no el contenido."""
    _, _, src, kind, addr, val, nota = ev
    m = REG.search(nota)
    reg = m.group(1).upper() if m else ""
    return "%s|%s|%s|%s|%s|%s" % (src, kind, addr, val, reg, nota)


def forma(ev) -> str:
    fr, master, src, kind, addr, val, nota = ev
    m = REG.search(nota)
    reg = m.group(1).upper() if m else ""
    return "f%-6s m=%-12s %-4s %-10s $%s=%-3s %s" % (
        fr, master, src, kind, addr, val, ("reg=" + reg) if reg else "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--motor", required=True)
    ap.add_argument("--mesen", default=str(MESEN))
    ap.add_argument("--hasta", type=int, default=300)
    ap.add_argument("--kinds", default="",
                    help="comma separated; vacio = todos")
    ap.add_argument("--max-bloques", type=int, default=25)
    ap.add_argument("--cara-a-cara", type=int, default=0,
                    help="print the first N events of each side side by side")
    args = ap.parse_args()

    kinds = set(args.kinds.split(",")) if args.kinds else None
    mot = cargar(pathlib.Path(args.motor), args.hasta, kinds)
    hw = cargar(pathlib.Path(args.mesen), args.hasta, kinds)
    print("motor: %d eventos   mesen: %d eventos   (hasta f%d%s)"
          % (len(mot), len(hw), args.hasta,
             ", kinds=" + ",".join(sorted(kinds)) if kinds else ""))

    if not mot:
        print("El motor no emitio eventos. Falta SNESRECOMP_TRACE_EVENTS=<fichero>.")
        return 1
    if not hw:
        print("Mesen no tiene eventos en ese rango.")
        return 1

    a = [clave(e) for e in mot]
    b = [clave(e) for e in hw]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    bloques = [g for g in sm.get_opcodes() if g[0] != "equal"]
    print("bloques que difieren: %d de %d" % (len(bloques), len(sm.get_opcodes())))

    # Reparto por clase de fallo: eso dice de que va el problema.
    clases = collections.Counter()
    for tag, i1, i2, j1, j2 in bloques:
        if tag == "replace":
            clases["replace"] += 1
        elif tag == "delete":
            clases["solo en el motor (delete)"] += 1
        else:
            clases["solo en mesen (insert)"] += 1
    for k, v in clases.most_common():
        print("   %-26s %d" % (k, v))

    if args.cara_a_cara:
        print()
        print("cara a cara, los primeros %d eventos:" % args.cara_a_cara)
        print()
        print("   %-50s | %s" % ("MOTOR", "MESEN"))
        for k in range(min(args.cara_a_cara, max(len(mot), len(hw)))):
            izq = forma(mot[k]) if k < len(mot) else ""
            der = forma(hw[k]) if k < len(hw) else ""
            print("%s %-50s | %s" % ("  " if izq == der else "!!", izq, der))

    print("\nprimeros bloques (contexto de 2 eventos por lado):\n")
    for tag, i1, i2, j1, j2 in bloques[:args.max_bloques]:
        ini = max(0, i1 - 2)
        print("--- %s  motor[%d:%d]  mesen[%d:%d]  frames motor f%s-f%s"
              % (tag, i1, i2, j1, j2,
                 mot[i1][0] if i1 < len(mot) else "?",
                 mot[i2 - 1][0] if i2 > i1 else "?"))
        for k in range(ini, i1):
            print("      = %s" % forma(mot[k]))
        for k in range(i1, min(i2, i1 + 4)):
            print("      M %s" % forma(mot[k]))
        if i2 - i1 > 4:
            print("      M ... (%d mas)" % (i2 - i1 - 4))
        ini2 = max(0, j1 - 2)
        for k in range(ini2, j1):
            print("      = %s" % forma(hw[k]))
        for k in range(j1, min(j2, j1 + 4)):
            print("      H %s" % forma(hw[k]))
        if j2 - j1 > 4:
            print("      H ... (%d mas)" % (j2 - j1 - 4))
        print()

    # Un dato que no sale de la alineacion y que siempre hace falta: la
    # diferencia de frame entre el mismo evento en los dos lados. Si esa
    # diferencia crece con el frame, el problema no es de contenido sino de
    # RELOJ, y hay que ir a por el reloj antes que a los datos.
    print("deriva de frame (motor - mesen) en bloques de 50 frames:")
    deriva = {}
    for _a, i1, j1 in sm.get_matching_blocks():
        for k in range(i1, j1):
            fr_m = mot[k][0]
            if k + (j1 - i1) >= len(hw):
                continue
            fr_h = hw[k + (j1 - i1)][0]
            b = fr_m // 50
            deriva.setdefault(b, []).append(fr_m - fr_h)
    for b in sorted(deriva)[:20]:
        d = deriva[b]
        media = sum(d) / len(d)
        print("   f%4d-%4d  eventos=%-6d  deriva media %+.2f frames  "
              "(min %+d, max %+d)" % (b * 50, b * 50 + 49, len(d), media,
                                      min(d), max(d)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
