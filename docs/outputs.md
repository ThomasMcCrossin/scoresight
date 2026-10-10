---
title: Outputs
nav_order: 4
has_children: true
description: "Overview of every ScoreSight output: text files, the HTTP server, OBS, vMix, overlays.uno and outbound HTTP requests."
---

# Outputs

ScoreSight can publish its readings to several destinations at the same time. Each output has its own tab at the bottom left of the main window.

| Output | Tab | Direction | Sends | Best for |
|---|---|---|---|---|
| [Text, CSV & XML files](text-files.md) | **Text Files** | ScoreSight writes files | `<Box Name>.txt`, `results.csv`, `results.xml` | Any software that reads text files: OBS text (from file), vMix Data Sources, NewBlue, CasparCG, Excel |
| [HTTP server](http_server.md) | **Browser** | Other software pulls from ScoreSight | HTML, JSON, XML, CSV on port 18099 | Browser sources, web overlays, data feeds, scripts, Home Assistant |
| [OBS Studio](obs.md) | **OBS** | ScoreSight pushes over the OBS WebSocket | Text of OBS text sources | OBS scoreboards without browser sources |
| [vMix](vmix.md) | **VMix** | ScoreSight pushes to the vMix Web API | `SetText` on title fields | vMix GT titles |
| [Overlays.uno](uno.md) | **UNO** | ScoreSight pushes to the UNO control app API | Commands / overlay fields | overlays.uno graphics |
| [Outbound HTTP API](out_api.md) | **API** | ScoreSight pushes to your URL | JSON, XML, CSV or GET query | Your own server, cloud functions, automations |
| [Other software](other-software.md) | (uses the outputs above) | | | NewBlue Captivate/Titler Live, CasparCG, Streamlabs, Home Assistant and more |

## Which readings are sent?

Every detection cycle produces one reading per box, in one of four **states**:

| State | Meaning | Colour in the viewer |
|---|---|---|
| `Success` | A new value was read | Green |
| `SameNoChange` | The same value as the box's last good reading: with **Update on change** on, for a box whose OCR was skipped by [Skip Similar Image](box-settings.md#skip-similar-image), and for a [template field](boxes.md#template-fields) whose text didn't change | Light green |
| `FailedFilter` | Something was read but it failed the box's Format or confidence threshold | Yellow |
| `Empty` | Nothing was read | Red `EMP` |

`Success` and `SameNoChange` are the **good** readings. [Template fields](boxes.md#template-fields) follow the same rules: `Success` when their text changes, `SameNoChange` when it doesn't, and `Empty` until every box they use has had a good reading.

Each output treats states differently:

| Output | What is sent |
|---|---|
| Text files | The latest good value of each box. A file is rewritten when its content changes (or the file is missing), at most **Save / s** times per second |
| HTTP server | Always the latest reading of every box, including its state. The `?pivot` endpoints include only good values |
| OBS | A box's good value whenever it differs from the text last sent to its OBS text source. Sent right away, not limited by **Save / s**, and no output folder needed |
| vMix, UNO | New values (`Success`). With **Send Same?**, unchanged values (`SameNoChange`) are resent too. Fields with an empty mapping are skipped |
| Outbound HTTP API | *JSON (Full)*, *XML* and *CSV*: every reading of every box on every cycle, so the receiver should check the state. *JSON (Simple key-value)* and `GET`: only the good readings |

## Global controls that affect outputs

- **Stop Updates** freezes all outputs at their current values until you click **Resume Updates**. The field list in ScoreSight keeps updating, so you can watch the readings without sending them.
- **Update on change** (on by default) marks unchanged values as `SameNoChange` so that most outputs don't resend them.
- **Detections / s** sets how often new readings are produced (see [Performance Tuning](performance.md)).
- **Save / s** (in the **Text Files** tab) limits only how often the files are written. It doesn't slow down the other outputs.

## Network outputs run in the background

OBS, vMix, UNO and the outbound API send from background workers, never from the ScoreSight window itself:

- Every HTTP request has a timeout (2 seconds to connect, 2 seconds to answer). OBS has a 3-second timeout.
- If a target falls behind, only the most recent value of each field is kept, so old values never pile up.
- If a target can't be reached, ScoreSight retries with an increasing delay and sends the latest values when it is back. The OBS connection is re-established automatically.
- Any 2xx HTTP status counts as success.
- Errors are logged at most once every 30 seconds per output, with the number of errors that were not logged, and recovery is logged once, for example `vMix: connection restored`.

{: .new }
In ScoreSight 0.1.x, a slow or unreachable target could freeze the ScoreSight window, and OBS updates only ran when an output folder was set. Both are fixed in 0.2.0.
