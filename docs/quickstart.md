---
title: Quickstart
parent: Getting Started
nav_order: 2
description: "Read your first scoreboard with ScoreSight in about five minutes."
---

# Quickstart
{: .no_toc }

This walkthrough takes you from a fresh install to live scores in your graphics in about five minutes.

<details open markdown="block">
  <summary>Steps</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

![ScoreSight reading the time and both scores from an LED scoreboard](image-11.png)

## 1. Open a source

Start ScoreSight. In the **Source** drop-down at the top of the window, choose where the picture comes from:

- a camera or capture card (listed by name), or an NDI source,
- **Open a Video File** (`.mp4`, `.avi`, `.mov`), which is useful for practising with a recording,
- **URL Source (HTTP, RTSP)** for IP cameras and network streams,
- **Screen Capture** for a window or your whole screen (Windows and macOS).

Cameras and NDI sources are found in the background, so they may appear in the list a moment after the window opens. The picture appears in the viewer after a moment, and the rest of the window becomes active. If your camera isn't listed, click **Reload**. More details: [Video Sources](sources.md).

## 2. Straighten the picture (optional)

The view tools above the picture help when the camera is not square to the scoreboard:

- **Rotate** turns the picture in 90° steps.
- **Crop** removes pixels from the edges.
- **4-corner Correction**: click it, then click the four corners of the scoreboard. ScoreSight warps the picture so the board becomes a flat rectangle.
- **Stabilize** removes small camera bumps and drift.

Do this **before** you draw boxes, because boxes are placed on the corrected picture. More details: [Viewer & Image Tools](view-tools.md).

## 3. Add boxes over the values

The **Fields** list on the left contains the standard fields: Home Score, Away Score, Time, Period, Home Fouls, Away Fouls and Shot Clock.

1. Click a field, for example **Home Score**.
2. Click **Place on picture** under the list. A red box appears in the top-left corner of the picture, and the **Box** tab on the right shows its settings.
3. Drag the box over the home score and drag its edges or corners to resize it. Leave a small margin around the digits.
4. Repeat for every value you need.

Need something that isn't in the list, such as "Downs", "Yards to go" or "Balls"? Click **+** to add a custom field, double-click it (or press **F2**) to rename it, then place it on the picture the same way. More details: [Detection Boxes & Templates](boxes.md).

## 4. Check the readings

Within a second, each box shows what ScoreSight reads, and the **Value** column in the field list shows the latest good reading. The colour of the text on each box tells you its state:

| Colour | State | Meaning |
|---|---|---|
| Green | `Success` | A new value was read and sent to the outputs. |
| Light green | `SameNoChange` | The same value as the last good reading, for example with **Update on change** on (see [Outputs](outputs.md#which-readings-are-sent)). |
| Yellow | `FailedFilter` | Something was read but rejected by the box's **Format**, or by its confidence threshold. |
| Red `EMP` | `Empty` | Nothing was read, or the box is over a blank area. |

If readings are wrong or unstable:

- Click **Binary View** to see the black-and-white image the OCR engine reads. Digits should be solid and clearly separated from the background.
- Select the box and, in the **Box** tab on the right, set its **Type** (Number, Time or Text) and a **Format** preset, such as *Time mm:ss* or *Score ddd*.
- Try another **OCR model** (under **All boxes**, at the bottom of the Box tab): *Daktronics* for segment/LED digits, or *General Scoreboard Large* for big digits.

The [Recognition Tuning](recognition-tuning.md) guide walks through this step by step.

## 5. Send the results to your graphics

Pick one or more outputs in the **Outputs** tab, on the right next to the **Box** tab. Select one to show its settings under the list, and turn it on with its switch:

| Output | What it does | Guide |
|---|---|---|
| **Text files** | Writes `<Box Name>.txt`, and optionally `results.csv` and `results.xml`, to a folder | [Text, CSV & XML Files](text-files.md) |
| **HTTP server** | Serves live HTML, JSON, XML and CSV at `http://localhost:18099` (or the port set with `--port`). Always on | [HTTP Server API](http_server.md) |
| **OBS** | Updates OBS text sources over the OBS WebSocket | [OBS Studio](obs.md) |
| **vMix** | Updates vMix title fields through the vMix Web API (port 8088) | [vMix](vmix.md) |
| **UNO** | Updates an overlays.uno control app | [Overlays.uno](uno.md) |
| **HTTP API** | Sends the readings to your own HTTP endpoint | [Outbound HTTP API](out_api.md) |

Each row shows whether that output works: ● working, ◐ waiting for a value, ▲ retrying or needs attention, ■ not working (with what to do), ○ off. The status bar repeats it for every output; click one to show its settings. See [Outputs](outputs.md#is-it-working-the-outputs-list-and-the-status-bar).

The quickest test: open [http://localhost:18099/json?pivot](http://localhost:18099/json?pivot) in a browser on the same computer. You should see something like `{"Home Score": "65", "Away Score": "39", "Time": "4:27"}`.

## 6. Keep your setup

ScoreSight saves your boxes and settings automatically and reopens the last source (camera, NDI source, URL stream, video file or screen capture) at the next start. To back up a box layout or move it to another computer, use **File** > **Export Configuration**, and **File** > **Import Configuration** to load it again. See [Settings, Files & Command Line](configuration.md).

## Global controls worth knowing

| Control | What it does |
|---|---|
| **Detections / s** | How many times per second the boxes are read (1–15, default 5). Under **All boxes**, at the bottom of the Box tab. |
| **Update on change** | When on (default), a value that hasn't changed is marked "unchanged", and vMix and UNO don't resend it. Under **All boxes**. |
| **Pause outputs** | At the top of the field list. Freezes all outputs at their current values, for example during a timeout or replay (**Ctrl+Shift+P**). The field list keeps updating; an orange banner and the status bar show that the outputs are paused. Click **Resume outputs** to continue. |
| **OCR model** | The recognition model used for all boxes, under **All boxes**. See [OCR Models](ocr-models.md). |
| **Status bar** | At the bottom of the window: the source with its resolution and frame rate, how many times per second the boxes are read, **PAUSED** while the outputs are paused, and the HTTP server's address with a **Copy** button. |
| **File > Appearance** | Switch between the System, Light and Dark colour schemes. |

## Where to next

- [Recognition Tuning](recognition-tuning.md): get rock-solid readings.
- [Outputs](outputs.md): all integrations in detail.
- [Performance Tuning](performance.md): understand the on-screen statistics and reduce CPU use.
