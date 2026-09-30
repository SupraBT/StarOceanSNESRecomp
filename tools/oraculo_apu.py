#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Oraculo de APU: compara el flujo del CPU a los puertos $2140-$2143 del recomp
contra el del trace de hardware, alineado por reloj master.

Por que este y no los registros: los registros de CPU muestreados por frame no
son comparables (§29: A coincide en el 0,2 % porque manda el instante de
muestreo). El flujo de escrituras al puerto de la APU si es un observable
estable: lo produce el driver de sonido del juego, que es esclavo de la logica
de partida, asi que cambia cuando la partida cambia de estado (escena, musica,
SFX) y no ciclo a ciclo.

Lados:
  nuestro : apu_port_rw.log del motor (`SNESRECOMP_APU_PORT_RW=<ruta>`), lineas
            `f<frame> R|W $214x=VV master=<m> (simbolo)`
  hardware: `*_events.tsv`, filas `fr master src kind addr val nota` con
            src=cpu y kind=w214x (escrituras del CPU al puerto)

Comparacion:
  1. escrituras agrupadas por frame de hardware (grid `M(fr)=306900+(fr-1)*357368`)
  2. **curva acumulada**: la primera abscisa en la que el conteo acumulado de un
     lado se separa del otro mas de la tolerancia. Es inmune al desfase de medio
     frame en los bordes, que en el conteo por frame da +-1 ruido.
  3. secuencia de valores dentro de la ventana de la primera separacion.

Uso:
  python tools/oraculo_apu.py --nuestro logs/apu_rw_full.log --eventos events.tsv
"""
import argparse
import re
import sys

MASTER_PER_FRAME = 1364 * 262
M1 = 306900          # master al cerrar el frame 1 de hardware


def fr_of_master(m):
    return int((m - M1) // MASTER_PER_FRAME) + 1


OURS = re.compile(r"^f(\d+)\s+([RW])\s+\$([0-9A-Fa-f]{4})=([0-9A-Fa-f]{2})\s+master=(\d+)")


def load_ours(path):
    w, r = [], []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = OURS.match(line)
            if not m:
                continue
            fr, rw, addr, val, master = m.groups()
            item = (int(master), int(addr, 16), int(val, 16), int(fr))
            (w if rw == "W" else r).append(item)
    return w, r


def load_hw(path, hasta_fr):
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("#"):
                continue
            c = line.rstrip("\r\n").split("\t")
            if len(c) < 6 or c[2] != "cpu" or not c[3].startswith("w214"):
                continue
            fr = int(c[0])
            if fr > hasta_fr:
                continue
            try:
                out.append((int(c[1]), int(c[4], 16), int(c[5], 16), fr))
            except ValueError:
                continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nuestro", required=True)
    ap.add_argument("--eventos", required=True)
    ap.add_argument("--tolerancia", type=int, default=4)
    ap.add_argument("--hasta-fr", type=int, default=100000)
    a = ap.parse_args()

    W, R = load_ours(a.nuestro)
    maxfr = max([x[3] for x in W] + [1]) if W else 1
    H = load_hw(a.eventos, min(a.hasta_fr, maxfr * 3))
    W.sort(); H.sort()
    print("nuestro : %d escrituras, %d lecturas al puerto (hasta frame nuestro %d)"
          % (len(W), len(R), maxfr))
    print("hardware: %d escrituras del CPU al puerto" % len(H))
    if not W or not H:
        print("ERROR: falta un lado")
        return 1

    # 1+2. curvas acumuladas por frame de hardware
    cu, ch, ih = 0, 0, 0
    first = None
    filas = []
    for m, addr, val, frn in W:
        f = fr_of_master(m)
        cu += 1
        while ih < len(H) and H[ih][0] <= m:
            ch += 1
            ih += 1
        if first is None and abs(cu - ch) > a.tolerancia:
            first = (f, m, cu, ch)
        if len(filas) < 12 or (first and filas[-1][0] < f <= first[0] + 6):
            filas.append((f, cu, ch))

    print("\ncumulativo: nuestro=%d  hardware=%d  (diferencia final %+d)" % (cu, ch, cu - ch))
    if first:
        f, m, cu1, ch1 = first
        print("PRIMERA SEPARACION: frame de hardware %d (master %d)" % (f, m))
        print("  en ese punto: nuestro acumulado=%d  hardware=%d  (delta %+d)"
              % (cu1, ch1, cu1 - ch1))
        print("  curva (frame_hw, acumulado_nuestro, acumulado_hw):")
        for fila in filas[-14:]:
            print("    fr %6d   %7d   %7d" % fila)
        # 3. valores en la ventana
        print("\n  valores alrededor de la separacion:")
        print("   nuestro:")
        for m, addr, val, frn in [x for x in W if first[1] - 4000 <= x[0] <= first[1] + 4000][:16]:
            print("     f=%-6d $%04X=%02X master=%d" % (frn, addr, val, m))
        print("   hardware:")
        for m, addr, val, frn in [x for x in H if first[1] - 4000 <= x[0] <= first[1] + 4000][:16]:
            print("     fr=%-6d $%04X=%02X master=%d" % (frn, addr, val, m))
    else:
        print("SIN SEPARACION: el flujo coincide dentro de +-%d escrituras en todo el tramo" % a.tolerancia)
        print("  curva (frame_hw, acumulado_nuestro, acumulado_hw), ultimas muestras:")
        for fila in filas[-12:]:
            print("    fr %6d   %7d   %7d" % fila)
    return 0


if __name__ == "__main__":
    sys.exit(main())
