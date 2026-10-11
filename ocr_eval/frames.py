"""The whole-frame experiment: one engine call reads every box of a frame.

ScoreSight reads each box on its own (one crop per box), and so does
`python -m ocr_eval run`. A vision-language model can instead look at the whole
frame once and answer for every box. This module groups a dataset's crops by the
frame (photo) they were cut from, gives the engine the frame and the boxes, and
scores each box's reading exactly like a crop's, so the numbers compare
directly with a crop run on the same crops (python -m ocr_eval.pairwise).

Frames. A crop's frame is its row's "frame" key, else "source_image"
(textocr_scoreboards: "openimages:<id>"). The frame's image is the row's
"frame_image" (a path in the dataset folder) when the dataset ships its frames,
else <frames dir>/<id>.jpg (or .jpeg, .png), where <id> is the frame key after
its "prefix:". textocr_scoreboards doesn't ship its photos (they are about ten
times the size of the crops); its builder's cache has them in <cache>/images/.
A field's box is the crop's source_box (the padded box a user would draw), in
frame pixels; crops without one are skipped. A row's "role" key (e.g. "home
score") is passed on when the dataset has semantic field names.

Engines. An engine reads frames if it has `frame_modes` and
`read_frame(frame, fields, mode) -> (recognitions, info)`: frame is a read-only
uint8 BGR array, fields a list of FrameField, recognitions one per field in
order, info a small JSON-serializable dict about the call (kept per frame). In
ocr_eval.engines.vlm, qwen-vl has the modes "boxes" (the prompt lists the
boxes' coordinates) and "marks" (numbered boxes are drawn on the frame), and
florence2 "spot" (<OCR_WITH_REGION>; each box gets the text regions centred in
it).

    python -m ocr_eval.frames --dataset textocr_scoreboards --frames-dir CACHE/images \\
        --engine qwen-vl:qwen3.5-0.8b --mode boxes --out results/frames [--frames N]

writes DIR/results.json (the results schema of ocr_eval.runner; the run key is
"<engine>:<variant>@frames-<mode>", latency.batch is the frame's time divided
by its fields, latency.frame the time per frame, and run.frames lists each
frame's call) and DIR/report.md.
"""

import argparse
import hashlib
import sys
import time
import traceback
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from ocr_eval import REPO_ROOT, utf8_output
from ocr_eval.dataset import Dataset, DatasetError, Sample, load_dataset, read_image
from ocr_eval.fields import SPLITS, scoresight_postfilter
from ocr_eval.metrics import latency_summary, score_item, summarize

FRAME_EXTENSIONS = (".jpg", ".jpeg", ".png")


class FrameField(NamedTuple):
    """A box to read in a frame: x, y, w, h in frame pixels."""

    id: str
    box: tuple[int, int, int, int]
    field_type: str
    # a semantic name (e.g. "home score") when the dataset has one
    role: str | None = None


@dataclass
class Frame:
    key: str
    image_path: Path
    samples: list[Sample]

    def fields(self) -> list[FrameField]:
        return [
            FrameField(s.id, tuple(s.source_box), s.field_type, s.extra.get("role"))
            for s in self.samples
        ]


def frame_key(sample: Sample) -> str | None:
    key = sample.extra.get("frame") or sample.extra.get("source_image")
    return key if isinstance(key, str) and key else None


def _frame_path(dataset: Dataset, key: str, sample: Sample, frames_dirs) -> Path | None:
    relative = sample.extra.get("frame_image")
    if isinstance(relative, str) and relative:
        path = (dataset.path / relative).resolve()
        if path.is_file() and dataset.path.resolve() in path.parents:
            return path
        return None
    stem = key.split(":", 1)[-1]
    for directory in frames_dirs:
        for extension in FRAME_EXTENSIONS:
            path = Path(directory) / f"{stem}{extension}"
            if path.is_file():
                return path
    return None


def find_frames(dataset: Dataset, frames_dirs=()) -> tuple[list[Frame], Counter]:
    """The dataset's crops grouped by frame (frames sorted by key), and the
    number of crops skipped by reason."""
    skipped: Counter = Counter()
    groups: dict[str, list[Sample]] = {}
    for sample in dataset.samples:
        key = frame_key(sample)
        if key is None:
            skipped["no frame key"] += 1
        elif sample.source_box is None:
            skipped["no source_box"] += 1
        else:
            groups.setdefault(key, []).append(sample)
    frames = []
    for key in sorted(groups):
        samples = groups[key]
        path = _frame_path(dataset, key, samples[0], frames_dirs)
        if path is None:
            skipped["frame image not found"] += len(samples)
        else:
            frames.append(Frame(key, path, samples))
    return frames, skipped


