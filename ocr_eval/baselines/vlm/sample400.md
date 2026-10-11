# OCR evaluation: VLMs on a stratified sample of 400 textocr_scoreboards crops and every synthetic_7seg crop (CPU); florence2-large-wl and smolvlm-500m-wl left out (run before the fix of their constrained decoding)

Created 2026-10-10T22:44:12+00:00 with harness v1 on Windows 11 AMD64, Python 3.13.2.

Exact = normalized exact match; Digits = same digits ignoring separators; CER = character error rate; Empty = no output; Post-filter = exact match after ScoreSight's whitelist and format regex for the field type. Percentages with 95% confidence intervals (Wilson; CER: bootstrap). Latency per crop in ms, p50 / p95.

## textocr_scoreboards (400 crops)

Real scoreboard and clock crops cut from Open Images photos (CC BY), with TextOCR's human transcriptions.

Subset: a stratified sample (by field_type, seed 0) of 400 of 1276 crops: 400 of the manifest's 1276 crops.

| Engine:variant | Exact % | Digits % | CER % | Empty % | Post-filter exact % | ms single | ms batch | Load s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| smolvlm:smolvlm-500m | 66.2 (61.5–70.7) | 66.8 | 48.0 (37.2–60.2) | 0.0 | 66.2 (61.5–70.7) | 513.3 / 870.0 | 390.2 / 440.3 | 1.035 |
| florence2:florence2-base-wl | 64.2 (59.4–68.8) | 65.0 | 25.0 (21.0–29.1) | 0.2 | 64.2 (59.4–68.8) | 664.2 / 687.3 | 664.2 / 687.3 | 0.91 |
| florence2:florence2-base | 56.5 (51.6–61.3) | 57.2 | 30.3 (26.1–34.8) | 0.2 | 56.5 (51.6–61.3) | 666.1 / 689.7 | 666.1 / 689.7 | 3.662 |
| florence2:florence2-base-sq | 47.8 (42.9–52.6) | 48.8 | 40.2 (35.6–45.2) | 0.0 | 48.0 (43.1–52.9) | 671.4 / 695.5 | 671.4 / 695.5 | 0.86 |

### By field type (exact %, 95% CI)

| Engine:variant | clock (n=44) | number (n=297) | other (n=1) | text (n=58) |
|---|---:|---:|---:|---:|
| smolvlm:smolvlm-500m | 29.5 (18.2–44.2) | 69.7 (64.2–74.6) | 0.0 (0.0–79.3) | 77.6 (65.3–86.4) |
| florence2:florence2-base-wl | 40.9 (27.7–55.6) | 64.6 (59.1–69.9) | 0.0 (0.0–79.3) | 81.0 (69.2–89.1) |
| florence2:florence2-base | 36.4 (23.8–51.1) | 54.9 (49.2–60.4) | 0.0 (0.0–79.3) | 81.0 (69.2–89.1) |
| florence2:florence2-base-sq | 18.2 (9.5–32.0) | 47.5 (41.9–53.1) | 0.0 (0.0–79.3) | 72.4 (59.8–82.2) |

### By display technology (exact %, 95% CI)

| Engine:variant | broadcast (n=23) | bulb (n=24) | dotmatrix (n=130) | flip (n=25) | lcd (n=26) | led7 (n=122) | printed (n=50) |
|---|---:|---:|---:|---:|---:|---:|---:|
| smolvlm:smolvlm-500m | 73.9 (53.5–87.5) | 37.5 (21.2–57.3) | 68.5 (60.0–75.8) | 88.0 (70.0–95.8) | 34.6 (19.4–53.8) | 64.8 (55.9–72.7) | 80.0 (67.0–88.8) |
| florence2:florence2-base-wl | 65.2 (44.9–81.2) | 37.5 (21.2–57.3) | 75.4 (67.3–82.0) | 64.0 (44.5–79.8) | 23.1 (11.0–42.0) | 57.4 (48.5–65.8) | 86.0 (73.8–93.0) |
| florence2:florence2-base | 65.2 (44.9–81.2) | 29.2 (14.9–49.2) | 65.4 (56.9–73.0) | 64.0 (44.5–79.8) | 19.2 (8.5–37.9) | 45.1 (36.5–53.9) | 86.0 (73.8–93.0) |
| florence2:florence2-base-sq | 34.8 (18.8–55.1) | 20.8 (9.2–40.5) | 54.6 (46.1–62.9) | 64.0 (44.5–79.8) | 15.4 (6.2–33.5) | 37.7 (29.6–46.6) | 82.0 (69.2–90.2) |

