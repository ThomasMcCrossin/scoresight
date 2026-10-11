"""Build ocr_eval/datasets/commons_scoreboards: scoreboard fields on Wikimedia Commons photos.

Source: photos of physical scoreboards (basketball, ice hockey, American and
association football, cricket, shot clocks, Daktronics boards ...) in the
Category:Scoreboards tree and a few related categories of Wikimedia Commons,
whose license allows redistribution (CC BY, CC BY-SA, CC0 or public domain;
re-checked with the Commons API on every build). Each crop keeps its photo's
license: a CC BY-SA photo gives CC BY-SA crops.

Labels: commons_scoreboards_labels.json next to this file. For every photo used,
the fields of its scoreboard(s) that are legible (scores, clock, shot clock,
period, fouls, ...) with a box drawn the way a ScoreSight user would draw it,
the exact text displayed, the field type, the field's role and the display
technology, in the pixel coordinates of the photo's 1280 px wide rendition
("size"). Photos looked at and not used are listed with the reason. The labels
were drawn and transcribed with a model's help (Claude) and are marked
"model-assisted-unverified" until a person checks them with
`python -m ocr_eval review commons_scoreboards` and the result is applied with
--apply-review, which marks the checked fields "human".

    python -m ocr_eval.builders.commons_scoreboards --cache DIR --frames [--offline]
    python -m ocr_eval.builders.commons_scoreboards --cache DIR --discover
    python -m ocr_eval.builders.commons_scoreboards --apply-review REVIEW.json

--discover lists the candidate photos (category members with a usable license)
in DIR/candidates.json and downloads small thumbnails of them to
DIR/triage/ for choosing photos to label. A build downloads the 1280 px
renditions of the labelled photos to DIR/photos/ (about 0.3 MB each) and writes
the crops, manifest.jsonl, frames.jsonl (each photo with its rendition URL and
all of its labelled fields, for whole-frame experiments), LICENSE,
ATTRIBUTION.md and README.md. --frames (used for the committed dataset) also
writes frames/cm<pageid>.jpg, the photos downscaled to FRAME_MAX_SIDE, for
whole-frame experiments. --offline rebuilds from the cache without re-checking
the licenses.

Requests go to the Commons API and upload.wikimedia.org one at a time, at most
one per second, with a descriptive User-Agent, as Wikimedia's API etiquette
asks. Downloads are only parsed (JSON, images), never executed.
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from ocr_eval import DATASETS_DIR
from ocr_eval.builders._common import USER_AGENT, fit_height, write_png, write_text
from ocr_eval.dataset import Sample, assign_split, write_manifest
from ocr_eval.fields import DISPLAY_TECHS, FIELD_TYPES

NAME = "commons_scoreboards"
LABELS_FILE = Path(__file__).with_name(f"{NAME}_labels.json")
API_URL = "https://commons.wikimedia.org/w/api.php"
REFERENCE_WIDTH = 1280  # labels are in the coordinates of this rendition
TRIAGE_WIDTH = 330
MAX_CROP_HEIGHT = 160
FRAME_MAX_SIDE = 576  # keeps the committed dataset under 25 MB
FRAME_JPEG_QUALITY = 70
MIN_REQUEST_INTERVAL = 1.0  # seconds between requests

# category -> sport (None: a mix). Searched with their subcategories (DEPTH).
CATEGORIES = {
    "Category:Basketball scoreboards": "basketball",
    "Category:Ice hockey scoreboards": "ice hockey",
    "Category:American football scoreboards": "american football",
    "Category:Canadian football scoreboards": "canadian football",
    "Category:Association football scoreboards": "association football",
    "Category:Digital scoreboards in cricket": "cricket",
    "Category:Electro-mechanical scoreboards in cricket": "cricket",
    "Category:Volleyball scoreboards": "volleyball",
    "Category:Table tennis scoreboards": "table tennis",
    "Category:Tennis scoreboards": "tennis",
    "Category:Baseball scoreboards": "baseball",
    "Category:Australian rules football scoreboards": "australian rules football",
    "Category:Athletics scoreboards": "athletics",
    "Category:Aquatic sports scoreboards": "aquatics",
    "Category:Curling scoreboards": "curling",
    "Category:Wrestling scoreboards": "wrestling",
    "Category:Judo scoreboards": "judo",
    "Category:Shot clock": "basketball",
    "Category:Daktronics": None,
    "Category:Sports scoreboards": None,
    "Category:Scoreboards": None,
}
DEPTH = 2
# Wikimedia license short names (extmetadata LicenseShortName) we accept, and
# their SPDX-style ids; ported versions (e.g. "CC BY-SA 3.0 de") are skipped.
_CC_RE = re.compile(r"CC (BY|BY-SA) (\d\.\d)")
_PUBLIC_DOMAIN = {"public domain", "pdm", "pd"}
_CC0 = {"cc0", "cc0 1.0", "cc-zero"}

FIELD_ROLES = (
    "home_score",
    "away_score",
    "score",  # a team's score when it isn't clear which team is at home
    "name",
    "clock",
    "shot_clock",
    "period",
    "home_fouls",
    "away_fouls",
    "home_timeouts",
    "away_timeouts",
    "home_bonus",
    "down",
    "to_go",
    "ball_on",
    "inning",
    "balls",
    "strikes",
    "outs",
    "runs",
    "wickets",
    "overs",
    "target",
    "batter_runs",
    "penalty_player",
    "penalty_time",
    "home_name",
    "away_name",
    "label",
    "other",
)


class CommonsClient:
    """Polite access to the Commons API and upload.wikimedia.org: one request
    at a time, at least MIN_REQUEST_INTERVAL apart, retried with backoff on
    network errors, 429 and 5xx (honouring Retry-After)."""

    def __init__(self, min_interval: float = MIN_REQUEST_INTERVAL, log=print):
        self.min_interval = min_interval
        self.log = log
        self._last = 0.0

    def _wait(self) -> None:
        delay = self._last + self.min_interval - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()

    def get(self, url: str, data: bytes | None = None, attempts: int = 6) -> bytes:
        """The body of url (a POST of the form data if given)."""
        request = urllib.request.Request(
            url, data=data, headers={"User-Agent": USER_AGENT}
        )
        for attempt in range(attempts):
            self._wait()
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    return response.read()
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                    raise
                retry_after = e.headers.get("Retry-After") if e.headers else None
                delay = (
                    float(retry_after)
                    if retry_after and retry_after.isdigit()
                    else 5.0 * (attempt + 1)
                )
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt == attempts - 1:
                    raise
                delay = 5.0 * (attempt + 1)
                if self.log:
                    self.log(f"  retrying after {e}")
            time.sleep(delay)
        raise RuntimeError("unreachable")

    def api(self, **params) -> dict:
        """A Commons API query (POSTed: 50 titles don't fit in a URL)."""
        params.update(format="json", formatversion="2", maxlag="5")
        body = urllib.parse.urlencode(params).encode("ascii")
        for _ in range(6):
            data = json.loads(self.get(API_URL, data=body))
            error = data.get("error")
            if error and error.get("code") == "maxlag":
                time.sleep(5)
                continue
            if error:
                raise RuntimeError(f"Commons API error: {error}")
            return data
        raise RuntimeError("Commons API: server lagged too long")

    def download(self, url: str, destination: Path) -> Path:
        if destination.is_file() and destination.stat().st_size > 0:
            return destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_name(destination.name + ".part")
        partial.write_bytes(self.get(url))
        partial.replace(destination)
        return destination


def category_members(client: CommonsClient, category: str, kind: str) -> list[dict]:
    members = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmtype": kind,
        "cmlimit": "500",
    }
    while True:
        data = client.api(**params)
        members += data["query"]["categorymembers"]
        if "continue" not in data:
            return members
        params.update(data["continue"])


