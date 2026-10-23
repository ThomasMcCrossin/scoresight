"""Offline checks for the scorer, on synthetic samples (no ScoreSight needed).

Run: nice -n 15 python -m pytest eval_canteen/test_scoring.py -q
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import scoring  # noqa: E402
import truth as truth_mod  # noqa: E402


def _truth():
    return truth_mod.load_truth("20261023T091022.mkv")


def _sample(wall, home="1", away="0", period="1", clock="10:00", home_state="Success"):
    return {
        "wall": wall,
        "readings": {
            "Home Score": {"text": home, "state": home_state},
            "Away Score": {"text": away, "state": "Success"},
            "Period": {"text": period, "state": "Success"},
            "Time": {"text": clock, "state": "Success"},
        },
        "game": {},
    }


def test_parse_clock():
    assert truth_mod.parse_clock("11:31") == 691
    assert truth_mod.parse_clock("59.7") == 59.7
    assert truth_mod.parse_clock("") is None
    assert truth_mod.parse_clock("1") == 1


def test_reference_timeline_is_anchored_on_media_time():
    timeline = scoring.Timeline(_truth())
    # 5:09 at the home goal (media 496), 15:00 after the period change
    assert round(timeline.predicted(496)[3]) == 309
    assert timeline.predicted(1044)[2] == 2
    assert round(timeline.predicted(1044)[3]) == 900


def test_clock_holds_through_a_stop():
    timeline = scoring.Timeline(_truth())
    start, end = _truth().clock_stops[0]
    before = timeline.predicted(start - 1)[3]
    during = timeline.predicted((start + end) / 2)[3]
    assert during is not None and abs(during - before) <= 1.0


def test_unknown_is_not_wrong():
    samples = [_sample(1000.0 + i, home="", home_state="Empty") for i in range(5)]
    result = scoring.score(samples, _truth(), [], 100.0, 10.0)
    home = result["fields"]["home"]
    assert home["wrong"] == 0
    assert home["unknown"] == 5


def test_wrong_reading_is_counted_and_listed():
    # media 100 is period 1 home 1, away 0
    samples = [_sample(1000.0, home="7") for _ in range(4)]
    result = scoring.score(samples, _truth(), [], 100.0, 4.0)
    home = result["fields"]["home"]
    assert home["wrong"] == 4
    assert home["correct"] == 0
    assert result["wrong_readings"][0]["expected"] == 1


def test_fit_offset_recovers_a_known_shift():
    truth = _truth()
    timeline = scoring.Timeline(truth)
    # a run that started 20 s late: media(1000) = 120
    samples = []
    for i in range(20):
        media = 120 + i
        samples.append(
            _sample(1000.0 + i, clock=_clock_text(timeline.predicted(media)[3]))
        )
    offset, aligned = scoring.fit_offset(samples, truth, 100.0)
    assert aligned > 0
    assert abs(offset - 20.0) <= 1.0


def _clock_text(seconds):
    seconds = int(round(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def test_transition_latency_is_measured_in_media_time():
    truth = _truth()
    timeline = scoring.Timeline(truth)
    # a run over media 600-610 (a running clock), whose engine detected the
    # media-605.4 clock stop 2 s "early" in media terms
    samples = [
        _sample(1000.0 + i, clock=_clock_text(timeline.predicted(600 + i)[3]))
        for i in range(10)
    ]
    events = [
        {
            "id": 1,
            "kind": "clock_stop",
            "at": 1000.0 + 2.0,
            "period": 1,
            "text": "Clock stopped at 4:47",
        }
    ]
    result = scoring.score(samples, truth, events, 600.0, 10.0)
    row = result["transitions"]["clock_stop"]
    assert row["detected"] == 1
    assert row["false"] == 0
    assert abs(row["mean_latency"] - (602.0 - 605.4)) <= 0.6


def test_engine_startup_events_are_not_detections():
    truth = _truth()
    # the engine's first cycle "starts the period" and "starts the clock"
    events = [
        {
            "id": 1,
            "kind": "period_start",
            "at": 1000.0,
            "period": 1,
            "text": "Start of P1",
        },
        {
            "id": 2,
            "kind": "clock_start",
            "at": 1000.0,
            "period": 1,
            "text": "Clock started",
        },
    ]
    samples = [_sample(1000.0 + i) for i in range(5)]
    result = scoring.score(samples, truth, events, 200.0, 5.0)
    for row in result["transitions"].values():
        assert row["false"] == 0
