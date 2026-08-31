#!/usr/bin/env python3
"""Autoload a savestate before the bridge, advance ~500 frames with
SNESRECOMP_TRACE_TILEMAP=1 (printed by debug_server_on_vram_write on writes to
word range $5400-$57ff), and grep the captured stderr for those writes. This
tells us whether the recompiler attempts to write the bridge BG1 tilemap during
the fade / scene load, or whether the write path is omitted entirely.
"""
import os, sys, subprocess, time, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import wait_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build-cosim", "tilemap-trace")
os.makedirs(OUT, exist_ok=True)
EXE = r"E:\Recompilador Super Nintendo\StarOceanTest2\build-dbg\Release\StarOcean.exe"
EXEDIR = os.path.dirname(EXE)


def main():
    state = sys.argv[1] if len(sys.argv) > 1 else "up_1.st"
    advance = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    lo = sys.argv[3] if len(sys.argv) > 3 else "5400"
    hi = sys.argv[4] if len(sys.argv) > 4 else "57ff"

    state_path = os.path.join(EXEDIR, state).replace("\\", "/")
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False)
        time.sleep(2)

    env = dict(os.environ)
    env["SNESRECOMP_AUTOLOAD"] = state_path
    env["SNESRECOMP_TRACE_TILEMAP"] = "1"
    env["SNESRECOMP_TRACE_TILEMAP_RANGE"] = "%s %s" % (lo, hi)
    for k in ("CPU_TRACE_RING_ENTRIES", "BOUNDARY_RING_ENTRIES",
              "GM14_TRACE_ENTRIES", "VRAM_RING_ENTRIES"):
        env["SNESRECOMP_" + k] = "128" if "VRAM" not in k else "256"

    log = open(os.path.join(OUT, state + ".stderr.log"), "wb")
    proc = subprocess.Popen([EXE], cwd=EXEDIR, env=env,
                            stdout=subprocess.DEVNULL, stderr=log)
    try:
        c = wait_client(60)
        time.sleep(1.0)
        f0 = c.frame()
        print("[ttrace] connected f0=%d, advancing %d -> target=%d"
              % (f0, advance, f0 + advance), flush=True)
        target = f0 + advance
        start = time.monotonic()
        while time.monotonic() - start < 120 and c.frame() < target:
            time.sleep(0.2)
        print("[ttrace] done f=%d" % c.frame(), flush=True)
    finally:
        time.sleep(0.4)
        proc.kill()
        log.close()

    # Analyze the captured stderr for tilemap writes.
    path = os.path.join(OUT, state + ".stderr.log")
    data = open(path, "rb").read().decode("utf-8", "replace")
    lines = [l for l in data.splitlines() if "VRAM-TM" in l]
    print("[ttrace] tilemap writes to %s-%s: %d" % (lo, hi, len(lines)))
    # Summarize by frame and value density.
    frames = []
    nonzero = 0
    for l in lines[:2000]:
        m = re.search(r"f=(\d+) word=\$([0-9A-Fa-f]{4}) val=\$([0-9A-Fa-f]{2}) fn=(\S+)", l)
        if m:
            frames.append(int(m.group(1)))
            if int(m.group(3), 16) & 0x7fff:
                nonzero += 1
    if frames:
        print("[ttrace] first-write-frame=%d last-write-frame=%d"
              % (min(frames), max(frames)))
    print("[ttrace] nonzero writes=%d/%d" % (nonzero, len(frames)))
    for l in lines[:12]:
        print("   " + l[:110])


if __name__ == "__main__":
    main()