def select_frames(frames: list[Frame], n: int | None, seed: int = 0) -> list[Frame]:
    """n frames chosen by a seeded hash of their key (reproducible, the same on
    every machine), in their original order; all of them if n is None."""
    if n is None or n >= len(frames):
        return list(frames)
    ranked = sorted(
        frames,
        key=lambda f: hashlib.sha256(f"{seed}:{f.key}".encode("utf-8")).digest(),
    )
    chosen = {f.key for f in ranked[: max(0, n)]}
    return [f for f in frames if f.key in chosen]


def run_frames(
    engine_class,
    variant: str,
    mode: str,
    dataset: Dataset,
    frames: list[Frame],
    warmup: int = 1,
    log=print,
) -> dict:
    """Run one engine variant in one frame mode; returns the run record. Like
    runner.run_engine, never raises for engine problems."""
    record = {
        "dataset": dataset.name,
        "engine": engine_class.name,
        "variant": variant,
        "key": f"{engine_class.name}:{variant}@frames-{mode}",
        "status": "ok",
        "mode": mode,
    }
    if mode not in getattr(engine_class, "frame_modes", ()):
        record.update(
            status="skipped",
            reason=f"{engine_class.name} doesn't read whole frames in mode {mode!r}",
        )
        return record
    reason = engine_class.unavailable_reason()
    if reason:
        record.update(status="skipped", reason=reason)
        return record
    from ocr_eval.engines import EngineUnavailable
    from ocr_eval.runner import _as_recognition

    engine = None
    try:
        engine = engine_class(variant)
        started = time.perf_counter()
        engine.load()
        record["load_seconds"] = round(time.perf_counter() - started, 3)
        record["engine_info"] = engine.info()

        def read(frame: Frame):
            image = read_image(frame.image_path)
            image.flags.writeable = False
            fields = frame.fields()
            started = time.perf_counter()
            output, info = engine.read_frame(image, fields, mode)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            if output is None or len(output) != len(fields):
                raise RuntimeError(
                    f"{record['key']} returned {0 if output is None else len(output)} "
                    f"readings for the {len(fields)} fields of {frame.key}"
                )
            return [_as_recognition(value) for value in output], info, elapsed_ms

        for frame in frames[: max(0, warmup)]:
            read(frame)

        predictions, frame_records, field_ms, frame_ms = [], [], [], []
        scored = {"raw": [], "postfilter": []}
        started_all = time.perf_counter()
        for number, frame in enumerate(frames, start=1):
            recognitions, info, elapsed_ms = read(frame)
            frame_ms.append(elapsed_ms)
            per_field = elapsed_ms / len(frame.samples)
            frame_records.append(
                {
                    "key": frame.key,
                    "fields": len(frame.samples),
                    "ms": round(elapsed_ms, 1),
                    "info": info or {},
                }
            )
            for sample, recognition in zip(frame.samples, recognitions):
                field_ms.append(per_field)
                raw = score_item(recognition.text, sample.text, sample.field_type)
                filtered_text = scoresight_postfilter(
                    recognition.text, sample.field_type, sample.extra.get("role")
                )
                filtered = score_item(filtered_text, sample.text, sample.field_type)
                scored["raw"].append((sample, raw))
                scored["postfilter"].append((sample, filtered))
                prediction = {
                    "id": sample.id,
                    "truth": sample.text,
                    "text": recognition.text,
                    "conf": recognition.confidence,
                    "ms": round(per_field, 3),
                    "exact": raw.exact,
                    "pf_exact": filtered.exact,
                    "frame": frame.key,
                }
                if filtered_text != recognition.text:
                    prediction["pf_text"] = filtered_text
                if recognition.info:
                    prediction["info"] = recognition.info
                predictions.append(prediction)
            if log and number % 10 == 0:
                log(f"  {record['key']}: {number}/{len(frames)} frames")
        record["latency"] = {
            "single": None,
            "batch": latency_summary(field_ms),
            "frame": latency_summary(frame_ms),
            "batch_size": None,
            "total_seconds": round(time.perf_counter() - started_all, 3),
        }
        record["scores"] = {
            scoring: summarize(items) for scoring, items in scored.items()
        }
        record["frames"] = frame_records
        record["predictions"] = predictions
    except EngineUnavailable as e:
        record.update(status="skipped", reason=str(e))
    except Exception as e:
        record.update(
            status="error",
            reason=f"{type(e).__name__}: {e}",
            traceback=traceback.format_exc(),
        )
    finally:
        if engine is not None:
            try:
                engine.close()
            except Exception:
                pass
    return record


def frame_summary(run: dict) -> dict:
    """Frames, fields, parse errors and frame latency of a frame run."""
    frames = run.get("frames") or []
    return {
        "frames": len(frames),
        "fields": sum(f["fields"] for f in frames),
        "parse_errors": sum(1 for f in frames if f.get("info", {}).get("parse_error")),
        "frame_latency": (run.get("latency") or {}).get("frame"),
    }


