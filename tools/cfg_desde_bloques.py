#!/usr/bin/env python3
"""cfg de banco a partir de un mapa de BLOQUES MEDIDOS (Ghidra), no a ojo.

Por que existe: `config/bankC0.cfg` declara 20 funciones de exactamente 0x200 en
0x200 (`0400 end:0600`, `0600 end:0800`, ...), que no es un mapa de nada; 18 de
las 19 declaradas no se ejecutan nunca (ENCICLOPEDIA 32.2 y 33.4). Mientras
tanto, el codigo que `C0` ejecuta de verdad esta medido: el mapa de bloques de
Ghidra trae, por bloque, inicio, ultima instruccion, fin exclusivo, numero de
instrucciones, ejecuciones y terminador (RTS/RTL/RTI).

Medido el 2026-09-30 con el mismo toolchain y la misma corrida: cambiar el cfg
inventado por uno generado desde los bloques medidos multiplica por 6,8 los
pasos interpretados cubiertos por C (0,36 % -> 2,46 %) usando MENOS entradas.

Uso:
    python tools/cfg_desde_bloques.py --bloques <c0_bloques.json> --banco C0 \
        --conservar config/bankC0.cfg --out out/cfg-ghidra/bankC0.cfg

`--conservar` copia directivas del cfg anterior que SI tienen evidencia
(exclude_range, force_lle, name, ...). Ojo con force_lle: conservarlo es lo que
mas cobertura destruye (2,46 % -> 0,12 % en `$C0`), asi que el script avisa del
efecto en vez de copiarlo en silencio.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

CONSERVABLES = ("exclude_range", "force_lle", "name", "entry_mx_at", "end_at")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bloques", required=True, help="JSON: lista de bloques medidos")
    ap.add_argument("--banco", required=True, help="banco en hex, p.ej. C0")
    ap.add_argument("--out", required=True, help="cfg de salida")
    ap.add_argument("--conservar", default=None,
                    help="cfg anterior del que copiar directivas con evidencia")
    ap.add_argument("--sin-force-lle", action="store_true",
                    help="NO conservar force_lle (es lo que mas cobertura cuesta)")
    args = ap.parse_args()

    banco = int(args.banco, 16)
    bloques = json.loads(pathlib.Path(args.bloques).read_text(encoding="utf-8"))

    lineas = [
        "# %s generado desde BLOQUES MEDIDOS (%s)" % (pathlib.Path(args.out).name, args.bloques),
        "# Cada entrada es un bloque con terminador real y ejecuciones medidas:",
        "# no hay rangos inventados.",
        "bank = 0x%02X" % banco,
        "",
    ]
    for fila in bloques:
        ini, _ultima, fin, n_instr, ejec, terminador = fila[:6]
        lineas.append("func Ghidra_%s %s end:%s   # %d instr, %s ejec, termina en %s"
                      % (ini, ini, fin, n_instr, ejec, terminador))

    if args.conservar:
        evid = []
        for linea in pathlib.Path(args.conservar).read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(%s)\b" % "|".join(CONSERVABLES), linea)
            if not m:
                continue
            if args.sin_force_lle and m.group(1) == "force_lle":
                continue
            evid.append(linea.rstrip())
        if any(l.startswith("force_lle") for l in evid):
            print("AVISO: se conservan las lineas force_lle. Medido en $C0: pasan la "
                  "cobertura de 2.46%% a 0.12%% porque clavan al interprete los bloques "
                  "calientes. Usa --sin-force-lle para medir el efecto.", file=sys.stderr)
        lineas += ["", "# --- directivas con evidencia conservadas de %s ---" % args.conservar]
        lineas += evid

    salida = pathlib.Path(args.out)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("%s: %d bloques -> %s" % (salida.name, len(bloques), salida))
    print("siguiente paso: emitir con --cfg-dir <dir del cfg> y medir cobertura "
          "con tools/trabajo_aot.py --hist")
    return 0


if __name__ == "__main__":
    sys.exit(main())
