"""Running engines on datasets and collecting predictions, scores and latency."""

import datetime
import importlib.metadata
import os
import platform
import sys
import time
import traceback
from dataclasses import dataclass

import numpy as np

from ocr_eval import HARNESS_VERSION, REPO_ROOT, RESULTS_SCHEMA
from ocr_eval.dataset import Dataset
from ocr_eval.engines import Engine, EngineUnavailable, Recognition
from ocr_eval.fields import scoresight_postfilter
from ocr_eval.metrics import latency_summary, score_item, summarize

SCORINGS = ("raw", "postfilter")


@dataclass
class RunOptions:
    # crops read one at a time for the single-crop latency of engines with
    # batch_size > 1 (with batch_size 1 every crop is a single-crop call)
    single_latency_samples: int = 50
    # untimed calls before timing (lazy initialization, caches)
    warmup: int = 1


def load_images(dataset: Dataset) -> list[np.ndarray]:
    images = []
    for sample in dataset.samples:
        image = dataset.load_image(sample)
        # engines get read-only crops: one engine can't change another's input
        image.flags.writeable = False
        images.append(image)
    return images


def _as_recognition(value) -> Recognition:
    if isinstance(value, Recognition):
        recognition = value
    elif isinstance(value, str):
        recognition = Recognition(value)
    else:
        recognition = Recognition(*value)
    text = recognition.text if isinstance(recognition.text, str) else ""
    confidence = recognition.confidence
    if confidence is not None:
        confidence = float(confidence)
    return Recognition(text, confidence, recognition.info)


def _recognize(engine: Engine, crops, field_types) -> list[Recognition]:
    output = engine.recognize(list(crops), list(field_types))
    if output is None or len(output) != len(crops):
        raise RuntimeError(
            f"{engine.key} returned {0 if output is None else len(output)} results "
            f"for {len(crops)} crops"
        )
    return [_as_recognition(value) for value in output]


