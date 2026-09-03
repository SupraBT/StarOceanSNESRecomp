#!/usr/bin/env python3
"""Load a named savestate, advance frames, capture stderr, verify state."""
import os, sys, time, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "cosim"))
from semantic_cosim import DebugClient, wait_client

EXE = os.path.join(ROOT, "build", "Release", "StarOcean.exe")
STATE = sys.argv[1] if len(sys.argv) > 1 else "500_bridge_bad.st"
NFRAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 5
path = os.path.join(ROOT, "build-cosim", "states", STATE)
errlog = os.path.join(ROOT, "build-cosim", "load-test.stderr")

subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
time.sleep(2)
err = open(errlog, "w")
proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE),
                        stdout=subprocess.DEVNULL, stderr=err)
try:
    c = wait_client(60)
    time.sleep(0.5)
    r = c.j(f"load_state {path.replace(os.sep, '/')}")
    print("load resp:", r)
    time.sleep(1.5)
    for _ in range(NFRAMES):
        c.frame()
        time.sleep(0.3)
    cur = c.frame()
    st = c.ppu()
    print(f"frame after load+{NFRAMES}: {cur}")
    print(f"  bgmode={st.get('bgmode')} tm={st.get('tm')} sc0={st.get('sc0')}")
    cg = c.cgram()
    bg1 = sum(1 for i in range(128) if cg[2*i] != 0 or cg[2*i+1] != 0)
    print(f"  cgram BG1 non-black: {bg1}/128")
    print(f"  cgram total non-black: {sum(1 for i in range(256) if cg[2*i] != 0 or cg[2*i+1] != 0)}/256")
finally:
    err.close()
    subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
print("=== stderr tail ===")
with open(errlog, errors="replace") as f:
    lines = f.readlines()
    print("".join(lines[-8:]))
