#!/usr/bin/env python3
"""Answer the 10:10 hour's incidents from a replay's samples.

Reads the report ``replay_1010.py`` writes and prints, for whichever incidents
fall inside the run's window, a verdict that can be checked against the frames:

* **a** the clock: the largest difference between the engine's clock (/game)
  and the board as read (/json), and how long the engine's clock stood still
  while the board's moved -- the live service froze at 5:15 for minutes.
* **b** the final and the next game's board: the events after the final, and
  whether any of them is an overtime period (a period label with OT) or a score
  correction, both of which the live service logged while the operator set the
  board up for the next game.
* **c** the clock set up before the game: a period ended (or the period moved)
  between the run-down to 0:00 and the reset to 15:00, which is the live
  service's "End of P1" at 10:27:51.
* **d** every goal: each detected score event against the list verified on
  frames, and the false ones.

    nice -n 15 .venv/bin/python eval_canteen/check_incidents.py \\
        --report .../fork_a_330_660.json --md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta

# media seconds -> ADT, per clip (the clips are named by their segment start)
SEGMENT_START = {
    "20261023T091022.mkv": "2026-10-23T09:10:22-03:00",
    "20261023T101023.mkv": "2026-10-23T10:10:23-03:00",
}

# The goals, at the media time of the frame where the score changed, checked
# by viewing the frames (see eval_canteen/reports/evidence/). The live service
# detected each 0-8 s later.
# Every goal of the hour is the HOME team's: the Hawks wore home white and the
# Predators away dark, and both the frames and the live service's log
# ("Home +1") say so. The brief called the 10:31 onward goals "Hawks", which
# is the same team -- not the away score.
GOALS = {
    "20261023T091022.mkv": [(3545.0, "home", 5, "10:09:24 live")],
    "20261023T101023.mkv": [
        (359.0, "home", 6, "10:16:22 live"),
        (408.0, "home", 7, "10:17:11 live, a ~8 s late detection"),
        (1280.0, "home", 1, "10:31:43 live; GUEST stays 0 on the frames"),
        (1412.0, "home", 2, "10:33:56 live; GUEST stays 0 on the frames"),
        (1812.0, "home", 3, "10:40:43 live; frames 2 at 1808, 3 at 1812"),
        (2237.0, "home", 4, "10:47:51 live; frames 3 at 2234, 4 at 2237"),
    ],
}

# incidents, as media seconds; the window each needs
INCIDENTS = {
    # the spans the replay windows cover: the live service froze from media 341
    # (10:16:04) to 564 (10:19:47), its new-game misfire ran 660-820, and its
    # "End of P1" was media 1048 (10:27:51)
    "a": {"label": "clock frozen at 5:15 while the board ran", "from": 330, "to": 650},
    "b": {"label": "final, then a board set for the next game", "from": 660, "to": 845},
    "c": {"label": "clock set up before the game", "from": 1028, "to": 1065},
}
GOAL_WINDOW = 25.0
_CLOCK = re.compile(r"(?:(\d{1,3}):)?(\d{1,2})(?:[.,](\d{1,2}))?")


def adt(clip, media):
    start = datetime.fromisoformat(SEGMENT_START[clip])
    return (start + timedelta(seconds=media)).strftime("%H:%M:%S")


def parse_clock(text):
    """Seconds for a board clock ("5:15" -> 315, "0.0" -> 0.0), or None."""
    text = (text or "").strip().replace(" ", "")
    if not text:
        return None
    match = _CLOCK.fullmatch(text)
    if not match:
        return None
    minutes = int(match.group(1) or 0)
    seconds = int(match.group(2))
    fraction = match.group(3)
    value = minutes * 60 + seconds
    if fraction:
        value += int(fraction) / (10 ** len(fraction))
    return float(value)


def events_of(samples):
    """Every event once, oldest first, with the media time it was first seen."""
    seen = {}
    for sample in samples:
        for event in sample.get("events") or (sample.get("game") or {}).get(
            "events"
        ) or []:
            key = event.get("id")
            if key is not None and key not in seen:
                event = dict(event)
                event["media"] = sample.get("media")
                seen[key] = event
    return [seen[key] for key in sorted(seen)]


def _score(game, side):
    value = (game or {}).get(side)
    return value.get("score") if isinstance(value, dict) else value


def _period_number(label):
    """The period number a "Start of P1"/"End of P3" label names, or None."""
    match = re.search(r"(?:^|\b)(?:P|Q|H|OT|SET)\s*(\d*)", label or "", re.I)
    if not match:
        return None
    return int(match.group(1)) if match.group(1) else "OT"


def check_a(report):
    span = INCIDENTS["a"]
    rows = []
    for sample in report["samples"]:
        media = sample.get("media")
        if media is None or not (span["from"] <= media <= span["to"]):
            continue
        game = sample.get("game") or {}
        board = parse_clock((sample.get("readings") or {}).get("Time", {}).get("text"))
        engine = parse_clock(game.get("clock"))
        rows.append((media, engine, board, game.get("clock_running")))
    # the engine's clock against the board's, both in seconds
    behind = [
        (media, engine, board)
        for media, engine, board, _ in rows
        if engine is not None and board is not None
    ]
    worst = max(behind, key=lambda row: abs(row[1] - row[2])) if behind else None
    # the longest stretch where the engine's clock did not change while the
    # board's did (the freeze), measured between the first and last sample
    freeze_start = freeze_end = None
    worst_freeze = (0.0, None, None)
    previous = None
    for index, (media, engine, board, _) in enumerate(rows):
        if engine is None:
            continue
        if previous is not None and engine == previous[1]:
            if freeze_start is None:
                freeze_start = previous[0]
            freeze_end = media
            # only a freeze if the board moved inside it
            board_moved = any(
                abs(row[2] - previous[2]) > 1.0
                for row in rows
                if row[2] is not None and freeze_start <= row[0] <= media
                and previous[2] is not None
            )
            if board_moved and (media - freeze_start) > worst_freeze[0]:
                worst_freeze = (media - freeze_start, freeze_start, media)
        else:
            freeze_start = None
        previous = (media, engine, board)
    return {
        "samples": len(rows),
        "worst_engine_vs_board_s": (
            None
            if worst is None
            else {
                "media": round(worst[0], 1),
                "adt": adt(report["clip"], worst[0]),
                "engine": worst[1],
                "board": worst[2],
                "difference_s": round(worst[1] - worst[2], 1),
            }
        ),
        "longest_freeze_s": round(worst_freeze[0], 1),
        "freeze_span": (
            None
            if not worst_freeze[1]
            else [round(worst_freeze[1], 1), round(worst_freeze[2], 1)]
        ),
    }


def check_b(report):
    span = INCIDENTS["b"]
    events = [
        e
        for e in events_of(report["samples"])
        if (e.get("media") or 0) >= span["from"] - 5.0
    ]
    overtime = [
        e
        for e in events
        if "OT" in (e.get("period_label") or "").upper().replace("STOP", "")
    ]
    corrections = [
        e for e in events if e.get("kind") == "score" and (e.get("delta") or 0) < 0
    ]
    return {
        "events": [
            {
                "media": round(e["media"], 1) if e.get("media") is not None else None,
                "adt": adt(report["clip"], e["media"]) if e.get("media") else None,
                "kind": e.get("kind"),
                "period": e.get("period_label"),
                "text": e.get("text"),
            }
            for e in events
        ],
        "final": sum(1 for e in events if e.get("kind") == "final"),
        "new_game": sum(1 for e in events if e.get("kind") == "new_game"),
        "overtime_events": len(overtime),
        "score_corrections": len(corrections),
        "period_starts": sum(1 for e in events if e.get("kind") == "period_start"),
    }


def check_c(report):
    span = INCIDENTS["c"]
    rows = []
    for sample in report["samples"]:
        media = sample.get("media")
        if media is None or not (span["from"] <= media <= span["to"]):
            continue
        game = sample.get("game") or {}
        rows.append(
            (
                media,
                (sample.get("readings") or {}).get("Time", {}).get("text"),
                game.get("clock"),
                game.get("period"),
                game.get("period_label"),
            )
        )
    events = [
        e
        for e in events_of(report["samples"])
        if span["from"] <= (e.get("media") or 0) <= span["to"]
    ]
    # Setting the board up runs the clock down, reaches 0:00 and resets it to
    # 15:00. The reset -- a period start or a clock start from a stopped clock
    # at 15:00 -- is expected; what must not happen is a period END, which is
    # the live service's 10:27:51 "End of P1". A period start is only wrong if
    # it names a period other than the one being set up (the next game's P1).
    endings = [e for e in events if e.get("kind") == "period_end"]
    starts = [
        e for e in events if e.get("kind") in ("period_start", "clock_start")
    ]
    period_ends = {"count": len(endings),
                   "real": [e for e in endings if not _ran_down_before(e, rows)]}
    return {
        "clock_readings": [
            {"media": round(m, 1), "adt": adt(report["clip"], m), "board": b}
            for m, b, _, _, _ in rows
        ],
        "period_values": sorted({str(r[4]) for r in rows if r[4]}),
        "events": [
            {
                "media": round(e["media"], 1) if e.get("media") is not None else None,
                "adt": adt(report["clip"], e["media"]) if e.get("media") else None,
                "kind": e.get("kind"),
                "text": e.get("text"),
            }
            for e in events
        ],
        "period_end": period_ends["count"],
        "period_end_after_a_flick": len(period_ends["real"]),
        "period_start": sum(1 for e in events if e.get("kind") == "period_start"),
        "clock_start": sum(1 for e in events if e.get("kind") == "clock_start"),
    }


def check_d(report):
    events = events_of(report["samples"])
    scores = [
        e for e in events if e.get("kind") == "score" and (e.get("delta") or 0) > 0
    ]
    wanted = [
        (media, team, value, note)
        for media, team, value, note in GOALS.get(report["clip"], [])
        if report.get("start_media", 0.0) - 25.0
        <= media
        <= report.get("start_media", 0.0) + report.get("duration", 0.0) + 25.0
    ]
    used = set()
    matched = []
    for media, team, value, note in wanted:
        best = None
        for index, event in enumerate(scores):
            if index in used or event.get("team") != team:
                continue
            distance = abs((event.get("media") or 0.0) - media)
            if best is None or distance < best[1]:
                best = (index, distance)
        if best is not None and best[1] <= GOAL_WINDOW:
            used.add(best[0])
            event = scores[best[0]]
            matched.append(
                {
                    "want": f"{team} {value} at {media:.0f}s ({note})",
                    "detected_media": round(event["media"], 1),
                    "detected_adt": adt(report["clip"], event["media"]),
                    "delta_s": round(event["media"] - media, 1),
                    "detected_value": event.get("value"),
                    "ok": event.get("value") == value,
                }
            )
        else:
            matched.append({"want": f"{team} {value} at {media:.0f}s ({note})",
                            "detected_media": None, "ok": False})
    false_scores = [
        {
            "media": round(s["media"], 1),
            "adt": adt(report["clip"], s["media"]),
            "team": s.get("team"),
            "value": s.get("value"),
        }
        for index, s in enumerate(scores)
        if index not in used
    ]
    return {
        "wanted": len(wanted),
        "matched": sum(1 for m in matched if m["ok"]),
        "goals": matched,
        "false_scores": false_scores,
    }


def _ran_down_before(event, rows):
    """Whether the board's clock ran down to 0 rather than being flicked there.

    The frames show 0:05 -> 0:03 -> 0:01 -> 0:00 over 4 s, then 15:00; a flick
    goes 15:00 -> 0:00 -> 15:00 between two samples. If the two samples before
    the event show a clock within 6 s of zero and moving toward it, the period
    really did run out.
    """
    media = event.get("media")
    if media is None:
        return False
    before = [
        row for row in rows if row[0] <= media and parse_clock(row[1]) is not None
    ]
    if len(before) < 2:
        return False
    last = parse_clock(before[-1][1])
    prior = parse_clock(before[-2][1])
    if last is None or prior is None:
        return False
    # two samples a second apart, the clock inside the last seconds and falling
    return last <= 6.0 and prior >= last and (prior - last) <= 4.0


CHECKS = {"a": check_a, "b": check_b, "c": check_c, "d": check_d}


def report_checks(report):
    """Which incidents the run's window covers."""
    lo = report.get("start_media", 0.0)
    hi = lo + report.get("duration", 0.0)
    keys = []
    if lo <= INCIDENTS["a"]["from"] and hi >= INCIDENTS["a"]["to"]:
        keys.append("a")
    if lo <= INCIDENTS["b"]["from"] and hi >= INCIDENTS["b"]["to"]:
        keys.append("b")
    if lo <= INCIDENTS["c"]["from"] and hi >= INCIDENTS["c"]["to"]:
        keys.append("c")
    keys.append("d")
    return keys


