#!/usr/bin/env python3
"""Capture screenshot + ring VRAM/CGRAM at the SAME populated frame."""
import json
import os
import socket
import subprocess
import time

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


def cmd(sock, line, timeout=60):
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
p, sock, logf = launch_and_drive(EXE, ROM, log_path=os.path.join(BASE, "build-trace", "same_frame.log"))

try:
    t0 = time.time()
    entered = False
    while True:
        if time.time() - t0 > 90:
            print("TIMEOUT")
            break
        st = cmd(sock, "get_ppu_state")
        try:
            d = json.loads(st)
            mode, tileadr, inidisp = d.get("bgmode"), d.get("bgTileAdr"), d.get("inidisp")
        except Exception:
            mode = tileadr = inidisp = None
        if not entered and mode == 0 and tileadr == "0x4222" and inidisp != "0x00":
            entered = True
        if entered:
            blob = bytes.fromhex(json.loads(cmd(sock, "dump_vram 0x4800 1024"))["hex"])
            nz = sum(1 for k in range(0, len(blob), 2) if blob[k] | blob[k + 1])
            if nz >= 400:
                # screenshot NOW, then ring frame
                shot = os.path.join(BASE, "build-trace", "same_frame.bmp").replace("\\", "/")
                cmd(sock, "screenshot %s" % shot)
                hist = json.loads(cmd(sock, "history"))
                frame = hist["history"]["newest"]
                v = bytes.fromhex(json.loads(cmd(sock, "dump_frame_vram %d 0 65536" % frame))["hex"])
                c = bytes.fromhex(json.loads(cmd(sock, "dump_frame_cgram %d" % frame))["hex"])
                open(os.path.join(BASE, "build-trace", "verify_replay", "vram_sf.bin"), "wb").write(v)
                open(os.path.join(BASE, "build-trace", "verify_replay", "cgram_sf.bin"), "wb").write(c)
                print("captured frame %d (BG1=%d/1024)" % (frame, nz))
                break
        time.sleep(0.1)
finally:
    sock.close()
    kill_tree(p)
    logf.close()
