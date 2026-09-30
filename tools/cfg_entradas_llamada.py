#!/usr/bin/env python3
"""cfg de banco desde DESTINOS DE LLAMADA cruzados con lo que se ejecuta.

Por que existe: los bancos `$C2`-`$CC` no tenian ningun cfg declarado y suman el
~31 % del trabajo interpretado (ENCICLOPEDIA 33.2). Dos intentos anteriores
fallaron por el mismo motivo, y conviene no repetirlo:

* declarar los *destinos sin cuerpo* que el manifiesto nombra
  (`tools/aot_seeds.py`): 0 nodos convertidos, el cfg no es la palanca (33.5);
* declarar los PCs **mas calientes** del histograma como entradas: son mitades de
  funcion, y el analizador no puede emitir un cuerpo que empieza a mitad
  (cobertura 0,36 % -> 0,59 %).

Lo que SI funciona es el **inicio de funcion de verdad**. Se obtiene escaneando
la pagina 0 del MMC (`bancos $C0-$CF`, ver `sdd1_mmc_linear` en sdd1.c) buscando
los operandos de `JSR`/`JMP` (mismo banco) y `JSL`/`JML` (banco explicito), y
filtrando por dos cosas: que el byte del destino no sea `0x00`/`0xFF`, y que ese
PC **se ejecute** en el histograma del interprete. El cruce con ejecucion es lo
que quita los falsos positivos de datos que se leen como opcode.

Medido (misma corrida de 6000 frames, mismo toolchain): cobertura de pasos
interpretados cubiertos por C **0,36 % -> 51,33 %** (1.271 nodos, 200 elegibles),
y el A/B byte-exacto contra LLE puro sigue dando **6000/6000 frames identicos**.

Uso:
    python tools/cfg_entradas_llamada.py \
        --hist build-prof/Release/logs/h_full.txt \
        --rom "Star Ocean (Japan).sfc" --cfg-dir config --out-dir out/cfg-calls
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys
from collections import defaultdict


def load_hist(path: pathlib.Path) -> dict[int, int]:
    hist: dict[int, int] = defaultdict(int)
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            cols = line.split()
            if len(cols) != 2:
                continue
            try:
                hist[int(cols[0], 16)] += int(cols[1])
            except ValueError:
                continue
    return hist


def ejecutado(hist, pc24: int, ventana: int = 0x20) -> int:
    lo = pc24 & ~(ventana - 1)
    return sum(n for pc, n in hist.items() if lo <= pc <= lo + ventana)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", required=True)
    ap.add_argument("--hist", required=True, help="histograma del interprete (perfil_interp.py)")
    ap.add_argument("--cfg-dir", required=True, help="dir con los cfg ya existentes (se copian)")
    ap.add_argument("--out-dir", required=True, help="dir de cfg de salida")
    ap.add_argument("--bancos", default="",
                    help="bancos a sembrar (hex, separados por coma). Vacio = 'sin cfg'")
    args = ap.parse_args()

    rom = pathlib.Path(args.rom).read_bytes()
    page0 = rom[:0x100000]          # bancos $C0-$CF = pagina 0 del MMC
    hist = load_hist(pathlib.Path(args.hist))

    cfg_dir = pathlib.Path(args.cfg_dir)
    ya = {f.stem.lower().replace("bank", "") for f in cfg_dir.glob("bank*.cfg")}
    if args.bancos:
        interes = {int(b, 16) for b in args.bancos.split(",") if b}
    else:
        # Bancos con trabajo interpretado propio y sin cfg declarado.
        interes = {b for b in range(0xC0, 0xD0) if "%02x" % b not in ya}

    cand: dict[int, set[int]] = defaultdict(set)
    for off in range(len(page0) - 4):
        banco = 0xC0 + (off >> 16)
        op = page0[off]
        if op in (0x20, 0x4C):
            cand[banco].add(page0[off + 1] | (page0[off + 2] << 8))
        elif op in (0x22, 0x5C):
            cand[page0[off + 3]].add(page0[off + 1] | (page0[off + 2] << 8))

    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for f in cfg_dir.iterdir():
        if f.is_file():
            (out / f.name).write_bytes(f.read_bytes())

    total_entradas = 0
    for banco in sorted(interes):
        entradas = []
        for t in sorted(cand.get(banco, ())):
            if not (0 <= banco - 0xC0 < (len(page0) >> 16)):
                continue
            if page0[((banco - 0xC0) << 16) | t] in (0x00, 0xFF):
                continue
            n = ejecutado(hist, (banco << 16) | t)
            if n:
                entradas.append((t, n))
        if not entradas:
            continue
        entradas.sort(key=lambda e: -e[1])
        total_entradas += len(entradas)
        lineas = [
            "# banco $%02X sin cfg declarado." % banco,
            "# Entradas = destinos de JSR/JMP (mismo banco) y JSL/JML (banco explicito)",
            "# en la pagina 0 del MMC, que ADEMAS se ejecutan en el histograma.",
            "# Sin `end:`: el analizador descubre la extension hasta el terminador.",
            "bank = 0x%02X" % banco,
            "",
        ]
        for t, n in entradas:
            lineas.append("func Call_%02X%04X %04X   # %d pasos interpretados"
                          % (banco, t, t, n))
        (out / ("bank%02X.cfg" % banco)).write_text("\n".join(lineas) + "\n", encoding="utf-8")
        print("banco $%02X: %d entradas" % (banco, len(entradas)))

    print("\n%d entradas en %d bancos -> %s" % (total_entradas, len(interes), out))
    print("siguiente paso: emitir con --cfg-dir %s y pasar la puerta A/B "
          "(SNESRECOMP_LLE_BOUNCE=1 vs 0, tools/ab_lle.py)" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
