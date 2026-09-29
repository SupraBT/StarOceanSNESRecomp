#!/usr/bin/env python3
"""Overlay a recomp run against the Mesen oracle on the GUEST CLOCK axis.

Why this exists
---------------
A recomp *host frame* is not a hardware frame: one `RunOneFrameOfGame` can
cover many guest frames (Star Ocean's whole boot collapses into a handful of
host frames), so comparing "oracle frame N" with "recomp frame N" measures the
frame driver, not the guest. Both recordings do carry a guest clock though --
the oracle's `cpuCyc`/`master` columns and the recomp's
`[fstate] ... cpu=<cycles> master=<master>` fields -- so aligning the two on
that clock isolates *how much guest time the recomp needs to reach the same
state*, which is what "is the emulation falling behind" actually means.

The tool extracts, from both sides, every change of the observable state
($2100 brightness value `inidisp`, the $4200 register value, and the joypad
word the guest reads) together with the guest clock at that instant, aligns
the two event sequences, and reports per-event deltas plus the local rate
(recomp guest-cycles per oracle guest-cycle) so a phase that runs cheap or
expensive stands out on its own.

Inputs
------
oracle : StarOceanRecompDocumentacion/mesen_oracle.tsv (11 tab columns:
         fr master cpuCyc inidisp w2140 r2140 ram83 spcOut dspw reg4200 pad).
         The file holds the SAME run twice with different column sets; the
         second pass (starts at fr 411) is the one with inidisp/reg4200/pad.
recomp : the stderr log of a dev build run with SNESRECOMP_FRAME_STATE=1.

Usage
-----
    python tools/oracle_overlay.py \
        --oracle "../StarOceanRecompDocumentacion/mesen_oracle.tsv" \
        --recomp build-dev/Release/state.log \
        --csv build-dev/Release/overlay.csv
"""
import argparse
import bisect
import re
import sys

ORACLE_NF = 11
FSTATE_RE = re.compile(
    r"^\[fstate\] f=(\d+) nmiEn=(\d+) resume=([0-9A-F]+) inidisp=([0-9A-F]+) "
    r"cpu=(\d+) master=(\d+) pad=([0-9A-F]+) r4200=([0-9A-F]+)")


def last_token(cell):
    """Oracle cells may carry several writes ('80+0F'): the register value at
    the frame boundary is the last one."""
    cell = cell.strip()
    if not cell:
        return None
    return cell.split('+')[-1].upper()


def parse_oracle(path, pass_index):
    """Return pass `pass_index` of the oracle as a list of dicts, plus stats.

    Pass 1 has no inidisp/reg4200 columns, and the two passes are the same run;
    the second pass is detected as the first row whose frame index goes
    backwards. Rows that are not 11 columns (one line in the shipped file is a
    mangled concatenation) are skipped and counted."""
    rows, skipped, passes_seen = [], 0, 0
    prev_fr = -1
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            fields = line.rstrip("\n").split("\t")
            if lineno == 1 and fields and fields[0].strip() == "fr":
                continue                      # header
            if len(fields) != ORACLE_NF:
                skipped += 1
                continue
            try:
                fr = int(fields[0])
                master = int(fields[1])
                cpu = int(fields[2])
            except ValueError:
                skipped += 1
                continue
            if prev_fr >= 0 and fr < prev_fr:
                passes_seen += 1              # pass boundary (frame index restarts)
            prev_fr = fr
            if passes_seen + 1 != pass_index:
                continue
            rows.append({
                "fr": fr, "master": master, "cpu": cpu,
                "inidisp": last_token(fields[3]),   # $2100
                "r4200": last_token(fields[9]),     # $4200
                "pad": last_token(fields[10]),
            })
    return rows, skipped, passes_seen + 1


def parse_recomp(path):
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = FSTATE_RE.match(line)
            if not m:
                continue
            rows.append({
                "fr": int(m.group(1)), "master": int(m.group(6)),
                "cpu": int(m.group(5)),
                "inidisp": m.group(4).upper(),
                "r4200": m.group(8).upper(),
                "pad": m.group(7).upper(),
            })
    return rows


# Power-on register values. The oracle only logs a register when the game
# writes it, so frames before the first write must be seeded with these
# instead of 'unknown', otherwise the first transitions of the two sides are
# not even comparable ($2100 = 0x80 forced blank, $4200 = 0, pad = 0).
RESET_DEFAULTS = ("80", "00", "0000")


