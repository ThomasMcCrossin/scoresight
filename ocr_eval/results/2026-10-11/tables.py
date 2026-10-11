"""Recompute the tables of REPORT.md from the results in this folder.

    python ocr_eval/results/2026-10-11/tables.py [SECTION ...] > tables.md
    python ocr_eval/results/2026-10-11/tables.py --fill ocr_eval/results/2026-10-11/REPORT.md

--fill rewrites the tables of REPORT.md in place (between its
<!-- tables:NAME --> and <!-- /tables:NAME --> markers); --check FILE exits
with 1 if they are out of date (tests/test_ocr_eval_report.py runs it).

Sections: leaderboards, pooled, field-types, display-techs, test-split,
mcnemar, calibration, latency, threads, budget, startup, galleries (default:
all).

Inputs: results.json.gz (the accuracy run: every non-VLM engine on the three
datasets), latency.json.gz (the timing runs: for each engine and thread setting,
the repeat during which the rest of the machine was least busy) and, for
reference rows, ocr_eval/baselines/vlm/crops.json.gz (VLMs, not re-run).
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from ocr_eval import utf8_output  # noqa: E402
from ocr_eval.dataset import load_dataset  # noqa: E402
from ocr_eval.metrics import mcnemar_exact_p, wilson_interval  # noqa: E402
from ocr_eval.report import read_results  # noqa: E402

REAL = ("textocr_scoreboards", "commons_scoreboards")
SHORT = {
    "textocr_scoreboards": "TextOCR",
    "commons_scoreboards": "Commons",
    "synthetic_7seg": "synthetic",
}
APP_DEFAULT = "tesseract:scoreboard_general"
# the engines of the detailed tables
KEY_ENGINES = (
    "ppocr:v6-medium-wl",
    "ppocr:v6-small-wl",
    "ppocr:v6-tiny-wl",
    "ppocr:v6-tiny",
    "ppocr:v5-en-mobile-wl",
    "onnxtr:parseq-wl",
    "onnxtr:crnn_mobilenet_v3_small-wl",
    "windows-ocr:tile-digits",
    "tesseract:eng-nobin",
    "tesseract:scoreboard_general-nobin",
    APP_DEFAULT,
)
PAIRS = (
    ("ppocr:v6-tiny-wl", "ppocr:v6-small-wl"),
    ("ppocr:v6-small-wl", "ppocr:v6-medium-wl"),
    ("ppocr:v6-tiny-wl", "ppocr:v6-medium-wl"),
    ("ppocr:v6-tiny", "ppocr:v6-tiny-wl"),
    ("ppocr:v6-small", "ppocr:v6-small-wl"),
    ("ppocr:v6-tiny-wl", "ppocr:v5-en-mobile-wl"),
    ("onnxtr:crnn_mobilenet_v3_small-wl", "ppocr:v6-tiny-wl"),
    ("onnxtr:parseq-wl", "ppocr:v6-small-wl"),
    ("tesseract:eng-nobin", "ppocr:v6-tiny-wl"),
    ("tesseract:eng-nobin", "ppocr:v6-small-wl"),
    (APP_DEFAULT, "ppocr:v6-tiny-wl"),
    (APP_DEFAULT, "ppocr:v6-small-wl"),
    ("qwen-vl:qwen3.5-0.8b-wl", "ppocr:v6-small-wl"),
    ("qwen-vl:qwen3-vl-2b-wl", "ppocr:v6-medium-wl"),
)
CALIBRATED = (
    "ppocr:v6-medium-wl",
    "ppocr:v6-small-wl",
    "ppocr:v6-tiny-wl",
    "onnxtr:parseq-wl",
    "tesseract:eng-nobin",
    APP_DEFAULT,
)
THRESHOLDS = (0.5, 0.7, 0.8, 0.9, 0.95)
LATENCY_KEYS = (
    APP_DEFAULT,
    "tesseract:eng-nobin",
    "windows-ocr:tile-digits",
    "ppocr:v6-tiny-wl",
    "onnxtr:crnn_mobilenet_v3_small-wl",
    "ppocr:v6-small-wl",
    "ppocr:v5-en-mobile-wl",
    "ppocr:v6-medium-wl",
    "onnxtr:vitstr_small-wl",
    "onnxtr:parseq-wl",
)
# crops per second: 10 boxes read 5 times a second, 20 boxes 10 times
LOADS = ((10, 5), (20, 10))
GALLERY = (("ppocr:v6-small-wl", 16), ("ppocr:v6-tiny-wl", 16))


def pct(value: float | None) -> str:
    return "–" if value is None else f"{value * 100:.1f}"


def ci(k: int, n: int) -> str:
    if not n:
        return "–"
    low, high = wilson_interval(k, n)
    return f"{pct(k / n)} ({pct(low)}–{pct(high)})"


def p_value(p: float) -> str:
    if p >= 0.001:
        return f"{p:.3f}"
    if p < 1e-300:  # below what a float holds
        return "<1e-300"
    mantissa, exponent = f"{p:.1e}".split("e")
    return f"{mantissa}e{int(exponent)}"


def table(header: list[str], rows: list[list[str]], align: str = "") -> list[str]:
    align = align or "l" + "r" * (len(header) - 1)
    marks = ["---" if a == "l" else "---:" for a in align]
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(marks) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


class Data:
    def __init__(self):
        accuracy = read_results(HERE / "results.json.gz")
        vlm = read_results(REPO / "ocr_eval" / "baselines" / "vlm" / "crops.json.gz")
        self.vlm_keys = {r["key"] for r in vlm["runs"]}
        self.runs = {
            (r["dataset"], r["key"]): r
            for r in accuracy["runs"] + vlm["runs"]
            if r["status"] == "ok"
        }
        self.datasets = list(accuracy["datasets"])
        self.order = [r["key"] for r in accuracy["runs"]]
        self.environment = accuracy["environment"]
        self.samples = {
            name: {s.id: s for s in load_dataset(name).samples}
            for name in self.datasets
        }
        self.manifest_dirs = {name: load_dataset(name).path for name in self.datasets}
        latency_path = HERE / "latency.json.gz"
        self.latency = read_results(latency_path) if latency_path.exists() else None

    def predictions(self, dataset: str, key: str) -> dict:
        run = self.runs.get((dataset, key))
        return {p["id"]: p for p in run["predictions"]} if run else {}

    def label(self, key: str) -> str:
        return f"`{key}`" + (" (VLM, reference)" if key in self.vlm_keys else "")


def leaderboards(data: Data) -> list[str]:
    out = []
    for dataset in data.datasets:
        runs = [r for (d, _), r in data.runs.items() if d == dataset]
        runs.sort(key=lambda r: -r["scores"]["raw"]["exact"]["value"])
        n = len(data.samples[dataset])
        rows = []
        for run in runs:
            raw, post = run["scores"]["raw"], run["scores"]["postfilter"]
            rows.append(
                [
                    data.label(run["key"]),
                    ci(raw["exact"]["k"], raw["exact"]["n"]),
                    pct(raw["cer"]["value"]),
                    pct(raw["empty_rate"]["value"]),
                    pct(post["exact"]["value"]),
                ]
            )
        out += [f"#### {dataset} (n={n})", ""]
        out += table(
            ["Engine:variant", "Exact % (95% CI)", "CER %", "Empty %", "Post-filter %"],
            rows,
        )
        out.append("")
    return out


def _pooled(data: Data, key: str, flag: str = "exact", split: str | None = None):
    k = n = 0
    for dataset in REAL:
        predictions = data.predictions(dataset, key)
        if not predictions:
            return None
        for item_id, p in predictions.items():
            if split and data.samples[dataset][item_id].split != split:
                continue
            n += 1
            k += bool(p[flag])
    return k, n


def _cer(data: Data, keys_datasets) -> float:
    edits = chars = 0
    for dataset, key in keys_datasets:
        run = data.runs[(dataset, key)]
        edits += run["scores"]["raw"]["cer"]["edits"]
        chars += run["scores"]["raw"]["cer"]["chars"]
    return edits / chars


def pooled(data: Data) -> list[str]:
    rows = []
    for key in dict.fromkeys(data.order):
        both = _pooled(data, key)
        if both is None:
            continue
        post = _pooled(data, key, "pf_exact")
        cells = [data.label(key), ci(*both), pct(post[0] / post[1])]
        cells.append(pct(_cer(data, [(d, key) for d in REAL])))
        for dataset in data.datasets:
            run = data.runs.get((dataset, key))
            cells.append(pct(run["scores"]["raw"]["exact"]["value"]) if run else "–")
        rows.append((both[0] / both[1], cells))
    rows.sort(key=lambda r: -r[0])
    n = sum(len(data.samples[d]) for d in REAL)
    header = [
        "Engine:variant",
        f"Both real datasets, exact % (n={n})",
        "Post-filter %",
        "CER %",
    ] + [f"{SHORT[d]} %" for d in data.datasets]
    return table(header, [cells for _, cells in rows])


def _breakdown(data: Data, attribute: str) -> list[str]:
    out = []
    for dataset in REAL:
        groups = {}
        for key in KEY_ENGINES:
            run = data.runs.get((dataset, key))
            for name, summary in run["scores"]["raw"][f"by_{attribute}"].items():
                groups[name] = summary["n"]
        names = [g for g in sorted(groups, key=lambda g: -groups[g]) if groups[g] >= 20]
        rows = []
        for key in KEY_ENGINES:
            by = data.runs[(dataset, key)]["scores"]["raw"][f"by_{attribute}"]
            rows.append(
                [data.label(key)]
                + [pct(by[g]["exact"]["value"]) if g in by else "–" for g in names]
            )
        out += [f"{SHORT[dataset]}:", ""]
        out += table(["Engine:variant"] + [f"{g} (n={groups[g]})" for g in names], rows)
        out.append("")
    return out


def field_types(data: Data) -> list[str]:
    return _breakdown(data, "field_type")


def display_techs(data: Data) -> list[str]:
    return _breakdown(data, "display_tech")


def test_split(data: Data) -> list[str]:
    rows = []
    for key in KEY_ENGINES:
        test = _pooled(data, key, split="test")
        dev = _pooled(data, key, split="dev")
        rows.append([data.label(key), ci(*test), ci(*dev)])
    n_test = _pooled(data, KEY_ENGINES[0], split="test")[1]
    n_dev = _pooled(data, KEY_ENGINES[0], split="dev")[1]
    return table(
        ["Engine:variant", f"test split (n={n_test})", f"dev split (n={n_dev})"], rows
    )


def mcnemar(data: Data) -> list[str]:
    rows = []
    for a, b in PAIRS:
        for scope in REAL + ("both",):
            datasets = REAL if scope == "both" else (scope,)
            a_only = b_only = a_right = b_right = n = 0
            missing = False
            for dataset in datasets:
                pa, pb = data.predictions(dataset, a), data.predictions(dataset, b)
                if not pa or not pb:
                    missing = True
                    break
                for item_id in pa:
                    ea, eb = bool(pa[item_id]["exact"]), bool(pb[item_id]["exact"])
                    n += 1
                    a_right += ea
                    b_right += eb
                    a_only += ea and not eb
                    b_only += eb and not ea
            if missing:
                continue
            rows.append(
                [
                    f"`{a}` → `{b}`",
                    SHORT.get(scope, "both real"),
                    str(n),
                    pct(a_right / n),
                    pct(b_right / n),
                    f"{(b_right - a_right) / n * 100:+.1f}",
                    str(b_only),
                    str(a_only),
                    p_value(mcnemar_exact_p(a_only, b_only)),
                ]
            )
    return table(
        ["A → B", "Crops", "n", "A %", "B %", "Δ points", "B only", "A only", "p"],
        rows,
        "llrrrrrrr",
    )


def calibration(data: Data) -> list[str]:
    """On both real datasets: a reading is published when it passes
    ScoreSight's post-filter and its confidence is at least the threshold."""
    rows = []
    for key in CALIBRATED:
        items = []
        for dataset in REAL:
            for p in data.predictions(dataset, key).values():
                text = p.get("pf_text", p["text"])
                items.append((p["conf"], bool(text), bool(p["pf_exact"])))
        n = len(items)
        cells = [data.label(key)]
        for threshold in (0.0,) + THRESHOLDS:
            published = [
                (conf, right)
                for conf, has_text, right in items
                if has_text and conf is not None and conf >= threshold
            ]
            wrong = sum(not right for _, right in published)
            cells.append(
                f"{pct(len(published) / n)} / {pct(wrong / n)}"
                if published
                else "0 / 0"
            )
        # expected calibration error over the readings with a confidence
        scored = [(conf, right) for conf, has_text, right in items if conf is not None]
        ece = 0.0
        for b in range(10):
            low, high = b / 10, (b + 1) / 10
            bin_items = [
                (c, r) for c, r in scored if low <= c < high or (b == 9 and c == 1.0)
            ]
            if bin_items:
                mean_conf = sum(c for c, _ in bin_items) / len(bin_items)
                accuracy = sum(r for _, r in bin_items) / len(bin_items)
                ece += len(bin_items) / len(scored) * abs(mean_conf - accuracy)
        cells.append(pct(ece))
        rows.append(cells)
    header = (
        ["Engine:variant", "any conf."]
        + [f"conf ≥ {t}" for t in THRESHOLDS]
        + ["ECE %"]
    )
    return table(header, rows)


