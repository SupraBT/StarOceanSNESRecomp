#!/usr/bin/env python3
"""TCP probe for the debug server (line protocol, one client at a time).

Usage:
  python tcp_probe.py "audio_stats" "audio_wav C:\\path\\out.wav -1 0" ...
Each command is sent as a line; replies are printed separated by a marker.
"""
import socket, sys, time

HOST, PORT = "127.0.0.1", 13308


def recv_line(sock):
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = sock.recv(65536)
        if not chunk:
            break
        buf += chunk
    return buf.decode(errors="replace").strip()


def run_cmds(cmds, timeout=60):
    s = socket.create_connection((HOST, PORT), timeout=timeout)
    s.settimeout(timeout)
    for c in cmds:
        s.sendall((c + "\n").encode())
        line = recv_line(s)
        print("CMD : %s" % c)
        print("REPL: %s" % line)
        print("----")
    s.close()


if __name__ == "__main__":
    cmds = sys.argv[1:]
    if not cmds:
        print("no commands")
        sys.exit(1)
    run_cmds(cmds)
