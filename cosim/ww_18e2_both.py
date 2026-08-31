#!/usr/bin/env python3
"""Replay recorded inputs with SNESRECOMP_WRITE_WATCH=0x18E2 through BOTH
bridge scenes (normal f~3187, alarm f~5108) to see what populates the
fade-in source zone $7E:18E2 in the working case.

Usage: python cosim/ww_18e2_both.py [target] [out_log]
"""
import os, sys, subprocess, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import DebugClient, wait_client

EXE = os.path.join(ROOT, "build", "Release", "StarOcean.exe")
INPUTS = os.path.join(ROOT, "build-cosim", "grabacion_inputs.txt")
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 5200
LOG = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.abspath(os.path.join(ROOT, "build-cosim", "ww-18E2-both.log"))


def parse_events(path):
    ev = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.split()
            if len(p) < 2:
                continue
            try:
                fr = int(p[0]); mask = int(p[1], 16)
            except ValueError:
                continue
            ev[fr] = mask
    return ev


def events_to_frames(ev):
    last = max(ev)
    frames = [0] * (last + 1)
    for fr, mask in ev.items():
        frames[fr] = mask
    return frames


def main():
    subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    time.sleep(2)
    frames = events_to_frames(parse_events(INPUTS))
    print(f"[ww] replaying to frame {TARGET}", flush=True)
    env = os.environ.copy()
    env["SNESRECOMP_WRITE_WATCH"] = "0x18E2"
    env["SNESRECOMP_WRITE_WATCH_LOG"] = LOG
    err = open(LOG + ".stderr", "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE), env=env,
                            stdout=subprocess.DEVNULL, stderr=err)
    try:
        c = wait_client(90)
        print("[ww] connected", flush=True)
        time.sleep(0.5)
        start = time.monotonic()
        while True:
            cur = c.frame()
            idx = cur + 1
            if idx < len(frames):
                c.controller(frames[idx])
            if cur >= TARGET:
                print(f"[ww] reached frame {cur}", flush=True)
                break
            if cur >= len(frames) + 1000:
                print(f"[ww] end of recording at frame {cur}", flush=True)
                break
            if time.monotonic() - start > 600:
                print(f"[ww] TIMEOUT at frame {cur}", flush=True)
                break
        time.sleep(0.5)
    finally:
        err.close()
        try:
            proc.terminate()
        except Exception:
            pass
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    print(f"[ww] done - log at {LOG}", flush=True)


if __name__ == "__main__":
    main()
