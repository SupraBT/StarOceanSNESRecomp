#!/usr/bin/env python3
"""Measure raw emulation FPS of the Release build (headless, no vsync).

Launches build/Release/StarOcean.exe with the user's input log in replay
mode, times the stderr heartbeat "frame 600", and reports average FPS.
Kills the game when done.
"""
import os
import subprocess
import sys
import time

BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2"
EXE = os.path.join(BASE, "build", "Release", "StarOcean.exe")
ROM = os.path.join(BASE, "build", "Release", "Star Ocean (Japan).sfc")
LOG = os.path.join(BASE, "so_inputs.log")
OUT = os.path.join(BASE, "fps_measure.log")

TARGET_FRAME = 600


def main():
    from so_drive import launch_and_drive
    p, sock, logf = launch_and_drive(EXE, ROM, log_path=OUT)
    t0 = time.time()
    seen_f5 = None
    seen_600 = None
    try:
        while time.time() - t0 < 120:
            logf.flush()
            with open(OUT, "rb") as f:
                data = f.read().decode("utf-8", errors="replace")
            if seen_f5 is None and "frame 5 " in data:
                seen_f5 = time.time() - t0
            if seen_600 is None and ("frame 600 " in data or "frame 600\n" in data):
                seen_600 = time.time() - t0
                break
            time.sleep(0.2)
    finally:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                       capture_output=True, timeout=10)
        try:
            p.wait(timeout=5)
        except Exception:
            pass
        logf.close()

    if seen_600 is None:
        print("TIMEOUT: frame %d never reached in 120s" % TARGET_FRAME)
        sys.exit(1)
    fps = TARGET_FRAME / seen_600
    print("frame 5   at t=%6.2fs" % seen_f5)
    print("frame 600 at t=%6.2fs" % seen_600)
    print("average FPS (0..%d) = %.1f" % (TARGET_FRAME, fps))
    print("frame budget (ms/frame) = %.3f" % (1000.0 / fps))
    sys.exit(0)


if __name__ == "__main__":
    main()