# Channels that take part in the alignment key, and the state-channel order.
# $4200 is REPORTED but not aligned on: the oracle only logs the register when
# the game writes it (4 writes in the whole pass), so the recomp's reconstructed
# byte (which tracks auto-joypad from frame 2) has no comparable counterpart and
# would break every early match.
STATE_CHANNELS = ("inidisp", "r4200", "pad")
# Align on the brightness value alone: it is by far the richest channel (72
# oracle / 114 recomp transitions in the covered span) and its ramps form
# unique chains. The pad is matched separately, by ordinal (see pad_segments),
# because it is sparse and ambiguous by value -- and because a recording's
# presses are known to be the same presses in the same order on both sides.
KEY_CHANNELS = ("inidisp",)


def events(rows, channels=STATE_CHANNELS, defaults=RESET_DEFAULTS):
    """State changes: {cpu, master, fr, state, key}.

    A blank oracle cell means 'no write this frame' = the register keeps its
    value, so blanks do not reset the comparison.

    `key` is the (previous state -> state) TRANSITION, not the state itself:
    the same register values recur in different phases (80|01 during the boot
    and again mid-intro), so matching on states alone pairs unrelated frames.
    Fade ramps then align as a chain of distinct transitions."""
    idx = [channels.index(c) for c in KEY_CHANNELS]

    def key_of(state):
        return tuple(state[i] for i in idx)

    out, prev = [], defaults
    for r in rows:
        state = tuple(r[c] if r[c] is not None else prev[i]
                      for i, c in enumerate(channels))
        if state != prev:
            out.append({"cpu": r["cpu"], "master": r["master"],
                        "fr": r["fr"], "state": state,
                        "key": (key_of(prev), key_of(state))})
            prev = state
    return out


def channel_counts(rows, channels=("inidisp", "r4200", "pad")):
    """Per-channel change counts, for judging whether an alignment has
    enough signal on each axis."""
    counts, last = {c: 0 for c in channels}, {c: None for c in channels}
    for r in rows:
        for c in channels:
            v = r[c]
            if v is None:
                continue
            if v != last[c]:
                counts[c] += 1
                last[c] = v
    return counts