def gray(data: Data) -> list[str]:
    """The colour crop against the crop in gray (gray.json.gz), crop by crop."""
    path = HERE / "gray.json.gz"
    if not path.exists():
        return ["(no gray.json.gz)"]
    gray_runs = {
        (r["dataset"], r["key"]): {p["id"]: p for p in r["predictions"]}
        for r in read_results(path)["runs"]
        if r["status"] == "ok"
    }
    rows = []
    for model in ("v6-tiny", "v6-small", "v6-medium"):
        colour_key = f"ppocr:{model}-wl"
        gray_key = f"ppocr:{model}-gray-wl"
        for scope in REAL + ("both",):
            datasets = REAL if scope == "both" else (scope,)
            n = colour_right = gray_right = colour_only = gray_only = 0
            for dataset in datasets:
                colour = data.predictions(dataset, colour_key)
                grays = gray_runs[(dataset, gray_key)]
                for item_id, p in colour.items():
                    c, g = bool(p["exact"]), bool(grays[item_id]["exact"])
                    n += 1
                    colour_right += c
                    gray_right += g
                    colour_only += c and not g
                    gray_only += g and not c
            rows.append(
                [
                    f"`{colour_key}`",
                    SHORT.get(scope, "both real"),
                    pct(colour_right / n),
                    pct(gray_right / n),
                    f"{(gray_right - colour_right) / n * 100:+.1f}",
                    str(colour_only),
                    str(gray_only),
                    p_value(mcnemar_exact_p(colour_only, gray_only)),
                ]
            )
    return table(
        [
            "Model",
            "Crops",
            "Colour %",
            "Gray %",
            "Δ points",
            "Colour only",
            "Gray only",
            "p",
        ],
        rows,
        "llrrrrrr",
    )


