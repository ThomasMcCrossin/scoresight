from collections import Counter, deque
from datetime import datetime
import enum

import numpy as np
from PySide6.QtCore import QRectF


def iso_datetime(value: datetime | None) -> str | None:
    """value as an ISO-8601 string with its UTC offset ("2026-10-23T09:10:22.500-03:00"),
    or None. A naive value is taken as local time and given an offset."""
    if value is None:
        return None
    try:
        if value.tzinfo is None:
            value = value.astimezone()
        return value.isoformat(timespec="milliseconds")
    except (OverflowError, OSError, ValueError):
        return None


def iso_from_timestamp(timestamp: float | None) -> str | None:
    """A wall-clock time.time() value as an ISO-8601 string with the local UTC
    offset, or None."""
    if timestamp is None:
        return None
    try:
        return (
            datetime.fromtimestamp(timestamp)
            .astimezone()
            .isoformat(timespec="milliseconds")
        )
    except (OverflowError, OSError, ValueError):
        return None


def captured_at_text(value) -> str | None:
    """The captured_at of a reading as served: an ISO-8601 string with its
    offset, or None."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return iso_datetime(value)
    return None


def latency_ms_value(value) -> float | None:
    """The latency_ms of a reading as served: milliseconds to one decimal, or
    None."""
    if value is None:
        return None
    try:
        return round(max(0.0, float(value)), 1)
    except (TypeError, ValueError):
        return None


class OCRResultPerCharacterSmoother:
    # This class is used to smooth the OCR results of a box over time.
    # It holds the last n accepted OCR results (strings) and returns the most
    # common one. Whole strings are compared, not characters, so a change in
    # the number of digits (9 -> 10) can't produce a mix of old and new digits.

    def __init__(self, max_history=5):
        self.max_history = max_history
        self.history: deque[str] = deque(maxlen=max_history)

    def get_smoothed_result(self, result: str) -> str:
        """Add result to the history and return the most common recent result.

        Ties go to the most recent value. An empty result (a failed read) is not
        added, so it can't come back as the output later.
        """
        if result:
            self.history.append(result)
        if not self.history:
            return result
        counts = Counter(self.history)
        best = None
        best_key = None
        for position, value in enumerate(self.history):
            key = (counts[value], position)
            if best_key is None or key > best_key:
                best, best_key = value, key
        return best

    def clear(self):
        self.history.clear()


class TextDetectionTarget(QRectF):
    # number of recent character width/height ratios used for normalize_wh_ratio
    WH_RATIO_WINDOW = 50

    def __init__(
        self,
        x,
        y,
        width,
        height,
        name: str,
        settings: dict | None = None,
        mini_rects: list[QRectF] | None = None,
    ):
        super().__init__(x, y, width, height)
        self.name = name
        self.settings = settings if settings is not None else {}
        self.ocrResultPerCharacterSmoother = OCRResultPerCharacterSmoother()
        self.last_image = None
        self.last_text = None
        # when the box started to be blank ("When blank", camera_thread)
        self.blank_since = None
        self.mini_rects: list[QRectF] = mini_rects if mini_rects is not None else []
        # Runtime OCR state for normalize_wh_ratio (not persisted): the recent
        # character width/height ratios and the settings they were measured with.
        self.wh_ratios: deque[float] = deque(maxlen=self.WH_RATIO_WINDOW)
        self.wh_ratios_key = None

    def median_wh_ratio(self, key) -> float | None:
        """The median of the recent character width/height ratios measured with
        the settings identified by key, or None if there are none yet. A
        different key (the box's preprocessing changed) starts over."""
        if key != self.wh_ratios_key:
            self.wh_ratios.clear()
            self.wh_ratios_key = key
        if not self.wh_ratios:
            return None
        return float(np.median(self.wh_ratios))

    def add_wh_ratios(self, key, ratios):
        if key != self.wh_ratios_key:
            self.wh_ratios.clear()
            self.wh_ratios_key = key
        self.wh_ratios.extend(ratios)


class TextDetectionTargetWithResult(TextDetectionTarget):
    class ResultState(enum.Enum):
        Success = 0
        FailedFilter = 1
        Empty = 2
        SameNoChange = 3

    def __init__(
        self,
        detection_target: TextDetectionTarget,
        result: str,
        result_state: ResultState,
        effectiveRect=None,
        extras=None,
        captured_at: datetime | None = None,
        latency_ms: float | None = None,
    ):
        super().__init__(
            detection_target.x(),
            detection_target.y(),
            detection_target.width(),
            detection_target.height(),
            detection_target.name,
            detection_target.settings,
        )
        self.result = result
        self.result_state = result_state
        self.effectiveRect = effectiveRect
        self.extras = extras
        # When the frame these readings came from was captured (wall clock, so
        # it can be compared with another program's timestamps) and how long
        # from reading it to publishing these readings. None when the caller
        # doesn't know (results made outside a capture cycle).
        self.captured_at = captured_at
        self.latency_ms = latency_ms

    def to_dict(self):
        return {
            "name": self.name,
            "text": self.result,
            "state": self.result_state.name,
            "rect": {
                "x": self.x(),
                "y": self.y(),
                "width": self.width(),
                "height": self.height(),
            },
            "captured_at": captured_at_text(self.captured_at),
            "latency_ms": latency_ms_value(self.latency_ms),
        }


class TextDetectionResult:
    def __init__(
        self,
        text: str,
        state: TextDetectionTargetWithResult.ResultState,
        rect: QRectF | None = None,
        extra=None,
        *,
        unchanged_image: bool = False,
    ):
        self.text = text
        self.state = state
        self.rect = rect
        self.extra = extra
        # The OCR was skipped because the box's image hasn't changed since its
        # last OCR (skip_similar_image). There is no text; the capture thread
        # reports the box's last good reading as SameNoChange instead.
        self.unchanged_image = unchanged_image
