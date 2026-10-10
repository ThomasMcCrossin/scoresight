# OCR evaluation: Tesseract baseline

Created 2026-10-10T19:51:26+00:00 with harness v1 on Linux 5.15.167.4-microsoft-standard-WSL2 x86_64, Python 3.13.2.

Exact = normalized exact match; Digits = same digits ignoring separators; CER = character error rate; Empty = no output; Post-filter = exact match after ScoreSight's whitelist and format regex for the field type. Percentages with 95% confidence intervals (Wilson; CER: bootstrap). Latency per crop in ms, p50 / p95.

## textocr_scoreboards (1276 crops)

Real scoreboard and clock crops cut from Open Images photos (CC BY), with TextOCR's human transcriptions.

| Engine:variant | Exact % | Digits % | CER % | Empty % | Post-filter exact % | ms single | ms batch | Load s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| tesseract:eng-nobin | 35.9 (33.3–38.6) | 36.8 | 55.6 (52.9–58.4) | 20.3 | 35.9 (33.3–38.6) | 2.2 / 6.5 | 2.2 / 6.5 | 0.123 |
| tesseract:eng | 30.1 (27.6–32.7) | 31.2 | 63.9 (61.1–66.7) | 19.6 | 30.1 (27.6–32.7) | 2.2 / 7.4 | 2.2 / 7.4 | 0.134 |
| tesseract:scoreboard_general-nobin | 18.6 (16.5–20.8) | 18.9 | 83.2 (80.7–85.5) | 10.0 | 18.6 (16.5–20.8) | 1.5 / 3.6 | 1.5 / 3.6 | 0.029 |
| tesseract:scoreboard_general | 17.6 (15.6–19.7) | 17.9 | 84.8 (82.5–87.3) | 7.3 | 17.6 (15.6–19.7) | 1.5 / 3.7 | 1.5 / 3.7 | 0.329 |
| tesseract:scoreboard_general_large | 14.9 (13.0–17.0) | 15.3 | 88.1 (85.7–90.5) | 7.4 | 14.9 (13.0–17.0) | 4.8 / 12.2 | 4.8 / 12.2 | 0.039 |
| tesseract:scoreboard_general_large-nobin | 14.8 (13.0–16.9) | 15.1 | 87.1 (84.7–89.7) | 9.3 | 14.8 (13.0–16.9) | 4.7 / 12.3 | 4.7 / 12.3 | 0.036 |
| tesseract:daktronics | 8.9 (7.4–10.5) | 8.9 | 95.5 (93.7–97.4) | 7.2 | 8.9 (7.4–10.5) | 1.3 / 2.8 | 1.3 / 2.8 | 0.028 |
| tesseract:daktronics-nobin | 7.6 (6.3–9.2) | 7.8 | 95.9 (94.1–97.8) | 9.1 | 7.6 (6.3–9.2) | 1.3 / 2.9 | 1.3 / 2.9 | 0.028 |

### By field type (exact %, 95% CI)

| Engine:variant | clock (n=139) | number (n=948) | other (n=4) | text (n=185) |
|---|---:|---:|---:|---:|
| tesseract:eng-nobin | 12.2 (7.8–18.7) | 40.6 (37.5–43.8) | 0.0 (0.0–49.0) | 30.3 (24.1–37.2) |
| tesseract:eng | 10.1 (6.1–16.2) | 34.4 (31.4–37.5) | 0.0 (0.0–49.0) | 23.8 (18.2–30.4) |
| tesseract:scoreboard_general-nobin | 6.5 (3.4–11.8) | 24.1 (21.4–26.9) | 0.0 (0.0–49.0) | 0.0 (0.0–2.0) |
| tesseract:scoreboard_general | 4.3 (2.0–9.1) | 23.0 (20.4–25.8) | 0.0 (0.0–49.0) | 0.0 (0.0–2.0) |
| tesseract:scoreboard_general_large | 4.3 (2.0–9.1) | 19.4 (17.0–22.1) | 0.0 (0.0–49.0) | 0.0 (0.0–2.0) |
| tesseract:scoreboard_general_large-nobin | 3.6 (1.6–8.1) | 19.4 (17.0–22.1) | 0.0 (0.0–49.0) | 0.0 (0.0–2.0) |
| tesseract:daktronics | 0.7 (0.1–4.0) | 11.8 (9.9–14.0) | 0.0 (0.0–49.0) | 0.0 (0.0–2.0) |
| tesseract:daktronics-nobin | 0.7 (0.1–4.0) | 10.1 (8.4–12.2) | 0.0 (0.0–49.0) | 0.0 (0.0–2.0) |

