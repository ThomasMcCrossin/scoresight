---
title: Game & Sports
parent: Guides
nav_order: 9
description: "Choose the sport and ScoreSight follows the game from the scoreboard: each score, the start and end of each period, the clock starting and stopping, the final buzzer, and the points of each period."
---

# Game & Sports
{: .no_toc }

Choose the **sport** being played and ScoreSight follows the **game**, not only the readings: it notices each score (who scored and how many points), the start and the end of each period, the clock starting and stopping, fouls and timeouts changing, and the final buzzer. It keeps them in the game's **event log**, adds up the **points of each period** (the line score), and serves it all at [`/game`](#the-game-over-http).

This is the first step of the [roadmap](https://github.com/royshil/scoresight/issues/116): graphics that react to the game (a goal animation, a line score, end-of-period cards), automatic highlights and player stats build on it. For now, following the game doesn't change what the outputs get.

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Choose the sport

In the **Box** tab of the inspector, under **All boxes**, choose the **Sport**. *None* (the default) follows nothing, as in earlier versions.

| Sport | Score changes that make sense | Periods | Clock |
|---|---|---|---|
| Basketball | +1, +2, +3 | 4 quarters (Q1–Q4, then OT) | counts down |
| Basketball (halves) | +1, +2, +3 | 2 halves (H1, H2, then OT) | counts down |
| Soccer | +1 | 2 halves (H1, H2) | counts up |
| Ice hockey | +1 | 3 periods (P1–P3, then OT) | counts down |
| American football | +1, +2, +3, +6, +7, +8 | 4 quarters (Q1–Q4, then OT) | counts down |
| Volleyball | +1 (the scores start again each set) | up to 5 sets | none |

A clock that counts the other way (a youth soccer board counting down, for example) is noticed after a few seconds.

Under the sport, a line says which fields ScoreSight follows and where the game is, for example:

> Follows Home Score, Away Score, Time, Period
> Q2 · 24–21 · clock running

Hover it for the latest events. **New game** forgets the game: the event log and the points per period start over, and the values are learned again from the next readings.

## Which fields are followed

ScoreSight finds each field by its **name**. The standard fields (*Home Score*, *Away Score*, *Time*, *Period*, *Home Fouls*, *Away Fouls*, *Shot Clock*) are followed as they are, and so are the usual variants:

| Field | Names (case, spaces and `_` don't matter) |
|---|---|
| Home score | Home Score, Score Home, Home, Home Points |
| Away score | Away Score, Guest Score, Visitor Score, Visitors Score, Score Away, Away, Guest, Visitor |
| Clock | Time, Clock, Game Clock, Game Time, Timer |
| Period | Period, Quarter, Qtr, Half, Set |
| Shot clock | Shot Clock, Shot Time, Play Clock |
| Fouls | Home Fouls, Away Fouls (or Guest / Visitor Fouls) |
| Timeouts | Home Timeouts, Away Timeouts (or Guest / Visitor Timeouts, Home TOL, Away TOL) |

Rename a custom field to one of these names to have it followed. The sport decides which ones are used: soccer has no fouls on the board, volleyball has no clock.

The values are read as a scoreboard shows them: scores `0`–`999`, the clock as `12:00`, `4:32`, `45.3` or `0:09.8`, the period as `2`, `2nd`, `Q2`, `P3`, `Set 4`, `OT` or `OT2`.

## Wrong readings don't make events

A misread must not become a "score". So a changed value counts only once it has been **read twice in a row**: a reading that flickers for one cycle makes no event.

A change the sport doesn't allow counts only once it has been read **steadily for 3 seconds**:
- a score going up by 5 in basketball, or 21 becoming 81;
- a score going down;
- a period skipped;
- the clock jumping.

A real correction (the scorer's table fixing a score) is steady, so it still counts, as a *corrected* score. A misread isn't.

A value held with [Hold value](boxes.md#hold-value) counts as the value, so a held correction counts too. The game is followed while the outputs are paused.

## Events

| Event | When |
|---|---|
| **Score** | A team's score changed: *Home +3 (24–21)*, or *Home score corrected to 22* |
| **Start of a period** | The period went up: *Start of Q2* |
| **End of a period** | A clock that counts down reached 0:00, or the period went up: *End of Q2 (34–30)* |
| **Final** | The clock reached 0:00 at the end of the last period (or of an overtime), stayed there for 3 seconds, and the scores aren't tied: *Final (64–58)* |
| **Clock started / stopped** | The clock moved after standing still, or stood still for about 2 seconds |
| **Fouls, timeouts** | A team's fouls or timeouts changed |

The events go to the log (**Tools › View log**): the clock's at the debug level, because they come at every whistle.

Limits:
- **Final** needs a clock that counts down, so soccer and volleyball games have no final event yet.
- The **points of each period** need a period field. They count from when ScoreSight started following the game, so they are marked complete only when it saw the game start at 0–0 in the first period.

## The game over HTTP

`http://<scoresight-ip>:18099/game` returns the game as JSON:

```json
{
  "sport": "basketball",
  "roles": {"home_score": "Home Score", "away_score": "Away Score", "clock": "Time", "period": "Period"},
  "home": {"score": 24, "fouls": 3, "timeouts": null},
  "away": {"score": 21, "fouls": 5, "timeouts": null},
  "period": 2, "period_label": "Q2",
  "clock": "4:32", "clock_running": true, "shot_clock": "14",
  "line_score": [
    {"period": 1, "label": "Q1", "home": 18, "away": 15},
    {"period": 2, "label": "Q2", "home": 6, "away": 6}
  ],
  "line_score_complete": true,
  "final": false,
  "events": [
    {"id": 41, "kind": "score", "text": "Home +3 (24–21)", "team": "home", "delta": 3,
     "value": 24, "home": 24, "away": 21, "period": 2, "period_label": "Q2",
     "clock": "4:32", "at": 1760300000.5}
  ]
}
```

- `events` is the game's event log, oldest first. Each event has an `id`, so polling `/game?since=41` returns only the events after event 41.
- `kind` is one of `score`, `period_start`, `period_end`, `final`, `clock_start`, `clock_stop`, `fouls` or `timeouts`.
- `at` is the time in seconds since 1970 (UTC).

Like the other endpoints, `/game` doesn't change while the outputs are paused.

## Settings

The sport is saved as `sport` in the settings file (see [Settings, Files & Command Line](configuration.md)). The game itself isn't saved: a new session starts a new game.
