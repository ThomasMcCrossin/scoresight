"""Evaluation datasets: a folder with manifest.jsonl, the crop images, and the
LICENSE and ATTRIBUTION files.

manifest.jsonl has one JSON object per crop:

    id            unique id ([A-Za-z0-9._-], starting with a letter or digit)
    image         the crop, a PNG path relative to the dataset folder. The raw
                  colour or gray crop as a user's box would cut it from the
                  frame, never a binarized one: preprocessing is part of what is
                  evaluated.
    text          the ground truth, exactly as displayed (non-empty)
    field_type    score | clock | period | number | text | other (fields.py)
    display_tech  led7 | dotmatrix | lcd | bulb | flip | broadcast | printed | unknown
    split         train | dev | test (tune on dev, report on test)
    label_source  human | model-assisted-unverified | synthetic
    license       the crop's license (SPDX-style id, e.g. CC-BY-2.0, CC0-1.0)
    source_url    where the source image came from (optional for synthetic)
    author        the source image's author
    attribution   the attribution line the license asks for
    source_box    [x, y, w, h] of the crop in the source image, or null
    notes         free text

Unknown keys are kept (Sample.extra) and ignored.
"""

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import numpy as np

from ocr_eval import DATASETS_DIR
from ocr_eval.fields import DISPLAY_TECHS, FIELD_TYPES, LABEL_SOURCES, SPLITS

MANIFEST = "manifest.jsonl"
REQUIRED_FIELDS = (
    "id",
    "image",
    "text",
    "field_type",
    "display_tech",
    "split",
    "label_source",
    "license",
)
OPTIONAL_FIELDS = ("source_url", "author", "attribution", "source_box", "notes")
LICENSE_FILES = ("LICENSE", "LICENSE.md", "LICENSE.txt")
ATTRIBUTION_FILES = ("ATTRIBUTION", "ATTRIBUTION.md", "ATTRIBUTION.txt")

# Licenses that allow committing the crops to this repository (with
# attribution where the license asks for it).
REDISTRIBUTABLE_LICENSE_RE = re.compile(
    r"CC0-1\.0|CC-BY-\d\.\d|CC-BY-SA-\d\.\d|PDM-1\.0|MIT"
)
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# Extra dataset folders to search by name, separated by os.pathsep.
DATASETS_PATH_ENV = "OCR_EVAL_DATASETS"


class DatasetError(Exception):
    pass


@dataclass(frozen=True)
class Sample:
    id: str
    image: str
    text: str
    field_type: str
    display_tech: str
    split: str
    label_source: str
    license: str
    source_url: str | None = None
    author: str | None = None
    attribution: str | None = None
    source_box: tuple[int, int, int, int] | None = None
    notes: str | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        row = {name: getattr(self, name) for name in REQUIRED_FIELDS}
        for name in OPTIONAL_FIELDS:
            row[name] = getattr(self, name)
        if row["source_box"] is not None:
            row["source_box"] = list(row["source_box"])
        row.update(self.extra)
        return row


@dataclass
class Dataset:
    name: str
    path: Path
    samples: list[Sample]
    manifest_sha256: str
    description: str = ""

    def image_path(self, sample: Sample) -> Path:
        return self.path / sample.image

    def load_image(self, sample: Sample) -> np.ndarray:
        return read_image(self.image_path(sample))

    def __len__(self) -> int:
        return len(self.samples)


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def read_image(path) -> np.ndarray:
    """A crop as a C-contiguous uint8 BGR array (H, W, 3), whatever the PNG's
    channels and bit depth. Reads paths with non-ASCII characters on Windows."""
    import cv2

    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise DatasetError(f"can't decode image {path}")
    if image.dtype != np.uint8:
        image = cv2.convertScaleAbs(image, alpha=255.0 / max(1, int(image.max())))
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return np.ascontiguousarray(image)


def _search_dirs() -> list[Path]:
    dirs = [DATASETS_DIR]
    for entry in os.environ.get(DATASETS_PATH_ENV, "").split(os.pathsep):
        if entry.strip():
            dirs.append(Path(entry.strip()).expanduser())
    return dirs


