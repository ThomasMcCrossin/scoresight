#!/usr/bin/env python3
"""Replay the 10:10 hour and check the incidents the live service got wrong.

There is no reader journal for the 10:10 segment, so this is not a scored
compare: it replays a slice at real-time pace, keeps every /json and /game
sample with the media time it belongs to, and answers the specific questions
the live logs raised:

* the clock must follow a board that runs on (the fork's held-reading fix);
* a board set up for the next game after the final is a new game, with no
  overtime and no score correction;
* a clock flicked 15:00 -> 0:00 -> 15:00 before play is not the end of a period;
* every goal of the hour is detected once, and nothing else is.

Media time comes from ffmpeg's ``-progress`` stream (``out_time`` on the wall
clock), aligned to the clip's segment start, so the same mapping as the live
timeline is used without a journal.

    nice -n 15 .venv/bin/python eval_canteen/replay_1010.py \\
        --build /home/canteenhub/worktrees/scoresight/qualify \\
        --variant filtered --start 330 --duration 200 --name b_fork
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import runner  # noqa: E402

CLIP = os.path.expanduser(
    "~/.local/share/canteen-ops/scoreboard-camera/crop/20261023T101023.mkv"
)
REPORTS = os.path.join(HERE, "reports")
SEGMENT_OFFSET = 0.0  # the clip's first frame is 10:10:23 ADT, media 0.0


def parse_progress(path):
    """[(wall, media seconds)] from ffmpeg's -progress file, as it was read.

    Called while the feed runs (a watcher in ``Watch``), so each row's wall
    time is when the line first appeared, not when the file was parsed.
    """
    rows = []
    media = None
    try:
        with open(path, errors="replace") as handle:
            for line in handle:
                key, _, value = line.strip().partition("=")
                if key == "out_time":
                    try:
                        h, m, s = value.split(":")
                        media = int(h) * 3600 + int(m) * 60 + float(s)
                    except ValueError:
                        continue
                elif key == "progress" and media is not None:
                    rows.append((time.time(), media))
    except FileNotFoundError:
        pass
    return rows


class Watch:
    """Tails ffmpeg's -progress file while the feed runs, recording
    (wall, out_time) pairs as they appear."""

    def __init__(self, path, interval=0.25):
        self.path = path
        self.interval = interval
        self.rows = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def _loop(self):
        seen = 0
        while not self._stop.is_set():
            rows = parse_progress(self.path)
            for row in rows[seen:]:
                self.rows.append(row)
            seen = len(rows)
            time.sleep(self.interval)

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2.0)
        # pick up anything written after the last poll
        rows = parse_progress(self.path)
        for row in rows[len(self.rows):]:
            self.rows.append(row)
        return self.rows


def media_of(wall, progress, feed_start):
    """The media time of a wall-clock instant, by ffmpeg's own progress.

    The feed seeks with -ss before -i and does not copy timestamps, so ffmpeg's
    out_time restarts at 0 at the seek: media = feed_start + out_time. It is
    the feed's start (window start - lead-in), not the window start: using the
    window start shifted every recorded media time by the lead-in.
    """
    if not progress:
        return None
    before = None
    for at_wall, media in progress:
        if at_wall <= wall:
            before = (at_wall, media)
        else:
            # between two progress reports: the earlier one's media time
            return feed_start + (before[1] if before else media)
    return feed_start + (before[1] if before else progress[-1][1])


def wait_reading(app, timeout=300.0, poll=2.0):
    """Wait until /json has a reading from the live feed, not a stale one.

    The feed is a URL source: the app opens the stream once, and a seek that
    lands before the stream is readable makes OpenCV time out and give up (its
    own log says "Stream timeout triggered"), after which it never reopens. So
    the run starts the feed, waits here for real readings, and only then begins
    the window -- the lead-in frames are discarded from the record.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            rows = app.readings()
        except Exception:
            time.sleep(poll)
            continue
        if any(row[0].strip() for row in rows.values()):
            return True
        time.sleep(poll)
    return False