### By display technology (exact %, 95% CI)

| Engine:variant | broadcast (n=69) | bulb (n=60) | dotmatrix (n=458) | flip (n=94) | lcd (n=74) | led7 (n=353) | printed (n=168) |
|---|---:|---:|---:|---:|---:|---:|---:|
| tesseract:eng-nobin | 21.7 (13.6–32.8) | 23.3 (14.4–35.4) | 40.0 (35.6–44.5) | 51.1 (41.1–60.9) | 16.2 (9.5–26.2) | 36.8 (32.0–42.0) | 33.3 (26.7–40.8) |
| tesseract:eng | 11.6 (6.0–21.2) | 23.3 (14.4–35.4) | 31.9 (27.8–36.3) | 54.3 (44.2–64.0) | 9.5 (4.7–18.3) | 30.3 (25.8–35.3) | 30.4 (23.9–37.7) |
| tesseract:scoreboard_general-nobin | 2.9 (0.8–10.0) | 28.3 (18.5–40.8) | 16.2 (13.1–19.8) | 14.9 (9.1–23.5) | 9.5 (4.7–18.3) | 33.7 (29.0–38.8) | 2.4 (0.9–6.0) |
| tesseract:scoreboard_general | 4.3 (1.5–12.0) | 31.7 (21.3–44.2) | 16.4 (13.3–20.0) | 8.5 (4.4–15.9) | 9.5 (4.7–18.3) | 29.7 (25.2–34.7) | 4.2 (2.0–8.3) |
| tesseract:scoreboard_general_large | 5.8 (2.3–14.0) | 13.3 (6.9–24.2) | 15.5 (12.5–19.1) | 4.3 (1.7–10.4) | 8.1 (3.8–16.6) | 24.9 (20.7–29.7) | 5.4 (2.8–9.9) |
| tesseract:scoreboard_general_large-nobin | 4.3 (1.5–12.0) | 15.0 (8.1–26.1) | 15.5 (12.5–19.1) | 7.4 (3.6–14.6) | 8.1 (3.8–16.6) | 24.6 (20.4–29.4) | 3.6 (1.7–7.6) |
| tesseract:daktronics | 5.8 (2.3–14.0) | 13.3 (6.9–24.2) | 8.3 (6.1–11.2) | 4.3 (1.7–10.4) | 0.0 (0.0–4.9) | 15.9 (12.4–20.0) | 1.8 (0.6–5.1) |
| tesseract:daktronics-nobin | 1.4 (0.3–7.8) | 13.3 (6.9–24.2) | 5.0 (3.4–7.4) | 6.4 (3.0–13.2) | 5.4 (2.1–13.1) | 14.7 (11.4–18.8) | 1.8 (0.6–5.1) |

### By split (exact %, 95% CI)

| Engine:variant | dev (n=268) | test (n=1008) |
|---|---:|---:|
| tesseract:eng-nobin | 32.1 (26.8–37.9) | 36.9 (34.0–39.9) |
| tesseract:eng | 28.4 (23.3–34.0) | 30.6 (27.8–33.5) |
| tesseract:scoreboard_general-nobin | 17.5 (13.5–22.5) | 18.8 (16.6–21.4) |
| tesseract:scoreboard_general | 17.2 (13.1–22.1) | 17.7 (15.4–20.1) |
| tesseract:scoreboard_general_large | 16.0 (12.1–20.9) | 14.6 (12.5–16.9) |
| tesseract:scoreboard_general_large-nobin | 16.0 (12.1–20.9) | 14.5 (12.4–16.8) |
| tesseract:daktronics | 9.3 (6.4–13.4) | 8.7 (7.1–10.6) |
| tesseract:daktronics-nobin | 6.0 (3.7–9.5) | 8.0 (6.5–9.9) |

<details><summary>Errors of tesseract:eng-nobin (first 25 of 818)</summary>

