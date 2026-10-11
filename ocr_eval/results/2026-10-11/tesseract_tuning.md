Tesseract settings on the dev split (410 crops: TextOCR 268, Commons 142), 144 combinations, best first (python ocr_eval/results/2026-10-11/tune_tesseract.py, tesserocr 2.10.0, Tesseract 5.5.2, win32). An untuned preset is a variant of the report as it is.

| Model | Binarization | Dilate | Dark on light | Height px | Dev exact % | TextOCR dev % | Commons dev % |
|---|---|---:|---|---|---:|---:|---:|
| `eng` **(tuned)** | none | 0 | yes | 24 | 54.4 | 47.4 | 67.6 |
| `eng` | none | 0 | yes | 20 | 53.7 | 46.6 | 66.9 |
| `eng` | none | 0 | yes | 28 | 53.7 | 47.4 | 65.5 |
| `eng` | none | 0 | no | 24 | 52.4 | 46.3 | 64.1 |
| `eng` | none | 0 | no | 28 | 52.0 | 47.0 | 61.3 |
| `eng` | none | 0 | yes | 32 | 51.7 | 44.8 | 64.8 |
| `eng` | none | 0 | yes | 35 (app) | 51.5 | 42.5 | 68.3 |
| `eng` | none | 0 | no | 32 | 51.2 | 45.9 | 61.3 |
| `eng` | none | 0 | no | 35 (app) | 50.7 | 42.5 | 66.2 |
| `eng` | none | 0 | no | 20 | 50.7 | 44.4 | 62.7 |
| `eng` | none | 0 | yes | 64 | 50.5 | 43.3 | 64.1 |
| `eng` | none | 1 | yes | 64 | 49.8 | 44.4 | 59.9 |
| `eng` | none | 1 | yes | 80 | 49.8 | 45.1 | 58.5 |
| `eng` | otsu | 0 | yes | 35 (app) | 49.3 | 40.7 | 65.5 |
| `eng` | none | 0 | yes | 16 | 48.8 | 39.6 | 66.2 |
| `eng` | otsu | 1 | yes | 80 | 48.8 | 46.3 | 53.5 |
| `eng` | none | 0 | yes | 80 | 48.5 | 43.3 | 58.5 |
| `eng` | none | 0 | no | 16 | 48.5 | 38.8 | 66.9 |
| `eng` | otsu | 0 | yes | 28 | 48.5 | 43.7 | 57.7 |
| `eng` | otsu | 0 | yes | 32 | 48.5 | 43.7 | 57.7 |
| `eng` | none | 0 | yes | 48 | 47.8 | 41.8 | 59.2 |
| `eng` | none | 1 | no | 64 | 47.8 | 41.8 | 59.2 |
| `eng` | otsu | 0 | yes | 24 | 47.3 | 40.7 | 59.9 |
| `eng` | otsu | 0 | yes | 64 | 47.3 | 39.9 | 61.3 |
| `eng` | otsu | 0 | no | 28 | 47.3 | 43.3 | 54.9 |
| `eng` | otsu | 0 | no | 32 | 47.3 | 42.9 | 55.6 |
| `eng` | none | 0 | no | 64 | 47.1 | 40.7 | 59.2 |
| `eng` | none | 1 | yes | 48 | 47.1 | 41.4 | 57.7 |
| `eng` | otsu | 0 | no | 35 (app) | 47.1 | 40.7 | 59.2 |
| `eng` | otsu | 0 | no | 64 | 46.6 | 39.6 | 59.9 |
| `eng` | none | 1 | no | 80 | 46.3 | 40.3 | 57.7 |
| `eng` | none | 0 | no | 48 | 45.9 | 41.0 | 54.9 |
| `eng` | otsu | 0 | yes | 48 | 45.9 | 39.9 | 57.0 |
| `eng` | none | 0 | no | 80 | 45.6 | 41.4 | 53.5 |
| `eng` | otsu | 1 | yes | 64 | 45.6 | 42.9 | 50.7 |
| `eng` | otsu | 1 | yes | 48 | 45.4 | 43.3 | 49.3 |
| `eng` | otsu | 0 | yes | 80 | 45.1 | 39.9 | 54.9 |
| `eng` | otsu | 0 | no | 24 | 45.1 | 39.2 | 56.3 |
| `eng` | otsu | 0 | no | 48 | 44.9 | 39.2 | 55.6 |
| `eng` | otsu | 0 | yes | 20 | 44.6 | 39.2 | 54.9 |
| `eng` | otsu | 1 | no | 80 | 44.4 | 40.3 | 52.1 |
| `eng` | otsu | 0 | no | 80 | 44.1 | 38.8 | 54.2 |
| `eng` | otsu | 0 | no | 20 | 43.4 | 38.1 | 53.5 |
| `eng` | none | 1 | no | 48 | 43.2 | 35.8 | 57.0 |
| `eng` | none | 1 | yes | 35 (app) | 42.9 | 36.9 | 54.2 |
| `eng` | none | 1 | yes | 32 | 42.2 | 36.2 | 53.5 |
| `eng` (an untuned preset) | none | 1 | no | 35 (app) | 41.7 | 32.1 | 59.9 |
| `eng` | otsu | 1 | no | 64 | 40.5 | 33.6 | 53.5 |
| `eng` | none | 1 | no | 28 | 40.0 | 32.5 | 54.2 |
| `eng` | otsu | 1 | no | 48 | 40.0 | 33.6 | 52.1 |
| `eng` | none | 1 | no | 32 | 38.5 | 31.3 | 52.1 |
| `eng` | none | 1 | yes | 28 | 38.0 | 33.2 | 47.2 |
| `eng` | otsu | 1 | yes | 35 (app) | 38.0 | 33.6 | 46.5 |
| `eng` (an untuned preset) | otsu | 1 | no | 35 (app) | 37.8 | 28.4 | 55.6 |
| `eng` | none | 1 | yes | 24 | 37.3 | 34.0 | 43.7 |
| `eng` | otsu | 0 | yes | 16 | 35.9 | 29.9 | 47.2 |
| `eng` | otsu | 0 | no | 16 | 35.4 | 29.5 | 46.5 |
| `eng` | none | 1 | no | 24 | 35.1 | 29.5 | 45.8 |
| `scoreboard_general` | otsu | 0 | no | 35 (app) | 33.4 | 25.4 | 48.6 |
| `scoreboard_general` | otsu | 0 | no | 64 | 32.9 | 25.4 | 47.2 |
| `eng` | otsu | 1 | yes | 32 | 31.7 | 29.9 | 35.2 |
| `scoreboard_general` | otsu | 0 | no | 32 | 31.7 | 24.3 | 45.8 |
| `scoreboard_general` | otsu | 0 | no | 28 | 31.0 | 23.5 | 45.1 |
| `scoreboard_general` | otsu | 0 | no | 48 | 30.7 | 22.8 | 45.8 |
| `scoreboard_general` | otsu | 0 | no | 24 | 30.2 | 25.0 | 40.1 |
| `scoreboard_general` | otsu | 0 | no | 80 | 30.0 | 22.4 | 44.4 |
| `scoreboard_general` | none | 0 | no | 35 (app) | 29.8 | 19.4 | 49.3 |
| `scoreboard_general` | none | 0 | no | 20 | 29.8 | 22.4 | 43.7 |
| `scoreboard_general` | none | 0 | no | 24 | 29.8 | 19.8 | 48.6 |
| `scoreboard_general` | none | 0 | no | 32 | 29.5 | 19.8 | 47.9 |
| `scoreboard_general` | none | 1 | no | 64 | 29.0 | 24.3 | 38.0 |
| `scoreboard_general` | otsu | 0 | no | 20 | 29.0 | 21.3 | 43.7 |
| `scoreboard_general` | none | 0 | no | 64 | 28.8 | 20.1 | 45.1 |
| `eng` | otsu | 1 | no | 32 | 28.5 | 22.4 | 40.1 |
| `scoreboard_general` | none | 0 | no | 48 | 28.5 | 19.4 | 45.8 |
| `scoreboard_general` | none | 0 | no | 80 | 28.3 | 20.5 | 43.0 |
| `scoreboard_general` | none | 0 | no | 28 | 28.0 | 20.1 | 43.0 |
| `eng` | otsu | 1 | no | 28 | 27.6 | 22.0 | 38.0 |
| `scoreboard_general` | otsu | 1 | no | 80 | 27.6 | 20.1 | 41.5 |
| `scoreboard_general` | none | 1 | no | 80 | 27.3 | 20.1 | 40.8 |
| `scoreboard_general` | otsu | 0 | no | 16 | 27.3 | 22.0 | 37.3 |
| `scoreboard_general` | otsu | 1 | no | 64 | 27.3 | 22.4 | 36.6 |
| `scoreboard_general` | none | 1 | no | 48 | 27.1 | 19.8 | 40.8 |
| `eng` | none | 1 | no | 20 | 26.8 | 21.6 | 36.6 |
| `scoreboard_general` | none | 0 | no | 16 | 25.9 | 17.9 | 40.8 |
| `scoreboard_general` (an untuned preset) | none | 1 | no | 35 (app) | 25.1 | 17.5 | 39.4 |
| `scoreboard_general` | otsu | 1 | no | 48 | 25.1 | 17.5 | 39.4 |
| `eng` | otsu | 1 | yes | 28 | 24.9 | 25.0 | 24.6 |
| `scoreboard_general` (an untuned preset) | otsu | 1 | no | 35 (app) | 24.9 | 17.2 | 39.4 |
| `eng` | none | 1 | yes | 20 | 24.1 | 23.1 | 26.1 |
| `eng` | otsu | 1 | no | 24 | 22.0 | 16.0 | 33.1 |
| `scoreboard_general` | otsu | 1 | no | 32 | 22.0 | 15.3 | 34.5 |
| `scoreboard_general` | none | 1 | no | 32 | 21.7 | 14.9 | 34.5 |
| `scoreboard_general` | none | 1 | no | 28 | 21.2 | 15.3 | 32.4 |
| `scoreboard_general` | otsu | 1 | yes | 48 | 20.5 | 15.7 | 29.6 |
| `scoreboard_general` | none | 1 | no | 24 | 19.8 | 14.9 | 28.9 |
| `scoreboard_general` | otsu | 0 | yes | 64 | 19.8 | 14.6 | 29.6 |
| `scoreboard_general` | otsu | 0 | yes | 35 (app) | 19.3 | 13.4 | 30.3 |
| `scoreboard_general` | none | 0 | yes | 35 (app) | 19.0 | 12.7 | 31.0 |
| `scoreboard_general` | otsu | 0 | yes | 32 | 19.0 | 14.6 | 27.5 |
| `scoreboard_general` | none | 0 | yes | 28 | 18.3 | 13.1 | 28.2 |
| `scoreboard_general` | none | 0 | yes | 80 | 18.3 | 13.4 | 27.5 |
| `scoreboard_general` | none | 1 | yes | 48 | 18.3 | 14.9 | 24.6 |
| `scoreboard_general` | otsu | 0 | yes | 24 | 18.3 | 14.2 | 26.1 |
| `scoreboard_general` | none | 0 | yes | 48 | 18.0 | 14.2 | 25.4 |
| `scoreboard_general` | otsu | 0 | yes | 28 | 18.0 | 14.2 | 25.4 |
| `scoreboard_general` | none | 1 | no | 20 | 17.8 | 15.7 | 21.8 |
| `scoreboard_general` | otsu | 0 | yes | 48 | 17.8 | 13.1 | 26.8 |
| `eng` | none | 1 | no | 16 | 17.6 | 12.7 | 26.8 |
| `eng` | otsu | 1 | no | 20 | 17.6 | 12.7 | 26.8 |
| `scoreboard_general` | none | 0 | yes | 24 | 17.6 | 11.2 | 29.6 |
| `scoreboard_general` | none | 1 | yes | 64 | 17.6 | 13.1 | 26.1 |
| `scoreboard_general` | none | 1 | yes | 80 | 17.6 | 11.6 | 28.9 |
| `scoreboard_general` | none | 1 | yes | 35 (app) | 17.3 | 11.2 | 28.9 |
| `scoreboard_general` | otsu | 1 | yes | 64 | 17.3 | 15.3 | 21.1 |
| `scoreboard_general` | none | 0 | yes | 64 | 17.1 | 11.6 | 27.5 |
| `scoreboard_general` | otsu | 0 | yes | 20 | 16.8 | 11.2 | 27.5 |
| `scoreboard_general` | otsu | 0 | yes | 80 | 16.8 | 11.6 | 26.8 |
| `scoreboard_general` | otsu | 1 | no | 28 | 16.8 | 11.6 | 26.8 |
| `scoreboard_general` | none | 0 | yes | 32 | 16.6 | 11.2 | 26.8 |
| `scoreboard_general` | otsu | 1 | yes | 80 | 16.6 | 14.6 | 20.4 |
| `scoreboard_general` | otsu | 1 | no | 24 | 16.1 | 8.6 | 30.3 |
| `scoreboard_general` | none | 0 | yes | 16 | 15.6 | 11.2 | 23.9 |
| `scoreboard_general` | none | 0 | yes | 20 | 15.6 | 10.1 | 26.1 |
| `scoreboard_general` | none | 1 | yes | 28 | 15.6 | 11.9 | 22.5 |
| `scoreboard_general` | otsu | 1 | yes | 35 (app) | 15.6 | 12.3 | 21.8 |
| `scoreboard_general` | otsu | 0 | yes | 16 | 14.9 | 10.8 | 22.5 |
| `eng` | otsu | 1 | yes | 24 | 13.9 | 15.7 | 10.6 |
| `scoreboard_general` | none | 1 | yes | 32 | 13.2 | 9.3 | 20.4 |
| `scoreboard_general` | none | 1 | yes | 24 | 12.9 | 10.8 | 16.9 |
| `scoreboard_general` | otsu | 1 | no | 20 | 12.9 | 9.0 | 20.4 |
| `eng` | none | 1 | yes | 16 | 12.7 | 12.3 | 13.4 |
| `scoreboard_general` | otsu | 1 | yes | 32 | 12.7 | 11.6 | 14.8 |
| `scoreboard_general` | none | 1 | yes | 20 | 11.5 | 10.1 | 14.1 |
| `scoreboard_general` | otsu | 1 | yes | 28 | 11.2 | 9.3 | 14.8 |
| `eng` | otsu | 1 | no | 16 | 10.7 | 8.2 | 15.5 |
| `scoreboard_general` | otsu | 1 | yes | 24 | 10.7 | 10.1 | 12.0 |
| `scoreboard_general` | none | 1 | no | 16 | 9.3 | 8.2 | 11.3 |
| `scoreboard_general` | otsu | 1 | yes | 20 | 7.8 | 9.0 | 5.6 |
| `scoreboard_general` | otsu | 1 | no | 16 | 7.6 | 5.2 | 12.0 |
| `scoreboard_general` | none | 1 | yes | 16 | 7.1 | 9.0 | 3.5 |
| `eng` | otsu | 1 | yes | 20 | 6.1 | 8.2 | 2.1 |
| `scoreboard_general` | otsu | 1 | yes | 16 | 4.1 | 4.9 | 2.8 |
| `eng` | otsu | 1 | yes | 16 | 2.9 | 4.5 | 0.0 |
