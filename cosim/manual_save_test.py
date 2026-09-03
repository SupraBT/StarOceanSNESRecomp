#!/usr/bin/env python3
import os, sys, time, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "cosim"))
from semantic_cosim import DebugClient, wait_client

EXE = os.path.join(ROOT, "build", "Release", "StarOcean.exe")
subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
time.sleep(2)
err = open(os.path.join(ROOT, "build-cosim", "save-test.stderr"), "w")
proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE),
                        stdout=subprocess.DEVNULL, stderr=err)
try:
    c = wait_client(60)
    print("connected, frame:", c.frame())
    path = os.path.join(ROOT, "build-cosim", "states", "manual_test.st")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = c.j(f"save_state {path.replace(os.sep, '/')}")
    print("save resp:", r)
    for i in range(6):
        c.frame()
        time.sleep(0.5)
    print("file exists:", os.path.exists(path),
          os.path.getsize(path) if os.path.exists(path) else "")
finally:
    err.close()
    subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
print("=== stderr tail ===")
with open(os.path.join(ROOT, "build-cosim", "save-test.stderr")) as f:
    print("".join(f.readlines()[-5:]))
