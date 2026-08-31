#!/usr/bin/env python3
"""Bisect the promote_tier2_mx regression.

The 87 entry_mx_at directives (recovered from the dispatch diff as 115
variants) were pinned into the bank cfgs and regenerated the AOT code.
One or more of them break the boot (game stalls in the $00FE80 IRQ wait).
This script binary-searches the directive list for a minimal failing
subset, using a fast boot test (~15 s) after each regen+build.

Usage: python cosim/bisect_promote.py
"""
import os, re, subprocess, sys, time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_DIR = os.path.join(ROOT, "config")
DIRECTIVES = os.path.join(ROOT, "cosim", "promoted_directives.txt")
ANALYZER = os.path.join(ROOT, "snesrecomp-tool", "recompiler-rs", "target",
                        "release", "snesrecomp-analyze.exe")
ROM = os.path.join(ROOT, "Star Ocean (Japan).sfc")

directives = []
for line in open(DIRECTIVES):
    line = line.strip()
    if not line:
        continue
    bank, pc16, m, x = line.split()
    directives.append((bank, pc16, m, x))
print(f"directives: {len(directives)}")


def clear_cfgs():
    for f in os.listdir(CFG_DIR):
        if f.startswith("bank") and f.endswith(".cfg"):
            p = os.path.join(CFG_DIR, f)
            txt = "\n".join(l for l in open(p).read().splitlines()
                            if "entry_mx_at" not in l)
            open(p, "w").write(txt + "\n")


def apply(dirs):
    clear_cfgs()
    bybank = {}
    for bank, pc16, m, x in dirs:
        bybank.setdefault(bank, []).append((pc16, m, x))
    for bank, entries in bybank.items():
        p = os.path.join(CFG_DIR, f"bank{bank}.cfg")
        with open(p, "a") as f:
            for pc16, m, x in entries:
                f.write(f"entry_mx_at {pc16} {m} {x}  # bisect\n")


def regen():
    env = os.environ.copy()
    env["SNESRECOMP_NATIVE_ANALYZER"] = ANALYZER
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "snesrecomp-tool", "tools",
                                      "v2_emit.py"),
         "--rom", ROM, "--cfg-dir", CFG_DIR,
         "--out-dir", os.path.join(ROOT, "generated"), "--cfg-roots"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print("REGEN FAILED:\n", r.stdout[-2000:], r.stderr[-2000:])
        return False
    m = re.search(r"(\d+) exact AOT variants", r.stdout)
    print("  regen:", m.group(1) if m else "?")
    return True


def build():
    r = subprocess.run(
        ["cmake", "--build", ".", "--config", "Release"],
        cwd=os.path.join(ROOT, "build"), capture_output=True, text=True,
        timeout=600)
    return r.returncode == 0


def boot_test():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "cosim",
                                                     "boot_test.py")],
                       capture_output=True, text=True, timeout=120)
    out = (r.stdout + r.stderr).strip()
    print("  boot:", out.replace("\n", " | "))
    return r.returncode == 0


def test_set(dirs, label):
    t0 = time.monotonic()
    print(f"[{label}] applying {len(dirs)} directives...")
    apply(dirs)
    if not regen():
        return None
    if not build():
        return None
    ok = boot_test()
    print(f"[{label}] {'PASS' if ok else 'FAIL'} ({time.monotonic()-t0:.0f}s)")
    return ok


# --- sanity: all directives should reproduce the broken boot ---
if test_set(directives, "ALL") is not False:
    print("WARNING: all-directives build did NOT fail boot test; "
          "regression not reproduced. Aborting bisect.")
    sys.exit(2)

# --- binary search for a minimal failing subset ---
lo, hi = 0, len(directives)  # failing set is directives[lo:hi]
while hi - lo > 1:
    mid = (lo + hi) // 2
    cand = directives[lo:mid]
    # candidate subset failing -> shrink hi; passing -> culprit in [mid:hi]
    r = test_set(cand, f"range {lo}:{mid} ({mid-lo})")
    if r is None:
        print("aborting (regen/build failure)")
        sys.exit(3)
    if r is False:      # subset still breaks boot
        hi = mid
    else:               # subset boots fine -> culprit after mid
        lo = mid

culprits = directives[lo:hi]
print("\n=== minimal failing directives ===")
for bank, pc16, m, x in culprits:
    print(f"  bank {bank} {pc16} M{m} X{x}")
# leave them applied for the user to inspect
apply(culprits)
print(f"applied {len(culprits)} directive(s) to cfgs")
