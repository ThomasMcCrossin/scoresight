"""Game state: follows the game from the readings, for the sport chosen
(sports.py). GameEngine knows the scores, the clock and whether it runs, the
period, the fouls and timeouts, the points of each period (the line score),
and keeps an event log: a score, the start and the end of a period, the clock
starting and stopping, fouls and timeouts changing, the final buzzer.

MainWindow.ocrResult calls update() with each cycle's results, after Hold value
and the template fields (a held value counts), on the GUI thread. Each box
gets its role from its name (sports.assign_roles).

A changed value counts only once it has been read again (CONFIRM_READINGS), so
a reading that flickers for one cycle makes no event. A change the sport
doesn't allow (a basketball score going up by 5 or down, 21 -> 81, a period
skipped, the clock jumping) counts only once it has been read steadily for
HOLD_SECONDS, which a real correction is. The clock's small moves count at
once. Nothing here changes what the outputs get.
"""

import re
import time
from collections import deque
from collections.abc import Iterable
from dataclasses import asdict, dataclass

import sports
from sports import (
    AWAY_FOULS,
    AWAY_SCORE,
    AWAY_TIMEOUTS,
    CLOCK,
    HOME,
    HOME_FOULS,
    HOME_SCORE,
    HOME_TIMEOUTS,
    PERIOD,
    SHOT_CLOCK,
    TEAM_OF,
    SportProfile,
)
from text_detection_target import TextDetectionTargetWithResult

_GOOD_STATES = (
    TextDetectionTargetWithResult.ResultState.Success,
    TextDetectionTargetWithResult.ResultState.SameNoChange,
)

# readings of a new value before it counts
CONFIRM_READINGS = 2
# a change the sport doesn't allow counts once read this long and this often
HOLD_SECONDS = 3.0
HOLD_READINGS = 3
# the clock is stopped when it hasn't changed for this long (at least; longer
# when the boxes are read less often)
CLOCK_STOP_SECONDS = 1.6
# a small clock move: at most this many seconds more than the time since the
# clock was last read, times CLOCK_SLACK
CLOCK_MARGIN = 1.5
CLOCK_SLACK = 1.5
# moves against the counting direction, in a row, that turn it around
CLOCK_TURN_MOVES = 3
# the final buzzer: the last period ended this long ago, with different scores
FINAL_SETTLE_SECONDS = 3.0
MAX_EVENTS = 5000

# event kinds
SCORE = "score"
PERIOD_START = "period_start"
PERIOD_END = "period_end"
CLOCK_START = "clock_start"
CLOCK_STOP = "clock_stop"
FOULS = "fouls"
TIMEOUTS = "timeouts"
FINAL = "final"

# --- reading the values ----------------------------------------------------------

_COUNT = re.compile(r"\d{1,3}")
_CLOCK = re.compile(
    r"(?:(?:(?P<h>\d{1,2}):)?(?P<m>\d{1,3}):)?(?P<s>\d{1,2})(?:[.,](?P<f>\d{1,2}))?"
)
_OVERTIME = re.compile(r"(?:OT|O)\s*(\d?)")


def parse_count(text: str) -> int | None:
    """A score, fouls or timeouts: 0-999 ("07" is 7)."""
    text = text.strip().replace(" ", "")
    return int(text) if _COUNT.fullmatch(text) else None


def parse_clock(text: str) -> float | None:
    """The clock in seconds: "4:32" 272, "12:00" 720, "45.3" 45.3, "0:09.8"
    9.8, "1:02:03" 3723, "45" (seconds only) 45."""
    match = _CLOCK.fullmatch(text.strip().replace(" ", ""))
    if match is None:
        return None
    hours = int(match["h"] or 0)
    minutes = int(match["m"] or 0)
    seconds = int(match["s"])
    if match["m"] is not None and seconds > 59:
        return None
    fraction = match["f"]
    total = hours * 3600 + minutes * 60 + seconds
    if fraction:
        total += int(fraction) / 10 ** len(fraction)
    return float(total)


