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
| offset_seconds | 1.75 |
| aligned_clock_samples | 896 |

## Field accuracy

| field | correct | wrong | unknown | no reference | accuracy | unknown rate |
|---|---|---|---|---|---|---|
| Period | 898 | 0 | 2 | 0 | 100.0% | 0.2% |
| Home Score | 898 | 0 | 2 | 0 | 100.0% | 0.2% |
| Away Score | 898 | 0 | 2 | 0 | 100.0% | 0.2% |
| Time | 796 | 0 | 5 | 99 | 100.0% | 0.6% |

## Transitions

| kind | expected | detected | missed | false | mean latency (s) | max latency (s) |
|---|---|---|---|---|---|---|
| clock_start | 10 | 10 | 0 | 3 | -0.32 | -0.03 |
| clock_stop | 10 | 10 | 0 | 2 | +1.44 | +1.70 |
| score_home | 1 | 1 | 0 | 0 | +0.56 | +0.56 |

## Wrong readings (0)

None.

## Reference notes

- 1025 journal polls, 24 clock runs
- 19 clock stops 160-189s, 232-255s, 351-387s, 461-484s, 489-522s, 605-631s, 702-744s, 784-815s, 843-875s, 879-897s, 1043-1141s, 1152-1176s, 1195-1228s, 1255-1284s, 1292-1322s, 1382-1406s, 1539-1565s, 1640-1679s, 1738-1778s
- 1 clock gaps with no reference inside: 914-1043s (big journal gap)