| id | truth | read | post-filter |
|---|---|---|---|
| 00792db6bb86e0e2_19 | 0:00 | ... | ∅ |
| 00792db6bb86e0e2_22 | 5 | 1 | 1 |
| 00792db6bb86e0e2_23 | 0:05 | ∅ | ∅ |
| 00918f59a42f88f5_2 | 5:21 | 5221 | ∅ |
| 00918f59a42f88f5_4 | 19 | 9 | 9 |
| 00d480fe5f01a039_1 | 10 | ∅ | ∅ |
| 00dd785b54674737_1 | 0 | 5 | 5 |
| 00dd785b54674737_4 | VISITORS | VISITORS \| | VISITORS \| |
| 012929dbb05a8ddf_41 | 2 | ∅ | ∅ |
| 013a40f4c388e5b6_101 | R | _. | _. |
| 013a40f4c388e5b6_102 | H | _. | _. |
| 013a40f4c388e5b6_116 | 0 | ∅ | ∅ |
| 013a40f4c388e5b6_124 | 2 | ∅ | ∅ |
| 013a40f4c388e5b6_129 | 6 | ∅ | ∅ |
| 013a40f4c388e5b6_93 | 2 | ∅ | ∅ |
| 013a40f4c388e5b6_98 | 7 | ∅ | ∅ |
| 016894011b8686b4_33 | 12:00 | 1 | ∅ |
| 016894011b8686b4_36 | 0 | 1 | 1 |
| 016894011b8686b4_40 | 6 | 1 | 1 |
| 016894011b8686b4_42 | 0 | 1 | 1 |
| 019128504b2d8249_11 | 90 | 3 | 3 |
| 019128504b2d8249_9 | 41.7 | ∅ | ∅ |
| 024033e1c44a12ac_12 | 1 | 5 | 5 |
| 025532b54c27c825_4 | 0 | 5 | 5 |
| 025532b54c27c825_5 | 0 | 1 | 1 |

</details>

## synthetic_7seg (56 crops)

Rendered 7-segment LED and LCD digits (scores, clocks, periods): a synthetic control set, not a measure of real-world accuracy.

| Engine:variant | Exact % | Digits % | CER % | Empty % | Post-filter exact % | ms single | ms batch | Load s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| tesseract:scoreboard_general | 58.9 (45.9–70.8) | 60.7 | 33.3 (21.5–45.0) | 0.0 | 58.9 (45.9–70.8) | 1.7 / 2.8 | 1.7 / 2.8 | 0.022 |
| tesseract:eng-nobin | 42.9 (30.8–55.9) | 44.6 | 34.0 (25.0–44.2) | 0.0 | 42.9 (30.8–55.9) | 3.2 / 10.3 | 3.2 / 10.3 | 0.103 |
| tesseract:scoreboard_general_large | 41.1 (29.2–54.1) | 46.4 | 41.0 (31.3–50.0) | 0.0 | 41.1 (29.2–54.1) | 5.3 / 9.6 | 5.3 / 9.6 | 0.032 |
| tesseract:eng | 39.3 (27.6–52.4) | 44.6 | 42.4 (31.9–53.8) | 0.0 | 39.3 (27.6–52.4) | 3.0 / 9.0 | 3.0 / 9.0 | 0.136 |
| tesseract:scoreboard_general_large-nobin | 37.5 (26.0–50.6) | 39.3 | 50.7 (39.6–61.3) | 0.0 | 37.5 (26.0–50.6) | 5.4 / 10.8 | 5.4 / 10.8 | 0.034 |
| tesseract:scoreboard_general-nobin | 35.7 (24.5–48.8) | 44.6 | 44.4 (33.9–55.8) | 0.0 | 35.7 (24.5–48.8) | 1.8 / 2.7 | 1.8 / 2.7 | 0.026 |
| tesseract:daktronics-nobin | 8.9 (3.9–19.3) | 8.9 | 72.2 (62.7–82.7) | 0.0 | 8.9 (3.9–19.3) | 1.7 / 2.8 | 1.7 / 2.8 | 0.022 |
| tesseract:daktronics | 3.6 (1.0–12.1) | 5.4 | 77.1 (68.2–86.5) | 0.0 | 3.6 (1.0–12.1) | 1.7 / 2.4 | 1.7 / 2.4 | 0.022 |

### By field type (exact %, 95% CI)

| Engine:variant | clock (n=20) | period (n=8) | score (n=28) |
|---|---:|---:|---:|
| tesseract:scoreboard_general | 35.0 (18.1–56.7) | 62.5 (30.6–86.3) | 75.0 (56.6–87.3) |
| tesseract:eng-nobin | 30.0 (14.5–51.9) | 62.5 (30.6–86.3) | 46.4 (29.5–64.2) |
| tesseract:scoreboard_general_large | 10.0 (2.8–30.1) | 62.5 (30.6–86.3) | 57.1 (39.1–73.5) |
| tesseract:eng | 25.0 (11.2–46.9) | 75.0 (40.9–92.8) | 39.3 (23.6–57.6) |
| tesseract:scoreboard_general_large-nobin | 15.0 (5.2–36.0) | 75.0 (40.9–92.8) | 42.9 (26.5–60.9) |
| tesseract:scoreboard_general-nobin | 10.0 (2.8–30.1) | 50.0 (21.5–78.5) | 50.0 (32.6–67.4) |
| tesseract:daktronics-nobin | 5.0 (0.9–23.6) | 12.5 (2.2–47.1) | 10.7 (3.7–27.2) |
| tesseract:daktronics | 0.0 (0.0–16.1) | 0.0 (0.0–32.4) | 7.1 (2.0–22.7) |

