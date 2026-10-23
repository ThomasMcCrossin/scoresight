# Curly's ScoreSight fork — qualification

## Scored runs (09:10 clip, first 900 s)

| measure | filtered/ppocr (upstream) | filtered/ppocr (fork) | levels/ppocr (fork) |
|---|---|---|---|
| build | `upstream` | `fork` | `fork` |
| offset (s) | 1.0 | 0.25 | 1.0 |
| Period accuracy | 100.0% (wrong 0, unknown 0.4%) | 100.0% (wrong 0, unknown 0.2%) | 100.0% (wrong 0, unknown 0.3%) |
| Home Score accuracy | 100.0% (wrong 0, unknown 0.4%) | 100.0% (wrong 0, unknown 0.2%) | 99.9% (wrong 1, unknown 0.3%) |
| Away Score accuracy | 100.0% (wrong 0, unknown 0.4%) | 100.0% (wrong 0, unknown 0.2%) | 100.0% (wrong 0, unknown 0.3%) |
| Time accuracy | 100.0% (wrong 0, unknown 1.0%) | 100.0% (wrong 0, unknown 0.5%) | 100.0% (wrong 0, unknown 0.5%) |
| score_home | 1/1 detected, 0 false, +0.8s | 1/1 detected, 0 false, +1.1s | 1/1 detected, 0 false, +1.4s |
| clock_start | 11/11 detected, 2 false, -0.4s | 11/11 detected, 2 false, -0.3s | 11/11 detected, 2 false, +0.2s |
| clock_stop | 11/11 detected, 1 false, +1.2s | 11/11 detected, 1 false, +1.4s | 11/11 detected, 1 false, +1.8s |

## Checks against the baseline

| check | baseline | verdict | notes |
|---|---|---|---|
| no field accuracy below baseline (filtered) | archived | PASS | — |
| no new false score events (filtered) | archived | PASS | — |
| latency within 0.5 s of baseline (filtered) | archived | PASS | — |
| no field accuracy below baseline (levels) | archived | FAIL | home accuracy 99.9% below the baseline's 100.0% |
| no new false score events (levels) | archived | PASS | — |
| latency within 0.5 s of baseline (levels) | archived | FAIL | score_home mean latency +1.37s vs baseline +0.81s |
| no field accuracy below baseline (filtered) | control | PASS | — |
| no new false score events (filtered) | control | PASS | — |
| latency within 0.5 s of baseline (filtered) | control | PASS | — |
| no field accuracy below baseline (levels) | control | FAIL | home accuracy 99.9% below the baseline's 100.0% |
| no new false score events (levels) | control | PASS | — |
| latency within 0.5 s of baseline (levels) | control | FAIL | clock_start mean latency +0.17s vs baseline -0.43s; clock_stop mean latency +1.85s vs baseline +1.23s; score_home mean latency +1.37s vs baseline +0.85s |

## Incident replays (10:10 hour, filtered)

| incident | upstream 0.4.1 | fork | evidence |
|---|---|---|---|
| a clock followed (not reproduced by either) | engine vs board 0.0 s, freeze 0.0 s | engine vs board -1.0 s, freeze 0.0 s | frames + /game |
| b new game, no OT/correction | new_game 0, OT 2, corrections 1 | new_game 1, OT 2, corrections 0 | frames |
| c one period end on the run-down, none on the reset | period_end 1, period_start 0 | period_end 1, period_start 0 | frames + /game |
| d goals | 7/7 goals, 0 false | 7/7 goals, 0 false | frames |

Replay reports:

- `fork_a_330_660` (fork, media 330s +330s) — `reports/replay/fork_a_330_660.json`
- `fork_b_660_850` (fork, media 660s +190s) — `reports/replay/fork_b_660_850.json`
- `fork_c_1010_1070` (fork, media 1010s +60s) — `reports/replay/fork_c_1010_1070.json`
- `fork_d12_1250_1460` (fork, media 1250s +210s) — `reports/replay/fork_d12_1250_1460.json`
- `fork_d3_1780_1840` (fork, media 1780s +60s) — `reports/replay/fork_d3_1780_1840.json`
- `fork_d4_2210_2260` (fork, media 2210s +50s) — `reports/replay/fork_d4_2210_2260.json`
- `fork_d5_3400_3600` (fork, media 3400s +200s) — `reports/replay/fork_d5_3400_3600.json`
- `upstream_a_330_660` (upstream, media 330s +330s) — `reports/replay/upstream_a_330_660.json`
- `upstream_b_660_850` (upstream, media 660s +190s) — `reports/replay/upstream_b_660_850.json`
- `upstream_c_1010_1070` (upstream, media 1010s +60s) — `reports/replay/upstream_c_1010_1070.json`
- `upstream_d12_1250_1460` (upstream, media 1250s +210s) — `reports/replay/upstream_d12_1250_1460.json`
- `upstream_d3_1780_1840` (upstream, media 1780s +60s) — `reports/replay/upstream_d3_1780_1840.json`
- `upstream_d4_2210_2260` (upstream, media 2210s +50s) — `reports/replay/upstream_d4_2210_2260.json`
- `upstream_d5_3400_3600` (upstream, media 3400s +200s) — `reports/replay/upstream_d5_3400_3600.json`