def _latency_runs(data: Data):
    out = {}
    for run in data.latency["runs"]:
        out[(run["key"], run["threads"])] = run
    return out


def latency(data: Data) -> list[str]:
    if not data.latency:
        return ["(no latency.json.gz)"]
    runs = _latency_runs(data)
    rows = []
    for key in LATENCY_KEYS:
        onnx = key.split(":")[0] in ("ppocr", "onnxtr")
        for threads in ("1", "all") if onnx else ("1",):
            run = runs.get((key, threads))
            if not run:
                continue
            lat = run["latency"]
            single, batch = lat["single"], lat["batch"]
            batched = lat["batch_size"] > 1
            rows.append(
                [
                    f"`{key}`",
                    threads if onnx else "1 (own)",
                    f"{single['p50_ms']:.1f} / {single['p95_ms']:.1f}",
                    f"{batch['p50_ms']:.1f} / {batch['p95_ms']:.1f}"
                    if batched
                    else "–",
                    f"{lat['cpu_ms']['single']:.1f}",
                    f"{lat['cpu_ms']['batch']:.1f}" if batched else "–",
                    f"{run['load_seconds']:.2f}",
                    f"{run['machine_load']['background_mean_pct']:.0f}",
                ]
            )
    return table(
        [
            "Engine:variant",
            "Threads",
            "One crop per call: p50 / p95 ms",
            "Batches of 16: p50 / p95 ms per crop",
            "CPU ms per crop, one at a time",
            "CPU ms per crop, batched",
            "Load s",
            "Other load %",
        ],
        rows,
        "llrrrrrr",
    )


