"""Picture levels (src/defaults.py, src/camera_thread.py): the source-level
black point, white point and gamma applied in adjust_frame, and the ghosting
they suppress on a dim LED display."""

import cv2
import numpy as np
import pytest

pytest.importorskip("tesserocr")  # camera_thread imports the OCR pipeline

import camera_thread  # noqa: E402
from camera_info import CameraInfo  # noqa: E402
from camera_thread import (  # noqa: E402
    PictureLevels,
    TimerThread,
    apply_picture_levels,
    picture_levels_lut,
)
from defaults import (  # noqa: E402
    PICTURE_BLACK_POINT,
    PICTURE_GAMMA,
    PICTURE_LEVELS_ENABLED,
    PICTURE_WHITE_POINT,
    normalize_picture_levels,
)
from storage import store_data  # noqa: E402
from synthetic_images import ghosted_display, seven_segment  # noqa: E402
from text_detection_target import TextDetectionResult  # noqa: E402

# --- the lookup table -------------------------------------------------------------


def test_default_levels_leave_every_gray_level_alone():
    levels = normalize_picture_levels({})
    assert levels == {
        PICTURE_LEVELS_ENABLED: False,
        PICTURE_BLACK_POINT: 0,
        PICTURE_WHITE_POINT: 255,
        PICTURE_GAMMA: 1.0,
    }
    lut = picture_levels_lut(levels[PICTURE_BLACK_POINT], levels[PICTURE_WHITE_POINT])
    assert list(lut) == list(range(256))


@pytest.mark.parametrize(
    "black_point, white_point, level, expected",
    [
        # below the black point: black
        (150, 221, 149, 0),
        # at the black point: black
        (150, 221, 150, 0),
        # at the white point and above: white
        (150, 221, 221, 255),
        (150, 221, 255, 255),
        # between: stretched over the whole range ((level - black) * 255 / span)
        (150, 221, 186, 129),  # 36 * 255 / 71 = 129.3
    ],
)
def test_levels_stretch_the_black_to_white_range(
    black_point, white_point, level, expected
):
    lut = picture_levels_lut(black_point, white_point)
    assert int(lut[level]) == expected


def test_a_gamma_above_one_brightens_the_midtones():
    plain = picture_levels_lut(0, 255)
    bright = picture_levels_lut(0, 255, gamma=2.0)
    dark = picture_levels_lut(0, 255, gamma=0.5)
    assert bright[128] > plain[128] > dark[128]
    # the ends don't move: a gamma only shapes the midtones
    for lut in (bright, dark):
        assert lut[0] == 0
        assert lut[255] == 255


def test_the_lut_never_goes_down_and_the_white_point_stays_above_the_black():
    lut = picture_levels_lut(250, 10)  # a white point below the black point
    assert all(int(a) <= int(b) for a, b in zip(lut, lut[1:]))
    assert lut[250] == 0 and lut[255] == 255


@pytest.mark.parametrize(
    "settings, expected",
    [
        ({PICTURE_BLACK_POINT: -5, PICTURE_WHITE_POINT: 999}, (0, 255)),
        ({PICTURE_BLACK_POINT: 200, PICTURE_WHITE_POINT: 180}, (200, 201)),
        ({PICTURE_GAMMA: 0}, (0, 255, 1.0)),
        ({PICTURE_GAMMA: "1.8"}, (0, 255, 1.8)),
        ({PICTURE_GAMMA: None}, (0, 255, 1.0)),
    ],
)
def test_normalize_clamps_the_levels(settings, expected):
    levels = normalize_picture_levels(settings)
    assert levels[PICTURE_BLACK_POINT] == expected[0]
    assert levels[PICTURE_WHITE_POINT] == expected[1]
    if len(expected) > 2:
        assert levels[PICTURE_GAMMA] == expected[2]


def test_levels_apply_to_every_channel_of_a_colour_frame():
    frame = np.dstack(
        [
            np.full((4, 4), 160, np.uint8),
            np.full((4, 4), 200, np.uint8),
            np.full((4, 4), 255, np.uint8),
        ]
    )
    leveled = apply_picture_levels(frame, picture_levels_lut(150, 221))
    assert tuple(leveled[0, 0]) == (36, 180, 255)


def test_no_levels_change_nothing():
    frame = np.arange(64, dtype=np.uint8).reshape(8, 8)
    assert apply_picture_levels(frame, None) is frame


# --- the settings the capture thread follows --------------------------------------


def store_levels(**settings):
    defaults = normalize_picture_levels({})
    defaults.update(settings)
    for name, value in defaults.items():
        store_data("scoresight.json", name, value)


def test_levels_are_off_by_default():
    levels = PictureLevels()
    try:
        assert levels.lut is None
    finally:
        levels.close()


def test_levels_follow_the_stored_settings():
    store_levels(
        **{
            PICTURE_LEVELS_ENABLED: True,
            PICTURE_BLACK_POINT: 150,
            PICTURE_WHITE_POINT: 221,
        }
    )
    levels = PictureLevels()
    try:
        assert levels.lut is not None
        assert int(levels.lut[150]) == 0
        assert int(levels.lut[221]) == 255
        # and a change while the capture runs
        store_data("scoresight.json", PICTURE_LEVELS_ENABLED, False)
        assert levels.lut is None
    finally:
        levels.close()