def run(build, variant, start, duration, name, out, keep_work=True, lead_in=20.0,
        clip=None):
    runner.configure(build)
    if not os.path.exists(runner.VENV_PYTHON):
        raise SystemExit(f"build venv missing: {runner.VENV_PYTHON}")
    workdir = runner.make_run_dir(os.path.join(out, "work"), name)
    progress_path = os.path.join(workdir, "progress.txt")
    feed_port = runner.free_port()
    feed_url = f"udp://127.0.0.1:{feed_port}"
    # the feed starts a little before the window so the app has frames to open
    # and lock onto; the window's own samples are the record
    feed_start = max(0.0, start - lead_in)
    clip = clip or CLIP
    feed = runner.Feed(
        clip, feed_port, variant, feed_start, duration + lead_in, progress=progress_path
    )
    app = runner.ScoreSight(name, variant, "ppocr", 2.0, workdir, feed_url)
    samples = []
    started = time.time()
    watch = Watch(progress_path)
    live = False
    try:
        watch.start()
        feed.start_feed()
        time.sleep(1.0)
        app.start()
        live = wait_reading(app, timeout=240.0)
        print(f"[replay] {name}: live readings {'seen' if live else 'NOT seen'}", flush=True)
        if live:
            # sample until the feed has played past the window's end
            deadline = time.monotonic() + duration + lead_in + 15.0
            while time.monotonic() < deadline:
                t0 = time.monotonic()
                try:
                    rows, game, wall = app.sample(0)
                except Exception as exc:
                    samples.append({"error": str(exc), "wall": time.time()})
                    time.sleep(1.0)
                    continue
                samples.append(
                    {
                        "wall": wall,
                        "readings": {
                            str(r.get("name")): {
                                "text": str(r.get("text", "")),
                                "state": str(r.get("state", "")),
                            }
                            for r in rows
                        },
                        "game": {
                            key: game.get(key)
                            for key in (
                                "home", "away", "period", "period_label", "clock",
                                "clock_running", "final", "line_score",
                            )
                        },
                        "events": list(game.get("events") or []),
                    }
                )
                time.sleep(max(0.0, 1.0 - (time.monotonic() - t0)))
    finally:
        app.stop()
        feed.stop()
        progress = watch.stop()
    for sample in samples:
        if "wall" in sample:
            sample["media"] = media_of(sample["wall"], progress, feed_start)
    # the record is the window; the lead-in only opened the stream
    samples = [
        sample
        for sample in samples
        if sample.get("media") is None or sample["media"] >= start - 2.0
    ]
    # Once the feed ends, every later poll maps to the same final out_time;
    # those repeats are not a second of media and would read as a frozen
    # engine, so only the first sample at each media time is kept.
    deduped = []
    seen_media = set()
    for sample in samples:
        media = sample.get("media")
        if media is not None and media in seen_media:
            continue
        seen_media.add(media)
        deduped.append(sample)
    samples = deduped
    report = {
        "build": runner.SCORESIGHT_ROOT,
        "variant": variant,
        "clip": os.path.basename(clip),
        "start_media": start,
        "duration": duration,
        "name": name,
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(started)),
        "feed_port": feed_port,
        "http_port": app.port,
        "progress": progress,
        "samples": samples,
    }
    path = os.path.join(out, f"{name}.json")
    with open(path, "w") as handle:
        json.dump(report, handle, indent=1)
    if not keep_work:
        import shutil

        shutil.rmtree(workdir, ignore_errors=True)
    print(f"[replay] {path} ({len(samples)} samples)")
    return path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--build", required=True, help="ScoreSight checkout to run")
    parser.add_argument(
        "--variant", choices=tuple(runner.VARIANTS), default="filtered"
    )
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--duration", type=float, default=900.0)
    parser.add_argument("--name", required=True)
    parser.add_argument("--clip", default=CLIP, help="recording to replay")
    parser.add_argument("--out", default=REPORTS)
    parser.add_argument("--no-keep-work", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    run(
        args.build,
        args.variant,
        args.start,
        args.duration,
        args.name,
        args.out,
        not args.no_keep_work,
        clip=os.path.abspath(os.path.expanduser(args.clip)),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
