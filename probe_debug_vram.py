#!/usr/bin/env python3
import os, socket, subprocess, sys, time, json

PORT = 13308
BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2"
EXE = os.path.join(BASE, "build-trace", "StarOcean.exe")
ROM = os.path.join(BASE, "build-trace", "Star Ocean (Japan).sfc")

log = open(os.path.join(BASE, "build-trace", "verify", "dbg_stderr.log"), "wb")
p = subprocess.Popen([EXE, ROM], stderr=log, stdout=subprocess.DEVNULL)
try:
    sock = None
    for _ in range(60):
        try:
            sock = socket.create_connection(("127.0.0.1", PORT), timeout=2)
            break
        except OSError:
            time.sleep(0.25)
    if sock is None:
        print("no server")
        sys.exit(1)
    time.sleep(35)  # let it reach the name screen
    sock.sendall(b"dump_vram 0x0 0x10000\n")
    sock.settimeout(30)
    buf = b""
    while True:
        try:
            chunk = sock.recv(1 << 20)
        except socket.timeout:
            print("TIMEOUT, got %d bytes" % len(buf))
            break
        if not chunk:
            print("EOF, got %d bytes" % len(buf))
            break
        buf += chunk
        if buf.endswith(b"}\n"):
            break
    print("total len:", len(buf))
    print("head:", buf[:80])
    print("tail:", buf[-40:])
    try:
        data = json.loads(buf)
        hx = data.get("hex", "")
        print("hex len:", len(hx), "blob len:", len(bytes.fromhex(hx)))
    except Exception as e:
        print("json fail:", e)
finally:
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, timeout=10)
    except Exception:
        pass
    try:
        p.kill(); p.wait(timeout=5)
    except Exception:
        pass
    log.close()
