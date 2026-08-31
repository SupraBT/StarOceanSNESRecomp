#!/usr/bin/env python3
"""Fast boot regression test.

Launches build/Release/StarOcean.exe, waits ~14 s (enough for frame 600,
where the working build is already deep in bank-C0/C2 game code), then
checks the last [so_rtl] resume PC.  A build stuck in the boot IRQ wait
stays at $00FE80 / $00FEBD; a working build resumes in bank C0-CF.

Exit code 0 = PASS, 1 = FAIL.
"""
import os, re, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.path.join(ROOT, "build", "Release", "StarOcean.exe")
LOG = os.path.join(os.environ.get("TEMP", "/tmp"), "boot_test.log")
WAIT = float(sys.argv[1]) if len(sys.argv) > 1 else 14.0

# Clean any stragglers first.
subprocess.run(["powershell", "-NoProfile", "-Command",
                "Stop-Process -Name StarOcean -Force -ErrorAction SilentlyContinue"],
               capture_output=True)
time.sleep(1)

with open(LOG, "wb") as err:
    proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE),
                            stdout=subprocess.DEVNULL, stderr=err)
    time.sleep(WAIT)
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    f"Stop-Process -Id {proc.pid} -Force -ErrorAction SilentlyContinue"],
                   capture_output=True)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

frames = []
with open(LOG, "rb") as f:
    for line in f:
        try:
            s = line.decode(errors="replace")
        except Exception:
            continue
        m = re.search(r"\[so_rtl\] frame (\d+) nmiEn=(\d) resume=\$([0-9A-Fa-f]{6})", s)
        if m:
            frames.append((int(m.group(1)), int(m.group(2)), int(m.group(3), 16)))

if not frames:
    print("FAIL: no [so_rtl] lines in log")
    sys.exit(1)

last = frames[-1]
print(f"frames sampled: {len(frames)}; last={last[0]} nmiEn={last[1]} resume=${last[2]:06X}")
# PASS requires the game to have CLEARED frame 600 (the [so_rtl] log prints
# frames 1-5 then every 600; a last-line of frame 5 means the game never got
# past ~600 frames in the wait window -> stalled/crawling).
if last[0] < 600:
    print("FAIL: game did not reach frame 600 (stalled or crawling)")
    sys.exit(1)
stuck = (last[2] == 0x00FE80 or last[2] == 0x00FEBD)
if stuck:
    print("FAIL: stuck in boot IRQ wait ($00FE80/$00FEBD)")
    sys.exit(1)
print("PASS: game advanced past boot IRQ wait")
sys.exit(0)
