---
title: Detection Boxes & Templates
parent: Guides
nav_order: 3
description: "Standard and custom fields, placing boxes, template fields with {{Box Name}} placeholders, and importing/exporting box layouts."
---

# Detection Boxes & Templates
{: .no_toc }

A **field** is a named value, such as *Home Score*, and its **box** is the rectangle over that value on the picture. ScoreSight reads every box on every detection cycle and publishes the result under the field's name.

The window has three parts: the **Fields** list on the left, the picture in the middle, and the **inspector** on the right, with a **Box** tab (the selected field's settings) and an **Outputs** tab. Drag the dividers between them to give one more room; ScoreSight remembers it. Double-click a divider (or drag it to the edge) to hide the Fields list or the inspector, and double-click it again to bring it back.

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
| Period | Number | Period 1-4, with **Add ordinal suffix** on (1st, 2nd...) | `Period` |
| Home Fouls | Number | Any number | `#Home Fouls` |
| Away Fouls | Number | Any number | `#Away Fouls` |
| Shot Clock | Number | Shotclock 0-39 | `shotclock` |

The OBS name is the text source each field updates in OBS (see [OBS Studio](obs.md)).

## Custom fields

Use custom fields for anything else: downs, yards to go, balls/strikes/outs, sets and games, a second shot clock, team names, and so on.

- **Add**: click **+** at the top of the field list (or press **Ctrl+N**). A new field named *Custom 1* (*Custom 2*, ...) appears, selected.
- **Rename**: double-click the field name, press **F2**, or right-click it and choose **Rename...**, then type a new name. Names must be unique, and names that differ only in upper and lower case count as the same (their text files would be the same file): ScoreSight says so and asks again. Choose names carefully, because they become file names, JSON keys and template placeholders.
- **Delete**: select the field and click **Delete field** under the list (or press **Del**, **Backspace** on a Mac, or right-click it). ScoreSight asks first. **Delete field** only shows for custom fields.

Custom fields start as a Number field with the *Any number* format. Change the **Type** and **Format** in the Box tab.

## Placing a box

1. Open a source first: until the picture shows, the field list is greyed out and says *Open a source to place fields on the picture*.
2. Select a field in the list. Its icon is a red ✗ while it has no box.
3. Click **Place on picture** under the list (in ScoreSight 0.1.x: **Add to Scene**). The icon turns into a green ✓, a box appears in the top-left corner of the picture, and the Box tab shows its settings.
4. Drag the box over the value and resize it with the edge and corner handles.
5. To take a box off the picture, select its field and click **Remove from picture** (in 0.1.x: **Remove Selected**), which replaces **Place on picture** while the field has a box. Its settings go back to the defaults; if you changed any of them, ScoreSight asks first.

Boxes and their settings are saved automatically, about half a second after each change. A box that reaches past the edge of the picture (for example after you changed the crop) is read from the part that is still inside the picture. Its saved position isn't changed, so it fits again when you undo the crop.

Tips for good boxes:

- One value per box. Read "12:34" as one Time box, but put the home and away scores in separate boxes.
- Leave a small margin around the digits (about a quarter of the digit height), but keep other text, logos and frame edges out of the box.
- Make the box wide enough for the largest value. A score box should fit "188", not just "88".
- For digits that sometimes disappear (for example a leading "1" that only lights up above 99), size the box for the full width anyway.

## Reading the field list

The **Value** column shows each box's last good reading in large type, so you can check the values at a glance during a game. Next to the value, a symbol shows the state of the latest reading (the symbol's shape, not only its colour, tells the states apart), and the line under it shows that state and how long ago the last good reading was made:

| Symbol | Line under the value | Meaning |
|---|---|---|
| ✓ (green) | *new · 0 s* | A new value was read |
| = (grey) | *same · 2 s* | The value hasn't changed |
| ! (amber) | *rejected ‘2l’ · 4 s* | Something was read, but it failed the box's **Format** or **Minimum confidence**. The value shown is still the last good one |
| ∅ (red) | *no reading · 4 s* | Nothing was read. The value shown is still the last good one |

- The age turns amber when the box hasn't had a good reading for a while (20 detection cycles, at least 10 seconds): check the box's position and settings.
- A dash (–) means the box hasn't had a good reading yet.
- While the outputs are paused, the values are marked *not sent*.
- Click a value to select its field, as with a click on the name. Hover over it for the details.

Right-click a field for its actions:

