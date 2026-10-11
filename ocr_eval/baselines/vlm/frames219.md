# OCR evaluation: VLMs reading whole frames: all 219 photos of textocr_scoreboards (CPU)

Created 2026-10-10T22:17:18+00:00 with harness v1 on Windows 11 AMD64, Python 3.13.2.

Exact = normalized exact match; Digits = same digits ignoring separators; CER = character error rate; Empty = no output; Post-filter = exact match after ScoreSight's whitelist and format regex for the field type. Percentages with 95% confidence intervals (Wilson; CER: bootstrap). Latency per crop in ms, p50 / p95.

## textocr_scoreboards (1276 crops)

Real scoreboard and clock crops cut from Open Images photos (CC BY), with TextOCR's human transcriptions.

| Engine:variant | Exact % | Digits % | CER % | Empty % | Post-filter exact % | ms single | ms batch | Load s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen-vl:qwen3.5-0.8b@frames-boxes | 31.5 (29.0–34.1) | 32.4 | 77.3 (72.2–82.2) | 0.2 | 31.2 (28.7–33.8) | – | 1011.9 / 2519.0 | 4.66 |

### By field type (exact %, 95% CI)

| Engine:variant | clock (n=139) | number (n=948) | other (n=4) | text (n=185) |
|---|---:|---:|---:|---:|
| qwen-vl:qwen3.5-0.8b@frames-boxes | 61.9 (53.6–69.5) | 29.6 (26.8–32.6) | 0.0 (0.0–49.0) | 18.9 (13.9–25.2) |

### By display technology (exact %, 95% CI)

| Engine:variant | broadcast (n=69) | bulb (n=60) | dotmatrix (n=458) | flip (n=94) | lcd (n=74) | led7 (n=353) | printed (n=168) |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen-vl:qwen3.5-0.8b@frames-boxes | 17.4 (10.2–28.0) | 28.3 (18.5–40.8) | 32.8 (28.6–37.2) | 13.8 (8.3–22.2) | 35.1 (25.2–46.5) | 41.9 (36.9–47.1) | 21.4 (15.9–28.2) |

### By split (exact %, 95% CI)

| Engine:variant | dev (n=268) | test (n=1008) |
|---|---:|---:|
| qwen-vl:qwen3.5-0.8b@frames-boxes | 29.5 (24.3–35.2) | 32.0 (29.2–35.0) |

<details><summary>Errors of qwen-vl:qwen3.5-0.8b@frames-boxes (first 25 of 874)</summary>

| id | truth | read | post-filter |
|---|---|---|---|
| 00792db6bb86e0e2_19 | 0:00 | 000 | ∅ |
| 00792db6bb86e0e2_23 | 0:05 | 000 | ∅ |
| 00d480fe5f01a039_1 | 10 | 101 | 101 |
| 00d480fe5f01a039_2 | 1 | BUSINESS | ∅ |
| 00dd785b54674737_1 | 0 | 1 | 1 |
| 00dd785b54674737_2 | 1 | 0 | 0 |
| 00dd785b54674737_4 | VISITORS | S | S |
| 00dd785b54674737_5 | HOME | O | O |
| 00f814e1fc9f25c9_6 | Out | Nobumi | Nobumi |
| 012929dbb05a8ddf_41 | 2 | 82 | 82 |
| 012929dbb05a8ddf_47 | 1 | 21 | 21 |
| 013a40f4c388e5b6_101 | R | ROYALS | ROYALS |
| 013a40f4c388e5b6_102 | H | YANKEES | YANKEES |
| 013a40f4c388e5b6_116 | 0 | 1 | 1 |
| 013a40f4c388e5b6_122 | 2 | 0 | 0 |
| 013a40f4c388e5b6_124 | 2 | 0 | 0 |
| 013a40f4c388e5b6_127 | 0 | 1 | 1 |
| 013a40f4c388e5b6_129 | 6 | 0 | 0 |
| 013a40f4c388e5b6_131 | 1 | 0 | 0 |
| 013a40f4c388e5b6_93 | 2 | 0 | 0 |
| 013a40f4c388e5b6_98 | 7 | 0 | 0 |
| 016894011b8686b4_40 | 6 | 1 | 1 |
| 016894011b8686b4_42 | 0 | 2 | 2 |
| 019128504b2d8249_11 | 90 | 95 | 95 |
| 019128504b2d8249_9 | 41.7 | 41-7-7 | ∅ |

</details>

## Whole frames

One engine call per frame reads all of its boxes. ms per field = the frame's time divided by its fields; parse errors = answers that weren't valid JSON (their fields were still picked out where possible).

| Dataset | Engine:variant@mode | Frames | Fields | Exact % | ms per frame p50 / p95 | ms per field p50 | Parse errors |
|---|---|---:|---:|---:|---:|---:|---:|
| textocr_scoreboards | qwen-vl:qwen3.5-0.8b@frames-boxes | 219 | 1276 | 31.5 (29.0–34.1) | 6534 / 12050 | 1012 | 4 |