def _environment() -> dict:
    packages = {}
    for name in ("numpy", "opencv-python-headless", "opencv-python", "tesserocr"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    return {
        "platform": sys.platform,
        "os": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "packages": packages,
    }


def run_engine(
    engine_class: type[Engine],
    variant: str,
    dataset: Dataset,
    images: list[np.ndarray],
    options: RunOptions | None = None,
    log=print,
) -> dict:
    """Run one engine variant on a dataset; returns the run record (see
    run_all for the layout). Never raises for engine problems: an unavailable
    engine is "skipped", a failing one "error"."""
    options = options or RunOptions()
    record = {
        "dataset": dataset.name,
        "engine": engine_class.name,
        "variant": variant,
        "key": f"{engine_class.name}:{variant}",
        "status": "ok",
    }
    reason = engine_class.unavailable_reason()
    if reason:
        record.update(status="skipped", reason=reason)
        return record

    engine = None
    try:
        engine = engine_class(variant)
        record["engine_info"] = engine.info()
        started = time.perf_counter()
        engine.load()
        record["load_seconds"] = round(time.perf_counter() - started, 3)
        record["engine_info"] = engine.info()

        samples = dataset.samples
        field_types = [s.field_type for s in samples]
        for i in range(min(options.warmup, len(samples))):
            _recognize(engine, [images[i]], [field_types[i]])

        batch_size = max(1, int(engine.batch_size))
        recognitions: list[Recognition] = []
        per_crop_ms: list[float] = []
        started_all = time.perf_counter()
        # the CPU time of every thread of the process (an engine's thread pool
        # included): what the work costs, which wall time hides on many cores
        cpu_started = time.process_time()
        for start in range(0, len(samples), batch_size):
            crops = images[start : start + batch_size]
            started = time.perf_counter()
            recognitions.extend(
                _recognize(engine, crops, field_types[start : start + batch_size])
            )
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            per_crop_ms.extend([elapsed_ms / len(crops)] * len(crops))
            if log and (start // batch_size) % 100 == 99:
                log(f"  {record['key']}: {len(recognitions)}/{len(samples)}")
        total_seconds = time.perf_counter() - started_all
        batch_cpu_ms = (time.process_time() - cpu_started) * 1000.0 / len(samples)

        if batch_size == 1:
            single_ms = per_crop_ms
            single_cpu_ms = batch_cpu_ms
        else:
            single_ms = []
            cpu_started = time.process_time()
            for i in range(min(options.single_latency_samples, len(samples))):
                started = time.perf_counter()
                _recognize(engine, [images[i]], [field_types[i]])
                single_ms.append((time.perf_counter() - started) * 1000.0)
            single_cpu_ms = (
                (time.process_time() - cpu_started) * 1000.0 / len(single_ms)
                if single_ms
                else None
            )
        record["latency"] = {
            "single": latency_summary(single_ms),
            "batch": latency_summary(per_crop_ms),
            "batch_size": batch_size,
            "total_seconds": round(total_seconds, 3),
            # mean process CPU time per crop, ms
            "cpu_ms": {
                "single": None if single_cpu_ms is None else round(single_cpu_ms, 3),
                "batch": round(batch_cpu_ms, 3),
            },
        }

        predictions = []
        scored = {scoring: [] for scoring in SCORINGS}
        for sample, recognition, ms in zip(samples, recognitions, per_crop_ms):
            raw = score_item(recognition.text, sample.text, sample.field_type)
            filtered_text = scoresight_postfilter(recognition.text, sample.field_type)
            filtered = score_item(filtered_text, sample.text, sample.field_type)
            scored["raw"].append((sample, raw))
            scored["postfilter"].append((sample, filtered))
            prediction = {
                "id": sample.id,
                "truth": sample.text,
                "text": recognition.text,
                "conf": recognition.confidence,
                "ms": round(ms, 3),
                "exact": raw.exact,
                "pf_exact": filtered.exact,
            }
            if filtered_text != recognition.text:
                prediction["pf_text"] = filtered_text
            if recognition.info:
                prediction["info"] = recognition.info
            predictions.append(prediction)
        record["scores"] = {
            scoring: summarize(items) for scoring, items in scored.items()
        }
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


def run_all(
    datasets: list[Dataset],
    engines: list[tuple[type[Engine], str]],
    options: RunOptions | None = None,
    label: str | None = None,
    log=print,
) -> dict:
    """Run every engine variant on every dataset. The results:

    {"schema", "harness_version", "created", "label", "environment",
     "datasets": {name: {"path", "n", "manifest_sha256", "description",
                         "subset"? (dataset.Dataset.subset, when not all crops)}},
     "runs": [{"dataset", "engine", "variant", "key", "status" (ok | skipped |
               error), "reason", "engine_info", "load_seconds",
               "latency": {"single", "batch", "batch_size", "total_seconds",
                           "cpu_ms": {"single", "batch"}},
               "scores": {"raw" | "postfilter": summary (metrics.summarize)},
               "predictions": [{"id", "truth", "text", "conf", "ms", "exact",
                                "pf_exact", "pf_text"?, "info"?}]}]}
    """
    results = {
        "schema": RESULTS_SCHEMA,
        "harness_version": HARNESS_VERSION,
        "created": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "label": label,
        "environment": _environment(),
        "datasets": {},
        "runs": [],
    }
    for dataset in datasets:
        try:
            relative = dataset.path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            relative = str(dataset.path)
        results["datasets"][dataset.name] = {
            "path": relative,
            "n": len(dataset),
            "manifest_sha256": dataset.manifest_sha256,
            "description": dataset.description,
        }
        if dataset.subset:
            results["datasets"][dataset.name]["subset"] = dataset.subset
        if log:
            log(f"{dataset.name}: loading {len(dataset)} crops")
        images = load_images(dataset)
        for engine_class, variant in engines:
            if log:
                log(f"{dataset.name}: {engine_class.name}:{variant}")
            record = run_engine(engine_class, variant, dataset, images, options, log)
            if log and record["status"] != "ok":
                log(f"  {record['status']}: {record.get('reason')}")
            elif log:
                raw = record["scores"]["raw"]["exact"]["value"]
                log(f"  exact {raw:.3f}")
            results["runs"].append(record)
    return results
