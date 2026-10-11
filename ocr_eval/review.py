"""An HTML contact sheet for checking a dataset's labels by eye.

    python -m ocr_eval review DATASET [--out FILE] [--results RESULTS.json]

The page shows every crop with its label (text, field type, display technology,
role), grouped by source photo with a link to it and its license, and, when the
dataset has a frames.jsonl with frame images, the photo with all its boxes.
With --results, each crop also shows what the engines of a results file read.
The page is one self-contained file (the images are embedded).

The reviewer marks each crop OK, fixes its text, or drops it; decisions are
kept in the browser (localStorage) and exported as a JSON file:

    {"schema": "scoresight-ocr-eval-review/1", "dataset": NAME,
     "manifest_sha256": ..., "reviewer": ..., "exported": ISO time,
     "decisions": {ID: {"verdict": "ok" | "fix" | "drop", "text": ..., "reason": ...}}}

A dataset's builder applies it (e.g. commons_scoreboards --apply-review).
"""

import base64
import html
import json
from collections import defaultdict
from pathlib import Path

from ocr_eval.dataset import Dataset, MANIFEST

REVIEW_SCHEMA = "scoresight-ocr-eval-review/1"
FRAMES_FILE = "frames.jsonl"
DROP_REASONS = (
    "illegible",
    "ambiguous",
    "cut off",
    "box covers another field",
    "not a scoreboard value",
    "other",
)


