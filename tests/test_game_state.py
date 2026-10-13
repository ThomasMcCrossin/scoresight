"""The game-state engine (game_state.py) and the sport profiles (sports.py):
reading the values, the roles of the boxes, and the events of whole game
sequences with a fake clock."""

import pytest

import game_state
import sports
from game_state import (
    CLOCK_START,
    CLOCK_STOP,
    FINAL,
    FOULS,
    PERIOD_END,
    PERIOD_START,
    SCORE,
    TIMEOUTS,
    GameEngine,
    parse_clock,
    parse_count,
    parse_period,
)


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture
def game(make_result):
    """game(sport) -> a Game that feeds readings to a GameEngine."""

    class Game:
        def __init__(self, sport):
            self.clock = FakeClock()
            self.engine = GameEngine(sport, clock=self.clock, wall_clock=lambda: 1.0)

        def read(self, step=0.5, states=None, **values):
            """One cycle, step seconds after the last one: {box name: text}
            (keyword arguments with "_" for spaces)."""
            self.clock.now += step
            states = states or {}
            results = []
            for key, text in values.items():
                name = key.replace("_", " ")
                results.append(
                    make_result(name, text, state=states.get(name, "Success"))
                )
            return self.engine.update(results)

        def kinds(self, events):
            return [event.kind for event in events]

    return Game


# --- reading the values ------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("21", 21),
        ("07", 7),
        (" 105 ", 105),
        ("1 2", 12),
        ("", None),
        ("2a", None),
        ("1234", None),
    ],
)
def test_parse_count(text, expected):
    assert parse_count(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("4:32", 272.0),
        ("12:00", 720.0),
        ("04:32", 272.0),
        ("45.3", 45.3),
        ("0:09.8", 9.8),
        ("9.8", 9.8),
        ("45", 45.0),
        ("0", 0.0),
        ("0.0", 0.0),
        ("90:00", 5400.0),
        ("1:02:03", 3723.0),
        ("4:72", None),
        ("abc", None),
        ("", None),
    ],
)
def test_parse_clock(text, expected):
    result = parse_clock(text)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2", 2),
        ("2nd", 2),
        ("Q2", 2),
        ("P3", 3),
        ("Set 4", 4),
        ("OT", 5),
        ("ot", 5),
        ("OT2", 6),
        ("2OT", 6),
        ("", None),
        ("H", None),
        ("0", None),
    ],
)
def test_parse_period(text, expected):
    assert parse_period(text, sports.BASKETBALL) == expected


def test_overtime_is_after_the_regular_periods():
    assert parse_period("OT", sports.HOCKEY) == 4
    assert parse_period("OT", sports.VOLLEYBALL) is None  # no overtime


# --- sports and roles ----------------------------------------------------------------


def test_roles_from_box_names():
    role_of = sports.role_of
    assert role_of("Home Score") == sports.HOME_SCORE
    assert role_of("score_home") == sports.HOME_SCORE
    assert role_of("GUEST") == sports.AWAY_SCORE
    assert role_of("Visitors Score") == sports.AWAY_SCORE
    assert role_of("Game Clock") == sports.CLOCK
    assert role_of("Time") == sports.CLOCK
    assert role_of("Quarter") == sports.PERIOD
    assert role_of("Shot Clock") == sports.SHOT_CLOCK
    assert role_of("Home Fouls") == sports.HOME_FOULS
    assert role_of("Guest TOL") == sports.AWAY_TIMEOUTS
    assert role_of("Sponsor") is None


def test_every_standard_box_has_a_role():
    from defaults import default_boxes

    assert all(sports.role_of(box["name"]) for box in default_boxes)


def test_assign_roles_follows_the_sport_and_takes_the_first_box():
    names = ["Home Score", "Home", "Away Score", "Time", "Home Fouls"]
    assert sports.assign_roles(names, sports.BASKETBALL) == {
        sports.HOME_SCORE: "Home Score",
        sports.AWAY_SCORE: "Away Score",
        sports.CLOCK: "Time",
        sports.HOME_FOULS: "Home Fouls",
    }
    # soccer has no fouls on the board
    assert sports.HOME_FOULS not in sports.assign_roles(names, sports.SOCCER)
    assert sports.assign_roles(names, sports.NONE) == {}


def test_profiles():
    assert sports.profile("basketball") is sports.BASKETBALL
    assert sports.profile("curling") is sports.NONE
    assert sports.profile(["basketball"]) is sports.NONE
    assert not sports.NONE.active and sports.BASKETBALL.active
    assert sports.BASKETBALL.period_label(2) == "Q2"
    assert sports.BASKETBALL.period_label(5) == "OT"
    assert sports.BASKETBALL.period_label(6) == "OT2"
    assert sports.BASKETBALL.period_label(None) == ""
    assert sports.SOCCER.period_label(2) == "H2"
    assert sports.HOCKEY.period_label(3) == "P3"
    assert sports.VOLLEYBALL.period_label(5) == "Set 5"


