class FieldType:
    # Enum for the type of the field
    NUMBER = 0
    TIME = 1
    TEXT = 2


# The characters Tesseract may output for a box, by its field type (TEXT boxes
# use GENERAL_CHAR_WHITELIST). Here rather than in tesseract.py so tools such as
# the OCR evaluation harness (ocr_eval/) can apply them without importing
# Tesseract.
CHAR_WHITELISTS = {
    FieldType.NUMBER: "0123456789",
    FieldType.TIME: "0123456789:.",
}
GENERAL_CHAR_WHITELIST = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ .,;:!?-_()[]{}<>@#$%^&*+=|\\~`\"'"

# "When blank" (the box setting clear_value): what the outputs get once the box
# has been blank (or, with CLEAR_BLANK_OR_ZERO, has shown zero: 0, 00, 0:00)
# for CLEAR_AFTER_SECONDS: its last value (CLEAR_NEVER) or an empty value. In
# the order of comboBox_clearValue's items.
CLEAR_NEVER = "never"
CLEAR_BLANK = "blank"
CLEAR_BLANK_OR_ZERO = "blank_or_zero"
CLEAR_VALUES = (CLEAR_NEVER, CLEAR_BLANK, CLEAR_BLANK_OR_ZERO)
CLEAR_AFTER_SECONDS = 2.0


# 0 - Time MM:ss and ss.m
# 1 - Time MM:ss
# 2 - Time ss.m
# 3 - Time 0-59
# 4 - Shotclock 0-39
# 5 - Score 1dd
# 6 - Score ddd
# 7 - Period 1-4
# 8 - Period d
# 9 - Alphanumeric
# 10 - Any text
# 11 - Any number
# 12 - Time M:SS, M:SS.t and SS.t (tenths)
# 13 - Custom
format_prefixes = [
    "^(?:(?:[0-5]?\\d:[0-5]\\d)|(?:[0-5]?\\d\\.\\d))$",  # Time MM:ss and ss.m
    "^[0-5]?\\d:[0-5]\\d$",  # Time MM:ss
    "^[0-5]?\\d\\.\\d$",  # Time ss.m
    # one or two digits: clocks show 9, not 09 (up to 0.3.0 these took exactly
    # two; storage.migrate_boxes updates the boxes that stored those)
    "^[0-5]?\\d$",  # Time 0-59
    "^[0-3]?\\d$",  # Shotclock 0-39
    "^1?\\d{1,2}$",  # Score 1dd
    "^\\d{1,3}$",  # Score ddd
    "^[1-4]{1}$",  # Period 1-4
    "^\\d{1}$",  # Period d
    "^[A-Za-z0-9]*$",  # Alphanumeric
    "^.*$",  # Any text
    "^\\d*$",  # Any number
    # a clock in minutes and seconds with tenths: M:SS ("0:09"), M:SS.t
    # ("0:09.8") or SS.t ("9.8") - the last minute of a period, where boards
    # switch to tenths while the minutes go on showing
    "^(?:[0-5]?\\d:[0-5]\\d(?:\\.\\d)?|[0-5]?\\d\\.\\d)$",  # Time M:SS.t
    "^.*$",  # Custom
]


# --- picture levels (the source's black point, white point and gamma) -------------
# A source-level black point, white point and optional gamma, applied to every
# frame once it is rotated and cropped (camera_thread.TimerThread.adjust_frame),
# before stabilization and the four-corner correction: the preview, the binary
# view and the OCR all see the same picture. It suppresses what a dim LED or LCD
# display shows for the segments that are off (ghosting): raising the black
# point past them makes them black, and the white point brings the lit segments
# back to full white. Off by default, so nothing changes for existing settings.
PICTURE_LEVELS_ENABLED = "picture_levels"
PICTURE_BLACK_POINT = "picture_black_point"
PICTURE_WHITE_POINT = "picture_white_point"
PICTURE_GAMMA = "picture_gamma"

