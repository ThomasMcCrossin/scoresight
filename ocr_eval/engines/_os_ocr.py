"""Pre- and post-processing shared by the operating systems' OCR adapters
(windows_ocr.py and apple_vision.py). Not an adapter itself: discovery skips
modules whose name starts with "_".

The OS engines are document OCR: a text detector finds lines and words, then a
recognizer with a language model reads them. They have no character whitelist
and no "single word" mode, and scoreboard crops are small, often a single
character, and touch the crop's edges. Each adapter variant combines one
preprocessing with an optional "-digits" suffix:

raw       the crop as it is.
upscale   a crop shorter than UPSCALE_HEIGHT px is scaled up to that height
          (bicubic, aspect ratio kept), then put on a canvas with a margin of
          MARGIN x its height on every side, filled with the crop's border
          colour (the median of its outermost pixels). Detectors miss small text
          and text that touches the image edge.
tile      upscale, then TILE_COPIES copies of the crop side by side, TILE_GAP x
          its height apart. Each recognized word is assigned to the copy under
          its centre; a word spanning k copies that reads as k equal parts
          ("333" over three copies of a 3) is split between them. The copies'
          readings are then majority-voted (a tie goes to the leftmost copy).
          Windows OCR never returns a lone character, and half of the real
          crops are one digit; a row of copies reads as a word.
-digits   for numeric field types (score, clock, period, number), letters the
          engines confuse with digits are mapped to them (O->0, l->1, S->5,
          B->8, ...; DIGIT_LOOKALIKES), before the copies are voted: the OS
          engines' stand-in for Tesseract's digit whitelist. Text fields are
          left alone.

Geometry: UPSCALE_HEIGHT, MARGIN, TILE_COPIES and TILE_GAP were chosen on the
dev split of textocr_scoreboards with Windows OCR; heights 48 to 96 px, margins
0.25 to 1 and gaps 0.25 to 0.5 gave the same accuracy within about a point
(wider gaps and two copies were worse). See docs/development/ocr-eval.md.
"""

import importlib.util
from dataclasses import dataclass
from typing import NamedTuple

import cv2
import numpy as np

from ocr_eval.engines import Recognition

PREPROCESSING = ("raw", "upscale", "tile")
DIGITS_SUFFIX = "-digits"

UPSCALE_HEIGHT = 64
MARGIN = 0.5
TILE_COPIES = 3
TILE_GAP = 0.5

NUMERIC_FIELD_TYPES = ("score", "clock", "period", "number")
# Letters and punctuation document OCR reads in place of a digit, ":" or "."
DIGIT_LOOKALIKES = {
    "O": "0",
    "o": "0",
    "D": "0",
    "Q": "0",
    "I": "1",
    "l": "1",
    "i": "1",
    "|": "1",
    "!": "1",
    "Z": "2",
    "z": "2",
    "A": "4",
    "S": "5",
    "s": "5",
    "G": "6",
    "b": "6",
    "T": "7",
    "B": "8",
    "g": "9",
    "q": "9",
    ";": ":",
    ",": ".",
}
_DIGIT_TABLE = str.maketrans(DIGIT_LOOKALIKES)


class Word(NamedTuple):
    """A recognized word (or line) with its box in the prepared image's pixels
    (origin top left)."""

    text: str
    x: float
    y: float
    width: float
    height: float
    confidence: float | None = None


@dataclass(frozen=True)
class Prepared:
    """The image given to the engine (C-contiguous uint8 BGR) and the x range
    [start, end) of each copy of the crop in it (one copy unless tiled)."""

    image: np.ndarray
    copies: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class VariantSpec:
    level: str | None  # e.g. Apple Vision's "accurate"; None if the engine has none
    preprocessing: str  # one of PREPROCESSING
    digits: bool