def category_files(client: CommonsClient, category: str, depth: int) -> dict:
    """title -> pageid of the files in a category and its subcategories down
    to depth levels."""
    files = {}
    seen = set()
    queue = [(category, 0)]
    while queue:
        current, level = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        for member in category_members(client, current, "file"):
            files[member["title"]] = member["pageid"]
        if level < depth:
            for sub in category_members(client, current, "subcat"):
                queue.append((sub["title"], level + 1))
    return files


_EXTMETADATA_KEYS = (
    "LicenseShortName",
    "License",
    "LicenseUrl",
    "UsageTerms",
    "Artist",
    "Credit",
    "ObjectName",
    "AttributionRequired",
    "Copyrighted",
    "Restrictions",
    "DateTimeOriginal",
)


def file_infos(client: CommonsClient, titles, width: int = REFERENCE_WIDTH) -> dict:
    """title -> the file's page id, size, URLs, rendition (width px wide, or
    the original if narrower) and license metadata, from the Commons API."""
    infos = {}
    titles = list(titles)
    for start in range(0, len(titles), 50):
        chunk = titles[start : start + 50]
        data = client.api(
            action="query",
            prop="imageinfo",
            titles="|".join(chunk),
            iiprop="url|size|mime|sha1|extmetadata",
            iiurlwidth=str(width),
            iiextmetadatafilter="|".join(_EXTMETADATA_KEYS),
        )
        normalized = {n["to"]: n["from"] for n in data["query"].get("normalized", [])}
        for page in data["query"]["pages"]:
            title = normalized.get(page["title"], page["title"])
            if page.get("missing") or not page.get("imageinfo"):
                infos[title] = None
                continue
            info = page["imageinfo"][0]
            meta = {
                key: value.get("value")
                for key, value in (info.get("extmetadata") or {}).items()
            }
            infos[title] = {
                "title": page["title"],
                "pageid": page["pageid"],
                "width": info["width"],
                "height": info["height"],
                "mime": info.get("mime"),
                "sha1": info.get("sha1"),
                "url": info["url"],
                "page_url": info.get("descriptionurl"),
                "rendition_url": info.get("thumburl") or info["url"],
                "rendition_size": [
                    info.get("thumbwidth") or info["width"],
                    info.get("thumbheight") or info["height"],
                ],
                "extmetadata": meta,
            }
    return infos


