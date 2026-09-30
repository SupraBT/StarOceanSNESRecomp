#!/usr/bin/env python3
"""Semillas de cfg desde el propio manifiesto del generador AOT.

El manifiesto (`generated/program_manifest.json`) trae por nodo `disposition`
(`aot_eligible` / `lle_only`) y `reasons`. Entre los motivos hay uno que NO es
un problema estructural sino una *declaracion que falta*:

    unproven_call_at_<site>_to_<target>_m<m>x<x>

Significa: el nodo llama a `<target>` con M/X = m,x y el analizador no puede
probar el ancho de salida de ese callee, asi que marca el nodo entero como
`lle_only` (sin C generado) aunque su codigo sea perfectamente traducible.

El parser de cfg acepta `func NAME <pc16>` **sin `end:`**, que significa
"decodifica hasta el terminador": declarar el destino como raiz es suficiente
para que el analizador descubra su extension y pruebe su salida.

Este script extrae esos destinos y los escribe como semillas en el cfg de su
banco, en una seccion marcada e idempotente. No toca nada mas del cfg.

Uso:
    python tools/aot_seeds.py --check      # solo informa
    python tools/aot_seeds.py --write      # escribe las semillas
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "generated" / "program_manifest.json"
CFG_DIR = ROOT / "config"
MARK_BEGIN = "# --- semillas autogeneradas (tools/aot_seeds.py): destinos de llamada"
MARK_END = "# --- fin de semillas autogeneradas ---"

REASON = re.compile(
    r"unproven_call_at_([0-9A-F]{6})_to_([0-9A-F]{6})_m(\d)x(\d)")


def cfg_for_bank(bank: int) -> pathlib.Path:
    """Nombre del cfg por banco, siguiendo la convencion del repo."""
    if bank == 0:
        return CFG_DIR / "bank00.cfg"
    return CFG_DIR / ("bank%02X.cfg" % bank)


def strip_old_seeds(text: str) -> str:
    """Quita un bloque de semillas anterior para poder reescribirlo."""
    if MARK_BEGIN not in text:
        return text
    out, keep = [], True
    for line in text.splitlines(keepends=True):
        if line.startswith(MARK_BEGIN):
            keep = False
            continue
        if not keep and line.startswith(MARK_END):
            keep = True
            continue
        if keep:
            out.append(line)
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="escribe las semillas en config/bank*.cfg")
    ap.add_argument("--manifest", default=str(MANIFEST))
    args = ap.parse_args()

    man = json.loads(pathlib.Path(args.manifest).read_text(encoding="utf-8"))
    nodes = man["nodes"]
    it = nodes.values() if isinstance(nodes, dict) else nodes

    # target pc24 -> (m, x) de entrada observados, y quienes lo llaman.
    seeds: dict[str, dict[int, tuple[int, int]]] = {}
    callers: dict[int, set[str]] = {}
    for node in it:
        if not isinstance(node, dict):
            continue
        for reason in node.get("reasons", []):
            hit = REASON.match(reason)
            if not hit:
                continue
            site, target, m, x = hit.group(1), int(hit.group(2), 16), int(hit.group(3)), int(hit.group(4))
            bank = (target >> 16) & 0xFF
            seeds.setdefault(bank, {})[target] = (m, x)
            callers.setdefault(target, set()).add(site)

    if not seeds:
        print("no hay destinos sin cuerpo: nada que declarar")
        return 0

    total = 0
    for bank in sorted(seeds):
        targets = seeds[bank]
        total += len(targets)
        path = cfg_for_bank(bank)
        print("banco $%02X: %d destinos -> %s" % (bank, len(targets), path.name))
        for target in sorted(targets):
            m, x = targets[target]
            sites = ",".join(sorted(callers[target]))
            print("    $%06X  entry_mx:%d,%d  llamado desde %s" % (target, m, x, sites))

        if not args.write:
            continue
        if not path.exists():
            print("    (sin cfg para el banco $%02X: crea el fichero con"
                  " 'bank = 0x%02X' y repite)" % (bank, bank))
            continue
        text = strip_old_seeds(path.read_text(encoding="utf-8"))
        if not text.endswith("\n"):
            text += "\n"
        text += ("\n%s: el analizador no puede probar su salida y por eso el\n"
                 "# llamante entero se queda en el interprete. Sin `end:` el\n"
                 "# analizador decodifica hasta el terminador y descubre la\n"
                 "# extension por si mismo.\n" % MARK_BEGIN)
        for target in sorted(targets):
            m, x = targets[target]
            sites = ",".join(sorted(callers[target]))
            text += ("func Auto_%06X %04X entry_mx:%d,%d"
                     "   # llamado desde %s\n"
                     % (target, target & 0xFFFF, m, x, sites))
        text += MARK_END + "\n"
        path.write_text(text, encoding="utf-8")
        print("    escrito en %s" % path)

    print("\ntotal: %d destinos" % total)
    if not args.write:
        print("(modo --check: nada escrito)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
