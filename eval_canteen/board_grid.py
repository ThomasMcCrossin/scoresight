#!/usr/bin/env python3
"""A grid of frames with their media time burned in, for incident verification.

Ambiguity in a montage is what makes a misread arguable, so every tile carries
its own media time and ADT time. The tile is the board's four reading boxes
with the clock and scores large enough to read.

    nice -n 15 .venv/bin/python eval_canteen/board_grid.py \\
        --clip .../20261023T101023.mkv --from 330 --to 340 --step 2 \\
        --out /tmp/grid/a.png
"""

from __future__ import annotations

import argparse
import re
import os
import subprocess
import sys
from datetime import datetime, timedelta

CLIPS = {
    "20261023T091022.mkv": "2026-10-23T09:10:22-03:00",
    "20261023T101023.mkv": "2026-10-23T10:10:23-03:00",
}

# the reading boxes, x:y:w:h in the recorder crop, joined into one strip
STRIP = "crop=420:150:0:50,scale=630:225:flags=neighbor"


def adt(clip, media):
    start = datetime.fromisoformat(CLIPS[os.path.basename(clip)])
    return (start + timedelta(seconds=media)).strftime("%H:%M:%S")


_PTS = re.compile(r"\bn:\s*\d+\s+pts:\s*(-?\d+)")


def _pts_from_showinfo(text):
    """The PTS (seconds) of the first frame showinfo reported, or None."""
    match = _PTS.search(text)
    if not match:
        return None
    return int(match.group(1)) / 1000.0  # ffmpeg reports PTS in milliseconds


def grid(clip, times, out, cols):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    frames = []
    tmp = os.path.join(os.path.dirname(os.path.abspath(out)), "_tiles")
    os.makedirs(tmp, exist_ok=True)
    for media in times:
        path = os.path.join(tmp, f"t{media:08.2f}.png")
        # The label carries the frame's own PTS, not the requested seek time:
        # ffmpeg -ss lands on the nearest frame, and a seek into a long run of
        # frames can land seconds off, which would make the tile's time a
        # guess. showinfo prints the PTS it actually decoded; the tile is then
        # stamped with that, so a viewer can check the claim on the frame.
        decode = subprocess.run(
            [
                "nice", "-n", "15", "ffmpeg", "-nostdin", "-copyts", "-ss", f"{media:.3f}",
                "-i", clip, "-frames:v", "1", "-vf", f"showinfo,{STRIP}",
                "-y", path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        pts = _pts_from_showinfo(decode.stderr)
        label = (
            f"seek {media:.1f}s  frame pts {pts:.1f}s  {adt(clip, pts)}"
            if pts is not None
            else f"seek {media:.1f}s  pts unknown"
        )
        stamped = path.replace(".png", "_label.png")
        subprocess.run(
            [
                "nice", "-n", "15", "ffmpeg", "-nostdin", "-loglevel", "error",
                "-i", path, "-vf",
                "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"text='{label}':x=6:y=6:fontsize=24:fontcolor=yellow:"
                "box=1:boxcolor=black@0.75",
                "-y", stamped,
            ],
            check=True,
        )
        frames.append(stamped)
    rows = (len(frames) + cols - 1) // cols
    layout = "|".join(
        f"{(i % cols) * 630}_{(i // cols) * 225}" for i in range(len(frames))
    )
    stream = "".join(f"[{i}:v]" for i in range(len(frames)))
    inputs = []
    for path in frames:
        inputs += ["-i", path]
    subprocess.run(
        ["nice", "-n", "15", "ffmpeg", "-nostdin", "-loglevel", "error", "-y"]
        + inputs
        + [
            "-filter_complex",
            ";".join(f"[{i}:v]format=rgb24[v{i}]" for i in range(len(frames)))
            + ";"
            + "".join(f"[v{i}]" for i in range(len(frames)))
            + f"xstack=inputs={len(frames)}:layout={layout}:fill=black[out]",
            "-map", "[out]", out,
        ],
        check=True,
    )
    print(f"{out}  ({len(frames)} tiles, {rows} rows)")
    return out


def times_from(start, stop, step):
    times = []
    value = start
    while value <= stop + 1e-9:
        times.append(value)
        value += step
    return times


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--clip", required=True)
    parser.add_argument("--from", dest="start", type=float, default=0.0)
    parser.add_argument("--to", dest="stop", type=float, default=-1.0)
    parser.add_argument("--step", type=float, default=1.0)
    parser.add_argument("--at", nargs="+", type=float, default=None)
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    times = args.at or times_from(args.start, args.stop, args.step)
    grid(args.clip, times, args.out, args.cols)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