def plain_text(value: str | None) -> str:
    """Text of an HTML snippet of the Commons metadata, on one line."""
    text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def license_id(meta: dict) -> str | None:
    """The SPDX-style id of a file's license (extmetadata), or None unless it
    allows redistribution with attribution: CC BY, CC BY-SA (unported
    versions), CC0 or public domain."""
    short = plain_text(meta.get("LicenseShortName"))
    folded = short.casefold()
    if folded in _CC0:
        return "CC0-1.0"
    if folded in _PUBLIC_DOMAIN:
        return "PDM-1.0"
    match = _CC_RE.fullmatch(short)
    if match:
        kind, version = match.groups()
        return f"CC-{kind}-{version}"
    return None


LICENSE_URLS = {
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "PDM-1.0": "https://creativecommons.org/publicdomain/mark/1.0/",
}


def license_url(license: str, meta: dict | None = None) -> str:
    if license in LICENSE_URLS:
        return LICENSE_URLS[license]
    match = re.fullmatch(r"CC-(BY|BY-SA)-(\d\.\d)", license)
    if match:
        kind, version = match.groups()
        return f"https://creativecommons.org/licenses/{kind.lower()}/{version}/"
    return (meta or {}).get("LicenseUrl") or ""


def author_of(meta: dict) -> str:
    author = plain_text(meta.get("Artist"))
    if not author or author.casefold() in ("unknown", "unknown author"):
        author = plain_text(meta.get("Credit"))
    return author[:200] or "unknown author"


def title_of(info: dict) -> str:
    """The file name without "File:" and the extension."""
    name = info["title"].split(":", 1)[-1]
    return name.rsplit(".", 1)[0]


# --- discovery ------------------------------------------------------------------------