def variant_names(levels: tuple[str, ...] = ()) -> tuple[str, ...]:
    """[level-]preprocessing[-digits] for every combination."""
    names = tuple(
        f"{prep}{suffix}" for prep in PREPROCESSING for suffix in ("", DIGITS_SUFFIX)
    )
    if not levels:
        return names
    return tuple(f"{level}-{name}" for level in levels for name in names)


def parse_variant(variant: str) -> VariantSpec:
    rest, digits = variant, False
    if rest.endswith(DIGITS_SUFFIX):
        rest, digits = rest[: -len(DIGITS_SUFFIX)], True
    level, _, prep = rest.rpartition("-")
    if prep not in PREPROCESSING:
        raise ValueError(f"unknown preprocessing in variant {variant!r}")
    return VariantSpec(level or None, prep, digits)


def describe(spec: VariantSpec) -> dict:
    """The variant's preprocessing for engine info()."""
    info = {"preprocessing": spec.preprocessing, "digit_lookalikes": spec.digits}
    if spec.preprocessing != "raw":
        info["upscale_height"] = UPSCALE_HEIGHT
        info["margin"] = MARGIN
    if spec.preprocessing == "tile":
        info["copies"] = TILE_COPIES
        info["gap"] = TILE_GAP
    return info


def missing_modules(names) -> list[str]:
    """The modules (dotted names allowed) that can't be found. Unlike a bare
    importlib.util.find_spec, a missing parent package counts as missing
    instead of raising."""
    missing = []
    for name in names:
        try:
            found = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            found = False
        if not found:
            missing.append(name)
    return missing


def border_colour(image: np.ndarray) -> tuple[int, int, int]:
    ring = np.concatenate([image[0], image[-1], image[:, 0], image[:, -1]])
    return tuple(int(v) for v in np.median(ring, axis=0))


def upscale(image: np.ndarray, height: int = UPSCALE_HEIGHT) -> np.ndarray:
    """The image scaled up to `height` px (bicubic), or as it is if it is at
    least that tall."""
    if image.shape[0] >= height:
        return image
    scale = height / image.shape[0]
    width = max(1, round(image.shape[1] * scale))
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_CUBIC)


def prepare(
    crop: np.ndarray,
    preprocessing: str,
    *,
    height: int | None = None,
    margin: float | None = None,
    copies: int | None = None,
    gap: float | None = None,
    max_dimension: int | None = None,
) -> Prepared:
    """The image an OS engine reads for a crop (see the module docstring; the
    geometry defaults to the module's constants). max_dimension: the engine's
    largest image side; a larger image is scaled down to fit."""
    if preprocessing not in PREPROCESSING:
        raise ValueError(f"unknown preprocessing {preprocessing!r}")
    height = UPSCALE_HEIGHT if height is None else height
    margin = MARGIN if margin is None else margin
    copies = TILE_COPIES if copies is None else copies
    gap = TILE_GAP if gap is None else gap
    if preprocessing == "raw":
        image = crop
        spans = [(0.0, float(crop.shape[1]))]
    else:
        scaled = upscale(crop, height)
        h, w = scaled.shape[:2]
        count = copies if preprocessing == "tile" else 1
        pad = round(margin * h)
        spacing = round(gap * h)
        image = np.empty(
            (h + 2 * pad, 2 * pad + count * w + (count - 1) * spacing, 3), np.uint8
        )
        image[:] = border_colour(scaled)
        spans = []
        for i in range(count):
            left = pad + i * (w + spacing)
            image[pad : pad + h, left : left + w] = scaled
            spans.append((float(left), float(left + w)))
    if max_dimension and max(image.shape[:2]) > max_dimension:
        scale = max_dimension / max(image.shape[:2])
        size = (
            min(max_dimension, max(1, round(image.shape[1] * scale))),
            min(max_dimension, max(1, round(image.shape[0] * scale))),
        )
        image = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
        spans = [(a * scale, b * scale) for a, b in spans]
    return Prepared(np.ascontiguousarray(image), tuple(spans))


