#!/usr/bin/env python3
"""Pull frames from a clip at given media times, to check a report's readings.

    nice -n 15 python eval_canteen/frame_check.py \
        --clip .../20261023T091022.mkv --at 496 1042 1255 --out /tmp/eval_frames

Writes one PNG per time, plus a montage of all of them (``montage.png``) when
there is more than one. The frame is taken at the clip's own resolution; view
it to see what the board showed at that instant.

``--boxes`` crops to the profile's four reading boxes (the recorder crop's
coordinates) and scales them up, so the digits can be read without squinting;
the montage then has one row per time (Time, Home, Away, Period).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

# make_profile.py's boxes, in the recorder crop's coordinates (420x240)
BOXES = (
    ("Time", 179, 68, 82, 36),
    ("Home", 73, 87, 44, 33),
    ("Away", 322, 93, 42, 33),
    ("Period", 211, 124, 20, 26),
)
BOX_SCALE = 4


def grab(clip, media, out, scale=None, boxes=False):
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"t{media:08.2f}.png")
    if boxes:
        pieces = []
        for _, x, y, w, h in BOXES:
            pieces.append(
                f"crop={w}:{h}:{x}:{y},scale={w * BOX_SCALE}:{h * BOX_SCALE}"
                ":flags=neighbor"
            )
        # side by side, with a black gap so the boxes stay apart
        chain = [f"[0:v]{pieces[0]}[b0]"]
        for index, piece in enumerate(pieces[1:], start=1):
            chain.append(f"[0:v]{piece}[b{index}]")
        chain.append(
            "[b0][b1][b2][b3]hstack=inputs=4:fill=black[out]"
        )
        vf = ";".join(chain)
        cmd = [
            "nice", "-n", "15", "ffmpeg", "-nostdin", "-loglevel", "error",
            "-ss", f"{media:.3f}", "-i", clip, "-frames:v", "1",
            "-filter_complex", vf, "-map", "[out]", "-y", path,
        ]
        subprocess.run(cmd, check=True)
        return path
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
    parser.add_argument(
        "--boxes",
        action="store_true",
        help="crop to the four reading boxes and scale them up",
    )
    args = parser.parse_args(argv)
    paths = [
        grab(args.clip, media, args.out, args.scale, args.boxes)
        for media in args.at
    ]
    for path in paths:
        print(path)
    montage_path = montage(paths, args.out)
    if montage_path:
        print(montage_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
