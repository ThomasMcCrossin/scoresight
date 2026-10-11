"""Head-to-head comparison of different engines on the crops they share.

`python -m ocr_eval compare` checks one engine variant against its own
baseline. This compares every run of one results file with every run of
another (e.g. a VLM run on a stratified sample against the committed Tesseract
baseline, which has every crop), on the crops both read, pairing them crop by
crop: both accuracies on exactly the same crops, the crops only one of them
read right, and an exact McNemar test.

    python -m ocr_eval.pairwise ocr_eval/baselines/tesseract.json results/vlm/results.json \\
        [--a-key 'tesseract:eng-nobin'] [--b-key 'qwen-vl:*'] [--scoring raw] [--markdown FILE]

Keys are shell-style patterns matched against "<engine>:<variant>" (default:
every run). Exit code 0, or 2 on bad input.
"""

import argparse
import fnmatch
import sys
from dataclasses import dataclass
from pathlib import Path

from ocr_eval import utf8_output
from ocr_eval.metrics import mcnemar_exact_p, wilson_interval
from ocr_eval.report import pct, read_results

_FLAGS = {"raw": "exact", "postfilter": "pf_exact"}


@dataclass
class Pair:
    dataset: str
    a_key: str
    b_key: str
    n: int
    a_right: int
    b_right: int
    # right in a only / in b only
    a_only: int
    b_only: int
    p_value: float

    @property
    def delta(self) -> float:
        return (self.b_right - self.a_right) / self.n if self.n else 0.0


def pair_runs(a: dict, b: dict, a_pattern="*", b_pattern="*", scoring="raw"):
    """Every (run of a, run of b) on the same dataset whose keys match the
    patterns, compared on the crops both have predictions for."""
    flag = _FLAGS[scoring]
    pairs = []
    for run_a in a.get("runs", []):
        if run_a.get("status") != "ok" or not fnmatch.fnmatchcase(
            run_a["key"], a_pattern
        ):
            continue
        predictions_a = {p["id"]: bool(p[flag]) for p in run_a.get("predictions", [])}
        for run_b in b.get("runs", []):
            if (
                run_b.get("status") != "ok"
                or run_b["dataset"] != run_a["dataset"]
                or not fnmatch.fnmatchcase(run_b["key"], b_pattern)
            ):
                continue
            predictions_b = {
                p["id"]: bool(p[flag]) for p in run_b.get("predictions", [])
            }
            common = [i for i in predictions_b if i in predictions_a]
            if not common:
                continue
            a_only = sum(predictions_a[i] and not predictions_b[i] for i in common)
            b_only = sum(predictions_b[i] and not predictions_a[i] for i in common)
            pairs.append(
                Pair(
                    dataset=run_a["dataset"],
                    a_key=run_a["key"],
                    b_key=run_b["key"],
                    n=len(common),
                    a_right=sum(predictions_a[i] for i in common),
                    b_right=sum(predictions_b[i] for i in common),
                    a_only=a_only,
                    b_only=b_only,
                    p_value=mcnemar_exact_p(a_only, b_only),
                )
            )
    return pairs


def _rate(k: int, n: int) -> str:
    low, high = wilson_interval(k, n)
    return f"{pct(k / n)} ({pct(low)}–{pct(high)})" if n else "–"


def render_pairs(pairs: list[Pair], scoring: str) -> str:
    lines = [
        f"# Head to head ({scoring} exact match, on the crops both runs read)",
        "",
        "| Dataset | A | B | n | A exact % | B exact % | Δ points | A only | B only "
        "| p (McNemar) |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for pair in pairs:
        lines.append(
            f"| {pair.dataset} | {pair.a_key} | {pair.b_key} | {pair.n} "
            f"| {_rate(pair.a_right, pair.n)} | {_rate(pair.b_right, pair.n)} "
            f"| {pair.delta * 100:+.1f} | {pair.a_only} | {pair.b_only} "
            f"| {pair.p_value:.2g} |"
        )
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    utf8_output()
    parser = argparse.ArgumentParser(
        prog="python -m ocr_eval.pairwise",
        description="Compare the runs of two results files crop by crop.",
    )
    parser.add_argument("a", help="results.json (A, e.g. the Tesseract baseline)")
    parser.add_argument("b", help="results.json (B)")
    parser.add_argument("--a-key", default="*", help="pattern of A's run keys")
    parser.add_argument("--b-key", default="*", help="pattern of B's run keys")
    parser.add_argument("--scoring", choices=tuple(_FLAGS), default="raw")
    parser.add_argument("--markdown", help="also write the table to this file")
    args = parser.parse_args(argv)
    try:
        a = read_results(args.a)
        b = read_results(args.b)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    markdown = render_pairs(
        pair_runs(a, b, args.a_key, args.b_key, args.scoring), args.scoring
    )
    if args.markdown:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown).write_text(markdown, encoding="utf-8", newline="\n")
    print(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
