#!/usr/bin/env python3
"""Trace cgramPointer every frame during the palette copy loop."""
import os,sys,subprocess,time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import DebugClient, wait_client
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE=os.path.join(ROOT,"build","Release","StarOcean.exe")
INPUTS=os.path.join(ROOT,"build-cosim","grabacion_inputs.txt")
STATE=os.path.join(ROOT,"build-cosim",sys.argv[1] if len(sys.argv)>1 else "bridge-2600.st")
START=int(sys.argv[2]) if len(sys.argv)>2 else 2610
END=int(sys.argv[3]) if len(sys.argv)>3 else 2640
def parse_events(path):
    ev={}
    for line in open(path,encoding="utf-8"):
        p=line.split()
        if len(p)<2: continue
        try: fr=int(p[0]); mask=int(p[1],16)
        except ValueError: continue
        ev[fr]=mask
    return ev
def events_to_frames(ev):
    last=max(ev); frames=[0]*(last+1)
    for fr,mask in ev.items(): frames[fr]=mask
    return frames
def kill_game():
    subprocess.run(["taskkill","/F","/IM","StarOcean.exe"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
kill_game(); time.sleep(2)
frames=events_to_frames(parse_events(INPUTS))
proc=subprocess.Popen([EXE],cwd=os.path.dirname(EXE),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    c=wait_client(60); print("connected",flush=True); time.sleep(0.5)
    r=c.cmd("load_state "+STATE.replace("\\","/"),timeout=20); print("load:",r[:70],flush=True)
    time.sleep(1.5)
    last=-1
    while True:
        cur=c.frame()
        idx=cur+1
        if idx<len(frames): c.controller(frames[idx])
        if START<=cur<=END and cur!=last:
            last=cur
            try:
                ppu=c.ppu()
                def hx(v):
                    try: return int(v,16) if isinstance(v,str) else int(v)
                    except Exception: return -1
                print(f"frame {cur}: cgramPtr=0x{hx(ppu.get('cgramPointer',-1)):02X}",flush=True)
            except Exception as e:
                print(f"frame {cur}: err {str(e)[:50]}",flush=True)
        if cur>END+3: break
        if cur>len(frames)+2000: break
        time.sleep(0.01)
finally:
    kill_game()
