"""ScoreSight's own PP-OCR engine (src/ppocr_engine.py) through its pipeline
(src/tesseract.py's TextDetector), as the app reads boxes.

A batch of crops is laid out side by side in one colour frame, each crop
exactly as it is, and read as one box per crop with a single
TextDetector.detect_multi_text call: the boxes' colour crops, batched into one
onnxruntime run per padded width (src/ppocr_engine.py), as the capture thread
reads a frame. Each box has the settings ScoreSight gives a box of the crop's
field type, or of its role's preset when the dataset has roles
(ocr_eval.fields.box_settings: the defaults.py preset, minus the multi-frame
and output-formatting options); for PP-OCR they decide only the box's
character whitelist (its type), and its format regex sets the state.

Variants: accurate (PP-OCRv6 small) and fast (PP-OCRv6 tiny), the app's
"PP-OCR (accurate)" and "PP-OCR (fast)". "PP-OCR (automatic)" reads with one
of them depending on the computer's speed, so it isn't a variant. The models
are the app's: python scripts/fetch_models.py downloads them (the same pinned
revisions as ocr_eval/engines/ppocr.py's v6-small and v6-tiny), and the
predictions must equal ppocr's v6-small-wl and v6-tiny-wl crop for crop
(tests/test_ocr_eval_ppocr_scoresight.py; CI: .github/workflows/ocr-eval.yml).

The text of a prediction is the pipeline's reading (stripped, as the app
publishes it); info["state"] is the pipeline's verdict: Success, FailedFilter
(rejected by the box's format regex) or Empty.
"""

import importlib.metadata

import cv2
import numpy as np

from ocr_eval._src import isolate_app_state
from ocr_eval.engines import Engine, EngineUnavailable, Recognition
from ocr_eval.fields import box_name, box_settings

# Nothing beyond ScoreSight's own requirements.txt (onnxruntime, tesserocr,
# opencv, PySide6); the models come from scripts/fetch_models.py.
REQUIREMENTS: list[str] = []

# variant -> the app's model id (src/ppocr_engine.py)
MODEL_IDS = {"accurate": "ppocr:small", "fast": "ppocr:tiny"}
# the eval adapter's variant each one must match (ocr_eval/engines/ppocr.py)
MATCHES = {"accurate": "v6-small-wl", "fast": "v6-tiny-wl"}
# pixels between the crops of a frame
GAP = 8


def frame_of(crops: list[np.ndarray]) -> tuple[np.ndarray, list[tuple]]:
    """The crops side by side in one BGR frame (black elsewhere), and each
    crop's (x, y, width, height) in it."""
    height = max(crop.shape[0] for crop in crops)
    width = sum(crop.shape[1] for crop in crops) + GAP * (len(crops) + 1)
    frame = np.zeros((height + 2 * GAP, width, 3), np.uint8)
    rects = []
    x = GAP
    for crop in crops:
        h, w = crop.shape[:2]
        frame[GAP : GAP + h, x : x + w] = crop
        rects.append((x, GAP, w, h))
        x += w + GAP
    return frame, rects


class ScoreSightPPOCR(Engine):
    name = "ppocr-app"
    variants = tuple(MODEL_IDS)
    description = (
        "ScoreSight's PP-OCR engine (src/ppocr_engine.py) through its pipeline "
        "(src/tesseract.py TextDetector), a batch of crops read as one frame's "
        "boxes, with the default box settings of the crop's field type"
    )
    size = "PP-OCRv6 small 21 MB, tiny 4.5 MB"
    license = "Apache-2.0 (PP-OCRv6)"
    runtime = "onnxruntime (the app's 2 intra-op threads, no spinning), CPU"
    imports = ("onnxruntime", "tesserocr", "cv2", "PySide6")
    batch_size = 16
    reads_roles = True

    def __init__(self, variant: str | None = None):
        super().__init__(variant)
        self.model_id = MODEL_IDS[self.variant]
        self._detector = None
        self._target_class = None

    @classmethod
    def unavailable_reason(cls) -> str | None:
        reason = super().unavailable_reason()
        if reason:
            return reason
        isolate_app_state()
        import ppocr_engine

        for model_id in MODEL_IDS.values():
            reason = ppocr_engine.unavailable_reason(model_id)
            if reason:
                return reason
        return None

    def load(self) -> None:
        isolate_app_state()
        # ScoreSight's src/tesseract.py and text_detection_target.py
        from tesseract import TextDetector
        from text_detection_target import TextDetectionTarget

        detector = TextDetector(self.model_id)
        if detector.model != self.model_id or not detector.wait_for_engine(120):
            status = detector.engine_status()
            raise EngineUnavailable(
                f"{self.model_id} didn't load: {status.ppocr_error or status}"
            )
        self._detector = detector
        self._target_class = TextDetectionTarget

    def recognize(self, crops, field_types, roles=None):
        frame, rects = frame_of(crops)
        targets = [
            self._target_class(
                *rect,
                box_name(field_type, role),
                box_settings(field_type, role),
                [],
            )
            for rect, field_type, role in zip(
                rects, field_types, roles or [None] * len(crops)
            )
        ]
        # what the capture thread's to_gray() does to a BGR frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        results = self._detector.detect_multi_text(None, gray, targets, color=frame)
        recognitions = []
        for result in results:
            confidence = (result.extra or {}).get("confidence")
            recognitions.append(
                Recognition(
                    result.text,
                    None if confidence is None else round(confidence / 100.0, 4),
                    {"state": result.state.name},
                )
            )
        return recognitions

    def close(self) -> None:
        self._detector = None

    def info(self) -> dict:
        info = super().info()
        info["model"] = self.model_id
        info["matches"] = f"ppocr:{MATCHES[self.variant]}"
        try:
            info["version"] = f"onnxruntime {importlib.metadata.version('onnxruntime')}"
        except importlib.metadata.PackageNotFoundError:
            pass
        return info