def discover(client: CommonsClient, cache: Path, log=print) -> list[dict]:
    """Write cache/candidates.json: the files of CATEGORIES with a usable
    license (JPEG or PNG photos at least 640 px wide), and download their
    TRIAGE_WIDTH px thumbnails to cache/triage/<pageid>.jpg. The category
    listings are cached in cache/categories.json."""
    listings_path = cache / "categories.json"
    listings = {}
    if listings_path.is_file():
        with open(listings_path, encoding="utf-8") as f:
            listings = json.load(f)
    found = {}
    for category, sport in CATEGORIES.items():
        if category not in listings:
            listings[category] = category_files(client, category, DEPTH)
            write_text(listings_path, json.dumps(listings, indent=1))
        files = listings[category]
        log(f"{category}: {len(files)} files")
        for title, pageid in files.items():
            entry = found.setdefault(
                title, {"title": title, "pageid": pageid, "categories": []}
            )
            entry["categories"].append(category)
            if sport and not entry.get("sport"):
                entry["sport"] = sport
    infos = file_infos(client, sorted(found), width=TRIAGE_WIDTH)
    candidates = []
    skipped = Counter()
    for title, entry in sorted(found.items()):
        info = infos.get(title)
        if info is None:
            skipped["missing"] += 1
            continue
        if info["mime"] not in ("image/jpeg", "image/png"):
            skipped[f"type {info['mime']}"] += 1
            continue
        if info["width"] < 640 and info["height"] < 640:
            skipped["smaller than 640 px"] += 1
            continue
        license = license_id(info["extmetadata"])
        if license is None:
            skipped[
                f"license {plain_text(info['extmetadata'].get('LicenseShortName'))}"
            ] += 1
            continue
        entry.update(
            license=license,
            width=info["width"],
            height=info["height"],
            thumb_url=info["rendition_url"],
        )
        candidates.append(entry)
    log(f"{len(candidates)} candidates; skipped {dict(skipped)}")
    write_text(cache / "candidates.json", json.dumps(candidates, indent=1))
    for number, entry in enumerate(candidates, start=1):
        try:
            client.download(
                entry["thumb_url"], cache / "triage" / f"{entry['pageid']}.jpg"
            )
        except OSError as e:
            log(f"can't download {entry['title']}: {e}")
        if number % 100 == 0:
            log(f"  {number}/{len(candidates)} thumbnails")
    return candidates


# --- building -------------------------------------------------------------------------


