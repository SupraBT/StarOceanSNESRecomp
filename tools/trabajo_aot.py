#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lista de trabajo AOT a partir de datos, no de suposiciones.

Fuentes (todas nuestras, ninguna conjetura):

  generated/program_manifest.json  lo que el generador ya decidio por nodo:
        entrada (pc24 + estado m/x), rango (min_pc24..max_pc24),
        instruction_count, `disposition` (native = tiene cuerpo en C,
        lle_only = se queda en el interprete) y `reasons`.
  config/*.cfg                     lo declarado a mano.
  trace de hardware (*_trace.tsv)  los PC que se ejecutan DE VERDAD, un
        muestreo por frame: es la verdad de campo, no nuestro perfil.

Salida: por banco, cuantos nodos hay en C y cuantos en el interprete, el trabajo
que representan, cuanto de lo observado en hardware cae dentro de cada grupo, y
una lista ordenada de nodos `lle_only` por evidencia (muestras observadas en su
rango x instrucciones). Es el orden de promocion, y cada fila lleva su `reason`.

Uso:
  python tools/trabajo_aot.py --trace <trace.tsv> [--top 25]
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load_manifest(path):
    d = json.load(open(path, encoding="utf-8"))
    nodes = []
    for nid, n in d.get("nodes", {}).items():
        k = n.get("key", {})
        pc = k.get("pc24")
        if pc is None:
            continue
        nodes.append(dict(
            id=nid, pc24=int(pc), m=int(k.get("m", 1)), x=int(k.get("x", 1)),
            lo=int(n.get("min_pc24", pc)), hi=int(n.get("max_pc24", pc)),
            instr=int(n.get("instruction_count", 0)),
            disp=n.get("disposition", "?"),
            reasons=",".join(n.get("reasons", []) or []),
        ))
    return nodes, len(d.get("roots", []))


def load_cfg(dirpath):
    """Rangos declarados a mano: `func Nombre inicio end:fin`."""
    out = []
    pat = re.compile(r"^\s*func\s+(\S+)\s+([0-9A-Fa-f]+)\s+end:([0-9A-Fa-f]+)")
    if not os.path.isdir(dirpath):
        return out
    for name in sorted(os.listdir(dirpath)):
        if not name.endswith(".cfg"):
            continue
        bank_m = re.search(r"bank([0-9A-Fa-f]{2})", name, re.I)
        bank = int(bank_m.group(1), 16) if bank_m else None
        for line in open(os.path.join(dirpath, name), encoding="utf-8", errors="replace"):
            m = pat.match(line)
            if not m:
                continue
            out.append((bank, m.group(1), int(m.group(2), 16), int(m.group(3), 16)))
    return out


def load_observed(path, hasta):
    """PC24 muestreado por frame en el trace de hardware -> cuantas veces cada uno."""
    obs = defaultdict(int)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("#"):
                continue
            c = line.rstrip("\r\n").split("\t")
            if len(c) < 7 or not c[0].strip().isdigit():
                continue
            if int(c[0]) > hasta:
                continue
            try:
                obs[int(c[6], 16)] += 1
            except ValueError:
                pass
    return obs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=os.path.join(ROOT, "generated", "program_manifest.json"))
    ap.add_argument("--cfg", default=os.path.join(ROOT, "config"))
    ap.add_argument("--trace", required=True)
    ap.add_argument("--hasta", type=int, default=100000)
    ap.add_argument("--top", type=int, default=25)
    a = ap.parse_args()

    nodes, nroots = load_manifest(a.manifest)
    cfg = load_cfg(a.cfg)
    obs = load_observed(a.trace, a.hasta)
    print("manifiesto: %d nodos, %d raices | cfg: %d funciones declaradas | observado: %d frames con PC (%d PCs distintos)"
          % (len(nodes), nroots, len(cfg), sum(obs.values()), len(obs)))

    # indice por banco: nodos nativos y nodos lle_only
    per_bank = defaultdict(lambda: dict(nat=[], lle=[], instr_nat=0, instr_lle=0))
    for n in nodes:
        b = n["pc24"] >> 16
        e = per_bank[b]
        if n["disp"] in ("native", "aot", "aot_eligible"):
            e["nat"].append(n); e["instr_nat"] += n["instr"]
        else:
            e["lle"].append(n); e["instr_lle"] += n["instr"]

    def covered(pc24, lst):
        for n in lst:
            if n["lo"] <= pc24 <= n["hi"]:
                return True
        return False

    print("\n=== por banco: C generado vs interprete, contra lo que hardware ejecuta ===")
    print("banco  nodos_C  nodos_LLE  instr_C  instr_LLE  muestras_hw  muestras_en_C  cobertura")
    tot_hw = 0
    for b in sorted(set(list(per_bank.keys()) + [p >> 16 for p in obs])):
        e = per_bank.get(b, dict(nat=[], lle=[], instr_nat=0, instr_lle=0))
        hw = [p for p in obs if (p >> 16) == b]
        m_hw = sum(obs[p] for p in hw)
        m_nat = sum(obs[p] for p in hw if covered(p, e["nat"]))
        tot_hw += m_hw
        cob = ("%.1f%%" % (100.0 * m_nat / m_hw)) if m_hw else "-"
        print("%02X     %5d  %8d  %7d  %8d  %11d  %13d  %8s"
              % (b, len(e["nat"]), len(e["lle"]), e["instr_nat"], e["instr_lle"],
                 m_hw, m_nat, cob))

    # lista de trabajo: nodos lle_only por evidencia observada
    filas = []
    for n in nodes:
        if n["disp"] in ("native", "aot", "aot_eligible"):
            continue
        muestras = sum(v for p, v in obs.items() if n["lo"] <= p <= n["hi"])
        filas.append((muestras, n["instr"], n["pc24"], n["hi"], n["id"], n["disp"], n["reasons"]))
    filas.sort(key=lambda r: (-r[0], -r[1]))
    print("\n=== lista de trabajo: nodos que se quedan en el interprete, por evidencia ===")
    print("  PC24   rango            instr  muestras_hw  disposition  reason")
    for muestras, instr, pc, hi, nid, disp, reasons in filas[:a.top]:
        print("  %06X %06X-%06X %6d %11d  %-10s %s"
              % (pc, pc, hi, instr, muestras, disp, reasons[:70]))

    # motivos agrupados: es la parte accionable, porque cada motivo es un
    # bloqueo concreto del generador (no una impresion nuestra).
    porMotivo = defaultdict(lambda: [0, 0, 0])
    for n in nodes:
        if n["disp"] in ("native", "aot", "aot_eligible"):
            continue
        for r in (n["reasons"] or "").split(","):
            if not r:
                continue
            clave = r.split("_", 1)[0] if not r.startswith("unproven_call") else "unproven_call"
            muestras = sum(v for p, v in obs.items() if n["lo"] <= p <= n["hi"])
            e = porMotivo[clave]
            e[0] += 1; e[1] += n["instr"]; e[2] = max(e[2], muestras)
    print("\n=== motivos por los que el generador no emitio C (agrupados) ===")
    print("  motivo                    nodos   instr   max muestras_hw")
    for k in sorted(porMotivo, key=lambda k: -porMotivo[k][2]):
        v = porMotivo[k]
        print("  %-24s %5d %7d %13d" % (k, v[0], v[1], v[2]))

    sinNodo = [(p, v) for p, v in obs.items()
               if not covered(p, nodes) ]
    sinNodo.sort(key=lambda x: -x[1])
    print("\n=== PCs observados en hardware SIN NINGUN nodo en el manifiesto (huecos) ===")
    print("  total: %d PCs distintos, %d muestras (%.1f%% del total observado)"
          % (len(sinNodo), sum(v for _, v in sinNodo),
             100.0 * sum(v for _, v in sinNodo) / max(1, sum(obs.values()))))
    bancos = defaultdict(lambda: [0, 0])
    for p, v in sinNodo:
        bancos[p >> 16][0] += 1
        bancos[p >> 16][1] += v
    for b in sorted(bancos, key=lambda b: -bancos[b][1])[:12]:
        print("    banco %02X: %5d PCs sin nodo, %6d muestras" % (b, bancos[b][0], bancos[b][1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
