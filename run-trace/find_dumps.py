"""
Properly analyze DSP register dumps for the beep zone.
Voice N registers are at N*16 + offset:
  +0:VOLL  +1:VOLR  +2:PITCHL  +3:PITCHH  +4:SRCN  +5:ADSR1  +6:ADSR2  +7:GAIN

Voice 5 = $50-$57 (NOT $28-$2F which was wrong earlier!)
"""
import struct, os, glob

# Find the most recent recomp SPC dump files
trace_dir = 'F:/StarOceanRecompRAID/run-trace'
spc_files = sorted(glob.glob(os.path.join(trace_dir, '*.bin')), key=os.path.getmtime, reverse=True)
print("Available .bin files (SPC dumps):")
for f in spc_files[:10]:
    size = os.path.getsize(f)
    print(f"  {os.path.basename(f)} ({size} bytes)")

# Also look for any dump files in StarOceanTest2
sodir = 'F:/Recompilador Super Nintendo/StarOceanTest2'
spc_files2 = sorted(glob.glob(os.path.join(sodir, '*.bin')), key=os.path.getmtime, reverse=True)
print(f"\nIn StarOceanTest2:")
for f in spc_files2[:10]:
    size = os.path.getsize(f)
    print(f"  {os.path.basename(f)} ({size} bytes)")

# Also check the save states
sav_files = sorted(glob.glob(os.path.join(trace_dir, '*.sav*')), key=os.path.getmtime, reverse=True)
bst_files = sorted(glob.glob(os.path.join(sodir, '*.bst')), key=os.path.getmtime, reverse=True)
print(f"\nSavestates:")
for f in sav_files[:5]:
    print(f"  {os.path.basename(f)} ({os.path.getsize(f)} bytes)")
for f in bst_files[:5]:
    print(f"  {os.path.basename(f)} ({os.path.getsize(f)} bytes)")
