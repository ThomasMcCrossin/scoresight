"""ScoreSight's OCR evaluation harness.

Measures OCR engines (ScoreSight's own Tesseract pipeline, and any other engine
with an adapter in ocr_eval/engines/) on datasets of real scoreboard crops, and
compares the results with a committed baseline. Run it from the repository root:

    python -m ocr_eval list
    python -m ocr_eval run --dataset textocr_scoreboards --engine tesseract --out results/run1
    python -m ocr_eval compare ocr_eval/baselines/tesseract-windows.json results/run1/results.json

See docs/development/ocr-eval.md.
"""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent
DATASETS_DIR = PACKAGE_DIR / "datasets"
BASELINES_DIR = PACKAGE_DIR / "baselines"

# Bumped when the meaning of a number in the results changes (normalization,
# metric definitions), so results of different versions aren't compared blindly.
HARNESS_VERSION = "1"
RESULTS_SCHEMA = "scoresight-ocr-eval/1"