def summarise(report):
    results = {key: CHECKS[key](report) for key in report_checks(report)}
    verdict = {}
    if "a" in results:
        worst = results["a"]["worst_engine_vs_board_s"]
        verdict["a"] = {
            "engine_vs_board": None if worst is None else worst["difference_s"],
            "longest_freeze_s": results["a"]["longest_freeze_s"],
        }
    if "b" in results:
        verdict["b"] = {
            "new_game": results["b"]["new_game"],
            "overtime_events": results["b"]["overtime_events"],
            "score_corrections": results["b"]["score_corrections"],
        }
    if "c" in results:
        verdict["c"] = {
            "period_end": results["c"]["period_end"],
            "period_start": results["c"]["period_start"],
        }
    if "d" in results:
        verdict["d"] = {
            "matched": results["d"]["matched"],
            "wanted": results["d"]["wanted"],
            "false_scores": len(results["d"]["false_scores"]),
        }
    return results, verdict


def render(report):
    results, verdict = summarise(report)
    lo = report.get("start_media", 0.0)
    hi = lo + report.get("duration", 0.0)
    lines = [
        f"# Replay incidents — {report.get('name')}",
        "",
        "| | |",
        "|---|---|",
        f"| build | `{report.get('build')}` |",
        f"| variant | {report.get('variant')} |",
        f"| clip | {report.get('clip')} |",
        f"| media | {lo:.0f}–{hi:.0f} s |",
        f"| samples | {len(report.get('samples') or [])} |",
        "",
        "```json",
        json.dumps(verdict, indent=1),
        "```",
        "",
    ]
    for key in sorted(results):
        title = INCIDENTS[key]["label"] if key in INCIDENTS else "every goal"
        lines += [f"## Incident {key} — {title}", "", "```json",
                  json.dumps(results[key], indent=1), "```", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--report", required=True)
    parser.add_argument("--md", action="store_true")
    parser.add_argument("--json", action="store_true", help="print the full detail")
    args = parser.parse_args(argv)
    with open(args.report) as handle:
        report = json.load(handle)
    results, verdict = summarise(report)
    print(json.dumps({"report": os.path.basename(args.report),
                      "build": os.path.basename(os.path.dirname(report.get("build", ""))),
                      "verdict": verdict,
                      **({"detail": results} if args.json else {})}, indent=1))
    if args.md:
        path = os.path.splitext(args.report)[0] + ".md"
        with open(path, "w") as handle:
            handle.write(render(report))
        print(f"[incidents] written {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
