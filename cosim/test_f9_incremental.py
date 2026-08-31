#!/usr/bin/env python3
"""Launch the game, send a real F9 keypress via Windows SendInput, and verify
that a new numbered snapshot (continuing from existing snapshot_N.st files)
is written to saves/."""
import os, sys, time, subprocess, ctypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "cosim"))
from semantic_cosim import DebugClient, wait_client

EXE = os.path.join(ROOT, "build", "Release", "StarOcean.exe")
SAVES = os.path.join(ROOT, "saves")


def send_f9():
    """Bring the game window to the foreground and send a real F9 press."""
    VK_F9 = 0x78
    user32 = ctypes.windll.user32
    # find the game window by enumerating top-level windows and matching title
    hwnd = None
    import ctypes.wintypes as wt
    EnumWindows = user32.EnumWindows
    GetWindowTextW = user32.GetWindowTextW
    IsWindowVisible = user32.IsWindowVisible
    buf = ctypes.create_unicode_buffer(256)
    found = []
    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, l):
        if IsWindowVisible(h) and GetWindowTextW(h, buf, 256) > 0:
            found.append((h, buf.value))
        return True
    EnumWindows(cb, 0)
    # pick the window whose title mentions the game or the rom
    for h, t in found:
        if any(k in t.lower() for k in ("star ocean", "star ocean (japan)")):
            hwnd = h
            print(f"  found game window: '{t}'", flush=True)
            break
    if not hwnd and found:
        hwnd = found[0][0]
        print(f"  no title match, using '{found[0][1]}'", flush=True)
    if hwnd:
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.3)
    user32.keybd_event(VK_F9, 0, 0, 0)               # down
    time.sleep(0.05)
    user32.keybd_event(VK_F9, 0, 2, 0)               # up (KEYEVENTF_KEYUP)
    time.sleep(0.05)


def list_snapshots():
    if not os.path.isdir(SAVES):
        return []
    return sorted(f for f in os.listdir(SAVES) if f.startswith("snapshot_") and f.endswith(".st"))


def main():
    before = set(list_snapshots())
    print(f"snapshots before: {sorted(before) or '(none)'}", flush=True)

    subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    time.sleep(2)
    proc = subprocess.Popen([EXE], cwd=os.path.dirname(EXE),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        c = wait_client(60)
        time.sleep(2.0)  # let the window appear and come to foreground
        print("connected, sending F9...", flush=True)
        send_f9()
        # wait for the save to land
        time.sleep(3.0)
        after = set(list_snapshots())
        new = sorted(after - before)
        print(f"snapshots after: {sorted(after)}", flush=True)
        if new:
            print(f"NEW: {new}", flush=True)
        else:
            print("NO NEW SNAPSHOT — F9 did not produce a file", flush=True)
    finally:
        subprocess.run(["taskkill", "/F", "/IM", "StarOcean.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


if __name__ == "__main__":
    main()
