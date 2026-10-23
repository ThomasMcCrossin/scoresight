"""Ground truth for the 2026-10-23 Amherst Stadium game, media time based.

Two independent references, both keyed on video position (seconds into the
recording), so a run can be scored whatever wall-clock offset it started at:

* ``journal`` -- the homegrown scoreboard reader's poll journal
  (~/.local/state/canteen-ops/scoreboard-reader/20261023-game-v1fix/polls).
  One record per accepted reading: home/away score, period, clock.
* ``frame`` -- hand-verified frames (``ffmpeg -ss`` + view), recorded in
  ``truth/20261023_game.json``. They cover the facts the journal can only
  approximate (score changes at a wall-clock timestamp) and the ones it does
  not record at all (the clock stopping).

The journal is a **reference, not gospel**: a gap of many seconds in its
polls is usually the reader catching up, not the clock stopping. Every gap is
classified by comparing the clock's change with the gap's length, and only
gaps the frames confirm are kept as stops.
"""

from __future__ import annotations

import base64
import glob
import json
import os
import re
from dataclasses import dataclass, field

JOURNAL_DIR = os.path.expanduser(
    "~/.local/state/canteen-ops/scoreboard-reader/20261023-game-v1fix/polls"
)
TRUTH_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "truth", "20261023_game.json"
)

# The journal records the poll's time as ADT (-03:00). The footage is named by
# its segment start in ADT; its first frame carries start_time 0.0, so media
# seconds = wall clock - segment start.
ADT_SEGMENT_START = {
    "20261023T081020.mkv": "2026-10-23T08:10:20.000-03:00",
    "20261023T091022.mkv": "2026-10-23T09:10:22.000-03:00",
    "20261023T101023.mkv": "2026-10-23T10:10:23.000-03:00",
}

_CLOCK = re.compile(r"(?:(\d{1,3}):)?(\d{1,2})(?:[.,](\d{1,2}))?")


def parse_clock(text):
    """Seconds for a board clock: "11:31" -> 691, "59.7" -> 59.7, "" -> None."""
    text = (text or "").strip().replace(" ", "")
    if not text:
        return None
    m = _CLOCK.fullmatch(text)
    if not m:
        return None
    minutes = int(m.group(1) or 0)
    seconds = int(m.group(2))
    if minutes and seconds > 59:
        return None
    value = minutes * 60 + seconds
    if m.group(3):
        value += int(m.group(3)) / 10 ** len(m.group(3))
    return float(value)


def _int_or_none(text):
    text = (text or "").strip().replace(" ", "")
    return int(text) if text.isdigit() else None


@dataclass
class Observation:
    """One reference observation, at a media position."""

    media: float
    home: int | None
    away: int | None
    period: int | None
    clock: str | None  # as the board shows it
    clock_s: float | None
    source: str  # "journal" or "frame"


@dataclass
class Transition:
    """A change of state at a media position."""

    kind: str  # score_home, score_away, period_start, clock_start, clock_stop
    media: float
    value: object = None
    note: str = ""
    verified: bool = False