def align(oa, ra, window):
    """Greedy two-pointer alignment of the state-event sequences, with a
    look-ahead resync window so a single extra/missing event on either side
    does not desynchronise the rest. Returns matched pairs plus the unmatched
    event indices on each side."""
    pairs, i, j, skip_o, skip_r = [], 0, 0, set(), set()
    while i < len(oa) and j < len(ra):
        if oa[i]["key"] == ra[j]["key"]:
            pairs.append((i, j))
            i += 1
            j += 1
            continue
        # Which side is ahead? Resync on whichever comes first.
        o_next = next((k for k in range(i + 1, min(i + window, len(oa)))
                       if oa[k]["key"] == ra[j]["key"]), None)
        r_next = next((k for k in range(j + 1, min(j + window, len(ra)))
                       if ra[k]["key"] == oa[i]["key"]), None)
        if o_next is None and r_next is None:
            skip_o.add(i); skip_r.add(j); i += 1; j += 1
        elif r_next is None or (o_next is not None
                                and (o_next - i) <= (r_next - j)):
            for k in range(i, o_next):
                skip_o.add(k)
            i = o_next
        else:
            for k in range(j, r_next):
                skip_r.add(k)
            j = r_next
    while i < len(oa):
        skip_o.add(i); i += 1
    while j < len(ra):
        skip_r.add(j); j += 1
    return pairs, skip_o, skip_r


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--oracle", required=True, help="mesen_oracle.tsv")
    ap.add_argument("--recomp", required=True, help="log with [fstate] lines")
    ap.add_argument("--oracle-pass", type=int, default=2,
                    help="which oracle pass to use (default 2: the one with inidisp)")
    ap.add_argument("--window", type=int, default=40,
                    help="resync look-ahead window in events (default 40)")
    ap.add_argument("--csv", help="also write the matched table as CSV")
    ap.add_argument("--all", action="store_true", help="print every matched row")
    ap.add_argument("--max-rows", type=int, default=40,
                    help="rows to print when --all is not given (default 40)")
    args = ap.parse_args()

    oracle_rows, skipped, n_passes = parse_oracle(args.oracle, args.oracle_pass)
    recomp_rows = parse_recomp(args.recomp)
    if not oracle_rows:
        sys.exit("no oracle rows for pass %d" % args.oracle_pass)
    if not recomp_rows:
        sys.exit("no [fstate] lines in %s (run with SNESRECOMP_FRAME_STATE=1)"
                 % args.recomp)

    # Only compare the oracle frames the recomp run actually covers; otherwise
    # every oracle event past the end of the recomp run shows as 'unmatched'
    # and drowns the real signal. Both master clocks start at power-on.
    horizon = recomp_rows[-1]["master"]
    covered = [r for r in oracle_rows if r["master"] <= horizon]
    dropped = len(oracle_rows) - len(covered)
    oracle_rows = covered

    oa = events(oracle_rows)
    ra = events(recomp_rows)
    pairs, skip_o, skip_r = align(oa, ra, args.window)

    print("oracle: %s  pass %d of %d  rows=%d (skipped malformed=%d, "
          "beyond recomp horizon=%d)  events=%d %s"
          % (args.oracle, args.oracle_pass, n_passes, len(oracle_rows), skipped,
             dropped, len(oa), channel_counts(oracle_rows)))
    print("recomp: %s  frames=%d  events=%d %s"
          % (args.recomp, len(recomp_rows), len(ra), channel_counts(recomp_rows)))
    print("oracle horizon: master<=%d (recomp end)" % horizon)
    print("matched events=%d  unmatched oracle=%d  unmatched recomp=%d"
          % (len(pairs), len(skip_o), len(skip_r)))
    print()

    header = ("  #  oracle(fr  cpu        master        state)            "
              "recomp(f   cpu        master        state)            "
              "d_cpu      rate_cpu  skip(o/r)")
    print(header)
    print("-" * len(header))
    skip_o_sorted = sorted(skip_o)
    skip_r_sorted = sorted(skip_r)

    def skipped_between(sorted_skips, lo, hi):
        return bisect.bisect_left(sorted_skips, hi) - bisect.bisect_right(sorted_skips, lo)

    def key_changing_skips(events_list, lo, hi):
        """Skipped events that actually move the alignment channel. An event
        that only changes $4200 does not affect a brightness-axis comparison, so
        it must not invalidate the interval's rate."""
        return sum(1 for k in range(lo + 1, hi)
                   if events_list[k]["key"][0] != events_list[k]["key"][1])

    table = []
    prev_pair = None
    for n, (i, j) in enumerate(pairs):
        o, r = oa[i], ra[j]
        d_cpu = r["cpu"] - o["cpu"]
        d_master = r["master"] - o["master"]
        # State events that exist on one side only between the previous matched
        # pair and this one: an interval with skips is not a clean A->B phase,
        # so its rate must not be read as a pacing factor.
        s_o = s_r = k_o = k_r = 0
        if prev_pair is not None:
            s_o = skipped_between(skip_o_sorted, prev_pair[0], i)
            s_r = skipped_between(skip_r_sorted, prev_pair[1], j)
            k_o = key_changing_skips(oa, prev_pair[0], i)
            k_r = key_changing_skips(ra, prev_pair[1], j)
        rate = ""
        if prev_pair is not None:
            dc_o = o["cpu"] - prev_pair[2]["cpu"]
            dc_r = r["cpu"] - prev_pair[3]["cpu"]
            if dc_o > 0:
                rate = "%.3f" % (dc_r / dc_o)
        row = {
            "n": n,
            "oracle_fr": o["fr"], "oracle_cpu": o["cpu"], "oracle_master": o["master"],
            "oracle_state": "|".join(o["state"]),
            "recomp_f": r["fr"], "recomp_cpu": r["cpu"], "recomp_master": r["master"],
            "recomp_state": "|".join(r["state"]),
            "d_cpu": d_cpu, "d_master": d_master, "rate_cpu": rate,
            "skip_o": s_o, "skip_r": s_r,
            "key_skip_o": k_o, "key_skip_r": k_r,
            "clean": (k_o == 0 and k_r == 0),
        }
        table.append(row)
        prev_pair = (i, j, o, r)

    show = table if args.all else (table[:args.max_rows // 2] + table[-args.max_rows // 2:]
                                   if len(table) > args.max_rows else table)
    for row in show:
        print("%4d  %6d %11d %13d %-12s   %6d %11d %13d %-12s %10d  %-9s %d/%d%s"
              % (row["n"], row["oracle_fr"], row["oracle_cpu"], row["oracle_master"],
                 row["oracle_state"], row["recomp_f"], row["recomp_cpu"],
                 row["recomp_master"], row["recomp_state"], row["d_cpu"],
                 row["rate_cpu"], row["skip_o"], row["skip_r"],
                 "" if row["clean"] else " *"))
    if not args.all and len(table) > args.max_rows:
        print("... (%d rows omitted, use --all or --csv)" % (len(table) - len(show)))
    print("* interval contains state events present on one side only: its rate")
    print("  is an artefact of the alignment, not a pacing measurement.")

    # ── where the asymmetry lives ─────────────────────────────────────────
    def rate(a, b):
        dc_o = b["oracle_cpu"] - a["oracle_cpu"]
        dc_r = b["recomp_cpu"] - a["recomp_cpu"]
        return (dc_r / dc_o) if dc_o > 0 else None

    rated = []
    for n in range(1, len(table)):
        prev_row, row = table[n - 1], table[n]
        r = rate(prev_row, row)
        if r is not None:
            rated.append((r, prev_row, row))
    clean = [t for t in rated if t[1]["clean"] and t[2]["clean"]]
    rates = sorted(clean, key=lambda t: t[0])
    print("\nlocal rate (recomp guest cycles per oracle guest cycle):")
    print("  intervals=%d  clean=%d  rated-but-ambiguous=%d"
          % (len(rated), len(clean), len(rated) - len(clean)))
    if rates:
        med = rates[len(rates) // 2][0]
        print("  clean intervals: min=%.3f  median=%.3f  max=%.3f"
              % (rates[0][0], med, rates[-1][0]))
        print("  (1.000 = the recomp needs exactly the guest time hardware needs")
        print("   for the same state change)")
        print("\ncheapest clean phases (recomp spends far less guest time):")
        for r, a, b in rates[:6]:
            print("  rate %.3f  oracle fr %d->%d (%s -> %s)  cpu %d->%d  "
                  "recomp hostf %d->%d" % (r, a["oracle_fr"], b["oracle_fr"],
                                           a["oracle_state"], b["oracle_state"],
                                           a["oracle_cpu"], b["oracle_cpu"],
                                           a["recomp_f"], b["recomp_f"]))
        print("\nmost expensive clean phases (recomp spends far more guest time):")
        for r, a, b in rates[-6:][::-1]:
            print("  rate %.3f  oracle fr %d->%d (%s -> %s)  cpu %d->%d  "
                  "recomp hostf %d->%d" % (r, a["oracle_fr"], b["oracle_fr"],
                                           a["oracle_state"], b["oracle_state"],
                                           a["oracle_cpu"], b["oracle_cpu"],
                                           a["recomp_f"], b["recomp_f"]))

    # ── input timing check (the replay's whole point) ─────────────────────
    # Matched by ordinal, not by the state aligner: the i-th press on one side
    # is the i-th press on the other, which removes all ambiguity and answers
    # exactly the question the replay exists for -- does a press land at the
    # same guest instant it was recorded at?
    def pad_segments(rows):
        segs, open_seg = [], None
        for r in rows:
            held = r["pad"] not in (None, "0000")
            if held and open_seg is None:
                open_seg = {"start": r, "n": 0}
            if held:
                open_seg["n"] += 1
            elif open_seg is not None:
                open_seg["end"] = r
                segs.append(open_seg)
                open_seg = None
        if open_seg is not None:
            open_seg["end"] = rows[-1]
            segs.append(open_seg)
        return segs

    o_pads, r_pads = pad_segments(oracle_rows), pad_segments(recomp_rows)
    print("\npad (input) events, matched by ordinal:")
    print("  oracle presses=%d  recomp presses=%d" % (len(o_pads), len(r_pads)))
    for k in range(min(len(o_pads), len(r_pads))):
        op, rp = o_pads[k], r_pads[k]
        delta = rp["start"]["cpu"] - op["start"]["cpu"]
        print("  press %d: oracle fr %d cpu %d (held %d frames)  <->  recomp hostf %d "
              "cpu %d (held %d frames)   d_cpu %+d"
              % (k + 1, op["start"]["fr"], op["start"]["cpu"], op["n"],
                 rp["start"]["fr"], rp["start"]["cpu"], rp["n"], delta))

    if args.csv and table:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = __import__("csv").DictWriter(fh, fieldnames=list(table[0].keys()))
            w.writeheader()
            w.writerows(table)
        print("\nwrote %s (%d rows)" % (args.csv, len(table)))


if __name__ == "__main__":
    main()
