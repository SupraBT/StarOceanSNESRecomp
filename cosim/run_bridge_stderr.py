#!/usr/bin/env python3
"""Load a savestate, advance to a frame, capturing the game's stderr to a file
(used to read the [CGRAM_ZERO] diagnostic)."""
import os, sys, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from semantic_cosim import DebugClient, wait_client
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE=os.path.join(ROOT,"build","Release","StarOcean.exe")
INPUTS=os.path.join(ROOT,"build-cosim","grabacion_inputs.txt")
STATE=os.path.join(ROOT,"build-cosim",sys.argv[1] if len(sys.argv)>1 else "bridge-2600.st")
END=int(sys.argv[2]) if len(sys.argv)>2 else 2830
STDERR=sys.argv[3] if len(sys.argv)>3 else os.path.join(ROOT,"build-cosim","bridge-stderr.log")

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
log=open(STDERR,"wb")
proc=subprocess.Popen([EXE],cwd=os.path.dirname(EXE),stdout=subprocess.DEVNULL,stderr=log)
try:
    c=wait_client(60); print("connected",flush=True); time.sleep(0.5)
    r=c.cmd("load_state "+STATE.replace("\\","/"),timeout=20); print("load:",r[:80],flush=True)
    time.sleep(1.5)
    cur=c.frame(); print("frame after load:",cur,flush=True)
    start=time.monotonic()
    while True:
        cur=c.frame()
        idx=cur+1
        if idx<len(frames): c.controller(frames[idx])
        if cur>=END:
            print(f"reached {cur}",flush=True); break
        if time.monotonic()-start>90: print("TIMEOUT",flush=True); break
    time.sleep(1.0)
finally:
    kill_game(); log.close()
print("stderr ->",STDERR)
