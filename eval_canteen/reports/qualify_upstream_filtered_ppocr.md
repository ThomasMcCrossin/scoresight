# ScoreSight eval — 20261023T091022.mkv · filtered · ppocr

| | |
|---|---|
| clip | 20261023T091022.mkv |
| variant | filtered |
| engine | ppocr |
| cadence | 2.0 |
| start_media | 0.0 |
| duration | 900.0 |
| samples | 903 |
| offset_seconds | 1.0 |
| aligned_clock_samples | 892 |

## Field accuracy

| field | correct | wrong | unknown | not judged | accuracy | unknown rate |
|---|---|---|---|---|---|---|
| Period | 896 | 0 | 4 | 0 | 100.0% | 0.4% |
| Home Score | 896 | 0 | 4 | 0 | 100.0% | 0.4% |
| Away Score | 896 | 0 | 4 | 0 | 100.0% | 0.4% |
| Time | 785 | 0 | 8 | 107 | 100.0% | 1.0% |

*not judged*: samples the reference cannot score — a clock within 2.5 s of a start/stop (its timing is the transition latency's job), the board's blank clock under a minute, the intermission.

## Transitions

| kind | expected | detected | missed | false | mean latency (s) | max latency (s) |
|---|---|---|---|---|---|---|
| clock_start | 11 | 11 | 0 | 2 | -0.43 | -0.06 |
| clock_stop | 11 | 11 | 0 | 1 | +1.23 | +1.62 |
| score_home | 1 | 1 | 0 | 0 | +0.85 | +0.85 |

## Wrong readings (0)

None.

## Reference notes

- 1025 journal polls, 24 clock runs
- 20 clock stops 160-189s, 232-255s, 351-387s, 461-484s, 489-522s, 605-631s, 702-744s, 784-815s, 837-838s, 843-875s, 879-897s, 1043-1141s, 1152-1176s, 1195-1228s, 1255-1284s, 1292-1322s, 1382-1406s, 1539-1565s, 1640-1679s, 1738-1778s
- 1 clock gaps with no reference inside: 914-1043s (big journal gap)
