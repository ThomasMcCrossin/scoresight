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
| a clock followed | not replayed | engine vs board -1.0 s, freeze 0.0 s | frames |
| b new game, no OT/correction | new_game 0, OT 2, corrections 1 | new_game 1, OT 2, corrections 0 | frames |
| c no period end on a flick | not replayed | period_end 1, period_start 0 | frames + /game |
| d goals | 0/0 goals, 0 false | 6/6 goals, 0 false | frames |

Replay reports:

- `fork_a_330_660` (fork, media 330s +330s) — `reports/work/replay/fork_a_330_660.json`
- `fork_b_660_850` (fork, media 660s +190s) — `reports/work/replay/fork_b_660_850.json`
- `fork_c_1010_1070` (fork, media 1010s +60s) — `reports/work/replay/fork_c_1010_1070.json`
- `fork_d12_1250_1460` (fork, media 1250s +210s) — `reports/work/replay/fork_d12_1250_1460.json`
- `fork_d3_1780_1840` (fork, media 1780s +60s) — `reports/work/replay/fork_d3_1780_1840.json`
- `fork_d4_2210_2260` (fork, media 2210s +50s) — `reports/work/replay/fork_d4_2210_2260.json`
- `upstream_a_330_660` (upstream, media 330s +330s) — `reports/work/replay/upstream_a_330_660.json` — **recorded no samples (rerun)**
- `upstream_b_660_850` (upstream, media 660s +190s) — `reports/work/replay/upstream_b_660_850.json`