def resolve_dataset(ref: str | os.PathLike) -> Path:
    """The folder of a dataset given by name (a folder in ocr_eval/datasets/ or
    in $OCR_EVAL_DATASETS) or by path (its folder or its manifest.jsonl)."""
    path = Path(ref)
    if path.is_file() and path.name == MANIFEST:
        return path.parent.resolve()
    if (path / MANIFEST).is_file():
        return path.resolve()
    for directory in _search_dirs():
        candidate = directory / str(ref)
        if (candidate / MANIFEST).is_file():
            return candidate.resolve()
    raise DatasetError(
        f"no dataset {str(ref)!r}: not a folder with a {MANIFEST}, nor a dataset "
        f"in {', '.join(str(d) for d in _search_dirs())}"
    )


def list_datasets() -> list[Path]:
    """The folders of the datasets that can be given by name."""
    found = {}
    for directory in _search_dirs():
        if not directory.is_dir():
            continue
        for child in sorted(directory.iterdir()):
            if (child / MANIFEST).is_file() and child.name not in found:
                found[child.name] = child.resolve()
    return list(found.values())


def _description(path: Path) -> str:
    readme = path / "README.md"
    if not readme.is_file():
        return ""
    for line in readme.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "<!--", "|", "-", ">")):
            return line
    return ""


def _check_str(row, name, report, where, required):
    value = row.get(name)
    if value is None:
        if required:
            report.errors.append(f"{where}: missing {name!r}")
        return None
    if not isinstance(value, str):
        report.errors.append(f"{where}: {name!r} must be a string")
        return None
    return value


def _parse_row(row, line_no, root: Path, report: ValidationReport, strict_licenses):
    where = f"{MANIFEST}:{line_no}"
    if not isinstance(row, dict):
        report.errors.append(f"{where}: not a JSON object")
        return None
    values = {}
    for name in REQUIRED_FIELDS:
        values[name] = _check_str(row, name, report, where, required=True)
    for name in ("source_url", "author", "attribution", "notes"):
        values[name] = _check_str(row, name, report, where, required=False)
    if any(values[name] is None for name in REQUIRED_FIELDS):
        return None

    sample_id = values["id"]
    where = f"{MANIFEST}:{line_no} ({sample_id})"
    if not _ID_RE.fullmatch(sample_id):
        report.errors.append(f"{where}: invalid id")
    if not values["text"]:
        report.errors.append(f"{where}: empty text")
    elif values["text"] != values["text"].strip() or "\n" in values["text"]:
        report.errors.append(f"{where}: text has surrounding whitespace or newlines")
    for name, allowed in (
        ("field_type", FIELD_TYPES),
        ("display_tech", DISPLAY_TECHS),
        ("split", SPLITS),
        ("label_source", LABEL_SOURCES),
    ):
        if values[name] not in allowed:
            report.errors.append(
                f"{where}: {name} {values[name]!r} is not one of {', '.join(allowed)}"
            )
    if not values["license"]:
        report.errors.append(f"{where}: empty license")
    elif not REDISTRIBUTABLE_LICENSE_RE.fullmatch(values["license"]):
        message = f"{where}: license {values['license']!r} may not allow redistribution"
        (report.errors if strict_licenses else report.warnings).append(message)

    image = values["image"]
    image_path = PurePosixPath(image)
    if (
        image_path.is_absolute()
        or ".." in image_path.parts
        or "\\" in image
        or ":" in image
    ):
        report.errors.append(
            f"{where}: image must be a relative path inside the dataset"
        )
    elif image_path.suffix.lower() != ".png":
        report.errors.append(f"{where}: image must be a .png")
    else:
        full_path = root / image
        try:
            with open(full_path, "rb") as f:
                if f.read(len(_PNG_MAGIC)) != _PNG_MAGIC:
                    report.errors.append(f"{where}: {image} is not a PNG")
        except OSError:
            report.errors.append(f"{where}: missing image {image}")

    box = row.get("source_box")
    source_box = None
    if box is not None:
        if (
            isinstance(box, list)
            and len(box) == 4
            and all(isinstance(v, int) and not isinstance(v, bool) for v in box)
            and box[2] > 0
            and box[3] > 0
        ):
            source_box = tuple(box)
        else:
            report.errors.append(f"{where}: source_box must be null or [x, y, w, h]")

    known = set(REQUIRED_FIELDS) | set(OPTIONAL_FIELDS)
    extra = {k: v for k, v in row.items() if k not in known}
    return Sample(
        id=sample_id,
        image=image,
        text=values["text"],
        field_type=values["field_type"],
        display_tech=values["display_tech"],
        split=values["split"],
        label_source=values["label_source"],
        license=values["license"],
        source_url=values["source_url"],
        author=values["author"],
        attribution=values["attribution"],
        source_box=source_box,
        notes=values["notes"],
        extra=extra,
    )