def threads(data: Data) -> list[str]:
    """The PP-OCRv6 models with more onnxruntime threads: how long a frame of
    boxes takes and what it costs in CPU time, at 20 boxes read 10 times a
    second in batches (the OCR thread must be busy less than 1 s per second)."""
    if not data.latency:
        return ["(no latency.json.gz)"]
    runs = _latency_runs(data)
    order = (
        "1",
        "2",
        "2, no spinning",
        "4",
        "4, no spinning",
        "all",
        "all, no spinning",
    )
    rows = []
    for key in ("ppocr:v6-tiny-wl", "ppocr:v6-small-wl", "ppocr:v6-medium-wl"):
        for setting in order:
            run = runs.get((key, setting))
            if not run:
                continue
            lat = run["latency"]
            crops = 200
            rows.append(
                [
                    f"`{key}`",
                    setting,
                    f"{lat['single']['p50_ms']:.1f}",
                    f"{lat['batch']['p50_ms']:.1f}",
                    f"{lat['cpu_ms']['batch']:.1f}",
                    f"{crops * lat['batch']['mean_ms'] / 1000:.2f} s",
                    f"{crops * lat['cpu_ms']['batch'] / 1000:.1f}",
                ]
            )
    return table(
        [
            "Engine:variant",
            "Threads",
            "One crop: p50 ms",
            "Batched: p50 ms per crop",
            "CPU ms per crop, batched",
            "200 crops/s: OCR busy per second",
            "200 crops/s: cores of CPU time",
        ],
        rows,
        "llrrrrr",
    )


