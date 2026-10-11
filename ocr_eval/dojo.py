"""Turn a ScoreSight Training Dojo folder into an evaluation dataset.

The app's "Save OCR training data" writes, per box reading, <id>.png (the
binarized patch), <id>_gray.png (the raw gray crop) and <id>.txt (the text);
the Training Dojo corrects the texts and records the approved ones in
approved_annotations.json ({<id>: text}). This converter takes the approved
samples (labels checked by a person: label_source "human") and, with
include_unapproved, the others (label_source "model-assisted-unverified"),
always with the raw gray crop: the binarized patch is never used.
"""

import json
import shutil
from pathlib import Path

from ocr_eval.dataset import (
    MANIFEST,
    REDISTRIBUTABLE_LICENSE_RE,
    Sample,
    assign_split,
    read_manifest,
    write_manifest,
)
from ocr_eval.fields import DISPLAY_TECHS, FIELD_TYPES, guess_field_type

APPROVED_ANNOTATIONS_FILE = "approved_annotations.json"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def import_dojo(
    folder,
    out,
    *,
    author: str,
    license: str,
    attribution: str | None = None,
    source_url: str | None = None,
    field_type: str = "auto",
    display_tech: str = "unknown",
    include_unapproved: bool = False,
    prefix: str = "dojo",
    log=print,
) -> tuple[int, list[tuple[str, str]]]:
    """Add the folder's samples to the dataset at out (created if needed;
    samples whose id is already there are skipped). Returns (number added,
    [(sample, reason skipped)])."""
    folder = Path(folder)
    out = Path(out)
    if field_type != "auto" and field_type not in FIELD_TYPES:
        raise ValueError(f"unknown field type {field_type!r}")
    if display_tech not in DISPLAY_TECHS:
        raise ValueError(f"unknown display tech {display_tech!r}")
    if not folder.is_dir():
        raise ValueError(f"{folder} is not a folder")

    approved = {}
    approved_path = folder / APPROVED_ANNOTATIONS_FILE
    if approved_path.is_file():
        try:
            data = json.loads(approved_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                approved = {str(k): str(v) for k, v in data.items()}
        except (OSError, ValueError) as e:
            raise ValueError(f"can't read {approved_path}: {e}") from e

    existing: list[Sample] = []
    if (out / MANIFEST).is_file():
        existing, report, _ = read_manifest(out)
        if not report.ok:
            raise ValueError(f"{out} has an invalid manifest: {report.errors[0]}")
    known_ids = {s.id for s in existing}

    added: list[Sample] = []
    skipped: list[tuple[str, str]] = []
    (out / "images").mkdir(parents=True, exist_ok=True)
    for text_path in sorted(folder.glob("*.txt")):
        base = text_path.stem
        if base in approved:
            text, label_source = approved[base].strip(), "human"
        elif include_unapproved:
            text, label_source = _read_text(text_path), "model-assisted-unverified"
        else:
            skipped.append((base, "not approved in the Training Dojo"))
            continue
        gray_path = folder / f"{base}_gray.png"
        if not gray_path.is_file():
            skipped.append((base, "no raw crop (<id>_gray.png)"))
            continue
        if not text or "\n" in text:
            skipped.append((base, "empty or multi-line text"))
            continue
        sample_id = f"{prefix}_{base}"
        if sample_id in known_ids:
            skipped.append((base, "already in the dataset"))
            continue
        image = f"images/{sample_id}.png"
        shutil.copyfile(gray_path, out / image)
        added.append(
            Sample(
                id=sample_id,
                image=image,
                text=text,
                field_type=guess_field_type(text)
                if field_type == "auto"
                else field_type,
                display_tech=display_tech,
                split=assign_split(base),
                label_source=label_source,
                license=license,
                source_url=source_url,
                author=author,
                attribution=attribution
                or f"{author}, ScoreSight Training Dojo ({license})",
                source_box=None,
                notes="imported from a Training Dojo folder",
            )
        )
        known_ids.add(sample_id)

    write_manifest(out, existing + added)
    _ensure_license_files(out, author, license, attribution, source_url)
    if log:
        if not REDISTRIBUTABLE_LICENSE_RE.fullmatch(license):
            log(
                f"warning: {license!r} is not a license this repository accepts for "
                "committed data (CC0-1.0, CC-BY-4.0, ...); keep this dataset private"
            )
        log(
            "Reminder: only commit crops you have the rights to. Frames of TV or "
            "streamed broadcasts are copyrighted and must stay private."
        )
    return len(added), skipped


def _ensure_license_files(out: Path, author, license, attribution, source_url):
    license_path = out / "LICENSE"
    if not license_path.exists():
        license_path.write_text(
            f"The images and labels in this folder are licensed under {license} "
            f"by their contributors (see ATTRIBUTION.md and the license field of "
            f"each row of {MANIFEST}).\n",
            encoding="utf-8",
            newline="\n",
        )
    attribution_path = out / "ATTRIBUTION.md"
    line = f"- {attribution or author} ({license})" + (
        f", {source_url}" if source_url else ""
    )
    if attribution_path.exists():
        current = attribution_path.read_text(encoding="utf-8")
        if line in current:
            return
        attribution_path.write_text(
            current.rstrip("\n") + "\n" + line + "\n", encoding="utf-8", newline="\n"
        )
    else:
        attribution_path.write_text(
            "# Attribution\n\nCrops contributed from ScoreSight Training Dojo "
            "exports:\n\n" + line + "\n",
            encoding="utf-8",
            newline="\n",
        )
