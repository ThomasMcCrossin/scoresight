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
    """The reference, interpolated: what the board shows at any media time."""

    def __init__(self, truth):
        self.truth = truth
        self.observations = truth.observations
        self.stops = truth.clock_stops
        self._times = [obs.media for obs in self.observations]

    def _around(self, media):
        # bisect: an hour of samples against ~1000 polls must stay cheap
        index = bisect.bisect_right(self._times, media)
        before = self.observations[index - 1] if index > 0 else None
        after = self.observations[index] if index < len(self.observations) else None
        return before, after

    def _in_stop(self, media):
        return any(start - 2.0 <= media <= end + 2.0 for start, end in self.stops)

    def predicted(self, media):
        """(home, away, period, clock_seconds) the board shows at media."""
        before, after = self._around(media)
        if before is None:
            return None, None, None, None
        clock = None
        if before.clock_s is None:
            pass
        elif self._in_stop(media):
            # the clock stands still through the stop: it holds the last value
            # read before the reading stopped
            clock = before.clock_s
        elif after is not None and after.clock_s is not None:
            span = after.media - before.media
            drop = before.clock_s - after.clock_s
            if 0 <= drop <= span + 2.0:
                clock = before.clock_s - (media - before.media)
            else:
                clock = before.clock_s
        else:
            clock = before.clock_s
        return before.home, before.away, before.period, clock

    def has_reference(self, media, field_name):
        before, after = self._around(media)
        if before is None:
            return False
        if field_name == "clock":
            # The journal blanks the clock under a minute (the board switches
            # to tenths, "59.7", which it does not read): it cannot judge
            # those, so they are not scored.
            if before.clock_s is None:
                return False
            if before.clock_s <= 61.0 and after is not None and after.clock_s is None:
                return False
        if self._in_stop(media):
            # a stop is a recorded fact: the board is unchanged through it
            value = {
                "home": before.home,
                "away": before.away,
                "period": before.period,
                "clock": before.clock_s,
            }[field_name]
            return value is not None
        # a long journal gap that is not a stop (intermission, a reader hole):
        # nothing is known inside it
        if after is not None:
            gap = after.media - before.media
            if gap > 60.0 or (
                gap > 20.0 and media - before.media > 6.0 and after.media - media > 6.0
            ):
                return False
        if field_name == "home":
            return before.home is not None
        if field_name == "away":
            return before.away is not None
        if field_name == "period":
            return before.period is not None
        return False


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
    best_offset, best_score = 0.0, -1
    offset = -span
    while offset <= span + 1e-9:
        score = 0
        for wall, clock in candidates:
            media = start_media + (wall - t0) + offset
            predicted = timeline.predicted(media)[3]
            if predicted is not None and abs(predicted - clock) <= CLOCK_TOLERANCE:
                score += 1
        # on a tie prefer the offset closest to zero: a run whose clock stood
        # still (or a clip full of stops) aligns everywhere
        if score > best_score or (
            score == best_score and abs(offset) < abs(best_offset)
        ):
            best_offset, best_score = offset, score
        offset += step
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
    # +1 s: the engine's first cycle(s) learn the board's state
    observed_from = media_of(samples[0], t0, start_media, offset) + 1.0
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
        for index, got in enumerate(detected):
            if index in used or got.kind != want.kind:
                continue
            if abs(got.media - want.media) <= window:
                match = (index, got)
                break
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
