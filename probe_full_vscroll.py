#!/usr/bin/env python3
"""Dump ALL per-line PPU scrolls at the name screen, save to JSON."""
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
p, sock, logf = launch_and_drive(EXE, ROM, log_path=os.path.join(BASE, "build-trace", "vscroll_probe.log"))

try:
    for i in range(400):
        st = cmd(sock, "get_ppu_state")
        try:
            d = json.loads(st)
            mode, inidisp = d.get("bgmode"), d.get("inidisp")
        except Exception:
            mode = inidisp = None
        if mode == 0 and inidisp not in ("0x00", "0x80"):
            break
        time.sleep(0.1)
    # let it settle a few frames
    for _ in range(10):
        cmd(sock, "step_frame")
    time.sleep(0.4)
    lines = json.loads(cmd(sock, "ppu_lines 0 224"))
    out = {}
    for ln in lines.get("lines", []):
        out[ln["line"]] = {"v": ln["v"], "h": ln["h"], "en": ln["enabled"]}
    with open(os.path.join(BASE, "build-trace", "ppu_lines_full.json"), "w") as f:
        json.dump(out, f)
    print("saved ppu_lines_full.json with %d lines" % len(out))
finally:
    sock.close()
    kill_tree(p)
    logf.close()
