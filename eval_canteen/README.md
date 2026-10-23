# `eval_canteen` — offline accuracy harness for ScoreSight on Curly's footage

Measures ScoreSight against ground truth on the stadium scoreboard recordings,
so a later ScoreSight change can be scored instead of eyeballed.

This lives in a git worktree of ScoreSight (`~/worktrees/scoresight/eval`, branch
`canteen/eval-harness-20261023`) and does not modify ScoreSight's own source:
everything is under `eval_canteen/`.

## What it does

1. Pushes a slice of a recording into a local UDP port with `ffmpeg -re`
   (real-time pace). A `File` source is consumed as fast as the capture loop
   can read it, which makes `/game`'s clock events and the detection latencies
   meaningless, so the harness never uses one.
2. Starts ScoreSight headless (`QT_QPA_PLATFORM=offscreen`) on its own free
   HTTP port, data directory and log directory.
3. Polls `/json` and `/game?since=<id>` once a second.
4. Scores every field and every transition against the reference on **media
   time** (seconds into the recording), so the wall-clock offset of a run does
   not matter.

## Usage

```sh
cd ~/worktrees/scoresight/eval
nice -n 15 .venv/bin/python eval_canteen/run_eval.py \
  --clip ~/.local/share/canteen-ops/scoreboard-camera/crop/20261023T091022.mkv \
  --variant filtered --engine ppocr --start 0 --duration 900
```

| option | meaning |
|---|---|
| `--variant raw\|filtered` | `filtered` is the live feed's preprocessing (`format=gray,lut=y='clip((val-150)*3.6,0,255)'`); `raw` is the recorder's crop untouched |
| `--engine ppocr\|tesseract` | `ppocr` writes `ocr_model: "ppocr:auto"` (the live setting); `tesseract` writes `1` (Tesseract General Scoreboard) |
| `--cadence` | detections/s; the live profile uses `2.0` |
| `--start`, `--duration` | media seconds to play (played in real time) |
| `--out` | report directory (default `eval_canteen/reports`) |
| `--keep-work` | keep the run's data dir, ScoreSight log, samples and feed command |

Output: `<out>/<name>.json` (full detail), `<out>/<name>.md` (short report) and,
with `--keep-work`, `<out>/work/<name>/` (samples, reference dump, the exact
`ffmpeg` command, ScoreSight's log).

The harness opens only its own free UDP and TCP ports and stops only the
processes it started. It must never be pointed at the live services
(`canteen-scoresight`, `canteen-scoresight-feed`, `canteen-scoreboard-recorder`,
port 18099, udp 23000).

## Scoring rules

Each sample for each field lands in one bucket:

| bucket | meaning |
|---|---|
| `correct` | a good reading (`Success`/`SameNoChange`) equal to the reference; the clock within 1 s |
| `wrong` | a good reading different from the reference |
| `unknown` | no good reading (`Empty`/`FailedFilter`) — the field is unknown, not wrong |
| `no_reference` | the reference knows nothing at that instant (the journal's clock is blank under a minute, the intermission gap), so the sample is excluded |

`accuracy = correct / (correct + wrong)`; `unknown rate = unknown / (correct + wrong + unknown)`.

Transitions are matched within `MATCH_WINDOW` (25 s for scores and period
changes, 20 s for clock start/stop) and reported with the signed latency
(detected media time minus reference media time). The run is judged only from
its first sample to the end of the media it played: ScoreSight's first cycles
learn the board's state and emit a start-of-period/clock-start that are not
detections, and the feed's end freezes the clock.

The wall-clock → media offset is fitted per run by aligning its clock readings
with the reference clock (reported as `offset_seconds` with the number of
aligned clock samples).

## Ground truth

`truth/20261023_game.json` holds the hand-verified facts (score changes, the
period change, every clock stop), each checked by extracting the frame with
`ffmpeg -ss` and viewing it. `truth.py` adds the homegrown reader's journal
(`~/.local/state/canteen-ops/scoreboard-reader/20261023-game-v1fix/polls`):

* **scores and period** throughout the clip, at the first poll showing them;
* **clock** second by second, with each long journal gap classified by whether
  the clock moved across it. A gap where the clock moved ≤1 s is a stop; a gap
  where it moved about as much as the gap lasted is a reader hole (not a
  stop); a gap of 60 s or more is the intermission or a reader outage.

The journal is a reference, not gospel: its clock is blank under a minute (the
board switches to tenths) and its `period` reads as if the next period had
started through the intermission (corrected by requiring a 15:00 reset).

The reference is keyed on media time; `ADT_SEGMENT_START` in `truth.py` maps a
clip's name to its segment start, and the journal's `media_pts_seconds` is
used directly where present.

## Adding a clip

1. Add the clip's segment start to `ADT_SEGMENT_START` in `truth.py` if the
   journal has no `media_pts_seconds` for it.
2. Verify the facts a journal can only approximate (score changes, period
   changes, clock stops) on frames and add them to `truth/20261023_game.json`
   under `clips.<file name>`.
3. Run the harness. The report lists every wrong reading with its media time,
   which is what to re-check on a frame.
