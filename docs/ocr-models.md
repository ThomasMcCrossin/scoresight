---
title: OCR Models
parent: Guides
nav_order: 5
description: "The OCR models bundled with ScoreSight, how Tesseract is configured, and how to load your own .traineddata model."
---

# OCR Models

ScoreSight uses the [Tesseract](https://github.com/tesseract-ocr/tesseract) OCR engine with models trained for scoreboards. Choose the model in the **OCR Model** drop-down in the main window. The model applies to **all** boxes and is remembered between runs.

## Bundled models

| Menu name | File | Use for |
|---|---|---|
| **Daktronics** | `daktronics.traineddata` | Daktronics-style LED and dot-matrix scoreboard fonts |
| **General Scoreboard** (default) | `scoreboard_general.traineddata` | Most LED, LCD and 7-segment scoreboard digits. Start here |
| **General Fonts (English)** | `eng.traineddata` | Regular fonts: TV score bugs, games, apps, web pages, printed text, team names |
| **General Scoreboard Large** | `scoreboard_general_large.traineddata` | Large, bold segment digits. Slower than the others |
| **Load External OCR Model** | your `.traineddata` | A model you trained yourself (see below) |

The models are installed with ScoreSight, in the `tesseract/tessdata` folder of the application.

## How ScoreSight runs Tesseract

Knowing this helps when you train your own model:

- Each box is read as a **single word** (Tesseract page segmentation mode 8), so one box should contain one value.
- The **Type** of the box restricts the characters Tesseract may output:
  - *Number*: `0123456789`
  - *Time*: `0123456789:.`
  - *Text*: letters, digits, space and common punctuation
- Before recognition, the box image is pre-processed according to its [per-box settings](box-settings.md) and, with **Rescale Input** on (the default), scaled to 35 pixels high.
- After recognition, the [format, confidence and smoothing filters](box-settings.md#processing-order) are applied.

## Loading your own model

1. Choose **Load External OCR Model** in the **OCR Model** drop-down.
2. Pick a `.traineddata` file.

ScoreSight uses the file's folder as the Tesseract data folder and the file name (without `.traineddata`) as the language. For example, `D:\models\myboard.traineddata` loads language `myboard` from `D:\models`. The path is remembered, so keep the file where it is.

## Training a model for your scoreboard

1. [Collect and annotate training data](data_annotation.md) from your own scoreboard with the built-in Training Dojo.
2. Train a Tesseract LSTM model with the official [tesstrain](https://github.com/tesseract-ocr/tesstrain) tools. Fine-tuning one of the bundled scoreboard models usually needs far less data than training from scratch.
3. Load the resulting `.traineddata` with **Load External OCR Model**.

Training is an advanced topic. If you want to share data or a model that could help other users, [open an issue](https://github.com/royshil/scoresight/issues/new/choose) to discuss it.