def budget(data: Data) -> list[str]:
    """CPU time at the realistic loads, one thread per engine (the cheapest in
    CPU time), reading a frame's boxes one call per box and in one batch."""
    if not data.latency:
        return ["(no latency.json.gz)"]
    runs = _latency_runs(data)
    rows = []
    for key in LATENCY_KEYS:
        run = runs.get((key, "1"))
        if not run:
            continue
        cpu = run["latency"]["cpu_ms"]
        batched = run["latency"]["batch_size"] > 1
        cells = [f"`{key}`"]
        for boxes, rate in LOADS:
            crops = boxes * rate
            single = crops * cpu["single"] / 1000
            cells.append(f"{single * 100:.0f}%")
            cells.append(f"{crops * cpu['batch'] / 10:.0f}%" if batched else "–")
        rows.append(cells)
    header = ["Engine:variant"]
    for boxes, rate in LOADS:
        header += [
            f"{boxes} boxes × {rate}/s ({boxes * rate} crops/s), one call per box",
            "same, one batch per frame",
        ]
    return table(header, rows)


def startup(data: Data) -> list[str]:
    path = HERE / "startup.json"
    if not path.exists():
        return ["(no startup.json)"]
    report = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for key, metrics in report["models"].items():
        rows.append(
            [f"`ppocr:{key}`"]
            + [
                f"{metrics[m]['median']:.0f} ({metrics[m]['min']:.0f})"
                for m in ("import_ms", "load_ms", "first_ms", "second_ms")
            ]
        )
    return table(
        [
            "Model",
            "import onnxruntime, ms",
            "load the model, ms",
            "first inference, ms",
            "second inference, ms",
        ],
        rows,
    )


