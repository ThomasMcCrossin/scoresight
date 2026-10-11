"""ScoreSight's own OCR pipeline: src/tesseract.py's TextDetector.

Each crop is read as one box covering the whole crop, with the settings
ScoreSight gives a box of the crop's field type, or of its role's preset when
the dataset has roles (ocr_eval.fields.box_settings: the defaults.py preset,
minus the multi-frame and output-formatting options).
The crop plays the role of the frame, so the default GLOBAL (whole-frame Otsu)
binarization is an Otsu binarization of the crop; in the app it is computed
over the whole frame.

Variants: <model> uses ScoreSight's default preprocessing (Otsu binarization,
dilate 1, rescale to 35 px), <model>-nobin the same without binarization.
Models: the bundled tesseract/tessdata models. These are ScoreSight's presets
as they are, untuned.

"tuned" is Tesseract tuned on the dev split of the real datasets
(ocr_eval/results/2026-10-11/tune_tesseract.py; TUNED below): the same
pipeline and PSM 8, with the crop first made dark text on a light background
(inverted when the bright pixels are the minority of an Otsu threshold) and
scaled to TUNED["height"], then read without binarization, dilation or the
app's rescale. ScoreSight has no automatic polarity, and its 35 px rescale
target is fixed: those two steps happen here, before the pipeline.

The text of a prediction is what Tesseract recognized (with the field type's
character whitelist). info["state"] is the pipeline's verdict: Success,
FailedFilter (rejected by the box's format regex) or Empty, so the pipeline's
own filtered output is the text if the state is Success and "" otherwise; the
harness's "postfilter" scoring computes the same for every engine.
"""

import importlib.metadata

import cv2
import numpy as np

from ocr_eval import REPO_ROOT
from ocr_eval._src import isolate_app_state
from ocr_eval.engines import Engine, EngineUnavailable, Recognition
from ocr_eval.fields import box_name, box_settings

# Nothing beyond ScoreSight's own requirements.txt (tesserocr, opencv, PySide6).
REQUIREMENTS: list[str] = []

TESSDATA_DIR = REPO_ROOT / "tesseract" / "tessdata"
MODELS = ("scoreboard_general", "scoreboard_general_large", "daktronics", "eng")
# variant suffix -> box setting overrides
PREPROCESSING = {
    "": {},
    "-nobin": {
        "binarization_method": 1
    },  # TextDetector.BinarizationMethod.NO_BINARIZATION
}


# The dev-tuned variant, chosen on the dev split only (tune_tesseract.py):
# the model, the crop's height before the pipeline (px), whether to normalize
# its polarity, and the box setting overrides.
TUNED = {
    "model": "eng",
    "height": 24,
    "polarity": True,
    "overrides": {
        "binarization_method": 1,  # NO_BINARIZATION
        "dilate": 0,
        "rescale_patch": False,  # scaled to "height" before the pipeline
    },
}
TUNED_VARIANT = "tuned"


def dark_on_light(gray: np.ndarray) -> np.ndarray:
    """The crop with dark text on a light background: inverted when the
    bright side of an Otsu threshold is the minority of the pixels (light text
    on a dark board)."""
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    if np.count_nonzero(binary) < binary.size / 2:
        return 255 - gray
    return gray


def scale_to_height(gray: np.ndarray, height: int) -> np.ndarray:
    scale = height / gray.shape[0]
    if scale == 1:
        return gray
    return cv2.resize(
        gray,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA,
    )


def _split_variant(variant: str) -> tuple[str, str]:
    for suffix in sorted(PREPROCESSING, key=len, reverse=True):
        if suffix and variant.endswith(suffix):
            return variant[: -len(suffix)], suffix
    return variant, ""


