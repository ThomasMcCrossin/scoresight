# ScoreSight eval — 20261023T091022.mkv · raw · ppocr

| | |
|---|---|
| clip | 20261023T091022.mkv |
| variant | raw |
| engine | ppocr |
| cadence | 2.0 |
| start_media | 0.0 |
| duration | 900.0 |
| samples | 902 |
| offset_seconds | 0.0 |
| aligned_clock_samples | 703 |

## Field accuracy

| field | correct | wrong | unknown | not judged | accuracy | unknown rate |
|---|---|---|---|---|---|---|
| Period | 811 | 0 | 88 | 1 | 100.0% | 9.8% |
| Home Score | 438 | 395 | 66 | 1 | 52.6% | 7.3% |
| Away Score | 458 | 439 | 2 | 1 | 51.1% | 0.2% |
| Time | 631 | 81 | 105 | 83 | 88.6% | 12.9% |

*not judged*: samples the reference cannot score — a clock within 2.5 s of a start/stop (its timing is the transition latency's job), the board's blank clock under a minute, the intermission.

## Transitions

| kind | expected | detected | missed | false | mean latency (s) | max latency (s) |
|---|---|---|---|---|---|---|
| clock_start | 11 | 11 | 0 | 19 | -0.85 | +0.88 |
| clock_stop | 11 | 9 | 2 | 21 | +0.32 | +1.90 |
| score_away | 0 | 0 | 0 | 40 | n/a | n/a |
| score_home | 1 | 1 | 0 | 24 | +3.04 | +3.04 |

## Wrong readings (915)

| media (s) | field | read | expected | state |
|---|---|---|---|---|
| 3.0 | Home Score | `8` | `1` | Success |
| 4.0 | Home Score | `8` | `1` | Success |
| 5.0 | Home Score | `8` | `1` | SameNoChange |
| 6.0 | Home Score | `8` | `1` | SameNoChange |
| 7.0 | Home Score | `8` | `1` | SameNoChange |
| 9.0 | Home Score | `8` | `1` | SameNoChange |
| 10.0 | Home Score | `80` | `1` | Success |
| 11.0 | Home Score | `80` | `1` | SameNoChange |
| 12.0 | Home Score | `80` | `1` | SameNoChange |
| 13.0 | Home Score | `80` | `1` | SameNoChange |
| 14.0 | Home Score | `80` | `1` | SameNoChange |
| 15.0 | Home Score | `80` | `1` | SameNoChange |
| 16.0 | Home Score | `80` | `1` | SameNoChange |
| 17.0 | Home Score | `80` | `1` | SameNoChange |
| 18.0 | Home Score | `80` | `1` | SameNoChange |
| 19.0 | Home Score | `80` | `1` | SameNoChange |
| 20.0 | Home Score | `80` | `1` | SameNoChange |
| 21.0 | Home Score | `80` | `1` | SameNoChange |
| 22.0 | Home Score | `80` | `1` | SameNoChange |
| 22.0 | Away Score | `80` | `0` | Success |
| 23.0 | Home Score | `80` | `1` | Success |
| 23.0 | Away Score | `80` | `0` | SameNoChange |
| 24.0 | Home Score | `80` | `1` | SameNoChange |
| 24.0 | Away Score | `80` | `0` | SameNoChange |
| 25.0 | Home Score | `80` | `1` | Success |
| 25.0 | Away Score | `80` | `0` | SameNoChange |
| 26.0 | Home Score | `80` | `1` | SameNoChange |
| 26.0 | Away Score | `80` | `0` | SameNoChange |
| 27.0 | Home Score | `80` | `1` | SameNoChange |
| 28.0 | Home Score | `80` | `1` | SameNoChange |
| 29.0 | Home Score | `80` | `1` | SameNoChange |
| 30.0 | Home Score | `80` | `1` | SameNoChange |
| 31.0 | Home Score | `80` | `1` | SameNoChange |
| 32.0 | Home Score | `80` | `1` | SameNoChange |
| 32.0 | Away Score | `80` | `0` | SameNoChange |
| 33.0 | Away Score | `80` | `0` | SameNoChange |
| 34.0 | Away Score | `80` | `0` | SameNoChange |
| 35.0 | Home Score | `80` | `1` | SameNoChange |
| 35.0 | Away Score | `80` | `0` | SameNoChange |
| 36.0 | Home Score | `80` | `1` | SameNoChange |
| 36.0 | Away Score | `80` | `0` | SameNoChange |
| 37.0 | Home Score | `80` | `1` | Success |
| 37.0 | Away Score | `80` | `0` | SameNoChange |
| 38.0 | Home Score | `80` | `1` | SameNoChange |
| 38.0 | Away Score | `80` | `0` | SameNoChange |
| 39.0 | Home Score | `80` | `1` | SameNoChange |
| 39.0 | Away Score | `80` | `0` | SameNoChange |
| 40.0 | Home Score | `80` | `1` | SameNoChange |
| 41.0 | Home Score | `80` | `1` | SameNoChange |
| 42.0 | Home Score | `80` | `1` | SameNoChange |
| 43.0 | Home Score | `80` | `1` | SameNoChange |
| 44.0 | Home Score | `80` | `1` | SameNoChange |
| 45.0 | Home Score | `8` | `1` | SameNoChange |
| 46.0 | Home Score | `8` | `1` | SameNoChange |
| 47.0 | Home Score | `8` | `1` | Success |
| 48.0 | Home Score | `8` | `1` | SameNoChange |
| 49.0 | Home Score | `8` | `1` | SameNoChange |
| 50.0 | Home Score | `8` | `1` | SameNoChange |
| 51.0 | Home Score | `8` | `1` | SameNoChange |
| 52.0 | Home Score | `8` | `1` | SameNoChange |
| … | 855 more in the JSON report | | | |

## Reference notes

- 1025 journal polls, 24 clock runs
- 20 clock stops 160-189s, 232-255s, 351-387s, 461-484s, 489-522s, 605-631s, 702-744s, 784-815s, 837-838s, 843-875s, 879-897s, 1043-1141s, 1152-1176s, 1195-1228s, 1255-1284s, 1292-1322s, 1382-1406s, 1539-1565s, 1640-1679s, 1738-1778s
- 1 clock gaps with no reference inside: 914-1043s (big journal gap)
