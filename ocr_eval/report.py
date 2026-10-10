"""Reading and writing results files, and the markdown report."""

import json
from pathlib import Path

from ocr_eval import RESULTS_SCHEMA

_PLACEHOLDER = "@@ocr_eval_predictions_{}@@"


def write_results(path: Path, results: dict) -> None:
    """Write results as JSON: indented, with one line per prediction so that
    baselines diff readably."""
    runs = []
    blocks = {}
    for index, run in enumerate(results.get("runs", [])):
        predictions = run.get("predictions")
        if predictions is None:
            runs.append(run)
            continue
        marker = _PLACEHOLDER.format(index)
        lines = [
            json.dumps(p, ensure_ascii=False, separators=(",", ":"))
            for p in predictions
        ]
        # runs are list items at depth 2: their keys are indented by 6 spaces
        blocks[json.dumps(marker)] = (
            "[\n        " + ",\n        ".join(lines) + "\n      ]" if lines else "[]"
        )
        runs.append({**run, "predictions": marker})
    text = json.dumps({**results, "runs": runs}, indent=2, ensure_ascii=False)
    for marker, block in blocks.items():
        text = text.replace(marker, block, 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")


def read_results(path) -> dict:
    with open(path, encoding="utf-8") as f:
        results = json.load(f)
    if not isinstance(results, dict) or results.get("schema") != RESULTS_SCHEMA:
        raise ValueError(f"{path} is not an ocr_eval results file ({RESULTS_SCHEMA})")
    return results


def pct(value) -> str:
    return "–" if value is None else f"{value * 100:.1f}"


def pct_ci(metric: dict | None) -> str:
    if not metric or metric.get("value") is None:
        return "–"
    low, high = metric["ci95"]
    return f"{pct(metric['value'])} ({pct(low)}–{pct(high)})"


def _ms(latency: dict | None, key: str) -> str:
    if not latency or not latency.get(key):
        return "–"
    single = latency[key]
    return f"{single['p50_ms']:.1f} / {single['p95_ms']:.1f}"


def _escape(text) -> str:
    text = "" if text is None else str(text)
    return text.replace("|", "\\|").replace("\n", " ") or "∅"


def describe_subset(subset: dict | None) -> str:
    """A sentence saying which crops of a dataset were run, or "" for all."""
    if not subset:
        return ""
    parts = []
    if subset.get("splits"):
        parts.append(f"split {', '.join(subset['splits'])}")
    if subset.get("sample") is not None:
        parts.append(
            f"a stratified sample (by {subset.get('stratified_by', 'field_type')}, "
            f"seed {subset.get('seed', 0)}) of {subset['sample']} of "
            f"{subset.get('of', '?')} crops"
        )
    if subset.get("limit") is not None:
        parts.append(f"the first {subset['limit']}")
    if subset.get("frames") is not None:
        # ocr_eval.frames: the crops of the frames read
        parts.append(
            f"the crops of {subset['frames']} of {subset.get('of_frames', '?')} "
            f"frames (seed {subset.get('seed', 0)})"
        )
    crops = (
        f"{subset.get('n', '?')} of the manifest's {subset.get('manifest_n', '?')} "
        "crops."
    )
    return f"Subset: {'; '.join(parts)}: {crops}" if parts else f"Subset: {crops}"


def _breakdown_table(runs: list[dict], attribute: str, scoring: str) -> list[str]:
    groups = {}
    for run in runs:
        for key, summary in run["scores"][scoring][f"by_{attribute}"].items():
            groups[key] = summary["n"]
    if len(groups) < 2:
        return []
    keys = sorted(groups)
    lines = [
        "| Engine:variant | " + " | ".join(f"{k} (n={groups[k]})" for k in keys) + " |",
        "|---|" + "---:|" * len(keys),
    ]
    for run in runs:
        by = run["scores"][scoring][f"by_{attribute}"]
        cells = [pct_ci(by[k]["exact"]) if k in by else "–" for k in keys]
        lines.append(f"| {run['key']} | " + " | ".join(cells) + " |")
    return lines


def render_report(results: dict, max_examples: int = 25) -> str:
    env = results.get("environment", {})
    lines = [
        f"# OCR evaluation{': ' + results['label'] if results.get('label') else ''}"
    ]
    lines.append("")
    lines.append(
        f"Created {results.get('created', '?')} with harness v"
        f"{results.get('harness_version', '?')} on {env.get('os', '?')} "
        f"{env.get('machine', '')}, Python {env.get('python', '?')}."
    )
    lines.append("")
    lines.append(
        "Exact = normalized exact match; Digits = same digits ignoring separators; "
        "CER = character error rate; Empty = no output; Post-filter = exact match "
        "after ScoreSight's whitelist and format regex for the field type. "
        "Percentages with 95% confidence intervals (Wilson; CER: bootstrap). "
        "Latency per crop in ms, p50 / p95."
    )

    for name, info in results.get("datasets", {}).items():
        runs = [
            r
            for r in results.get("runs", [])
            if r["dataset"] == name and r["status"] == "ok"
        ]
        other = [
            r
            for r in results.get("runs", [])
            if r["dataset"] == name and r["status"] != "ok"
        ]
        lines += ["", f"## {name} ({info.get('n', '?')} crops)", ""]
        if info.get("description"):
            lines += [info["description"], ""]
        if info.get("subset"):
            lines += [describe_subset(info["subset"]), ""]
        runs.sort(key=lambda r: -(r["scores"]["raw"]["exact"]["value"] or 0))
        if runs:
            lines += [
                "| Engine:variant | Exact % | Digits % | CER % | Empty % "
                "| Post-filter exact % | ms single | ms batch | Load s |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
            for run in runs:
                raw = run["scores"]["raw"]
                post = run["scores"]["postfilter"]
                latency = run.get("latency")
                lines.append(
                    f"| {run['key']} | {pct_ci(raw['exact'])} | {pct(raw['digits']['value'])} "
                    f"| {pct_ci(raw['cer'])} | {pct(raw['empty_rate']['value'])} "
                    f"| {pct_ci(post['exact'])} | {_ms(latency, 'single')} "
                    f"| {_ms(latency, 'batch')} | {run.get('load_seconds', '–')} |"
                )
            for attribute, title in (
                ("field_type", "By field type"),
                ("display_tech", "By display technology"),
                ("split", "By split"),
            ):
                table = _breakdown_table(runs, attribute, "raw")
                if table:
                    lines += ["", f"### {title} (exact %, 95% CI)", ""] + table
        if other:
            lines += ["", "Not run:", ""]
            for run in other:
                lines.append(
                    f"- {run['key']}: {run['status']}: {_escape(run.get('reason'))}"
                )
        if runs and max_examples:
            best = runs[0]
            wrong = [p for p in best.get("predictions", []) if not p["exact"]]
            if wrong:
                lines += [
                    "",
                    f"<details><summary>Errors of {best['key']} "
                    f"(first {min(max_examples, len(wrong))} of {len(wrong)})</summary>",
                    "",
                    "| id | truth | read | post-filter |",
                    "|---|---|---|---|",
                ]
                for p in wrong[:max_examples]:
                    lines.append(
                        f"| {p['id']} | {_escape(p['truth'])} | {_escape(p['text'])} "
                        f"| {_escape(p.get('pf_text', p['text']))} |"
                    )
                lines += ["", "</details>"]
    return "\n".join(lines) + "\n"