@dataclass
class Truth:
    media_id: str
    observations: list[Observation] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    # media spans where the clock is known to be standing still
    clock_stops: list[tuple[float, float]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def observation_at(self, media):
        """The journal observation closest to media (within 5 s)."""
        best, best_d = None, 5.0
        for obs in self.observations:
            d = abs(obs.media - media)
            if d <= best_d:
                best, best_d = obs, d
        return best


def _load_journal(media_id):
    segment_start = ADT_SEGMENT_START.get(media_id)
    if segment_start:
        from datetime import datetime

        start = datetime.fromisoformat(segment_start)
    else:
        start = None
    observations = []
    for path in sorted(glob.glob(os.path.join(JOURNAL_DIR, "*.json"))):
        with open(path) as handle:
            record = json.load(handle)
        context = record.get("source_context") or {}
        if context.get("media_id") != media_id:
            continue
        body = record.get("response_body_base64")
        if not body:
            continue
        payload = json.loads(base64.b64decode(body))
        fields = payload.get("accepted_fields") or {}
        media = context.get("media_pts_seconds")
        if media is None and start is not None:
            received = datetime.fromisoformat(record["received_at"])
            media = (received - start).total_seconds()
        if media is None:
            continue
        observations.append(
            Observation(
                media=round(float(media), 2),
                home=_int_or_none(fields.get("home")),
                away=_int_or_none(fields.get("guest")),
                period=_int_or_none(fields.get("period")),
                clock=(fields.get("clock") or "").strip() or None,
                clock_s=parse_clock(fields.get("clock")),
                source="journal",
            )
        )
    observations.sort(key=lambda o: o.media)
    return observations


def _clock_gaps(observations, min_gap=6.0, slack=2.5):
    """Clock runs and the gaps between them, with the gap classified.

    Returns (stops, holes): stops are (start, end) media spans where the clock
    did not move across a long gap; holes are gaps of 60 s or more (the reader
    not polling) and short gaps the clock ran through.
    """
    runs = []
    current = None
    for obs in observations:
        if obs.clock_s is None:
            continue
        if current is not None and obs.media - current["end"] < 3.0:
            current["end"] = obs.media
            current["values"].append(obs.clock_s)
        else:
            if current is not None:
                runs.append(current)
            current = {"start": obs.media, "end": obs.media, "values": [obs.clock_s]}
    if current is not None:
        runs.append(current)

    stops, holes = [], []
    for before, after in zip(runs, runs[1:]):
        gap = after["start"] - before["end"]
        if gap < min_gap:
            continue
        delta = abs(before["values"][-1] - after["values"][0])
        if gap >= 60.0:
            holes.append((before["end"], after["start"], "big journal gap"))
        elif delta <= slack:
            stops.append((before["end"], after["start"]))
        elif abs(delta - gap) <= slack:
            holes.append((before["end"], after["start"], "clock ran through the gap"))
        else:
            holes.append(
                (
                    before["end"],
                    after["start"],
                    f"ambiguous gap {gap:.1f}s, clock moved {delta:.1f}s",
                )
            )
    return stops, holes, runs


def _frame_transitions(media_id, observations):
    """Hand-verified facts from truth/20261023_game.json, resolved to media."""
    if not os.path.exists(TRUTH_FILE):
        return [], []
    with open(TRUTH_FILE) as handle:
        data = json.load(handle)
    section = (data.get("clips") or {}).get(media_id) or {}
    transitions = []
    for item in section.get("transitions") or []:
        media = item.get("media")
        if media is None and item.get("at"):
            media = _media_from_adm(item["at"], media_id)
        if media is None:
            continue
        transitions.append(
            Transition(
                kind=item["kind"],
                media=float(media),
                value=item.get("value"),
                note=item.get("note", ""),
                verified=bool(item.get("verified", True)),
            )
        )
    stops = [(float(a), float(b)) for a, b in section.get("clock_stops") or []]
    return transitions, stops


def _media_from_adm(stamp, media_id):
    from datetime import datetime

    start = ADT_SEGMENT_START.get(media_id)
    if start is None:
        return None
    return (
        datetime.fromisoformat(stamp) - datetime.fromisoformat(start)
    ).total_seconds()


def _score_transitions(observations):
    """Score and period changes in the journal, at the first poll showing them."""
    transitions = []
    prev = None
    for obs in observations:
        if prev is not None:
            if obs.home is not None and prev.home is not None and obs.home != prev.home:
                transitions.append(
                    Transition("score_home", obs.media, obs.home, "journal")
                )
            if obs.away is not None and prev.away is not None and obs.away != prev.away:
                transitions.append(
                    Transition("score_away", obs.media, obs.away, "journal")
                )
            if (
                obs.period is not None
                and prev.period is not None
                and obs.period != prev.period
            ):
                transitions.append(
                    Transition("period_start", obs.media, obs.period, "journal")
                )
        prev = obs
    return transitions


def _merge_spans(spans, slack=3.0):
    """Overlapping or touching spans merged, sorted."""
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1] + slack:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def load_truth(media_id, strict_frames=True):
    """The reference for a clip: journal observations plus verified frames."""
    observations = _load_journal(media_id)
    stops, holes, runs = _clock_gaps(observations)
    frame_transitions, frame_stops = _frame_transitions(media_id, observations)

    transitions = _score_transitions(observations)
    # A period change is only real when the clock resets with it; a journal
    # blip reading "2" in the middle of period 1 is not a new period.
    period_changes = []
    for trans in transitions:
        if trans.kind != "period_start":
            continue
        before = None
        for obs in observations:
            if obs.media <= trans.media and obs.period is not None:
                before = obs
            elif obs.media > trans.media + 30:
                break
        if before is None or before.period == trans.value:
            continue
        # the clock must start over (down from ~15:00, or a fresh count)
        after = [
            o
            for o in observations
            if trans.media <= o.media <= trans.media + 40 and o.clock_s
        ]
        reset = bool(after) and after[0].clock_s >= 600
        if reset or not strict_frames:
            period_changes.append(trans)
    transitions = [t for t in transitions if t.kind != "period_start"] + period_changes

    # Hand-verified frame facts win over journal-derived ones of the same kind.
    for trans in frame_transitions:
        transitions = [
            t
            for t in transitions
            if not (t.kind == trans.kind and abs(t.media - trans.media) <= 20)
        ]
        transitions.append(trans)

    # Clock stops: the journal gaps classified as stops, plus every span the
    # frames verified (verified ones refine the journal's, they don't replace
    # the rest).
    stops = _merge_spans(sorted(list(stops) + list(frame_stops)))

    # Every stop contributes clock_stop / clock_start transitions; a stop that
    # a verified transition already names (the same edge within 3 s) is not
    # counted twice.
    for start, end in stops:
        if not any(
            t.kind == "clock_stop" and abs(t.media - start) <= 3.0 for t in transitions
        ):
            transitions.append(Transition("clock_stop", start, None, "clock gap", True))
        if not any(
            t.kind == "clock_start" and abs(t.media - end) <= 3.0 for t in transitions
        ):
            transitions.append(Transition("clock_start", end, None, "clock gap", True))

    transitions.sort(key=lambda t: t.media)
    truth = Truth(
        media_id=media_id,
        observations=observations,
        transitions=transitions,
        clock_stops=stops,
    )
    real_holes = [
        (a, b, why)
        for a, b, why in holes
        if not any(start - 3.0 <= a and b <= end + 3.0 for start, end in stops)
    ]
    truth.notes = [
        f"{len(observations)} journal polls, {len(runs)} clock runs",
        f"{len(stops)} clock stops {', '.join(f'{a:.0f}-{b:.0f}s' for a, b in stops)}",
        f"{len(real_holes)} clock gaps with no reference inside: "
        + "; ".join(f"{a:.0f}-{b:.0f}s ({why})" for a, b, why in real_holes),
    ]
    return truth


def save_truth_dump(media_id, path):
    """Write the journal-derived observations next to a report, for audit."""
    observations = _load_journal(media_id)
    with open(path, "w") as handle:
        json.dump([obs.__dict__ for obs in observations], handle, indent=1)
