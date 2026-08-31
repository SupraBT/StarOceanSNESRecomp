#!/usr/bin/env python3
"""Dump DMA/HDMA channel state at the name screen."""
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
p, sock, logf = launch_and_drive(EXE, ROM, log_path=os.path.join(BASE, "build-trace", "hdma_probe.log"))

try:
    # Wait for name screen populated
    for i in range(300):
        st = cmd(sock, "get_ppu_state")
        try:
            d = json.loads(st)
            mode, tileadr, inidisp = d.get("bgmode"), d.get("bgTileAdr"), d.get("inidisp")
        except:
            mode = tileadr = inidisp = None
        if mode == 0 and tileadr == "0x4222" and inidisp != "0x00":
            break
        time.sleep(0.1)
    print("Name screen entry detected")
    # Wait until the screen is visible (inidisp not forced blank)
    for i in range(200):
        st = cmd(sock, "get_ppu_state")
        try:
            d = json.loads(st)
            if d.get("inidisp") not in ("0x80", "0x00", "0x0f"):
                continue
            if d.get("inidisp") == "0x0f":
                break
        except:
            pass
        time.sleep(0.1)
    print("Screen visible, dumping state...")

    # Dump DMA state
    dma = cmd(sock, "get_dma_state", timeout=10)
    try:
        dd = json.loads(dma)
        channels = dd.get("channels", [])
        print("=== DMA/HDMA STATE ===")
        hdma_active = []
        for i in range(len(channels)):
            ch = channels[i]
            hdmaen = ch.get("hdmaActive", False)
            dmaen = ch.get("dmaActive", False)
            mode = ch.get("mode", -1)
            baddr = ch.get("bAdr", "??")
            aaddr = ch.get("aAdr", "??")
            abank = ch.get("aBank", "??")
            table = ch.get("tableAdr", "??")
            indbank = ch.get("indBank", "??")
            if hdmaen:
                hdma_active.append(i)
                print(f"  CH{i}: HDMA mode={mode} bAdr={baddr} aAddr={abank}:{aaddr} table={table} ind={indbank}")
            elif dmaen:
                print(f"  CH{i}: DMA mode={mode} bAdr={baddr} aAddr={abank}:{aaddr}")
        if not hdma_active:
            print("  (No HDMA channels active)")
        else:
            print(f"  Active HDMA channels: {hdma_active}")
    except Exception as e:
        print("DMA parse error:", e)
        print("Raw:", dma[:500])

    # Also check via get_ppu_state for window settings (for the gradient)
    ppu = json.loads(cmd(sock, "get_ppu_state"))
    print(f"\n=== PPU STATE ===")
    print(f"  bgmode={ppu.get('bgmode')}")
    print(f"  inidisp={ppu.get('inidisp')}")
    print(f"  cgadsub={ppu.get('cgadsub')}")
    print(f"  cgwsel={ppu.get('cgwsel')}")
    print(f"  fixedColor={ppu.get('fixedColor')}")
    print(f"  window={ppu.get('windowsel')}")
    print(f"  screenEnabled={ppu.get('screenEnabled')}")
    print(f"  screenWindowed={ppu.get('screenWindowed')}")

    # Screenshot
    shot_path = os.path.join(BASE, "build-trace", "hdma_name.bmp").replace("\\", "/")
    cmd(sock, f"screenshot {shot_path}")
    print(f"\nScreenshot saved to {shot_path}")

finally:
    sock.close()
    kill_tree(p)
    logf.close()
