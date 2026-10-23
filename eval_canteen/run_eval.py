#!/usr/bin/env python3
"""Offline accuracy harness for ScoreSight on Curly's stadium scoreboard footage.

Runs ScoreSight headless on a slice of a recording, at real-time pace over a
local UDP port, collects /json and /game once a second, and scores every field
against the reference (the homegrown reader's journal plus hand-verified
frames) on media time.

    nice -n 15 python eval_canteen/run_eval.py \\
        --clip ~/.local/share/canteen-ops/scoreboard-camera/crop/20261023T091022.mkv \\
        --variant filtered --engine ppocr --start 0 --duration 900

Writes <out>/<name>.json and <out>/<name>.md, plus the raw samples, the
ScoreSight log and the feed command for audit. It never touches the live
services: its own free UDP port for the feed, its own free HTTP port, its own
data and log directories, and it stops only the processes it started.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import runner  # noqa: E402
import scoring  # noqa: E402
import truth as truth_mod  # noqa: E402

DEFAULT_CLIP = os.path.expanduser(
    "~/.local/share/canteen-ops/scoreboard-camera/crop/20261023T091022.mkv"
)
REPORTS = os.path.join(HERE, "reports")


def media_id_of(clip):
    return os.path.basename(clip)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--clip", default=DEFAULT_CLIP, help="recording to evaluate")
    parser.add_argument(
        "--variant",
        choices=("raw", "filtered"),
        default="filtered",
        help="frame preprocessing (filtered = the live feed's lut)",
    )
    parser.add_argument("--engine", choices=tuple(runner.ENGINES), default="ppocr")
    parser.add_argument(
        "--cadence",
        type=float,
        default=2.0,
        help="detections per second (the live profile uses 2.0)",
    )
    parser.add_argument(
        "--start", type=float, default=0.0, help="media seconds to start at"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=900.0,
        help="media seconds to play (real time)",
    )
    parser.add_argument(
        "--settle",
        type=float,
        default=3.0,
        help="seconds to let the first frames decode before sampling",
    )
    parser.add_argument("--out", default=REPORTS)
    parser.add_argument("--name", default=None, help="report basename")
    parser.add_argument(
        "--keep-work", action="store_true", help="keep the run's data/log directory"
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    clip = os.path.abspath(os.path.expanduser(args.clip))
    if not os.path.exists(clip):
        raise SystemExit(f"clip not found: {clip}")
    if not os.path.exists(runner.VENV_PYTHON):
        raise SystemExit(f"ScoreSight venv missing: {runner.VENV_PYTHON}")

    media_id = media_id_of(clip)
    truth = truth_mod.load_truth(media_id)
    if not truth.observations:
        raise SystemExit(f"no reference observations for {media_id}")

    name = args.name or f"{os.path.splitext(media_id)[0]}_{args.variant}_{args.engine}"
    workdir = runner.make_run_dir(os.path.join(args.out, "work"), name)
    os.makedirs(args.out, exist_ok=True)

    feed_port = runner.free_port()
    feed_url = f"udp://127.0.0.1:{feed_port}"
    feed = runner.Feed(clip, feed_port, args.variant, args.start, args.duration)
    run = runner.ScoreSight(
        name, args.variant, args.engine, args.cadence, workdir, feed_url
    )

    # the reference dump + the feed command, for audit
    truth_mod.save_truth_dump(media_id, os.path.join(workdir, "reference.json"))
    with open(os.path.join(workdir, "feed_command.txt"), "w") as handle:
        handle.write(f"# variant={args.variant}\n")
        handle.write(f"# vf={feed.vf}\n")
        handle.write(
            f"ffmpeg -nostdin -loglevel error -ss {args.start} -t {args.duration} "
            f'-re -i {clip} -an -vf "{feed.vf}" -c:v libx264 -preset ultrafast '
            f"-tune zerolatency -g 5 -threads 1 -f mpegts {feed_url}\n"
        )

    started = time.time()
    samples = []
    try:
        feed.start_feed()
        time.sleep(1.0)
        run.start()
        if args.settle:
            time.sleep(args.settle)
        print(
            f"[eval] {name}: {args.duration:.0f}s of media from {args.start:.0f}s "
            f"(feed udp {feed_port}, http {run.port})",
            flush=True,
        )
        samples, _ = runner.collect(run, args.duration + 3.0)
    finally:
        run.stop()
        feed.stop()

    duration = args.duration
    result = scoring.score(samples, truth, _events(samples), args.start, duration)
    meta = {
        "clip": media_id,
        "clip_path": clip,
        "variant": args.variant,
        "engine": args.engine,
        "cadence": args.cadence,
        "start_media": args.start,
        "duration": duration,
        "samples": result.get("samples", len(samples)),
        "offset_seconds": result.get("offset_seconds"),
        "aligned_clock_samples": result.get("aligned_clock_samples"),
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(started)),
        "elapsed_seconds": round(time.time() - started, 1),
        "scoresight_log": os.path.join(workdir, "scoresight.out"),
        "samples_file": os.path.join(workdir, "samples.json"),
        "feed_port": feed_port,
        "http_port": run.port,
    }
    with open(os.path.join(workdir, "samples.json"), "w") as handle:
        json.dump(samples, handle, indent=1)

    report = {"meta": meta, "result": result}
    json_path = os.path.join(args.out, f"{name}.json")
    md_path = os.path.join(args.out, f"{name}.md")
    with open(json_path, "w") as handle:
        json.dump(report, handle, indent=1)
    with open(md_path, "w") as handle:
        handle.write(scoring.render_markdown(meta, result, truth))

    if not args.keep_work:
        import shutil

        shutil.rmtree(workdir, ignore_errors=True)
        meta["scoresight_log"] = None
        meta["samples_file"] = None

    print(f"[eval] written {json_path}")
    print(f"[eval] written {md_path}")
    for key, _ in scoring.FIELDS:
        row = result["fields"][key]
        acc = "n/a" if row["accuracy"] is None else f"{100 * row['accuracy']:.1f}%"
        print(
            f"[eval] {row['name']:<11} correct {row['correct']:>4} wrong {row['wrong']:>3} "
            f"unknown {row['unknown']:>4} accuracy {acc}",
            flush=True,
        )
    return 0


def _events(samples):
    """Every game event seen in the samples, once, oldest first."""
    seen = {}
    for sample in samples:
        for event in sample.get("events") or []:
            id_ = event.get("id")
            if id_ is not None and id_ not in seen:
                seen[id_] = event
    return [seen[key] for key in sorted(seen)]


if __name__ == "__main__":
    raise SystemExit(main())
