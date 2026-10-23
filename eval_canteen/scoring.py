"""Score a run's readings against the reference.

Everything is compared on **media time** (seconds into the recording), so a
run can be scored whatever clock offset it started at. The mapping from the
run's wall clock to media time is fitted once per run by aligning its clock
readings with the reference clock (the one signal that moves every second),
and the fitted offset is reported with the result.

Per field, every sample lands in exactly one bucket:

* ``correct``   -- a good reading, equal to the reference (clock within 1 s)
* ``wrong``     -- a good reading, different from the reference
* ``unknown``   -- no good reading (Empty / FailedFilter): the field is
  unknown, not wrong
* ``no_reference`` -- the reference has nothing for that instant (the board
  clock is blank at intermission, or the journal is inside a hole), so the
  sample is excluded from the accuracy denominator
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field

from truth import Transition, parse_clock

GOOD_STATES = ("Success", "SameNoChange")
CLOCK_TOLERANCE = 1.0  # seconds: the board shows whole seconds above a minute
# per-sample clock accuracy is not judged within this many seconds of a
# reference clock edge: a restart's timing is what the transition latency
# measures, and the journal's own resolution is one second
EDGE_GRACE = 2.5
# transitions are not judged this long after the harness started watching
SETTLE_SECONDS = 3.0
# a verified clock anchor replaces journal polls this close to it
VERIFIED_WINDOW = 3.0
FIELDS = (
    ("period", "Period"),
    ("home", "Home Score"),
    ("away", "Away Score"),
    ("clock", "Time"),
)
# how far a detected event may sit from the reference for it to match
MATCH_WINDOW = {
    "score_home": 25.0,
    "score_away": 25.0,
    "period_start": 25.0,
    "clock_start": 20.0,
    "clock_stop": 20.0,
}


@dataclass
class FieldScore:
    field: str
    correct: int = 0
    wrong: int = 0
    unknown: int = 0
    no_reference: int = 0

    @property
    def scoreable(self):
        return self.correct + self.wrong

    @property
    def sampled(self):
        return self.correct + self.wrong + self.unknown

    @property
    def accuracy(self):
        return self.correct / self.scoreable if self.scoreable else None

    @property
    def unknown_rate(self):
        return self.unknown / self.sampled if self.sampled else None

    def row(self):
        def pct(value):
            return "n/a" if value is None else f"{100 * value:.1f}%"

        return (
            self.field,
            self.correct,
            self.wrong,
            self.unknown,
            self.no_reference,
            pct(self.accuracy),
            pct(self.unknown_rate),
        )


@dataclass
class TransitionScore:
    kind: str
    expected: int = 0
    detected: int = 0
    false: int = 0
    latencies: list[float] = field(default_factory=list)

    @property
    def missed(self):
        return max(0, self.expected - self.detected)

    @property
    def mean_latency(self):
        return sum(self.latencies) / len(self.latencies) if self.latencies else None

    @property
    def max_latency(self):
        return max(self.latencies) if self.latencies else None


class Timeline:
    """The reference, interpolated: what the board shows at any media time.

    Scores and the period are the journal's last value; the clock is modelled
    with **runs**: sequences of journal polls where it moves about as much as
    the media does. Inside a run it is interpolated 1:1; outside one it holds
    (a stoppage, the intermission, a reader gap). A hand-verified clock start
    corrects a run whose first poll came late (the board showed 15:00 while
    the reader still reported 14:59's predecessor).
    """

    def __init__(self, truth):
        self.truth = truth
        self.observations = truth.observations
        self.stops = truth.clock_stops
        self._times = [obs.media for obs in self.observations]
        self.runs = self._build_runs()

    def _build_runs(self):
        runs = []
        current = None
        for obs in self.observations:
            if obs.clock_s is None:
                current = None
                continue
            if current is not None:
                span = obs.media - current["end_media"]
                moved = current["end_seconds"] - obs.clock_s
                if 0 < span <= 4.0 and 0 <= moved <= span + 2.0:
                    current["end_media"] = obs.media
                    current["end_seconds"] = obs.clock_s
                    continue
                runs.append(current)
            current = {
                "start_media": obs.media,
                "start_seconds": obs.clock_s,
                "end_media": obs.media,
                "end_seconds": obs.clock_s,
            }
        if current is not None:
            runs.append(current)
        # a verified clock start pulls the following run's start back to when
        # the board actually started
        for trans in self.truth.transitions:
            if trans.kind != "clock_start" or not trans.verified:
                continue
            if trans.value is None:
                continue
            media, seconds = trans.media, float(trans.value)
            for run in runs:
                delta = run["start_media"] - media
                if 0 <= delta <= VERIFIED_WINDOW + 2.0:
                    if abs(run["start_seconds"] - seconds) >= 1.0:
                        run["start_media"] = media
                        run["start_seconds"] = seconds
                    break
        return [
            (r["start_media"], r["start_seconds"], r["end_media"], r["end_seconds"])
            for r in runs
        ]

    def _around(self, media):
        # bisect: an hour of samples against ~1000 polls must stay cheap
        index = bisect.bisect_right(self._times, media)
        before = self.observations[index - 1] if index > 0 else None
        after = self.observations[index] if index < len(self.observations) else None
        return before, after

    def _in_stop(self, media):
        return any(start - 2.0 <= media <= end + 2.0 for start, end in self.stops)

    def pred_clock(self, media):
        """The clock's seconds at media: 1:1 inside a run, held outside one."""
        if not self.runs:
            return None
        # a recorded stop first: the board holds through it. It holds the
        # value it stopped on, except across a period change, where it is
        # already reset for the next period (0.0 becomes 15:00 during the
        # intermission).
        for stop_start, stop_end in self.stops:
            if stop_start <= media <= stop_end:
                period_change = any(
                    t.kind == "period_start"
                    and stop_start - 1.5 <= t.media <= stop_end + 1.5
                    for t in self.truth.transitions
                    if t.verified
                )
                if period_change:
                    following = [
                        start_seconds
                        for start_media, start_seconds, _, _ in self.runs
                        if start_media >= stop_end - 1.5
                    ]
                    if following:
                        return following[0]
                held = None
                for _, _, end_media, end_seconds in self.runs:
                    if end_media <= stop_start + 1.5:
                        held = end_seconds
                if held is not None:
                    return held
        for start_media, start_seconds, end_media, end_seconds in self.runs:
            if start_media <= media <= end_media:
                if end_media > start_media:
                    slope = (end_seconds - start_seconds) / (end_media - start_media)
                    value = start_seconds + slope * (media - start_media)
                else:
                    value = start_seconds
                # the board shows whole seconds: 684.0, not 684.02
                return float(round(value))
        if media < self.runs[0][0]:
            return self.runs[0][1]
        held = None
        for _, _, end_media, end_seconds in self.runs:
            if end_media <= media:
                held = end_seconds
        return held

    def near_edge(self, media):
        """True within EDGE_GRACE of a clock start, stop or period change."""
        edges = [start for start, _ in self.stops] + [end for _, end in self.stops]
        edges += [
            t.media
            for t in self.truth.transitions
            if t.kind in ("clock_start", "clock_stop", "period_start")
        ]
        return any(abs(media - edge) <= EDGE_GRACE for edge in edges)

    def scores_at(self, media):
        """(home, away, period) the board shows at media.

        The journal's last value, except that a hand-verified score or period
        change counts from its verified instant: the journal polled after the
        board flipped and still shows the old value for up to a second.
        """
        before, _ = self._around(media)
        if before is None:
            return None, None, None
        home, away, period = before.home, before.away, before.period
        for trans in self.truth.transitions:
            if not trans.verified or trans.media > media or trans.value is None:
                continue
            if trans.kind == "score_home":
                home = int(trans.value)
            elif trans.kind == "score_away":
                away = int(trans.value)
            elif trans.kind == "period_start":
                period = int(trans.value)
        return home, away, period

    def predicted(self, media):
        """(home, away, period, clock_seconds) the board shows at media."""
        home, away, period = self.scores_at(media)
        return home, away, period, self.pred_clock(media)

    def has_reference(self, media, field_name):
        before, after = self._around(media)
        if before is None:
            return False
        if field_name == "clock":
            # the journal blanks the clock under a minute (the board shows
            # tenths, "59.7", which it does not read)
            if before.clock_s is None and not self._in_stop(media):
                return False
            if before.clock_s is not None and before.clock_s <= 61.0:
                if (
                    after is not None
                    and after.clock_s is None
                    and not self._in_stop(media)
                ):
                    return False
            return self.pred_clock(media) is not None
        if self._in_stop(media):
            return {
                "home": before.home,
                "away": before.away,
                "period": before.period,
            }[field_name] is not None
        # a long journal gap that is not a stop (intermission, a reader hole):
        # nothing is known inside it
        if after is not None:
            gap = after.media - before.media
            if gap > 60.0 or (
                gap > 20.0 and media - before.media > 6.0 and after.media - media > 6.0
            ):
                return False
        return {
            "home": before.home,
            "away": before.away,
            "period": before.period,
        }[field_name] is not None


def _int(text):
    text = (text or "").strip().replace(" ", "")
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def fit_offset(samples, truth, start_media, span=40.0, step=0.25):
    """The wall->media offset that best aligns the run with the reference clock.

    media(t) = start_media + (t - t0) + offset, with t0 the run's first sample.
    Only running-clock samples are used: a stopped clock aligns everywhere.
    """
    if not samples:
        return 0.0, 0
    timeline = Timeline(truth)
    t0 = samples[0]["wall"]
    candidates = []
    for sample in samples:
        clock = parse_clock((sample.get("readings") or {}).get("Time", {}).get("text"))
        state = (sample.get("readings") or {}).get("Time", {}).get("state")
        if clock is None or state not in GOOD_STATES:
            continue
        candidates.append((sample["wall"], clock))
    if not candidates:
        return 0.0, 0
    # Whole-second clocks can't resolve an offset better than about a second,
    # so the best score is a plateau of many offsets: take the middle of it
    # (the median) rather than an edge of it.
    scores = []
    offset = -span
    while offset <= span + 1e-9:
        score = 0
        for wall, clock in candidates:
            media = start_media + (wall - t0) + offset
            predicted = timeline.predicted(media)[3]
            if predicted is not None and abs(predicted - clock) <= CLOCK_TOLERANCE:
                score += 1
        scores.append((round(offset, 3), score))
        offset += step
    best_score = max(score for _, score in scores)
    plateau = sorted(offset for offset, score in scores if score == best_score)
    best_offset = plateau[len(plateau) // 2]
    return best_offset, best_score


def media_of(sample, t0, start_media, offset):
    return start_media + (sample["wall"] - t0) + offset


def _event_kind_and_value(event):
    kind = str(event.get("kind") or "")
    if kind == "score":
        team = str(event.get("team") or "").lower()
        return ("score_home" if team == "home" else "score_away"), event.get("value")
    if kind in ("period_start", "period_end", "clock_start", "clock_stop", "final"):
        return kind, event.get("period")
    return kind, event.get("value")


def _score_transitions(events, t0, start_media, offset, end_media, observed_from):
    """The run's events, mapped to media time, in the reference's kinds.

    Events before ``observed_from`` (the moment the run began watching the
    clip) are dropped: the game engine emits a start-of-period and a
    clock-start when it first reads the board, which are not detections.
    """
    out = []
    for event in events:
        kind, value = _event_kind_and_value(event)
        wall = event.get("at")
        if wall is None:
            continue
        media = start_media + (float(wall) - t0) + offset
        if media < observed_from or media > end_media + 1.0:
            continue
        out.append(Transition(kind, media, value, str(event.get("text") or ""), True))
    return out


def score(samples, truth, game_events, start_media, duration):
    """Score a run. Returns the report dict (before rendering)."""
    timeline = Timeline(truth)
    offset, aligned = fit_offset(samples, truth, start_media)
    end_media = start_media + duration
    fields = {key: FieldScore(label) for key, label in FIELDS}
    wrong_readings = []
    if not samples:
        return {"error": "no samples"}

    t0 = samples[0]["wall"]
    # the run is only judged from its first sample (the engine's first cycles
    # learn the board's state, and they emit a start-of-period and a
    # clock-start that are not detections) and to the end of the media it
    # played (the feed's end stops the clock, which is not a real stop).
    # a settling window: the engine's first cycles learn the board's state
    # (and the harness never saw the board before the clip), so transitions in
    # the first seconds cannot be judged either way
    observed_from = media_of(samples[0], t0, start_media, offset) + SETTLE_SECONDS
    # --- per-sample field scoring -----------------------------------------
    for sample in samples:
        media = media_of(sample, t0, start_media, offset)
        if media > end_media + 1:
            continue
        home, away, period, clock = timeline.predicted(media)
        readings = sample.get("readings") or {}
        for key, label in FIELDS:
            score_row = fields[key]
            if not timeline.has_reference(media, key):
                score_row.no_reference += 1
                continue
            reading = readings.get(label) or {}
            text = reading.get("text") or ""
            state = reading.get("state") or "Empty"
            if state not in GOOD_STATES:
                score_row.unknown += 1
                continue
            expected = {"home": home, "away": away, "period": period, "clock": clock}[
                key
            ]
            if key == "clock":
                got = parse_clock(text)
                ok = (
                    got is not None
                    and expected is not None
                    and abs(got - expected) <= CLOCK_TOLERANCE
                )
            else:
                got = _int(text)
                ok = got is not None and got == expected
            if key == "clock" and timeline.near_edge(media):
                # a restart's exact second is the transition's latency
                score_row.no_reference += 1
                continue
            if ok:
                score_row.correct += 1
            else:
                score_row.wrong += 1
                wrong_readings.append(
                    {
                        "media": round(media, 2),
                        "field": label,
                        "read": text,
                        "expected": expected,
                        "state": state,
                    }
                )

    # --- transitions -------------------------------------------------------
    detected = _score_transitions(
        game_events, t0, start_media, offset, end_media, observed_from
    )
    expected = [
        t for t in truth.transitions if observed_from <= t.media <= end_media + 1.0
    ]
    kinds = sorted({t.kind for t in expected} | {t.kind for t in detected})
    transition_scores = {}
    used = set()
    for kind in kinds:
        row = TransitionScore(kind)
        row.expected = sum(1 for t in expected if t.kind == kind)
        transition_scores[kind] = row
    for want in sorted(expected, key=lambda t: t.media):
        window = MATCH_WINDOW.get(want.kind, 25.0)
        row = transition_scores[want.kind]
        match = None
        best = window + 1e-9
        for index, got in enumerate(detected):
            if index in used or got.kind != want.kind:
                continue
            distance = abs(got.media - want.media)
            # the nearest detection in the window, not the first one
            if distance < best:
                match = (index, got)
                best = distance
        if match is None:
            continue
        index, got = match
        used.add(index)
        row.detected += 1
        row.latencies.append(round(got.media - want.media, 2))
    for index, got in enumerate(detected):
        if index in used:
            continue
        row = transition_scores.get(got.kind)
        if row is None:
            row = transition_scores[got.kind] = TransitionScore(got.kind)
        row.false += 1

    return {
        "offset_seconds": round(offset, 2),
        "aligned_clock_samples": aligned,
        "samples": len(samples),
        "start_media": start_media,
        "duration": duration,
        "end_media": end_media,
        "fields": {
            key: {
                "name": row.field,
                "correct": row.correct,
                "wrong": row.wrong,
                "unknown": row.unknown,
                "no_reference": row.no_reference,
                "accuracy": row.accuracy,
                "unknown_rate": row.unknown_rate,
            }
            for key, row in fields.items()
        },
        "transitions": {
            kind: {
                "expected": row.expected,
                "detected": row.detected,
                "missed": row.missed,
                "false": row.false,
                "mean_latency": row.mean_latency,
                "max_latency": row.max_latency,
                "latencies": row.latencies,
            }
            for kind, row in transition_scores.items()
        },
        "wrong_readings": wrong_readings,
        "game_events": [
            {
                "media": round(t.media, 2),
                "kind": t.kind,
                "value": t.value,
                "text": t.note,
            }
            for t in sorted(detected, key=lambda t: t.media)
        ],
    }


def render_markdown(meta, result, truth):
    lines = []
    lines.append(
        f"# ScoreSight eval — {meta['clip']} · {meta['variant']} · {meta['engine']}"
    )
    lines.append("")
    lines.append("| | |")
    lines.append("|---|---|")
    for key in (
        "clip",
        "variant",
        "engine",
        "cadence",
        "start_media",
        "duration",
        "samples",
        "offset_seconds",
        "aligned_clock_samples",
    ):
        lines.append(f"| {key} | {meta.get(key)} |")
    lines.append("")
    lines.append("## Field accuracy")
    lines.append("")
    lines.append(
        "| field | correct | wrong | unknown | no reference | accuracy | unknown rate |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for key, _ in FIELDS:
        row = result["fields"][key]
        acc = "n/a" if row["accuracy"] is None else f"{100 * row['accuracy']:.1f}%"
        unk = (
            "n/a"
            if row["unknown_rate"] is None
            else f"{100 * row['unknown_rate']:.1f}%"
        )
        lines.append(
            f"| {row['name']} | {row['correct']} | {row['wrong']} | {row['unknown']} "
            f"| {row['no_reference']} | {acc} | {unk} |"
        )
    lines.append("")
    lines.append("## Transitions")
    lines.append("")
    lines.append(
        "| kind | expected | detected | missed | false | mean latency (s) | max latency (s) |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for kind in sorted(result["transitions"]):
        row = result["transitions"][kind]
        mean = "n/a" if row["mean_latency"] is None else f"{row['mean_latency']:+.2f}"
        worst = "n/a" if row["max_latency"] is None else f"{row['max_latency']:+.2f}"
        lines.append(
            f"| {kind} | {row['expected']} | {row['detected']} | {row['missed']} "
            f"| {row['false']} | {mean} | {worst} |"
        )
    lines.append("")
    wrong = result["wrong_readings"]
    lines.append(f"## Wrong readings ({len(wrong)})")
    lines.append("")
    if wrong:
        lines.append("| media (s) | field | read | expected | state |")
        lines.append("|---|---|---|---|---|")
        for item in wrong[:60]:
            lines.append(
                f"| {item['media']:.1f} | {item['field']} | `{item['read']}` "
                f"| `{item['expected']}` | {item['state']} |"
            )
        if len(wrong) > 60:
            lines.append(f"| … | {len(wrong) - 60} more in the JSON report | | | |")
    else:
        lines.append("None.")
    lines.append("")
    lines.append("## Reference notes")
    lines.append("")
    for note in truth.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)
