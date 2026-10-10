"""Comparing a results file with a baseline: paired, per run and scoring."""

from dataclasses import dataclass, field

from ocr_eval.metrics import mcnemar_exact_p, wilson_interval
from ocr_eval.report import pct

# scoring -> the per-prediction flag of an exact match
_FLAGS = {"raw": "exact", "postfilter": "pf_exact"}


@dataclass
class RunComparison:
    dataset: str
    key: str
    scoring: str
    n: int
    baseline: float
    new: float
    # discordant pairs: right in the baseline only / in the new run only
    lost: int
    gained: int
    p_value: float
    regression: bool
    examples: list[dict] = field(default_factory=list)

    @property
    def delta(self) -> float:
        return self.new - self.baseline


@dataclass
class Comparison:
    rows: list[RunComparison] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def _runs(results: dict) -> dict:
    return {(r["dataset"], r["key"]): r for r in results.get("runs", [])}


def compare_results(
    baseline: dict,
    new: dict,
    max_drop: float = 0.02,
    scorings=("raw", "postfilter"),
    alpha: float | None = None,
    require_all: bool = False,
) -> Comparison:
    """Compare new with baseline, run by run (same dataset and engine:variant)
    on the crops both have predictions for. A run regresses when its exact-match
    accuracy drops by more than max_drop (absolute), and, if alpha is given,
    the drop is significant (exact McNemar test, p < alpha).

    Failures: regressions; runs that are ok in the baseline but skipped or
    failed in new; and, with require_all, baseline runs missing from new."""
    comparison = Comparison()
    if baseline.get("harness_version") != new.get("harness_version"):
        comparison.warnings.append(
            f"harness versions differ ({baseline.get('harness_version')} vs "
            f"{new.get('harness_version')}): metric definitions may have changed"
        )
    base_env = baseline.get("environment", {})
    new_env = new.get("environment", {})
    if base_env.get("platform") != new_env.get("platform"):
        # Tesseract's results were identical on Windows and Linux when the
        # baseline was made; timings never compare across machines
        comparison.notes.append(
            f"platform differs ({base_env.get('platform')} vs "
            f"{new_env.get('platform')}): engine builds may differ, and latency "
            "isn't comparable"
        )
    for name, info in new.get("datasets", {}).items():
        base_info = baseline.get("datasets", {}).get(name)
        if base_info and base_info.get("manifest_sha256") != info.get(
            "manifest_sha256"
        ):
            comparison.warnings.append(
                f"dataset {name} changed since the baseline; comparing the crops both "
                "have (regenerate the baseline)"
            )

    base_runs = _runs(baseline)
    new_runs = _runs(new)
    for run_key, base in base_runs.items():
        dataset, key = run_key
        if base.get("status") != "ok":
            continue
        current = new_runs.get(run_key)
        if current is None:
            message = f"{dataset} {key}: in the baseline but not run"
            (comparison.failures if require_all else comparison.notes).append(message)
            continue
        if current.get("status") != "ok":
            comparison.failures.append(
                f"{dataset} {key}: {current.get('status')}: {current.get('reason')}"
            )
            continue
        base_predictions = {p["id"]: p for p in base.get("predictions", [])}
        new_predictions = {p["id"]: p for p in current.get("predictions", [])}
        common = [i for i in base_predictions if i in new_predictions]
        only_base = len(base_predictions) - len(common)
        only_new = len(new_predictions) - len(common)
        if only_base or only_new:
            comparison.warnings.append(
                f"{dataset} {key}: {only_base} crops only in the baseline, {only_new} "
                f"only in the new run; compared on the {len(common)} in both"
            )
        if not common:
            comparison.failures.append(f"{dataset} {key}: no crops in common")
            continue
        for scoring in scorings:
            flag = _FLAGS[scoring]
            lost = [
                i
                for i in common
                if base_predictions[i][flag] and not new_predictions[i][flag]
            ]
            gained = [
                i
                for i in common
                if new_predictions[i][flag] and not base_predictions[i][flag]
            ]
            n = len(common)
            base_acc = sum(bool(base_predictions[i][flag]) for i in common) / n
            new_acc = sum(bool(new_predictions[i][flag]) for i in common) / n
            p_value = mcnemar_exact_p(len(lost), len(gained))
            regression = base_acc - new_acc > max_drop + 1e-12 and (
                alpha is None or p_value < alpha
            )
            row = RunComparison(
                dataset=dataset,
                key=key,
                scoring=scoring,
                n=n,
                baseline=base_acc,
                new=new_acc,
                lost=len(lost),
                gained=len(gained),
                p_value=p_value,
                regression=regression,
                examples=[
                    {
                        "id": i,
                        "truth": base_predictions[i].get("truth"),
                        "baseline": base_predictions[i].get("text"),
                        "new": new_predictions[i].get("text"),
                    }
                    for i in lost[:10]
                ],
            )
            comparison.rows.append(row)
            if regression:
                comparison.failures.append(
                    f"{dataset} {key} ({scoring}): exact {pct(base_acc)}% -> "
                    f"{pct(new_acc)}% (drop {pct(base_acc - new_acc)} points > "
                    f"{pct(max_drop)}; {len(lost)} lost, {len(gained)} gained, "
                    f"McNemar p={p_value:.3g})"
                )
    for run_key, current in new_runs.items():
        if run_key not in base_runs and current.get("status") == "ok":
            comparison.notes.append(
                f"{run_key[0]} {run_key[1]}: new, not in the baseline"
            )
    return comparison


def render_comparison(comparison: Comparison, max_drop: float) -> str:
    lines = ["# OCR evaluation: comparison with the baseline", ""]
    if comparison.ok:
        lines.append(
            f"No run's exact-match accuracy dropped by more than {pct(max_drop)} points."
        )
    else:
        lines.append("**Regressions:**")
        lines.append("")
        lines += [f"- {failure}" for failure in comparison.failures]
    if comparison.warnings:
        lines += ["", "Warnings:", ""] + [f"- {w}" for w in comparison.warnings]
    if comparison.notes:
        lines += ["", "Notes:", ""] + [f"- {n}" for n in comparison.notes]
    if comparison.rows:
        lines += [
            "",
            "| Dataset | Engine:variant | Scoring | n | Baseline % | New % | Δ points "
            "| Lost | Gained | p (McNemar) | |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for row in comparison.rows:
            low, high = wilson_interval(round(row.new * row.n), row.n)
            verdict = "REGRESSION" if row.regression else ""
            lines.append(
                f"| {row.dataset} | {row.key} | {row.scoring} | {row.n} "
                f"| {pct(row.baseline)} | {pct(row.new)} ({pct(low)}–{pct(high)}) "
                f"| {row.delta * 100:+.1f} | {row.lost} | {row.gained} "
                f"| {row.p_value:.3g} | {verdict} |"
            )
        regressed = [row for row in comparison.rows if row.regression and row.examples]
        for row in regressed:
            lines += [
                "",
                f"Lost by {row.key} on {row.dataset} ({row.scoring}), first "
                f"{len(row.examples)}:",
                "",
                "| id | truth | baseline | new |",
                "|---|---|---|---|",
            ]
            for example in row.examples:
                lines.append(
                    f"| {example['id']} | {example['truth']} | {example['baseline']} "
                    f"| {example['new']} |"
                )
    return "\n".join(lines) + "\n"
