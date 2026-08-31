#!/usr/bin/env python3
"""Connect to the main-tree TRACE build, autoload a bridge savestate, then dump
select VRAM regions (BG1 tilemap + tiles) and report non-zero density so we can
tell whether the bridge's BG1 map/tiles are actually populated in VRAM.
"""
import os, sys, subprocess, time, json, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import DebugClient, wait_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build-cosim", "bridge-cgram")
os.makedirs(OUT, exist_ok=True)
EXE = r"E:\Recompilador Super Nintendo\StarOceanTest2\build-dbg\Release\StarOcean.exe"
EXEDIR = os.path.dirname(EXE)


def parse_hex(resp):
    m = re.search(r'"hex":"([0-9a-fA-F]+)"', resp)
    return bytes.fromhex(m.group(1)) if m else None


def density(data):
    return sum(1 for i in range(0, len(data), 2)
               if (data[i] | (data[i + 1] << 8)) != 0), len(data) // 2


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
    log = open(os.path.join(OUT, state + ".vram.log"), "wb")
    proc = subprocess.Popen([EXE], cwd=EXEDIR, env=env,
                            stdout=subprocess.DEVNULL, stderr=log)
    try:
        c = wait_client(60)
        print("[vram] connected")
        time.sleep(1.2)
        for _ in range(3):
            c.frame(); time.sleep(0.4)
        try:
            ppu = c.ppu()
            print("[vram] PPU mode=%s TM=%s bgTile=%s bgSC=%s" % (
                ppu.get("bgmode"), ppu.get("screenEnabled"),
                ppu.get("bgTileAdr"), ppu.get("bgXsc")))
        except Exception as e:
            print("[vram] ppu err:", e)
        regions = {
            "BG1 map SC0 0x5400": 0x5400,
            "BG1 map alt 0x5800": 0x5800,
            "BG1 map hist 0x7800": 0x7800,
            "BG1 tiles 0x0400": 0x0400,
            "BG1 tiles 0x4000": 0x4000,
            "BG1 tiles 0x4800": 0x4800,
        }
        for name, addr in regions.items():
            for attempt in range(3):
                try:
                    resp = c.cmd("dump_vram 0x%x 1024" % addr, timeout=8)
                    d = parse_hex(resp)
                    if d is None or len(d) < 1024:
                        print("[vram] %s: parse fail/len %s" % (name, len(d) if d else 0))
                        break
                    nz, words = density(d[:1024])
                    print("[vram] %-24s nonzero %4d/%4d words" % (name, nz, words))
                    break
                except Exception as e:
                    if attempt == 2:
                        print("[vram] %s err: %s" % (name, e))
        # Phase 2: let the emu advance ~180 frames (through the bridge fade, if
        # it runs) and re-dump the tilemaps to see if any get populated.
        if '--advance' in sys.argv:
            time.sleep(0.3)
            f0 = c.frame()
            target = f0 + 180
            start = time.monotonic()
            while time.monotonic() - start < 40 and c.frame() < target:
                time.sleep(0.2)
            print("[vram] advanced f0=%d -> fnow=%d" % (f0, c.frame()))
            time.sleep(0.5)
            # Query the always-on VRAM byte-write ring for the tilemaps and
            # tile areas: did the emu actually issue writes toward the map?
            for rname, lo, hi in [
                ("tilemap 0x5400-57ff", 0x5400, 0x57ff),
                ("tilemap 0x7800-7fff", 0x7800, 0x7fff),
                ("tiles 0x0400-07ff", 0x0400, 0x07ff),
                ("tiles 0x4000-47ff", 0x4000, 0x47ff),
            ]:
                try:
                    resp = c.cmd("vwring_get 0x%x 0x%x 128" % (lo, hi), timeout=8)
                    try:
                        j = json.loads(resp)
                        log = j.get("log", [])
                        tot = j.get("total_writes", "?")
                        print("[vram] vwring %-18s total=%s matched=%d" % (rname, tot, len(log)))
                        for e in log[:6]:
                            print("[vram]    f=%s a=%s v=%s fn=%s" % (
                                e.get("f"), e.get("a"), e.get("v"), e.get("fn")))
                        if not log:
                            print("[vram]    (no writes in this range)")
                    except Exception as e2:
                        print("[vram] vwring %s parse err: %s  head=%s" % (rname, e2, resp[:80]))
                except Exception as e:
                    print("[vram] vwring %s cmd err: %s" % (rname, e))
            for name, addr in regions.items():
                if 'map' not in name:
                    continue
                for attempt in range(3):
                    try:
                        resp = c.cmd("dump_vram 0x%x 1024" % addr, timeout=8)
                        d = parse_hex(resp)
                        if d is not None and len(d) >= 1024:
                            nz, words = density(d[:1024])
                            print("[vram] POST-fade %-18s nonzero %4d/%4d"
                                  % (name, nz, words))
                            break
                    except Exception:
                        pass
        print("[vram] done")
    finally:
        proc.kill()
        try:
            log.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()