# --- the capture thread -------------------------------------------------------------


class FakeDetector:
    """Stands in for TextDetector: records the frames it is given and reads
    each box as its name."""

    def __init__(self):
        self.grays = []

    def detect_multi_text(self, binary, gray, rects, display=None, color=None):
        self.grays.append(gray.copy())
        return [
            TextDetectionResult(rect.name, camera_thread.ResultState.Success)
            for rect in rects
        ]


@pytest.fixture
def make_thread(memory_storage, make_target):
    """A TimerThread that isn't started, reading one box with a fake clock."""
    threads = []

    def _make():
        store_data("scoresight.json", "detection_cadence", 10)
        thread = TimerThread(
            CameraInfo("test", "test", "x", CameraInfo.CameraType.FILE),
            memory_storage,
        )
        thread.textDetector = FakeDetector()
        thread.previews, thread.results = [], []
        thread.update_signal.connect(thread.previews.append)
        thread.ocr_result_signal.connect(thread.results.append)
        memory_storage.add_item(make_target("Home Score", rect=(0, 0, 40, 30)))
        thread.frame_interval = 0
        threads.append(thread)
        return thread

    yield _make
    for thread in threads:
        thread.cleanup()


def test_adjust_frame_applies_the_levels_after_the_crop():
    store_levels(
        **{
            PICTURE_LEVELS_ENABLED: True,
            PICTURE_BLACK_POINT: 150,
            PICTURE_WHITE_POINT: 221,
        }
    )
    store_data("scoresight.json", "crop_mode", True)
    store_data("scoresight.json", "top_crop", 10)
    thread = None
    try:
        thread = TimerThread(
            CameraInfo("test", "test", "x", CameraInfo.CameraType.FILE), None
        )
        frame = np.full((40, 60, 3), 150, np.uint8)
        adjusted = thread.adjust_frame(frame)
        # cropped by 10 rows, then leveled: nothing is left of the ghost
        assert adjusted.shape[:2] == (30, 60)
        assert int(adjusted.max()) == 0
    finally:
        if thread is not None:
            thread.cleanup()


def test_the_ocr_and_the_preview_see_the_leveled_picture(make_thread):
    store_levels(
        **{
            PICTURE_LEVELS_ENABLED: True,
            PICTURE_BLACK_POINT: 150,
            PICTURE_WHITE_POINT: 221,
        }
    )
    thread = make_thread()
    frame = np.full((40, 60, 3), 120, np.uint8)
    thread.process_frame(frame)
    thread.process_frame(frame)  # the first one is only the first preview
    read = thread.textDetector.grays[-1]
    assert int(read.max()) == 0, "the OCR still sees the ghost"
    preview = thread.previews[-1]
    assert int(preview.max()) == 0, "the preview still shows the ghost"


def test_without_the_levels_the_picture_is_untouched(make_thread):
    thread = make_thread()
    frame = np.full((40, 60, 3), 120, np.uint8)
    thread.process_frame(frame)
    thread.process_frame(frame)
    assert int(thread.textDetector.grays[-1].max()) == 120
    assert int(thread.previews[-1].max()) == 120


# --- the ghosting a dim display leaves on a 7-segment board ------------------------


def read_with_ppocr(gray):
    """What the app's PP-OCR (accurate) reads of a gray image, as a whole
    frame whose only box covers it. None without the models (the marker
    skips the test)."""
    from defaults import default_info_for_box_name, normalize_settings_dict
    from tesseract import TextDetector
    from text_detection_target import TextDetectionTarget

    height, width = gray.shape[:2]
    target = TextDetectionTarget(
        0,
        0,
        width,
        height,
        "Home Score",
        normalize_settings_dict({}, default_info_for_box_name("Home Score")),
        [],
    )
    detector = TextDetector()
    try:
        detector.setOcrModel("ppocr:small")
        assert detector.wait_for_engine(120), "the PP-OCR model did not load"
        color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        results = detector.detect_multi_text(None, gray, [target], color=color)
        return results[0].text
    finally:
        if detector.api is not None:
            detector.api.End()
            detector.api = None


@pytest.mark.ppocr
def test_the_levels_suppress_the_ghost_of_a_dim_seven_segment_display():
    """The board shows 0 but still glows the 8 of an earlier 80 in the cell to
    its left: the ghost reads as another digit without the levels (the board
    reads 80) and is gone with them (it reads 0). This is the reading our
    canteen board gave: a guest score of 0 read as 80."""
    ghosted = ghosted_display("0", "80", height=72, ghost_gray=60)
    assert read_with_ppocr(ghosted) == "80"
    leveled = apply_picture_levels(ghosted, picture_levels_lut(150, 221))
    assert read_with_ppocr(leveled) == "0"


@pytest.mark.ppocr
def test_the_levels_keep_a_plain_digit_readable():
    """A level change doesn't cost a clean reading: a bright digit on a dark
    background still reads after them."""
    plain = np.hstack([seven_segment("7", height=72, fg=225, bg=0)])
    leveled = apply_picture_levels(plain, picture_levels_lut(150, 221))
    assert read_with_ppocr(plain) == "7"
    assert read_with_ppocr(leveled) == "7"
