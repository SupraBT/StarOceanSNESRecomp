#!/usr/bin/env python3
"""Load a chosen bridge savestate via the diagnostic autoload env var
(SNESRECOMP_AUTOLOAD, which restores the full CpuState chunk) and capture the
rendered frame + PPU/VRAM so we can verify the ship-bridge background fix.

Usage: bridge_probe.py <state_name>  (e.g. 500_bridge_bad.st)
Output lands in build-cosim/bridge-probe/<state>.png + ppu_state.json.
"""
import os, sys, subprocess, time, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import DebugClient, wait_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build-cosim", "bridge-probe")
os.makedirs(OUT, exist_ok=True)

# Build with the debug server + the kCwBitsMod color-window fix, on E:.
EXE = (r"E:\Recompilador Super Nintendo\StarOceanTest2-ccc"
       r"\build-ccc-dbg\Release\StarOcean.exe")
# Savestates were copied next to that exe's cwd too, but autoload wants an
# explicit path — point at the copies we placed in build-ccc-dbg/Release.
EXEDIR = os.path.join(os.path.dirname(EXE))


def to_png(bmp_path):
    try:
        from PIL import Image
        im = Image.open(bmp_path)
        png = bmp_path.replace(".bmp", ".png")
        im.save(png)
        return png
    except Exception as e:
        print("[probe] PNG fail:", e)
        return None


def main():
    state = sys.argv[1] if len(sys.argv) > 1 else "500_bridge_bad.st"
    state_path = os.path.join(EXEDIR, state).replace("\\", "/")
    if not os.path.exists(state_path):
        print("[probe] state not found:", state_path)
        return 2

    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False)
        time.sleep(2)

    env = dict(os.environ)
    env["SNESRECOMP_AUTOLOAD"] = state_path
    env["SNESRECOMP_RELAXED_LOAD"] = "1"
    # Shrink the trace rings so the TRACE=ON build doesn't allocate 640 MB of
    # rings or hammer the disk (which turned runs into 4 FPS / grinding).
    env["SNESRECOMP_CPU_TRACE_RING_ENTRIES"] = "1024"
    env["SNESRECOMP_BOUNDARY_RING_ENTRIES"] = "128"
    env["SNESRECOMP_GM14_TRACE_ENTRIES"] = "128"
    env["SNESRECOMP_VRAM_RING_ENTRIES"] = "256"
    log = open(os.path.join(OUT, state + ".stderr.log"), "wb")
    proc = subprocess.Popen([EXE], cwd=EXEDIR,
                            env=env, stdout=subprocess.DEVNULL, stderr=log)
    try:
        c = wait_client(60)
        print("[probe] connected")
        # Let the render settle a couple frames past the loaded state.
        f0 = c.frame()
        print("[probe] frame at load:", f0)
        time.sleep(1.0)
        for _ in range(3):
            f1 = c.frame()
            time.sleep(0.4)

        # PPU state
        try:
            ppu = c.ppu()
            json.dump(ppu, open(os.path.join(OUT, state + ".ppu.json"), "w"),
                      indent=1)
            print("[probe] PPU mode=%s TM=%s bgTile=%s bgSC=%s"
                  % (ppu.get("bgmode"), ppu.get("screenEnabled"),
                     ppu.get("bgTileAdr"), ppu.get("bgXsc")))
        except Exception as e:
            print("[probe] ppu err:", e)

        # Screenshot (retry until render buffer is readable)
        ok = False
        for attempt in range(40):
            try:
                fr = c.frame()
                ss = os.path.join(OUT, state + ".bmp").replace("\\", "/")
                resp = c.cmd("screenshot " + ss, timeout=10)
                if "error" not in resp.lower() and os.path.exists(ss):
                    ok = True
                    png = to_png(ss)
                    print("[probe] shot OK frame=%d -> %s (png=%s)" % (fr, ss, png))
                    break
            except Exception:
                pass
            time.sleep(0.25)
        if not ok:
            print("[probe] screenshot FAILED repeatedly")

        # VRAM tilemap + a slice of tiles for the BG1 map at 0x7800-equivalent
        try:
            sc0 = int(ppu.get("bgXsc", ["00", "00", "00", "00"])[0], 16) & 0xfc
            mapadr = sc0 << 8
            mv = c.cmd("dump_vram 0x%x 512" % mapadr, timeout=8)
            open(os.path.join(OUT, state + ".map.txt"), "w").write(mv)
            print("[probe] map dump @ %04X" % mapadr)
        except Exception as e:
            print("[probe] vram dump err:", e)

        print("[probe] done")
    finally:
        proc.kill()
        try:
            log.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()