## The seven fixes, and what was seen of each

| fix | how it was checked | result |
|---|---|---|
| Picture levels (black/white point, gamma) | `tests/test_pipeline_picture_levels.py`; the LUT compared with the live ffmpeg lut on six frames of the 09:10 clip; a 900 s run with the levels set | 22 tests pass. The in-app table and the ffmpeg lut differ by at most one gray level (mean abs 0.018, 98% of pixels identical). The run reads every field but one Home Score sample, which lagged a poll |
| `captured_at` / `latency_ms` and `/health` | a private headless instance on a live feed: `/health` and `/json` | `/health` `ok: true`, `fps 24.61`, `nominal_fps 5.0`, engine `ready` (`ppocr:small`), `source_open: true`, `age_s 0.97`; `/json` `Time` carries `captured_at 2026-10-23T12:21:52.021-03:00` and `latency_ms 423.8` -- both read on a private instance fed a 60 s slice, not inferred from the code |
| Time `M:SS.t` preset | the preset's expression against the clock texts the board shows under a minute | accepts `0:09`, `0:09.8` and `9.8`. **Not exercised by this board**: across 4,872 clock readings in every run the board shows only `M:SS` (0 in the `M:SS.t` form), so the fork's Time accuracy here says nothing about the new preset |
| No settings clobber, `--settings-read-only` | 67 storage/settings tests; a real run with the flag, comparing the profile's checksum before and after | the profile is byte-identical after a full run; the tests pass |
| Clock-hold deadlock | the replay of the span the live service froze in (incident a), plus `tests/test_game_state.py` | the replay does **not** reproduce the live freeze on either build: upstream 0.4.1 also follows the board across media 330-650 (worst 0.0 s, no freeze), so the deadlock needs conditions this clip does not carry. The fix rests on the unit tests and on reading the code path, not on replay |
| `new_game` after a final | the replay of the final and the next game's board (incident b), plus three `new_game` tests | no score correction, and one `new_game` when the board gives the first period at 0-0; it still logs Start/End of OT while the board itself shows a 4th period |
| Period end only on a run-down | the replay of the pre-game clock (incident c), plus the flick test | the board runs 0:44 -> 0:00 at about a second a second, holds 0:00 for 6 s, then resets to 15:00; both builds log one period end at the 0:00 and no period start at the reset, which is the correct reading of that board |

The fork's own suite: 2026 passed, 15 skipped, 1 failed (`test_the_outputs_are_destinations_over_their_pages`). **The same test fails on upstream 0.4.1 at 0388a1a**, so it is an environment failure (a window size hint under `offscreen`), not a fork regression.

## Recommendation

- **Feed**: keep the ffmpeg lut. `levels` needs the profile keys below and, on this footage, is no better: it falls below the filtered run on home. Nothing measured argues for moving the suppression into the app.
- **Deploy the fork as the live service** on the filtered feed, with the profile unchanged apart from the new keys the fork adds (they default to off).
- **Do not enable picture levels in production yet.** The variant is sound and its LUT matches the ffmpeg lut to one gray level, but on this footage it bought nothing and cost one lagging score reading, so switching the feed to raw + in-app levels is a change with no measured benefit.

The check the fork does not fully pass is incident b's overtime: it still logs Start of OT / End of OT when the board itself shows a 4th period, which is the board's state and not a fork invention. It no longer logs the score correction, and it does start a new game when the board gives it the first period at 0-0.

### Profile settings

The live profile (`~/.local/share/canteen-scoresight/data/scoresight-stadium.json`),
unchanged by the fork:

```json
{ "source_selected": {"type": "URL", "value": "udp://127.0.0.1:23000"},
  "detection_cadence": 2.0, "sport": "hockey", "ocr_model": "ppocr:auto",
  "update_on_change": true, "disable_update_checks": true,
  "boxes": Time 179,68,82,36 / Home 73,87,44,33 / Away 322,93,42,33 / Period 211,124,20,26 }
```

Picture levels stay off (absent from the profile):
`picture_levels: false` (or absent), `picture_black_point: 0`,
`picture_white_point: 255`, `picture_gamma: 1.0`.

If the feed is ever switched to the recorder's crop without the lut,
set the levels that reproduce it exactly: `picture_levels: true`,
`picture_black_point: 150`, `picture_white_point: 221`,
`picture_gamma: 1.0`.