| Action | Key | |
|---|---|---|
| **Place on picture** / **Remove from picture** | | As the button under the list |
| **Rename...** | **F2** or double-click | Custom fields |
| **Delete field...** | **Del** (**Backspace** on a Mac) | Custom fields; asks first |
| **Reset settings to defaults** | | Its box's settings |
| **Copy value** | **Ctrl+C** | The last good reading, to paste elsewhere |
| **Zoom to box** | | Zooms the picture in on its box (**Ctrl+0** fits the whole picture again) |

The keys work while the field list has the focus.

## Box settings

When a field is selected, the **Box** tab of the inspector shows its name and its recognition settings in three sections: **Reading** (**Type**, **Format**...), **Filtering** and **Image cleanup** (collapsed until you open it). Each box has its own settings; **Reset to defaults** restores the defaults for the selected box. With nothing selected, the Box tab explains how to select a field; for a field that isn't on the picture, it explains how to place it.

**All boxes**, at the bottom of the Box tab, holds the settings that apply to every box: the **OCR model**, **Detections / s** and **Update on change**.

Every setting is described in the [Per-Box Settings reference](box-settings.md), and [Recognition Tuning](recognition-tuning.md) explains which ones to use when.

## Template fields

A **template field** is a custom field with no box on the picture. Its value is built from other fields' values plus your own text. Use template fields to:

- combine values: `{% raw %}{{Home Score}} - {{Away Score}}{% endraw %}` gives `65 - 39`
- add a prefix or suffix: `{% raw %}Q{{Period}}{% endraw %}`, `{% raw %}{{Time}} left{% endraw %}`, `{% raw %}{{Shot Clock}}s{% endraw %}`
- build a full line for a lower third: `{% raw %}{{Custom 1}} & {{Custom 2}} to go{% endraw %}`

To create one:

1. Click **+** to add a custom field, and rename it (for example *Score Line*). Don't place it on the picture.
2. In the **Template** section of the Box tab, tick **Build from other fields** (in ScoreSight 0.1.x: **Template Field**). Only custom fields that aren't on the picture can be templates.
3. Type the template into the text box. **Insert field** adds a field at the cursor, spelled exactly as the template needs it (fields that aren't on the picture yet are marked).

Rules:

- `{% raw %}{{Box Name}}{% endraw %}` is replaced with the **last good reading** (green) of the box with exactly that name. Rejected (yellow) and empty readings never appear in a template: it keeps showing the box's last good value instead. The name is case-sensitive, so `{% raw %}{{home score}}{% endraw %}` does not match *Home Score*.
- A template can use other template fields, for example `{% raw %}{{Score Line}} ({{Period}}){% endraw %}`. Templates that refer to each other in a circle are always empty.
- Placeholders for boxes that don't exist are left as they are.
- Until every box the template uses has had a good reading, the template is empty (state `Empty`), so your graphics never show a half-filled line.
- Templates are evaluated on every detection cycle, and the result is sent to every output just like a normal box. A template is reported as a new value (`Success`) when its text changes and as unchanged (`SameNoChange`) when it doesn't, so outputs that only send new values send it only when it changes.
- Template fields don't appear on the picture and have no recognition settings.

{: .new }
In ScoreSight 0.1.x, templates used whatever text the boxes had last read, including rejected readings such as `SIM`, and a template was reported as a new value on every cycle. ScoreSight 0.2.0 uses only good readings and reports changes only.

To stop using a template, untick **Build from other fields**. The field becomes a regular custom field that you can place on the picture.

## Composite (per-character) boxes (experimental)

The **Per-character sub-boxes** checkbox (under *Experimental / legacy* in **Image cleanup**; in ScoreSight 0.1.x: **Composite (Per-Character)**) lets you draw small sub-boxes, one per character, inside a box: click the green **+** in the box to add one, then move and resize it. The sub-boxes are saved with your layout, but **in this release, recognition still reads the whole box**. Per-character recognition is planned for a future release. Leave this option off unless you are testing that work.

## Import and export layouts

- **File > Export Configuration** saves all boxes (names, positions, settings including the **Type**, and composite sub-boxes) to a `.json` file.
- **File > Import Configuration** replaces the current boxes with the ones from a file.

Exported files contain **boxes only**. The source, crop/rotation/4-corner settings and output settings (folders, OBS/vMix/UNO/API connections) are not included. To keep complete, separate setups, use [profiles](profiles.md).

{: .tip }
Advanced: in an exported file, each box's `settings.obs_source_name` sets the OBS text source it updates. Custom fields have an empty name, so they don't update OBS. Set a name in the file and import it again to drive an OBS text source from a custom field. See [OBS Studio](obs.md#custom-fields).
