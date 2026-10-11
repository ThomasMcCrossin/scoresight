# OCR evaluation: VLMs reading whole frames: 100 of the 219 photos of textocr_scoreboards (CPU)

Created 2026-10-10T23:25:52+00:00 with harness v1 on Windows 11 AMD64, Python 3.13.2.

Exact = normalized exact match; Digits = same digits ignoring separators; CER = character error rate; Empty = no output; Post-filter = exact match after ScoreSight's whitelist and format regex for the field type. Percentages with 95% confidence intervals (Wilson; CER: bootstrap). Latency per crop in ms, p50 / p95.

## textocr_scoreboards (563 crops)

Real scoreboard and clock crops cut from Open Images photos (CC BY), with TextOCR's human transcriptions.

Subset: the crops of 100 of 219 frames (seed 0): 563 of the manifest's 1276 crops.

| Engine:variant | Exact % | Digits % | CER % | Empty % | Post-filter exact % | ms single | ms batch | Load s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen-vl:qwen3-vl-2b@frames-boxes | 39.6 (35.6–43.7) | 41.2 | 64.1 (56.5–71.8) | 0.2 | 39.4 (35.5–43.5) | – | 1817.2 / 4481.3 | 6.488 |
| florence2:florence2-base@frames-spot | 33.6 (29.8–37.6) | 35.5 | 60.9 (53.0–70.5) | 48.0 | 34.1 (30.3–38.1) | – | 554.2 / 1478.8 | 0.894 |
| qwen-vl:qwen3.5-0.8b@frames-marks | 32.1 (28.4–36.1) | 33.2 | 61.5 (55.5–67.6) | 0.0 | 31.8 (28.1–35.8) | – | 972.9 / 3175.4 | 4.614 |

### By field type (exact %, 95% CI)

| Engine:variant | clock (n=58) | number (n=421) | other (n=1) | text (n=83) |
|---|---:|---:|---:|---:|
| qwen-vl:qwen3-vl-2b@frames-boxes | 62.1 (49.2–73.4) | 37.5 (33.0–42.2) | 0.0 (0.0–79.3) | 34.9 (25.6–45.7) |
| florence2:florence2-base@frames-spot | 32.8 (22.1–45.6) | 27.3 (23.3–31.8) | 0.0 (0.0–79.3) | 66.3 (55.6–75.5) |
| qwen-vl:qwen3.5-0.8b@frames-marks | 63.8 (50.9–75.0) | 26.6 (22.6–31.0) | 0.0 (0.0–79.3) | 38.6 (28.8–49.3) |

### By display technology (exact %, 95% CI)

| Engine:variant | broadcast (n=22) | bulb (n=46) | dotmatrix (n=205) | flip (n=57) | lcd (n=23) | led7 (n=143) | printed (n=67) |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen-vl:qwen3-vl-2b@frames-boxes | 36.4 (19.7–57.0) | 15.2 (7.6–28.2) | 43.9 (37.3–50.7) | 33.3 (22.5–46.3) | 34.8 (18.8–55.1) | 46.2 (38.2–54.3) | 37.3 (26.7–49.3) |
| florence2:florence2-base@frames-spot | 13.6 (4.8–33.3) | 0.0 (0.0–7.7) | 40.5 (34.0–47.3) | 38.6 (27.1–51.6) | 34.8 (18.8–55.1) | 21.0 (15.1–28.4) | 64.2 (52.2–74.6) |
| qwen-vl:qwen3.5-0.8b@frames-marks | 27.3 (13.2–48.1) | 21.7 (12.3–35.6) | 29.3 (23.5–35.8) | 29.8 (19.5–42.7) | 47.8 (29.2–67.0) | 35.7 (28.3–43.8) | 38.8 (28.1–50.8) |

### By split (exact %, 95% CI)

| Engine:variant | dev (n=120) | test (n=443) |
|---|---:|---:|
| qwen-vl:qwen3-vl-2b@frames-boxes | 40.0 (31.7–48.9) | 39.5 (35.1–44.1) |
| florence2:florence2-base@frames-spot | 27.5 (20.3–36.1) | 35.2 (30.9–39.8) |
| qwen-vl:qwen3.5-0.8b@frames-marks | 30.0 (22.5–38.7) | 32.7 (28.5–37.2) |

<details><summary>Errors of qwen-vl:qwen3-vl-2b@frames-boxes (first 25 of 340)</summary>

| id | truth | read | post-filter |
|---|---|---|---|
| 00d480fe5f01a039_1 | 10 | 101 | 101 |
| 00d480fe5f01a039_2 | 1 | BUSINESS . . TAX | ∅ |
| 00dd785b54674737_1 | 0 | 1 | 1 |
| 00dd785b54674737_2 | 1 | 2 | 2 |
| 00dd785b54674737_4 | VISITORS | 3 | 3 |
| 00dd785b54674737_5 | HOME | 4 | 4 |
| 00f814e1fc9f25c9_6 | Out | Not Out | Not Out |
| 012929dbb05a8ddf_47 | 1 | 0 | 0 |
| 019128504b2d8249_9 | 41.7 | 4:17 | 4:17 |
| 02dc60e7b13e6dda_9 | 63 | 63°F | 63 |
| 04fb628ed85ee4fd_36 | 42 | 4 | 4 |
| 04fb628ed85ee4fd_40 | 30 | 3 | 3 |
| 04fb628ed85ee4fd_44 | 42 | 4 | 4 |
| 04fb628ed85ee4fd_56 | 30 | 3 | 3 |
| 071cbc2a74310c4c_3 | 1:25 | 12:34:125 | ∅ |
| 0c59f697a9e3b219_100 | 5 | 3 | 3 |
| 0c59f697a9e3b219_17 | 9:17 | 17 | ∅ |
| 0c59f697a9e3b219_9 | 2 | 3 | 3 |
| 0c59f697a9e3b219_98 | 3 | 2 | 2 |
| 0c59f697a9e3b219_99 | 6 | 2 | 2 |
| 0c6da2eb4a2189fe_34 | 12 | 18 | 18 |
| 0dcbcc3547b05310_14 | OUT | 1 | 1 |
| 0dcbcc3547b05310_21 | 0 | 1 | 1 |
| 0dcbcc3547b05310_25 | 010 | 1 | 1 |
| 0dcbcc3547b05310_29 | 200 | 1 | 1 |

</details>

## Whole frames

One engine call per frame reads all of its boxes. ms per field = the frame's time divided by its fields; parse errors = answers that weren't valid JSON (their fields were still picked out where possible).

| Dataset | Engine:variant@mode | Frames | Fields | Exact % | ms per frame p50 / p95 | ms per field p50 | Parse errors |
|---|---|---:|---:|---:|---:|---:|---:|
| textocr_scoreboards | qwen-vl:qwen3.5-0.8b@frames-marks | 100 | 563 | 32.1 (28.4–36.1) | 6771 / 12121 | 973 | 1 |
| textocr_scoreboards | florence2:florence2-base@frames-spot | 100 | 563 | 33.6 (29.8–37.6) | 2625 / 9594 | 554 | 0 |
| textocr_scoreboards | qwen-vl:qwen3-vl-2b@frames-boxes | 100 | 563 | 39.6 (35.6–43.7) | 12182 / 20175 | 1817 | 5 |
