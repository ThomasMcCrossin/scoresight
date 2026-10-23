#!/usr/bin/env python3
"""Build the qualification's pass/fail table from the reports on disk.

Reads the scored runs (run_eval.py: fork-filtered, fork-levels, upstream as the
control) and the replay reports (replay_1010.py + check_incidents.py) and
writes one markdown page stating each check, its numbers, and pass/fail
against the brief's bar. Nothing here measures anything itself: it is a
reading of the reports, so a reader can go to the report behind any cell.

    nice -n 15 .venv/bin/python eval_canteen/qualify_report.py \\
        --out eval_canteen/reports/QUALIFICATION.md
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import check_incidents  # noqa: E402

REPORTS = os.path.join(HERE, "reports")
# the brief's bar
LATENCY_SLACK = 0.5
FIELDS = ("period", "home", "away", "clock")


def load(path):
    with open(path) as handle:
        return json.load(handle)


def scored(path):
    """The scored run's meta and result, with the per-field numbers."""
    data = load(path)
    meta, result = data["meta"], data["result"]
    return {
        "name": meta.get("name"),
        "build": os.path.basename(os.path.dirname(meta.get("build") or ""))
        or meta.get("build"),
        "variant": meta.get("variant"),
        "engine": meta.get("engine"),
        "path": os.path.relpath(path, os.path.dirname(REPORTS)),
        "fields": {
            key: {
                "accuracy": result["fields"][key]["accuracy"],
                "wrong": result["fields"][key]["wrong"],
                "unknown": result["fields"][key]["unknown"],
                "unknown_rate": result["fields"][key]["unknown_rate"],
            }
            for key in FIELDS
        },
        "transitions": result["transitions"],
        "offset": result.get("offset_seconds"),
        "samples": result.get("samples"),
    }


def pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def transition_row(transitions, kind):
    row = transitions.get(kind) or {}
    if not row:
        return "—"
    lat = row.get("mean_latency")
    lat = "n/a" if lat is None else f"{lat:+.1f}s"
    return (
        f"{row.get('detected', 0)}/{row.get('expected', 0)} detected, "
        f"{row.get('false', 0)} false, {lat}"
    )


def replay_files():
    return sorted(glob.glob(os.path.join(REPORTS, "work", "replay", "*.json")))


def replay_rows(paths):
    rows = []
    for path in paths:
        report = load(path)
        results, verdict = check_incidents.summarise(report)
        rows.append(
            {
                "name": report.get("name"),
                "build": "upstream" if "upstream" in (report.get("build") or "") else "fork",
                "variant": report.get("variant"),
                "window": [report.get("start_media"), report.get("duration")],
                "clip": report.get("clip"),
                "path": os.path.relpath(path, os.path.dirname(REPORTS)),
                "verdict": verdict,
                "detail": results,
            }
        )
    return rows


def merged_verdict(rows, build):
    """One build's answers across its runs, for the incidents each covers."""
    out = {"a": None, "b": None, "c": None, "goals": [], "false": []}
    for row in rows:
        if row["build"] != build:
            continue
        verdict = row["verdict"]
        if "a" in verdict:
            out["a"] = verdict["a"]
        if "b" in verdict:
            out["b"] = verdict["b"]
        if "c" in verdict:
            out["c"] = verdict["c"]
        goals = verdict.get("d")
        if goals:
            out["goals"].append(goals)
            detail = row["detail"]["d"]
            out["false"].extend(detail["false_scores"])
    return out


def field_check(base, run):
    """No field accuracy below the baseline, and no new false score events."""
    failures = []
    for key in FIELDS:
        lo = base["fields"][key]["accuracy"]
        hi = run["fields"][key]["accuracy"]
        if lo is not None and hi is not None and hi < lo - 1e-9:
            failures.append(
                f"{key} accuracy {pct(hi)} below the baseline's {pct(lo)}"
            )
    for kind in ("score_home", "score_away"):
        lo = base["transitions"].get(kind) or {}
        hi = run["transitions"].get(kind) or {}
        if hi.get("false", 0) > lo.get("false", 0):
            failures.append(
                f"{kind} false events {hi.get('false', 0)} "
                f"(baseline {lo.get('false', 0)})"
            )
    return failures


def latency_check(base, run):
    """No transition latency worse than the baseline's by more than 0.5 s."""
    failures = []
    for kind, row in run["transitions"].items():
        lo = (base["transitions"].get(kind) or {}).get("mean_latency")
        hi = row.get("mean_latency")
        if lo is None or hi is None:
            continue
        if hi > lo + LATENCY_SLACK:
            failures.append(
                f"{kind} mean latency {hi:+.2f}s vs baseline {lo:+.2f}s"
            )
    return failures


def cell(ok):
    return "PASS" if ok else "FAIL"


