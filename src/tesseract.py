from defaults import FieldType
from os import path
from PIL import Image
from PySide6.QtCore import QRectF
from tesserocr import PyTessBaseAPI, RIL, iterate_level
from threading import Lock
import cv2
import numpy as np
import re
import time

from resource_path import resource_path
from storage import fetch_data
from text_detection_target import (
    TextDetectionResult,
    TextDetectionTarget,
    TextDetectionTargetWithResult,
)
from sc_logging import logger

ResultState = TextDetectionTargetWithResult.ResultState

CHAR_WHITELISTS = {
    FieldType.NUMBER: "0123456789",
    FieldType.TIME: "0123456789:.",
}
GENERAL_CHAR_WHITELIST = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ .,;:!?-_()[]{}<>@#$%^&*+=|\\~`\"'"

# skip_similar_image: a patch is "similar" to the last one that was read (and
# accepted) when fewer than this fraction of its foreground (text) pixels changed.
SIMILAR_PATCH_MAX_CHANGE = 0.02

# The same box failing on every frame is logged at most this often.
_BOX_ERROR_LOG_INTERVAL_S = 10.0


def autocrop(image_in):
    image = image_in.copy()
    # check if this image is black-on-white or white-on-black by looking at the first few pixels
    if np.sum(image[0:5, 0:5]) > 0:
        # black-on-white
        # invert the image
        image = 255 - image

    # find the first row that has a pixel
    first_row = 0
    for row in range(image.shape[0]):
        if np.sum(image[row, :]) > 0:
            first_row = row
            break
    # find the last row that has a pixel
    last_row = image.shape[0] - 1
    for row in range(image.shape[0] - 1, -1, -1):
        if np.sum(image[row, :]) > 0:
            last_row = row
            break
    # find the first column that has a pixel
    first_col = 0
    for col in range(image.shape[1]):
        if np.sum(image[:, col]) > 0:
            first_col = col
            break
    # find the last column that has a pixel
    last_col = image.shape[1] - 1
    for col in range(image.shape[1] - 1, -1, -1):
        if np.sum(image[:, col]) > 0:
            last_col = col
            break
    # leave a 10 pixel border on each side
    first_row = max(0, first_row - 10)
    last_row = min(image.shape[0] - 1, last_row + 10)
    first_col = max(0, first_col - 10)
    last_col = min(image.shape[1] - 1, last_col + 10)
    return image_in[first_row:last_row, first_col:last_col], (
        first_row,
        last_row,
        first_col,
        last_col,
    )


def add_ordinal_indicator(text):
    if text == "":
        return ""
    if text.endswith("1") and text != "11":
        return text + "st"
    elif text.endswith("2") and text != "12":
        return text + "nd"
    elif text.endswith("3") and text != "13":
        return text + "rd"
    else:
        return text + "th"


def is_valid_regex(pattern):
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


def _is_image(image) -> bool:
    return (
        isinstance(image, np.ndarray)
        and image.ndim >= 2
        and image.shape[0] >= 1
        and image.shape[1] >= 1
    )


def global_binarization(gray):
    """The whole-frame Otsu binarization used by boxes with GLOBAL binarization."""
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    return binary


def clamp_rect_to_image(rect: QRectF, width: int, height: int):
    """The pixel bounds (x0, y0, x1, y1) of the part of rect inside a width x
    height image, or None if less than a pixel of it is inside. rect itself is
    not changed: boxes are the user's settings, shared with the UI."""
    x0 = max(0, int(rect.x()))
    y0 = max(0, int(rect.y()))
    x1 = min(width, int(rect.x() + rect.width()))
    y1 = min(height, int(rect.y() + rect.height()))
    if x1 - x0 < 1 or y1 - y0 < 1:
        return None
    return x0, y0, x1, y1


def has_foreground(patch) -> bool:
    """False if every pixel of the patch has the same value, e.g. a binarized
    box over plain background: there is nothing to read, and the scoreboard
    models tend to hallucinate digits on such patches."""
    return patch.size > 0 and int(patch.min()) != int(patch.max())


def _foreground_pixels(patch) -> int:
    # The text is the minority class, whether it is white-on-black or black-on-white.
    bright = int(np.count_nonzero(patch > 127))
    return min(bright, patch.size - bright)


def patches_similar(previous, current, max_change=SIMILAR_PATCH_MAX_CHANGE) -> bool:
    """True if current differs from previous on fewer than max_change of the
    foreground pixels. Measuring against the foreground (not the whole patch
    area) keeps a one-digit change from being dismissed as noise."""
    if previous is None or previous.shape != current.shape:
        return False
    changed = int(np.count_nonzero(cv2.absdiff(previous, current) > 64))
    if changed == 0:
        return True
    foreground = max(1, _foreground_pixels(previous), _foreground_pixels(current))
    return changed / foreground < max_change


