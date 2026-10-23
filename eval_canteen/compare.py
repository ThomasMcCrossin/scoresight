#!/usr/bin/env python3
"""Compare eval reports side by side (one column per run).

    nice -n 15 python eval_canteen/compare.py eval_canteen/reports/*.json

Prints a markdown table: per-field accuracy and unknown rate, and each
transition's detected/missed/false counts and mean latency, so a ScoreSight
change can be compared against the run it is meant to improve.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

FIELDS = ("period", "home", "away", "clock")
KINDS = ("score_home", "score_away", "period_start", "clock_start", "clock_stop")


def _label(meta):
    return f"{meta.get('variant')}/{meta.get('engine')}"


def _pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def load(paths):
    reports = []
    for path in paths:
        with open(path) as handle:
            data = json.load(handle)
        if "result" not in data or "fields" not in data["result"]:
            continue
        reports.append(data)
    return reports


def render(reports):
    labels = [_label(r["meta"]) for r in reports]
    lines = []
    lines.append("| measure | " + " | ".join(labels) + " |")
    lines.append("|---" * (len(reports) + 1) + "|")
    lines.append(
        "| samples | "
        + " | ".join(str(r["result"].get("samples", "")) for r in reports)
        + " |"
    )
    lines.append(
        "| offset (s) | "
        + " | ".join(str(r["result"].get("offset_seconds", "")) for r in reports)
        + " |"
    )
    for key in FIELDS:
        name = reports[0]["result"]["fields"][key]["name"]
        cells = []
        for report in reports:
            row = report["result"]["fields"][key]
            cells.append(
                f"{_pct(row['accuracy'])} (wrong {row['wrong']}, "
                f"unknown {_pct(row['unknown_rate'])})"
            )
        lines.append(f"| {name} accuracy | " + " | ".join(cells) + " |")
    for kind in KINDS:
        if not any(kind in r["result"]["transitions"] for r in reports):
            continue
        cells = []
        for report in reports:
            row = report["result"]["transitions"].get(kind)
            if row is None:
                cells.append("—")
                continue
            latency = (
                "n/a" if row["mean_latency"] is None else f"{row['mean_latency']:+.1f}s"
            )
            cells.append(
                f"{row['detected']}/{row['expected']} detected, "
                f"{row['false']} false, {latency}"
            )
        lines.append(f"| {kind} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("reports", nargs="+", help="report JSON files")
    parser.add_argument("--out", default=None, help="also write the table here")
    args = parser.parse_args(argv)
    reports = load([os.path.expanduser(p) for p in args.reports])
    if not reports:
        raise SystemExit("no reports with a result")
    table = render(reports)
    print(table)
    if args.out:
        with open(args.out, "w") as handle:
            handle.write(table + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
