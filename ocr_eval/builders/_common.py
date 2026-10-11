"""Helpers shared by the dataset builders."""

import shutil
import urllib.request
from pathlib import Path

import numpy as np

USER_AGENT = "ScoreSight-ocr_eval-builder/1 (+https://github.com/royshil/scoresight)"


def download(url: str, destination: Path, log=print) -> Path:
    """Download url to destination unless it exists (a cache). The data is
    only ever parsed (JSON, CSV, images), never executed."""
    if destination.exists() and destination.stat().st_size > 0:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    if log:
        log(f"downloading {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with (
        urllib.request.urlopen(request, timeout=60) as response,
        open(partial, "wb") as f,
    ):
        shutil.copyfileobj(response, f, length=1 << 20)
    partial.replace(destination)
    return destination


def encode_png(image: np.ndarray) -> bytes:
    import cv2

    ok, buffer = cv2.imencode(".png", image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    if not ok:
        raise ValueError("PNG encoding failed")
    return buffer.tobytes()


def write_png(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encode_png(image))


def fit_height(image: np.ndarray, max_height: int) -> np.ndarray:
    """Downscale (never upscale) to at most max_height pixels tall."""
    import cv2

    height, width = image.shape[:2]
    if height <= max_height:
        return image
    scale = max_height / height
    size = (max(1, round(width * scale)), max_height)
    return cv2.resize(image, size, interpolation=cv2.INTER_AREA)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