def _vertical_scale(patch, vscale):
    # Scale the patch vertically about its center, keeping its size. vscale is
    # in [1, 10], where 10 is 1:1.
    rows, cols = patch.shape[:2]
    target_height = max(1, min(rows, int(rows * (vscale / 10.0))))
    if rows < 2 or target_height == rows:
        return patch
    scaled = cv2.resize(patch, (cols, target_height), interpolation=cv2.INTER_LINEAR)
    pad_top = (rows - target_height) // 2
    pad_bottom = rows - target_height - pad_top
    return cv2.copyMakeBorder(scaled, pad_top, pad_bottom, 0, 0, cv2.BORDER_REPLICATE)


def preprocess_patch(settings: dict, roi, gray, get_binary):
    """Cut the box's ROI out of the frame and apply its binarization, cleanup,
    vertical scale, skew and dilation. Returns a new array the size of the ROI;
    the frame images are never modified, so overlapping boxes don't affect each
    other. get_binary() returns the frame's global binarization."""
    x0, y0, x1, y1 = roi
    method = settings.get("binarization_method", TextDetector.BinarizationMethod.GLOBAL)
    if method == TextDetector.BinarizationMethod.NO_BINARIZATION:
        patch = gray[y0:y1, x0:x1].copy()
    elif method == TextDetector.BinarizationMethod.LOCAL:
        # local binarization using Otsu's method
        _, patch = cv2.threshold(
            gray[y0:y1, x0:x1], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
    elif method == TextDetector.BinarizationMethod.ADAPTIVE:
        patch = cv2.adaptiveThreshold(
            gray[y0:y1, x0:x1],
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            # use a fraction of the patch area
            max(int((x1 - x0) * (y1 - y0) * 0.01), 3) | 1,
            2,
        )
    else:
        patch = get_binary()[y0:y1, x0:x1].copy()

    cleanup_thresh = settings.get("cleanup_thresh", 0) or 0
    if cleanup_thresh > 0:
        # cleanup image from small components: find contours and remove small ones
        contours, _ = cv2.findContours(
            patch, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        # cleanup_thresh is [0, 1.0], convert to [0, 0.05]
        img_area_thresh = patch.shape[0] * patch.shape[1] * cleanup_thresh * 0.05
        for contour in contours:
            if cv2.contourArea(contour) < img_area_thresh:
                cv2.drawContours(patch, [contour], 0, 0, -1)

    vscale = settings.get("vscale", 10)
    if vscale is not None and vscale != 10:
        patch = _vertical_scale(patch, vscale)

    skew = settings.get("skew", 0)
    if skew:
        # skew the image in the x direction about the center
        rows, cols = patch.shape[:2]
        M = np.float32([[1, skew / 40.0, 0], [0, 1, 0]])
        try:
            patch = cv2.warpAffine(patch, M, (cols, rows))
        except cv2.error:
            pass

    dilate = int(settings.get("dilate", 0) or 0)
    if dilate > 0:
        patch = cv2.dilate(patch, np.ones((3, 3), np.uint8), iterations=dilate)

    return patch


def _draw_patch(display, roi, patch):
    x0, y0, x1, y1 = roi
    if display is not None and patch.shape[:2] == (y1 - y0, x1 - x0):
        display[y0:y1, x0:x1] = patch


def render_binary_view(binary, gray, rects: list[TextDetectionTarget]):
    """A copy of the frame's global binarization with each box's preprocessed
    patch drawn in, i.e. what the OCR sees (the "binary" preview)."""
    display = binary.copy()
    height, width = display.shape[:2]
    for rect in rects:
        if rect is None:
            continue
        roi = clamp_rect_to_image(rect, width, height)
        if roi is None:
            continue
        try:
            patch = preprocess_patch(rect.settings or {}, roi, gray, lambda: binary)
        except cv2.error:
            continue
        _draw_patch(display, roi, patch)
    return display


def _empty_result(rect=None):
    return TextDetectionResult("", ResultState.Empty, rect)


def _wh_ratio_key(settings: dict):
    # character width/height ratios depend on these settings; when one of them
    # changes the measured ratios are discarded
    return tuple(
        settings.get(key)
        for key in ("binarization_method", "vscale", "skew", "dilate", "autocrop")
    )


def _conf_threshold_percent(conf_thresh) -> float:
    # conf_thresh is stored as a fraction (the box settings slider / 100);
    # Tesseract's confidences are percentages. A value above 1 can only be a
    # percentage already (e.g. a hand-edited settings file).
    value = float(conf_thresh)
    return value if value > 1.0 else value * 100.0


def text_confidence(mean_text_conf: int, symbol_confidences: list[float]) -> float:
    """The read's confidence in percent: Tesseract's MeanTextConf(). That word
    level confidence bottoms out at 0 on some reads whose characters were all
    recognized with high confidence (seen with the bundled scoreboard models and
    eng), so a 0 falls back to the mean per-character confidence."""
    if mean_text_conf > 0 or not symbol_confidences:
        return float(mean_text_conf)
    return float(sum(symbol_confidences) / len(symbol_confidences))


class TextDetector:
    # model name enum: daktronics=0, scoreboard_general=1
    class OcrModelIndex:
        DAKTRONICS = 0
        SCOREBOARD_GENERAL = 1
        GENERAL_ENGLISH = 2
        SCOREBOARD_GENERAL_LARGE = 3

    class BinarizationMethod:
        GLOBAL = 0
        NO_BINARIZATION = 1
        LOCAL = 2
        ADAPTIVE = 3

    def __init__(self):
        # Guards self.api. The whole Tesseract sequence for a box (SetImage,
        # whitelist, GetUTF8Text, iterator, MeanTextConf) runs under it, and
        # setOcrModel swaps the API under it, so a model change from the GUI
        # thread can't land in the middle of a recognition on the OCR thread.
        self.api_lock = Lock()
        self.api = None
        self._box_error_log_times: dict[str, float] = {}
        self._warned_no_api = False
        stored_model = fetch_data(
            "scoresight.json",
            "ocr_model",
            TextDetector.OcrModelIndex.SCOREBOARD_GENERAL,
        )
        if (
            not self.setOcrModel(stored_model)
            and stored_model != TextDetector.OcrModelIndex.SCOREBOARD_GENERAL
        ):
            self.setOcrModel(TextDetector.OcrModelIndex.SCOREBOARD_GENERAL)

    @staticmethod
    def _resolve_model(ocrModelIndex):
        # (tessdata folder, model name) for a model index or a .traineddata path
        model_folder = resource_path("tesseract", "tessdata")
        if ocrModelIndex == TextDetector.OcrModelIndex.DAKTRONICS:
            return model_folder, "daktronics"
        if ocrModelIndex == TextDetector.OcrModelIndex.SCOREBOARD_GENERAL:
            return model_folder, "scoreboard_general"
        if ocrModelIndex == TextDetector.OcrModelIndex.GENERAL_ENGLISH:
            return model_folder, "eng"
        if ocrModelIndex == TextDetector.OcrModelIndex.SCOREBOARD_GENERAL_LARGE:
            return model_folder, "scoreboard_general_large"
        if isinstance(ocrModelIndex, str) and path.exists(ocrModelIndex):
            # Take the folder as the tessdata folder and the model name without
            # extension as the "language"
            return (
                path.dirname(ocrModelIndex),
                path.splitext(path.basename(ocrModelIndex))[0],
            )
        return None

    def setOcrModel(self, ocrModelIndex: OcrModelIndex | int | str | None = None):
        """Load an OCR model (a model index or a .traineddata path). Returns True
        on success; on failure the current model stays in use."""
        resolved = self._resolve_model(ocrModelIndex)
        if resolved is None:
            if ocrModelIndex is not None:
                logger.warning("Unknown OCR model: %r", ocrModelIndex)
            return False
        model_folder, ocr_model = resolved

        logger.info(f"Setting OCR model to {ocr_model} from {model_folder}")

        # Build the new API before taking the lock, so OCR isn't held up while
        # the model loads, and so a model that fails to load (e.g. an invalid
        # custom .traineddata) leaves the current one in place.
        try:
            api = PyTessBaseAPI(path=model_folder, lang=ocr_model)
            # single word PSM
            api.SetPageSegMode(8)
            api.SetVariable("load_system_dawg", "F")
            api.SetVariable("load_freq_dawg", "F")
        except Exception:
            logger.exception(
                "Unable to load OCR model %s from %s; keeping the current model",
                ocr_model,
                model_folder,
            )
            return False

        with self.api_lock:
            old_api, self.api = self.api, api
            if old_api is not None:
                old_api.End()
        self._warned_no_api = False
        return True

    def detect_text(self, image):
        if image is None:
            return ""
        if not isinstance(image, np.ndarray):
            return ""
        # check the image has rows and columns
        if len(image.shape) < 2 or image.shape[0] < 1 or image.shape[1] < 1:
            return ""
        pilimage = Image.fromarray(image)
        text = ""
        with self.api_lock:
            if self.api is None:
                return ""
            self.api.SetImage(pilimage)
            text = self.api.GetUTF8Text()
        return text.strip()

    def detect_multi_text(
        self, binary, gray, rects: list[TextDetectionTarget], display=None
    ) -> list[TextDetectionResult]:
        """OCR each box in rects and return one result per box, in order.

        binary is the frame's global (Otsu) binarization, or None to compute it
        only if a box uses GLOBAL binarization; gray is the grayscale frame.
        Neither image nor the boxes' geometry is modified; a box partly outside
        the frame is read from the part inside it. If display is given (e.g. a
        copy of binary), each box's preprocessed patch is drawn into it.
        """
        frame = gray if _is_image(gray) else binary
        if not _is_image(frame):
            return []
        if not _is_image(gray):
            gray = frame
        height, width = frame.shape[:2]

        global_binary = binary if _is_image(binary) else None

        def get_binary():
            nonlocal global_binary
            if global_binary is None:
                global_binary = global_binarization(gray)
            return global_binary

        texts = []
        for rect in rects:
            try:
                texts.append(
                    self._detect_box(rect, gray, get_binary, width, height, display)
                )
            except Exception:
                self._log_box_error(rect)
                texts.append(_empty_result())
        return texts

    def _log_box_error(self, rect):
        # called from an except block
        name = getattr(rect, "name", None)
        now = time.monotonic()
        last = self._box_error_log_times.get(name)
        if last is None or now - last >= _BOX_ERROR_LOG_INTERVAL_S:
            self._box_error_log_times[name] = now
            logger.exception("OCR failed for box %r", name)

    def _detect_box(self, rect, gray, get_binary, width, height, display):
        if rect is None:
            return _empty_result()
        # read the settings and geometry once: the GUI thread may replace them
        settings = rect.settings or {}
        roi = clamp_rect_to_image(rect, width, height)
        if roi is None:
            return _empty_result()

        patch = preprocess_patch(settings, roi, gray, get_binary)
        _draw_patch(display, roi, patch)

        # where the patch starts relative to the box (non-zero if the box sticks
        # out of the frame at the top or left); results are box-relative
        origin_x = roi[0] - int(rect.x())
        origin_y = roi[1] - int(rect.y())
        return self._recognize(rect, settings, patch, origin_x, origin_y)

    def _recognize(self, rect, settings, patch, origin_x, origin_y):
        effectiveRect = None
        scale_x = 1.0
        scale_y = 1.0

        if settings.get("invert_patch"):
            # invert the image
            patch = 255 - patch

        dot_detector = bool(settings.get("dot_detector"))
        if not has_foreground(patch):
            # a blank box (every pixel the same): nothing to read and no lit dot
            # to count. Counting contours would find one (the whole patch) when
            # it is all white, which uniform areas become with Local or Adaptive
            # binarization.
            if not dot_detector:
                return _empty_result()
            if settings.get("skip_similar_image"):
                # "0" is the box's new accepted read: compare with its image
                rect.last_image = patch.copy()
            return TextDetectionResult("0", ResultState.Success, None)

        # skip_similar_image: the patch to remember if this read is accepted
        skip_patch = None
        if settings.get("skip_similar_image"):
            # Compare with the image of the last accepted (Success) read. It isn't
            # refreshed on skips, so slow changes add up until they are read, nor
            # on rejected or empty reads, so that a new value whose first read
            # failed is read again instead of the box keeping its last value.
            if patches_similar(rect.last_image, patch):
                return TextDetectionResult(
                    "", ResultState.SameNoChange, None, unchanged_image=True
                )
            skip_patch = patch

        if settings.get("autocrop"):
            # auto crop the binary image around the text
            patch, (first_row, last_row, first_col, last_col) = autocrop(patch)
            effectiveRect = QRectF(
                first_col + origin_x,
                first_row + origin_y,
                last_col - first_col,
                last_row - first_row,
            )

        # check if image is size 0
        if patch.shape[0] == 0 or patch.shape[1] == 0:
            return _empty_result(effectiveRect)

        if settings.get("rescale_patch"):
            # rescale the image to 35 pixels height
            scale_x = 35 / patch.shape[0]
            scale_y = scale_x

        normalize_wh_ratio = bool(settings.get("normalize_wh_ratio"))
        wh_key = _wh_ratio_key(settings)
        if normalize_wh_ratio:
            median_wh_ratio = rect.median_wh_ratio(wh_key)
            if median_wh_ratio is not None and median_wh_ratio > 0:
                # rescale the image in x such that the width-to-height ratio is 0.5
                scale_x *= 0.5 / median_wh_ratio

        if scale_x != 1.0 or scale_y != 1.0:
            patch = cv2.resize(
                patch,
                None,
                fx=scale_x,
                fy=scale_y,
                interpolation=cv2.INTER_AREA,
            )

        # if dot detector count the blobs in the patch
        if dot_detector:
            contours, _ = cv2.findContours(
                patch, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            count = sum(1 for contour in contours if cv2.contourArea(contour) > 5)
            if skip_patch is not None:
                rect.last_image = skip_patch.copy()
            return TextDetectionResult(str(count), ResultState.Success, effectiveRect)

        if patch.shape[0] == 0 or patch.shape[1] == 0:
            return _empty_result(effectiveRect)

        whitelist = CHAR_WHITELISTS.get(settings.get("type"), GENERAL_CHAR_WHITELIST)
        want_confidence = settings.get("conf_thresh") is not None
        pilimage = Image.fromarray(patch)

        text = ""
        extras = {}
        wh_ratios = []
        symbol_confidences = []
        mean_conf = 0
        with self.api_lock:
            api = self.api
            if api is None:
                if not self._warned_no_api:
                    self._warned_no_api = True
                    logger.error("No OCR model is loaded; boxes can't be read")
                return _empty_result(effectiveRect)
            api.SetImage(pilimage)
            api.SetVariable("tessedit_char_whitelist", whitelist)
            text = api.GetUTF8Text().strip()
            if text != "":
                # get the per-character boxes using an iterator with RIL_SYMBOL level
                extras["boxes"] = []
                it = api.GetIterator()
                symbols = iterate_level(it, RIL.SYMBOL) if it is not None else []
                for w in symbols:
                    char = w.GetUTF8Text(RIL.SYMBOL)
                    box_tuple = w.BoundingBox(RIL.SYMBOL)
                    if (
                        box_tuple is None
                        or char is None
                        or char == ""
                        or len(box_tuple) != 4
                    ):
                        continue
                    symbol_confidences.append(w.Confidence(RIL.SYMBOL))
                    box = {
                        "x": box_tuple[0],
                        "y": box_tuple[1],
                        "w": box_tuple[2] - box_tuple[0],
                        "h": box_tuple[3] - box_tuple[1],
                    }
                    # box is a dict with x, y, w and h
                    if scale_x != 1.0 or scale_y != 1.0:
                        box["x"] = int(box["x"] / scale_x)
                        box["y"] = int(box["y"] / scale_y)
                        box["w"] = int(box["w"] / scale_x)
                        box["h"] = int(box["h"] / scale_y)
                    if effectiveRect is not None:
                        box["x"] = int(box["x"] + effectiveRect.x())
                        box["y"] = int(box["y"] + effectiveRect.y())
                    else:
                        box["x"] = int(box["x"] + origin_x)
                        box["y"] = int(box["y"] + origin_y)
                    extras["boxes"].append(box)
                    # if char is a "wide character" (like 0,2,3,4,5,6,7,8,9), add the width-to-height ratio
                    if char in "023456789" and box["h"] > 0:
                        wh_ratios.append(box["w"] / box["h"])
                if want_confidence:
                    mean_conf = api.MeanTextConf()

        textstate = ResultState.Success
        format_regex = settings.get("format_regex")
        if format_regex is not None and is_valid_regex(format_regex):
            # check the text matches the regex fully
            if not re.fullmatch(format_regex, text):
                textstate = ResultState.FailedFilter
        if want_confidence and text != "":
            confidence = text_confidence(mean_conf, symbol_confidences)
            if confidence < _conf_threshold_percent(settings["conf_thresh"]):
                textstate = ResultState.FailedFilter

        if normalize_wh_ratio and textstate == ResultState.Success and wh_ratios:
            rect.add_wh_ratios(wh_key, wh_ratios)

        if settings.get("smoothing") and textstate == ResultState.Success:
            # only accepted reads go into the smoothing history
            text = rect.ocrResultPerCharacterSmoother.get_smoothed_result(text) or ""
        if settings.get("remove_leading_zeros") and text != "":
            # remove leading zeros ("00" -> "0"); a failed read stays empty
            text = text.lstrip("0") or "0"
        if settings.get("ordinal_indicator"):
            # add ordinal indicator
            text = add_ordinal_indicator(text)

        if text == "":
            textstate = ResultState.Empty

        if skip_patch is not None and textstate == ResultState.Success:
            rect.last_image = skip_patch.copy()

        return TextDetectionResult(text, textstate, effectiveRect, extras)
