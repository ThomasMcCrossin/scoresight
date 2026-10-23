#!/usr/bin/env python3
"""Answer the 10:10 hour's incidents from a replay's samples.

Reads the report ``replay_1010.py`` writes and prints, per incident, what the
engine's /game and /json said at each step, so the pass/fail is a reading of
the record rather than of a log's prose:

* (a) the clock: the readings and ``clock_running`` across the span the live
  service froze in, and whether the clock kept step with the board;
* (b) the final and the new game: the events after the final, with the
  overtime and correction the live service logged named if they appear;
* (c) the pre-game clock flick: whether a period ended (or the period number
  moved) while the board was only being set up;
* (d) every goal: each detected score event with its media time, home/away and
  the value, against the expected list.

    nice -n 15 .venv/bin/python eval_canteen/check_incidents.py \\
        --report .../b_fork.json --incident b
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

SEGMENT_START = "2026-10-23T10:10:23-03:00"

# The goals of the hour, at the media time of the goal (the board changed), from
# the frames. The live service's detection times are 0.3-0.9 s later.
GOALS = (
    (3539.0, "home", 5),   # 10:09:24 ADT (in the 09:10 segment)
    (359.0, "home", 6),    # 10:16:22
    (408.0, "home", 7),    # 10:17:11
    (1280.0, "away", 1),   # 10:31:43
    (1413.0, "away", 2),   # 10:33:56
    (1811.0, "away", 3),   # 10:40:34
    (2237.0, "away", 4),   # 10:47:40
)

# incident spans, media seconds
INCIDENTS = {
    "a": {"label": "clock frozen at 5:15 while the board ran", "from": 300, "to": 720},
    "b": {"label": "final, then a board set for the next game", "from": 660, "to": 840},
    "c": {"label": "clock set up before the game", "from": 1030, "to": 1064},
}


def adt(media):
    start = datetime.fromisoformat(SEGMENT_START)
    return (start + timedelta(seconds=media)).strftime("%H:%M:%S")


def load(path):
    with open(path) as handle:
        return json.load(handle)


def events_of(samples):
    """Every event once, in id order, with the media time it was first polled."""
    seen = {}
    for sample in samples:
        for event in (sample.get("game") or {}).get("events") or sample.get(
            "events"
        ) or []:
            if event.get("id") not in seen:
                event = dict(event)
                event["media"] = sample.get("media")
                seen[event["id"]] = event
    return [seen[key] for key in sorted(seen)]


def clock_table(samples, start, stop):
    rows = []
    for sample in samples:
        media = sample.get("media")
        if media is None or not (start <= media <= stop):
            continue
        game = sample.get("game") or {}
        clock = (sample.get("readings") or {}).get("Time", {}).get("text")
        rows.append((media, game.get("clock"), game.get("clock_running"), clock))
    return rows


def check_a(report):
    samples = report["samples"]
    span = INCIDENTS["a"]
    rows = clock_table(samples, span["from"], span["to"])
    stale = 0
    for index in range(1, len(rows)):
        media, engine, running, board = rows[index]
        prev = rows[index - 1]
        if engine and prev[1] and engine == prev[1] and (media - prev[0]) >= 4.0:
            stale += 1
    # how long the engine's clock stood still while the board moved
    held = []
    hold_start = None
    for media, engine, running, board in rows:
        if engine and board and engine != board:
            if hold_start is None:
                hold_start = media
            held.append((media, engine, board))
        else:
            hold_start = None
    worst = max((stop - start for start, stop in _runs(rows)), default=0.0)
    return {
        "samples": len(rows),
        "stale_readings": stale,
        "worst_frozen_span": round(worst, 1),
        "engine_behind_board": [
            {"media": round(m, 1), "engine": e, "board": b} for m, e, b in held
        ][:20],
    }


def _runs(rows):
    """Spans where the engine's clock did not change while samples kept coming."""
    spans = []
    start = None
    last = None
    for media, engine, running, board in rows:
        if last is not None and engine is not None and engine == last:
            if start is None:
                start = prev_media
        else:
            if start is not None:
                spans.append((start, prev_media))
            start = None
        prev_media = media
        last = engine
    if start is not None and last is not None:
        spans.append((start, prev_media))
    return spans


