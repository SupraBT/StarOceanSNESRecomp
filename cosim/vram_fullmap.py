#!/usr/bin/env python3
"""Dump the full 64KB VRAM (bytes) of a loaded bridge savestate and print
non-zero density per 512-word (1024-byte) block, so we can locate where the
tilemap and tiles actually live.
"""
import os, sys, subprocess, time, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import wait_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build-cosim", "vrammap")
os.makedirs(OUT, exist_ok=True)
EXE = r"E:\Recompilador Super Nintendo\StarOceanTest2\build-dbg\Release\StarOcean.exe"
EXEDIR = os.path.dirname(EXE)


def parse_hex(resp):
    m = re.search(r'"hex":"([0-9a-fA-F]+)"', resp)
    return bytes.fromhex(m.group(1)) if m else None


def main():
    state = sys.argv[1] if len(sys.argv) > 1 else "up_2.st"
    state_path = os.path.join(EXEDIR, state).replace("\\", "/")
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False)
        time.sleep(2)
    env = dict(os.environ)
    env["SNESRECOMP_AUTOLOAD"] = state_path
    for k in ("CPU_TRACE_RING_ENTRIES", "BOUNDARY_RING_ENTRIES",
              "GM14_TRACE_ENTRIES", "VRAM_RING_ENTRIES"):
        env["SNESRECOMP_" + k] = "128" if "VRAM" not in k else "256"
    log = open(os.path.join(OUT, state + ".stderr.log"), "wb")
    proc = subprocess.Popen([EXE], cwd=EXEDIR, env=env,
                            stdout=subprocess.DEVNULL, stderr=log)
    try:
        c = wait_client(60)
        time.sleep(1.2)
        for _ in range(3):
            c.frame(); time.sleep(0.4)
        # change VRAM ring env limit doesn't matter for dump_vram; dump all 64KB.
        resp = c.cmd("dump_vram 0 65536", timeout=40)
        d = parse_hex(resp)
        if d is None or len(d) < 65536:
            print("[vrammap] dump fail len=%s (expected 65536)" % (len(d) if d else 0))
            return
        open(os.path.join(OUT, state + ".vram.bin"), "wb").write(d)
        nwords = 65536 // 2  # 32768 words
        print("[vrammap] VRAM 64KB, non-zero density per 512-word block (byte addr $0000-$7fff):")
        for wb in range(0, nwords, 512):
            byte0 = wb * 2
            nz = 0
            for w in range(wb, wb + 512):
                i = w * 2
                if d[i] | d[i + 1]:
                    nz += 1
            bar = '#' * (nz // 51)
            print("  word $%04X-$%03X (byte $%04X): %4d/512 %s" %
                  (wb, wb + 511, byte0, nz, bar))
    finally:
        proc.kill()
        try:
            log.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()