# --- a basketball game ----------------------------------------------------------------


def start_basketball(game, home="0", away="0", period="1", time="8:00"):
    g = game(sports.BASKETBALL)
    for _ in range(2):
        assert g.read(Home_Score=home, Away_Score=away, Period=period, Time=time) == []
    return g


def test_no_sport_follows_nothing(game):
    g = game(sports.NONE)
    for score in ("0", "2", "2"):
        assert g.read(Home_Score=score) == []
    assert g.engine.state().home is None


def test_the_first_readings_make_no_events(game):
    g = start_basketball(game, home="34", away="30", period="3", time="5:12")
    state = g.engine.state()
    assert (state.home, state.away, state.period, state.clock) == (34, 30, 3, "5:12")
    assert state.period_label == "Q3"
    assert g.engine.events == ()


def test_a_score_counts_once_read_twice(game):
    g = start_basketball(game)
    assert g.read(Home_Score="2", Away_Score="0", Period="1", Time="8:00") == []
    events = g.read(Home_Score="2", Away_Score="0", Period="1", Time="8:00")
    assert g.kinds(events) == [SCORE]
    event = events[0]
    assert (event.team, event.delta, event.value) == ("home", 2, 2)
    assert (event.home, event.away, event.period_label, event.clock) == (
        2,
        0,
        "Q1",
        "8:00",
    )
    assert event.text() == "Home +2 (2–0)"


def test_same_no_change_confirms_a_score(game):
    g = start_basketball(game)
    g.read(Away_Score="3", Home_Score="0")
    events = g.read(
        Away_Score="3", Home_Score="0", states={"Away Score": "SameNoChange"}
    )
    assert [(e.team, e.delta) for e in events] == [("away", 3)]


def test_a_flicker_makes_no_event(game):
    g = start_basketball(game, home="21")
    g.read(Home_Score="81")
    g.read(Home_Score="21")
    g.read(Home_Score="21")
    assert g.engine.events == ()
    assert g.engine.state().home == 21


def test_rejected_readings_neither_count_nor_reset(game):
    g = start_basketball(game)
    g.read(Home_Score="2")
    g.read(Home_Score="?", states={"Home Score": "FailedFilter"})
    assert g.kinds(g.read(Home_Score="2")) == [SCORE]


def test_a_change_the_sport_does_not_allow_waits(game):
    g = start_basketball(game, home="21")
    # +60 (21 -> 81): read steadily, it counts after HOLD_SECONDS
    for _ in range(5):
        assert g.read(step=0.5, Home_Score="81") == []
    events = g.read(step=1.0, Home_Score="81")
    assert [(e.kind, e.delta) for e in events] == [(SCORE, 60)]


def test_a_correction_counts_after_the_hold(game):
    g = start_basketball(game, home="24")
    for _ in range(10):
        events = g.read(step=0.5, Home_Score="22")
        if events:
            break
    assert [(e.kind, e.delta, e.value) for e in events] == [(SCORE, -2, 22)]
    assert events[0].text() == "Home score corrected to 22 (22–0)"


def test_the_clock_starts_and_stops(game):
    g = start_basketball(game, time="8:00")
    events = g.read(step=1.0, Time="7:59")
    assert g.kinds(events) == [CLOCK_START]
    assert g.engine.state().clock_running
    g.read(step=1.0, Time="7:58")
    g.read(step=1.0, Time="7:57")
    # stopped: the same time for longer than the clock's stop delay (at least
    # CLOCK_STOP_SECONDS, longer when the boxes are read less often)
    assert g.read(step=1.0, Time="7:57") == []
    events = []
    for _ in range(3):
        events += g.read(step=1.0, Time="7:57")
    assert g.kinds(events) == [CLOCK_STOP]
    assert events[0].clock == "7:57"
    assert not g.engine.state().clock_running


def test_a_second_back_does_not_start_the_clock(game):
    g = start_basketball(game, time="4:32")
    assert g.read(step=1.0, Time="4:33") == []
    assert g.engine.state().clock == "4:33"
    assert g.kinds(g.read(step=1.0, Time="4:32")) == [CLOCK_START]


def test_a_clock_jump_waits(game):
    g = start_basketball(game, time="7:00")
    # 7:00 -> 1:00 in a second: a misread, or the clock being set
    assert g.read(step=1.0, Time="1:00") == []
    assert g.engine.state().clock == "7:00"