### By split (exact %, 95% CI)

| Engine:variant | dev (n=76) | test (n=324) |
|---|---:|---:|
| smolvlm:smolvlm-500m | 63.2 (51.9–73.1) | 67.0 (61.7–71.9) |
| florence2:florence2-base-wl | 63.2 (51.9–73.1) | 64.5 (59.2–69.5) |
| florence2:florence2-base | 56.6 (45.4–67.1) | 56.5 (51.0–61.8) |
| florence2:florence2-base-sq | 44.7 (34.1–55.9) | 48.5 (43.1–53.9) |

<details><summary>Errors of smolvlm:smolvlm-500m (first 25 of 135)</summary>

| id | truth | read | post-filter |
|---|---|---|---|
| 00d480fe5f01a039_1 | 10 | 12 | 12 |
| 016894011b8686b4_36 | 0 | 1 | 1 |
| 019128504b2d8249_11 | 90 | 98 | 98 |
| 032a1bbda0389235_7 | 69:49 | 6:49 | 6:49 |
| 034ab6f9af333146_34 | 89:41 | 8:41 | 8:41 |
| 040e0ec637e99ec1_19 | 69 | 1234567890 | 1234567890 |
| 040e0ec637e99ec1_35 | 66 | 1234567890 | 1234567890 |
| 065674a596dea1bc_63 | 0 | 1234567890 | 1234567890 |
| 0684ea3155f00794_12 | 3:44 | 8:44 | 8:44 |
| 0684ea3155f00794_16 | 2 | 5 | 5 |
| 06f708e3394e4ab1_8 | 7 | 1234567890 | 1234567890 |
| 071cbc2a74310c4c_3 | 1:25 | 0:00 | 0:00 |
| 07f3049deeb13d8a_84 | 04 | 64 | 64 |
| 0c59f697a9e3b219_21 | 27 | 21 | 21 |
| 0c59f697a9e3b219_99 | 6 | 100 | 100 |
| 0ee252a8309c657b_1 | 8:08 | 8:26 | 8:26 |
| 0f8a4d564b264981_96 | 25 | 1234567890 | 1234567890 |
| 0fa8fa69288deb34_61 | 0 | 8 | 8 |
| 0fa8fa69288deb34_78 | 0 | 1 | 1 |
| 0fa8fa69288deb34_79 | 0 | 8 | 8 |
| 1131058b7fae34b0_18 | 28 | 26 | 26 |
| 1131058b7fae34b0_44 | 23 | 24 | 24 |
| 1131058b7fae34b0_54 | 10 | 11 | 11 |
| 1131058b7fae34b0_61 | 0 | 12 | 12 |
| 1131058b7fae34b0_62 | 0 | 12 | 12 |

</details>

## synthetic_7seg (56 crops)

Rendered 7-segment LED and LCD digits (scores, clocks, periods): a synthetic control set, not a measure of real-world accuracy.

Subset: a stratified sample (by field_type, seed 0) of 400 of 56 crops: 56 of the manifest's 56 crops.

