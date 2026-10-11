---
title: Home
layout: home
nav_order: 1
permalink: /
description: "ScoreSight documentation: install, set up, tune and integrate real-time scoreboard OCR."
---

# ScoreSight documentation
{: .fs-9 }

Real-time scoreboard OCR for live production. Free, open source, and available for Windows, macOS and Linux.
{: .fs-6 .fw-300 }

[Download ScoreSight](https://github.com/royshil/scoresight/releases/latest){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[Quickstart](quickstart.md){: .btn .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View on GitHub](https://github.com/royshil/scoresight){: .btn .fs-5 .mb-4 .mb-md-0 }

---

ScoreSight reads text and numbers from a live video feed (a stadium scoreboard filmed by a camera, a capture card, an NDI feed, an RTSP stream, a window on your screen or a video file). It sends the values to your production tools many times per second. You draw a box around each value you care about, such as the home score, the clock or the period. ScoreSight then reads every box with [PaddleOCR's PP-OCRv6](https://github.com/PaddlePaddle/PaddleOCR) text recognition models (or [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)) and publishes the results to text files, a built-in HTTP server, OBS, vMix, overlays.uno, or any HTTP endpoint you choose.

<div align="center">
<a href="https://youtu.be/MtctQZ2DIjU" target="_blank" rel="noopener"><img src="scoresight_getting_started.png" width="60%" alt="Video: getting started with ScoreSight"/></a>
</div>

## Start here

| I want to... | Go to |
|---|---|
| Install ScoreSight | [Installation](INSTALL.md) |
| Read my first scoreboard in five minutes | [Quickstart](quickstart.md) |
| Connect a camera, NDI feed, RTSP stream, screen or video file | [Video Sources](sources.md) |
| Get the data into OBS, vMix, UNO, a browser or my own app | [Outputs](outputs.md) |
| Fix readings that are wrong or flicker | [Recognition Tuning](recognition-tuning.md) |
| Run two scoreboards or cameras at once | [Multiple Instances & Profiles](profiles.md) |
| Fix a problem | [Troubleshooting](troubleshooting.md) and [FAQ](faq.md) |
| Build ScoreSight or contribute | [Developer Guide](development/index.md) |

## How it works

1. **Capture**: ScoreSight grabs frames from your [source](sources.md).
2. **Correct**: Optional rotation, cropping, stabilization and 4-corner perspective correction make the scoreboard flat and steady ([Viewer & Image Tools](view-tools.md)).
3. **Read**: Every [detection box](boxes.md) is read by an [OCR model](ocr-models.md) (PP-OCR by default, or Tesseract, which first cleans the box up according to its [per-box settings](box-settings.md)), then checked against the box's format.
4. **Validate**: Format rules (for example "a clock looks like `mm:ss`") reject impossible readings before they reach your graphics.
5. **Publish**: Results go to every [output](outputs.md) you enabled. Outputs run in the background, so a slow or offline target never freezes the app.

## Video tutorials

The videos show older versions of ScoreSight, so some screens look slightly different today. In particular, use port **8088** for vMix (see [vMix](vmix.md)).

<div>
<a href="https://youtu.be/wMNolI0w0tE" target="_blank" rel="noopener"><img src="image-16.png" width="30%" alt="Video tutorial: scoreboard OCR with ScoreSight"/></a>
<a href="https://youtu.be/ACY4-yT3x84" target="_blank" rel="noopener"><img src="image-17.png" width="30%" alt="Video tutorial: setting up ScoreSight"/></a>
<a href="https://youtu.be/yowoYzBWrps" target="_blank" rel="noopener"><img src="image-18.png" width="30%" alt="Video tutorial: ScoreSight with vMix"/></a>
<a href="https://youtu.be/ptR-Yh5FSPg" target="_blank" rel="noopener"><img src="image-19.png" width="30%" alt="Video tutorial: ScoreSight with NewBlue Captivate"/></a>
<a href="https://youtu.be/QO76EFmJ7Ig" target="_blank" rel="noopener"><img src="image-23.png" width="30%" alt="Video tutorial: collecting OCR training data"/></a>
</div>

## Getting help

- Search these docs (the search box at the top) and read [Troubleshooting](troubleshooting.md).
- Look through [existing issues](https://github.com/royshil/scoresight/issues?q=is%3Aissue).
- [Open a new issue](https://github.com/royshil/scoresight/issues/new/choose) and attach your log files. [Troubleshooting](troubleshooting.md#collect-logs-first) explains where to find them.