class ScoreSightTesseract(Engine):
    name = "tesseract"
    variants = tuple(f"{m}{suffix}" for suffix in PREPROCESSING for m in MODELS) + (
        TUNED_VARIANT,
    )
    description = (
        "ScoreSight's pipeline (src/tesseract.py TextDetector) with the default "
        "box settings of the crop's field type (tuned: with the settings chosen "
        "on the dev split)"
    )
    license = "Apache-2.0 (Tesseract)"
    runtime = "tesserocr (Tesseract 5 LSTM), CPU, single thread"
    imports = ("tesserocr", "cv2", "PySide6")
    batch_size = 1
    reads_roles = True

    def __init__(self, variant: str | None = None):
        super().__init__(variant)
        # the crop's height before the pipeline (None: as it is), and whether
        # to make it dark on light first
        self.height = None
        self.polarity = False
        if self.variant == TUNED_VARIANT:
            self.model = TUNED["model"]
            self.overrides = dict(TUNED["overrides"])
            self.height = TUNED["height"]
            self.polarity = TUNED["polarity"]
        else:
            self.model, suffix = _split_variant(self.variant)
            self.overrides = dict(PREPROCESSING[suffix])
        self._detector = None
        self._target_class = None

    @classmethod
    def unavailable_reason(cls) -> str | None:
        reason = super().unavailable_reason()
        if reason:
            return reason
        if not TESSDATA_DIR.is_dir():
            return f"no models in {TESSDATA_DIR}"
        return None

    def load(self) -> None:
        model_path = TESSDATA_DIR / f"{self.model}.traineddata"
        if not model_path.is_file():
            raise EngineUnavailable(f"missing model {model_path}")
        isolate_app_state()
        # ScoreSight's src/tesseract.py and text_detection_target.py
        from tesseract import TextDetector
        from text_detection_target import TextDetectionTarget

        detector = TextDetector()
        index = {
            "daktronics": TextDetector.OcrModelIndex.DAKTRONICS,
            "scoreboard_general": TextDetector.OcrModelIndex.SCOREBOARD_GENERAL,
            "eng": TextDetector.OcrModelIndex.GENERAL_ENGLISH,
            "scoreboard_general_large": TextDetector.OcrModelIndex.SCOREBOARD_GENERAL_LARGE,
        }[self.model]
        if not detector.setOcrModel(index):
            raise EngineUnavailable(f"Tesseract can't load {model_path}")
        self._detector = detector
        self._target_class = TextDetectionTarget

    def recognize(self, crops, field_types, roles=None):
        results = []
        for crop, field_type, role in zip(
            crops, field_types, roles or [None] * len(crops)
        ):
            # what the capture thread's to_gray() does to a BGR frame
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            if self.polarity:
                gray = dark_on_light(gray)
            if self.height:
                gray = scale_to_height(gray, self.height)
            height, width = gray.shape[:2]
            target = self._target_class(
                0,
                0,
                width,
                height,
                box_name(field_type, role),
                box_settings(field_type, role, **self.overrides),
                [],
            )
            [result] = self._detector.detect_multi_text(None, gray, [target])
            confidence = (result.extra or {}).get("confidence")
            results.append(
                Recognition(
                    result.text,
                    None if confidence is None else round(confidence / 100.0, 4),
                    {"state": result.state.name},
                )
            )
        return results

    def close(self) -> None:
        if self._detector is not None and self._detector.api is not None:
            with self._detector.api_lock:
                self._detector.api.End()
                self._detector.api = None
        self._detector = None

    def info(self) -> dict:
        info = super().info()
        model_path = TESSDATA_DIR / f"{self.model}.traineddata"
        if model_path.is_file():
            info["size"] = (
                f"{model_path.stat().st_size / 1e6:.1f} MB ({self.model}.traineddata)"
            )
        info["model"] = self.model
        info["box_setting_overrides"] = self.overrides
        if self.polarity or self.height:
            info["before_the_pipeline"] = {
                "dark_on_light": self.polarity,
                "height": self.height,
            }
        try:
            import tesserocr

            info["version"] = (
                f"tesserocr {importlib.metadata.version('tesserocr')}, "
                f"Tesseract {tesserocr.tesseract_version().split()[1]}"
            )
        except Exception:
            pass
        return info