def _data_uri(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(
        suffix, "application/octet-stream"
    )
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _source_key(sample) -> str:
    return str(
        sample.extra.get("source_image")
        or sample.extra.get("frame")
        or sample.source_url
        or sample.id
    )


def read_frames(dataset: Dataset) -> dict:
    """source key -> frame row (frames.jsonl), for datasets that have one."""
    path = dataset.path / FRAMES_FILE
    if not path.is_file():
        return {}
    frames = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            frames[str(row.get("source_image") or row.get("id"))] = row
    return frames


def predictions_by_id(results: dict, dataset_name: str, runs=None) -> tuple:
    """(run keys, {sample id: {run key: prediction}}) of the ok runs on the
    dataset in a results file (only the runs in runs, if given)."""
    keys = []
    by_id = defaultdict(dict)
    for run in results.get("runs", []):
        if run.get("dataset") != dataset_name or run.get("status") != "ok":
            continue
        if runs and run["key"] not in runs:
            continue
        keys.append(run["key"])
        for prediction in run.get("predictions") or []:
            by_id[prediction["id"]][run["key"]] = prediction
    return keys, by_id


def _esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _frame_svg(frame: dict, image_uri: str) -> str:
    """The frame image with every labelled box and its text (frames.jsonl
    boxes are in the labelling rendition's pixels, "size"; the committed
    frame may be smaller, "frame_size")."""
    size = frame.get("frame_size") or frame.get("size")
    if not size:
        return ""
    width, height = size
    scale = width / frame["size"][0] if frame.get("size") else 1.0
    font = max(6.0, width / 90)
    boxes = []
    for field in frame.get("fields", []):
        x, y, w, h = (v * scale for v in field["box"])
        label = f"{field.get('role', '')}: {field['text']}"
        boxes.append(
            f'<g data-id="{_esc(field.get("id"))}"><rect x="{x:.1f}" y="{y:.1f}" '
            f'width="{w:.1f}" height="{h:.1f}"/><text x="{x:.1f}" '
            f'y="{max(font, y - font / 4):.1f}">{_esc(label)}</text></g>'
        )
    return (
        f'<svg class="frame" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'style="font-size:{font:.1f}px">'
        f'<image href="{image_uri}" x="0" y="0" width="{width}" height="{height}"/>'
        + "".join(boxes)
        + "</svg>"
    )


def render_review(
    dataset: Dataset,
    results: dict | None = None,
    runs: list[str] | None = None,
    include_frames: bool = True,
) -> str:
    frames = read_frames(dataset) if include_frames else {}
    run_keys, predictions = (
        predictions_by_id(results, dataset.name, runs) if results else ([], {})
    )
    groups = defaultdict(list)
    for sample in dataset.samples:
        groups[_source_key(sample)].append(sample)
    n_sources = len(groups)
    if n_sources == len(dataset.samples) and not frames:
        # one crop per source (e.g. synthetic data): one section
        groups = {"": list(dataset.samples)}
    engines = {key.split(":", 1)[0] for key in run_keys}

    def run_label(key: str) -> str:
        return key if len(engines) > 1 else key.split(":", 1)[-1]

    sections = []
    for key in sorted(groups):
        items = groups[key]
        first = items[0]
        frame = frames.get(key)
        if key:
            title = (frame or {}).get("title") or first.extra.get("title") or key
            source = first.source_url
            header = (
                f'<a href="{_esc(source)}" target="_blank" rel="noopener">'
                f"{_esc(title)}</a>"
                if source
                else _esc(title)
            )
            meta = " · ".join(
                _esc(v)
                for v in (first.author, first.license, f"split {first.split}")
                if v
            )
        else:
            header = "All crops (one per source)"
            licenses = sorted({s.license for s in items})
            meta = _esc(", ".join(licenses))
        frame_html = ""
        if frame and frame.get("frame"):
            frame_path = dataset.path / frame["frame"]
            if frame_path.is_file():
                frame_html = (
                    "<details class=framebox><summary>Photo with all boxes</summary>"
                    + _frame_svg(frame, _data_uri(frame_path))
                    + "</details>"
                )
        tiles = []
        for sample in items:
            role = sample.extra.get("role")
            preds = predictions.get(sample.id, {})
            hits = sum(1 for p in preds.values() if p.get("exact"))
            pred_html = ""
            if run_keys:
                rows = []
                for run_key in run_keys:
                    p = preds.get(run_key)
                    if p is None:
                        continue
                    mark = "ok" if p.get("exact") else "bad"
                    rows.append(
                        f'<li class="{mark}"><span>{_esc(run_label(run_key))}</span>'
                        f"<code>{_esc(p.get('text')) or '∅'}</code></li>"
                    )
                pred_html = f'<ul class="preds">{"".join(rows)}</ul>'
            image_path = dataset.image_path(sample)
            image = _data_uri(image_path) if image_path.is_file() else ""
            tiles.append(
                f'<article class="tile" data-id="{_esc(sample.id)}" '
                f'data-ft="{_esc(sample.field_type)}" data-tech="{_esc(sample.display_tech)}" '
                f'data-ls="{_esc(sample.label_source)}" data-text="{_esc(sample.text)}" '
                f'data-hits="{hits}" data-runs="{len(preds)}">'
                f'<button class="crop" title="Enlarge"><img src="{image}" alt="crop {_esc(sample.id)}"></button>'
                f'<div class="truth">{_esc(sample.text)}</div>'
                f'<div class="meta">{_esc(sample.field_type)} · {_esc(sample.display_tech)}'
                + (f" · {_esc(role)}" if role else "")
                + "</div>"
                + pred_html
                + '<div class="actions"><button data-v="ok">OK</button>'
                '<button data-v="fix">Fix</button><button data-v="drop">Drop</button></div>'
                '<div class="edit" hidden><input class="fixtext" aria-label="Correct text" '
                'placeholder="correct text"><select class="reason" aria-label="Drop reason">'
                + "".join(f"<option>{_esc(r)}</option>" for r in DROP_REASONS)
                + "</select></div>"
                f'<div class="id">{_esc(sample.id)}</div></article>'
            )
        sections.append(
            f'<section class="src"><h2>{header}</h2><p class="srcmeta">{meta} · '
            f"{len(items)} crops</p>{frame_html}"
            f'<div class="grid">{"".join(tiles)}</div></section>'
        )

    field_types = sorted({s.field_type for s in dataset.samples})
    techs = sorted({s.display_tech for s in dataset.samples})
    label_sources = sorted({s.label_source for s in dataset.samples})
    config = {
        "dataset": dataset.name,
        "manifest_sha256": dataset.manifest_sha256,
        "schema": REVIEW_SCHEMA,
        "runs": run_keys,
    }
    options = lambda values: "".join(  # noqa: E731
        f'<option value="{_esc(v)}">{_esc(v)}</option>' for v in values
    )
    run_filter = (
        '<label><input type="checkbox" id="f-miss"> only crops no engine read</label>'
        if run_keys
        else ""
    )
    return (
        _PAGE.replace("@@TITLE@@", _esc(f"Review: {dataset.name}"))
        .replace(
            "@@SUMMARY@@",
            _esc(
                f"{len(dataset.samples)} crops from {n_sources} sources · "
                f"{MANIFEST} {dataset.manifest_sha256[:12]}"
                + (f" · predictions of {len(run_keys)} runs" if run_keys else "")
            ),
        )
        .replace("@@FT@@", options(field_types))
        .replace("@@TECH@@", options(techs))
        .replace("@@LS@@", options(label_sources))
        .replace("@@RUNFILTER@@", run_filter)
        .replace("@@SECTIONS@@", "".join(sections))
        .replace("@@CONFIG@@", json.dumps(config).replace("</", "<\\/"))
    )


_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@TITLE@@</title>
<style>
:root { --bg: #f6f6f4; --card: #fff; --ink: #1d1d1b; --muted: #6b6b66; --line: #deded8;
  --ok: #1f7a3d; --okbg: #e3f3e8; --bad: #b3261e; --badbg: #fbe7e5; --fix: #8a5a00; --fixbg: #fdf1d8;
  --accent: #2456b3; }
@media (prefers-color-scheme: dark) { :root { --bg: #161615; --card: #22221f; --ink: #ecece6;
  --muted: #a3a39b; --line: #3a3a35; --ok: #7bd69a; --okbg: #1d3325; --bad: #ff8a80; --badbg: #3d1f1c;
  --fix: #f2c46d; --fixbg: #3a2f17; --accent: #8fb3ff; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; }
header { position: sticky; top: 0; z-index: 2; background: var(--bg); border-bottom: 1px solid var(--line);
  padding: 10px 16px; }
h1 { font-size: 18px; margin: 0 0 2px; }
.summary, .srcmeta, .meta, .id { color: var(--muted); }
.summary { margin: 0 0 8px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; }
.toolbar input[type=search], .toolbar select, .toolbar input[type=text] { font: inherit; padding: 4px 6px;
  border: 1px solid var(--line); border-radius: 6px; background: var(--card); color: var(--ink); }
button { font: inherit; cursor: pointer; border: 1px solid var(--line); border-radius: 6px;
  background: var(--card); color: var(--ink); padding: 3px 9px; }
button.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.counts { font-variant-numeric: tabular-nums; }
main { padding: 8px 16px 40px; }
section.src { margin: 16px 0 22px; }
h2 { font-size: 15px; margin: 0; }
h2 a { color: var(--accent); }
.srcmeta { margin: 2px 0 8px; font-size: 12px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 10px; }
.tile { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 8px;
  display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.tile.v-ok { border-color: var(--ok); background: var(--okbg); }
.tile.v-fix { border-color: var(--fix); background: var(--fixbg); }
.tile.v-drop { border-color: var(--bad); background: var(--badbg); opacity: .75; }
.crop { padding: 0; border: 0; background: #000; border-radius: 4px; height: 84px; display: flex;
  align-items: center; justify-content: center; overflow: hidden; }
.crop img { max-width: 100%; max-height: 84px; }
.truth { font: 600 20px/1.2 ui-monospace, "Cascadia Mono", Consolas, monospace; word-break: break-all; }
.meta { font-size: 12px; }
.id { font-size: 11px; word-break: break-all; }
.preds { list-style: none; margin: 0; padding: 0; font-size: 12px; }
.preds li { display: flex; justify-content: space-between; gap: 6px; }
.preds li span { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.preds li.ok code { color: var(--ok); }
.preds li.bad code { color: var(--bad); }
.actions { display: flex; gap: 4px; }
.actions button { flex: 1; padding: 2px 4px; }
.tile.v-ok [data-v=ok], .tile.v-fix [data-v=fix], .tile.v-drop [data-v=drop] { font-weight: 700;
  border-color: currentColor; }
.edit input, .edit select { width: 100%; font: inherit; margin-top: 2px; padding: 3px 5px;
  border: 1px solid var(--line); border-radius: 5px; background: var(--card); color: var(--ink); }
.framebox summary { cursor: pointer; color: var(--accent); margin-bottom: 6px; }
svg.frame { width: 100%; max-height: 80vh; background: #000; }
svg.frame rect { fill: none; stroke: #ff2bd6; stroke-width: 2; vector-effect: non-scaling-stroke; }
svg.frame text { fill: #ff2bd6; font-weight: 600; font-family: system-ui, sans-serif; paint-order: stroke;
  stroke: #000; stroke-width: 0.25em; }
dialog { border: 0; border-radius: 10px; padding: 12px; background: var(--card); color: var(--ink);
  max-width: 95vw; }
dialog img { display: block; image-rendering: pixelated; max-width: 90vw; max-height: 75vh;
  min-height: 160px; object-fit: contain; background: #000; }
dialog p { margin: 8px 0 0; font: 600 22px ui-monospace, Consolas, monospace; }
.hidden { display: none !important; }
@media (max-width: 600px) { .grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); } }
</style>
</head>
<body>
<header>
<h1>@@TITLE@@</h1>
<p class="summary">@@SUMMARY@@</p>
<div class="toolbar">
<input type="search" id="f-q" placeholder="Filter by text or id" aria-label="Filter by text or id">
<select id="f-ft" aria-label="Field type"><option value="">all field types</option>@@FT@@</select>
<select id="f-tech" aria-label="Display technology"><option value="">all displays</option>@@TECH@@</select>
<select id="f-ls" aria-label="Label source"><option value="">all label sources</option>@@LS@@</select>
<select id="f-v" aria-label="Decision"><option value="">all decisions</option>
<option value="none">not reviewed</option><option value="ok">OK</option><option value="fix">fixed</option>
<option value="drop">dropped</option></select>
@@RUNFILTER@@
<span class="counts" id="counts"></span>
<button id="all-ok" title="Mark every shown crop that has no decision OK">Mark shown as OK</button>
<input type="text" id="reviewer" placeholder="Your name" aria-label="Reviewer name">
<button class="primary" id="export">Export decisions</button>
<label><button id="import-btn" type="button">Import…</button>
<input type="file" id="import" accept="application/json" hidden></label>
</div>
</header>
<main>@@SECTIONS@@</main>
<dialog id="zoom"><img alt=""><p></p><form method="dialog"><button>Close</button></form></dialog>
<script type="application/json" id="config">@@CONFIG@@</script>
<script>
(() => {
  const config = JSON.parse(document.getElementById("config").textContent);
  const storeKey = "ocr_eval_review:" + config.dataset + ":" + config.manifest_sha256;
  let state = { reviewer: "", decisions: {} };
  try { state = Object.assign(state, JSON.parse(localStorage.getItem(storeKey) || "{}")); } catch (e) {}
  const save = () => { try { localStorage.setItem(storeKey, JSON.stringify(state)); } catch (e) {} };
  const tiles = [...document.querySelectorAll(".tile")];
  const byId = new Map(tiles.map(t => [t.dataset.id, t]));

  function paint(tile) {
    const d = state.decisions[tile.dataset.id];
    tile.classList.remove("v-ok", "v-fix", "v-drop");
    const edit = tile.querySelector(".edit");
    const input = tile.querySelector(".fixtext");
    const reason = tile.querySelector(".reason");
    edit.hidden = true; input.hidden = true; reason.hidden = true;
    if (!d) return;
    tile.classList.add("v-" + d.verdict);
    if (d.verdict === "fix") { edit.hidden = false; input.hidden = false; input.value = d.text || ""; }
    if (d.verdict === "drop") { edit.hidden = false; reason.hidden = false; reason.value = d.reason || reason.options[0].value; }
  }
  function counts() {
    const c = { ok: 0, fix: 0, drop: 0 };
    for (const d of Object.values(state.decisions)) c[d.verdict] = (c[d.verdict] || 0) + 1;
    const shown = tiles.filter(t => !t.classList.contains("hidden")).length;
    document.getElementById("counts").textContent =
      `${shown} shown · OK ${c.ok} · fixed ${c.fix} · dropped ${c.drop} · not reviewed ${tiles.length - c.ok - c.fix - c.drop}`;
  }
  function decide(tile, verdict) {
    const id = tile.dataset.id;
    const current = state.decisions[id];
    if (current && current.verdict === verdict) { delete state.decisions[id]; }
    else if (verdict === "fix") { state.decisions[id] = { verdict, text: (current && current.text) || tile.dataset.text }; }
    else if (verdict === "drop") { state.decisions[id] = { verdict, reason: tile.querySelector(".reason").value }; }
    else { state.decisions[id] = { verdict }; }
    paint(tile); save(); counts(); filter();
    if (verdict === "fix" && state.decisions[id]) tile.querySelector(".fixtext").focus();
  }
  document.querySelector("main").addEventListener("click", e => {
    const button = e.target.closest("button");
    if (!button) return;
    const tile = button.closest(".tile");
    if (button.dataset.v && tile) decide(tile, button.dataset.v);
    else if (button.classList.contains("crop")) {
      const dialog = document.getElementById("zoom");
      dialog.querySelector("img").src = button.querySelector("img").src;
      dialog.querySelector("p").textContent = tile.dataset.text + "   (" + tile.dataset.id + ")";
      dialog.showModal();
    }
  });
  document.querySelector("main").addEventListener("input", e => {
    const tile = e.target.closest(".tile");
    if (!tile) return;
    const d = state.decisions[tile.dataset.id];
    if (!d) return;
    if (e.target.classList.contains("fixtext")) d.text = e.target.value.trim();
    if (e.target.classList.contains("reason")) d.reason = e.target.value;
    save();
  });

  const q = document.getElementById("f-q"), ft = document.getElementById("f-ft"),
    tech = document.getElementById("f-tech"), ls = document.getElementById("f-ls"),
    v = document.getElementById("f-v"), miss = document.getElementById("f-miss");
  function filter() {
    const text = q.value.trim().toLowerCase();
    for (const t of tiles) {
      const d = state.decisions[t.dataset.id];
      const show = (!text || t.dataset.text.toLowerCase().includes(text) || t.dataset.id.toLowerCase().includes(text))
        && (!ft.value || t.dataset.ft === ft.value) && (!tech.value || t.dataset.tech === tech.value)
        && (!ls.value || t.dataset.ls === ls.value)
        && (!v.value || (v.value === "none" ? !d : d && d.verdict === v.value))
        && (!miss || !miss.checked || (t.dataset.runs !== "0" && t.dataset.hits === "0"));
      t.classList.toggle("hidden", !show);
    }
    for (const s of document.querySelectorAll("section.src"))
      s.classList.toggle("hidden", !s.querySelector(".tile:not(.hidden)"));
    counts();
  }
  for (const el of [q, ft, tech, ls, v, miss]) if (el) el.addEventListener("input", filter);

  document.getElementById("all-ok").addEventListener("click", () => {
    for (const t of tiles) if (!t.classList.contains("hidden") && !state.decisions[t.dataset.id]) {
      state.decisions[t.dataset.id] = { verdict: "ok" }; paint(t);
    }
    save(); filter();
  });
  const reviewer = document.getElementById("reviewer");
  reviewer.value = state.reviewer || "";
  reviewer.addEventListener("input", () => { state.reviewer = reviewer.value.trim(); save(); });
  document.getElementById("export").addEventListener("click", () => {
    if (!state.reviewer) { reviewer.focus(); alert("Enter your name first: it goes into the export."); return; }
    const out = { schema: config.schema, dataset: config.dataset, manifest_sha256: config.manifest_sha256,
      reviewer: state.reviewer, exported: new Date().toISOString(), decisions: state.decisions };
    const blob = new Blob([JSON.stringify(out, null, 1)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `review-${config.dataset}-${state.reviewer.replace(/[^A-Za-z0-9_-]+/g, "_")}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });
  const file = document.getElementById("import");
  document.getElementById("import-btn").addEventListener("click", () => file.click());
  file.addEventListener("change", async () => {
    if (!file.files.length) return;
    try {
      const data = JSON.parse(await file.files[0].text());
      if (data.dataset !== config.dataset) throw new Error("this export is for " + data.dataset);
      for (const [id, d] of Object.entries(data.decisions || {})) if (byId.has(id)) state.decisions[id] = d;
      if (data.reviewer && !state.reviewer) { state.reviewer = data.reviewer; reviewer.value = data.reviewer; }
      save(); tiles.forEach(paint); filter();
    } catch (e) { alert("Can't import: " + e.message); }
    file.value = "";
  });
  tiles.forEach(paint);
  filter();
})();
</script>
</body>
</html>
"""


def write_review(
    dataset: Dataset,
    out: Path,
    results: dict | None = None,
    runs: list[str] | None = None,
    include_frames: bool = True,
) -> Path:
    page = render_review(dataset, results, runs, include_frames)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8", newline="\n")
    return out


def read_decisions(path) -> dict:
    """A review export, checked: {"dataset", "manifest_sha256", "reviewer",
    "decisions": {id: {"verdict", "text"?, "reason"?}}}."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or data.get("schema") != REVIEW_SCHEMA:
        raise ValueError(f"{path} is not a review export ({REVIEW_SCHEMA})")
    if not str(data.get("reviewer") or "").strip():
        raise ValueError(f"{path}: no reviewer name")
    decisions = data.get("decisions")
    if not isinstance(decisions, dict):
        raise ValueError(f"{path}: no decisions")
    for item, decision in decisions.items():
        verdict = (decision or {}).get("verdict")
        if verdict not in ("ok", "fix", "drop"):
            raise ValueError(f"{path}: {item}: unknown verdict {verdict!r}")
        if verdict == "fix":
            text = decision.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"{path}: {item}: a fix needs the correct text")
    return data
