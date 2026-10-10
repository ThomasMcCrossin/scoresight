---
title: Text, CSV & XML Files
parent: Outputs
nav_order: 1
description: "Write each field to a .txt file, plus results.csv and results.xml, for software that reads text files."
---

# Text, CSV & XML Files
{: .no_toc }

The **Text Files** tab writes the readings to files in a folder. Almost any broadcast or office software can read them: OBS (*Text (GDI+/FreeType 2)* > *Read from file*), vMix Data Sources, NewBlue Captivate/Titler Live, CasparCG, Excel and more.

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Setup

1. Open the **Text Files** tab.
2. Click **Open** next to **Folder** and choose an output folder. **Clear** stops file output.
3. Optionally tick **Save .csv file** and/or **Save .xml file**.
4. Choose an **Append** mode and a **Save / s** rate (see below).

## Files written

| File | Written when | Content |
|---|---|---|
| `<Box Name>.txt` (for example `Home Score.txt`) | Always, once a folder is set | The latest value of that box |
| `results.csv` | **Save .csv file** is ticked | A `Timestamp` column followed by one column per box |
| `results.xml` | **Save .xml file** is ticked | A snapshot of every box: name, text, state and position |

### Per-box `.txt` files

- A box's file is written when its value changes, and again if the file is missing (for example after you emptied the folder).
- Only good readings are written: rejected (yellow) readings never overwrite the file. With **Skip Empty Values** on (the default), empty readings don't either, so the file keeps the last value when, say, the board blanks out for a moment.
- Files are replaced **atomically**: ScoreSight writes a temporary file and swaps it in. Programs that poll the file never see it half-written or empty.
- A file contains just the value, as plain text. In an append mode (see below), each value goes on its own line.

### `results.csv`

A spreadsheet-friendly table with a timestamp and one column per box, for example:

```csv
Timestamp,Home Score,Away Score,Time,Period
2026-10-10T19:42:07.512345,65,39,4:27,2nd
```

Values are quoted correctly when they contain commas or quotes. The header row is written once at the top of the file.

### `results.xml`

An XML snapshot of all boxes (name, recognized text, state and the box position), rewritten as the readings change. Text is properly escaped, so values such as `<` or `&` produce valid XML.

{: .new }
ScoreSight 0.2.0 rewrote file output. Writes are state-based and atomic, the CSV header appears only once, and the XML is properly escaped. This fixes missing `.txt` files ([#6](https://github.com/royshil/scoresight/issues/6)) and makes `results.csv` usable as a live data file ([#29](https://github.com/royshil/scoresight/issues/29)).

## Append modes

The **Append** drop-down chooses which files keep a history instead of only the latest value:

| Append mode | `.txt` files | `results.csv` |
|---|---|---|
| **Don't append results** (default) | Latest value only | Header + latest row only (a live snapshot) |
| **Results in .csv file** | Latest value only | A new row is added for each update (a log) |
| **Results in .txt files** | Each new value is added on a new line | Header + latest row only |
| **Results in both** | Each new value on a new line | A new row for each update |

Use **Don't append results** for live graphics, and an append mode to log a whole game for later analysis.

## Save / s

**Save / s** (1–10, default 5) limits how many times per second the files are updated. Lower it if the reading software struggles with frequent changes, and raise it for fast clocks.

## Using the files

- **OBS**: add a *Text (GDI+)* (Windows) or *Text (FreeType 2)* source and enable **Read from file**, pointing at `Time.txt`, for example. To update OBS without files, see [OBS Studio](obs.md).
- **vMix**: add the CSV or XML file as a **Data Source** (Settings > Data Sources) and bind title fields to its columns. Alternatively, use the direct [vMix integration](vmix.md).
- **NewBlue, CasparCG and others**: see [Other Software](other-software.md).

{: .tip }
Keep the output folder on a local disk. Network shares and cloud-synced folders (OneDrive, Dropbox, iCloud) can delay or lock files.