def render(scored_runs, replays):
    base = next((r for r in scored_runs if r["variant"] == "filtered" and r["build"] == "upstream"), None)
    fork_f = next((r for r in scored_runs if r["variant"] == "filtered" and r["build"] != "upstream"), None)
    fork_l = next((r for r in scored_runs if r["variant"] == "levels"), None)
    lines = ["# Curly's ScoreSight fork — qualification", ""]
    if not scored_runs:
        lines.append("No scored reports yet.")
        return "\n".join(lines)

    lines += ["## Scored runs (09:10 clip, first 900 s)", ""]
    labels = [r for r in (base, fork_f, fork_l) if r]
    header = "| measure | " + " | ".join(
        f"{r['variant']}/{r['engine']} ({r['build']})" for r in labels
    ) + " |"
    lines += [header, "|---" * (len(labels) + 1) + "|"]
    lines.append("| build | " + " | ".join(f"`{r['build']}`" for r in labels) + " |")
    lines.append("| offset (s) | " + " | ".join(str(r["offset"]) for r in labels) + " |")
    for key, name in (
        ("period", "Period"),
        ("home", "Home Score"),
        ("away", "Away Score"),
        ("clock", "Time"),
    ):
        cells = []
        for run in labels:
            field = run["fields"][key]
            cells.append(
                f"{pct(field['accuracy'])} (wrong {field['wrong']}, "
                f"unknown {pct(field['unknown_rate'])})"
            )
        lines.append(f"| {name} accuracy | " + " | ".join(cells) + " |")
    for kind in ("score_home", "clock_start", "clock_stop"):
        lines.append(
            f"| {kind} | "
            + " | ".join(transition_row(r["transitions"], kind) for r in labels)
            + " |"
        )
    lines.append("")

    if base and fork_f and fork_l:
        lines += ["## Checks against the baseline", ""]
        checks = []
        f_fail = field_check(base, fork_f)
        l_fail = field_check(base, fork_l)
        checks.append(
            ("No field accuracy below the baseline (filtered)", not f_fail, f_fail)
        )
        checks.append(
            ("No field accuracy below the baseline (levels)", not l_fail, l_fail)
        )
        lat_f = latency_check(base, fork_f)
        lat_l = latency_check(base, fork_l)
        checks.append(("No latency worse by > 0.5 s (filtered)", not lat_f, lat_f))
        checks.append(("No latency worse by > 0.5 s (levels)", not lat_l, lat_l))
        lines += ["| check | verdict | notes |", "|---|---|---|"]
        for label, ok, notes in checks:
            lines.append(
                f"| {label} | {cell(ok)} | {'; '.join(notes) if notes else '—'} |"
            )
        lines.append("")

    if replays:
        lines += ["## Incident replays (10:10 hour, filtered)", ""]
        lines += [
            "| incident | upstream 0.4.1 | fork | evidence |",
            "|---|---|---|---|",
        ]
        up = merged_verdict(replays, "upstream")
        fk = merged_verdict(replays, "fork")

        def a_text(v):
            if not v:
                return "not replayed"
            return (
                f"engine vs board {v['engine_vs_board']} s, "
                f"freeze {v['longest_freeze_s']} s"
            )

        def b_text(v):
            if not v:
                return "not replayed"
            return (
                f"new_game {v['new_game']}, OT {v['overtime_events']}, "
                f"corrections {v['score_corrections']}"
            )

        def c_text(v):
            if not v:
                return "not replayed"
            return f"period_end {v['period_end']}, period_start {v['period_start']}"

        def d_text(v):
            if not v:
                return "not replayed"
            matched = sum(g["matched"] for g in v["goals"])
            wanted = sum(g["wanted"] for g in v["goals"])
            return f"{matched}/{wanted} goals, {len(v['false'])} false"

        lines.append(f"| a clock followed | {a_text(up['a'])} | {a_text(fk['a'])} | frames |")
        lines.append(
            f"| b new game, no OT/correction | {b_text(up['b'])} | {b_text(fk['b'])} | frames |"
        )
        lines.append(
            f"| c no period end on a flick | {c_text(up['c'])} | {c_text(fk['c'])} | frames + /game |"
        )
        lines.append(f"| d goals | {d_text(up)} | {d_text(fk)} | frames |")
        lines.append("")
        lines += ["Replay reports:", ""]
        for row in replays:
            lines.append(
                f"- `{row['name']}` ({row['build']}, media "
                f"{row['window'][0]:.0f}s +{row['window'][1]:.0f}s) — `{row['path']}`"
            )
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default=os.path.join(REPORTS, "QUALIFICATION.md"))
    args = parser.parse_args(argv)
    scored_paths = sorted(glob.glob(os.path.join(REPORTS, "qualify_*.json")))
    scored_runs = [scored(path) for path in scored_paths]
    replays = replay_rows(
        [path for path in replay_files() if "probe" not in os.path.basename(path)]
    )
    text = render(scored_runs, replays)
    with open(args.out, "w") as handle:
        handle.write(text + "\n")
    print(text)
    print(f"[qualify] written {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
