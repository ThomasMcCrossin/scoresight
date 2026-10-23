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
| `--rescore SAMPLES` | score a saved `samples.json` with the current scorer, without running ScoreSight (the clip, `--start` and `--duration` still come from the arguments) |

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

Samples are taken at 1 Hz from `/json`, which is what a consumer polling the
live server sees; a misread that lasts under a second between polls is not
counted as wrong (but a misread that reaches `/game`'s event log still shows
up as a false transition).

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

## Checking a wrong reading on a frame

```sh
nice -n 15 python eval_canteen/frame_check.py \
  --clip .../20261023T091022.mkv --at 496 1042 1255 --out /tmp/eval_frames --scale 630:360
```

writes one PNG per media time (and `montage.png`), which is how the reference
entries in `truth/20261023_game.json` were verified.

## Comparing runs

```sh
nice -n 15 python eval_canteen/compare.py eval_canteen/reports/*.json
```

puts the field accuracies and transition counts of several reports side by
side, so a ScoreSight change is compared against the run it should improve.

## Coverage today

Only `20261023T091022.mkv` (the game hour) has reference coverage: the reader
journal holds 1025 polls for that segment and none for the 08:10 warm-up or the
10:10 file. `run_eval.py` refuses a clip with no observations in
`truth/20261023_game.json` under `clips.<file name>`. Adding the 10:10 hour (home 4
by ~10:00, P3 from 10:05, home 5 at 10:09:24) means writing its verified
transitions the same way, or running a reader over it to produce a journal.

## Adding a clip

1. Add the clip's segment start to `ADT_SEGMENT_START` in `truth.py` if the
   journal has no `media_pts_seconds` for it.
2. Verify the facts a journal can only approximate (score changes, period
   changes, clock stops) on frames and add them to `truth/20261023_game.json`
   under `clips.<file name>`.
3. Run the harness. The report lists every wrong reading with its media time,
   which is what to re-check on a frame.

## Picture levels: the `levels` variant

The live feed suppresses a board's ghost segments in ffmpeg (the `filtered`
variant's lut). The fork can do it inside ScoreSight instead, in
`TimerThread.adjust_frame`, and `levels` measures that: the recorder's crop goes
in untouched and the profile carries

```json
"picture_levels": true, "picture_black_point": 150,
"picture_white_point": 221, "picture_gamma": 1.0
```

which is the affine stretch `clip((v-150)*255/(221-150),0,255)` -- the ffmpeg
lut's `*3.6` to within 0.2% (the white point where `clip((v-150)*3.6)` reaches
255 is 220.8). Measured on the 09:10 clip at six times, the in-app table and
the ffmpeg lut differ by at most one gray level (mean absolute difference
0.018, 98% of pixels identical), so the two variants see the same picture and a
difference between their runs is not the levels themselves.

A build without picture levels cannot run this variant: the harness imports the
build's own `defaults` and `camera_thread` and refuses rather than silently
scoring `raw`.

## Replaying the 10:10 hour

`replay_1010.py` runs a slice of a clip against any checkout (`--build`) with
the same feed variants, records every `/json` and `/game` poll with the media
time ffmpeg reported for it, and `check_incidents.py` answers the incidents the
live logs raised. Neither scores anything: with no reader journal for that
segment there is no per-field reference, so the checks are readings of the
record against facts verified on frames.

Two details matter for a replay to be believable:

* The feed seeks with `-ss` before `-i`, so ffmpeg's `out_time` restarts at 0:
  media = `--start` + `out_time`. The progress file is watched while the feed
  runs, because its lines carry no timestamp of their own.
* ScoreSight, a URL source, opens the stream once. If the feed's first frames
  are not decodable yet, OpenCV times out ("Stream timeout triggered") and the
  app never reopens, so the run waits for a live `/json` reading before taking
  the window, feeding `--lead-in` seconds first (discarded from the record).
