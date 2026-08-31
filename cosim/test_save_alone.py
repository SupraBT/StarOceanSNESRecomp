#!/usr/bin/env python3
import os, sys, time, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "cosim"))
from semantic_cosim import DebugClient, wait_client

EXE = os.path.join(ROOT, "build", "Release", "StarOcean.exe")
STATEDIR = os.path.join(ROOT, "build-cosim", "states")
errlog = os.path.join(ROOT, "build-cosim", "test-save-alone.stderr")

subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
time.sleep(2)
err = open(errlog, "w")
proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE),
                        stdout=subprocess.DEVNULL, stderr=err)
try:
    c = wait_client(60)
    time.sleep(0.5)
    # boot advance, print frames to confirm main loop is running
    for i in range(40):
        f = c.frame()
        if i % 10 == 0:
            print(f"boot frame {i}: {f}", flush=True)
    print("after boot, frame:", c.frame(), flush=True)

    path = os.path.join(STATEDIR, "alone_test.st")
    if os.path.exists(path):
        os.remove(path)
    r = c.j(f"save_state {path.replace(os.sep, '/')}")
    print("save ack:", r, flush=True)
    # monitor frame progression + file existence over 3s
    for i in range(10):
        time.sleep(0.3)
        print(f"  t={i*0.3:.1f}s frame={c.frame()} exists={os.path.exists(path)}", flush=True)
finally:
    err.close()
    subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
print("=== stderr save/load lines ===")
with open(errlog, errors="replace") as f:
    for line in f:
        if "[save]" in line or "[load]" in line or "fopen" in line:
            print("   ", line.rstrip())
