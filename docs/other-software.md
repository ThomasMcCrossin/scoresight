---
title: Other Software
parent: Outputs
nav_order: 8
description: "Use ScoreSight with NewBlue Captivate/Titler Live, CasparCG, Streamlabs, Home Assistant, Node-RED and anything that reads files or JSON."
---

# Other Software

ScoreSight has built-in integrations for [OBS](obs.md), [vMix](vmix.md) and [overlays.uno](uno.md). Other tools can use one of the generic outputs. For broadcast products (Wirecast, NewBlue Captivate, Ross XPression, SuiteCG, TriCaster, Epiphan Pearl, CasparCG, Singular.live, Chyron PRIME and more), see [Works with…](integrations.md), which has a setup guide for each.

| If your software can... | Use |
|---|---|
| read a text, CSV or XML file | [Text, CSV & XML Files](text-files.md) |
| poll a URL for JSON, XML or CSV | [HTTP Server API](http_server.md) (`http://<scoresight-ip>:18099/json?pivot&all`) |
| show a web page (browser source, HTML template) | The [browser overlays](overlays.md) (built-in or your own HTML, pushed live) |
| receive webhooks / HTTP requests | [Outbound HTTP API](out_api.md) |
| take text lines over a TCP connection or UDP | [TCP / UDP output](tcp-output.md) (presets for CasparCG, Chyron PRIME, Live Score, MagicSoft CG and Vizrt) |

## NewBlue Captivate / Titler Live

ScoreSight has no NewBlue-specific integration, but works with NewBlue through its data features: ScoreSight can push the values to Captivate with the [Outbound HTTP API](out_api.md), or Captivate can read the JSON/XML from the [HTTP server](http_server.md) or the files from the [Text Files](text-files.md) output. [Works with…](integrations.md#newblue-captivate) has both setups. This video shows a complete setup:

<a href="https://youtu.be/ptR-Yh5FSPg" target="_blank" rel="noopener"><img src="image-19.png" width="45%" alt="Video: ScoreSight with NewBlue Captivate"/></a>

## CasparCG

Use the [TCP / UDP output](tcp-output.md#casparcg) with its CasparCG preset: it loads ScoreSight's scorebug template (or your own) over AMCP and updates it as the values change.

Or play a [browser overlay](overlays.md#casparcg) with the HTML producer: `PLAY 1-20 [HTML] "http://<scoresight-ip>:18099/overlay/scorebug"`. For your own template, load `http://<scoresight-ip>:18099/overlay/client.js` in it and mark the elements with `data-field` (see [the overlay contract](overlays.md#the-overlay-contract)). Or adapt the polling template in [Works with…](integrations.md#casparcg).

## Streamlabs Desktop and other OBS-like apps

Use a **Text** source with "read from file" pointing at a field's `.txt` file, or a **Browser Source** with an HTML overlay as above.

## Home Assistant, Node-RED and automation

- **Home Assistant**: a REST sensor on `/json?pivot` (see the [example](http_server.md#home-assistant-rest-sensor)) turns any scoreboard value into a sensor you can automate on, for example to switch lights at the final buzzer.
- **Node-RED / n8n**: either poll `/json` with an HTTP request node, or let ScoreSight push to an HTTP-in node with the [Outbound HTTP API](out_api.md).

## Spreadsheets and statistics

Choose the **Results in .csv file** append mode in the [Text Files](text-files.md#append-modes) output to log every change during a game into `results.csv`, ready for Excel, Google Sheets or pandas.

{: .tip }
Built an integration with another tool? Share it in a [GitHub issue](https://github.com/royshil/scoresight/issues/new/choose) or contribute a page to these docs. See [CONTRIBUTING.md](https://github.com/royshil/scoresight/blob/main/CONTRIBUTING.md).
