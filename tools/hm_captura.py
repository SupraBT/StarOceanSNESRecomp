#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Captura la pantalla del recomp por el boton "imprimir pantalla".

El boton es el comando `screenshot` del servidor de depuracion (debug_server.c
`cmd_screenshot`), que copia el buffer de la PPU tal y como se presento en el
ultimo fotograma. Necesita un build con SNESRECOMP_ENABLE_TRACE=ON (puerto
13308); el volcado por variables de entorno (SNESRECOMP_FRAME_BMP) no sirve
porque vive dentro de RtlWidescreenPresent, y a este ejecutable lo usa solo
mmx23_host_main.inc.

Uso:  python tools/hm_captura.py [--n 12] [--cada 0.35] [--dir /tmp/hmshot]
"""
from __future__ import annotations

import argparse
import os
import pathlib
import socket
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
BUILD = ROOT / "build-hm-tr"
EXE = BUILD / "Release" / "StarOcean.exe"
PORT = 13308


def conectar(puerto: int, intentos: int = 60) -> socket.socket:
    ultimo = None
    for _ in range(intentos):
        try:
            s = socket.create_connection(("127.0.0.1", puerto), timeout=2.0)
            s.settimeout(10.0)
            return s
        except OSError as exc:
            ultimo = exc
            time.sleep(0.5)
    raise SystemExit("no abre el puerto %d: %s" % (puerto, ultimo))


def mandar(s: socket.socket, cmd: str) -> str:
    s.sendall((cmd + "\n").encode("ascii", "replace"))
    time.sleep(0.25)
    try:
        return s.recv(65536).decode("utf-8", "replace").strip()
    except socket.timeout:
        return "<sin respuesta>"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--cada", type=float, default=0.35)
    ap.add_argument("--dir", default="/tmp/hmshot")
    ap.add_argument("--frames", type=int, default=4000)
    args = ap.parse_args()

    if not EXE.exists():
        raise SystemExit("falta %s (compila con -DSNESRECOMP_ENABLE_TRACE=ON)" % EXE)
    out = pathlib.Path(args.dir)
    out.mkdir(parents=True, exist_ok=True)
    for viejo in out.glob("*.bmp"):
        viejo.unlink()

    env = dict(os.environ)
    env["SNESRECOMP_EXIT_AT_FRAME"] = str(args.frames)
    env["SNESRECOMP_LLE_BOUNCE"] = "1"
    env["SNESRECOMP_REPLAY_FILE"] = str(HERE / "input_scripts" / "mesen_master.txt")
    env["SNESRECOMP_REPLAY_CLOCK"] = "master"
    env["SNESRECOMP_HUD"] = "1"
    env.pop("SNESRECOMP_TURBO_PRESENT_EVERY", None)

    proc = subprocess.Popen([str(EXE)], cwd=str(BUILD / "Release"), env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        s = conectar(PORT)
        print("conectado al servidor de depuracion (puerto %d)" % PORT)
        for i in range(args.n):
            time.sleep(args.cada)
            estado = mandar(s, "get_frame")
            destino = out / ("f%03d.bmp" % i)
            resp = mandar(s, "screenshot %s" % destino)
            print("[%2d] %-28s -> %s  (%s)" %
                  (i, estado[:28], destino.name, resp[:60]))
        s.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
    print("\ncapturas en %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
