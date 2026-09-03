#!/usr/bin/env python3
"""Adversarial tests for the save_state/load_state TCP commands:
  1. empty input / no filename -> error (not crash, not saved)
  2. chained 'save A' + 'load B' in the same frame -> A saved, B loaded
     (regression for the shared single-buffer race)
  3. round-trip save/load with a path containing spaces and a long name
  4. load of a nonexistent file -> clean error, game keeps running
"""
import os, sys, time, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "cosim"))
from semantic_cosim import DebugClient, wait_client

EXE = os.path.join(ROOT, "build", "Release", "StarOcean.exe")
STATEDIR = os.path.join(ROOT, "build-cosim", "states")
os.makedirs(STATEDIR, exist_ok=True)

failures = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name} {detail}")
    if not cond:
        failures.append(name)


def main():
    subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    time.sleep(2)
    errlog = os.path.join(ROOT, "build-cosim", "test-state-cmds.stderr")
    err = open(errlog, "w")
    proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE),
                            stdout=subprocess.DEVNULL, stderr=err)
    try:
        c = wait_client(60)
        time.sleep(0.5)
        # advance a few frames to get past boot
        for _ in range(30):
            c.frame()

        # ---- 1. empty input ----
        print("== 1. empty / no filename ==")
        for cmd in ("save_state", "save_state   ", "load_state", "load_state   "):
            r = c.j(cmd)
            check(f"'{cmd}' returns error", "error" in r or "usage" in str(r), str(r)[:80])

        # ---- 2. chained save A + load B in the same frame ----
        print("== 2. chained save A + load B same frame ==")
        # First save a reference state B (to load later)
        f_b = os.path.join(STATEDIR, "chain_B.st")
        c.j(f"save_state {f_b.replace(os.sep, '/')}")
        for _ in range(5):
            c.frame()
            time.sleep(0.3)
        check("chain_B.st exists", os.path.exists(f_b) and os.path.getsize(f_b) > 100000,
              f"{os.path.getsize(f_b) if os.path.exists(f_b) else 0} bytes")

        # Now, in ONE frame, request save A then load B (same pending window)
        f_a = os.path.join(STATEDIR, "chain_A.st")
        if os.path.exists(f_a):
            os.remove(f_a)
        r1 = c.j(f"save_state {f_a.replace(os.sep, '/')}")
        r2 = c.j(f"load_state {f_b.replace(os.sep, '/')}")
        print(f"    save resp: {str(r1)[:60]}")
        print(f"    load resp: {str(r2)[:60]}")
        # Let the frame boundary flush both
        for _ in range(5):
            c.frame()
            time.sleep(0.3)
        check("chain_A.st written (not clobbered by B)", os.path.exists(f_a) and os.path.getsize(f_a) > 100000,
              f"{os.path.getsize(f_a) if os.path.exists(f_a) else 0} bytes")
        check("game still running after chained cmds", c.frame() > 0)

        # ---- 3. round-trip with spaces + long name ----
        print("== 3. round-trip with spaces + long name ==")
        f_long = os.path.join(STATEDIR, "espacio en nombre - " + "x" * 80 + ".st")
        r = c.j(f"save_state {f_long.replace(os.sep, '/')}")
        check("long-path save acked", r.get("ok") is True, str(r)[:60])
        for _ in range(5):
            c.frame()
            time.sleep(0.3)
        check("long-path file exists", os.path.exists(f_long) and os.path.getsize(f_long) > 100000,
              f"{os.path.getsize(f_long) if os.path.exists(f_long) else 0} bytes")
        # load it back and confirm frame continues
        r = c.j(f"load_state {f_long.replace(os.sep, '/')}")
        check("long-path load acked", r.get("ok") is True, str(r)[:60])
        for _ in range(3):
            c.frame()
            time.sleep(0.3)
        check("frame advances after long-path load", c.frame() > 0)

        # ---- 4. load nonexistent file ----
        print("== 4. load nonexistent file ==")
        r = c.j(f"load_state {os.path.join(STATEDIR, 'no_such_file.st').replace(os.sep, '/')}")
        for _ in range(3):
            c.frame()
            time.sleep(0.3)
        check("game keeps running after failed load", c.frame() > 0)
    finally:
        err.close()
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    print("=== stderr save/load lines ===")
    with open(errlog, errors="replace") as f:
        for line in f:
            if "[save]" in line or "[load]" in line or "fopen failed" in line:
                print("   ", line.rstrip())

    print(f"\n=== {len(failures)} failures ===")
    for f in failures:
        print(f"  FAIL: {f}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