# The stored values' defaults and limits (a gray level of 0-255 each, a gamma
# above 0; 1.0 leaves the midtones alone). Stored next to the other global
# settings (video_settings.py, storage.store_data).
PICTURE_LEVELS_DEFAULTS = {
    PICTURE_LEVELS_ENABLED: False,
    PICTURE_BLACK_POINT: 0,
    PICTURE_WHITE_POINT: 255,
    PICTURE_GAMMA: 1.0,
}
MIN_PICTURE_GAMMA = 0.1
MAX_PICTURE_GAMMA = 10.0


def _clamp_gray_level(value, default: int, low: int, high: int) -> int:
    try:
        value = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return min(max(value, low), high)


def normalize_picture_levels(settings: dict | None) -> dict:
    """The canonical picture-level settings: every key present, the gray levels
    clamped to 0-255 with the white point above the black point, and the gamma
    within its limits. An unknown or unusable value falls back to its default."""
    settings = settings or {}
    enabled = settings.get(
        PICTURE_LEVELS_ENABLED, PICTURE_LEVELS_DEFAULTS[PICTURE_LEVELS_ENABLED]
    )
    black = _clamp_gray_level(
        settings.get(PICTURE_BLACK_POINT),
        PICTURE_LEVELS_DEFAULTS[PICTURE_BLACK_POINT],
        0,
        254,
    )
    white = _clamp_gray_level(
        settings.get(PICTURE_WHITE_POINT),
        PICTURE_LEVELS_DEFAULTS[PICTURE_WHITE_POINT],
        1,
        255,
    )
    if white <= black:
        # a black point at or above the white point would leave nothing: keep
        # the one gray level above the black point
        white = black + 1
    try:
        gamma = float(
            settings.get(PICTURE_GAMMA, PICTURE_LEVELS_DEFAULTS[PICTURE_GAMMA])
        )
    except (TypeError, ValueError):
        gamma = PICTURE_LEVELS_DEFAULTS[PICTURE_GAMMA]
    if not (MIN_PICTURE_GAMMA <= gamma <= MAX_PICTURE_GAMMA):
        gamma = PICTURE_LEVELS_DEFAULTS[PICTURE_GAMMA]
    return {
        PICTURE_LEVELS_ENABLED: bool(enabled),
        PICTURE_BLACK_POINT: black,
        PICTURE_WHITE_POINT: white,
        PICTURE_GAMMA: gamma,
    }


# Default values for the scoreboard
default_boxes = [
    {
        "name": "Home Score",
        "type": FieldType.NUMBER,
        "x": 0,
        "y": 0,
        "width": 120,
        "height": 100,
        "obs_source_name": "Home score",
        "format_regex": format_prefixes[5],
        "ordinal_indicator": False,
        "is_custom": False,
    },
    {
        "name": "Away Score",
        "type": FieldType.NUMBER,
        "x": 0,
        "y": 0,
        "width": 120,
        "height": 100,
        "obs_source_name": "Away score",
        "format_regex": format_prefixes[5],
        "ordinal_indicator": False,
        "is_custom": False,
    },
    {
        "name": "Time",
        "type": FieldType.TIME,
        "x": 0,
        "y": 0,
        "width": 170,
        "height": 100,
        "obs_source_name": "Clock",
        "format_regex": format_prefixes[0],
        "ordinal_indicator": False,
        "is_custom": False,
    },
    {
        "name": "Period",
        "type": FieldType.NUMBER,
        "x": 0,
        "y": 0,
        "width": 50,
        "height": 80,
        "obs_source_name": "Period",
        "format_regex": format_prefixes[7],
        "ordinal_indicator": True,
        "is_custom": False,
    },
    {
        "name": "Home Fouls",
        "type": FieldType.NUMBER,
        "x": 0,
        "y": 0,
        "width": 80,
        "height": 80,
        "obs_source_name": "#Home Fouls",
        "format_regex": format_prefixes[11],
        "ordinal_indicator": False,
        "is_custom": False,
    },
    {
        "name": "Away Fouls",
        "type": FieldType.NUMBER,
        "x": 0,
        "y": 0,
        "width": 80,
        "height": 80,
        "obs_source_name": "#Away Fouls",
        "format_regex": format_prefixes[11],
        "ordinal_indicator": False,
        "is_custom": False,
    },
    {
        "name": "Shot Clock",
        "type": FieldType.NUMBER,
        "x": 0,
        "y": 0,
        "width": 150,
        "height": 100,
        "obs_source_name": "shotclock",
        "format_regex": format_prefixes[4],
        "ordinal_indicator": False,
        "is_custom": False,
    },
]
default_custom_box_info = {
    "type": FieldType.NUMBER,
    "x": 0,
    "y": 0,
    "width": 150,
    "height": 100,
    "obs_source_name": "",
    "format_regex": format_prefixes[11],
    "ordinal_indicator": False,
    "is_custom": True,
}