def render_frames_section(results: dict) -> str:
    lines = ["", "## Whole frames", ""]
    lines.append(
        "One engine call per frame reads all of its boxes. ms per field = the "
        "frame's time divided by its fields; parse errors = answers that weren't "
        "valid JSON (their fields were still picked out where possible)."
    )
    lines += [
        "",
        "| Dataset | Engine:variant@mode | Frames | Fields | Exact % | "
        "ms per frame p50 / p95 | ms per field p50 | Parse errors |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    from ocr_eval.report import pct_ci

    for run in results.get("runs", []):
        if run.get("status") != "ok":
            lines.append(
                f"| {run['dataset']} | {run['key']} | – | – | {run['status']}: "
                f"{run.get('reason', '')} | | | |"
            )
            continue
        summary = frame_summary(run)
        frame_latency = summary["frame_latency"] or {}
        field_latency = run["latency"].get("batch") or {}
        lines.append(
            f"| {run['dataset']} | {run['key']} | {summary['frames']} "
            f"| {summary['fields']} | {pct_ci(run['scores']['raw']['exact'])} "
            f"| {frame_latency.get('p50_ms', 0):.0f} / {frame_latency.get('p95_ms', 0):.0f} "
            f"| {field_latency.get('p50_ms', 0):.0f} | {summary['parse_errors']} |"
        )
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(
        prog="python -m ocr_eval.frames",
        description="Read every box of a frame in one engine call, and score "
        "each box like a crop.",
    )
    parser.add_argument("--dataset", action="append", required=True)
    parser.add_argument(
        "--frames-dir",
        action="append",
        default=[],
        help="folder with the frames as <id>.jpg/.png (repeatable)",
    )
    parser.add_argument("--engine", action="append", required=True)
    parser.add_argument(
        "--mode",
        required=True,
        help="comma-separated frame modes (qwen-vl: boxes, marks; florence2: spot)",
    )
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--frames",
        type=int,
        metavar="N",
        help="N frames, chosen by a seeded hash of their key (default: all)",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--split", help=f"comma-separated splits ({', '.join(SPLITS)})")
    parser.add_argument("--label")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    from ocr_eval.engines import discover, parse_engine_spec
    from ocr_eval.report import render_report, write_results
    from ocr_eval.runner import run_all

    registry = discover()
    try:
        engines = [e for spec in args.engine for e in parse_engine_spec(spec, registry)]
    except (KeyError, ValueError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2
    modes = [m.strip() for m in args.mode.split(",") if m.strip()]
    splits = [s.strip() for s in args.split.split(",")] if args.split else None
    log = None if args.quiet else (lambda message: print(message, flush=True))

    # the results' header (environment, datasets) as a crop run writes it
    results = run_all([], [], label=args.label, log=None)
    for ref in args.dataset:
        try:
            dataset = load_dataset(ref, splits)
        except DatasetError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        frames, skipped = find_frames(dataset, args.frames_dir)
        chosen = select_frames(frames, args.frames, args.seed)
        n_fields = sum(len(f.samples) for f in chosen)
        if log:
            log(
                f"{dataset.name}: {len(chosen)} of {len(frames)} frames, "
                f"{n_fields} fields"
                + "".join(f"; skipped {n}: {reason}" for reason, n in skipped.items())
            )
        if not chosen:
            print(f"error: {dataset.name}: no frames found", file=sys.stderr)
            return 2
        subset = {
            "frames": len(chosen),
            "of_frames": len(frames),
            "seed": args.seed,
            "skipped": dict(skipped),
            "n": n_fields,
            "manifest_n": (dataset.subset or {}).get("manifest_n", len(dataset)),
        }
        if splits:
            subset["splits"] = splits
        try:
            path = dataset.path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            path = str(dataset.path)
        results["datasets"][dataset.name] = {
            "path": path,
            "n": n_fields,
            "manifest_sha256": dataset.manifest_sha256,
            "description": dataset.description,
            "subset": subset,
        }
        for engine_class, variant in engines:
            for mode in modes:
                if log:
                    log(f"{dataset.name}: {engine_class.name}:{variant}@frames-{mode}")
                record = run_frames(
                    engine_class, variant, mode, dataset, chosen, args.warmup, log
                )
                if log and record["status"] != "ok":
                    log(f"  {record['status']}: {record.get('reason')}")
                elif log:
                    exact = record["scores"]["raw"]["exact"]["value"]
                    log(f"  exact {exact:.3f}")
                results["runs"].append(record)

    out = Path(args.out)
    write_results(out / "results.json", results)
    report = render_report(results) + render_frames_section(results)
    (out / "report.md").write_text(report, encoding="utf-8", newline="\n")
    print(f"Wrote {out / 'results.json'} and {out / 'report.md'}")
    errors = [r for r in results["runs"] if r["status"] == "error"]
    for run in errors:
        print(f"error: {run['dataset']} {run['key']}: {run['reason']}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
