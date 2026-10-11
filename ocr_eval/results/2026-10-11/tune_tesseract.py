"""Choose the settings of the dev-tuned Tesseract variant (tesseract:tuned) on
the dev split of the real datasets, and show how every combination does.

    python ocr_eval/results/2026-10-11/tune_tesseract.py [--out FILE.md]

Every combination of GRID is ScoreSight's real pipeline (the tesseract engine
of ocr_eval/engines/tesseract_scoresight.py with its settings replaced, PSM 8,
the field type's whitelist) on the dev crops of textocr_scoreboards and
commons_scoreboards; only exact match on those crops decides. The test split
is never read. The best combination is TUNED in tesseract_scoresight.py, and
tesseract_tuning.md in this folder is this script's output.

Settings:
  model         the bundled model
  binarization  none, or Otsu over the crop (the app's default: Otsu over the
                frame)
  dilate        the app's dilation iterations (default 1)
  dark on light invert the crop when Otsu's bright side is the minority (light
                text on a dark board), so Tesseract always sees dark text
  height        the crop scaled to this height before the pipeline (cubic up,
                area down), the app's own rescale off; "35 (app)" is the app's
                rescale to 35 px
"""

import argparse
import itertools
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ocr_eval import utf8_output  # noqa: E402
from ocr_eval.dataset import load_dataset  # noqa: E402
from ocr_eval.engines.tesseract_scoresight import (  # noqa: E402
    TUNED,
    ScoreSightTesseract,
)
from ocr_eval.metrics import score_item  # noqa: E402
from ocr_eval.runner import load_images  # noqa: E402

DATASETS = ("textocr_scoreboards", "commons_scoreboards")
SHORT = {"textocr_scoreboards": "TextOCR", "commons_scoreboards": "Commons"}
GRID = {
    "model": ("eng", "scoreboard_general"),
    "binarization": ("none", "otsu"),
    "dilate": (0, 1),
    "polarity": (True, False),
    "height": (None, 16, 20, 24, 28, 32, 48, 64, 80),
}
APP_RESCALE_HEIGHT = 35


def engine_for(model, binarization, dilate, polarity, height) -> ScoreSightTesseract:
    engine = ScoreSightTesseract(f"{model}-nobin")
    engine.model = model
    engine.overrides = {
        "binarization_method": 1 if binarization == "none" else 0,
        "dilate": dilate,
    }
    if height:
        engine.overrides["rescale_patch"] = False
    engine.height = height
    engine.polarity = polarity
    return engine


def evaluate(engine, crops) -> dict[str, tuple[int, int]]:
    """dataset -> (right, n) on the crops."""
    engine.load()
    try:
        counts = {name: [0, 0] for name in DATASETS}
        for dataset, sample, image in crops:
            [recognition] = engine.recognize([image], [sample.field_type])
            score = score_item(recognition.text, sample.text, sample.field_type)
            counts[dataset][0] += score.exact
            counts[dataset][1] += 1
        return {name: tuple(value) for name, value in counts.items()}
    finally:
        engine.close()


def main(argv=None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, help="also write the table here")
    args = parser.parse_args(argv)
    crops = []
    for name in DATASETS:
        dataset = load_dataset(name, splits=["dev"])
        crops += [
            (name, sample, image)
            for sample, image in zip(dataset.samples, load_images(dataset))
        ]
    started = time.perf_counter()
    rows = []
    for combination in itertools.product(*GRID.values()):
        settings = dict(zip(GRID, combination))
        counts = evaluate(engine_for(**settings), crops)
        right = sum(k for k, _ in counts.values())
        n = sum(n for _, n in counts.values())
        rows.append((right / n, settings, counts))
        print(f"{right / n * 100:5.1f}  {settings}", file=sys.stderr, flush=True)
    rows.sort(key=lambda row: -row[0])
    best = rows[0][1]
    chosen = {
        "model": TUNED["model"],
        "binarization": "none"
        if TUNED["overrides"]["binarization_method"] == 1
        else "otsu",
        "dilate": TUNED["overrides"]["dilate"],
        "polarity": TUNED["polarity"],
        "height": TUNED["height"],
    }
    n_dev = len(crops)
    version = ScoreSightTesseract("tuned").info().get("version", "Tesseract")
    lines = [
        f"Tesseract settings on the dev split ({n_dev} crops: "
        + ", ".join(
            f"{SHORT[d]} {sum(1 for c in crops if c[0] == d)}" for d in DATASETS
        )
        + f"), {len(rows)} combinations, best first (python "
        f"ocr_eval/results/2026-10-11/tune_tesseract.py, {version}, "
        f"{sys.platform}). An untuned preset is a variant of the report as it "
        "is.",
        "",
        "| Model | Binarization | Dilate | Dark on light | Height px "
        "| Dev exact % | " + " | ".join(f"{SHORT[d]} dev %" for d in DATASETS) + " |",
        "|---|---|---:|---|---|---:|" + "---:|" * len(DATASETS),
    ]
    for accuracy, settings, counts in rows:
        mark = " **(tuned)**" if settings == chosen else ""
        if settings == {
            "model": settings["model"],
            "binarization": settings["binarization"],
            "dilate": 1,
            "polarity": False,
            "height": None,
        }:
            mark += " (an untuned preset)"
        height = settings["height"] or f"{APP_RESCALE_HEIGHT} (app)"
        lines.append(
            f"| `{settings['model']}`{mark} | {settings['binarization']} "
            f"| {settings['dilate']} | {'yes' if settings['polarity'] else 'no'} "
            f"| {height} | {accuracy * 100:.1f} | "
            + " | ".join(f"{counts[d][0] / counts[d][1] * 100:.1f}" for d in DATASETS)
            + " |"
        )
    text = "\n".join(lines) + "\n"
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8", newline="\n")
    print(f"{time.perf_counter() - started:.0f} s", file=sys.stderr)
    if best != chosen:
        print(f"note: the best combination is {best}, TUNED is {chosen}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
