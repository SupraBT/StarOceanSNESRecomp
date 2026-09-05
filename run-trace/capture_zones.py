#!/usr/bin/env python3
"""Lanza el exe TRACE con la caminata y vuelca el anillo PCM cuando el frame
pasa cada zona de interes. No modifica nada del proyecto: solo escribe WAVs y
un manifest en el directorio de trabajo.

Zonas (frames de la sesion manual del usuario):
  A puente de mando:  f5264 .. f7782   -> dump amplio ~f4400..f8200
  B campo/village:    f10242 .. f10778 -> dump amplio ~f9700..f11400
"""
import json
import os
import socket
import subprocess
import sys
import time

WORK = r"F:\StarOceanRecompRAID\run-trace"
EXE = os.path.join(WORK, "StarOcean.exe")
REPLAY = os.path.join(WORK, "replay_3_peleas.txt")
HOST, PORT = "127.0.0.1", 13308

DUMP_A_FRAME = 8400   # dump 1 cuando el frame supere este valor
DUMP_B_FRAME = 11600  # dump 2 cuando el frame supere este valor
MAX_FRAME = 12500     # punto de corte: matamos el exe al llegar aqui
POLL_S = 3.0


def send_cmd(cmd, timeout=60):
    s = socket.create_connection((HOST, PORT), timeout=timeout)
    s.settimeout(timeout)
    s.sendall((cmd + "\n").encode())
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
    s.close()
    return buf.decode(errors="replace").strip()


def get_frame():
    try:
        line = send_cmd("ping", timeout=10)
        return json.loads(line).get("frame", -1)
    except Exception:
        return -1


def main():
    env = dict(os.environ)
    env["SNESRECOMP_REPLAY_FILE"] = REPLAY
    proc = subprocess.Popen([EXE], cwd=WORK, env=env)
    manifest = {"dumps": [], "zones": {"A": [4400, 8400], "B": [9700, 11600]}}
    dumped = set()
    try:
        while True:
            f = get_frame()
            if f < 0:
                if proc.poll() is not None:
                    print("exe termino (rc=%s)" % proc.returncode)
                    break
                time.sleep(POLL_S)
                continue
            print("frame=%d" % f, flush=True)
            if f >= DUMP_A_FRAME and "A" not in dumped:
                dumped.add("A")
                r = send_cmd("audio_wav %s %d %d" % (
                    os.path.join(WORK, "ring_A.wav").replace("\\", "/"), -1, 0))
                print("DUMP A:", r, flush=True)
                manifest["dumps"].append({"id": "A", "frame": f, "reply": r})
            if f >= DUMP_B_FRAME and "B" not in dumped:
                dumped.add("B")
                r = send_cmd("audio_wav %s %d %d" % (
                    os.path.join(WORK, "ring_B.wav").replace("\\", "/"), -1, 0))
                print("DUMP B:", r, flush=True)
                manifest["dumps"].append({"id": "B", "frame": f, "reply": r})
            if f >= MAX_FRAME and "done" not in dumped:
                dumped.add("done")
                break
            if proc.poll() is not None:
                print("exe termino (rc=%s)" % proc.returncode)
                break
            time.sleep(POLL_S)
    finally:
        if proc.poll() is None:
            proc.kill()
        with open(os.path.join(WORK, "capture_manifest.json"), "w") as fh:
            json.dump(manifest, fh, indent=1)
    print("captura finalizada")


if __name__ == "__main__":
    main()