def fix_digits(text: str, field_type: str) -> str:
    """For numeric field types, the text with DIGIT_LOOKALIKES mapped to digits."""
    if field_type not in NUMERIC_FIELD_TYPES:
        return text
    return text.translate(_DIGIT_TABLE)


def join_words(words: list[Word]) -> str:
    """The words in reading order: grouped into lines (a word joins the first
    line whose vertical extent holds its centre), lines top to bottom, words
    left to right, all separated by spaces."""
    lines: list[list] = []  # [top, bottom, [words]]
    for word in sorted(words, key=lambda w: (w.y, w.x)):
        if not word.text.strip():
            continue
        centre = word.y + word.height / 2
        for line in lines:
            if line[0] <= centre <= line[1]:
                line[2].append(word)
                line[0] = min(line[0], word.y)
                line[1] = max(line[1], word.y + word.height)
                break
        else:
            lines.append([word.y, word.y + word.height, [word]])
    lines.sort(key=lambda line: line[0])
    return " ".join(
        " ".join(w.text.strip() for w in sorted(line[2], key=lambda w: w.x))
        for line in lines
    )


def _confidence(words: list[Word]) -> float | None:
    """The weakest word's confidence, or None if a word has none."""
    values = [w.confidence for w in words]
    if not values or any(v is None for v in values):
        return None
    return round(float(min(values)), 4)


def _copy_index(word: Word, copies: tuple[tuple[float, float], ...]) -> int:
    centre = word.x + word.width / 2

    def distance(i):
        start, end = copies[i]
        if start <= centre <= end:
            return 0.0
        return min(abs(centre - start), abs(centre - end))

    return min(range(len(copies)), key=distance)


def _spanned_copies(word: Word, copies: tuple[tuple[float, float], ...]) -> list[int]:
    """The copies at least half covered by the word's box."""
    spanned = []
    for i, (start, end) in enumerate(copies):
        overlap = min(end, word.x + word.width) - max(start, word.x)
        if overlap >= 0.5 * (end - start):
            spanned.append(i)
    return spanned


def _assign_to_copies(
    words: list[Word], copies: tuple[tuple[float, float], ...]
) -> list[list[Word]]:
    """Each word goes to the copy under its centre. A word that spans k copies
    and reads as k equal parts (e.g. "333" over three copies of a "3": the
    engine merged the copies into one word) is split into one part per copy."""
    groups: list[list[Word]] = [[] for _ in copies]
    for word in words:
        text = "".join(word.text.split())
        if not text:
            continue
        spanned = _spanned_copies(word, copies)
        k = len(spanned)
        if k > 1 and len(text) % k == 0:
            size = len(text) // k
            parts = [text[i * size : (i + 1) * size] for i in range(k)]
            if len(set(parts)) == 1:
                for part, i in zip(parts, spanned):
                    start, end = copies[i]
                    groups[i].append(
                        word._replace(text=part, x=start, width=end - start)
                    )
                continue
        groups[_copy_index(word, copies)].append(word)
    return groups


def assemble(
    words: list[Word],
    prepared: Prepared,
    field_type: str,
    digits: bool = False,
) -> Recognition:
    """The crop's reading from the words the engine found in prepared.image:
    with -digits, look-alikes mapped first; for a tiled image, the majority of
    the copies' readings (info["copies"] lists them)."""
    if digits:
        words = [w._replace(text=fix_digits(w.text, field_type)) for w in words]
    if len(prepared.copies) == 1:
        return Recognition(join_words(words), _confidence(words), None)

    groups = _assign_to_copies(words, prepared.copies)
    readings = [join_words(group) for group in groups]
    keys = ["".join(reading.split()) for reading in readings]
    counts: dict[str, int] = {}
    for key in keys:
        if key:
            counts[key] = counts.get(key, 0) + 1
    info = {"copies": readings}
    if not counts:
        return Recognition("", None, info)
    best = max(counts.values())
    winner = next(i for i, key in enumerate(keys) if key and counts[key] == best)
    return Recognition(readings[winner], _confidence(groups[winner]), info)