def check_b(report):
    samples = report["samples"]
    span = INCIDENTS["b"]
    events = [e for e in events_of(samples) if (e.get("media") or 0) >= span["from"]]
    kinds = [e.get("kind") for e in events]
    return {
        "events_after_final": [
            {
                "media": round(e["media"], 1) if e.get("media") else None,
                "adt": adt(e["media"]) if e.get("media") else None,
                "kind": e.get("kind"),
                "text": e.get("text"),
            }
            for e in events
        ],
        "new_game": kinds.count("new_game"),
        "period_end": sum(1 for k in kinds if k == "period_end"),
        "score_corrected": sum(
            1
            for e in events
            if e.get("kind") == "score" and (e.get("delta") or 0) < 0
        ),
        "period_start": sum(1 for k in kinds if k == "period_start"),
        "final_at": [
            {"media": round(e["media"], 1), "adt": adt(e["media"])}
            for e in events
            if e.get("kind") == "final"
        ],
    }


def check_c(report):
    samples = report["samples"]
    span = INCIDENTS["c"]
    rows = clock_table(samples, span["from"], span["to"])
    events = [
        e
        for e in events_of(samples)
        if span["from"] <= (e.get("media") or 0) <= span["to"]
    ]
    periods = sorted({r[1] for r in [] if False})
    return {
        "clock_readings": [
            {"media": round(m, 1), "adt": adt(m), "board": b} for m, e, r, b in rows
        ],
        "events": [
            {
                "media": round(e["media"], 1) if e.get("media") else None,
                "kind": e.get("kind"),
                "text": e.get("text"),
            }
            for e in events
        ],
        "period_end": sum(1 for e in events if e.get("kind") == "period_end"),
    }


def check_d(report):
    events = events_of(report["samples"])
    scores = [
        e for e in events if e.get("kind") == "score" and (e.get("delta") or 0) > 0
    ]
    matched = []
    used = set()
    for media, team, value in GOALS:
        best = None
        for index, event in enumerate(scores):
            if index in used or event.get("team") != team:
                continue
            distance = abs((event.get("media") or 0) - media)
            if best is None or distance < best[1]:
                best = (index, distance)
        if best and best[1] <= 25.0:
            used.add(best[0])
            matched.append(
                {
                    "want_media": media,
                    "want": f"{team} {value}",
                    "got_media": round(scores[best[0]]["media"], 1),
                    "delta_s": round(scores[best[0]]["media"] - media, 1),
                    "got": f"{scores[best[0]].get('team')} {scores[best[0]].get('value')}",
                }
            )
        else:
            matched.append(
                {"want_media": media, "want": f"{team} {value}", "got": None}
            )
    extra = [
        {
            "media": round(s.get("media"), 1),
            "adt": adt(s.get("media")),
            "team": s.get("team"),
            "value": s.get("value"),
        }
        for index, s in enumerate(scores)
        if index not in used
    ]
    return {"goals": matched, "false_scores": extra, "detected": len(scores)}


CHECKS = {"a": check_a, "b": check_b, "c": check_c, "d": check_d}


def render(name, path, report, results):
    lines = [
        f"# Replay incidents — {name}",
        "",
        f"| | |",
        f"|---|---|",
        f"| build | `{report.get('build')}` |",
        f"| variant | {report.get('variant')} |",
        f"| clip | {report.get('clip')} |",
        f"| media | {report.get('start_media'):.0f}-"
        f"{report.get('start_media') + report.get('duration'):.0f} s |",
        f"| samples | {len(report.get('samples') or [])} |",
        "",
    ]
    for key in sorted(results):
        result = results[key]
        lines.append(f"## Incident {key} — {INCIDENTS[key]['label']}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(result, indent=1))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--report", required=True)
    parser.add_argument("--incident", nargs="+", default=sorted(CHECKS))
    parser.add_argument("--md", action="store_true", help="write a .md beside it")
    args = parser.parse_args(argv)
    report = load(args.report)
    results = {key: CHECKS[key](report) for key in args.incident}
    print(
        json.dumps(
            {
                "report": args.report,
                "build": report.get("build"),
                "variant": report.get("variant"),
                "results": results,
            },
            indent=1,
        )
    )
    if args.md:
        path = os.path.splitext(args.report)[0] + ".md"
        name = os.path.splitext(os.path.basename(args.report))[0]
        with open(path, "w") as handle:
            handle.write(render(name, path, report, results))
        print(f"[incidents] written {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
