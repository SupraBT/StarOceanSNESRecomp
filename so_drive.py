#!/usr/bin/env python3
"""Shared launch helper for headless validation.

The old SNESRECOMP_INPUT_MODE=record|replay + so_inputs.log mechanism was
removed (it overrode the keyboard on interactive runs). The game now takes
keyboard input directly from the host at all times.

Probes launch the exe and connect to the debug server; input (pressing A to
title -> New Game -> name selection) is driven by the human at the keyboard
(three presses), since frame-accurate scripted presses through set_controller
proved unreliable against the trace build's variable frame pacing.

Usage:
    from so_drive import launch_and_drive, cmd, kill_tree
    p, sock, logf = launch_and_drive(EXE, ROM, log_path="...", name="probe")
    ... poll get_ppu_state until the name screen ...
    sock.close(); kill_tree(p); logf.close()
"""
import os
import socket
import subprocess
import threading
import time

BASE = r"E:\Recompilador Super Nintendo\StarOceanTest2"
PORT = 13308
A_MASK = 0x100  # runner joypad layout: A=0x100 (New Game / confirm)

# Exact A-press timing recorded from a manual play session (see
# so_inputs_timed.log in the project root): the user pressed A 4 times to walk
# title -> New Game -> name selection. First 3 presses reach the name screen;
# the 4th (frame 288-296) was pressed on the menu itself and is NOT needed.
# Frame numbers come from `snes_frame_counter` (deterministic across builds).
NAME_SCREEN_PRESSES = [
    (76, 83),    # press A (hold ~7 frames)
    (171, 179),  # press A
    (234, 241),  # press A -> name selection menu (mode 0)
]


def connect(retries=120, delay=0.05):
    for _ in range(retries):
        try:
            return socket.create_connection(("127.0.0.1", PORT), timeout=2)
        except OSError:
            time.sleep(delay)
    return None


def cmd(sock, line, timeout=60):
    sock.sendall((line + "\n").encode())
    sock.settimeout(timeout)
    buf = b""
    while not buf.endswith(b"}\n"):
        try:
            chunk = sock.recv(1 << 20)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
    return buf.decode("utf-8", errors="replace").strip()


def kill_tree(p):
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                   capture_output=True, timeout=10)
    try:
        p.kill()
        p.wait(timeout=5)
    except Exception:
        pass


def drive_to_namescreen(sock, presses=NAME_SCREEN_PRESSES, lead=3, timeout=180):
    """Replicate the recorded A presses frame-accurately via set_controller.

    Polls the debug server `frame` command (snes_frame_counter, which is the
    same in every build) and presses/releases A at the recorded frame
    windows. Lead of `lead` frames accounts for poll latency; the game waits
    indefinitely at each screen so being a couple of frames early is safe.
    Returns True if every press was delivered.
    """
    import json
    done = [False] * len(presses)
    t0 = time.time()
    while not all(done) and time.time() - t0 < timeout:
        try:
            fr = int(json.loads(cmd(sock, "frame"))["frame"])
        except Exception:
            time.sleep(0.01)
            continue
        for i, (pf, rf) in enumerate(presses):
            if done[i]:
                continue
            if fr >= rf:
                cmd(sock, "set_controller 0")
                done[i] = True
            elif fr >= pf - lead:
                cmd(sock, "set_controller 0x%x" % A_MASK)
        time.sleep(0.004)
    return all(done)


def _auto_press_loop(sock, stop_event, hold=0.25, period=2.5):
    """Press A briefly every `period` seconds until stopped. The game waits
    at each menu until you confirm, so periodic presses walk title -> New
    Game -> name selection reliably regardless of boot pacing."""
    while not stop_event.is_set():
        try:
            cmd(sock, "set_controller 0x%x" % A_MASK)
            time.sleep(hold)
            cmd(sock, "set_controller 0")
        except Exception:
            return
        stop_event.wait(period)


def launch_and_drive(exe, rom, log_path=None, auto_a=True, name="probe"):
    """Launch `exe rom` (no input env vars) and connect to the debug server.

    With auto_a=True a background thread presses A every ~2.5s until the
    caller sets the returned stop_event, walking the game to the name screen
    without needing a human (keyboard stays fully live for interactive use).

    Returns (process, sock, stderr_file, stop_event). The caller must stop
    the event, close the sock, kill the process and close the log.
    """
    env = dict(os.environ)
    # Never inherit stale input env vars from a previous session.
    env.pop("SNESRECOMP_INPUT_MODE", None)
    env.pop("SNESRECOMP_INPUT_FILE", None)
    logf = open(log_path, "wb") if log_path else None
    kw = dict(env=env, stdout=subprocess.DEVNULL)
    if logf:
        kw["stderr"] = logf
    p = subprocess.Popen([exe, rom], **kw)
    sock = connect()
    stop_event = threading.Event()
    if sock and auto_a:
        threading.Thread(target=_auto_press_loop, args=(sock, stop_event),
                         daemon=True).start()
    return p, sock, logf, stop_event
