"""Head-to-head comparison of different engines on the crops they share.

`python -m ocr_eval compare` checks one engine variant against its own
baseline. This compares every run of one results file with every run of
another (e.g. a VLM run on a stratified sample against the committed Tesseract
baseline, which has every crop), on the crops both read, pairing them crop by
crop: both accuracies on exactly the same crops, the crops only one of them
read right, and an exact McNemar test. When the dataset can be found (by the
path or name the results recorded), also the photos the crops come from
(dataset.Sample.cluster), the 95% interval of the difference with photos
resampled, and a paired sign-flip test on the per-photo differences: crops of
one photo aren't independent, and McNemar's test treats them as if they were.

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

from ocr_eval import REPO_ROOT, utf8_output
from ocr_eval.dataset import load_dataset
from ocr_eval.metrics import (
    cluster_bootstrap_interval,
    cluster_count,
    cluster_sign_flip_p,
    mcnemar_exact_p,
    wilson_interval,
)
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
    # with the crops' photos known: how many photos, the 95% interval of the
    # difference (b - a) with photos resampled, and the sign-flip p-value
    clusters: int | None = None
    delta_ci: tuple[float, float] | None = None
    cluster_p: float | None = None

    @property
    def delta(self) -> float:
        return (self.b_right - self.a_right) / self.n if self.n else 0.0


def dataset_clusters(*results_files: dict) -> dict[str, dict[str, str]]:
    """dataset name -> {crop id: cluster} for the datasets of results files
    that can be found, by the path the results recorded (relative to the
    repository) or by name."""
    clusters = {}
    for results in results_files:
        for name, info in results.get("datasets", {}).items():
            if name in clusters:
                continue
            refs = [REPO_ROOT / info["path"]] if info.get("path") else []
            for ref in refs + [name]:
                try:
                    dataset = load_dataset(ref)
                except Exception:
                    continue
                clusters[name] = {s.id: s.cluster for s in dataset.samples}
                break
    return clusters


def pair_runs(
    a: dict, b: dict, a_pattern="*", b_pattern="*", scoring="raw", clusters=None
):
    """Every (run of a, run of b) on the same dataset whose keys match the
    patterns, compared on the crops both have predictions for. clusters
    (dataset_clusters()) adds the clustered statistics where it knows every
    compared crop."""
    flag = _FLAGS[scoring]
    clusters = clusters or {}
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
            pair = Pair(
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
            crop_clusters = clusters.get(run_a["dataset"], {})
            if all(i in crop_clusters for i in common):
                keys = [crop_clusters[i] for i in common]
                differences = [
                    int(predictions_b[i]) - int(predictions_a[i]) for i in common
                ]
                pair.clusters = cluster_count(keys)
                pair.delta_ci = cluster_bootstrap_interval(differences, keys)
                pair.cluster_p = cluster_sign_flip_p(differences, keys)
            pairs.append(pair)
    return pairs


def _rate(k: int, n: int) -> str:
    low, high = wilson_interval(k, n)
    return f"{pct(k / n)} ({pct(low)}–{pct(high)})" if n else "–"


def render_pairs(pairs: list[Pair], scoring: str) -> str:
    lines = [
        f"# Head to head ({scoring} exact match, on the crops both runs read)",
        "",
        "| Dataset | A | B | n | A exact % | B exact % | Δ points | A only | B only "
        "| p (McNemar) | Photos | Δ 95% CI, photos resampled | p (photos) |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for pair in pairs:
        if pair.clusters is None:
            clustered = "– | – | –"
        else:
            low, high = pair.delta_ci
            clustered = (
                f"{pair.clusters} | {low * 100:+.1f} to {high * 100:+.1f} "
                f"| {pair.cluster_p:.2g}"
            )
        lines.append(
            f"| {pair.dataset} | {pair.a_key} | {pair.b_key} | {pair.n} "
            f"| {_rate(pair.a_right, pair.n)} | {_rate(pair.b_right, pair.n)} "
            f"| {pair.delta * 100:+.1f} | {pair.a_only} | {pair.b_only} "
            f"| {pair.p_value:.2g} | {clustered} |"
        )
    lines += [
        "",
        "McNemar's test treats the crops as independent; the photo columns "
        "resample the photos the crops come from (or the groups of photos of "
        "one board) and test the per-photo differences with random sign flips. "
        "The p-values aren't corrected for multiple comparisons.",
    ]
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
    pairs = pair_runs(
        a, b, args.a_key, args.b_key, args.scoring, clusters=dataset_clusters(a, b)
    )
    markdown = render_pairs(pairs, args.scoring)
    if args.markdown:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown).write_text(markdown, encoding="utf-8", newline="\n")
    print(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
