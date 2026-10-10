"""ScoreSight's own OCR pipeline: src/tesseract.py's TextDetector.

Each crop is read as one box covering the whole crop, with the settings
ScoreSight gives a box of the crop's field type (ocr_eval.fields.box_settings:
the defaults.py preset, minus the multi-frame and output-formatting options).
The crop plays the role of the frame, so the default GLOBAL (whole-frame Otsu)
binarization is an Otsu binarization of the crop; in the app it is computed
over the whole frame.

Variants: <model> uses ScoreSight's default preprocessing (Otsu binarization,
dilate 1, rescale to 35 px), <model>-nobin the same without binarization.
Models: the bundled tesseract/tessdata models.

The text of a prediction is what Tesseract recognized (with the field type's
character whitelist). info["state"] is the pipeline's verdict: Success,
FailedFilter (rejected by the box's format regex) or Empty, so the pipeline's
own filtered output is the text if the state is Success and "" otherwise; the
harness's "postfilter" scoring computes the same for every engine.
"""

import importlib.metadata

import cv2

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


def _split_variant(variant: str) -> tuple[str, str]:
    for suffix in sorted(PREPROCESSING, key=len, reverse=True):
        if suffix and variant.endswith(suffix):
            return variant[: -len(suffix)], suffix
    return variant, ""


class ScoreSightTesseract(Engine):
    name = "tesseract"
    variants = tuple(f"{m}{suffix}" for suffix in PREPROCESSING for m in MODELS)
    description = (
        "ScoreSight's pipeline (src/tesseract.py TextDetector) with the default "
        "box settings of the crop's field type"
    )
    license = "Apache-2.0 (Tesseract)"
    runtime = "tesserocr (Tesseract 5 LSTM), CPU, single thread"
    imports = ("tesserocr", "cv2", "PySide6")
    batch_size = 1

    def __init__(self, variant: str | None = None):
        super().__init__(variant)
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

    def recognize(self, crops, field_types):
        results = []
        for crop, field_type in zip(crops, field_types):
            # what the capture thread's to_gray() does to a BGR frame
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape[:2]
            target = self._target_class(
                0,
                0,
                width,
                height,
                box_name(field_type),
                box_settings(field_type, **self.overrides),
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
        try:
            import tesserocr

            info["version"] = (
                f"tesserocr {importlib.metadata.version('tesserocr')}, "
                f"Tesseract {tesserocr.tesseract_version().split()[1]}"
            )
        except Exception:
            pass
        return info
