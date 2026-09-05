#!/usr/bin/env python3
"""Graba audio WAV de dos zonas de la caminata usando el exe existente.
El exe tiene un debug server TCP (port 13308) con comando 'audio_wav'
que vuelca el ring buffer de audio a un archivo WAV.

Zonas:
  A: f5015..f7589  (chasquidos, sonido cinemática ~f6200)
  B: f9808..f10520 (siempre hay pitidos)
"""
import json, os, socket, subprocess, sys, time

WORK = r"F:\StarOceanRecompRAID\run-trace"
EXE = os.path.join(WORK, "StarOcean.exe")
REPLAY = os.path.join(WORK, "replay_3_peleas.txt")
HOST, PORT = "127.0.0.1", 13308

# Zona A: dumpear cuando llegue a f7589 (el ring tiene ~4000 frames de historia)
# Zona B: dumpear cuando llegue a f10520
DUMP_A_FRAME = 7589
DUMP_B_FRAME = 10520
MAX_FRAME = 11000
POLL_S = 2.0

def send_cmd(cmd, timeout=30):
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
    env["SNESRECOMP_REPLAY_UP_PAUSE_MS"] = "0"
    
    proc = subprocess.Popen([EXE], cwd=WORK, env=env)
    print("Exe lanzado, esperando debug server...", flush=True)
    time.sleep(3)

    dumped = set()
    manifest = {"dumps": []}
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
                wav_a = os.path.join(WORK, "audio_f5015_f7589.wav").replace("\\", "/")
                r = send_cmd("audio_wav %s -1 0" % wav_a)
                print("DUMP A -> %s : %s" % (wav_a, r), flush=True)
                manifest["dumps"].append({"id": "A", "zone": "f5015-f7589", "frame": f, "path": wav_a, "reply": r})

            if f >= DUMP_B_FRAME and "B" not in dumped:
                dumped.add("B")
                wav_b = os.path.join(WORK, "audio_f9808_f10520.wav").replace("\\", "/")
                r = send_cmd("audio_wav %s -1 0" % wav_b)
                print("DUMP B -> %s : %s" % (wav_b, r), flush=True)
                manifest["dumps"].append({"id": "B", "zone": "f9808-f10520", "frame": f, "path": wav_b, "reply": r})
                break  # ambas zonas capturadas, salir

            if f >= MAX_FRAME:
                break
            if proc.poll() is not None:
                print("exe termino (rc=%s)" % proc.returncode)
                break
            time.sleep(POLL_S)
    finally:
        if proc.poll() is None:
            proc.kill()
        mpath = os.path.join(WORK, "capture_manifest.json")
        with open(mpath, "w") as fh:
            json.dump(manifest, fh, indent=1)
        print("Manifest: %s" % mpath)
    print("Captura finalizada. WAVs en %s" % WORK)

if __name__ == "__main__":
    main()
