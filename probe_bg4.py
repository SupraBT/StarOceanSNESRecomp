#!/usr/bin/env python3
"""Check BG4 tilemap/tile registers at the name screen and whether VRAM at
$B000/$8000 holds the STAR OCEAN lettering (per bsnes tilemap viewer)."""
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
p, sock, logf = launch_and_drive(EXE, ROM, log_path=os.path.join(BASE, "build-trace", "bg4_probe.log"))

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
    print("name screen: mode=%s inidisp=%s" % (mode, inidisp))
    d = json.loads(cmd(sock, "get_ppu_state"))
    print("bgTileAdr=%s bgXsc=%s" % (d["bgTileAdr"], d["bgXsc"]))
    print("screenEnabled=%s" % d["screenEnabled"])

    # Derive map/tile for each BG
    ta = int(d["bgTileAdr"], 16)
    for bg in range(4):
        tiles = ((ta >> (bg * 4)) & 0xF) << 12
        mp = (int(d["bgXsc"][bg], 16) & 0xFC) << 8
        print("BG%d: tiles @$%04X map @$%04X" % (bg + 1, tiles, mp))

    # Dump VRAM at $B000 (map) and $8000 (tiles)
    v = cmd(sock, "dump_vram 0xB000 0x800")
    with open(os.path.join(BASE, "build-trace", "vram_b000.bin"), "wb") as f:
        f.write(bytes.fromhex(v.split('"')[-2] if '"' in v else ""))
    v2 = cmd(sock, "dump_vram 0x8000 0x800")
    with open(os.path.join(BASE, "build-trace", "vram_8000.bin"), "wb") as f:
        f.write(bytes.fromhex(v2.split('"')[-2] if '"' in v2 else ""))
    print("dumped vram_b000.bin (%d B) and vram_8000.bin" % len(v) // 2)

    # Count nonzero map entries at $B000
    data = open(os.path.join(BASE, "build-trace", "vram_b000.bin"), "rb").read()
    nz = sum(1 for i in range(0, len(data), 2) if data[i] | data[i + 1])
    print("map $B000 nonzero entries: %d / %d" % (nz, len(data) // 2))
finally:
    sock.close()
    kill_tree(p)
    logf.close()
