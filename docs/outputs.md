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
| `SameNoChange` | Same value as the previous reading (only when **Update on change** is on) | Light green |
| `FailedFilter` | Something was read but it failed the box's Format or confidence check, or was skipped as `SIM` | Yellow |
| `Empty` | Nothing was read | Red `EMP` |

Each output treats states differently:

| Output | What is sent |
|---|---|
| Text files | The latest good value of each box. A file is rewritten when the value changes (or the file is missing) |
| HTTP server | Always the latest reading of every box, including its state. `?pivot` endpoints include only good values |
| OBS | New values (`Success`) |
| vMix, UNO | New values. With **Send Same?**, unchanged values are resent too |
| Outbound HTTP API | Every reading of every box on every cycle, so the receiver should check the state |

## Global controls that affect outputs

- **Stop Updates** freezes all outputs at their current values until you click **Resume Updates**. The field list in ScoreSight keeps updating, so you can watch the readings without sending them.
- **Update on change** (on by default) marks unchanged values as `SameNoChange` so that most outputs don't resend them.
- **Detections / s** sets how often new readings are produced (see [Performance Tuning](performance.md)).
- **Skip Empty Values** (a per-box setting, on by default) prevents empty readings from overwriting text files and OBS text sources.

{: .new }
In ScoreSight 0.2.0, OBS, vMix, UNO and the outbound API send from background workers with network timeouts. A slow or unreachable target no longer freezes the ScoreSight window, and if a target falls behind, only the most recent values are sent. OBS updates also no longer require an output folder to be set.
