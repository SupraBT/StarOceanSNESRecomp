#!/usr/bin/env python3
"""Dump VRAM + CGRAM from the history ring at the newest (fully populated)
name screen frame, using the regression_test.py logic."""
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

def parse_hex_blob(resp):
    try:
        return bytes.fromhex(json.loads(resp)["hex"])
    except Exception:
        return None

def kill_tree(p):
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, timeout=10)
    try:
        p.kill()
        p.wait(timeout=5)
    except Exception:
        pass

from so_drive import launch_and_drive
p, sock, logf = launch_and_drive(EXE, ROM, log_path=os.path.join(BASE, "build-trace", "cap_pop.log"))

try:
    t0 = time.time()
    entered = False
    entry_t = 0.0
    frame = None
    while True:
        now = time.time() - t0
        if now > 90:
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
            entry_t = now
            print("NAME SCREEN ENTRY t=%.1f" % now)
        if entered:
            blob = parse_hex_blob(cmd(sock, "dump_vram 0x4800 1024"))
            nz = sum(1 for k in range(0, len(blob), 2) if blob[k] | blob[k + 1]) if blob else 0
            waited = now - entry_t
            if nz >= 400 or waited >= 25:
                hist = json.loads(cmd(sock, "history"))
                frame = hist["history"]["newest"]
                print("populated: BG1=%d/1024, ring newest=%d (waited %.1fs)" % (nz, frame, waited))
                break
            if int(waited) % 5 == 0 and int(waited) != int(now - entry_t - 1):
                pass
        time.sleep(0.1)

    if frame is not None and frame >= 0:
        v = parse_hex_blob(cmd(sock, "dump_frame_vram %d 0 65536" % frame))
        c = parse_hex_blob(cmd(sock, "dump_frame_cgram %d" % frame))
        if v and c:
            open(os.path.join(BASE, "build-trace", "verify_replay", "vram_pop.bin"), "wb").write(v)
            open(os.path.join(BASE, "build-trace", "verify_replay", "cgram_pop.bin"), "wb").write(c)
            print("saved vram_pop.bin (%d B) cgram_pop.bin (%d B)" % (len(v), len(c)))
            for name, adr in (("BG1", 0x4800), ("BG2", 0x4C00), ("BG3", 0x5000), ("BG4", 0x5800)):
                d = v[adr:adr + 2048]
                nz = sum(1 for k in range(0, len(d), 2) if d[k] | d[k + 1])
                print("  %s map $%04X: %d/1024 entries" % (name, adr, nz))
finally:
    sock.close()
    kill_tree(p)
    logf.close()
