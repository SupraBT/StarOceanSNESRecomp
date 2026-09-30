#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Alinea nuestro [fstate] (motor recomp) contra el trace por frame de Mesen y
encuentra la PRIMERA divergencia, usando el reloj master del invitado como clave.

Por que: el indice de frame es un reloj con perdidas (§27): durante el boot y las
descompresiones S-DD1 un frame de host ejecuta varios frames de invitado, y los
guias de entrada keyeados por indice caen en otro instante del juego. El master
si es exacto en ambos lados (Mesen lo graba por frame; el host lo imprime en
[fstate]).

Uso:
  python tools/divergencia_mesen.py --fstate build-prof/Release/logs/c_full.log \
      --trace ".../Star_Ocean_Japan__so_trace_trace.tsv" [--desde N] [--hasta N]

Compara, al mismo master:
  * pad  : mascara entregada al invitado vs columna 'in'/'pin' de hardware
  * pc   : banco de PC de hardware vs banco del PC del invitado (nuestro resume)
  * db   : banco de datos
Informa la primera discrepancia de cada tipo con 8 frames de contexto.
"""
import argparse
import bisect
import re
import sys

MASTER_PER_FRAME = 1364 * 262  # 357368

FSTATE = re.compile(
    r"\[fstate\]\s+f=(\d+)\s+nmiEn=(\d+)\s+resume=([0-9A-F]{6})\s+inidisp=([0-9A-F]{2})\s+"
    r"cpu=(\d+)\s+master=(\d+)\s+pad=([0-9A-F]{4})\s+r4200=([0-9A-F]{2})\s+"
    r"hIrq=(\d+)\s+vIrq=(\d+)\s+irq=(\d+)\s+nmi=(\d+)\s+vTimer=(\d+)\s+"
    r"E4=([0-9A-F]{4})\s+DA=([0-9A-F]{2})\s+AFB=([0-9A-F]{2})\s+AFD=([0-9A-F]{4})\s+"
    r"D01=([0-9A-F]{2})\s+DB=([0-9A-F]{2})\s+PB=([0-9A-F]{2})\s+DP=([0-9A-F]{4})\s+S=([0-9A-F]{4})"
)

TRACE_HDR = ["fr", "in", "pin", "btn", "master", "cyc", "pc", "a", "x", "y", "sp", "d", "db",
             "p", "bright", "bg", "scan", "ppufr", "hc", "r2140", "w2140", "spcw", "ini",
             "kon", "konf", "spcpc", "spca", "spcx", "spcy", "spcsp", "spcps",
             "r4212", "sdnmi", "sw4200"]


def load_ours(path):
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "[fstate]" not in line:
                continue
            m = FSTATE.search(line)
            if not m:
                continue
            g = m.groups()
            out.append(dict(
                host=int(g[0]), nmiEn=int(g[1]), resume=int(g[2], 16), inidisp=int(g[3], 16),
                cpu=int(g[4]), master=int(g[5]), pad=int(g[6], 16), r4200=int(g[7], 16),
                hIrq=int(g[8]), vIrq=int(g[9]), irq=int(g[10]), nmi=int(g[11]),
                vTimer=int(g[12]), AFB=int(g[14], 16), DB=int(g[17], 16), PB=int(g[18], 16),
                DP=int(g[19], 16), S=int(g[20], 16),
            ))
    out.sort(key=lambda r: r["master"])
    return out


def load_trace(path, lo, hi):
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) < 34 or not parts[0].strip().isdigit():
                continue
            fr = int(parts[0])
            if fr < lo or fr > hi:
                continue
            try:
                rows.append(dict(
                    fr=fr, mask_in=int(parts[1] or 0, 16), pin=parts[2].strip(),
                    master=int(parts[4]), pc=int(parts[6], 16), db=int(parts[12] or 0, 16),
                    hc=int(parts[18] or 0), w2140=int(parts[20] or 0), kon=int(parts[23] or 0),
                ))
            except ValueError:
                continue
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fstate", required=True)
    ap.add_argument("--trace", required=True)
    ap.add_argument("--desde", type=int, default=1)
    ap.add_argument("--hasta", type=int, default=30000)
    ap.add_argument("--ventana", type=int, default=6)
    ap.add_argument("--simular", default="",
                    help="guion de entrada a simular sobre este log (sin recompilar)")
    a = ap.parse_args()

    ours = load_ours(a.fstate)
    if not ours:
        print("ERROR: no hay lineas [fstate] en %s" % a.fstate)
        return 1
    keys = [r["master"] for r in ours]
    print("nuestro: %d muestras [fstate], master %.0f .. %.0f (%.1f frames de master)"
          % (len(ours), ours[0]["master"], ours[-1]["master"],
             (ours[-1]["master"] - ours[0]["master"]) / MASTER_PER_FRAME))

    tr = load_trace(a.trace, a.desde, a.hasta)
    print("hardware: %d filas (%d..%d), master %.0f .. %.0f (%.1f frames de master)"
          % (len(tr), tr[0]["fr"], tr[-1]["fr"], tr[0]["master"], tr[-1]["master"],
             (tr[-1]["master"] - tr[0]["master"]) / MASTER_PER_FRAME))
    print("diferencia de frames de master entre ambos extremos: %.1f"
          % (((ours[-1]["master"] - ours[0]["master"]) / MASTER_PER_FRAME)
             - ((tr[-1]["master"] - tr[0]["master"]) / MASTER_PER_FRAME)))

    # --- pad: comparar por master, con tolerancia de medio frame ---
    def nearest(master):
        i = bisect.bisect_left(keys, master)
        cand = [j for j in (i - 1, i, i + 1) if 0 <= j < len(ours)]
        if not cand:
            return None
        j = min(cand, key=lambda k: abs(keys[k] - master))
        return ours[j], abs(keys[j] - master)

    pad_mismatch, pc_mismatch, db_mismatch = [], [], []
    for r in tr:
        got = nearest(r["master"])
        if got is None:
            continue
        o, d = got
        if d > MASTER_PER_FRAME // 2:      # sin muestra cerca: no es comparable
            continue
        # mascara efectiva de hardware: la del poll si existe, si no la de fin de frame
        hw = r["mask_in"]
        if r["pin"]:
            try:
                hw = int(r["pin"], 16)
            except ValueError:
                pass
        if o["pad"] != hw:
            pad_mismatch.append((r, o, hw))
        if (o["resume"] >> 16) != (r["pc"] >> 16):
            pc_mismatch.append((r, o))
        if o["DB"] != r["db"]:
            db_mismatch.append((r, o))

    def resumen(nombre, lst, campos):
        print("\n=== %s: %d de %d frames comparables ===" % (nombre, len(lst), len(tr)))
        if lst:
            print("  primer caso: frame de hardware %d" % lst[0][0]["fr"])
        return lst

    resumen("pad entregado != pad de hardware", pad_mismatch, None)
    resumen("banco de PC distinto", pc_mismatch, None)
    resumen("banco de datos distinto", db_mismatch, None)

    def contexto(lst, etiqueta, filas=8):
        if not lst:
            return
        r0 = lst[0][0]["fr"]
        print("\n--- contexto %s (hardware %d..%d) ---" % (etiqueta, r0 - filas, r0 + filas))
        print("  hw_fr  hw_pad  hw_pc   hw_db | nuestro: host_f  pad    resume db  (delta master)")
        for rr in tr:
            if r0 - filas <= rr["fr"] <= r0 + filas:
                got = nearest(rr["master"])
                if got is None:
                    continue
                o, d = got
                hw = int(rr["pin"], 16) if rr["pin"] else rr["mask_in"]
                print("  %6d  %04X  %06X  %02X   | f=%6d %04X  %06X %02X  %+d"
                      % (rr["fr"], hw, rr["pc"], rr["db"], o["host"], o["pad"],
                         o["resume"], o["DB"], int(d)))

    contexto(pad_mismatch, "primer desajuste de pad")
    contexto(pc_mismatch, "primer cambio de banco de PC")
    contexto(db_mismatch, "primer cambio de banco de datos")

    # --- desplazamiento sistematico de la entrada --------------------------
    # Emparejamos por master: nuestra muestra cuyo master cae en el frame fr
    # de hardware (residuo < medio frame) imprime la mascara que el invitado
    # leyo en ese frame. Si el guion keyea cada evento al master del FINAL del
    # frame del cambio, la transicion solo entra en vigor al siguiente inicio
    # de frame: eso es un desplazamiento de +1 frame. Aqui se mide el
    # desplazamiento s que maximiza el acuerdo contra in(fr+s).
    pad_por_fr, in_por_fr = {}, {}
    for r in tr:
        in_por_fr[r["fr"]] = r["mask_in"]
        got = nearest(r["master"])
        if got and got[1] <= MASTER_PER_FRAME // 4:
            pad_por_fr[r["fr"]] = got[0]["pad"]
    cerca = [fr for fr in in_por_fr
             if in_por_fr.get(fr) != in_por_fr.get(fr - 1) or in_por_fr.get(fr) != in_por_fr.get(fr + 1)]
    print("\n--- desplazamiento de la entrada (s: comparamos nuestro pad contra in(fr+s)) ---")
    print("  s = 0 correcto; s > 0 => entregamos las pulsaciones s frames TARDE")

    # Simulacion del cargador del motor sobre este mismo log: la mascara del
    # frame que va a ejecutar se elige con la clave = master AL INICIO de ese
    # frame (para nuestra muestra i, el master de la muestra i-1, porque los
    # frames son contiguos en el reloj). Con --simular se reproduce un guion
    # sin recompilar nada y se ve el desplazamiento que produce.
    if a.simular:
        ev = []
        with open(a.simular, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                ev.append((int(parts[0]), int(parts[1], 16)))
        ev.sort()
        ekeys = [e[0] for e in ev]
        print("\n--- simulacion del guion %s (%d eventos) ---"
              % (a.simular.split("/")[-1].split("\\")[-1], len(ev)))

        def sim_mask(key):
            i = bisect.bisect_right(ekeys, key) - 1
            return ev[i][1] if i >= 0 else 0

        hw_keys = [r["master"] for r in tr]
        hw_frs = [r["fr"] for r in tr]
        sim = {}
        for i in range(1, len(ours)):
            o = ours[i]
            j = bisect.bisect_left(hw_keys, o["master"])
            cand = [k for k in (j - 1, j) if 0 <= k < len(hw_keys)]
            if not cand:
                continue
            k = min(cand, key=lambda k: abs(hw_keys[k] - o["master"]))
            if abs(hw_keys[k] - o["master"]) > MASTER_PER_FRAME // 4:
                continue          # durante un fast-forward no hay frame equiparable
            sim[hw_frs[k]] = sim_mask(ours[i - 1]["master"])
        print("  muestras simuladas: %d" % len(sim))
        for s in range(-2, 3):
            tot = ok = tota = oka = 0
            for fr, p in sim.items():
                hw = in_por_fr.get(fr + s)
                if hw is None:
                    continue
                tot += 1
                ok += (p == hw)
                if fr in cerca:
                    tota += 1
                    oka += (p == hw)
            print("  s=%+d: todos %5d/%5d (%5.2f%%)   |  frames de cambio %4d/%4d (%5.2f%%)"
                  % (s, ok, tot, 100.0 * ok / max(tot, 1), oka, tota, 100.0 * oka / max(tota, 1)))
    for s in range(-3, 4):
        tot = ok = tota = oka = 0
        for fr, p in pad_por_fr.items():
            hw = in_por_fr.get(fr + s)
            if hw is None:
                continue
            tot += 1
            ok += (p == hw)
            if fr in cerca:
                tota += 1
                oka += (p == hw)
        print("  s=%+d: todos %5d/%5d (%5.2f%%)   |  frames de cambio %4d/%4d (%5.2f%%)"
              % (s, ok, tot, 100.0 * ok / max(tot, 1), oka, tota, 100.0 * oka / max(tota, 1)))

    # --- perfil de desajustes por tramo de 1000 frames (donde empieza a fallar) ---
    # --- perfil de desajustes por tramo de 1000 frames (donde empieza a fallar) ---
    if pad_mismatch or pc_mismatch:
        print("\n--- desajustes por tramo de 1000 frames (hasta el primero) ---")
        for base in range(0, max(r[0]["fr"] for r in (pad_mismatch + pc_mismatch)) + 1000, 1000):
            p = sum(1 for r, _, _ in pad_mismatch if base <= r["fr"] < base + 1000)
            c = sum(1 for r, _ in pc_mismatch if base <= r["fr"] < base + 1000)
            if p or c:
                print("  %6d-%6d  pad=%4d  pc=%.0f" % (base, base + 999, p, c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