def parse_period(text: str, sport: SportProfile) -> int | None:
    """The period: "2", "2nd", "Q2", "P3", "Set 4", "OT" (the first overtime:
    the period after the regular ones), "OT2", "2OT"."""
    text = text.strip().upper()
    if not text:
        return None
    overtime = _OVERTIME.fullmatch(text) or re.fullmatch(r"(\d)\s*OT", text)
    if overtime and sport.overtime and sport.periods:
        extra = int(overtime.group(1) or 1)
        return sport.periods + extra if 1 <= extra <= 9 else None
    digits = re.search(r"\d{1,2}", text)
    if digits is None:
        return None
    period = int(digits.group(0))
    return period if 1 <= period <= 20 else None


# --- the game ---------------------------------------------------------------------


def _score_text(home: int | None, away: int | None) -> str:
    return f"{'?' if home is None else home}–{'?' if away is None else away}"


@dataclass(frozen=True)
class GameEvent:
    id: int  # 1, 2... in the game
    kind: str
    at: float  # when it happened (seconds since the epoch)
    period: int | None
    period_label: str
    clock: str | None  # the clock as read
    home: int | None  # the scores then
    away: int | None
    team: str | None = None  # "home" or "away"
    delta: int | None = None  # points, or how much fouls or timeouts changed
    value: int | None = None  # the team's score, fouls or timeouts then

    def text(self) -> str:
        """In English (the log, /game); the UI has its own translated text."""
        team = (self.team or "").capitalize()
        score = _score_text(self.home, self.away)
        if self.kind == SCORE:
            if self.delta is not None and self.delta < 0:
                return f"{team} score corrected to {self.value} ({score})"
            return f"{team} +{self.delta} ({score})"
        if self.kind == PERIOD_START:
            return f"Start of {self.period_label}"
        if self.kind == PERIOD_END:
            return f"End of {self.period_label} ({score})"
        if self.kind == FINAL:
            return f"Final ({score})"
        if self.kind == CLOCK_START:
            return f"Clock started at {self.clock}"
        if self.kind == CLOCK_STOP:
            return f"Clock stopped at {self.clock}"
        if self.kind == FOULS:
            return f"{team} fouls: {self.value}"
        if self.kind == TIMEOUTS:
            return f"{team} timeouts: {self.value}"
        return self.kind

    def to_dict(self) -> dict:
        return {**asdict(self), "text": self.text()}


@dataclass(frozen=True)
class LinePeriod:
    period: int
    label: str
    home: int
    away: int


@dataclass(frozen=True)
class GameState:
    """A snapshot of the game (GameEngine.state())."""

    sport: str
    roles: dict[str, str]  # {role: box name}
    home: int | None = None
    away: int | None = None
    period: int | None = None
    period_label: str = ""
    clock: str | None = None
    clock_running: bool = False
    shot_clock: str | None = None
    home_fouls: int | None = None
    away_fouls: int | None = None
    home_timeouts: int | None = None
    away_timeouts: int | None = None
    # the points scored in each period, since ScoreSight followed the game;
    # complete when it saw the game start (0-0)
    line_score: tuple[LinePeriod, ...] = ()
    line_score_complete: bool = False
    final: bool = False
    events: tuple[GameEvent, ...] = ()

    def to_dict(self, since: int = 0) -> dict:
        """For /game: the events after event id since."""
        return {
            "sport": self.sport,
            "roles": dict(self.roles),
            "home": {
                "score": self.home,
                "fouls": self.home_fouls,
                "timeouts": self.home_timeouts,
            },
            "away": {
                "score": self.away,
                "fouls": self.away_fouls,
                "timeouts": self.away_timeouts,
            },
            "period": self.period,
            "period_label": self.period_label,
            "clock": self.clock,
            "clock_running": self.clock_running,
            "shot_clock": self.shot_clock,
            "line_score": [asdict(period) for period in self.line_score],
            "line_score_complete": self.line_score_complete,
            "final": self.final,
            "events": [event.to_dict() for event in self.events if event.id > since],
        }


