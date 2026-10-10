---
title: Per-Box Settings
parent: Reference
nav_order: 1
description: "Reference for every per-box recognition setting in ScoreSight: UI label, JSON key, range, default, effect and when to use it."
---

# Per-Box Settings Reference
{: .no_toc }

Each box has its own settings, shown in the settings panel when the box is selected. **Defaults** restores the defaults for the selected box. Settings are saved with your layout and included in **File > Export Configuration**. In exported files and `scoresight.json`, they appear under each box's `settings` object, using the JSON keys listed here.

For a task-oriented guide, see [Recognition Tuning](recognition-tuning.md).

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Summary

| UI label | JSON key | Values | Default |
|---|---|---|---|
| [Type](#type) | `type` | `0` Number, `1` Time, `2` Text | Time box: Time. Others: Number |
| [Format](#format) | `format_regex` | regular expression | depends on the field (see below) |
| [Average Output](#average-output) | `smoothing` | on/off | off |
| [Skip Empty Values](#skip-empty-values) | `skip_empty` | on/off | on |
| [Conf. Th](#conf-th-confidence-threshold) | `conf_thresh` | 0.00–0.99 (slider 0–99 = Tesseract confidence in %) | 0 (off) |
| [Binarize](#binarize) | `binarization_method` | `0` Global, `1` No Binarization, `2` Local, `3` Adaptive | `0` Global |
| [Cleanup](#cleanup) | `cleanup_thresh` | 0.00–0.99 (slider 0–99) | 0 (off) |
| [Dilate](#dilate) | `dilate` | 0–5 | 1 |
| [V.Scale](#vscale) | `vscale` | 1–10 | 10 (no scaling) |
| [Skew](#skew) | `skew` | −10 to 10 | 0 |
| [Auto Crop](#auto-crop) | `autocrop` | on/off | off |
| [Rescale Input](#rescale-input) | `rescale_patch` | on/off | on |
| [Normalize W-H Ratio](#normalize-w-h-ratio) | `normalize_wh_ratio` | on/off | off |
| [Invert Input](#invert-input) | `invert_patch` | on/off | off |
| [Skip Similar Image](#skip-similar-image) | `skip_similar_image` | on/off | off |
| [Remove leading 0s](#remove-leading-0s) | `remove_leading_zeros` | on/off | off |
| [Ordinal (1st, 2nd, ..)](#ordinal) | `ordinal_indicator` | on/off | Period: on. Others: off |
| [Dot Counter](#dot-counter) | `dot_detector` | on/off | off |
| [Template Field](#template-field) | `templatefield`, `templatefield_text` | on/off, text | off, empty |
| [Composite (Per-Character)](#composite-per-character) | `composite_box` | on/off | off |
| (not shown) | `is_custom` | true/false | true for fields you added with **+** |
| (not shown) | `obs_source_name` | text | see [OBS source name](#obs-source-name) |

## Processing order

For each box, on every detection cycle, ScoreSight:

1. takes the part of the box that is inside the processed picture (a box that reaches past the edge is read from its visible part; its saved position isn't changed),
2. **binarizes** it (*Binarize*),
3. removes small specks (*Cleanup*),
4. squashes it vertically (*V.Scale*) and shears it (*Skew*),
5. thickens strokes (*Dilate*),
6. inverts it (*Invert Input*),
7. reports the box as `Empty` without running OCR if the image is blank (every pixel the same, for example a box over plain background); a *Dot Counter* box reports `0` instead,
8. skips OCR if the image hasn't changed (*Skip Similar Image*),
9. crops to the text (*Auto Crop*),
10. scales it (*Rescale Input*, *Normalize W-H Ratio*),
11. counts dots (*Dot Counter*) **or** runs OCR with the character set of the *Type*,
12. checks the raw text against the *Format* and the *Conf. Th* threshold,
13. applies *Average Output* (to accepted readings only), *Remove leading 0s* and *Ordinal*,
14. marks the reading `Empty` if no text is left, or `SameNoChange` if it equals the box's last good reading and **Update on change** is on.

Each box is processed on its own copy of the picture, so overlapping boxes never affect each other. **Binary View** shows the result of steps 1–5 for every box: exactly the image the OCR receives, before *Invert Input*.

## Recognition

### Type

`type`: which characters the OCR may output.

| Value | UI | Allowed characters |
|---|---|---|
| `0` | Number 0-9 | `0123456789` |
| `1` | Time 0-9 , . : | `0123456789` plus `:` and `.` |
| `2` | Text | letters, digits, space and common punctuation |

**Use**: always set the narrowest type. *Number* for scores, fouls, periods and shot clocks. *Time* for clocks. *Text* only for names or other words.

{: .new }
In ScoreSight 0.1.x the Type of a box was lost after a restart or export ([#22](https://github.com/royshil/scoresight/issues/22)). It is saved since 0.2.0.

### Format

`format_regex`: a regular expression the **raw** OCR text must match completely, before averaging, leading-zero removal and ordinal suffixes. If it doesn't match, the reading is marked `FailedFilter` (yellow) and outputs that send only good values ignore it. An invalid expression is ignored.

Choose a preset from **Select Preset** to fill in the expression, or type your own:

| Preset | Expression | Default for |
|---|---|---|
| Time mm:ss.d | `mm:ss` or `ss.d` (expression below) | Time |
| Time mm:ss | `^[0-5]?\d:[0-5]\d$` | |
| Time ss.d | `^[0-5]?\d\.\d$` | |
| Time 0-59 | `^[0-5]\d$` | |
| Shotclock 0-39 | `^[0-3]\d$` | Shot Clock |
| Score 1dd | `^1?\d{1,2}$` | Home Score, Away Score |
| Score ddd | `^\d{1,3}$` | |
| Period 1-4 | `^[1-4]{1}$` | Period |
| Period d | `^\d{1}$` | |
| Alphanumeric | `^[A-Za-z0-9]*$` | |
| Any text | `^.*$` | |
| Any number | `^\d*$` | Home Fouls, Away Fouls, custom fields |

The *Time mm:ss.d* expression is:

```
^(?:(?:[0-5]?\d:[0-5]\d)|(?:[0-5]?\d\.\d))$
```

**Use**: always. A tight format is the most effective protection against wrong values reaching your graphics. Examples of custom formats: `^[0-3]?\d$` (shot clock with or without a leading zero), `^(1[0-2]|[1-9]):[0-5]\d$` (12-minute quarters), `^[0-4]$` (downs).

### Conf. Th (confidence threshold)

`conf_thresh`: the minimum confidence, in percent, that the Tesseract OCR engine must report for a reading. The slider goes from 0 to 99, and the setting is stored as a fraction (slider ÷ 100, so 60 % is stored as `0.6`). A reading below the threshold is marked `FailedFilter` (yellow). **0 turns the check off, and is the default.**

- ScoreSight uses Tesseract's mean confidence for the recognized text. Tesseract sometimes reports 0 for a correct, non-empty reading; in that case the average of the per-character confidences is used instead.
- A value above 1 in a hand-edited settings file is taken as a percentage (`60` means 60 %).

**Use**: leave it off unless wrong values get through a strict **Format**. Then try 30–50 and raise it slowly while watching for correct readings that turn yellow. Correct readings of real scoreboard footage often score only 30–50 %, so high thresholds reject good values.

{: .new }
In ScoreSight 0.1.x this setting had no effect, because a confidence of 0–100 was compared with a threshold of 0–1. ScoreSight 0.2.0 compares them correctly. Since the old default (50) never did anything, boxes saved by an older version get their threshold set to 0 (off) once, the first time 0.2.0 loads them, so they read exactly as before. The settings file records this with `"boxes_schema_version": 2`, and the log mentions it.

### Average Output

`smoothing`: replaces each reading with the most common value among the box's last 5 accepted (`Success`) readings, comparing whole values. Ties go to the most recent value. Rejected and empty readings don't enter the history.

**Use**: for values that flicker between two readings, for example during LED refresh. A new value must win the vote before it is shown, which delays changes by a couple of detection cycles, so prefer a stricter **Format** or better exposure for fast clocks.

{: .new }
ScoreSight 0.1.x voted character by character, so a change from `12` to `9` could briefly produce `92`. 0.2.0 votes on whole values.

### Skip Empty Values

`skip_empty`: never write an empty value to the box's text file or OBS text source.

**Use**: keep it on (the default). In ScoreSight 0.2.0, text files and OBS text sources receive only good readings, and an empty reading is never a good one, so they keep showing the last value when the board blanks out for a moment (a flickering LED, a person walking in front of the board, a camera flash), whether this option is on or off.

### Remove leading 0s

`remove_leading_zeros`: removes zeros at the start, so `07` becomes `7` (and `00` becomes `0`). An empty reading stays empty.

**Use**: for scoreboards that zero-pad scores or fouls, when your graphics should show `7`.

### Ordinal

`ordinal_indicator`: appends an ordinal suffix: `1` becomes `1st`, `2` becomes `2nd`, `3` becomes `3rd`, `4` becomes `4th`.

**Use**: for periods, quarters, innings or downs when the graphics should show "2nd". On by default for **Period**.

### Dot Counter

`dot_detector`: instead of reading characters, counts the separate bright blobs (larger than about 5 square pixels) in the processed box image and reports the count, for example `3`. The reading is always considered valid, and a box with no lit blobs reports `0`.

**Use**: for indicator lights such as balls/strikes/outs, possession arrows, bonus lights or timeouts left. Use one box per row of lights, and check in **Binary View** that each lit light is a separate white blob. Use **Invert Input** if lights appear dark.

## Image processing

### Binarize

`binarization_method`: how the box is turned into black and white before OCR.

| Value | UI | How it works | Use when |
|---|---|---|---|
| `0` | Global (default) | One automatic (Otsu) threshold computed over the **whole** picture | The picture is mostly the scoreboard (crop helps) and lighting is even |
| `1` | No Binarization | The grayscale image is passed to the OCR as is | Clean, high-contrast screen captures and TV graphics |
| `2` | Local | An automatic (Otsu) threshold computed for **this box only** | Dark surroundings, small board in a wide shot, low contrast. A good first thing to try |
| `3` | Adaptive | A threshold that varies across the box (Gaussian adaptive) | Uneven lighting, glare, reflections or gradients across the digits |

The whole-picture threshold is computed only when at least one box uses *Global*, so the other methods don't pay for it.

### Cleanup

`cleanup_thresh`: removes connected blobs smaller than a fraction of the box area. The limit is (slider position ÷ 100) × 5% of the box area, so at the maximum, blobs smaller than about 5% of the box area are removed.

**Use**: for specks, dust, LED "dead pixels" or bits of the frame inside the box. Too high a value erases thin digits such as `1`.

### Dilate

`dilate`: thickens the bright strokes by this many passes of a 3×3 dilation (0 = off). It applies to the image the OCR reads with every **Binarize** method, including *No Binarization*.

**Use**: raise it when the segments of 7-segment or dot-matrix digits don't touch each other. Lower it to 0 when digits merge into blobs.

{: .new }
In ScoreSight 0.1.x, Dilate changed the Binary View but didn't reach the OCR with every binarization method. In 0.2.0 what you see in Binary View is what the OCR reads.

### V.Scale

`vscale`: squashes the box vertically to `value/10` of its height (10 = unchanged), keeping it centred. It has no effect on boxes only a pixel high.

**Use**: for very tall, narrow fonts that the OCR misreads. Try values of 6–8.

### Skew

`skew`: shears the image horizontally by `value/40` (−0.25 to +0.25) to straighten slanted digits.

**Use**: for italic fonts or a camera that is slightly rotated. Adjust until the digits stand upright in Binary View.

### Invert Input

`invert_patch`: swaps black and white before OCR.

**Use**: when readings improve with the colours swapped, or for dark digits on a light background combined with **Dot Counter**.

### Auto Crop

`autocrop`: crops the box to the area that contains bright pixels, plus a 10-pixel margin, before OCR. With display style **All**, the cropped area is shown as a green rectangle.

**Use**: when the box must be larger than the digits, for example because the value changes width. Combine with **Cleanup** so specks don't widen the crop.

### Rescale Input

`rescale_patch`: scales the box image to 35 pixels high before OCR, the size the bundled models work best with.

**Use**: keep it on. Turn it off only to experiment with external models trained at another size.

### Normalize W-H Ratio

`normalize_wh_ratio`: measures the typical width-to-height ratio of the digits (the median over the last 50 accepted characters `0` and `2`–`9`), then stretches or squeezes the image horizontally so digits come out about half as wide as they are tall. The measurement starts over when you change **Binarize**, **V.Scale**, **Skew**, **Dilate** or **Auto Crop**, and it isn't saved: it is measured again after a restart.

**Use**: for unusually narrow or wide fonts.

### Skip Similar Image

`skip_similar_image`: compares the processed box image with the image of the last OCR that ran for this box. If fewer than 2% of the text pixels (the digits, not the background) changed, OCR is skipped and the box repeats its last good value as an unchanged reading (`SameNoChange`). The comparison image isn't refreshed on skipped cycles, so slow changes add up until they are read. Resizing the box starts over.

**Use**: to save CPU on values that change rarely (scores, periods). Because the change is measured against the digits, a one-digit change (for example `18` to `19`) is read. Turn it off if a very small change (a single segment of a large display) is ever missed.

{: .new }
ScoreSight 0.1.x measured the change against the whole box, so a one-digit change could be skipped, and it reported skipped cycles as a yellow `SIM` reading.

## Fields

### Template Field

`templatefield`, `templatefield_text`: makes a custom field a template whose value is built from other fields, for example `{% raw %}{{Home Score}} - {{Away Score}}{% endraw %}`. Available for custom fields only. See [Template fields](boxes.md#template-fields).

### Composite (Per-Character)

`composite_box` (with the per-character sub-boxes stored as `mini_rects`): experimental. Lets you draw one sub-box per character. The sub-boxes are saved, but in this release recognition still reads the whole box. See [Composite boxes](boxes.md#composite-per-character-boxes-experimental).

### OBS source name

`obs_source_name`: the OBS text source this box updates (see [OBS Studio](obs.md)). It is not editable in the UI. Standard fields use `Home score`, `Away score`, `Clock`, `Period`, `#Home Fouls`, `#Away Fouls` and `shotclock`. Custom fields have an empty name and don't update OBS unless you set one in an exported configuration file.

### is_custom

`is_custom`: `true` for fields created with **+**. Custom fields can be renamed, removed and turned into template fields.

## Other controls

- **Defaults**: restores all settings of the selected box to the defaults for its field.

{: .note }
The **Force Format** checkbox of ScoreSight 0.1.x had no effect and was removed in 0.2.0.
