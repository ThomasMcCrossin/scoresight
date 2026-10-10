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
| [Conf. Th](#conf-th-confidence-threshold) | `conf_thresh` | 0.00–0.99 (slider 0–99) | 0.50 |
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

1. takes the box area from the processed picture and **binarizes** it (*Binarize*),
2. removes small specks (*Cleanup*),
3. squashes it vertically (*V.Scale*) and shears it (*Skew*),
4. thickens strokes (*Dilate*),
5. inverts it (*Invert Input*),
6. skips OCR if the image hasn't changed (*Skip Similar Image*),
7. crops to the text (*Auto Crop*),
8. scales it (*Rescale Input*, *Normalize W-H Ratio*),
9. counts dots (*Dot Counter*) **or** runs OCR with the character set of the *Type*,
10. checks the raw text against the *Format* and the *Conf. Th* threshold,
11. applies *Average Output*, *Remove leading 0s* and *Ordinal*,
12. marks the reading `Empty` if no text is left, or `SameNoChange` if it equals the previous reading and **Update on change** is on.

**Binary View** shows the result of steps 1–4 for every box.

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

`conf_thresh`: the minimum average confidence (0–99 on the slider) the OCR engine must report for the reading. Below it, the reading is marked `FailedFilter`.

**Use**: raise it (for example to 70) when random wrong values slip through. Lower it if correct readings turn yellow. Combine it with a strict **Format**.

### Average Output

`smoothing`: replaces each reading with a per-character majority vote over the last 5 readings of the box.

**Use**: for values that flicker between two readings, for example during LED refresh. It delays changes by a few cycles, so prefer a stricter **Format** or better exposure for fast clocks.

### Skip Empty Values

`skip_empty`: when a reading is empty, don't overwrite the box's text file or OBS text source. They keep showing the last value.

**Use**: keep it on (the default) so a momentary blank (a flickering LED, a person walking in front of the board, a camera flash) doesn't blank your graphics. Turn it off if an empty board should also clear the graphics.

### Remove leading 0s

`remove_leading_zeros`: removes zeros at the start, so `07` becomes `7` (and `00` becomes `0`).

**Use**: for scoreboards that zero-pad scores or fouls, when your graphics should show `7`.

### Ordinal

`ordinal_indicator`: appends an ordinal suffix: `1` becomes `1st`, `2` becomes `2nd`, `3` becomes `3rd`, `4` becomes `4th`.

**Use**: for periods, quarters, innings or downs when the graphics should show "2nd". On by default for **Period**.

### Dot Counter

`dot_detector`: instead of reading characters, counts the separate bright blobs (larger than about 5 square pixels) in the processed box image and reports the count, for example `3`. The reading is always considered valid.

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

### Cleanup

`cleanup_thresh`: removes connected blobs smaller than a fraction of the box area. The limit is (slider position ÷ 100) × 5% of the box area, so at the maximum, blobs smaller than about 5% of the box area are removed.

**Use**: for specks, dust, LED "dead pixels" or bits of the frame inside the box. Too high a value erases thin digits such as `1`.

### Dilate

`dilate`: thickens the white strokes by this many passes of a 3×3 dilation (0 = off).

**Use**: raise it when the segments of 7-segment or dot-matrix digits don't touch each other. Lower it to 0 when digits merge into blobs.

### V.Scale

`vscale`: squashes the box vertically to `value/10` of its height (10 = unchanged), keeping it centred.

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

`normalize_wh_ratio`: measures the typical width-to-height ratio of the digits in the first readings, then stretches the image horizontally so digits come out about half as wide as they are tall.

**Use**: for unusually narrow or wide fonts.

### Skip Similar Image

`skip_similar_image`: compares the processed box image with the last one that was read. If less than 5% of it differs, OCR is skipped and the reading is `SIM` with state `FailedFilter` (yellow). Outputs that only send good values (text files, OBS, vMix, UNO, the `?pivot` HTTP endpoints) keep the previous value.

**Use**: to save CPU on values that change rarely (scores, periods). Turn it off if a real change is ever missed (for example when only a thin segment changes).

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

- **Force Format**: has no effect in this version.
- **Defaults**: restores all settings of the selected box to the defaults for its field.
