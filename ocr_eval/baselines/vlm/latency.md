# OCR evaluation: Latency per crop: 100 crops, idle machine (CPU)

Created 2026-10-10T21:34:04+00:00 with harness v1 on Windows 11 AMD64, Python 3.13.2.

Exact = normalized exact match; Digits = same digits ignoring separators; CER = character error rate; Empty = no output; Post-filter = exact match after ScoreSight's whitelist and format regex for the field type. Percentages with 95% confidence intervals (Wilson; CER: bootstrap). Latency per crop in ms, p50 / p95.

## textocr_scoreboards (100 crops)

Real scoreboard and clock crops cut from Open Images photos (CC BY), with TextOCR's human transcriptions.

Subset: a stratified sample (by field_type, seed 0) of 100 of 1276 crops: 100 of the manifest's 1276 crops.

| Engine:variant | Exact % | Digits % | CER % | Empty % | Post-filter exact % | ms single | ms batch | Load s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen-vl:qwen3-vl-2b | 92.0 (85.0–95.9) | 93.0 | 5.7 (2.0–10.1) | 0.0 | 91.0 (83.8–95.2) | 898.0 / 1324.7 | 704.4 / 769.5 | 3.875 |
| qwen-vl:qwen3.5-0.8b | 89.0 (81.4–93.8) | 91.0 | 7.1 (3.1–11.9) | 0.0 | 88.0 (80.2–93.0) | 710.1 / 980.9 | 413.3 / 427.6 | 5.111 |
| qwen-vl:qwen3.5-0.8b-wl | 89.0 (81.4–93.8) | 91.0 | 6.6 (2.8–11.2) | 0.0 | 88.0 (80.2–93.0) | 622.3 / 900.6 | 389.7 / 413.9 | 2.488 |
| smolvlm:smolvlm-256m | 63.0 (53.2–71.8) | 66.0 | 123.7 (56.0–196.6) | 0.0 | 63.0 (53.2–71.8) | 382.1 / 666.8 | 335.4 / 364.7 | 0.782 |
| florence2:florence2-base-wl | 63.0 (53.2–71.8) | 64.0 | 25.1 (17.6–33.5) | 1.0 | 63.0 (53.2–71.8) | 663.1 / 702.7 | 663.1 / 702.7 | 0.994 |
| tesseract:eng-nobin | 35.0 (26.4–44.8) | 35.0 | 55.0 (44.9–65.8) | 20.0 | 35.0 (26.4–44.8) | 2.1 / 9.5 | 2.1 / 9.5 | 0.063 |
| tesseract:scoreboard_general | 14.0 (8.5–22.1) | 15.0 | 86.3 (77.6–94.3) | 6.0 | 14.0 (8.5–22.1) | 1.8 / 3.7 | 1.8 / 3.7 | 0.071 |

### By field type (exact %, 95% CI)

| Engine:variant | clock (n=11) | number (n=74) | other (n=1) | text (n=14) |
|---|---:|---:|---:|---:|
| qwen-vl:qwen3-vl-2b | 81.8 (52.3–94.9) | 91.9 (83.4–96.2) | 100.0 (20.6–100.0) | 100.0 (78.5–100.0) |
| qwen-vl:qwen3.5-0.8b | 72.7 (43.4–90.2) | 90.5 (81.7–95.3) | 100.0 (20.6–100.0) | 92.9 (68.5–98.7) |
| qwen-vl:qwen3.5-0.8b-wl | 72.7 (43.4–90.2) | 90.5 (81.7–95.3) | 100.0 (20.6–100.0) | 92.9 (68.5–98.7) |
| smolvlm:smolvlm-256m | 18.2 (5.1–47.7) | 68.9 (57.7–78.3) | 0.0 (0.0–79.3) | 71.4 (45.4–88.3) |
| florence2:florence2-base-wl | 36.4 (15.2–64.6) | 66.2 (54.9–75.9) | 0.0 (0.0–79.3) | 71.4 (45.4–88.3) |
| tesseract:eng-nobin | 9.1 (1.6–37.7) | 37.8 (27.7–49.2) | 0.0 (0.0–79.3) | 42.9 (21.4–67.4) |
| tesseract:scoreboard_general | 0.0 (0.0–25.9) | 18.9 (11.6–29.3) | 0.0 (0.0–79.3) | 0.0 (0.0–21.5) |