def default_info_for_box_name(name):
    # Get the info for a box name
    for box in default_boxes:
        if box["name"] == name:
            return box
    return default_custom_box_info


def normalize_settings_dict(settings, box_info):
    # Normalize the settings dict with default values if they are not present
    if not settings:
        settings = {}
    if not box_info:
        box_info = {
            "obs_source_name": "",
            "format_regex": format_prefixes[11],
            "type": FieldType.NUMBER,
            "ordinal_indicator": False,
            "is_custom": True,
        }
    return {
        "is_custom": (
            settings["is_custom"] if "is_custom" in settings else box_info["is_custom"]
        ),
        "obs_source_name": (
            settings["obs_source_name"]
            if "obs_source_name" in settings
            else box_info["obs_source_name"]
        ),
        "format_regex": (
            settings["format_regex"]
            if "format_regex" in settings
            else box_info["format_regex"]
        ),
        "type": (settings["type"] if "type" in settings else box_info["type"]),
        "smoothing": (settings["smoothing"] if "smoothing" in settings else False),
        "clear_value": (
            settings["clear_value"]
            if settings.get("clear_value") in CLEAR_VALUES
            else CLEAR_NEVER
        ),
        # minimum Tesseract confidence, as a fraction (slider % / 100); 0 = off
        "conf_thresh": (settings["conf_thresh"] if "conf_thresh" in settings else 0.0),
        "cleanup_thresh": (
            settings["cleanup_thresh"] if "cleanup_thresh" in settings else 0
        ),
        "dilate": (settings["dilate"] if "dilate" in settings else 1),
        "skew": (settings["skew"] if "skew" in settings else 0),
        "vscale": (settings["vscale"] if "vscale" in settings else 10),
        "autocrop": (settings["autocrop"] if "autocrop" in settings else False),
        "skip_similar_image": (
            settings["skip_similar_image"]
            if "skip_similar_image" in settings
            else False
        ),
        "remove_leading_zeros": (
            settings["remove_leading_zeros"]
            if "remove_leading_zeros" in settings
            else False
        ),
        "rescale_patch": (
            settings["rescale_patch"] if "rescale_patch" in settings else True
        ),
        "normalize_wh_ratio": (
            settings["normalize_wh_ratio"]
            if "normalize_wh_ratio" in settings
            else False
        ),
        "invert_patch": (
            settings["invert_patch"] if "invert_patch" in settings else False
        ),
        "dot_detector": (
            settings["dot_detector"] if "dot_detector" in settings else False
        ),
        "binarization_method": (
            settings["binarization_method"] if "binarization_method" in settings else 0
        ),
        "ordinal_indicator": (
            settings["ordinal_indicator"]
            if "ordinal_indicator" in settings
            else box_info["ordinal_indicator"]
        ),
        "templatefield": (
            settings["templatefield"] if "templatefield" in settings else False
        ),
        "templatefield_text": (
            settings["templatefield_text"] if "templatefield_text" in settings else ""
        ),
        "composite_box": (
            settings["composite_box"] if "composite_box" in settings else False
        ),
    }
