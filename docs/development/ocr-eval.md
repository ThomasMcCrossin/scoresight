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
python -m ocr_eval review commons_scoreboards             # HTML contact sheet for checking labels
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

**`commons_scoreboards`** (1,044 crops from 186 photos, about 24 MB with the downscaled photos): the fields of physical scoreboards and stadium video boards photographed by Wikimedia Commons contributors: ice hockey, basketball, American, Canadian and association football, cricket, volleyball, table tennis and a few others. Each field is its own crop, cut by a box drawn the way a ScoreSight user would draw it, and labelled with its role (`home_score`, `clock`, `shot_clock`, `period`, `home_fouls`, `down`, `overs`, ...) and a field type from its meaning: `score` for scores, `clock` for game, shot and penalty clocks with a separator, `period`, `number` for other counts (shot clocks in whole seconds, fouls, timeouts, downs, cricket totals), `text` for team names and words. Display technologies: 411 crops 7-segment LED, 304 dot matrix, 216 video boards, 54 bulb, 51 flip or hand-hung cards. Licenses are per photo (CC BY 2.0 to 4.0, CC BY-SA 2.0 to 4.0, CC0 and public domain; crops of CC BY-SA photos stay CC BY-SA), re-checked with the Commons API on every build, and `LICENSE` and `ATTRIBUTION.md` credit every photo. `frames.jsonl` lists each photo with the URL of its 1280 px rendition and all its boxes, and `frames/` holds the photos downscaled to 576 px, for whole-frame experiments (for example a vision-language model reading the whole board). `ocr_eval/builders/commons_scoreboards.py --cache FOLDER --discover` lists the candidates (2,901 files with a usable license in the scoreboard categories) and downloads their thumbnails for choosing; about 900 thumbnails of the sport categories were looked at, 235 photos picked, and 186 used (the 49 others are in the labels file with the reason). `--cache FOLDER --frames` rebuilds the dataset from `ocr_eval/builders/commons_scoreboards_labels.json`, fetching about 60 MB of renditions at most one request per second. Photos of the same board and game share a split (`group`). The labels were drawn and transcribed with a model's help (Claude): every field looked at zoomed in, fields that weren't clearly legible left out, and every crop checked on contact sheets. They are marked `model-assisted-unverified` until a person checks them (see [Checking labels](#checking-labels)).

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

`ocr_eval/baselines/tesseract-commons.json` and `tesseract-commons.md` hold the same for `commons_scoreboards`, made the same way (Linux and Windows agreed on 8,351 of the 8,352 predictions; the one difference is a wrong reading on both). Exact match (95% CI), by field type, and latency per crop:

| Variant | Exact % | Clock % | Number % | Period % | Score % | Text % | Post-filter % | ms p50 / p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `eng-nobin` | 52.8 (49.7–55.8) | 32.7 | 52.4 | 60.3 | 62.8 | 51.5 | 52.0 | 3.8 / 12.7 |
| `eng` | 47.4 (44.4–50.4) | 22.4 | 52.1 | 52.6 | 55.3 | 42.5 | 46.7 | 4.4 / 14.7 |
| `scoreboard_general-nobin` | 44.3 (41.4–47.4) | 17.9 | 59.3 | 71.8 | 53.7 | 0.0 | 44.2 | 2.6 / 7.1 |
| `scoreboard_general` (the app's default) | 40.4 (37.5–43.4) | 16.0 | 53.2 | 69.2 | 49.2 | 0.0 | 40.2 | 2.1 / 6.4 |
| `scoreboard_general_large-nobin` | 37.4 (34.5–40.3) | 12.2 | 49.6 | 69.2 | 44.7 | 0.0 | 37.3 | 6.2 / 20.1 |
| `scoreboard_general_large` | 34.0 (31.2–36.9) | 9.0 | 42.9 | 64.1 | 44.3 | 0.0 | 33.7 | 6.4 / 22.6 |
| `daktronics-nobin` | 22.4 (20.0–25.0) | 0.6 | 24.5 | 42.3 | 36.2 | 0.0 | 22.3 | 2.3 / 6.1 |
| `daktronics` | 20.2 (17.9–22.8) | 0.0 | 22.8 | 42.3 | 31.1 | 0.0 | 20.1 | 2.0 / 5.5 |

One field per crop, boxed like a user's box, is easier than TextOCR's word crops (the app's default reads 40% instead of 18%), but the picture is the same: `eng-nobin` is best overall, carried by video boards (73% of them) and words; on 7-segment LED digits `scoreboard_general-nobin` is best (65.0%, against 59.4% for the default and 45.0% for `eng-nobin`); turning binarization off helps every model; and clocks stay the weakest field (16% with the default). The post-filter rejects up to 8 correct readings: soccer clocks past 59 minutes (`90:00`, `93:03`; the set has 11 such clocks), `0:00.0`, and periods 0 and 5.

### PaddleOCR (`ppocr`)

`ocr_eval/engines/ppocr.py` runs PaddleOCR's text recognition models (Apache-2.0) with onnxruntime: PP-OCRv6 `v6-tiny` (1.1M parameters, 4.5 MB), `v6-small` (5.2M, 21 MB) and `v6-medium` (19M, 77 MB), and PP-OCRv5 `v5-mobile`, `v5-en-mobile` (English dictionary) and `v5-server`. The official ONNX exports are downloaded from the Hugging Face Hub at pinned revisions. Only the recognizer runs, since a box already is the text line, with the models' own preprocessing (48 px high, padded to at least 320 px). The CTC output is decoded by the adapter (its texts match RapidOCR's on every crop). Variants:

- `<model>`: the raw crop, unconstrained.
- `<model>-wl`: the decoder may only emit the field type's ScoreSight whitelist (digits for a score, digits, `:` and `.` for a clock).
- `<model>-bin`, `<model>-bin-wl`: the crop after ScoreSight's own binarization (`preprocess_patch`).

`--engine ppocr` runs every model but `v5-server` (about 0.6 s per crop even on all cores) raw and `-wl`; `ppocr:*` runs everything. `OCR_EVAL_ORT_THREADS` sets onnxruntime's threads (default 1; 0 = all cores).

```bash
uv venv --python 3.13 .venv-eval
uv pip install --python .venv-eval/Scripts/python.exe -r requirements.txt -r requirements-win.txt $(python -m ocr_eval requirements ppocr)
.venv-eval/Scripts/python.exe -m ocr_eval run --dataset textocr_scoreboards --dataset synthetic_7seg --engine ppocr --out results/ppocr
```

`ocr_eval/baselines/ppocr.json` and `ppocr.md` hold the run of every variant (Windows 11, onnxruntime 1.31.0). `textocr_scoreboards` exact match (95% CI), next to Tesseract's best variant and the app's default:

| Variant | Exact % | Clock % | Number % | Text % | Post-filter % | `synthetic_7seg` % |
|---|---:|---:|---:|---:|---:|---:|
| `ppocr:v6-medium-wl` | 96.2 (95.0–97.1) | 89.2 | 97.0 | 97.8 | 95.7 | 100.0 |
| `ppocr:v6-small-wl` | 94.7 (93.4–95.8) | 84.2 | 96.1 | 96.8 | 94.4 | 100.0 |
| `ppocr:v6-medium` | 94.1 (92.7–95.3) | 89.2 | 94.3 | 97.8 | 94.0 | 98.2 |
| `ppocr:v5-en-mobile-wl` | 92.9 (91.3–94.2) | 79.9 | 94.7 | 95.1 | 92.5 | 98.2 |
| `ppocr:v6-small` | 92.0 (90.4–93.4) | 83.5 | 92.6 | 96.2 | 91.8 | 100.0 |
| `ppocr:v6-tiny-wl` | 90.8 (89.0–92.2) | 79.1 | 92.4 | 92.4 | 90.4 | 100.0 |
| `ppocr:v5-server-wl` | 90.4 (88.6–91.9) | 77.0 | 91.5 | 95.7 | 90.0 | 85.7 |
| `ppocr:v6-tiny` | 87.8 (85.9–89.5) | 75.5 | 88.9 | 92.4 | 87.5 | 100.0 |
| `ppocr:v5-mobile-wl` | 84.8 (82.7–86.7) | 63.3 | 87.3 | 89.7 | 84.4 | 82.1 |
| `ppocr:v6-medium-bin-wl` | 62.1 (59.4–64.7) | 46.0 | 67.0 | 49.7 | 61.9 | 100.0 |
| `ppocr:v6-small-bin` | 55.0 (52.3–57.7) | 43.2 | 59.2 | 43.8 | 55.3 | 98.2 |
| `tesseract:eng-nobin` | 35.9 (33.3–38.6) | 12.2 | 40.6 | 30.3 | 35.9 | 42.9 |
| `tesseract:scoreboard_general` (the app's default) | 17.6 (15.6–19.7) | 4.3 | 23.0 | 0.0 | 17.6 | 58.9 |

Paired crop by crop, `ppocr:v6-small-wl` reads 993 crops that the app's default misses and misses 8 that it reads (McNemar p < 1e-280); against `tesseract:eng-nobin` the counts are 756 and 5. The whitelist never cost a crop: it gained 26 to 68 crops per model, mostly digits that the multilingual dictionaries read as letters or CJK look-alikes (`口` for 0, `日` for 8). ScoreSight's binarization costs these models 35 to 37 points (`-bin`), so a recognizer like this should read the colour crop. Most of the remaining errors are clocks whose colon dots aren't read (`1206` for `12:06`) and look-alike digits. The post-filter column is lower only because the Time format rejects clocks past 59 minutes (`69:49`, `90:00`).

Single-crop latency, p50 / p95 ms, on the first 300 crops in one run with Tesseract. This was measured on an Intel Core i9-14900K desktop (24 cores) that was busy with other jobs, so treat it as an upper bound: Tesseract took 2.1 / 5.0 ms here, against 1.5 / 3.7 ms in the Linux baseline.

| Variant | 1 thread | all cores | all cores, batches of 16 |
|---|---:|---:|---:|
| `tesseract:scoreboard_general` | 2.1 / 5.0 | | |
| `tesseract:eng-nobin` | 2.8 / 7.6 | | |
| `ppocr:v6-tiny` | 5.3 / 7.3 | 1.8 / 5.0 | 1.1 / 4.6 |
| `ppocr:v6-small` | 17.1 / 35.6 | 4.7 / 7.3 | 3.8 / 5.0 |
| `ppocr:v5-en-mobile` | 19.8 / 31.6 | 5.4 / 7.3 | 2.9 / 4.2 |
| `ppocr:v6-medium` | 103 / 145 | 17.1 / 32.2 | 12.1 / 17.4 |

Caveat: PaddleOCR's training data is in-house and not published, so these models may have seen Open Images photos or TextOCR crops like the ones in `textocr_scoreboards`. There is no sign of it: no model reads the crops from TextOCR's train photos clearly better than those from its val photos, and the differences are well within the intervals (`v6-small-wl`: 94.6% on 1,110 train crops, 95.8% on 166 val crops). Still, the uncontaminated checks are `synthetic_7seg` and Training Dojo data.

## Operating-system OCR

`windows-ocr` (`Windows.Media.Ocr`, built into Windows 10 and 11) and `apple-vision` (Apple's Vision framework and Live Text, through [ocrmac](https://github.com/straussmaximilian/ocrmac)) read crops with the OCR that comes with the operating system: nothing to download or bundle, but each runs on one platform only, and both are document OCR, with a text detector, a language model, and no character whitelist or single-word mode. Their adapters share `ocr_eval/engines/_os_ocr.py`, and their variants combine one preprocessing with an optional `-digits` suffix:

| Variant part | What the engine is given |
|---|---|
| `raw` | The crop as it is |
| `upscale` | A crop shorter than 64 px scaled up to 64 px (bicubic), with a margin of half its height on every side in the crop's border colour: the detectors miss small text and text that touches the image edge |
| `tile` | `upscale`, then three copies of the crop side by side, half a height apart. Words are assigned to the copy under them (a word spanning several copies that reads as equal parts, like `333`, is split) and the copies' readings are majority-voted. Windows OCR never returns a lone character, and half of the real crops are one digit |
| `-digits` | For numeric field types, letters these engines read for digits are mapped to them (`O`→`0`, `l`→`1`, `S`→`5`, `B`→`8`, ...) before voting: the stand-in for Tesseract's digit whitelist |

`apple-vision` variants also name a recognition level: `accurate-...`, `fast-...` or `livetext-...` (macOS 14 or later), for example `accurate-tile-digits`. The geometry (64 px, half-height margins and gaps, three copies) was chosen on the `dev` split with Windows OCR; values around it gave the same accuracy within about a point.

**Windows.** Install the extras in the evaluation environment (`$(python -m ocr_eval requirements windows-ocr)` lists the pinned `winrt-*` packages winocr uses) and check that `python -m ocr_eval list` shows `windows-ocr` as available. It also needs the OCR language pack for English (United States), which comes with that Windows language; if it is missing, `list` says so, and an administrator PowerShell installs it with `Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"`. The adapter keeps one `OcrEngine` (winocr's helpers create one per call, which costs about 2.5 ms per crop). pywinrt ships an old `msvcp140.dll` that crashes Tesseract if it is loaded first, so the adapter loads the system's copy before importing pywinrt, and `--engine windows-ocr --engine tesseract` can share a run.

**macOS.** `apple-vision` needs `ocrmac==1.0.1` and `pyobjc-framework-Vision==12.2.2` (`python -m ocr_eval requirements apple-vision`). It hasn't been run on a Mac yet: it was written against ocrmac's API and tested with ocrmac faked, and its results record `"verified": false`. Run `python -m ocr_eval run --dataset textocr_scoreboards --dataset synthetic_7seg --engine apple-vision --out results/apple-vision` on a Mac to measure it (and to verify it: no run should end in `error`).

### Windows OCR results

`ocr_eval/baselines/windows-ocr.json` and `windows-ocr.md` hold every `windows-ocr` variant on both datasets (Windows 11 build 26200, Intel Core i9-14900K). CI doesn't run them (it runs on Linux); compare a change to the adapter with `python -m ocr_eval compare ocr_eval/baselines/windows-ocr.json NEW.json`. On `textocr_scoreboards`, next to Tesseract (same machine, same run), exact match:

| Engine:variant | Exact % (95% CI) | Clock % | Number % | Text % | 1 char % | 2 chars % | 3+ chars % | ms p50 / p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `tesseract:eng-nobin` | 35.9 (33.3–38.6) | 12.2 | 40.6 | 30.3 | 47.7 | 28.4 | 21.7 | 3.5 / 10.9 |
| `windows-ocr:tile-digits` | 25.5 (23.2–28.0) | 22.3 | 21.8 | 47.6 | 18.4 | 28.8 | 35.3 | 2.4 / 8.6 |
| `windows-ocr:tile` | 21.7 (19.5–24.1) | 21.6 | 16.8 | 47.6 | 11.0 | 28.1 | 35.0 | 2.2 / 12.5 |
| `tesseract:scoreboard_general` (the app's default) | 17.6 (15.6–19.7) | 4.3 | 23.0 | 0.0 | 28.9 | 11.1 | 3.1 | 3.0 / 7.4 |
| `windows-ocr:upscale-digits` | 15.4 (13.5–17.4) | 21.6 | 9.8 | 39.5 | 0.3 | 24.5 | 33.9 | 0.6 / 4.6 |
| `windows-ocr:upscale` | 15.1 (13.3–17.2) | 20.9 | 9.6 | 39.5 | 0.2 | 24.2 | 33.6 | 0.6 / 4.3 |
| `windows-ocr:raw-digits` | 6.6 (5.3–8.1) | 9.4 | 3.2 | 22.2 | 0.0 | 8.2 | 16.8 | 0.1 / 1.2 |
| `windows-ocr:raw` | 6.3 (5.1–7.8) | 7.9 | 3.1 | 22.2 | 0.0 | 7.8 | 16.2 | 0.1 / 1.3 |

(n: clock 139, number 948, text 185; 619 crops of 1 character, 306 of 2, 351 of 3 or more. Latencies vary by about a millisecond between runs.) On the `test` split alone: `tile-digits` 28.3%, `eng-nobin` 36.9%, `scoreboard_general` 17.7%. On `synthetic_7seg` Windows OCR reads at most 10.7% (`tile`), against 58.9% for `scoreboard_general`.

What this says:

- As it is (`raw`), Windows OCR is unusable on scoreboard crops: it returns nothing for 91% of them and reads none of the 619 single characters.
- Each step helps significantly (paired McNemar tests): upscaling (+8.8 points over `raw`, p = 4×10⁻²⁶), tiling (+6.6 over `upscale`, p = 2×10⁻¹³) and, on tiled images, the digit mapping (+3.8 over `tile`, p = 4×10⁻¹⁵; without tiling it changes 3 crops). `tile-digits` beats the app's default Tesseract setup by 7.9 points (293 crops gained, 191 lost, p = 4×10⁻⁶) and reads multi-character values (clocks, words, numbers of 3 or more digits) better than any Tesseract variant, but loses to `eng-nobin` overall by 10.4 points (176 gained, 308 lost, p = 2×10⁻⁹), mostly on single digits and 7-segment and LCD displays (led7 13.6%, lcd 4.1%).
- The two are complementary: 49.7% of the crops are read by `eng-nobin` or `tile-digits` (an upper bound, with a perfect chooser).
- Being Windows-only, it can't be ScoreSight's cross-platform engine; it is at most a candidate for text and clock boxes on Windows.

## Vision-language models

`ocr_eval/engines/vlm.py` runs small vision-language models (VLMs) on the CPU with PyTorch and Hugging Face transformers. They are optional extras, so install them in a separate virtual environment (on Linux, install PyTorch's CPU wheels first: PyPI's Linux wheels bundle CUDA, about 3 GB):

```bash
uv venv --python 3.13 .venv-vlm
# Linux only, first:
uv pip install --python .venv-vlm/bin/python --index-url https://download.pytorch.org/whl/cpu torch==2.14.1 torchvision==0.29.1
uv pip install --python .venv-vlm/Scripts/python.exe -r requirements.txt -r requirements-win.txt $(python -m ocr_eval requirements qwen-vl)
.venv-vlm/Scripts/python.exe -m ocr_eval run --dataset textocr_scoreboards --engine qwen-vl --sample 200 --out results/qwen
```

| Engine | Variants: model | Parameters (download) | License |
|---|---|---|---|
| `florence2` | `florence2-base`, `florence2-large`: Florence-2 with its `<OCR>` task | 0.23B (0.44 GB), 0.77B (1.5 GB) | MIT |
| `smolvlm` | `smolvlm-256m`, `smolvlm-500m`: SmolVLM-Instruct, the cheap control | 0.26B (0.49 GB), 0.51B (0.97 GB) | Apache-2.0 |
| `qwen-vl` | `qwen3.5-0.8b`: Qwen3.5-0.8B; `qwen3-vl-2b`: Qwen3-VL-2B-Instruct (non-thinking) | 0.9B (1.7 GB), 2.1B (4.1 GB) | Apache-2.0 |

- Every model is pinned to a Hugging Face revision and downloaded into the Hugging Face cache on first use (`HF_HUB_OFFLINE=1` uses only the cache).
- The chat models get one prompt per crop that says what the box holds (ScoreSight knows each box's field type), e.g. *"This image is cropped from a scoreboard. Read the game clock (digits with ':' or '.') shown in it. Answer with only the characters on the display, exactly as shown."* Florence-2 takes no prompt: it runs its `<OCR>` task on the crop centred on a square (variant suffix `-sq`: stretched to its square input instead).
- Decoding is greedy (temperature 0, no repetition penalty), at most 16 tokens. The answer is cleaned up mechanically only (its first line, without quotes and a trailing period); the raw answer is kept in the prediction's `info` when that changed it. The confidence is the probability of the generated sequence.
- Variant suffix `-wl`: decoding may only use tokens made of the field type's characters (the whitelist ScoreSight gives Tesseract), the VLM counterpart of masking a CTC decoder.
- The chat models read 8 crops per call (left-padded batches gave the same answers as one crop at a time); latency is reported for both. `OCR_EVAL_VLM_BATCH`, `OCR_EVAL_TORCH_THREADS` and `OCR_EVAL_TORCH_DEVICE` (`cpu`, `cuda`, `mps`) change that.
- VLMs take about a second per crop on a CPU, so `run --sample N` reads a stratified sample instead of every crop; the report says which subset it ran on. Compare engines on the same crops with `python -m ocr_eval.pairwise A.json B.json` (it pairs any two runs crop by crop, e.g. a VLM on a sample against the Tesseract baseline, which has every crop).

### Results on CPU

Measured on Windows 11 with an Intel Core i9-14900K (24 cores, 32 threads; PyTorch's 24 threads, fp32), torch 2.14.1 and transformers 5.18.0; no GPU. Every prediction is in `ocr_eval/baselines/vlm/`: `crops.json` (the variants run on every crop), `sample400.json` (those run on a stratified sample of 400 `textocr_scoreboards` crops, and every `synthetic_7seg` crop), `latency.json`, and `frames219.json` and `frames100.json` (whole frames, below), each with its `.md` report. They are reference results, not checked by CI; `python -m ocr_eval compare` against them checks a change to an adapter.

`textocr_scoreboards`, exact match (95% CI) by field type, with ScoreSight's Tesseract pipeline from the baseline for comparison:

| Engine:variant | Crops | Exact % | Clock % | Number % | Text % | CER % | Post-filter % |
|---|---:|---:|---:|---:|---:|---:|---:|
| `qwen-vl:qwen3-vl-2b` | 1276 | 93.0 (91.5–94.3) | 92.8 | 92.3 | 96.8 | 5.2 | 92.6 |
| `qwen-vl:qwen3-vl-2b-wl` | 1276 | 93.5 (92.0–94.7) | 92.8 | 92.9 | 96.8 | 4.9 | 92.9 |
| `qwen-vl:qwen3.5-0.8b` | 1276 | 91.3 (89.6–92.7) | 88.5 | 91.0 | 95.1 | 5.8 | 90.8 |
| `qwen-vl:qwen3.5-0.8b-wl` | 1276 | 91.5 (89.9–92.9) | 88.5 | 91.4 | 95.1 | 5.6 | 91.1 |
| `smolvlm:smolvlm-256m` | 1276 | 67.8 (65.2–70.3) | 46.8 | 68.6 | 80.5 | 58.1 | 68.1 |
| `smolvlm:smolvlm-256m-wl` | 1276 | 68.6 (66.0–71.1) | 54.7 | 68.5 | 80.5 | 25.0 | 68.3 |
| `smolvlm:smolvlm-500m` | 400 | 66.2 (61.5–70.7) | 29.5 | 69.7 | 77.6 | 48.0 | 66.2 |
| `smolvlm:smolvlm-500m-wl` | 400 | SMOL500_WL |
| `florence2:florence2-base-wl` | 400 | FLOR_BASE_WL |
| `florence2:florence2-base` | 400 | 56.5 (51.6–61.3) | 36.4 | 54.9 | 81.0 | 30.3 | 56.5 |
| `florence2:florence2-base-sq` | 400 | 47.8 (42.9–52.6) | 18.2 | 47.5 | 72.4 | 40.2 | 48.0 |
| `florence2:florence2-large` | 400 | FLOR_LARGE |
| `florence2:florence2-large-wl` | 400 | FLOR_LARGE_WL |
| `tesseract:eng-nobin` (baseline) | 1276 | 35.9 (33.3–38.6) | 12.2 | 40.6 | 30.3 | 55.6 | 35.9 |
| `tesseract:scoreboard_general` (the app's default) | 1276 | 17.6 (15.6–19.7) | 4.3 | 23.0 | 0.0 | 84.8 | 17.6 |

The 400-crop sample is `run --sample 400` (seed 0: 297 numbers, 58 texts, 44 clocks, 1 other); on those crops Tesseract `eng-nobin` reads 37.0% (32.4–41.8), Qwen3.5-0.8B 90.2% (86.9–92.8) and Qwen3-VL-2B 91.5% (88.4–93.9), within about a point of their full-set numbers, so the sample's rows compare with the others. On `synthetic_7seg` (56 crops): Qwen3.5-0.8B 98.2% (90.5–99.7), Qwen3-VL-2B 94.6%, SmolVLM-256M 51.8%, Florence-2-base-wl SYN_FLOR, against 58.9% for `scoreboard_general`.

Head to head on the same 1,276 crops (`python -m ocr_eval.pairwise`): Qwen3.5-0.8B reads 727 crops right that `tesseract:eng-nobin` gets wrong and 20 the other way round (McNemar p < 10⁻¹⁸⁰); against the app's default model, 961 against 18. Qwen3-VL-2B beats Qwen3.5-0.8B by 1.7 points (62 crops against 40, p = 0.04).

Latency per crop, measured separately on a stratified sample of 100 crops with the machine otherwise idle (`latency.json`; one crop per call, and in calls of 8 crops for the chat models):

| Engine:variant | One crop: p50 / p95 ms | In batches of 8: p50 ms per crop | Load s |
|---|---:|---:|---:|
| `tesseract:scoreboard_general` | 1.8 / 3.7 | – | 0.1 |
| `tesseract:eng-nobin` | 2.1 / 9.5 | – | 0.1 |
| `smolvlm:smolvlm-256m` | 382 / 667 | 335 | 0.8 |
| `qwen-vl:qwen3.5-0.8b` | 710 / 981 | 413 | 5.1 |
| `qwen-vl:qwen3.5-0.8b-wl` | 622 / 901 | 390 | 2.5 |
| `florence2:florence2-base-wl` | 663 / 703 | – | 1.0 |
| `qwen-vl:qwen3-vl-2b` | 898 / 1325 | 704 | 3.9 |
| `florence2:florence2-large-wl` | about 2,300 (from its accuracy run) | – | |

Load times are with the model already in the Hugging Face cache (the first run downloads it); the `-wl` row was measured before the two fixes to its token mask (spaces, and periods or newlines ending an answer), which don't change what a token costs. Qwen3.5's linear-attention layers run PyTorch's reference implementation on a CPU (the fast kernels need CUDA), so it may get faster.

The confidence is useful: Qwen3.5-0.8B's answers with confidence ≥ 0.5 cover 80.6% of the crops at 97.4% accuracy, ≥ 0.7 cover 68.3% at 99.2%; Qwen3-VL-2B's ≥ 0.9 cover 90.8% at 98.1%. (Tesseract `eng-nobin` at ≥ 0.5: 55.9% of the crops at 54.3%.)

What this says:

- Every model reads real scoreboards far better than ScoreSight's Tesseract pipeline, even the 256M control. A 0.8B model reads nine crops in ten exactly where Tesseract reads one in three at best (one in six with the app's defaults), on every field type and display technology; its weakest are incandescent bulb boards (65%) and LCDs (86.5%).
- The cost is time and size: 0.4–0.7 s per crop against 2 ms, so about 4 s for a frame of 10 boxes on a fast desktop CPU (a laptop CPU will be slower; a GPU or Apple silicon faster, not measured here), and PyTorch plus a 1.7 GB model. That doesn't fit ScoreSight's per-frame loop as it is.
- The errors left are small or dim digits on dot-matrix and bulb boards (a dark "0" read as "1" is the commonest), a missed clock separator, and a few crops whose truth is debatable (a neighbour's digit at the crop's edge).
- `-wl` makes no difference to the Qwen models, which already answer with just the characters; it helps Florence-2, whose `<OCR>` output mixes up letters and digits. Florence-2 needs its crop letterboxed (stretched, it loses 8.8 points); `florence2-large` is not better than `base` here.

Next steps this suggests (not measured yet): a VLM per box at a lower rate, only for boxes whose image changed (ScoreSight already detects that), with its confidence deciding whether to keep the previous value; or Tesseract every frame with a VLM checking it; Qwen3.5-0.8B on a GPU, Apple's MPS, or as a GGUF in llama.cpp, to see how fast it gets; and the VLM's readings as labels to train a small fast recognizer (PP-OCR, PARSeq) on scoreboards.

### Whole frames

A VLM can also look at the whole frame once and read every box in one call. `python -m ocr_eval.frames` groups a dataset's crops by the frame they were cut from (the row's `frame` or `source_image` key), finds the frame's image (the row's `frame_image`, a path in the dataset folder, or `--frames-dir FOLDER/<id>.jpg`), gives the engine the frame and every box (the crop's `source_box`, plus the row's `role`, e.g. "home score", when the dataset has one) and scores each box's reading like a crop's:

```bash
python -m ocr_eval.frames --dataset textocr_scoreboards --frames-dir CACHE/images \
    --engine qwen-vl:qwen3.5-0.8b --mode boxes,marks --out results/frames [--frames 50]
python -m ocr_eval.pairwise results/qwen/results.json results/frames/results.json
```

Modes: `qwen-vl` `boxes` lists the boxes' coordinates (0–1000 scale) in the prompt, `marks` draws numbered boxes on the frame; both ask for a JSON object of the boxes' texts (the start of the answer is written for the model, because the small Qwen models otherwise answer in their grounding format, which is still parsed). `florence2` `spot` runs `<OCR_WITH_REGION>` on the frame and gives each box the words centred in it. An engine reads frames if it has `frame_modes` and `read_frame(frame, fields, mode)`. `textocr_scoreboards` doesn't ship its photos; its builder's cache has them (`<cache>/images/`).

On `textocr_scoreboards`'s photos (219 frames with 1 to 12 boxes, 5.8 on average; 100 of them, chosen by `--frames 100`, for the slower runs), each box's exact match, and the same boxes read as crops by the same model:

| Engine:variant@mode | Frames | Boxes | Exact % | As crops % | ms per frame p50 / p95 | ms per box p50 |
|---|---:|---:|---:|---:|---:|---:|
| `qwen-vl:qwen3-vl-2b@frames-boxes` | 100 | 563 | 39.6 (35.6–43.7) | 90.8 | 12,182 / 20,175 | 1,817 |
| `florence2:florence2-base@frames-spot` | 100 | 563 | 33.6 (29.8–37.6) | – | 2,625 / 9,594 | 554 |
| `qwen-vl:qwen3.5-0.8b@frames-marks` | 100 | 563 | 32.1 (28.4–36.1) | 89.7 | 6,771 / 12,121 | 973 |
| `qwen-vl:qwen3.5-0.8b@frames-boxes` | 219 | 1276 | 31.5 (29.0–34.1) | 91.3 | 6,534 / 12,050 | 1,012 |

(Frame times come from the accuracy runs, on the same machine, mostly idle.) Reading the whole frame is much worse with these models, and not faster per box: they misplace boxes, reading a neighbour's value or repeating one value for several boxes, and a 15–30 px digit in a 1,000 px photo is a much smaller target than in its crop. The Qwen models do best on clocks, the largest text (62–64%). TextOCR has no semantic field names, so prompting by role ("home score": the rows' `role` key) is implemented but not measured; a dataset with full frames and roles (such as the Wikimedia Commons set) can measure it with the same command.

## Continuous integration

`.github/workflows/ocr-eval.yml` runs on pull requests that change recognition (`src/tesseract.py`, `src/defaults.py`, `src/text_detection_target.py`, `tesseract/`, `ocr_eval/`, `requirements.txt`, the workflow) and manually. On Ubuntu 24.04 it validates the datasets, runs every Tesseract variant on the committed datasets, and compares with the baseline:

```bash
python -m ocr_eval compare ocr_eval/baselines/tesseract.json ocr-eval-results/results.json \
    --max-drop 0.02 --require-all
```

It fails when a variant's exact-match accuracy (raw or post-filter) drops by more than 2 points on either dataset, or a variant didn't run. The same run also reads `commons_scoreboards`, compared with its own baseline, `ocr_eval/baselines/tesseract-commons.json`, in a second step. Add `--alpha 0.05` to also require the drop to be significant (McNemar). The comparisons and the report go to the job summary, and the results are uploaded as the `ocr-eval-results` artifact.

When a change improves recognition, or changes a dataset, update the baseline in the same pull request: run the command the workflow runs (on Linux, or check that your platform gives the same predictions) and copy `results.json` to `ocr_eval/baselines/tesseract.json` and `report.md` to `ocr_eval/baselines/tesseract.md`; for `commons_scoreboards`, run it alone (`--dataset commons_scoreboards`) and copy the files to `tesseract-commons.json` and `tesseract-commons.md`. A changed dataset is flagged by `compare` (the manifest hash differs), which then compares the crops both runs have.

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

**From other sources.** Write a builder in `ocr_eval/builders/` that downloads, selects and crops reproducibly (see `textocr_scoreboards.py`, or `commons_scoreboards.py` for photos labelled by hand), records every photo's license and author, and keeps decisions made by hand in a review or labels file next to it. Keep crops small (the committed sets downscale to at most 160 px tall) and the total for a dataset under about 25 MB; a large set belongs on a dataset host, with a small subset here.

### Checking labels

Labels that a model helped make (`label_source: model-assisted-unverified`) should be checked by a person. `python -m ocr_eval review DATASET [--out FILE] [--results RESULTS.json [--run engine:variant,...]]` writes one self-contained HTML page (the images are embedded) with every crop, its text, field type, display technology and role, grouped by source photo with its link, author and license; for datasets with `frames.jsonl`, each photo can be opened with all its boxes drawn. With `--results`, each crop also shows what each engine read, and "only crops no engine read" filters to the likeliest label errors. Mark each crop **OK**, **Fix** (type the correct text) or **Drop** (with a reason); "Mark shown as OK" marks every shown crop without a decision. Decisions are kept in the browser, and **Export decisions** saves them as a JSON file (`scoresight-ocr-eval-review/1`: the dataset, its manifest hash, the reviewer and `decisions` by crop id), which **Import** loads again. For `commons_scoreboards`, `python -m ocr_eval.builders.commons_scoreboards --apply-review FILE` applies an export to the labels file (checked fields become `human`, fixed texts keep the old one as `corrected_from`, dropped fields move to `rejected_fields`); rebuild with `--cache FOLDER --frames` and regenerate its baseline afterwards. For other datasets, carry the decisions into their review file (the crop ids of `textocr_scoreboards` are the TextOCR word ids that `textocr_scoreboards_review.json` uses).

## Results file

`results.json` (schema `scoresight-ocr-eval/1`) holds the environment, the datasets (with the hash of each manifest, and a `subset` when the run didn't read every crop: `splits`, `sample` with its `seed`, `limit`, or the `frames` of a whole-frame run) and one record per dataset and engine variant: `status` (`ok`, `skipped` or `error`, with a `reason`), `engine_info`, `load_seconds`, `latency` (`single`, `batch`), `scores.raw` and `scores.postfilter` (the metrics above, each with `value`, `k`, `n` and `ci95`, plus `by_field_type`, `by_display_tech` and `by_split`), and `predictions`: one line per crop with `id`, `truth`, `text`, `conf`, `ms`, `exact`, `pf_exact`, and `pf_text` and `info` when present. A whole-frame run (`ocr_eval.frames`) has the key `<engine>:<variant>@frames-<mode>`, `latency.frame` (per frame), `frames` (each frame's key, number of boxes, time and the engine's `info`, e.g. its raw answer) and the frame's key in each prediction. `HARNESS_VERSION` in `ocr_eval/__init__.py` changes when a metric's definition does.