class _Tracker:
    """A role's value: the one that counts, and a new one being confirmed."""

    __slots__ = (
        "value",
        "text",
        "changed_at",
        "seen_at",
        "candidate",
        "candidate_text",
        "candidate_since",
        "candidate_count",
    )

    def __init__(self):
        self.value = None
        self.text: str | None = None
        self.changed_at: float | None = None  # when the value last changed
        self.seen_at: float | None = None  # when the role was last read
        self.candidate = None
        self.candidate_text: str | None = None
        self.candidate_since = 0.0
        self.candidate_count = 0

    def offer(
        self, value, text: str, now: float, plausible: bool, confirm: int
    ) -> bool:
        """A reading of value. True when it becomes the value: the first one,
        or a change read confirm times in a row (a change the sport doesn't
        allow: HOLD_READINGS times over HOLD_SECONDS)."""
        if value == self.value:
            self.text = text
            self.candidate = None
            return False
        if self.candidate is None or value != self.candidate:
            self.candidate = value
            self.candidate_text = text
            self.candidate_since = now
            self.candidate_count = 1
        else:
            self.candidate_count += 1
        if self.value is not None and not plausible:
            ready = (
                self.candidate_count >= HOLD_READINGS
                and now - self.candidate_since >= HOLD_SECONDS
            )
        else:
            ready = self.candidate_count >= confirm
        if not ready:
            return False
        self.value, self.text = self.candidate, self.candidate_text
        self.changed_at = now
        self.candidate = None
        return True


