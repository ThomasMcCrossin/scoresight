#!/usr/bin/env python3
"""Pull frames from a clip at given media times, to check a report's readings.

    nice -n 15 python eval_canteen/frame_check.py \
        --clip .../20261023T091022.mkv --at 496 1042 1255 --out /tmp/eval_frames

Writes one PNG per time, plus a montage of all of them (``montage.png``) when
there is more than one. The frame is taken at the clip's own resolution; view
it to see what the board showed at that instant.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys


def grab(clip, media, out, scale=None):
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"t{media:08.2f}.png")
    vf = f"scale={scale}:flags=neighbor" if scale else None
    cmd = [
        "nice",
        "-n",
        "15",
        "ffmpeg",
        "-nostdin",
        "-loglevel",
        "error",
        "-ss",
        f"{media:.3f}",
        "-i",
        clip,
        "-frames:v",
        "1",
    ]
    if vf:
        cmd += ["-vf", vf]
    cmd += ["-y", path]
    subprocess.run(cmd, check=True)
    return path


def montage(paths, out, cols=4):
    if len(paths) < 2:
        return None
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            paths[0],
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    width, height = (int(x) for x in probe.stdout.strip().split(","))
    inputs = []
    for path in paths:
        inputs += ["-i", path]
    layout = "|".join(
        f"{(i % cols) * width}_{(i // cols) * height}" for i in range(len(paths))
    )
    stream = "".join(f"[v{i}]" for i in range(len(paths)))
    filter_complex = (
        ";".join(f"[{i}:v]format=rgb24[v{i}]" for i in range(len(paths)))
        + ";"
        + stream
        + f"xstack=inputs={len(paths)}:layout={layout}:fill=black[out]"
    )
    path = os.path.join(out, "montage.png")
    subprocess.run(
        ["nice", "-n", "15", "ffmpeg", "-nostdin", "-loglevel", "error", "-y"]
        + inputs
        + ["-filter_complex", filter_complex, "-map", "[out]", path],
        check=True,
    )
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--clip", required=True)
    parser.add_argument(
        "--at", nargs="+", type=float, required=True, help="media seconds"
    )
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--scale", default=None, help="scale WIDTH:HEIGHT (e.g. 630:360)"
    )
    args = parser.parse_args(argv)
    paths = [grab(args.clip, media, args.out, args.scale) for media in args.at]
    for path in paths:
        print(path)
    montage_path = montage(paths, args.out)
    if montage_path:
        print(montage_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