### By display technology (exact %, 95% CI)

| Engine:variant | broadcast (n=7) | bulb (n=4) | dotmatrix (n=33) | flip (n=4) | lcd (n=11) | led7 (n=31) | printed (n=10) |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen-vl:qwen3-vl-2b | 100.0 (64.6–100.0) | 75.0 (30.1–95.4) | 90.9 (76.4–96.9) | 100.0 (51.0–100.0) | 72.7 (43.4–90.2) | 96.8 (83.8–99.4) | 100.0 (72.2–100.0) |
| qwen-vl:qwen3.5-0.8b | 100.0 (64.6–100.0) | 75.0 (30.1–95.4) | 87.9 (72.7–95.2) | 100.0 (51.0–100.0) | 63.6 (35.4–84.8) | 96.8 (83.8–99.4) | 90.0 (59.6–98.2) |
| qwen-vl:qwen3.5-0.8b-wl | 100.0 (64.6–100.0) | 75.0 (30.1–95.4) | 87.9 (72.7–95.2) | 100.0 (51.0–100.0) | 63.6 (35.4–84.8) | 96.8 (83.8–99.4) | 90.0 (59.6–98.2) |
| smolvlm:smolvlm-256m | 85.7 (48.7–97.4) | 50.0 (15.0–85.0) | 66.7 (49.6–80.2) | 75.0 (30.1–95.4) | 27.3 (9.8–56.6) | 64.5 (46.9–78.9) | 70.0 (39.7–89.2) |
| florence2:florence2-base-wl | 57.1 (25.1–84.2) | 25.0 (4.6–69.9) | 75.8 (59.0–87.2) | 75.0 (30.1–95.4) | 18.2 (5.1–47.7) | 61.3 (43.8–76.3) | 90.0 (59.6–98.2) |
| tesseract:eng-nobin | 14.3 (2.6–51.3) | 25.0 (4.6–69.9) | 36.4 (22.2–53.4) | 0.0 (0.0–49.0) | 18.2 (5.1–47.7) | 48.4 (32.0–65.2) | 40.0 (16.8–68.7) |
| tesseract:scoreboard_general | 0.0 (0.0–35.4) | 25.0 (4.6–69.9) | 21.2 (10.7–37.8) | 0.0 (0.0–49.0) | 0.0 (0.0–25.9) | 19.4 (9.2–36.3) | 0.0 (0.0–27.8) |

### By split (exact %, 95% CI)

| Engine:variant | dev (n=20) | test (n=80) |
|---|---:|---:|
| qwen-vl:qwen3-vl-2b | 95.0 (76.4–99.1) | 91.2 (83.0–95.7) |
| qwen-vl:qwen3.5-0.8b | 95.0 (76.4–99.1) | 87.5 (78.5–93.1) |
| qwen-vl:qwen3.5-0.8b-wl | 95.0 (76.4–99.1) | 87.5 (78.5–93.1) |
| smolvlm:smolvlm-256m | 50.0 (29.9–70.1) | 66.2 (55.4–75.6) |
| florence2:florence2-base-wl | 50.0 (29.9–70.1) | 66.2 (55.4–75.6) |
| tesseract:eng-nobin | 35.0 (18.1–56.7) | 35.0 (25.4–45.9) |
| tesseract:scoreboard_general | 15.0 (5.2–36.0) | 13.8 (7.8–23.0) |

<details><summary>Errors of qwen-vl:qwen3-vl-2b (first 8 of 8)</summary>

| id | truth | read | post-filter |
|---|---|---|---|
| 071cbc2a74310c4c_3 | 1:25 | 1:39 | 1:39 |
| 139bf8dea434ff39_2 | 31.0 | 3:10 | 3:10 |
| 30a69dec756e7cfc_32 | 3 | 12 | 12 |
| 39a0f61c7505ea32_8 | 21 | 21.3 | 213 |
| 39a16e9bf5b65da3_20 | 1 | 11 | 11 |
| 684b0dd3d4c4e041_42 | 9 | 19 | 19 |
| 8dc0aec0b3fc358b_5 | 1 | 11 | 11 |
| b1eaf2da437bda91_27 | 00 | 09 | 09 |

</details>
