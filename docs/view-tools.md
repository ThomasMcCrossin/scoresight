---
title: Viewer & Image Tools
parent: Guides
nav_order: 2
description: "Zoom and pan the viewer, Binary View, 4-corner perspective correction, crop, rotate, stabilize, box display styles and the OSD statistics."
---

# Viewer & Image Tools
{: .no_toc }

The large viewer shows the source picture with your boxes on top. The tool bar above it changes how the picture is processed before any box is read.

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Processing order

Every frame goes through the same steps, in this order:

1. **Rotate** (0°, 90°, 180°, 270°)
2. **Crop** (left / top / right / bottom pixels)
3. **Stabilize** (if enabled)
4. **4-corner correction** (perspective warp, if set)
5. Convert to grayscale, plus one black-and-white version of the whole picture if a box uses [Global binarization](box-settings.md#binarize).
6. Read every box with its own [per-box settings](box-settings.md), each on its own copy of the picture.

Boxes are positioned on the **result** of steps 1–4. Change rotation, crop or 4-corner correction first, then place your boxes. If you change them later, check that the boxes still sit on the right digits.

## Navigating the viewer

| Action | How |
|---|---|
| Zoom in / out | **Ctrl + mouse wheel** (**⌘ Cmd + mouse wheel** on macOS), from 0.33x to 3x, in 5% steps |
| Scroll | Mouse wheel (vertical). Use the scroll bars when zoomed in |
| Pan | Drag with the **middle mouse button** |
| Fit the picture to the window | **1:1** button |
| Select a box | Click it (the field list selects it too) |
| Move a box | Drag it |
| Resize a box | Drag an edge or a corner handle. Handles appear on the selected box |
| Deselect | Click empty space in the picture, or press **Esc** |

See [Keyboard & Mouse](keyboard-mouse.md) for the full reference.

## Binary View

**Binary View** switches the preview between the camera picture and the black-and-white image the OCR engine reads. Inside each box you see the result of that box's own settings (binarization method, cleanup, vertical scale, skew and dilation), exactly as the OCR receives it.

This is the most useful tuning tool: the OCR can only read what you see here. Digits should be solid and clearly separated from the background, with no stray specks touching them. See [Recognition Tuning](recognition-tuning.md).

## 4-corner correction

When the camera looks at the scoreboard at an angle, the digits are skewed and get smaller towards the far side. 4-corner correction warps the picture so the scoreboard becomes a straight rectangle.

1. Click **4-corner Correction**.
2. Click the four corners of the scoreboard (or of the area you want straightened) in the picture. The order doesn't matter: ScoreSight sorts them clockwise from the top-left. Red markers and a red outline show your clicks.
3. After the fourth click the warp is applied and saved, and the button stays highlighted.

To redo it, click the button again (this clears the correction), then click it once more and pick new corners. To remove the correction, click the button so it is no longer highlighted.

If the four points can't be used (for example the same corner clicked twice, points almost in a line, a crossed shape, or a very small area), ScoreSight shows "Invalid four-corner selection", clears the points and lets you click four new corners. An unusable correction saved by an older version is discarded at startup.

{: .tip }
Pick corners that form a real rectangle in the world, such as the outer frame of the scoreboard.

## Crop

**Crop** opens the crop panel with **Left**, **Top**, **Right** and **Bottom** values in pixels. Cropping removes the parts of the picture you don't need. That reduces CPU use, makes the picture larger in the viewer and, with [Global binarization](box-settings.md#binarize), improves the black-and-white threshold because the dark surroundings are gone. Click **Crop** again to turn cropping off; the values are kept.

## Rotate

**Rotate** turns the picture 90° clockwise each time you click it (0° → 90° → 180° → 270° → 0°). Use it for cameras mounted sideways or upside down.

## Stabilize

**Stabilize** compensates for small camera movements, such as a tripod bumped during the game or a camera that slowly drifts. When you enable it, ScoreSight averages the next few processed frames into a reference image, and passes the frames through unchanged meanwhile. After that, it aligns every new frame to the reference.

- Enable it after the camera is in its final position.
- To take a new reference (for example after re-aiming the camera), turn **Stabilize** off and on again. A change of the picture size also starts over.
- Frames that can't be aligned (black or featureless frames, or too few matching details) are passed through unchanged instead of being distorted.
- Leave it off for fixed, rigid mounts and for screen capture, because it costs CPU.

## Box display style

The drop-down next to the view tools controls how boxes are drawn:

| Style | Shows |
|---|---|
| **No Box** | Nothing, except the box you have selected |
| **Outline** | Box outlines only |
| **Names** | Outlines, box names and the current reading |
| **All** (default) | Everything in *Names*, plus a green rectangle around the area that was actually read (with [Auto Crop](box-settings.md#auto-crop)) and blue rectangles around each character the OCR found |

The reading under each box is colour-coded. Green means a new value, light green an unchanged value, yellow a value rejected by a filter, and red `EMP` means nothing was read.

## OSD (on-screen statistics)

**OSD** toggles the statistics in the top-left corner of the viewer:

| Statistic | Meaning |
|---|---|
| **Frames/s** | How many frames per second ScoreSight reads from the source (capped at about 33). |
| **Updates/s** | How many times per second the boxes are read. Follows the **Detections / s** slider (1–15, default 5). |
| **Previews/s** | How often the preview picture is refreshed. This is about **1 per second on purpose**, at any Detections / s setting, to leave the CPU for OCR. It does not affect how fast values are read or sent. |
| **Resolution** | The resolution delivered by the source. |

See [Performance Tuning](performance.md) for how to interpret and improve these numbers.
