#!/usr/bin/env python3
"""Dump full PPU state (windows, TM/TS, color math) at the name screen."""
import json, os, socket, subprocess, time

BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2"
PORT = 13308
EXE = os.path.join(BASE, "build-trace", "StarOcean.exe")
ROM = os.path.join(BASE, "build-trace", "Star Ocean (Japan).sfc")
LOG = os.path.join(BASE, "so_inputs.log")

def connect(retries=60):
    for _ in range(retries):
        try:
            return socket.create_connection(("127.0.0.1", PORT), timeout=2)
        except OSError:
            time.sleep(0.25)
    return None

def cmd(sock, line, timeout=30):
    sock.sendall((line + "\n").encode())
    sock.settimeout(timeout)
    buf = b""
    while not buf.endswith(b"}\n"):
        try:
            chunk = sock.recv(1 << 20)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
    return buf.decode("utf-8", errors="replace").strip()

def kill_tree(p):
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, timeout=10)
    try:
        p.kill()
        p.wait(timeout=5)
    except Exception:
        pass

from so_drive import launch_and_drive
p, sock, logf = launch_and_drive(EXE, ROM, log_path=os.path.join(BASE, "build-trace", "win_probe.log"))
try:
    t0 = time.time()
    entered = False
    while time.time() - t0 < 90:
        st = cmd(sock, "get_ppu_state")
        try:
            d = json.loads(st)
            mode, tileadr, inidisp = d.get("bgmode"), d.get("bgTileAdr"), d.get("inidisp")
        except Exception:
            d, mode = {}, None
        if mode == 0 and tileadr == "0x4222" and inidisp == "0x0f":
            entered = True
        if entered:
            blob = bytes.fromhex(json.loads(cmd(sock, "dump_vram 0x9000 1024"))["hex"])
            nz = sum(1 for k in range(0, len(blob), 2) if blob[k] | blob[k + 1])
            if nz >= 400:
                break
        time.sleep(0.1)
    print("=== get_ppu_state ===")
    for k, v in d.items():
        print("%-24s %s" % (k, v))
finally:
    sock.close()
    kill_tree(p)
    logf.close()
