"""Build ocr_eval/datasets/textocr_scoreboards: real scoreboard and clock crops.

Source: the TextVQA images tagged "Scoreboard" or "Digital clock" (TextVQA 0.5.1
image_classes), with the human word transcriptions and boxes of TextOCR 0.1
(CC BY 4.0). The images are Open Images photos from Flickr; only those whose
Open Images metadata lists CC BY, CC BY-SA, CC0 or the public domain mark are
used, and each crop keeps its photo's license, author and source.

Each selected word becomes one crop padded like a ScoreSight box (a quarter of
the word height on every side, cut short before a neighbouring word), at most
160 px tall. Selected words: clocks (M:SS, MM:SS, S.D), numbers of 1-3 digits,
ordinals (1st..) and common scoreboard words (HOME, GUEST, BALL, ...). Then the
manual review (textocr_scoreboards_review.json next to this file) drops crops
that aren't legible or aren't scoreboard values and sets display technologies.
The review is keyed by TextOCR word id; crops it doesn't mention are kept as
they are, so after changing the selection, review the new crops too.

    python -m ocr_eval.builders.textocr_scoreboards --cache DIR [--contact-sheets DIR]

The cache folder receives the downloads (about 0.5 GB: the TextOCR and TextVQA
annotations, the photos, and the rows of the 2.7 GB Open Images metadata CSV for
these photos, which is filtered as it streams in unless the whole CSV is already
in <cache>/openimages/); they are only parsed, never executed. With
--contact-sheets the crops are also drawn on numbered sheets for the review.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from ocr_eval import DATASETS_DIR
from ocr_eval.builders._common import (
    USER_AGENT,
    download,
    fit_height,
    write_png,
    write_text,
)
from ocr_eval.dataset import Sample, assign_split, write_manifest
from ocr_eval.fields import DISPLAY_TECHS, FIELD_TYPES

NAME = "textocr_scoreboards"
REVIEW_FILE = Path(__file__).with_name(f"{NAME}_review.json")

TEXTVQA_URL = "https://dl.fbaipublicfiles.com/textvqa/data/TextVQA_0.5.1_{split}.json"
TEXTOCR_URL = (
    "https://dl.fbaipublicfiles.com/textvqa/data/textocr/TextOCR_0.1_{split}.json"
)
OPENIMAGES_META_URL = (
    "https://storage.googleapis.com/openimages/v6/"
    "oidv6-train-images-with-labels-with-rotation.csv"
)
OPENIMAGES_IMAGE_URL = "https://open-images-dataset.s3.amazonaws.com/{subset}/{id}.jpg"
TEXTOCR_HOME = "https://textvqa.org/textocr/"

IMAGE_CLASSES = ("Scoreboard", "Digital clock")
MIN_WORD_HEIGHT = 12  # px in the source photo; smaller digits are rarely legible
MAX_ROTATION_DEGREES = 15  # a ScoreSight box is axis-aligned
PAD_FRACTION = 0.25  # of the word height, on every side
MAX_CROP_HEIGHT = 160
MAX_CROPS_PER_IMAGE = 12
# another word box covering more of a word than this makes the crop ambiguous
MAX_WORD_OVERLAP = 0.2

CLOCK_RE = re.compile(r"\d{1,2}:\d{2}|\d{1,2}\.\d")
NUMBER_RE = re.compile(r"\d{1,3}")
ORDINAL_RE = re.compile(r"\d{1,2}(st|nd|rd|th)", re.IGNORECASE)
SCOREBOARD_WORDS = {
    word.casefold()
    for word in """
    HOME GUEST GUESTS VISITOR VISITORS AWAY BALL BALLS STRIKE STRIKES OUT OUTS
    INNING INN PERIOD PER QTR QUARTER HALF BONUS POSS FOUL FOULS TOL TIMEOUTS
    DOWN TOGO YDS YARDS TIME SCORE SHOT CLOCK PLAYER PTS SET SETS GAME GAMES
    POINTS MATCH TEAM LAP LAPS OT R H E AT BAT HIT ERROR
    """.split()
}

_LICENSE_RE = re.compile(
    r"https?://creativecommons\.org/(?:licenses/(by|by-sa)/(\d\.\d)"
    r"|publicdomain/(zero|mark)/1\.0)/?"
)


def license_id(url: str) -> str | None:
    """The license id of an Open Images license URL, or None if it isn't one
    that allows redistribution (CC BY, CC BY-SA, CC0, PDM)."""
    match = _LICENSE_RE.fullmatch((url or "").strip())
    if not match:
        return None
    kind, version, public_domain = match.groups()
    if public_domain == "zero":
        return "CC0-1.0"
    if public_domain == "mark":
        return "PDM-1.0"
    return f"CC-{kind.upper()}-{version}"


def classify_word(text: str) -> str | None:
    """The field type a TextOCR word is kept as, or None to skip it."""
    if CLOCK_RE.fullmatch(text):
        return "clock"
    if NUMBER_RE.fullmatch(text):
        return "number"
    if ORDINAL_RE.fullmatch(text) or text.casefold() in SCOREBOARD_WORDS:
        return "text"
    return None


def word_rotation(points: list[float]) -> float:
    """The angle in degrees of a word polygon's top edge (first two points)."""
    if len(points) < 4:
        return 0.0
    dx, dy = points[2] - points[0], points[3] - points[1]
    if dx == 0 and dy == 0:
        return 0.0
    return math.degrees(math.atan2(dy, dx))