def test_a_quarter_ends_at_zero_and_the_next_starts(game):
    g = start_basketball(game, home="10", away="8", time="0:02")
    g.read(step=1.0, Time="0:01")
    events = g.read(step=1.0, Time="0.0")
    assert g.kinds(events) == [PERIOD_END]
    assert events[0].text() == "End of Q1 (10–8)"
    # the board goes to the second quarter: no second end
    g.read(step=1.0, Period="2", Time="8:00")
    events = g.read(step=1.0, Period="2", Time="8:00")
    # (and the clock has stood at 0.0 long enough to count as stopped)
    assert g.kinds(events) == [PERIOD_START, CLOCK_STOP]
    assert events[0].text() == "Start of Q2"
    assert g.kinds(g.engine.events).count(PERIOD_END) == 1


def test_final_after_the_last_period_unless_tied(game):
    g = start_basketball(game, home="60", away="58", period="4", time="0:01")
    g.read(step=1.0, Time="0.0")
    # a last basket counts first: the final waits a few seconds
    g.read(step=1.0, Home_Score="60", Away_Score="61", Time="0.0")
    g.read(step=1.0, Home_Score="60", Away_Score="61", Time="0.0")
    g.read(step=2.0, Home_Score="60", Away_Score="61", Time="0.0")
    final = [e for e in g.engine.events if e.kind == FINAL]
    assert len(final) == 1 and final[0].text() == "Final (60–61)"
    assert g.engine.state().final

    tied = start_basketball(game, home="60", away="60", period="4", time="0:01")
    tied.read(step=1.0, Time="0.0")
    for _ in range(5):
        tied.read(step=1.0, Time="0.0")
    assert FINAL not in tied.kinds(tied.engine.events)


def test_overtime_ends_the_game(game):
    g = start_basketball(game, home="70", away="70", period="OT", time="0:01")
    g.read(step=1.0, Home_Score="72", Time="0.0")
    g.read(step=1.0, Home_Score="72", Time="0.0")
    for _ in range(4):
        g.read(step=1.0, Home_Score="72", Time="0.0")
    assert FINAL in g.kinds(g.engine.events)


def test_the_line_score(game):
    g = start_basketball(game)
    assert g.engine.state().line_score_complete
    for home, away in (("2", "0"), ("2", "3"), ("5", "3")):
        g.read(Home_Score=home, Away_Score=away)
        g.read(Home_Score=home, Away_Score=away)
    for _ in range(2):
        g.read(Period="2", Home_Score="5", Away_Score="3")
    for _ in range(2):
        g.read(Period="2", Home_Score="5", Away_Score="5")
    lines = [(p.label, p.home, p.away) for p in g.engine.state().line_score]
    assert lines == [("Q1", 5, 3), ("Q2", 0, 2)]


def test_a_game_joined_late_has_a_partial_line_score(game):
    g = start_basketball(game, home="34", away="30", period="3")
    assert not g.engine.state().line_score_complete


def test_fouls_and_timeouts(game):
    g = start_basketball(game)
    for _ in range(2):
        g.read(Home_Fouls="3", Away_Timeouts="4")
    for _ in range(2):
        events = g.read(Home_Fouls="4", Away_Timeouts="3")
    assert [(e.kind, e.team, e.value, e.delta) for e in events] == [
        (FOULS, "home", 4, 1),
        (TIMEOUTS, "away", 3, -1),
    ]
    assert events[0].text() == "Home fouls: 4"
    # back to 0 at halftime is allowed
    for _ in range(2):
        events = g.read(Home_Fouls="0", Away_Timeouts="3")
    assert [(e.kind, e.value) for e in events] == [(FOULS, 0)]


def test_new_game_and_another_sport_start_over(game):
    g = start_basketball(game)
    g.read(Home_Score="2")
    g.read(Home_Score="2")
    assert g.engine.events
    g.engine.new_game()
    assert g.engine.events == () and g.engine.state().home is None
    g.engine.set_sport(sports.SOCCER)
    assert g.engine.state().sport == "soccer"


# --- other sports ---------------------------------------------------------------------


def test_volleyball_sets(game):
    g = game(sports.VOLLEYBALL)
    for _ in range(2):
        g.read(Home_Score="0", Away_Score="0", Set="1")
    for home, away in (("24", "20"),):
        # fast-forward: hold the jump to 24-20
        for _ in range(8):
            g.read(Home_Score=home, Away_Score=away, Set="1")
    for _ in range(2):
        g.read(Home_Score="25", Away_Score="20", Set="1")
    # the board goes to set 2: the scores go back to 0 (not a correction)
    events = []
    for _ in range(2):
        events += g.read(Home_Score="0", Away_Score="0", Set="2")
    assert g.kinds(events) == [PERIOD_END, PERIOD_START]
    assert events[0].text() == "End of Set 1 (25–20)"
    assert all(e.delta is None or e.delta > 0 for e in g.engine.events)
    lines = [(p.label, p.home, p.away) for p in g.engine.state().line_score]
    assert lines == [("Set 1", 25, 20), ("Set 2", 0, 0)]


