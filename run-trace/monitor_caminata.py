#!/usr/bin/env python3
"""Monitor live caminata. Launches exe with replay and polls frame.
User can type 'dump' at any time to capture the audio ring buffer."""
import json, os, socket, subprocess, sys, time

WORK = r"F:\StarOceanRecompRAID\run-trace"
EXE = os.path.join(WORK, "StarOcean.exe")
REPLAY = os.path.join(WORK, "replay_3_peleas.txt")
HOST, PORT = "127.0.0.1", 13308

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

dump_count = 0

def dump_ring(label=""):
    global dump_count
    dump_count += 1
    fname = "live_dump_%02d.wav" % dump_count
    path = os.path.join(WORK, fname).replace("\\", "/")
    r = send_cmd("audio_wav %s -1 0" % path)
    print(">>> DUMP #%d -> %s | frame ~%d | %s" % (dump_count, fname, get_frame(), r), flush=True)
    return path

def main():
    env = dict(os.environ)
    env["SNESRECOMP_REPLAY_FILE"] = REPLAY
    env["SNESRECOMP_REPLAY_UP_PAUSE_MS"] = "0"

    proc = subprocess.Popen([EXE], cwd=WORK, env=env)
    print("Exe launched. Waiting for debug server...", flush=True)
    time.sleep(3)

    print("Monitoring caminata. Commands:", flush=True)
    print("  'd' = dump ring buffer to WAV", flush=True)
    print("  'q' = quit", flush=True)
    print("  (just press Enter to see current frame)", flush=True)

    try:
        while True:
            f = get_frame()
            if f < 0:
                if proc.poll() is not None:
                    print("exe exited (rc=%s)" % proc.returncode)
                    break
                time.sleep(1)
                continue

            sys.stdout.write("frame=%d> " % f)
            sys.stdout.flush()

            try:
                cmd = input().strip()
            except EOFError:
                break

            if cmd in ("d", "dump"):
                dump_ring()
            elif cmd in ("q", "quit", "exit"):
                break

            if proc.poll() is not None:
                print("exe exited (rc=%s)" % proc.returncode)
                break
    finally:
        if proc.poll() is None:
            proc.kill()
    print("Done. %d dumps captured." % dump_count)

if __name__ == "__main__":
    main()
