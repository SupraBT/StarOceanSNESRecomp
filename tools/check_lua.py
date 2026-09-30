#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validador estructural para los scripts .lua de Mesen.

No hay Lua en esta maquina, asi que un error de sintaxis solo se veria cuando el
usuario lo ejecuta en Mesen, con el script a medias. Esto no es un parser de
Lua: es un contador de bloques y de parentesis que sabe distinguir codigo de
cadenas y comentarios, y que es lo que detecta el fallo que de verdad se cuela
al editar un script a mano (un `end` que falta, una llave desbalanceada).

Uso:
    python tools/check_lua.py tools/mesen_so_probe.lua
"""
from __future__ import annotations

import pathlib
import re
import sys

# Palabras que abren un bloque y necesitan un `end`.
ABRE = {"function", "if", "for", "while", "do"}


def tokeniza(src: str):
    """Devuelve (tokens, errores). Cada token es ('code', txt) o ('str', txt)."""
    i, n = 0, len(src)
    out = []
    line = 1
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
            # El salto de línea ES código: sin él, los números de línea de todo
            # lo que viene después colapsan a 1 y el diagnóstico es inservible.
            out.append(("code", "\n"))
            i += 1
            continue
        # comentario de linea
        if src.startswith("--", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        # cadenas cortas y largas
        if c == '"' or c == "'":
            quote = c
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == "\n":
                    break
                if src[j] == quote:
                    j += 1
                    break
                j += 1
            else:
                raise SyntaxError(f"linea {line}: cadena sin cerrar")
            if j >= n or src[j - 1] != quote:
                raise SyntaxError(f"linea {line}: cadena sin cerrar")
            out.append(("str", src[i:j]))
            i = j
            continue
        if src.startswith("--[[", i):
            j = src.find("]]", i)
            i = n if j < 0 else j + 2
            continue
        m = re.match(r"\[(=*)\[", src[i:])
        if m:
            close = "]" + m.group(1) + "]"
            j = src.find(close, i)
            i = n if j < 0 else j + len(close)
            continue
        out.append(("code", c))
        i += 1
    return out


def comprueba(ruta: pathlib.Path) -> int:
    src = ruta.read_text(encoding="utf-8", errors="replace")
    try:
        toks = tokeniza(src)
    except SyntaxError as e:
        print(f"{ruta}: ERROR {e}")
        return 1

    pila = []          # (palabra, linea)
    prof = []          # parentesis/llaves
    errores = 0
    linea = 1
    idx = 0
    codigo = [(k, t, ) for k, t in toks if k == "code"]

    # reconstruye el codigo concatenado para buscar palabras completas
    texto = "".join(t for k, t in toks if k == "code")
    # posicion -> linea, para decir donde falla
    pos_linea = []
    ln = 1
    for k, t in toks:
        if k == "code":
            for ch in t:
                pos_linea.append(ln)
                if ch == "\n":
                    ln += 1
        else:
            pass

    def linea_de(p):
        return pos_linea[p] if 0 <= p < len(pos_linea) else 0

    pares = {")": "(", "]": "[", "}": "{"}
    for p, ch in enumerate(texto):
        if ch in "([{":
            prof.append((ch, linea_de(p)))
        elif ch in ")]}":
            if not prof:
                print(f"{ruta}:{linea_de(p)}: '{ch}' de mas")
                errores += 1
            else:
                ab, _ = prof.pop()
                if ab != pares[ch]:
                    print(f"{ruta}:{linea_de(p)}: '{ch}' cierra un '{ab}'")
                    errores += 1

    # palabras clave de bloque, en orden
    for m in re.finditer(r"\b(function|if|for|while|do|end|then|else|elseif|repeat|until)\b",
                         texto):
        w = m.group(1)
        if w in ("function", "for", "while", "repeat"):
            pila.append((w, linea_de(m.start())))
        elif w == "do":
            # `do` cierra un for/while ya abierto: no cuenta como bloque nuevo
            if pila and pila[-1][0] in ("for", "while"):
                pass
            else:
                pila.append((w, linea_de(m.start())))
        elif w == "if":
            pila.append((w, linea_de(m.start())))
        elif w == "end":
            if not pila:
                print(f"{ruta}:{linea_de(m.start())}: 'end' sin bloque abierto")
                errores += 1
            else:
                top = pila[-1][0]
                # un `end` cierra el if/function/for/while/do mas reciente
                pila.pop()
        elif w == "until":
            if pila and pila[-1][0] == "repeat":
                pila.pop()
            else:
                print(f"{ruta}:{linea_de(m.start())}: 'until' sin 'repeat'")
                errores += 1

    for ch, l in prof:
        print(f"{ruta}:{l}: '{ch}' sin cerrar")
        errores += 1
    for w, l in pila:
        print(f"{ruta}:{l}: bloque '{w}' sin cerrar (falta 'end')")
        errores += 1

    # `then` sin `if` ni `elseif` en la MISMA linea es un error de gramatica.
    # `elseif ... then` es Lua valido (la cadena entera comparte un `end`, asi
    # que no lleva `if` propio) y se acepta para no dar falsos positivos: dar
    # avisos erroneos hace que el validador se deje de mirar.
    for m in re.finditer(r"\bthen\b", texto):
        desde = texto.rfind("\n", 0, m.start()) + 1
        trozo = texto[desde:m.start()]
        if re.search(r"\bif\b", trozo) or re.search(r"\belseif\b", trozo):
            continue
        print(f"{ruta}:{linea_de(m.start())}: 'then' sin 'if' ni 'elseif'")
        errores += 1

    if errores:
        print(f"{ruta}: {errores} problema(s)")
        return 1
    print(f"{ruta}: estructura correcta "
          f"({len(src.splitlines())} lineas, {len(codigo)} caracteres de codigo)")
    return 0


def main() -> int:
    rc = 0
    for a in sys.argv[1:]:
        rc |= comprueba(pathlib.Path(a))
    return rc


if __name__ == "__main__":
    sys.exit(main())