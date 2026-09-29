#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Comprobacion estatica de un .lua pensado para Mesen (sin interprete Lua local).

No sustituye a un interprete Lua, pero detecta los fallos que ya nos costaron
dias de trabajo perdido:
  * `/* */` (comentario de C): Lua NO lo soporta y el script entero deja de
    compilar, en silencio.  Fue el fallo original de mesen_intro_probe.lua.
  * `//` y `;` en posiciones raras.
  * desbalance de bloques (function/if/for/while/do/repeat vs end/until).
  * parentesis, corchetes y llaves desbalanceados.
  * caracteres no ASCII (los ficheros de Mesen se cargan como bytes; mejor
    mantenerlos ASCII puros para no depender de la codificacion del editor).

Uso: python tools/lua_balance.py fichero.lua [otro.lua ...]
"""
import re, sys


def strip(src):
    """Quita comentarios y contenidos de cadena, respetando el orden."""
    src = re.sub(r"--\[\[.*?\]\]", "", src, flags=re.S)
    src = re.sub(r"--[^\n]*", "", src)
    src = re.sub(r'"(?:\\.|[^"\\])*"', '""', src)
    src = re.sub(r"'(?:\\.|[^'\\])*'", "''", src)
    return src


def check(fn):
    raw = open(fn, encoding="utf-8", errors="replace").read()
    src = strip(raw)
    problems = []

    # 1) comentarios estilo C (fuera de cadenas: hay que mirar el crudo)
    for pat, why in ((r"/\*", "comentario /* de C (Lua no lo soporta)"),
                     (r"\*/", "cierre */ de C"),
                     (r"//[^\n]*", "comentario // de C")):
        for m in re.finditer(pat, raw):
            # // dentro de una URL o un path no es un comentario; lo unico que
            # hay en este arbol son paths con una sola barra
            line = raw[:m.start()].count("\n") + 1
            problems.append("L%-4d %s" % (line, why))

    # 2) balance de bloques
    kw = {k: len(re.findall(r"\b%s\b" % k, src))
          for k in ("function", "if", "for", "while", "do", "repeat", "end",
                    "until")}
    opens = (kw["function"] + kw["if"] + kw["for"] + kw["while"] + kw["repeat"]
             + max(0, kw["do"] - kw["for"] - kw["while"]))
    ends = kw["end"] + kw["until"]
    if opens != ends:
        problems.append("bloques desbalanceados: open=%d end=%d" % (opens, ends))

    # 3) parentesis / corchetes / llaves
    for o, c, name in (("(", ")", "parentesis"), ("[", "]", "corchetes"),
                       ("{", "}", "llaves")):
        if src.count(o) != src.count(c):
            problems.append("%s desbalanceados: %d vs %d" % (name, src.count(o), src.count(c)))

    # 4) no ASCII
    for i, line in enumerate(raw.split("\n"), 1):
        bad = [ch for ch in line if ord(ch) > 126]
        if bad:
            problems.append("L%-4d no-ASCII: %s" % (i, "".join(sorted(set(bad)))))

    # 5) avisos utiles (no bloquean)
    notes = []
    if re.search(r"^local function try", raw) and raw.find("local function try") > raw.find("local function status"):
        notes.append("status() se declara antes que try(): no puede usar try() dentro (un local no se ve hacia arriba)")

    return kw, problems, notes


def asciisafe(s):
    """La consola de Windows es cp1252: nunca dejar que un acento la tumbe."""
    return s.encode("ascii", "backslashreplace").decode("ascii")


def main():
    bad = 0
    for fn in sys.argv[1:]:
        kw, problems, notes = check(fn)
        if problems:
            bad = 1
        print("%-44s open=%-4d end=%-4d  %s" % (
            fn, kw["function"] + kw["if"] + kw["for"] + kw["while"] + kw["repeat"],
            kw["end"] + kw["until"], "OK" if not problems else "PROBLEMAS"))
        for p in problems:
            print(asciisafe("    ! %s" % p))
        for n in notes:
            print(asciisafe("    ~ %s" % n))
    return bad


if __name__ == "__main__":
    sys.exit(main())
