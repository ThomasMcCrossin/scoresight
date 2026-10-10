---
title: FAQ
nav_order: 7
description: "Frequently asked questions about ScoreSight."
---

# Frequently Asked Questions
{: .no_toc }

<details open markdown="block">
  <summary>Questions</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Is ScoreSight free?

Yes. ScoreSight is free and open source under the [MIT license](https://github.com/royshil/scoresight/blob/main/LICENSE), for personal and commercial productions alike. There is no paid edition, no watermark and no time limit.

## Which sports and scoreboards does it support?

Any scoreboard whose values you can see in a video picture: LED, LCD, 7-segment, dot-matrix and flip-digit boards, as well as TV score bugs, games, web pages and apps. The seven standard fields (scores, time, period, fouls, shot clock) suit basketball-style boards. For everything else, add [custom fields](boxes.md#custom-fields): downs and yards to go in American football ([#32](https://github.com/royshil/scoresight/issues/32)), sets and games, innings, korfball shot clocks ([#8](https://github.com/royshil/scoresight/issues/8)), and so on.

## Can it read indicator lights, like balls, strikes and outs?

Yes. Use [Dot Counter](box-settings.md#dot-counter) on a box that covers a row of lights. ScoreSight reports how many are lit ([#4](https://github.com/royshil/scoresight/issues/4)).

## Can it read one character at a time?

Put one box over each digit and combine them with a [template field](boxes.md#template-fields) such as `{% raw %}{{Digit 1}}{{Digit 2}}{% endraw %}`. The *Composite (Per-Character)* option is experimental: in this release you can draw the sub-boxes, but recognition doesn't use them yet ([#3](https://github.com/royshil/scoresight/issues/3)).

## Can I use two cameras?

Yes, by running two instances with different [profiles](profiles.md), for example `--profile shotclock --port 18100`. Or combine both cameras into one picture in OBS/vMix and send that to ScoreSight ([#8](https://github.com/royshil/scoresight/issues/8)).

## Does ScoreSight need an internet connection?

No. Reading the scoreboard and all local outputs (files, the HTTP server, OBS, vMix) work offline. You only need a network for network sources (NDI, RTSP), for outputs on other computers, and for cloud services you configure yourself (overlays.uno or your own API URL).

## Does ScoreSight send my data anywhere?

Only to the outputs you configure. It has no accounts, no cloud service of its own and no analytics.

## How many boxes can I use?

There is no fixed limit. Each box costs CPU on every detection cycle, so dozens of boxes at 15 detections per second need a fast computer. See [Performance Tuning](performance.md).

## How fast is it?

Up to 15 readings per second (the **Detections / s** slider), with all boxes read on every cycle. The preview picture refreshes about once per second on purpose. It doesn't affect how fast values are read or sent.

## Which languages is the interface available in?

English, French, Spanish, German, Italian, Japanese, Korean, Dutch, Polish, Portuguese (Brazil), Portuguese (Portugal), Russian and Chinese (Simplified). ScoreSight picks your system language at startup. Change it with **File > Language**. Want to help translate? See [Translations](development/translations.md).

## Can I make the interface dark (or light)?

Yes: **File > Appearance** > **Dark**, **Light** or **System** ([#50](https://github.com/royshil/scoresight/issues/50)).

## Can other computers on my network read the data?

Yes, through the [HTTP server](http_server.md) at `http://<scoresight-ip>:18099`. Allow ScoreSight through the firewall on trusted networks only. There is no password protection (see [SECURITY.md](https://github.com/royshil/scoresight/blob/main/SECURITY.md)).

## Can I control ScoreSight remotely (start/stop, change boxes)?

Not at the moment. The HTTP server is read-only.

## Do you still need OCR training data?

The project doesn't currently run a central data collection. You can use the [built-in tools](data_annotation.md) to collect and annotate data and train a model for your own scoreboard. If you'd like to contribute data or a model, [open an issue](https://github.com/royshil/scoresight/issues/new/choose) first to discuss it ([#54](https://github.com/royshil/scoresight/issues/54)).

## Where are my settings? How do I back them up or move them to another computer?

See [Settings, Files & Command Line](configuration.md#where-scoresight-keeps-its-files). To move only the boxes, use **File > Export Configuration** and **Import Configuration**. To move everything, copy `scoresight.json` (or a profile's `scoresight-<name>.json`) to the same folder on the other computer.

## How do I report a bug or request a feature?

Use the [issue forms on GitHub](https://github.com/royshil/scoresight/issues/new/choose). For bugs, attach your [logs](troubleshooting.md#collect-logs-first). Security issues: see [SECURITY.md](https://github.com/royshil/scoresight/blob/main/SECURITY.md).

## How can I help?

Report bugs, improve these docs, translate the interface, share scoreboard samples, or contribute code. See [CONTRIBUTING.md](https://github.com/royshil/scoresight/blob/main/CONTRIBUTING.md).
