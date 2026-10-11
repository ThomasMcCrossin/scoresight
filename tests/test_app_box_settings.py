"""The Box tab's helpers (box_settings_ui_handler): the format preset that
matches an expression, invalid expressions and the changed settings."""

import pytest

from box_settings_ui_handler import (
    CUSTOM_PRESET_INDEX,
    IMAGE_CLEANUP_SETTINGS,
    changed_settings,
    matching_preset,
    regex_error,
)
from defaults import (
    default_info_for_box_name,
    format_prefixes,
    normalize_settings_dict,
)


def test_every_preset_matches_itself():
    for index, preset in enumerate(format_prefixes[:CUSTOM_PRESET_INDEX]):
        # "Any text" and the last ("Custom") share their expression: the
        # named preset is shown
        assert matching_preset(preset) == format_prefixes.index(preset), index


@pytest.mark.parametrize("regex", ["", "^[0-3]?\\d$", "^1?\\d{1,2}", "^(bad$"])
def test_other_expressions_are_custom(regex):
    assert matching_preset(regex) == CUSTOM_PRESET_INDEX


def test_regex_error():
    assert regex_error("^1?\\d{1,2}$") is None
    assert regex_error("") is None
    # Python reads an unfinished {...} as text: a valid expression
    assert regex_error("^1?\\d{1,2$") is None
    assert "missing )" in regex_error("^(1?\\d$")
    assert regex_error("[0-9") is not None


def test_changed_settings_against_the_fields_defaults():
    # the defaults differ per field (Period has an ordinal suffix)
    period = normalize_settings_dict({}, default_info_for_box_name("Period"))
    assert changed_settings(period, "Period") == []
    assert changed_settings(None, "Home Score") == []
    assert changed_settings({"dilate": 2, "smoothing": True}, "Home Score") == [
        "smoothing",
        "dilate",
    ]
    # only the given keys
    assert changed_settings(
        {"dilate": 2, "smoothing": True}, "Home Score", IMAGE_CLEANUP_SETTINGS
    ) == ["dilate"]
    # a custom field's defaults
    assert changed_settings({"format_regex": "^\\d*$"}, "Custom 1") == []