### By display technology (exact %, 95% CI)

| Engine:variant | lcd (n=15) | led7 (n=41) |
|---|---:|---:|
| tesseract:scoreboard_general | 33.3 (15.2–58.3) | 68.3 (53.0–80.4) |
| tesseract:eng-nobin | 33.3 (15.2–58.3) | 46.3 (32.1–61.3) |
| tesseract:scoreboard_general_large | 26.7 (10.9–51.9) | 46.3 (32.1–61.3) |
| tesseract:eng | 20.0 (7.0–45.2) | 46.3 (32.1–61.3) |
| tesseract:scoreboard_general_large-nobin | 20.0 (7.0–45.2) | 43.9 (29.9–59.0) |
| tesseract:scoreboard_general-nobin | 13.3 (3.7–37.9) | 43.9 (29.9–59.0) |
| tesseract:daktronics-nobin | 6.7 (1.2–29.8) | 9.8 (3.9–22.6) |
| tesseract:daktronics | 0.0 (0.0–20.4) | 4.9 (1.4–16.1) |

### By split (exact %, 95% CI)

| Engine:variant | dev (n=8) | test (n=48) |
|---|---:|---:|
| tesseract:scoreboard_general | 75.0 (40.9–92.8) | 56.2 (42.3–69.3) |
| tesseract:eng-nobin | 25.0 (7.1–59.1) | 45.8 (32.6–59.7) |
| tesseract:scoreboard_general_large | 37.5 (13.7–69.4) | 41.7 (28.8–55.7) |
| tesseract:eng | 25.0 (7.1–59.1) | 41.7 (28.8–55.7) |
| tesseract:scoreboard_general_large-nobin | 50.0 (21.5–78.5) | 35.4 (23.4–49.6) |
| tesseract:scoreboard_general-nobin | 37.5 (13.7–69.4) | 35.4 (23.4–49.6) |
| tesseract:daktronics-nobin | 12.5 (2.2–47.1) | 8.3 (3.3–19.6) |
| tesseract:daktronics | 12.5 (2.2–47.1) | 2.1 (0.4–10.9) |

<details><summary>Errors of tesseract:scoreboard_general (first 23 of 23)</summary>

| id | truth | read | post-filter |
|---|---|---|---|
| syn7_score_9_1_40 | 9 | 94 | 94 |
| syn7_score_9_0_40 | 9 | 94 | 94 |
| syn7_score_99_0_28 | 99 | 227 | ∅ |
| syn7_score_105_3_40 | 105 | 12 | 12 |
| syn7_score_118_3_28 | 118 | 119 | 119 |
| syn7_score_147_3_40 | 147 | 1422 | ∅ |
| syn7_score_199_3_40 | 199 | 1 | 1 |
| syn7_clock_12c34_2_28 | 12:34 | 1203.4 | ∅ |
| syn7_clock_12c34_1_28 | 12:34 | 1203.4 | ∅ |
| syn7_clock_0c59_2_28 | 0:59 | 0271 | ∅ |
| syn7_clock_0c59_0_56 | 0:59 | 0:55.. | ∅ |
| syn7_clock_9c07_2_40 | 9:07 | 9:01 | 9:01 |
| syn7_clock_15c00_0_28 | 15:00 | 155.00 | ∅ |
| syn7_clock_15c00_1_40 | 15:00 | 15.00 | ∅ |
| syn7_clock_1c45_0_28 | 1:45 | 15..56 | ∅ |
| syn7_clock_20c00_3_40 | 20:00 | 1 | ∅ |
| syn7_clock_20c00_1_28 | 20:00 | 2658.8 | ∅ |
| syn7_clock_9d5_3_40 | 9.5 | 022 | ∅ |
| syn7_clock_9d5_1_56 | 9.5 | 9.56 | ∅ |
| syn7_clock_0d4_3_28 | 0.4 | 30.4 | 30.4 |
| syn7_period_1_3_40 | 1 | 0 | ∅ |
| syn7_period_3_3_28 | 3 | 1 | 1 |
| syn7_period_4_3_40 | 4 | 0 | ∅ |

</details>
