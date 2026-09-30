#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Captura la pantalla por fotograma INVITADO, no por tiempo de host.

El boton "imprimir pantalla" es el comando `screenshot` del servidor de
depuracion (debug_server.c `cmd_screenshot`): copia el buffer de la PPU tal
como se presento. Hace falta un build con SNESRECOMP_ENABLE_TRACE=ON.

El servidor no expone el contador de fotograma (`get_frame` devuelve 0 en
esta build), asi que el numero se toma del log [fstate] que el propio motor
escribe con SNESRECOMP_FRAME_STATE=1: cada linea lleva `f=N`. Se correlaciona
por el final del log en el instante de pedir la captura, con un desfase de
unos pocos fotogramas.

Uso:
    python tools/hm_captura_por_frame.py --n 250 --cada 0.08 --dir build-hm/shots
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import socket
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
EXE = ROOT / "build-hm-tr" / "Release" / "StarOcean.exe"
PORT = 13308
RE_FRAME = re.compile(r"\[fstate\] f=(\d+)")


def conectar(puerto: int, intentos: int = 80) -> socket.socket:
    for _ in range(intentos):
        try:
            s = socket.create_connection(("127.0.0.1", puerto), timeout=2.0)
            s.settimeout(5.0)
            return s
        except OSError:
            time.sleep(0.5)
    raise SystemExit("el puerto %d no abre" % puerto)


def mandar(s: socket.socket, cmd: str) -> str:
    s.sendall((cmd + "\n").encode("ascii", "replace"))
    time.sleep(0.12)
    try:
        return s.recv(65536).decode("utf-8", "replace").strip()
    except socket.timeout:
        return ""


def frame_actual(log: pathlib.Path) -> int:
    try:
        with log.open("rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - 65536))
            return int(RE_FRAME.search(fh.read().decode("utf-8", "replace")).group(1))
    except (OSError, AttributeError):
        return -1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=250)
    ap.add_argument("--cada", type=float, default=0.08)
    ap.add_argument("--dir", default="build-hm/shots")
    ap.add_argument("--frames", type=int, default=40000)
    args = ap.parse_args()

    if not EXE.exists():
        raise SystemExit("falta %s" % EXE)
    out = ROOT / args.dir
    out.mkdir(parents=True, exist_ok=True)
    for viejo in out.glob("*.bmp"):
        viejo.unlink()
    log = out / "fstate.log"

    env = dict(os.environ)
    env.update({
        "SNESRECOMP_FRAME_STATE": "1",
        "SNESRECOMP_EXIT_AT_FRAME": str(args.frames),
        "SNESRECOMP_LLE_BOUNCE": "1",
        "SNESRECOMP_REPLAY_FILE": str(HERE / "input_scripts" / "mesen_master.txt"),
        "SNESRECOMP_REPLAY_CLOCK": "master", "SNESRECOMP_HUD": "1",
    })
    fh = log.open("w")
    proc = subprocess.Popen([str(EXE)], cwd=str(EXE.parent), env=env,
                            stdout=subprocess.DEVNULL, stderr=fh)
    try:
        s = conectar(PORT)
        vistos = set()
        for _ in range(args.n):
            time.sleep(args.cada)
            f = frame_actual(log)
            destino = out / ("f%06d.bmp" % f)
            if destino in vistos:
                continue
            mandar(s, "screenshot %s" % destino)
            vistos.add(destino)
        s.close()
        fh.flush()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
        fh.close()
    print("capturas en %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
