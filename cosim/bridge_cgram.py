#!/usr/bin/env python3
"""Load a native main-tree savestate (SNESRECOMP_AUTOLOAD) into the TRACE build
that shares the g_cpu layout, then dump CGRAM palette + PPU + screenshot so we
can see whether the ship-bridge BG1 palette is actually loaded (non-black).

Requires: build-dbg/Release/StarOcean.exe (main tree, TRACE=ON), savestate up_2.st
Output: build-cosim/bridge-cgram/<state>.png + .cgram.json + .ppu.json
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
    # resp is like {"len":512,"hex":"<hex>",...} possibly with trailing }
    m = re.search(r'"hex":"([0-9a-fA-F]+)"', resp)
    if not m:
        return None
    return bytes.fromhex(m.group(1))


def count_palette(cgram, base, n):
    """Count non-black colors in palette block `base`..base+n (0-based, 16 colors each)."""
    nb = 0
    for i in range(n):
        lo = cgram[(base + i) * 2]
        hi = cgram[(base + i) * 2 + 1]
        color = lo | (hi << 8)
        r = color & 0x1f; g = (color >> 5) & 0x1f; b = (color >> 10) & 0x1f
        if r or g or b:
            nb += 1
    return nb


def main():
    state = sys.argv[1] if len(sys.argv) > 1 else "up_2.st"
    state_path = os.path.join(EXEDIR, state).replace("\\", "/")
    if not os.path.exists(state_path):
        print("[cgram] state not found:", state_path)
        return 2

    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False)
        time.sleep(2)

    env = dict(os.environ)
    env["SNESRECOMP_AUTOLOAD"] = state_path
    env["SNESRECOMP_CPU_TRACE_RING_ENTRIES"] = "1024"
    env["SNESRECOMP_BOUNDARY_RING_ENTRIES"] = "128"
    env["SNESRECOMP_GM14_TRACE_ENTRIES"] = "128"
    env["SNESRECOMP_VRAM_RING_ENTRIES"] = "256"
    log = open(os.path.join(OUT, state + ".stderr.log"), "wb")
    proc = subprocess.Popen([EXE], cwd=EXEDIR, env=env,
                            stdout=subprocess.DEVNULL, stderr=log)
    try:
        c = wait_client(60)
        print("[cgram] connected")
        f0 = c.frame()
        print("[cgram] frame at load:", f0)
        time.sleep(1.2)
        for _ in range(3):
            f1 = c.frame(); time.sleep(0.4)

        # PPU state
        ppu = None
        try:
            ppu = c.ppu()
            json.dump(ppu, open(os.path.join(OUT, state + ".ppu.json"), "w"), indent=1)
            print("[cgram] PPU mode=%s TM=%s bgTile=%s bgSC=%s" % (
                ppu.get("bgmode"), ppu.get("screenEnabled"),
                ppu.get("bgTileAdr"), ppu.get("bgXsc")))
        except Exception as e:
            print("[cgram] ppu err:", e)

        # CGRAM dump
        try:
            resp = c.cmd("dump_cgram", timeout=8)
            cg = parse_hex(resp)
            if cg is None:
                print("[cgram] cgram parse fail, resp[:80]:", resp[:80])
            else:
                json.dump(cg.hex(), open(os.path.join(OUT, state + ".cgram.json"), "w"))
                blues = [count_palette(cg, b * 16, 16) for b in range(16)]
                print("[cgram] length=%d  non-black colors per 16-color palette block:" % len(cg))
                for bi in range(16):
                    print("[cgram]   BG%pl% plock %d: %d non-black" % (bi, blues[bi]))
                # total non-black across first 128 colors (BG palettes region)
                tot = count_palette(cg, 0, 128)
                print("[cgram] TOTAL non-black in first 128 colors: %d" % tot)
        except Exception as e:
            print("[cgram] cgram err:", e)

        # screenshot
        ok = False
        for attempt in range(20):
            try:
                fr = c.frame()
                ss = os.path.join(OUT, state + ".bmp").replace("\\", "/")
                resp = c.cmd("screenshot " + ss, timeout=10)
                if "error" not in resp.lower() and os.path.exists(ss):
                    ok = True
                    try:
                        from PIL import Image
                        png = ss.replace(".bmp", ".png")
                        Image.open(ss).save(png)
                        print("[cgram] shot OK frame=%d -> %s" % (fr, png))
                    except Exception as e:
                        print("[cgram] shot saved bmp, png fail:", e)
                    break
            except Exception:
                pass
            time.sleep(0.25)
        print("[cgram] done")
    finally:
        proc.kill()
        try:
            log.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()