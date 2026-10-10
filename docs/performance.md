---
title: Performance Tuning
parent: Guides
nav_order: 6
description: "Understand Frames/s, Updates/s and Previews/s, and reduce CPU use and latency in ScoreSight."
---

# Performance Tuning
{: .no_toc }

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Reading the OSD numbers

Turn on **OSD** to see the statistics in the corner of the viewer:

| Number | What it measures | Typical value |
|---|---|---|
| **Frames/s** | Frames read from the source per second. ScoreSight caps this at about 33. | 25–33 for a healthy camera or stream. Lower if the source is slower or the CPU is busy |
| **Updates/s** | How many times per second all boxes are read. | Close to your **Detections / s** setting (1–15, default **5**) |
| **Previews/s** | How often the preview picture in the viewer refreshes. | About **1**. This is intentional |

{: .important }
A low **Previews/s** is **not** a problem. The preview is refreshed about once per second to save CPU for recognition. Readings are still taken and sent at the **Updates/s** rate. If your graphics update slowly, look at **Updates/s** and your output settings, not at the preview.

## How fast do you need to be?

**Detections / s** sets how often the boxes are read:

| Content | Suggested Detections / s |
|---|---|
| Scores, periods, fouls, timeouts | 2–5 |
| Game clock showing seconds | 5 (the default). Higher values don't make a once-per-second change appear sooner in a meaningful way |
| Clock with tenths (`9.5`), shot clock in the final seconds | 10–15 |

Every reading costs CPU for **every** box, so the total cost is roughly *number of boxes × detections per second*. If you need a fast shot clock but slow scores, consider running the shot clock in a [second instance](profiles.md).

## Reducing CPU use

1. **Lower Detections / s** to what you actually need.
2. **Remove boxes you don't use**, and keep boxes tight around the digits.
3. **Crop** the picture to the scoreboard. Less picture means less processing per frame.
4. Turn on **Skip Similar Image** for values that rarely change (scores, periods). When a box's image hasn't changed, OCR is skipped for that box.
5. Turn **Stabilize** off when the camera is fixed or you use screen capture.
6. Use a lower source resolution. In [Video Settings](sources.md#cameras-and-capture-cards), 1280x720 with the `MJPG` format is a good choice for USB cameras. For IP cameras, use a sub stream.
7. Prefer **General Scoreboard** over **General Scoreboard Large** if both read your board correctly. The large model is slower.
8. Close the [log viewer](troubleshooting.md#collect-logs-first) window when you don't need it.

## Output latency

- Outputs (OBS, vMix, UNO, the outbound API) send in the background. If a target is slow or unreachable, ScoreSight keeps only the latest values and drops intermediate ones. The window and the readings never wait for the network.
- **Update on change** (on by default) means unchanged values are not resent to vMix, UNO and file outputs, which keeps traffic low. Turn on **Send Same?** in the vMix/UNO tabs only if your target needs constant refreshes.
- The [outbound HTTP API](out_api.md) sends on **every** detection cycle. Point it at a fast endpoint on your local network.
- File outputs are written at most **Save / s** times per second (1–10, set in the **Text Files** tab).
- The built-in [HTTP server](http_server.md) always serves the latest values. Browser overlays that poll it every 100–250 ms are fine.

## Video files

When tuning on a recording, use the **Speed** button (x1–x32) to skip quickly to the interesting parts. Speed skips frames. It doesn't change how often boxes are read.

## Multiple instances

Each ScoreSight instance runs its own capture and OCR, so CPU use adds up. On a busy machine, prefer one instance with several boxes over several instances with one box each, unless you need different cameras. See [Multiple Instances & Profiles](profiles.md).