def load_labels(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        labels = json.load(f)
    labels.setdefault("photos", {})
    labels.setdefault("rejected", {})
    for title, photo in labels["photos"].items():
        if photo.get("display_tech", "unknown") not in DISPLAY_TECHS:
            raise ValueError(f"{title}: unknown display tech {photo['display_tech']!r}")
        roles = set()
        for field in photo.get("fields", []):
            where = f"{title} {field.get('role')}"
            if field.get("field_type") not in FIELD_TYPES:
                raise ValueError(f"{where}: unknown field type")
            if field.get("display_tech", "unknown") not in DISPLAY_TECHS:
                raise ValueError(f"{where}: unknown display tech")
            role = field.get("role") or ""
            if re.sub(r"_\d+$", "", role) not in FIELD_ROLES:
                raise ValueError(f"{where}: unknown role")
            if role in roles:
                raise ValueError(f"{where}: duplicate role")
            roles.add(role)
            box = field.get("box")
            if not (
                isinstance(box, list)
                and len(box) == 4
                and all(isinstance(v, int) for v in box)
                and box[2] > 0
                and box[3] > 0
            ):
                raise ValueError(f"{where}: box must be [x, y, w, h]")
            text = field.get("text")
            if not isinstance(text, str) or not text or text != text.strip():
                raise ValueError(f"{where}: bad text {text!r}")
    return labels


def dump_labels(labels: dict) -> str:
    """The labels file's text: one line per field, photos sorted by title, so
    that edits diff readably."""

    def line(value) -> str:
        return json.dumps(value, ensure_ascii=False)

    lines = ["{"]
    for key in labels:
        if key not in ("photos", "rejected", "rejected_fields"):
            lines.append(f"  {line(key)}: {line(labels[key])},")
    lines.append('  "photos": {')
    photos = sorted(labels.get("photos", {}).items())
    for number, (title, photo) in enumerate(photos):
        lines.append(f"    {line(title)}: {{")
        for key, value in photo.items():
            if key != "fields":
                lines.append(f"      {line(key)}: {line(value)},")
        fields = photo.get("fields", [])
        lines.append('      "fields": [')
        for index, field in enumerate(fields):
            comma = "," if index < len(fields) - 1 else ""
            lines.append(f"        {line(field)}{comma}")
        lines.append("      ]")
        lines.append("    }" + ("," if number < len(photos) - 1 else ""))
    lines.append("  },")
    for name in ("rejected_fields", "rejected"):
        items = sorted(labels.get(name, {}).items())
        if name == "rejected_fields" and not items:
            continue
        lines.append(f"  {line(name)}: {{")
        for number, (key, reason) in enumerate(items):
            comma = "," if number < len(items) - 1 else ""
            lines.append(f"    {line(key)}: {line(reason)}{comma}")
        lines.append("  }" + ("," if name != "rejected" else ""))
    lines.append("}")
    return "\n".join(lines) + "\n"


def save_labels(path: Path, labels: dict) -> None:
    write_text(path, dump_labels(labels))


def sample_id(pageid: int, role: str) -> str:
    return f"cm{pageid}_{role}"


def _infos(client: CommonsClient, cache: Path, titles, offline: bool, log) -> dict:
    """The Commons metadata of the photos (fresh from the API, so that every
    build re-checks the licenses), cached in cache/fileinfo.json for
    --offline builds."""
    path = cache / "fileinfo.json"
    cached = {}
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            cached = json.load(f)
    titles = sorted(titles)
    if offline:
        missing = [t for t in titles if t not in cached]
        if missing:
            raise SystemExit(f"--offline: no cached metadata for {missing[:3]} ...")
        return cached
    if log:
        log(f"checking {len(titles)} photos with the Commons API")
    fresh = file_infos(client, titles)
    cached.update(fresh)
    write_text(path, json.dumps(cached, indent=1, ensure_ascii=False))
    return fresh


def _attribution(info: dict, license: str) -> str:
    meta = info["extmetadata"]
    return (
        f'"{title_of(info)}" by {author_of(meta)} ({info["page_url"]}), {license} '
        f"({license_url(license, meta)}), via Wikimedia Commons; cropped and resized"
    )


def _md(text: str) -> str:
    return re.sub(r"([\\`*_\[\]<>|#])", r"\\\1", text.replace("\n", " ").strip())


def _base_role(role: str) -> str:
    return re.sub(r"_\d+$", "", role)


def build(
    cache: Path,
    out: Path,
    labels_path: Path,
    frames: bool = False,
    offline: bool = False,
    log=print,
) -> list[Sample]:
    import shutil

    import cv2
    import numpy as np

    log = log or (lambda message: None)
    labels = load_labels(labels_path)
    client = CommonsClient(log=log)
    infos = _infos(client, cache, labels["photos"], offline, log)
    samples = []
    frame_rows = []
    sources = {}
    problems = []
    shutil.rmtree(out / "images", ignore_errors=True)
    shutil.rmtree(out / "frames", ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    photos = sorted(labels["photos"].items())
    for number, (title, photo) in enumerate(photos, start=1):
        info = infos.get(title)
        if info is None:
            problems.append(f"{title}: no longer on Commons")
            continue
        license = license_id(info["extmetadata"])
        if license is None:
            short = plain_text(info["extmetadata"].get("LicenseShortName"))
            problems.append(f"{title}: license is now {short!r}")
            continue
        pageid = info["pageid"]
        if photo.get("pageid") not in (None, pageid):
            problems.append(f"{title}: page id {pageid}, labels say {photo['pageid']}")
            continue
        path = client.download(
            info["rendition_url"], cache / "photos" / f"{pageid}.jpg"
        )
        image = cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            problems.append(f"{title}: can't decode {path}")
            continue
        if log and number % 25 == 0:
            log(f"  {number}/{len(photos)} photos")
        height, width = image.shape[:2]
        ref_width, ref_height = photo["size"]
        sx, sy = width / ref_width, height / ref_height
        if abs(sx - sy) > 0.02:
            problems.append(
                f"{title}: rendition is {width}x{height}, labels are for "
                f"{ref_width}x{ref_height}"
            )
            continue
        meta = info["extmetadata"]
        author = author_of(meta)
        attribution = _attribution(info, license)
        source_image = f"commons:{pageid}"
        # photos of the same board (a "group") share a split
        group = photo.get("group")
        split = assign_split(f"commons-group:{group}" if group else source_image)
        frame_fields = []
        for field in photo["fields"]:
            role = field["role"]
            x, y, w, h = field["box"]
            x0, y0 = max(0, round(x * sx)), max(0, round(y * sy))
            x1 = min(width, round((x + w) * sx))
            y1 = min(height, round((y + h) * sy))
            if x1 - x0 < 2 or y1 - y0 < 2:
                problems.append(f"{title} {role}: box outside the photo")
                continue
            crop = fit_height(image[y0:y1, x0:x1], MAX_CROP_HEIGHT)
            item_id = sample_id(pageid, role)
            image_name = f"images/{item_id}.png"
            write_png(out / image_name, crop)
            display_tech = field.get("display_tech") or photo.get(
                "display_tech", "unknown"
            )
            sport = photo.get("sport") or "sport unknown"
            notes = f"Wikimedia Commons {title}; {sport}; {role}"
            for extra_note in (field.get("notes"), photo.get("notes")):
                if extra_note:
                    notes += f"; {extra_note}"
            samples.append(
                Sample(
                    id=item_id,
                    image=image_name,
                    text=field["text"],
                    field_type=field["field_type"],
                    display_tech=display_tech,
                    split=split,
                    label_source=(
                        "human"
                        if field.get("verified_by")
                        else "model-assisted-unverified"
                    ),
                    license=license,
                    source_url=info["page_url"],
                    author=author,
                    attribution=attribution,
                    source_box=[x0, y0, x1 - x0, y1 - y0],
                    notes=notes,
                    extra={
                        "source_image": source_image,
                        # photos of the same board and game: clustered
                        # statistics resample them together
                        "group": group,
                        "source_size": [width, height],
                        "role": role,
                        "sport": photo.get("sport"),
                    },
                )
            )
            frame_fields.append(
                {
                    "id": item_id,
                    "role": role,
                    "box": [x0, y0, x1 - x0, y1 - y0],
                    "text": field["text"],
                    "field_type": field["field_type"],
                    "display_tech": display_tech,
                }
            )
        if not frame_fields:
            continue
        frame_name = frame_size = None
        if frames:
            small = image
            scale = FRAME_MAX_SIDE / max(width, height)
            if scale < 1:
                small = cv2.resize(
                    image,
                    (round(width * scale), round(height * scale)),
                    interpolation=cv2.INTER_AREA,
                )
            ok, buffer = cv2.imencode(
                ".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, FRAME_JPEG_QUALITY]
            )
            if not ok:
                raise ValueError("JPEG encoding failed")
            frame_name = f"frames/cm{pageid}.jpg"
            (out / "frames").mkdir(parents=True, exist_ok=True)
            (out / frame_name).write_bytes(buffer.tobytes())
            frame_size = [small.shape[1], small.shape[0]]
        frame_rows.append(
            {
                "id": f"cm{pageid}",
                "source_image": source_image,
                "title": info["title"],
                "source_url": info["page_url"],
                "image_url": info["rendition_url"],
                "original_size": [info["width"], info["height"]],
                "size": [width, height],
                "frame": frame_name,
                "frame_size": frame_size,
                "license": license,
                "author": author,
                "attribution": attribution,
                "sport": photo.get("sport"),
                "group": group,
                "split": split,
                "fields": frame_fields,
            }
        )
        sources[pageid] = (info, license, len(frame_fields))
    samples.sort(key=lambda s: s.id)
    frame_rows.sort(key=lambda r: r["id"])
    write_manifest(out, samples)
    with open(out / "frames.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for row in frame_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    write_text(out / "LICENSE", LICENSE_TEXT)
    write_attribution(out, sources)
    write_readme(out, samples, frame_rows, labels)
    for problem in problems:
        log(f"warning: {problem}")
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    log(
        f"Wrote {len(samples)} crops from {len(frame_rows)} photos to {out} "
        f"({size / 1e6:.1f} MB in all)"
    )
    return samples


# --- output files ---------------------------------------------------------------------

LICENSE_TEXT = """\
The commons_scoreboards dataset combines material under these licenses:

1. Images (images/*.png, and frames/*.jpg if present). Each crop or frame is
   an adaptation of a photograph published on Wikimedia Commons by its author
   under the license in the "license" field of its row in manifest.jsonl and
   frames.jsonl:
     CC-BY-<v>     Creative Commons Attribution, version <v>,
                   https://creativecommons.org/licenses/by/<v>/
     CC-BY-SA-<v>  Creative Commons Attribution-ShareAlike, version <v>,
                   https://creativecommons.org/licenses/by-sa/<v>/ ; adaptations
                   of these photographs are shared under the same license
     CC0-1.0       Creative Commons Zero (public domain dedication),
                   https://creativecommons.org/publicdomain/zero/1.0/
     PDM-1.0       in the public domain (the reason is on the file's page)
   The author, title and source of every photograph are in the rows'
   "author", "source_url" and "attribution" fields and in ATTRIBUTION.md.
   Changes: crops are cut around one scoreboard field and, if taller than 160
   pixels, downscaled; frames are downscaled. No endorsement by the authors is
   implied.

2. The labels (the boxes, texts, field types, roles and display technologies
   in manifest.jsonl and frames.jsonl, and
   ocr_eval/builders/commons_scoreboards_labels.json) are by the ScoreSight
   contributors, licensed under Creative Commons Attribution 4.0
   (https://creativecommons.org/licenses/by/4.0/).

These licenses apply to this folder only; the ScoreSight code is MIT licensed.
"""


def write_attribution(out: Path, sources: dict) -> None:
    lines = [
        "# Attribution",
        "",
        "Photographs from Wikimedia Commons (https://commons.wikimedia.org/), each cut "
        "into crops of its scoreboard fields (downscaled if taller than 160 px). "
        "Labels: ScoreSight contributors, CC BY 4.0.",
        "",
    ]
    for pageid in sorted(sources):
        info, license, count = sources[pageid]
        meta = info["extmetadata"]
        lines.append(
            f'- `cm{pageid}` ({count} crops): "{_md(title_of(info))}" by '
            f"{_md(author_of(meta))}, <{info['page_url']}>, {license} "
            f"(<{license_url(license, meta)}>)"
        )
    write_text(out / "ATTRIBUTION.md", "\n".join(lines) + "\n")


def write_readme(out: Path, samples, frame_rows, labels) -> None:
    def table(title, counter, unit="Crops"):
        rows = [f"| {title} | {unit} |", "|---|---:|"]
        rows += [f"| {k} | {v} |" for k, v in sorted(counter.items())]
        return rows + [""]

    by_source = Counter(s.label_source for s in samples)
    # reasons are "category: detail"
    rejected = Counter(
        reason.split(":", 1)[0] for reason in labels.get("rejected", {}).values()
    )
    has_frames = any(row["frame"] for row in frame_rows)
    lines = [
        f"# {NAME}",
        "",
        "Real scoreboard fields (scores, clocks, shot clocks, periods, fouls ...) cut from "
        "Wikimedia Commons photos of physical scoreboards, labelled field by field.",
        "",
        f"Built by `python -m ocr_eval.builders.{NAME} --cache DIR --frames` (see its "
        f"docstring) from `ocr_eval/builders/{NAME}_labels.json`, which re-checks every "
        "photo's license with the Commons API. Licenses: see LICENSE and "
        "ATTRIBUTION.md; crops of CC BY-SA photos are CC BY-SA.",
        "",
        f"{len(samples)} crops from {len(frame_rows)} photos. `frames.jsonl` lists every "
        "photo with its rendition URL, license and all its labelled fields (boxes in the "
        "pixels of the 1280 px rendition), for whole-frame experiments"
        + ("; `frames/` has the photos downscaled." if has_frames else "."),
        "",
        "Labels: "
        + ", ".join(f"{k} {v}" for k, v in sorted(by_source.items()))
        + ". The boxes and texts were drawn and transcribed with a model's help "
        "(Claude), looking at every field zoomed in; fields that weren't clearly legible "
        "were left out. Check them with `python -m ocr_eval review commons_scoreboards` "
        "and apply the exported decisions with the builder's `--apply-review`.",
        "",
    ]
    lines += table("Field type", Counter(s.field_type for s in samples))
    lines += table("Role", Counter(_base_role(s.extra["role"]) for s in samples))
    lines += table("Display technology", Counter(s.display_tech for s in samples))
    lines += table(
        "Sport", Counter(row["sport"] or "unknown" for row in frame_rows), "Photos"
    )
    lines += table("License", Counter(s.license for s in samples))
    lines += table("Split", Counter(s.split for s in samples))
    lines += [
        "Field types: `score` for scores (read like ScoreSight's Home Score box, 0-199), "
        "`clock` for game clocks and shot clocks showing tenths (`M:SS`, `MM:SS`, `S.D`), "
        "`period` for periods, quarters and innings (ScoreSight's Period box accepts 1-4), `number` for other numbers (shot clocks in "
        "whole seconds, fouls, timeouts, downs, cricket totals ...), `text` for team names "
        "and words, `other` for values with other characters (cricket overs such as "
        "`12.4`).",
        "",
        "## Photos looked at and not used",
        "",
        "| Reason | Photos |",
        "|---|---:|",
    ]
    lines += [
        f"| {_md(k)} | {v} |"
        for k, v in sorted(rejected.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    write_text(out / "README.md", "\n".join(lines) + "\n")


# --- review ---------------------------------------------------------------------------


def apply_review(labels_path: Path, review_path: Path, log=print) -> Counter:
    """Apply a review export (python -m ocr_eval review) to the labels: fields
    marked OK or fixed get "verified_by" (so their label_source becomes
    "human"), a fix replaces the text (the old one is kept as
    "corrected_from"), a drop removes the field (recorded in
    "rejected_fields")."""
    from ocr_eval.review import read_decisions

    review = read_decisions(review_path)
    if review.get("dataset") != NAME:
        raise ValueError(f"{review_path} is a review of {review.get('dataset')!r}")
    reviewer = review["reviewer"].strip()
    labels = load_labels(labels_path)
    by_id = {}
    for photo in labels["photos"].values():
        for field in photo.get("fields", []):
            by_id[sample_id(photo["pageid"], field["role"])] = (photo, field)
    counts = Counter()
    rejected_fields = labels.setdefault("rejected_fields", {})
    for item_id, decision in sorted(review["decisions"].items()):
        if item_id not in by_id:
            counts["unknown id"] += 1
            if log:
                log(f"warning: {item_id} is not in the labels")
            continue
        photo, field = by_id[item_id]
        verdict = decision["verdict"]
        counts[verdict] += 1
        if verdict == "drop":
            photo["fields"].remove(field)
            reason = decision.get("reason") or "dropped"
            rejected_fields[item_id] = f"{reason} (review by {reviewer})"
            continue
        if verdict == "fix" and decision["text"].strip() != field["text"]:
            field.setdefault("corrected_from", field["text"])
            field["text"] = decision["text"].strip()
        field["verified_by"] = reviewer
    save_labels(labels_path, labels)
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, help="download/cache folder")
    parser.add_argument("--out", type=Path, default=DATASETS_DIR / NAME)
    parser.add_argument("--labels", type=Path, default=LABELS_FILE)
    parser.add_argument(
        "--frames", action="store_true", help="also write downscaled frames/"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="use the cached Commons metadata instead of re-checking it",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="list candidate photos and download their thumbnails",
    )
    parser.add_argument(
        "--apply-review",
        type=Path,
        metavar="FILE",
        help="apply a review export (python -m ocr_eval review) to the labels",
    )
    args = parser.parse_args(argv)
    if args.apply_review:
        counts = apply_review(args.labels, args.apply_review)
        summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
        print(f"Applied: {summary}. Rebuild with --cache to update {args.out}.")
        return 0
    if not args.cache:
        parser.error("--cache is required")

    def log(message):
        print(message, flush=True)

    if args.discover:
        discover(CommonsClient(log=log), args.cache, log=log)
        return 0
    build(
        args.cache,
        args.out,
        args.labels,
        frames=args.frames,
        offline=args.offline,
        log=log,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