def read_manifest(
    path: Path, strict_licenses: bool = False
) -> tuple[list[Sample], ValidationReport, str]:
    """Parse and validate a dataset folder. Returns (samples, report, sha256 of
    the manifest). Samples with errors are still returned when they parse."""
    report = ValidationReport()
    manifest = path / MANIFEST
    try:
        data = manifest.read_bytes()
    except OSError as e:
        report.errors.append(f"can't read {manifest}: {e}")
        return [], report, ""
    # of the LF form, so that a checkout with CRLF line endings hashes the same
    digest = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
    if not any((path / name).is_file() for name in LICENSE_FILES):
        report.errors.append(f"{path.name}: no LICENSE file")
    if not any((path / name).is_file() for name in ATTRIBUTION_FILES):
        report.errors.append(f"{path.name}: no ATTRIBUTION file")

    samples = []
    seen = set()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        report.errors.append(f"{MANIFEST}: not UTF-8")
        return [], report, digest
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as e:
            report.errors.append(f"{MANIFEST}:{line_no}: invalid JSON ({e})")
            continue
        sample = _parse_row(row, line_no, path, report, strict_licenses)
        if sample is None:
            continue
        if sample.id in seen:
            report.errors.append(f"{MANIFEST}:{line_no}: duplicate id {sample.id!r}")
            continue
        seen.add(sample.id)
        samples.append(sample)
    if not samples and not report.errors:
        report.errors.append(f"{MANIFEST}: no samples")
    return samples, report, digest


def validate_dataset(ref, strict_licenses: bool = False) -> ValidationReport:
    try:
        path = resolve_dataset(ref)
    except DatasetError as e:
        return ValidationReport(errors=[str(e)])
    return read_manifest(path, strict_licenses)[1]


def load_dataset(
    ref,
    splits: list[str] | tuple[str, ...] | None = None,
    limit: int | None = None,
) -> Dataset:
    """Load and validate a dataset; raises DatasetError if it has errors.
    splits keeps only those splits; limit keeps the first N samples (after the
    split filter), for quick runs."""
    path = resolve_dataset(ref)
    samples, report, digest = read_manifest(path)
    if not report.ok:
        shown = "\n  ".join(report.errors[:20])
        more = len(report.errors) - 20
        raise DatasetError(
            f"dataset {path} is invalid:\n  {shown}"
            + (f"\n  ... and {more} more" if more > 0 else "")
        )
    if splits:
        samples = [s for s in samples if s.split in splits]
    if limit is not None:
        samples = samples[: max(0, limit)]
    return Dataset(path.name, path, samples, digest, _description(path))


def write_manifest(path: Path, samples: list[Sample]) -> None:
    """Write samples as path/manifest.jsonl (LF line endings, UTF-8)."""
    lines = [
        json.dumps(sample.to_dict(), ensure_ascii=False, separators=(", ", ": "))
        for sample in samples
    ]
    with open(path / MANIFEST, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))


def assign_split(group: str, dev_fraction: float = 0.2) -> str:
    """A stable dev/test split for a group of samples (e.g. all crops of one
    source image, so the same scoreboard is never in both)."""
    digest = hashlib.sha256(group.encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big") / 2**64
    return "dev" if value < dev_fraction else "test"