class GameEngine:
    """Follows a game (see the module's docstring). Called on the GUI thread."""

    def __init__(
        self,
        sport: SportProfile = sports.NONE,
        clock=time.monotonic,
        wall_clock=time.time,
    ):
        self._clock = clock
        self._wall_clock = wall_clock
        self.sport = sport
        self.new_game()

    # --- settings -------------------------------------------------------------

    def set_sport(self, sport: SportProfile):
        """Follow another sport: a new game."""
        if sport != self.sport:
            self.sport = sport
            self.new_game()

    def new_game(self):
        """Forget the game: the values are learned again from the next
        readings (without events), the event log and the line score start
        over."""
        self._trackers = {role: _Tracker() for role in sports.ROLES}
        self._events: deque[GameEvent] = deque(maxlen=MAX_EVENTS)
        self._next_id = 1
        self._line: dict[int, list[int]] = {}  # {period: [home, away]}
        self._started_at_zero: bool | None = None
        self._ended: set[int] = set()  # periods whose end was an event
        self._last_end: tuple[int, float] | None = None  # (period, when)
        self._final = False
        self._running = False
        self._direction = -1 if self.sport.clock_counts_down else 1  # -1: counts down
        self._against = 0  # clock moves against the direction, in a row
        self._last_update_at: float | None = None
        self._interval: float | None = None  # between updates (average)
        self._roles_for: tuple[tuple[str, ...], dict[str, str]] = ((), {})

    # --- the readings ---------------------------------------------------------

    def update(
        self, results: Iterable[TextDetectionTargetWithResult]
    ) -> list[GameEvent]:
        """Follow a cycle's results; returns the events they made."""
        if not self.sport.active:
            return []
        results = list(results)
        now = self._clock()
        if self._last_update_at is not None:
            gap = now - self._last_update_at
            self._interval = (
                gap if self._interval is None else (0.8 * self._interval + 0.2 * gap)
            )
        self._last_update_at = now
        roles = self.roles(result.name for result in results)
        by_name = {result.name: result for result in results}
        texts: dict[str, str] = {}
        for role, name in roles.items():
            result = by_name.get(name)
            if (
                result is None
                or result.result_state not in _GOOD_STATES
                or result.result is None
            ):
                continue
            text = str(result.result).strip()
            if text:
                texts[role] = text
        events: list[GameEvent] = []
        # the scores first: a score read with a new period still counts for
        # the period it was scored in
        for role in (HOME_SCORE, AWAY_SCORE):
            if role in texts:
                self._read_score(role, texts[role], now, events)
        for role, kind in (
            (HOME_FOULS, FOULS),
            (AWAY_FOULS, FOULS),
            (HOME_TIMEOUTS, TIMEOUTS),
            (AWAY_TIMEOUTS, TIMEOUTS),
        ):
            if role in texts:
                self._read_counter(role, kind, texts[role], now, events)
        if PERIOD in texts:
            self._read_period(texts[PERIOD], now, events)
        if CLOCK in texts:
            self._read_clock(texts[CLOCK], now, events)
        if SHOT_CLOCK in texts:
            self._trackers[SHOT_CLOCK].text = texts[SHOT_CLOCK]
        self._check_clock_stopped(now, events)
        self._check_final(now, events)
        return events

    def roles(self, names: Iterable[str]) -> dict[str, str]:
        """{role: box name} for these boxes."""
        names = tuple(names)
        if names != self._roles_for[0]:
            self._roles_for = (names, sports.assign_roles(names, self.sport))
        return dict(self._roles_for[1])

    def _read_score(self, role: str, text: str, now: float, events: list):
        value = parse_count(text)
        if value is None:
            return
        tracker = self._trackers[role]
        old = tracker.value
        plausible = old is None or (
            value - old in self.sport.score_steps
            or (self.sport.scores_reset_each_period and value == 0)
        )
        if not tracker.offer(value, text, now, plausible, CONFIRM_READINGS):
            return
        if old is None:
            self._note_first_scores()
            return
        if self.sport.scores_reset_each_period and value == 0:
            return  # a new set
        delta = value - old
        period = self._trackers[PERIOD].value
        if period is not None:
            line = self._line.setdefault(period, [0, 0])
            line[0 if TEAM_OF[role] == HOME else 1] += delta
        self._emit(SCORE, events, team=TEAM_OF[role], delta=delta, value=value)

    def _note_first_scores(self):
        """Whether the game was followed from 0-0 (the line score is
        complete), once both scores are known."""
        home = self._trackers[HOME_SCORE].value
        away = self._trackers[AWAY_SCORE].value
        if self._started_at_zero is None and home is not None and away is not None:
            period = self._trackers[PERIOD].value
            self._started_at_zero = home == 0 and away == 0 and period in (None, 1)

    def _read_counter(self, role: str, kind: str, text: str, now: float, events):
        value = parse_count(text)
        if value is None:
            return
        tracker = self._trackers[role]
        old = tracker.value
        plausible = old is None or abs(value - old) <= 1 or value == 0
        if not tracker.offer(value, text, now, plausible, CONFIRM_READINGS):
            return
        if old is not None:
            self._emit(kind, events, team=TEAM_OF[role], delta=value - old, value=value)

    def _read_period(self, text: str, now: float, events: list):
        period = parse_period(text, self.sport)
        if period is None:
            return
        tracker = self._trackers[PERIOD]
        old = tracker.value
        plausible = old is None or period == old + 1
        if not tracker.offer(period, text, now, plausible, CONFIRM_READINGS):
            return
        self._line.setdefault(period, [0, 0])
        if old is None:
            self._note_first_scores()
            return
        self._end_period(old, now, events)
        self._emit(PERIOD_START, events)

    def _read_clock(self, text: str, now: float, events: list):
        if self.sport.clock_counts_down is None:
            return
        seconds = parse_clock(text)
        if seconds is None:
            return
        tracker = self._trackers[CLOCK]
        old = tracker.value
        small = old is None or self._small_clock_move(
            old, seconds, tracker.seen_at, now
        )
        tracker.seen_at = now
        if not tracker.offer(seconds, text, now, small, 1):
            return
        if old is None:
            return
        if small:
            self._learn_direction(seconds - old)
            # only a move the way the clock counts starts it (a second back
            # is a misread, or the board being set)
            if not self._running and (seconds - old) * self._direction > 0:
                self._running = True
                self._emit(CLOCK_START, events)
        if seconds == 0 and self._direction < 0:
            self._end_period(self._trackers[PERIOD].value, now, events, at_zero=True)

    def _small_clock_move(self, old: float, new: float, seen_at, now: float) -> bool:
        """The clock ran (either way) for about the time since it was last
        read."""
        since = 0.0 if seen_at is None else max(0.0, now - seen_at)
        return abs(new - old) <= since * CLOCK_SLACK + CLOCK_MARGIN

    def _learn_direction(self, delta: float):
        """A clock set to count the other way (a soccer clock counting down)
        turns the direction around after CLOCK_TURN_MOVES moves."""
        if delta == 0:
            return
        if (delta > 0) == (self._direction > 0):
            self._against = 0
            return
        self._against += 1
        if self._against >= CLOCK_TURN_MOVES:
            self._direction = -self._direction
            self._against = 0

    def _check_clock_stopped(self, now: float, events: list):
        tracker = self._trackers[CLOCK]
        if not self._running or tracker.changed_at is None:
            return
        stop_after = max(CLOCK_STOP_SECONDS, 2.5 * (self._interval or 0.0))
        if now - tracker.changed_at > stop_after:
            self._running = False
            self._emit(CLOCK_STOP, events)

    def _end_period(self, period, now: float, events: list, at_zero=False):
        if period is None or period in self._ended:
            return
        self._ended.add(period)
        scores = {}
        if self.sport.scores_reset_each_period and period in self._line:
            # the board may show the next set's 0-0 already: the set's points
            scores = dict(zip(("home", "away"), self._line[period]))
        self._emit(PERIOD_END, events, period=period, **scores)
        if at_zero:
            self._last_end = (period, now)

    def _check_final(self, now: float, events: list):
        """The final buzzer: the clock reached 0:00 at the end of the last
        regular period (or of an overtime), and stayed there for
        FINAL_SETTLE_SECONDS (a last basket is counted first) with the
        scores not tied."""
        if self._final or self._last_end is None or not self.sport.periods:
            return
        period, ended_at = self._last_end
        if period < self.sport.periods or now - ended_at < FINAL_SETTLE_SECONDS:
            return
        if self._trackers[PERIOD].value != period or self._trackers[CLOCK].value != 0:
            return
        home = self._trackers[HOME_SCORE].value
        away = self._trackers[AWAY_SCORE].value
        if home is None or away is None or home == away:
            return
        self._final = True
        self._emit(FINAL, events)

    def _emit(self, kind: str, events: list, period=None, **fields):
        if period is None:
            period = self._trackers[PERIOD].value
        values = {
            "home": self._trackers[HOME_SCORE].value,
            "away": self._trackers[AWAY_SCORE].value,
            **fields,
        }
        event = GameEvent(
            id=self._next_id,
            kind=kind,
            at=self._wall_clock(),
            period=period,
            period_label=self.sport.period_label(period),
            clock=self._trackers[CLOCK].text,
            **values,
        )
        self._next_id += 1
        self._events.append(event)
        events.append(event)

    # --- what it knows --------------------------------------------------------

    @property
    def events(self) -> tuple[GameEvent, ...]:
        return tuple(self._events)

    def state(self) -> GameState:
        trackers = self._trackers
        period = trackers[PERIOD].value
        return GameState(
            sport=self.sport.key,
            roles=dict(self._roles_for[1]),
            home=trackers[HOME_SCORE].value,
            away=trackers[AWAY_SCORE].value,
            period=period,
            period_label=self.sport.period_label(period),
            clock=trackers[CLOCK].text,
            clock_running=self._running,
            shot_clock=trackers[SHOT_CLOCK].text,
            home_fouls=trackers[HOME_FOULS].value,
            away_fouls=trackers[AWAY_FOULS].value,
            home_timeouts=trackers[HOME_TIMEOUTS].value,
            away_timeouts=trackers[AWAY_TIMEOUTS].value,
            line_score=tuple(
                LinePeriod(p, self.sport.period_label(p), points[0], points[1])
                for p, points in sorted(self._line.items())
            ),
            line_score_complete=bool(self._started_at_zero),
            final=self._final,
            events=tuple(self._events),
        )
