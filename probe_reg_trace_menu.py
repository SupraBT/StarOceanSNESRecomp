#!/usr/bin/env python3
"""Trace ALL writes to PPU regs $2100-$210C and $2120-$2133 in our runner
while reaching the populated name screen. Reveals if the game ever writes
BG4SC=$B0 (per bsnes tilemap viewer) or keeps $58."""
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
p, sock, logf = launch_and_drive(EXE, ROM, log_path=os.path.join(BASE, "build-trace", "reg_trace_menu.log"))

try:
    # Arm register traces BEFORE the menu populates: exclude scroll spam
    print(cmd(sock, "trace_reg_reset"))
    print(cmd(sock, "trace_reg 0x210a 0x210a"))
    print(cmd(sock, "trace_reg 0x210c 0x210c"))
    print("trace armed")

    # Wait for populated name screen
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
    print("name screen: mode=%s inidisp=%s" % (mode, inidisp))

    # Give it a few more frames to populate
    for _ in range(15):
        cmd(sock, "step_frame")
    time.sleep(0.5)

    d = json.loads(cmd(sock, "get_ppu_state"))
    print("FINAL bgTileAdr=%s bgXsc=%s" % (d["bgTileAdr"], d["bgXsc"]))

    # Dump register trace
    t = cmd(sock, "get_reg_trace")
    with open(os.path.join(BASE, "build-trace", "menu_regtrace.json"), "w") as f:
        f.write(t)
    try:
        entries = json.loads(t).get("entries", [])
        print("reg trace entries:", len(entries))
        # Summarize unique writes per register
        from collections import Counter
        uniq = Counter()
        for e in entries:
            uniq[(e.get("reg"), e.get("val"))] += 1
        for (reg, val), c in sorted(uniq.items()):
            print("  reg=$%s val=$%s x%d" % (reg, val, c))
    except Exception as ex:
        print("parse error:", ex)
        print(t[:2000])
finally:
    sock.close()
    kill_tree(p)
    logf.close()
