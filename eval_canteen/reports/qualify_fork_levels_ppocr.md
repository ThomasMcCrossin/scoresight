# ScoreSight eval — 20261023T091022.mkv · levels · ppocr

| | |
|---|---|
| clip | 20261023T091022.mkv |
| variant | levels |
| engine | ppocr |
| cadence | 2.0 |
| start_media | 0.0 |
| duration | 900.0 |
| samples | 903 |
| offset_seconds | 1.0 |
| aligned_clock_samples | 897 |

## Field accuracy

| field | correct | wrong | unknown | not judged | accuracy | unknown rate |
|---|---|---|---|---|---|---|
| Period | 897 | 0 | 3 | 0 | 100.0% | 0.3% |
| Home Score | 896 | 1 | 3 | 0 | 99.9% | 0.3% |
| Away Score | 897 | 0 | 3 | 0 | 100.0% | 0.3% |
| Time | 789 | 0 | 4 | 107 | 100.0% | 0.5% |

*not judged*: samples the reference cannot score — a clock within 2.5 s of a start/stop (its timing is the transition latency's job), the board's blank clock under a minute, the intermission.

## Transitions

| kind | expected | detected | missed | false | mean latency (s) | max latency (s) |
|---|---|---|---|---|---|---|
| clock_start | 11 | 11 | 0 | 2 | +0.17 | +0.48 |
| clock_stop | 11 | 11 | 0 | 1 | +1.85 | +2.34 |
| score_home | 1 | 1 | 0 | 0 | +1.37 | +1.37 |

## Wrong readings (1)

| media (s) | field | read | expected | state |
|---|---|---|---|---|
| 496.1 | Home Score | `1` | `2` | SameNoChange |

## Reference notes

- 1025 journal polls, 24 clock runs
- 20 clock stops 160-189s, 232-255s, 351-387s, 461-484s, 489-522s, 605-631s, 702-744s, 784-815s, 837-838s, 843-875s, 879-897s, 1043-1141s, 1152-1176s, 1195-1228s, 1255-1284s, 1292-1322s, 1382-1406s, 1539-1565s, 1640-1679s, 1738-1778s
- 1 clock gaps with no reference inside: 914-1043s (big journal gap)
