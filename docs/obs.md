---
title: OBS Studio
parent: Outputs
nav_order: 3
description: "Update OBS text sources from ScoreSight over the OBS WebSocket, or use browser and file-based alternatives."
---

# OBS Studio
{: .no_toc }

ScoreSight can update text sources in OBS Studio directly over the OBS WebSocket (protocol v5, built into OBS 28 and newer).

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Three ways to get scores into OBS

| Method | How | Pros |
|---|---|---|
| **WebSocket** (this page) | ScoreSight sets the text of OBS text sources | Native OBS text, no files, works across computers |
| **Browser Source** | An HTML overlay polls the [HTTP server](http_server.md) | Full design freedom (HTML/CSS), any field name including custom fields |
| **Text from file** | OBS text sources read the [text files](text-files.md) | Simple, works with every OBS version |

## 1. Enable the WebSocket server in OBS

1. In OBS, open **Tools** > **WebSocket Server Settings**.
2. Tick **Enable WebSocket server**. The default port is **4455**.
3. Tick **Enable Authentication** and set a password (recommended), or click **Show Connect Info** to see the generated one.
4. Click **OK**.

## 2. Connect ScoreSight

1. In ScoreSight, open the **OBS** tab and click **Connect OBS**.
2. Enter the OBS computer's address (`localhost` if OBS runs on the same computer), port `4455`, and the password.
3. Click **Connect**. If the connection works within 3 seconds, the dialog closes and the scene controls in the tab become available. If not, it shows "Cannot connect to OBS".

ScoreSight remembers the connection and connects again in the background the next time it starts, so the window appears right away even if OBS isn't running yet.

If OBS restarts or the connection drops while ScoreSight is running, ScoreSight reconnects by itself as soon as OBS is reachable again (the log shows `OBS: reconnected to <host>:<port>`). The latest value of each text source is sent after the reconnect.

## 3. Create the text sources

ScoreSight updates OBS text sources whose names exactly match the standard fields:

| ScoreSight field | OBS text source name |
|---|---|
| Home Score | `Home score` |
| Away Score | `Away score` |
| Time | `Clock` |
| Period | `Period` |
| Home Fouls | `#Home Fouls` |
| Away Fouls | `#Away Fouls` |
| Shot Clock | `shotclock` |

You have two options:

- **Use the ready-made scene**: type a scene name (default *ScoreSight Scene*) and click **Create OBS Scene**. ScoreSight builds a complete scoreboard graphic in OBS, with the text sources above plus team names, logos and backgrounds you can restyle. If a scene with that name already exists, its contents are removed and rebuilt.
- **Use your own design**: create *Text (GDI+)* or *Text (FreeType 2)* sources with the names in the table, anywhere in your scenes. Names are case-sensitive.

Once connected, every change of a field's value updates its OBS text source.

{: .new }
In ScoreSight 0.1.x, OBS updates only ran when an output folder was set in the **Text Files** tab, and a slow OBS connection could freeze ScoreSight. In 0.2.0, OBS updates are independent of the file output, are sent in the background, and survive an OBS restart.

## What gets sent

- A box's **good** reading (green or light green) is sent when it differs from the text ScoreSight last sent to that OBS source. Rejected (yellow) and empty readings never change the OBS text, so it keeps the last good value.
- Updates are sent as soon as the value changes, in the background. They are **not** limited by the **Save / s** setting of the Text Files tab, and they don't need an output folder.
- If OBS is slow, only the latest text of each source is kept and sent.
- Boxes without an OBS source name are skipped (see [Custom fields](#custom-fields)).
- **Stop Updates** freezes the OBS text.

## Custom fields

Custom fields have no OBS source name by default, so they don't update OBS. Your options:

- Use a **Browser Source** with the [HTTP server](http_server.md) (recommended). It can show any field.
- Use a text source that **reads from file** with the field's `.txt` file ([Text Files](text-files.md)).
- Advanced: **File > Export Configuration**, set `"obs_source_name": "My OBS Source"` in that box's `settings` in the exported `.json`, then **File > Import Configuration**. The custom field now updates the OBS text source with that name.

## Troubleshooting

OBS messages in the log start with `OBS:`.

| Problem | Check |
|---|---|
| "Cannot connect to OBS" | OBS is running, the WebSocket server is enabled, the port and password match, and the firewall on the OBS computer allows the port |
| Connected, but text doesn't change | The OBS source names match the table exactly (including case, spaces and `#`). The reading is green in ScoreSight. **Stop Updates** is off |
| Log shows `OBS: OBSSDKRequestError: Request SetInputSettings returned code 600...` | OBS has no input with that name (code 600 means "resource not found"). Check the source names |
| Updates stop after a while | While OBS can't be reached, the log shows `OBS: OBSConnectionLost: ...` (at most every 30 seconds). ScoreSight reconnects by itself when OBS is back. If it doesn't, click **Connect OBS** again |
| One field never updates | It is a custom field (see [Custom fields](#custom-fields)) |

{: .note }
ScoreSight 0.2.0 no longer writes the OBS WebSocket password to its log files.