def _intersects(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _overlap(a, b) -> float:
    """The fraction of box a covered by box b."""
    width = min(a[2], b[2]) - max(a[0], b[0])
    height = min(a[3], b[3]) - max(a[1], b[1])
    area = (a[2] - a[0]) * (a[3] - a[1])
    if width <= 0 or height <= 0 or area <= 0:
        return 0.0
    return width * height / area


def padded_crop(word, others, width, height, pad_fraction=PAD_FRACTION):
    """The crop (x0, y0, x1, y1) for a word box (x0, y0, x1, y1): padded by
    pad_fraction of its height on each side, clipped to the image, and cut short
    on the side of any other word box that reaches into the padding (at the
    word's edge, if the other box touches the word). None if another word box
    covers more than MAX_WORD_OVERLAP of the word."""
    x0, y0, x1, y1 = word
    pad = (y1 - y0) * pad_fraction
    crop = [
        max(0.0, x0 - pad),
        max(0.0, y0 - pad),
        min(width, x1 + pad),
        min(height, y1 + pad),
    ]
    for other in others:
        if not _intersects(other, crop):
            continue
        if _overlap(word, other) > MAX_WORD_OVERLAP:
            return None
        gaps = {
            0: x0 - other[2],  # other is left of the word
            2: other[0] - x1,  # right
            1: y0 - other[3],  # above
            3: other[1] - y1,  # below
        }
        side = max(gaps, key=gaps.get)
        if side == 0:
            crop[0] = max(crop[0], min(other[2], x0))
        elif side == 2:
            crop[2] = min(crop[2], max(other[0], x1))
        elif side == 1:
            crop[1] = max(crop[1], min(other[3], y0))
        else:
            crop[3] = min(crop[3], max(other[1], y1))
    box = (
        int(math.floor(crop[0])),
        int(math.floor(crop[1])),
        int(math.ceil(crop[2])),
        int(math.ceil(crop[3])),
    )
    if box[2] - box[0] < 2 or box[3] - box[1] < 2:
        return None
    return box


# --- sources --------------------------------------------------------------------------


def load_textvqa_images(cache: Path, log) -> dict:
    """image_id -> {"classes", "textvqa_split"} for the tagged images."""
    images = {}
    for split in ("train", "val"):
        path = download(
            TEXTVQA_URL.format(split=split),
            cache / "textvqa" / f"TextVQA_0.5.1_{split}.json",
            log,
        )
        with open(path, encoding="utf-8") as f:
            data = json.load(f)["data"]
        for question in data:
            classes = question.get("image_classes") or []
            if any(c in IMAGE_CLASSES for c in classes):
                images[question["image_id"]] = {
                    "classes": sorted(c for c in classes if c in IMAGE_CLASSES),
                    "textvqa_split": split,
                }
    return images


def load_textocr(cache: Path, image_ids: set, log) -> tuple[dict, dict]:
    """(imgs, anns by image) of TextOCR for the given images, cached."""
    subset_path = cache / "textocr_subset.json"
    if subset_path.is_file():
        with open(subset_path, encoding="utf-8") as f:
            subset = json.load(f)
        if set(subset["image_ids"]) == set(image_ids):
            return subset["imgs"], subset["anns"]
    imgs, anns = {}, {}
    for split in ("train", "val"):
        path = download(
            TEXTOCR_URL.format(split=split),
            cache / "textocr" / f"TextOCR_0.1_{split}.json",
            log,
        )
        if log:
            log(f"reading {path.name}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for image_id in image_ids:
            if image_id in data["imgs"]:
                imgs[image_id] = data["imgs"][image_id]
                anns[image_id] = [
                    data["anns"][a] for a in data["imgToAnns"].get(image_id, [])
                ]
        del data
    with open(subset_path, "w", encoding="utf-8") as f:
        json.dump({"image_ids": sorted(image_ids), "imgs": imgs, "anns": anns}, f)
    return imgs, anns


def load_openimages_metadata(cache: Path, image_ids: set, log) -> dict:
    """ImageID -> Open Images metadata row (license, author, URLs), for the
    given images. Filters the 2.7 GB metadata CSV once (streamed unless it is
    in the cache folder) into a small cached subset."""
    subset_path = cache / "openimages_metadata_subset.csv"
    if subset_path.is_file():
        with open(subset_path, encoding="utf-8", newline="") as f:
            rows = {row["ImageID"]: row for row in csv.DictReader(f)}
        if image_ids <= set(rows) | _missing_ids(cache):
            return rows
    full = cache / "openimages" / Path(OPENIMAGES_META_URL).name
    if full.is_file():
        stream = open(full, encoding="utf-8", newline="")
    else:
        if log:
            log(f"streaming {OPENIMAGES_META_URL} (2.7 GB, filtered on the fly)")
        request = urllib.request.Request(
            OPENIMAGES_META_URL, headers={"User-Agent": USER_AGENT}
        )
        response = urllib.request.urlopen(request, timeout=120)
        stream = io.TextIOWrapper(response, encoding="utf-8", newline="")
    rows = {}
    with stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        for row in reader:
            if row["ImageID"] in image_ids:
                rows[row["ImageID"]] = row
    with open(subset_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for image_id in sorted(rows):
            writer.writerow(rows[image_id])
    (cache / "openimages_metadata_missing.txt").write_text(
        "\n".join(sorted(image_ids - set(rows))), encoding="utf-8"
    )
    return rows


def _missing_ids(cache: Path) -> set:
    path = cache / "openimages_metadata_missing.txt"
    if not path.is_file():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def load_photo(cache: Path, image_id: str, subset: str, log):
    import cv2

    path = cache / "images" / f"{image_id}.jpg"
    try:
        download(
            OPENIMAGES_IMAGE_URL.format(subset=subset, id=image_id), path, log=None
        )
    except OSError as e:
        if log:
            log(f"can't download {image_id}: {e}")
        return None
    return cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)


# --- building -------------------------------------------------------------------------


def load_review(path: Path) -> dict:
    review = {
        "drop_images": {},
        "drop": {},
        "image_display_tech": {},
        "display_tech": {},
        "field_type": {},
        "text": {},
    }
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for key in review:
            review[key].update(data.get(key, {}))
    for key in ("image_display_tech", "display_tech"):
        for item, tech in review[key].items():
            if tech not in DISPLAY_TECHS:
                raise ValueError(f"review: {item}: unknown display tech {tech!r}")
    for item, field_type in review["field_type"].items():
        if field_type not in FIELD_TYPES:
            raise ValueError(f"review: {item}: unknown field type {field_type!r}")
    return review


def _stable_order(values, key):
    return sorted(values, key=lambda v: hashlib.sha256(key(v).encode()).hexdigest())


def select_candidates(textvqa, imgs, anns, metadata, log):
    """The words to crop, and the counts of why others were skipped."""
    skipped = Counter()
    candidates = []
    for image_id in sorted(imgs):
        meta = metadata.get(image_id)
        if meta is None:
            skipped["image: no Open Images metadata"] += len(anns.get(image_id, []))
            continue
        license = license_id(meta.get("License", ""))
        if license is None:
            skipped[f"image: license {meta.get('License')}"] += len(
                anns.get(image_id, [])
            )
            continue
        boxes = []
        for ann in anns.get(image_id, []):
            x, y, w, h = ann["bbox"]
            boxes.append((x, y, x + w, y + h))
        chosen = []
        for index, ann in enumerate(anns.get(image_id, [])):
            text = ann["utf8_string"].strip()
            if text == ".":
                skipped["illegible in TextOCR"] += 1
                continue
            field_type = classify_word(text)
            if field_type is None:
                skipped["not a scoreboard value"] += 1
                continue
            word = boxes[index]
            if word[3] - word[1] < MIN_WORD_HEIGHT:
                skipped[f"smaller than {MIN_WORD_HEIGHT} px"] += 1
                continue
            angle = word_rotation(ann.get("points") or [])
            if abs(angle) > MAX_ROTATION_DEGREES:
                skipped[f"rotated more than {MAX_ROTATION_DEGREES} degrees"] += 1
                continue
            others = [b for i, b in enumerate(boxes) if i != index]
            chosen.append((ann, text, field_type, word, others, license))
        if len(chosen) > MAX_CROPS_PER_IMAGE:
            kept = _stable_order(chosen, key=lambda c: c[0]["id"])[:MAX_CROPS_PER_IMAGE]
            skipped[f"over {MAX_CROPS_PER_IMAGE} per photo"] += len(chosen) - len(kept)
            chosen = sorted(kept, key=lambda c: c[0]["id"])
        for ann, text, field_type, word, others, license in chosen:
            candidates.append(
                {
                    "id": ann["id"],
                    "image_id": image_id,
                    "text": text,
                    "field_type": field_type,
                    "word": word,
                    "others": others,
                    "license": license,
                    "meta": meta,
                    "textvqa": textvqa[image_id],
                    "image_size": (imgs[image_id]["width"], imgs[image_id]["height"]),
                }
            )
    return candidates, skipped


def _attribution(meta: dict, license: str) -> str:
    title = (meta.get("Title") or "").replace("\n", " ").strip() or "Untitled"
    author = (meta.get("Author") or "").strip() or "unknown author"
    return (
        f'"{title}" by {author} ({meta.get("OriginalLandingURL")}), {license} '
        f"({meta.get('License')}); cropped and resized. Transcription: TextOCR "
        f"({TEXTOCR_HOME}), CC-BY-4.0"
    )


def crop_candidates(candidates, cache: Path, out: Path, review: dict, log):
    """Crop, review and write the images; returns (samples, sources, dropped)."""
    samples = []
    dropped = []
    sources = {}
    photos = {}
    by_image = defaultdict(list)
    for candidate in candidates:
        by_image[candidate["image_id"]].append(candidate)
    for number, (image_id, items) in enumerate(sorted(by_image.items()), start=1):
        if image_id in review["drop_images"]:
            for c in items:
                dropped.append(
                    (c["id"], c["text"], f"review: {review['drop_images'][image_id]}")
                )
            continue
        photo = load_photo(
            cache, image_id, items[0]["meta"].get("Subset") or "train", log
        )
        if photo is None:
            for c in items:
                dropped.append((c["id"], c["text"], "photo not downloadable"))
            continue
        photos[image_id] = photo.shape
        if log and number % 50 == 0:
            log(f"  {number}/{len(by_image)} photos")
        height, width = photo.shape[:2]
        ann_width, ann_height = items[0]["image_size"]
        sx, sy = width / ann_width, height / ann_height
        for c in items:
            if c["id"] in review["drop"]:
                dropped.append(
                    (c["id"], c["text"], f"review: {review['drop'][c['id']]}")
                )
                continue
            scale = lambda b: (b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy)  # noqa: E731
            word = scale(c["word"])
            box = padded_crop(word, [scale(o) for o in c["others"]], width, height)
            if box is None:
                dropped.append(
                    (
                        c["id"],
                        c["text"],
                        f"another word box covers over {MAX_WORD_OVERLAP:.0%} of it",
                    )
                )
                continue
            x0, y0, x1, y1 = box
            crop = fit_height(photo[y0:y1, x0:x1], MAX_CROP_HEIGHT)
            text = review["text"].get(c["id"], c["text"])
            image = f"images/{c['id']}.png"
            write_png(out / image, crop)
            display_tech = review["display_tech"].get(
                c["id"], review["image_display_tech"].get(image_id, "unknown")
            )
            meta = c["meta"]
            samples.append(
                Sample(
                    id=c["id"],
                    image=image,
                    text=text,
                    field_type=review["field_type"].get(c["id"], c["field_type"]),
                    display_tech=display_tech,
                    split=assign_split(image_id),
                    label_source=(
                        "model-assisted-unverified"
                        if c["id"] in review["text"]
                        else "human"
                    ),
                    license=c["license"],
                    source_url=meta.get("OriginalLandingURL"),
                    author=(meta.get("Author") or "").strip() or None,
                    attribution=_attribution(meta, c["license"]),
                    source_box=[x0, y0, x1 - x0, y1 - y0],
                    notes=(
                        f"Open Images {image_id}; TextVQA {c['textvqa']['textvqa_split']} "
                        f"({', '.join(c['textvqa']['classes'])})"
                        + (
                            f"; TextOCR read {c['text']!r}, corrected in review"
                            if c["id"] in review["text"]
                            else ""
                        )
                    ),
                    extra={
                        "source_image": f"openimages:{image_id}",
                        "word_box": [
                            round(v)
                            for v in (
                                word[0],
                                word[1],
                                word[2] - word[0],
                                word[3] - word[1],
                            )
                        ],
                    },
                )
            )
            sources[image_id] = meta
    return samples, sources, dropped, photos


# --- output files ---------------------------------------------------------------------

LICENSE_TEXT = """\
The textocr_scoreboards dataset combines material under these licenses:

1. Images (images/*.png). Each crop is an adaptation of a photograph from the
   Open Images dataset, published on Flickr by its author under the license in
   the "license" field of the crop's row in manifest.jsonl (CC-BY-2.0 = Creative
   Commons Attribution 2.0, https://creativecommons.org/licenses/by/2.0/;
   CC-BY-SA-2.0 = Attribution-ShareAlike 2.0; CC0-1.0; PDM-1.0 = public domain
   mark). The author, title and source of every photograph are in the row's
   "author", "source_url" and "attribution" fields and in ATTRIBUTION.md.
   Changes: cropped around one word of text and, if taller than 160 pixels,
   downscaled. No endorsement by the authors is implied.

2. Transcriptions and word boxes ("text" and "word_box") come from TextOCR
   (Singh et al., "TextOCR: Towards large-scale end-to-end reasoning for
   arbitrary-shaped scene text", CVPR 2021, https://textvqa.org/textocr/),
   licensed under Creative Commons Attribution 4.0
   (https://creativecommons.org/licenses/by/4.0/). Image classes come from
   TextVQA (https://textvqa.org/), CC BY 4.0.

3. The rest of manifest.jsonl (field types, display technologies, splits and
   the review decisions in ocr_eval/builders/textocr_scoreboards_review.json)
   is by the ScoreSight contributors, licensed under CC BY 4.0.

These licenses apply to this folder only; the ScoreSight code is MIT licensed.
"""


def _md(text: str) -> str:
    return re.sub(r"([\\`*_\[\]<>|#])", r"\\\1", text.replace("\n", " ").strip())


def write_attribution(out: Path, sources: dict, samples: list[Sample]) -> None:
    counts = Counter(sample.extra["source_image"].split(":")[-1] for sample in samples)
    lines = [
        "# Attribution",
        "",
        "Transcriptions and word boxes: TextOCR (Singh et al., CVPR 2021, "
        f"{TEXTOCR_HOME}), CC BY 4.0. Image classes: TextVQA (https://textvqa.org/), "
        "CC BY 4.0.",
        "",
        "Photographs, from Open Images (https://storage.googleapis.com/openimages/web/index.html), "
        "each cropped (and downscaled if taller than 160 px):",
        "",
    ]
    for image_id in sorted(sources):
        meta = sources[image_id]
        title = _md(meta.get("Title") or "Untitled")
        author = _md(meta.get("Author") or "unknown author")
        license = license_id(meta.get("License", ""))
        lines.append(
            f'- `{image_id}` ({counts[image_id]} crops): "{title}" by {author}, '
            f"<{meta.get('OriginalLandingURL')}>, {license} (<{meta.get('License')}>)"
        )
    write_text(out / "ATTRIBUTION.md", "\n".join(lines) + "\n")


def write_readme(out: Path, samples, skipped: Counter, dropped, review_counts) -> None:
    by_type = Counter(s.field_type for s in samples)
    by_tech = Counter(s.display_tech for s in samples)
    by_split = Counter(s.split for s in samples)
    dropped_reasons = Counter(reason for _, _, reason in dropped)
    lines = [
        f"# {NAME}",
        "",
        "Real scoreboard and clock crops cut from Open Images photos (CC BY), with TextOCR's human transcriptions.",
        "",
        f"Built by `python -m ocr_eval.builders.{NAME}` (see its docstring); the manual review is in "
        f"`ocr_eval/builders/{NAME}_review.json`. Licenses: see LICENSE and ATTRIBUTION.md.",
        "",
        f"{len(samples)} crops from {len({s.extra['source_image'] for s in samples})} photos.",
        "",
        "| Field type | Crops |",
        "|---|---:|",
    ]
    lines += [f"| {k} | {v} |" for k, v in sorted(by_type.items())]
    lines += ["", "| Display technology | Crops |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(by_tech.items())]
    lines += ["", "| Split | Crops |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in sorted(by_split.items())]
    lines += [
        "",
        "Field types come from the transcription: `clock` for M:SS, MM:SS and S.D, `number` for 1-3 "
        "digits (scores, periods, innings and other numbers are not told apart), `text` for ordinals "
        "and scoreboard words. Display technologies were assigned per photo or crop in the review.",
        "",
        "## Selection",
        "",
        "TextOCR words of the photos, skipped automatically:",
        "",
        "| Reason | Words |",
        "|---|---:|",
    ]
    lines += [
        f"| {k} | {v} |" for k, v in sorted(skipped.items(), key=lambda kv: -kv[1])
    ]
    lines += [
        "",
        "Candidates dropped after cropping or in the review:",
        "",
        "| Reason | Crops |",
        "|---|---:|",
    ]
    lines += [
        f"| {_md(k)} | {v} |"
        for k, v in sorted(dropped_reasons.items(), key=lambda kv: -kv[1])
    ]
    if review_counts:
        lines += [
            "",
            "Review corrections: "
            + ", ".join(f"{k} {v}" for k, v in review_counts.items())
            + ".",
        ]
    write_text(out / "README.md", "\n".join(lines) + "\n")


def write_contact_sheets(
    samples: list[Sample], out: Path, sheets_dir: Path, per_sheet=60
):
    """Grids of the crops (numbered) for the manual review, and index.json."""
    import cv2

    from ocr_eval.dataset import read_image

    sheets_dir.mkdir(parents=True, exist_ok=True)
    tile_w, tile_h, cols = 220, 110, 6
    index = {}
    for sheet_number, start in enumerate(range(0, len(samples), per_sheet), start=1):
        chunk = samples[start : start + per_sheet]
        rows = math.ceil(len(chunk) / cols)
        sheet = np.full((rows * tile_h, cols * tile_w, 3), 255, np.uint8)
        for i, sample in enumerate(chunk):
            number = start + i + 1
            index[number] = sample.id
            crop = read_image(out / sample.image)
            scale = min((tile_h - 24) / crop.shape[0], (tile_w - 8) / crop.shape[1])
            size = (
                max(1, int(crop.shape[1] * scale)),
                max(1, int(crop.shape[0] * scale)),
            )
            crop = cv2.resize(
                crop,
                size,
                interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC,
            )
            r, c = divmod(i, cols)
            y, x = r * tile_h, c * tile_w
            sheet[y + 2 : y + 2 + size[1], x + 4 : x + 4 + size[0]] = crop
            label = f"{number}: {sample.text}"
            cv2.putText(
                sheet,
                label,
                (x + 4, y + tile_h - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 200),
                1,
                cv2.LINE_AA,
            )
            cv2.rectangle(
                sheet, (x, y), (x + tile_w - 1, y + tile_h - 1), (200, 200, 200), 1
            )
        write_png(sheets_dir / f"sheet_{sheet_number:03d}.png", sheet)
    write_text(sheets_dir / "index.json", json.dumps(index, indent=1))


def build(cache: Path, out: Path, review_path: Path, sheets: Path | None, log=print):
    import shutil

    review = load_review(review_path)
    textvqa = load_textvqa_images(cache, log)
    log(f"{len(textvqa)} TextVQA photos tagged {' or '.join(IMAGE_CLASSES)}")
    imgs, anns = load_textocr(cache, set(textvqa), log)
    log(f"{len(imgs)} of them in TextOCR, {sum(len(a) for a in anns.values())} words")
    metadata = load_openimages_metadata(cache, set(imgs), log)
    candidates, skipped = select_candidates(textvqa, imgs, anns, metadata, log)
    log(f"{len(candidates)} candidate words")
    shutil.rmtree(out / "images", ignore_errors=True)
    samples, sources, dropped, _ = crop_candidates(candidates, cache, out, review, log)
    samples.sort(key=lambda s: s.id)
    write_manifest(out, samples)
    write_text(out / "LICENSE", LICENSE_TEXT)
    write_attribution(out, sources, samples)
    review_counts = {
        "texts corrected": len(review["text"]),
        "field types set": len(review["field_type"]),
    }
    write_readme(out, samples, skipped, dropped, review_counts)
    with open(out / "dropped.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for item_id, text, reason in sorted(dropped):
            f.write(
                json.dumps(
                    {"id": item_id, "text": text, "reason": reason}, ensure_ascii=False
                )
                + "\n"
            )
    size = sum(p.stat().st_size for p in (out / "images").glob("*.png"))
    log(
        f"Wrote {len(samples)} crops ({size / 1e6:.1f} MB) to {out}; dropped {len(dropped)}"
    )
    if sheets:
        write_contact_sheets(samples, out, sheets)
        log(f"Contact sheets in {sheets}")
    return samples


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--cache", type=Path, required=True, help="download/cache folder"
    )
    parser.add_argument("--out", type=Path, default=DATASETS_DIR / NAME)
    parser.add_argument("--review", type=Path, default=REVIEW_FILE)
    parser.add_argument(
        "--contact-sheets", type=Path, help="write review contact sheets here"
    )
    args = parser.parse_args(argv)
    build(args.cache, args.out, args.review, args.contact_sheets)
    return 0


if __name__ == "__main__":
    sys.exit(main())
