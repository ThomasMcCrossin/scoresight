---
title: Other Software
parent: Outputs
nav_order: 7
description: "Use ScoreSight with NewBlue Captivate/Titler Live, CasparCG, Streamlabs, Home Assistant, Node-RED and anything that reads files or JSON."
---

# Other Software

ScoreSight has built-in integrations for [OBS](obs.md), [vMix](vmix.md) and [overlays.uno](uno.md). Other tools can use one of the generic outputs:

| If your software can... | Use |
|---|---|
| read a text, CSV or XML file | [Text, CSV & XML Files](text-files.md) |
| poll a URL for JSON, XML or CSV | [HTTP Server API](http_server.md) (`http://<scoresight-ip>:18099/json?pivot`) |
| show a web page (browser source, HTML template) | An HTML page that polls the [HTTP server](http_server.md#custom-html-overlay-obs-browser-source-vmix-web-browser-input) |
| receive webhooks / HTTP requests | [Outbound HTTP API](out_api.md) |

## NewBlue Captivate / Titler Live

ScoreSight has no NewBlue-specific integration, but works with NewBlue through its data features. Point your title's data at the files from the [Text Files](text-files.md) output (one `.txt` per field, or `results.csv` / `results.xml`), or at the JSON/XML from the [HTTP server](http_server.md). This video shows a complete setup:

<a href="https://youtu.be/ptR-Yh5FSPg" target="_blank" rel="noopener"><img src="image-19.png" width="45%" alt="Video: ScoreSight with NewBlue Captivate"/></a>

## CasparCG

Use an HTML template that polls `http://<scoresight-ip>:18099/json?pivot` and updates its elements. The [custom HTML overlay example](http_server.md#custom-html-overlay-obs-browser-source-vmix-web-browser-input) is a good starting point. Play it with CasparCG's HTML producer.

## Streamlabs Desktop and other OBS-like apps

Use a **Text** source with "read from file" pointing at a field's `.txt` file, or a **Browser Source** with an HTML overlay as above.

## Home Assistant, Node-RED and automation

- **Home Assistant**: a REST sensor on `/json?pivot` (see the [example](http_server.md#home-assistant-rest-sensor)) turns any scoreboard value into a sensor you can automate on, for example to switch lights at the final buzzer.
- **Node-RED / n8n**: either poll `/json` with an HTTP request node, or let ScoreSight push to an HTTP-in node with the [Outbound HTTP API](out_api.md).

## Spreadsheets and statistics

Choose the **Results in .csv file** append mode in the [Text Files](text-files.md#append-modes) output to log every change during a game into `results.csv`, ready for Excel, Google Sheets or pandas.

{: .tip }
Built an integration with another tool? Share it in a [GitHub issue](https://github.com/royshil/scoresight/issues/new/choose) or contribute a page to these docs. See [CONTRIBUTING.md](https://github.com/royshil/scoresight/blob/main/CONTRIBUTING.md).
