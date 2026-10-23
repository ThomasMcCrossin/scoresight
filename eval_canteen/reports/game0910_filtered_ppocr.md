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
| offset_seconds | 2.0 |
| aligned_clock_samples | 895 |

## Field accuracy

| field | correct | wrong | unknown | no reference | accuracy | unknown rate |
|---|---|---|---|---|---|---|
| Period | 897 | 0 | 2 | 0 | 100.0% | 0.2% |
| Home Score | 897 | 0 | 2 | 0 | 100.0% | 0.2% |
| Away Score | 897 | 0 | 2 | 0 | 100.0% | 0.2% |
| Time | 787 | 0 | 5 | 107 | 100.0% | 0.6% |

## Transitions

| kind | expected | detected | missed | false | mean latency (s) | max latency (s) |
|---|---|---|---|---|---|---|
| clock_start | 11 | 11 | 0 | 1 | -0.02 | +0.51 |
| clock_stop | 11 | 11 | 0 | 1 | +1.58 | +1.95 |
| score_home | 1 | 1 | 0 | 0 | +0.81 | +0.81 |

## Wrong readings (0)

None.

## Reference notes

- 1025 journal polls, 24 clock runs
- 20 clock stops 160-189s, 232-255s, 351-387s, 461-484s, 489-522s, 605-631s, 702-744s, 784-815s, 837-838s, 843-875s, 879-897s, 1043-1141s, 1152-1176s, 1195-1228s, 1255-1284s, 1292-1322s, 1382-1406s, 1539-1565s, 1640-1679s, 1738-1778s
- 1 clock gaps with no reference inside: 914-1043s (big journal gap)