def _category(truth: str, text: str, field_type: str) -> str:
    if not text:
        return "nothing read"
    stripped = truth.replace(":", "").replace(".", "")
    if stripped != truth and text.replace(":", "").replace(".", "") == stripped:
        return "clock separator missing or wrong"
    if len(text) == len(truth):
        wrong = sum(a != b for a, b in zip(text, truth))
        return "one character wrong" if wrong == 1 else "several characters wrong"
    if len(text) < len(truth):
        return "character(s) missing"
    return "extra character(s)"


def galleries(data: Data) -> list[str]:
    out = []
    for key, limit in GALLERY:
        for dataset in REAL:
            samples = data.samples[dataset]
            wrong = [
                p for p in data.predictions(dataset, key).values() if not p["exact"]
            ]
            counts = {}
            for p in wrong:
                category = _category(p["truth"], p["text"], samples[p["id"]].field_type)
                counts[category] = counts.get(category, 0) + 1
            out += [
                f"#### `{key}` on {dataset}: {len(wrong)} errors",
                "",
                ", ".join(
                    f"{name} {count}"
                    for name, count in sorted(counts.items(), key=lambda c: -c[1])
                )
                + ".",
                "",
            ]
            # a deterministic spread: every k-th error in id order
            wrong.sort(key=lambda p: p["id"])
            step = max(1, len(wrong) // limit)
            shown = wrong[::step][:limit]
            rows = []
            for p in shown:
                sample = samples[p["id"]]
                image = (data.manifest_dirs[dataset] / sample.image).relative_to(REPO)
                link = Path("../..") / image.relative_to("ocr_eval")
                conf = "–" if p["conf"] is None else f"{p['conf']:.2f}"
                rows.append(
                    [
                        f'<img src="{link.as_posix()}" height="36" alt="{p["id"]}">',
                        f"`{p['truth']}`",
                        f"`{p['text']}`" if p["text"] else "∅",
                        conf,
                        sample.display_tech,
                    ]
                )
            out += table(["Crop", "Truth", "Read", "Conf.", "Display"], rows, "lllrl")
            out.append("")
    return out


SECTIONS = {
    "leaderboards": leaderboards,
    "pooled": pooled,
    "field-types": field_types,
    "display-techs": display_techs,
    "test-split": test_split,
    "mcnemar": mcnemar,
    "calibration": calibration,
    "gray": gray,
    "latency": latency,
    "threads": threads,
    "budget": budget,
    "startup": startup,
    "galleries": galleries,
}


def fill(path: Path, data: Data, check: bool = False) -> int:
    """Rewrite every table of a markdown file that sits between
    <!-- tables:NAME --> and <!-- /tables:NAME --> with the section's output.
    With check, change nothing and return 1 if a table is out of date."""
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(<!-- tables:([a-z-]+) -->\n)(?:.*?\n)?(<!-- /tables:\2 -->)", re.DOTALL
    )
    filled = []

    def replace(match):
        filled.append(match.group(2))
        body = "\n".join(SECTIONS[match.group(2)](data))
        return f"{match.group(1)}{body}\n{match.group(3)}"

    new = pattern.sub(replace, text)
    if check:
        if new != text:
            print(f"{path.name}: tables out of date (run --fill)")
            return 1
        print(f"{path.name}: tables up to date ({len(filled)})")
        return 0
    path.write_bytes(new.encode("utf-8"))
    print(f"{path.name}: filled {', '.join(filled)}")
    return 0


def main(argv: list[str]) -> int:
    utf8_output()
    data = Data()
    if argv[:1] in (["--fill"], ["--check"]):
        return fill(Path(argv[1]), data, check=argv[0] == "--check")
    for name in argv or list(SECTIONS):
        print(f"<!-- {name} -->")
        print("\n".join(SECTIONS[name](data)))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
