---
title: Detection Boxes & Templates
parent: Guides
nav_order: 3
description: "Standard and custom fields, placing boxes, template fields with {{Box Name}} placeholders, and importing/exporting box layouts."
---

# Detection Boxes & Templates
{: .no_toc }

A **box** (also called a field) is a named rectangle over one value on the scoreboard. ScoreSight reads every box on every detection cycle and publishes the result under the box's name.

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Standard fields

The field list always contains seven standard fields. They cannot be renamed or deleted, and they come with sensible defaults:

| Field | Default Type | Default Format | OBS text source name |
|---|---|---|---|
| Home Score | Number | Score 1dd | `Home score` |
| Away Score | Number | Score 1dd | `Away score` |
| Time | Time | Time mm:ss.d | `Clock` |
| Period | Number | Period 1-4, with **Ordinal** on (1st, 2nd...) | `Period` |
| Home Fouls | Number | Any number | `#Home Fouls` |
| Away Fouls | Number | Any number | `#Away Fouls` |
| Shot Clock | Number | Shotclock 0-39 | `shotclock` |

The OBS name is the text source each field updates in OBS (see [OBS Studio](obs.md)).

## Custom fields

Use custom fields for anything else: downs, yards to go, balls/strikes/outs, sets and games, a second shot clock, team names, and so on.

- **Add**: click **+** below the field list. A new field named *Custom 1* (*Custom 2*, ...) appears.
- **Rename**: double-click the field name and type a new name. Names must be unique. Choose them carefully, because they become file names, JSON keys and template placeholders.
- **Remove**: select the field and click **-**.

Custom fields start as a Number field with the *Any number* format. Change the **Type** and **Format** in the box settings.

## Placing a box

1. Select a field in the list. Its icon is a red ✗ while it has no box.
2. Click **Add to Scene ->**. The icon turns into a green ✓ and a box appears in the top-left corner of the picture.
3. Drag the box over the value and resize it with the edge and corner handles.
4. To take a box off the picture, select it and click **Remove Selected**. Its settings are reset the next time you add it.

Boxes and their settings are saved automatically, about half a second after each change. A box that reaches past the edge of the picture (for example after you changed the crop) is read from the part that is still inside the picture. Its saved position isn't changed, so it fits again when you undo the crop.

Tips for good boxes:

- One value per box. Read "12:34" as one Time box, but put the home and away scores in separate boxes.
- Leave a small margin around the digits (about a quarter of the digit height), but keep other text, logos and frame edges out of the box.
- Make the box wide enough for the largest value. A score box should fit "188", not just "88".
- For digits that sometimes disappear (for example a leading "1" that only lights up above 99), size the box for the full width anyway.

## Box settings

When a box is selected, the settings panel below the field list shows its recognition settings: **Type**, **Format**, binarization, cleanup, scaling, skew, smoothing and more. Each box has its own settings. **Defaults** restores the defaults for the selected box.

Every setting is described in the [Per-Box Settings reference](box-settings.md), and [Recognition Tuning](recognition-tuning.md) explains which ones to use when.

## Template fields

A **template field** is a custom field with no box on the picture. Its value is built from other fields' values plus your own text. Use template fields to:

- combine values: `{% raw %}{{Home Score}} - {{Away Score}}{% endraw %}` gives `65 - 39`
- add a prefix or suffix: `{% raw %}Q{{Period}}{% endraw %}`, `{% raw %}{{Time}} left{% endraw %}`, `{% raw %}{{Shot Clock}}s{% endraw %}`
- build a full line for a lower third: `{% raw %}{{Custom 1}} & {{Custom 2}} to go{% endraw %}`

To create one:

1. Click **+** to add a custom field, and rename it (for example *Score Line*).
2. Select it and tick **Template Field** (only available for custom fields).
3. Type the template into the text box next to the checkbox.

Rules:

- `{% raw %}{{Box Name}}{% endraw %}` is replaced with the **last good reading** (green) of the box with exactly that name. Rejected (yellow) and empty readings never appear in a template: it keeps showing the box's last good value instead. The name is case-sensitive, so `{% raw %}{{home score}}{% endraw %}` does not match *Home Score*.
- A template can use other template fields, for example `{% raw %}{{Score Line}} ({{Period}}){% endraw %}`. Templates that refer to each other in a circle are always empty.
- Placeholders for boxes that don't exist are left as they are.
- Until every box the template uses has had a good reading, the template is empty (state `Empty`), so your graphics never show a half-filled line.
- Templates are evaluated on every detection cycle, and the result is sent to every output just like a normal box. A template is reported as a new value (`Success`) when its text changes and as unchanged (`SameNoChange`) when it doesn't, so outputs that only send new values send it only when it changes.
- Template fields don't appear on the picture and have no recognition settings.

{: .new }
In ScoreSight 0.1.x, templates used whatever text the boxes had last read, including rejected readings such as `SIM`, and a template was reported as a new value on every cycle. ScoreSight 0.2.0 uses only good readings and reports changes only.

To stop using a template, untick **Template Field**. The field becomes a regular custom field that you can add to the scene.

## Composite (per-character) boxes (experimental)

The **Composite (Per-Character)** checkbox lets you draw small sub-boxes, one per character, inside a box: click the green **+** in the box to add one, then move and resize it. The sub-boxes are saved with your layout, but **in this release, recognition still reads the whole box**. Per-character recognition is planned for a future release. Leave this option off unless you are testing that work.

## Import and export layouts

- **File > Export Configuration** saves all boxes (names, positions, settings including the **Type**, and composite sub-boxes) to a `.json` file.
- **File > Import Configuration** replaces the current boxes with the ones from a file.

Exported files contain **boxes only**. The source, crop/rotation/4-corner settings and output settings (folders, OBS/vMix/UNO/API connections) are not included. To keep complete, separate setups, use [profiles](profiles.md).

{: .tip }
Advanced: in an exported file, each box's `settings.obs_source_name` sets the OBS text source it updates. Custom fields have an empty name, so they don't update OBS. Set a name in the file and import it again to drive an OBS text source from a custom field. See [OBS Studio](obs.md#custom-fields).
