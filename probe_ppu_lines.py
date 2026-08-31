#!/usr/bin/env python3
"""Probe the name screen PPU state: TM/TS masks, windows, color math,
and per-line enabled masks. Goal: find why the STAR OCEAN lettering
behind the panels is not rendering."""
import json, os, socket, subprocess, sys, time

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
p, sock, logf = launch_and_drive(EXE, ROM, log_path=os.path.join(BASE, "build-trace", "ppu_lines_probe.log"))

try:
    # Wait for name screen (mode 0, screen visible)
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
    print("Name screen detected (mode 0, inidisp=%s)" % inidisp)

    d = json.loads(cmd(sock, "get_ppu_state"))
    print("\n=== PPU STATE (name screen) ===")
    print("  inidisp=%s bgmode=%d bgTileAdr=%s" % (d["inidisp"], d["bgmode"], d["bgTileAdr"]))
    print("  TM (main)  = 0x%02x -> BG1:%d BG2:%d BG3:%d BG4:%d OBJ:%d" % (
        int(d["screenEnabled"][0], 16),
        (int(d["screenEnabled"][0], 16) >> 0) & 1,
        (int(d["screenEnabled"][0], 16) >> 1) & 1,
        (int(d["screenEnabled"][0], 16) >> 2) & 1,
        (int(d["screenEnabled"][0], 16) >> 3) & 1,
        (int(d["screenEnabled"][0], 16) >> 4) & 1))
    print("  TS (sub)   = 0x%02x -> BG1:%d BG2:%d BG3:%d BG4:%d OBJ:%d" % (
        int(d["screenEnabled"][1], 16),
        (int(d["screenEnabled"][1], 16) >> 0) & 1,
        (int(d["screenEnabled"][1], 16) >> 1) & 1,
        (int(d["screenEnabled"][1], 16) >> 2) & 1,
        (int(d["screenEnabled"][1], 16) >> 3) & 1,
        (int(d["screenEnabled"][1], 16) >> 4) & 1))
    print("  windowsel=0x%08x wbgobjlog=0x%04x" % (int(d["windowsel"], 16), int(d["wbgobjlog"], 16)))
    print("  cgwsel=%s cgadsub=%s fixedColor=%s" % (d["cgwsel"], d["cgadsub"], d["fixedColor"]))
    print("  hScroll=%s vScroll=%s" % (d["hScroll"], d["vScroll"]))
    print("  window1=[%s..%s] window2=[%s..%s]" % (d["window1left"], d["window1right"], d["window2left"], d["window2right"]))

    # Per-line state for the whole frame
    lines = json.loads(cmd(sock, "ppu_lines 0 224"))
    print("\n=== PER-LINE (sample every 16 lines + lettering band) ===")
    def mask_str(m):
        m = int(m, 16)
        return "BG1=%d BG2=%d BG3=%d BG4=%d OBJ=%d" % (
            (m >> 0) & 1, (m >> 1) & 1, (m >> 2) & 1, (m >> 3) & 1, (m >> 4) & 1)
    sample = list(range(0, 225, 16)) + list(range(48, 170, 8))
    seen = set()
    for ln in lines.get("lines", []):
        l = ln["line"]
        if l in seen:
            continue
        if l not in sample:
            continue
        seen.add(l)
        en0, en1 = ln["enabled"][0], ln["enabled"][1]
        print("  L%3d: TM[%s] TS[%s] wsel=%s cgad=%s cgw=%s v=[%s] h=[%s]" % (
            l, mask_str(en0), mask_str(en1), ln["windowsel"], ln["cgadsub"],
            ln["cgwsel"], ",".join(map(str, ln["v"])), ",".join(map(str, ln["h"]))))

    # Screenshot of our render
    shot_path = os.path.join(BASE, "build-trace", "ppu_lines_name.bmp").replace("\\", "/")
    cmd(sock, "screenshot %s" % shot_path)
    print("\nScreenshot: %s" % shot_path)
finally:
    sock.close()
    kill_tree(p)
    logf.close()
