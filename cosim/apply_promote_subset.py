#!/usr/bin/env python3
"""Apply a subset of the recovered promote directives to the bank cfgs.

Usage:
  python cosim/apply_promote_subset.py            # apply ALL
  python cosim/apply_promote_subset.py C0 02F6 1 0   # apply all EXCEPT that
  ... (repeat exclude args: BANK PC16 M X)

Then regenerates the AOT code and rebuilds Release.
"""
import os, re, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_DIR = os.path.join(ROOT, "config")
DIRECTIVES = os.path.join(ROOT, "cosim", "promoted_directives.txt")
ANALYZER = os.path.join(ROOT, "snesrecomp", "recompiler-rs", "target",
                        "release", "snesrecomp-analyze.exe")
ROM = os.path.join(ROOT, "Star Ocean (Japan).sfc")

exclude = set()
args = sys.argv[1:]
while len(args) >= 4:
    exclude.add(tuple(args[:4]))
    args = args[4:]

directives = []
for line in open(DIRECTIVES):
    parts = line.split()
    if parts and tuple(parts) not in exclude:
        directives.append(tuple(parts))
print(f"applying {len(directives)} directives (excluded {len(exclude)})")

bybank = {}
for bank, pc16, m, x in directives:
    bybank.setdefault(bank, []).append((pc16, m, x))
for f in os.listdir(CFG_DIR):
    if f.startswith("bank") and f.endswith(".cfg"):
        p = os.path.join(CFG_DIR, f)
        txt = "\n".join(l for l in open(p).read().splitlines()
                        if "entry_mx_at" not in l)
        open(p, "w").write(txt + "\n")
for bank, entries in bybank.items():
    with open(os.path.join(CFG_DIR, f"bank{bank}.cfg"), "a") as f:
        for pc16, m, x in entries:
            f.write(f"entry_mx_at {pc16} {m} {x}  # subset\n")

env = os.environ.copy()
env["SNESRECOMP_NATIVE_ANALYZER"] = ANALYZER
r = subprocess.run(
    [sys.executable, os.path.join(ROOT, "snesrecomp", "tools",
                                  "v2_emit.py"),
     "--rom", ROM, "--cfg-dir", CFG_DIR,
     "--out-dir", os.path.join(ROOT, "generated"), "--cfg-roots"],
    cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
if r.returncode != 0:
    print("REGEN FAILED:\n", r.stdout[-1500:], r.stderr[-1500:])
    sys.exit(1)
m = re.search(r"(\d+) exact AOT variants", r.stdout)
print("regen:", m.group(1) if m else "?")

r = subprocess.run(["cmake", "--build", ".", "--config", "Release"],
                   cwd=os.path.join(ROOT, "build"), capture_output=True,
                   text=True, timeout=600)
print("build:", "OK" if r.returncode == 0 else "FAILED")

r = subprocess.run([sys.executable, os.path.join(ROOT, "cosim",
                                                 "boot_test.py")],
                   capture_output=True, text=True, timeout=120)
print("boot:", (r.stdout + r.stderr).strip().replace("\n", " | "))
sys.exit(r.returncode)
