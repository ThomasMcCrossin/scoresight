---
title: OCR Evaluation
parent: Developer Guide
nav_order: 6
description: "Measure OCR engines on real scoreboard crops against a committed baseline, add an engine adapter, and contribute evaluation data."
---

# OCR Evaluation
{: .no_toc }

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Why

Whether ScoreSight should keep Tesseract, tune it, or move to another engine (a small recognizer such as PaddleOCR or PARSeq, the operating system's OCR, or a small vision-language model) is decided by measurement only: every engine reads the same real scoreboard crops, the results are compared with a committed baseline, and the comparison runs in CI. The harness is the `ocr_eval` package at the repository root (not shipped with the app).

```bash
python -m ocr_eval list                                   # datasets, engines and whether they can run here
python -m ocr_eval run --dataset textocr_scoreboards --dataset synthetic_7seg \
    --engine tesseract --out results/my-change            # results.json + report.md
python -m ocr_eval compare ocr_eval/baselines/tesseract.json results/my-change/results.json
python -m ocr_eval report results/my-change/results.json  # print the markdown report again
```

Run it from the repository root with the development environment (see [Building from Source](building.md)); the Tesseract engine needs nothing beyond `requirements.txt`. The harness never touches your ScoreSight settings or logs: it points `SCORESIGHT_DATA_DIR` and `SCORESIGHT_LOG_DIR` at a temporary folder unless you set them.

`run` options: `--engine NAME` runs the engine's default variants, `NAME:VARIANT` (or `NAME:V1,V2`, `NAME:*`) chooses; both `--dataset` and `--engine` repeat. `--split dev` or `--split test` keeps one split, `--limit N` the first N crops (quick runs), `--sample N` a stratified sample of N crops (for slow engines: allocated to the field types in proportion, with at least one each, and chosen by a hash of the crop id and `--seed`, so it is reproducible and the same crops on every machine), `--label` names the run in the report. A run on a subset records it in `results.json` (`datasets.<name>.subset`) and its report says which subset it is. `compare` exits with 1 when a run regresses (see [CI](#continuous-integration)) and 2 on bad input; `--markdown FILE` also writes the comparison.

## Datasets

A dataset is a folder with `manifest.jsonl`, the crop images, and `LICENSE` and `ATTRIBUTION.md` files. Datasets are found by name in `ocr_eval/datasets/` and in the folders listed in `$OCR_EVAL_DATASETS` (separated like `PATH`), or given by path. `python -m ocr_eval validate NAME_OR_PATH [--strict-licenses]` checks one.

Each line of `manifest.jsonl` is one crop:

| Field | Meaning |
|---|---|
| `id` | Unique id: letters, digits, `.`, `_`, `-` |
| `image` | The crop, a PNG path relative to the folder. Always the **raw** colour or gray crop, as a user's box would cut it from the frame, never a binarized one: preprocessing is part of what is evaluated |
| `text` | The ground truth, exactly as displayed |
| `field_type` | `score`, `clock`, `period`, `number`, `text` or `other` (below) |
| `display_tech` | `led7` (7-segment), `dotmatrix`, `lcd`, `bulb`, `flip` (flip or hand-hung cards), `broadcast` (rendered graphics), `printed` (painted or printed text), `unknown` |
| `split` | `dev` (tune on it) or `test` (report on it); `train` for crops meant for training. Assigned per source image, so one scoreboard is never in two splits |
| `label_source` | `human`, `model-assisted-unverified` or `synthetic` |
| `license` | The crop's license, SPDX style (`CC-BY-2.0`, `CC-BY-SA-4.0`, `CC0-1.0`, `PDM-1.0`, ...) |
| `source_url`, `author`, `attribution` | Where the source image comes from, who made it, and the attribution line its license asks for |
| `source_box` | `[x, y, w, h]` of the crop in the source image, or `null` |
| `notes` | Free text |

Other keys are allowed and kept (the TextOCR rows add `source_image` and `word_box`).

Each field type is read with the box settings ScoreSight gives that kind of box (`ocr_eval/fields.py`, from `defaults.py`):

| `field_type` | ScoreSight box | Character whitelist | Format regex |
|---|---|---|---|
| `score` | Home Score preset | digits | `^1?\d{1,2}$` (0 to 199) |
| `clock` | Time preset | digits, `:`, `.` | `MM:SS` or `SS.D` |
| `period` | Period preset | digits | `^[1-4]$` |
| `number` | custom box | digits | any number |
| `text`, `other` | custom box of type Text | letters, digits, punctuation | any text |

Settings that only matter across frames or format the output (smoothing, "skip similar image", ordinal indicator, leading zeros) are off: every crop is read once, as a fresh box.

### The committed datasets

**`textocr_scoreboards`** (1,276 crops from 219 photos, about 11 MB): real scoreboards and clocks. The photos are the TextVQA images tagged "Scoreboard" or "Digital clock" whose Open Images metadata lists a license that allows redistribution (all of them are CC BY 2.0); the transcriptions are TextOCR's human annotations (CC BY 4.0). `ocr_eval/builders/textocr_scoreboards.py` rebuilds it from scratch (`python -m ocr_eval.builders.textocr_scoreboards --cache FOLDER`; it downloads about 3.1 GB, 2.7 GB of which is the Open Images metadata CSV, filtered as it streams in, and keeps about 0.5 GB in the cache folder). It keeps clocks (`M:SS`, `MM:SS`, `S.D`), numbers of 1 to 3 digits, ordinals and common scoreboard words that are at least 12 px tall and nearly level, at most 12 per photo, and pads each word box by a quarter of its height like a user's box. Every remaining crop was then reviewed on contact sheets (`--contact-sheets FOLDER` renders them): crops that aren't scoreboard values (phone screens, analog dials, signs, jerseys, ads, keypads), aren't legible, or whose transcription disagrees with the display were dropped, and each photo or crop got a display technology. The decisions are in `ocr_eval/builders/textocr_scoreboards_review.json`, and the dataset's `dropped.jsonl` and `README.md` list every dropped candidate with its reason. Field types come from the transcription only: `number` covers scores, periods, innings and other numbers alike. The review was model-assisted (Claude), so a second human pass is welcome.

**`synthetic_7seg`** (56 crops): rendered 7-segment LED and LCD displays from `tests/synthetic_images.py`, CC0. A control, not a measure of real-world accuracy; `python -m ocr_eval.builders.synthetic_7seg` rebuilds it.

## Metrics

Both the prediction and the ground truth are normalized first: Unicode NFKC (full-width digits and colons become ASCII), every space removed, and `text`/`other` compared case-insensitively. Nothing else, and in particular **a clock's separator must match**: `12:34` (minutes:seconds) and `12.34` are different readings, ScoreSight's Time formats tell them apart, and an overlay showing the wrong one is wrong.

| Metric | Definition |
|---|---|
| Exact | The normalized prediction equals the normalized truth. The headline number |
| Digits | For numeric field types, the digits match with every other character removed (`12.34` matches `12:34`; `1O` doesn't match `10`). For `text`/`other`, the same as Exact |
| CER | Character error rate: total edit distance / total ground-truth characters |
| Empty | The engine returned nothing |
| Post-filter exact | Exact match of what ScoreSight would publish: the reading without characters outside the field type's whitelist, or nothing if it doesn't fully match the box's format regex. For Tesseract this is the pipeline's own verdict (its prediction records `info.state`: `Success`, `FailedFilter` or `Empty`); for other engines it shows what plugging them into ScoreSight's filters would give |
| Latency | Per crop, in ms, p50 / p95. *Single*: one crop per call. *Batch*: the call time divided by the crops in it, for engines that take batches |

Accuracies come with a 95% Wilson score interval and CER with a 95% bootstrap interval (2,000 resamples, fixed seed), so small differences aren't over-read: on 1,276 crops an accuracy near 30% is known to about ±2.5 points. Every metric is also broken down by field type, display technology and split. `compare` pairs the two runs crop by crop and reports the crops lost and gained and an exact McNemar test.

## Baseline

`ocr_eval/baselines/tesseract.json` holds every Tesseract variant on both datasets, with every prediction; `ocr_eval/baselines/tesseract.md` is its report. It was made on Linux (tesserocr 2.11.0 with Tesseract 5.5.1, as in CI); Windows (tesserocr 2.10.0, Tesseract 5.5.2) gave identical predictions.

`textocr_scoreboards`, exact match (95% CI) and latency per crop:

| Variant | Exact % | Clock % | Number % | Text % | Post-filter % | ms p50 / p95 |
|---|---:|---:|---:|---:|---:|---:|
| `eng-nobin` | 35.9 (33.3–38.6) | 12.2 | 40.6 | 30.3 | 35.9 | 2.2 / 6.5 |
| `eng` | 30.1 (27.6–32.7) | 10.1 | 34.4 | 23.8 | 30.1 | 2.2 / 7.4 |
| `scoreboard_general-nobin` | 18.6 (16.5–20.8) | 6.5 | 24.1 | 0.0 | 18.6 | 1.5 / 3.6 |
| `scoreboard_general` (the app's default) | 17.6 (15.6–19.7) | 4.3 | 23.0 | 0.0 | 17.6 | 1.5 / 3.7 |
| `scoreboard_general_large` | 14.9 (13.0–17.0) | 4.3 | 19.4 | 0.0 | 14.9 | 4.8 / 12.2 |
| `scoreboard_general_large-nobin` | 14.8 (13.0–16.9) | 3.6 | 19.4 | 0.0 | 14.8 | 4.7 / 12.3 |
| `daktronics` | 8.9 (7.4–10.5) | 0.7 | 11.8 | 0.0 | 8.9 | 1.3 / 2.8 |
| `daktronics-nobin` | 7.6 (6.3–9.2) | 0.7 | 10.1 | 0.0 | 7.6 | 1.3 / 2.9 |

On `synthetic_7seg`, `scoreboard_general` reads 58.9% (45.9–70.8), the best variant there.

What this says: with its default settings, ScoreSight's pipeline reads fewer than one in five real crops exactly; the general English model without binarization does twice as well but is still far from usable; the scoreboard models never output a letter, so they read no words, and clocks are the weakest field. Part of the gap is the eval's single-crop, default-settings setup (users tune boxes, invert patches and pick a model per board), but the size of the gap is why other engines are worth measuring. Note also that the Time format rejects soccer clocks past 59 minutes (`89:41`).

## Continuous integration

`.github/workflows/ocr-eval.yml` runs on pull requests that change recognition (`src/tesseract.py`, `src/defaults.py`, `src/text_detection_target.py`, `tesseract/`, `ocr_eval/`, `requirements.txt`, the workflow) and manually. On Ubuntu 24.04 it validates the datasets, runs every Tesseract variant on both datasets, and compares with the baseline:

```bash
python -m ocr_eval compare ocr_eval/baselines/tesseract.json ocr-eval-results/results.json \
    --max-drop 0.02 --require-all
```

It fails when a variant's exact-match accuracy (raw or post-filter) drops by more than 2 points on either dataset, or a variant didn't run. Add `--alpha 0.05` to also require the drop to be significant (McNemar). The comparison and the report go to the job summary, and the results are uploaded as the `ocr-eval-results` artifact.

When a change improves recognition, or changes a dataset, update the baseline in the same pull request: run the command the workflow runs (on Linux, or check that your platform gives the same predictions) and copy `results.json` to `ocr_eval/baselines/tesseract.json` and `report.md` to `ocr_eval/baselines/tesseract.md`. A changed dataset is flagged by `compare` (the manifest hash differs), which then compares the crops both runs have.

## Adding an engine

Engines are found automatically: every module in `ocr_eval/engines/` whose name doesn't start with `_` is imported, and every `Engine` subclass with a `name` defined in it is registered. There is no registry to edit, so adapters can be added in parallel.

```python
# ocr_eval/engines/my_engine.py
from ocr_eval.engines import Engine, EngineUnavailable, Recognition

# pip requirements beyond ScoreSight's requirements.txt (shown by
# `python -m ocr_eval requirements my-engine` and in unavailable reasons)
REQUIREMENTS = ["some-ocr-package==1.2.3", "onnxruntime==1.22.0"]


class MyEngine(Engine):
    name = "my-engine"                  # [a-z0-9_-]+, unique
    variants = ("small", "large")       # e.g. models or preprocessing options
    default_variants = ("small",)       # run by `--engine my-engine`; None = all
    description = "What it is"
    size = "5.3M parameters, 21 MB"     # for the report; info() can refine per variant
    license = "Apache-2.0"
    runtime = "onnxruntime, CPU"
    imports = ("some_ocr_package", "onnxruntime")  # checked by unavailable_reason()
    batch_size = 16                     # the most crops recognize() gets per call

    @classmethod
    def unavailable_reason(cls):       # optional: OS checks, model files ...
        return super().unavailable_reason()

    def load(self):                    # timed separately; import heavy deps here
        import some_ocr_package
        try:
            self.model = some_ocr_package.load(self.variant)
        except FileNotFoundError as e:
            raise EngineUnavailable(f"model not downloaded: {e}")

    def recognize(self, crops, field_types):
        # crops: read-only uint8 BGR arrays (H, W, 3); field_types: e.g. "clock"
        texts, scores = self.model.read(crops)
        return [Recognition(t, s) for t, s in zip(texts, scores)]

    def close(self):
        self.model = None
```

Rules:

- Don't import optional dependencies at module level: discovery must work without them. An engine that can't run is listed as unavailable with the reason and is reported as skipped, not as an error.
- `recognize()` returns one `Recognition(text, confidence, info)` (or a `(text, confidence)` tuple) per crop, in order. `confidence` is in [0, 1] or `None`; `info` is a small JSON-serializable dict kept with the prediction (e.g. a VLM's raw answer).
- Return what the engine read. Don't apply ScoreSight's filters yourself: the post-filter scoring does that for every engine. Engine-specific output cleanup (e.g. masking a CTC decoder to the field type's whitelist from `ocr_eval.fields.whitelist()`) is fair, and makes a good variant.
- Install heavy dependencies (torch, transformers, onnxruntime) in a separate virtual environment, not in the app's: `uv venv --python 3.13 .venv-eval`, then `uv pip install --python .venv-eval/Scripts/python.exe -r requirements.txt -r requirements-win.txt $(python -m ocr_eval requirements my-engine)` (`.venv-eval/bin/python` and `requirements-mac.txt` on macOS, no platform file on Linux).
- Add fast tests in `tests/test_ocr_eval_<engine>.py` that skip when the engine's dependencies are missing (`pytest.importorskip`).
- Model downloads go to the library's default cache (e.g. the Hugging Face cache); never commit weights.

## Contributing data

The more real crops, the narrower the intervals. Only data whose license allows redistribution is committed: CC0, CC BY, CC BY-SA or the public domain mark, with attribution (`validate --strict-licenses`, run by the tests and CI, enforces the license ids). Never commit frames of TV or streamed broadcasts (copyrighted), stock photos, or data under non-commercial or "no redistribution" terms (SoccerNet, SVHN, Roboflow's sets without the author's permission); keep those in a private dataset folder listed in `$OCR_EVAL_DATASETS`.

**From the Training Dojo.** ScoreSight's "Save OCR training data" writes each reading as `<id>.png` (binarized), `<id>_gray.png` (the raw crop) and `<id>.txt`; the Training Dojo corrects and approves the texts (`approved_annotations.json`). Turn a reviewed folder into a dataset:

```bash
python -m ocr_eval import-dojo "path/to/ocr_training_data" --out ocr_eval/datasets/my_dojo \
    --author "Your Name" --license CC0-1.0 --display-tech led7 [--field-type clock]
```

Only approved samples are imported (`label_source: human`; `--include-unapproved` adds the rest as `model-assisted-unverified`), always with the raw gray crop. The field type is guessed from the text unless given; running it again adds only new samples. Contributions need the contributor to grant CC0-1.0 or CC-BY-4.0 and to own the footage (your own camera at your own venue, not a broadcast).

**From other sources.** Write a builder in `ocr_eval/builders/` that downloads, selects and crops reproducibly (see `textocr_scoreboards.py`), records every photo's license and author, and keeps decisions made by hand in a review file next to it. Keep crops small (the committed sets downscale to at most 160 px tall) and the total for a dataset under about 15 MB; a large set belongs on a dataset host, with a small subset here.

## Results file

`results.json` (schema `scoresight-ocr-eval/1`) holds the environment, the datasets (with the hash of each manifest) and one record per dataset and engine variant: `status` (`ok`, `skipped` or `error`, with a `reason`), `engine_info`, `load_seconds`, `latency` (`single`, `batch`), `scores.raw` and `scores.postfilter` (the metrics above, each with `value`, `k`, `n` and `ci95`, plus `by_field_type`, `by_display_tech` and `by_split`), and `predictions`: one line per crop with `id`, `truth`, `text`, `conf`, `ms`, `exact`, `pf_exact`, and `pf_text` and `info` when present. `HARNESS_VERSION` in `ocr_eval/__init__.py` changes when a metric's definition does.
