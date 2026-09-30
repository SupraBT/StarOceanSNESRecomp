#!/usr/bin/env python3
"""Convierte un trace de partida de Mesen en un guion de entrada del motor.

Entrada: el `*_trace.tsv` que escribe tools/mesen_so_trace.lua (una fila por
frame, con la mascara del pad y el reloj del invitado).
Salida : '<clave> <mascara>' con un evento por CAMBIO de mascara, apuntando al
reloj pedido, mas la cabecera que declara ese reloj (ver tools/replay_clock.py
para por que el reloj y no el indice de frame).

    python tools/mesen_replay_por_reloj.py <trace.tsv> <salida.txt> [--clock master]

Relojes: master (recomendado, `master` del trace), cpu (`cyc`) o frame (`fr`).
El orden de bits de la mascara es el de $4218:
    b0=B b1=Y b2=Sel b3=Start b4=Up b5=Down b6=Left b7=Right b8=A b9=X b10=L b11=R
"""
import argparse
import os
import sys

CLOCKS = {"master": "master", "cpu": "cyc", "frame": "fr"}


def read_trace(path):
    """Devuelve (cabecera, filas) saltando los comentarios del header."""
    header = None
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("#fr\t"):
                header = line[1:].split("\t")
                continue
            if line.startswith("#") or not line.strip():
                continue
            if header is None:
                raise SystemExit("el TSV no trae la fila de cabecera '#fr ...': %s" % path)
            rows.append(line.split("\t"))
    if header is None:
        raise SystemExit("el TSV no trae la fila de cabecera '#fr ...': %s" % path)
    return header, rows


def convert(tsv, clock, clave="frame-start"):
    """Devuelve los eventos del pad keyeados al reloj pedido.

    `clave` decide en que instante del invitado entra en vigor cada mascara:

      frame-start (por defecto): el reloj del INICIO del frame del cambio, o
        sea el reloj del frame anterior (`M(fr-1)`). El motor elige la mascara
        del frame que va a ejecutar leyendo el master AL INICIO de ese frame,
        asi que una clave puesta al final del frame del cambio solo se ve en
        el frame siguiente: medido con el trace de Mesen, eso retrasaba TODAS
        las pulsaciones un frame (49,8 % de acierto en los frames de cambio)
        y con la clave al inicio acierta el 100,00 % (890/890).

      frame-end: el reloj del final del frame del cambio (comportamiento
        anterior, se conserva para reproducir guiones ya validados).
    """
    header, rows = read_trace(tsv)
    for name in ("in", CLOCKS[clock]):
        if name not in header:
            raise SystemExit("al TSV le falta la columna '%s'" % name)
    key_col = header.index(CLOCKS[clock])
    mask_col = header.index("in")
    events = []
    last = None
    con_pulsacion = 0
    prev_key = 0
    for row in rows:
        mask = (row[mask_col].strip() or "0000").upper() if mask_col < len(row) else "0000"
        if mask not in ("", "0000"):
            con_pulsacion += 1
        key_here = int(row[key_col] or 0)
        if mask == last:
            prev_key = key_here
            continue
        key = prev_key if clave == "frame-start" else key_here
        events.append((key, mask))
        last = mask
        prev_key = key_here
    return events, len(rows), con_pulsacion


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace", help="*_trace.tsv de la sesion de Mesen")
    ap.add_argument("salida", help="guion de entrada a escribir (p.ej. tools/input_scripts/mesen_master.txt)")
    ap.add_argument("--clock", default="master", choices=sorted(CLOCKS),
                    help="reloj del invitado al que keyear el guion (por defecto master)")
    ap.add_argument("--clave", default="frame-start", choices=("frame-start", "frame-end"),
                    help="instante en que entra en vigor cada mascara: inicio del frame del "
                         "cambio (correcto) o final del mismo frame (un frame tarde)")
    args = ap.parse_args()

    events, frames, con_pulsacion = convert(args.trace, args.clock, args.clave)
    if not events:
        print("FALLO: el trace no tiene ni una pulsacion")
        return 1
    outdir = os.path.dirname(os.path.abspath(args.salida))
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    with open(args.salida, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# replay de %s (sesion de Mesen), keyeado al reloj del invitado\n"
                 % os.path.basename(args.trace))
        fh.write("# clock: %s\n" % args.clock)
        fh.write("# clave: %s (inicio del frame del cambio = la mascara entra en vigor "
                 "ese mismo frame)\n" % args.clave)
        fh.write("# formato: '<%s> <mascara hex $4218>' -- "
                 "b0=B b1=Y b2=Sel b3=Start b4=Up b5=Down b6=Left b7=Right "
                 "b8=A b9=X b10=L b11=R\n" % CLOCKS[args.clock])
        for key, mask in events:
            fh.write("%d %s\n" % (key, mask))

    print("[mesen_replay] %s: %d frames, %d con pulsacion, %d eventos -> %s (clock=%s, clave=%s)"
          % (os.path.basename(args.trace), frames, con_pulsacion, len(events),
             args.salida, args.clock, args.clave))
    print("[mesen_replay] primera clave=%d ultima=%d"
          % (events[0][0], events[-1][0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
