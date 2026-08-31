#!/usr/bin/env python3
"""Extract an extended, chronological bsnes-plus trace window.

bsnes-plus traces are CPU-instruction traces. This tool preserves every CPU
line and classifies register accesses visible in the instruction text. It
cannot invent DMA/HDMA events that the source trace does not contain; those
are reported as CPU writes to $420B/$420C and $43xx plus NMI/IRQ vector/PC
activity. Use --start-line/--end-line or --until-text to delimit the capture.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CPU_RE = re.compile(
    r"^(?P<pc>[0-9a-fA-F]{6})\s+(?P<op>.*?)\s+"
    r"A:(?P<a>[0-9a-fA-F]{4})\s+X:(?P<x>[0-9a-fA-F]{4})\s+Y:(?P<y>[0-9a-fA-F]{4})\s+"
    r"S:(?P<s>[0-9a-fA-F]{4})\s+D:(?P<d>[0-9a-fA-F]{4})\s+DB:(?P<db>[0-9a-fA-F]{2})\s+"
    r"(?P<flags>[NVOQM\.DCZ]{8})\s+V:(?P<v>\d+)\s+H:\s*(?P<h>\d+)\s+F:(?P<f>\d+)"
)
ADDR_RE = re.compile(r"\$(?P<addr>[0-9a-fA-F]{4})")


def category(addr: int, op: str) -> str | None:
    if 0x2100 <= addr <= 0x2133:
        return "ppu"
    if 0x4200 <= addr <= 0x420D:
        return "timing_dma_control"
    if 0x4300 <= addr <= 0x437F:
        return "dma_channel"
    if addr in (0x4016, 0x4218, 0x4219):
        return "joypad"
    if addr in (0xFFEA, 0xFFEB, 0xFFEE, 0xFFEF):
        return "interrupt_vector"
    if op.lower().startswith(("nmi", "irq")):
        return "interrupt"
    return None


def extract(path: Path, start_line: int, end_line: int | None, until: str | None) -> tuple[list[dict], dict]:
    events: list[dict] = []
    counts: dict[str, int] = {}
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for number, line in enumerate(stream):
            if number < start_line:
                continue
            if end_line is not None and number >= end_line:
                break
            if until and until in line:
                break
            match = CPU_RE.match(line.rstrip("\r\n"))
            if not match:
                continue
            op = match.group("op").strip()
            addresses = [int(m.group("addr"), 16) for m in ADDR_RE.finditer(op)]
            categories = sorted({c for addr in addresses if (c := category(addr, op))})
            if not categories and op.lower().startswith(("nmi", "irq")):
                categories = ["interrupt"]
            if not categories:
                continue
            event = {
                "line": number,
                "pc": int(match.group("pc"), 16),
                "op": op,
                "a": int(match.group("a"), 16),
                "x": int(match.group("x"), 16),
                "y": int(match.group("y"), 16),
                "s": int(match.group("s"), 16),
                "d": int(match.group("d"), 16),
                "db": int(match.group("db"), 16),
                "flags": match.group("flags"),
                "v": int(match.group("v")),
                "h": int(match.group("h")),
                "f": int(match.group("f")),
                "addresses": addresses,
                "categories": categories,
                "raw": line.rstrip("\r\n"),
            }
            events.append(event)
            for c in categories:
                counts[c] = counts.get(c, 0) + 1
    return events, counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument("--start-line", type=int, default=0)
    parser.add_argument("--end-line", type=int)
    parser.add_argument("--until-text")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    events, counts = extract(args.trace, args.start_line, args.end_line, args.until_text)
    result = {
        "source": str(args.trace),
        "start_line": args.start_line,
        "end_line": args.end_line,
        "until_text": args.until_text,
        "event_count": len(events),
        "counts": counts,
        "events": events,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"events": len(events), "counts": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