| Engine:variant | Exact % | Digits % | CER % | Empty % | Post-filter exact % | ms single | ms batch | Load s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| smolvlm:smolvlm-500m | 69.6 (56.7–80.1) | 69.6 | 20.1 (12.0–29.8) | 0.0 | 69.6 (56.7–80.1) | 570.4 / 658.5 | 378.8 / 390.2 | 1.0 |
| florence2:florence2-base-wl | 57.1 (44.1–69.2) | 57.1 | 18.8 (12.2–25.9) | 0.0 | 57.1 (44.1–69.2) | 662.7 / 691.0 | 662.7 / 691.0 | 1.01 |
| florence2:florence2-base | 48.2 (35.7–61.0) | 50.0 | 24.3 (16.7–33.3) | 0.0 | 50.0 (37.3–62.7) | 671.1 / 697.3 | 671.1 / 697.3 | 0.788 |
| florence2:florence2-base-sq | 21.4 (12.7–33.8) | 21.4 | 59.7 (47.5–72.5) | 0.0 | 21.4 (12.7–33.8) | 661.8 / 694.7 | 661.8 / 694.7 | 0.786 |

### By field type (exact %, 95% CI)

| Engine:variant | clock (n=20) | period (n=8) | score (n=28) |
|---|---:|---:|---:|
| smolvlm:smolvlm-500m | 65.0 (43.3–81.9) | 75.0 (40.9–92.8) | 71.4 (52.9–84.8) |
| florence2:florence2-base-wl | 65.0 (43.3–81.9) | 75.0 (40.9–92.8) | 46.4 (29.5–64.2) |
| florence2:florence2-base | 65.0 (43.3–81.9) | 50.0 (21.5–78.5) | 35.7 (20.7–54.2) |
| florence2:florence2-base-sq | 30.0 (14.5–51.9) | 25.0 (7.1–59.1) | 14.3 (5.7–31.5) |

### By display technology (exact %, 95% CI)

| Engine:variant | lcd (n=15) | led7 (n=41) |
|---|---:|---:|
| smolvlm:smolvlm-500m | 66.7 (41.7–84.8) | 70.7 (55.5–82.4) |
| florence2:florence2-base-wl | 60.0 (35.8–80.2) | 56.1 (41.0–70.1) |
| florence2:florence2-base | 46.7 (24.8–69.9) | 48.8 (34.2–63.5) |
| florence2:florence2-base-sq | 0.0 (0.0–20.4) | 29.3 (17.6–44.5) |

### By split (exact %, 95% CI)

| Engine:variant | dev (n=8) | test (n=48) |
|---|---:|---:|
| smolvlm:smolvlm-500m | 62.5 (30.6–86.3) | 70.8 (56.8–81.8) |
| florence2:florence2-base-wl | 62.5 (30.6–86.3) | 56.2 (42.3–69.3) |
| florence2:florence2-base | 25.0 (7.1–59.1) | 52.1 (38.3–65.5) |
| florence2:florence2-base-sq | 25.0 (7.1–59.1) | 20.8 (11.7–34.3) |

<details><summary>Errors of smolvlm:smolvlm-500m (first 17 of 17)</summary>

| id | truth | read | post-filter |
|---|---|---|---|
| syn7_score_0_3_28 | 0 | 100 | 100 |
| syn7_score_9_0_40 | 9 | 8 | 8 |
| syn7_score_21_0_28 | 21 | 32 | 32 |
| syn7_score_45_0_28 | 45 | 42 | 42 |
| syn7_score_99_0_28 | 99 | 2 | 2 |
| syn7_score_118_2_56 | 118 | 18 | 18 |
| syn7_score_118_3_28 | 118 | 88 | 88 |
| syn7_score_199_0_28 | 199 | 19 | 19 |
| syn7_clock_0c59_2_28 | 0:59 | 0:39 | 0:39 |
| syn7_clock_15c00_0_28 | 15:00 | 1:57 | 1:57 |
| syn7_clock_1c45_0_28 | 1:45 | 45 | ∅ |
| syn7_clock_20c00_1_28 | 20:00 | 3:00 | 3:00 |
| syn7_clock_9d5_3_40 | 9.5 | 9:51 | 9:51 |
| syn7_clock_9d5_1_56 | 9.5 | 9:51 | 9:51 |
| syn7_clock_0d4_3_28 | 0.4 | 0:00 | 0:00 |
| syn7_period_2_3_28 | 2 | 1 | 1 |
| syn7_period_2_0_28 | 2 | 1 | 1 |

</details>