def test_soccer_clock_counts_up_and_halves(game):
    g = game(sports.SOCCER)
    for _ in range(2):
        g.read(Home_Score="0", Away_Score="0", Period="1", Time="44:58")
    events = g.read(step=1.0, Time="44:59")
    assert g.kinds(events) == [CLOCK_START]
    g.read(step=1.0, Time="45:00")
    for _ in range(2):
        events = g.read(step=1.0, Period="2", Time="45:00")
    assert PERIOD_END in g.kinds(events) and PERIOD_START in g.kinds(events)
    assert FINAL not in g.kinds(g.engine.events)


def test_a_clock_counting_the_other_way_is_learned(game):
    # a youth soccer board counting down: after a few moves it is learned,
    # and 0:00 ends the half
    g = game(sports.SOCCER)
    for _ in range(2):
        g.read(Period="1", Time="0:05")
    for time_ in ("0:04", "0:03", "0:02", "0:01"):
        g.read(step=1.0, Time=time_)
    events = g.read(step=1.0, Time="0:00")
    assert g.kinds(events) == [PERIOD_END]


# --- the snapshot ---------------------------------------------------------------------


def test_state_to_dict(game):
    g = start_basketball(game)
    g.read(Home_Score="3", Home_Fouls="1", Shot_Clock="14")
    g.read(Home_Score="3", Home_Fouls="1", Shot_Clock="14")
    data = g.engine.state().to_dict()
    assert data["sport"] == "basketball"
    assert data["home"] == {"score": 3, "fouls": 1, "timeouts": None}
    assert data["away"]["score"] == 0
    assert data["period_label"] == "Q1"
    assert data["shot_clock"] == "14"
    assert data["roles"]["home_score"] == "Home Score"
    assert data["line_score"] == [{"period": 1, "label": "Q1", "home": 3, "away": 0}]
    assert [event["text"] for event in data["events"]] == ["Home +3 (3–0)"]
    last = data["events"][-1]["id"]
    assert g.engine.state().to_dict(since=last)["events"] == []


def test_the_event_log_is_capped(game, monkeypatch):
    monkeypatch.setattr(game_state, "MAX_EVENTS", 3)
    g = start_basketball(game)
    for score in range(1, 6):
        g.read(Home_Score=str(score))
        g.read(Home_Score=str(score))
    events = g.engine.events
    assert [e.value for e in events] == [3, 4, 5]
    assert events[-1].id == 5


# --- the UI's texts ----------------------------------------------------------------------


def test_every_sport_has_a_translatable_name(qapp):
    from game_ui_handler import sport_names

    names = sport_names()
    assert set(names) == set(sports.PROFILES)
    assert names["hockey"] == "Ice hockey"


def test_the_ui_texts_match_the_engine_in_english(game, qapp):
    from game_ui_handler import event_text

    g = start_basketball(game, home="60", away="58", period="4", time="0:02")
    for _ in range(2):
        g.read(step=1.0, Home_Score="57", Home_Fouls="3", Away_Timeouts="2")
    for _ in range(8):
        g.read(
            step=1.0, Home_Score="57", Home_Fouls="4", Away_Timeouts="1", Time="0:01"
        )
    g.read(step=1.0, Home_Score="57", Time="0.0")
    for _ in range(5):
        g.read(step=1.0, Home_Score="57", Time="0.0")
    kinds = set(g.kinds(g.engine.events))
    assert {SCORE, FOULS, TIMEOUTS, CLOCK_START, CLOCK_STOP, PERIOD_END, FINAL} <= kinds
    for event in g.engine.events:
        assert event_text(event) == event.text()


def test_status_text(game, qapp):
    from game_ui_handler import status_text

    g = start_basketball(game, home="24", away="21", period="2", time="4:32")
    assert status_text(g.engine.state(), sports.BASKETBALL) == (
        "Follows Home Score, Away Score, Time, Period\nQ2 · 24–21 · clock stopped"
    )
    g.read(step=1.0, Time="4:31")
    assert status_text(g.engine.state(), sports.BASKETBALL).endswith("clock running")
    assert status_text(g.engine.state(), sports.NONE) == ""
    other = game(sports.BASKETBALL)
    other.read(Sponsor="ACME")
    assert status_text(other.engine.state(), sports.BASKETBALL).startswith(
        "No field is named like a score"
    )
