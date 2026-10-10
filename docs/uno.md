---
title: Overlays.uno (UNO)
parent: Outputs
nav_order: 5
description: "Drive overlays.uno control apps from ScoreSight, including the Essentials content-field API."
---

# Overlays.uno (UNO)
{: .no_toc }

ScoreSight can update [overlays.uno](https://overlays.uno/) graphics directly through the UNO control app API.

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Setup

1. In overlays.uno, open your overlay's control app and copy its **API URL**. It looks like:

   ```
   https://app.overlays.uno/apiv2/controlapps/<token>/api
   ```

   Treat this URL like a password: anyone who has it can control your overlay.

2. In ScoreSight, select **UNO** in the **Outputs** list (or click **UNO** in the status bar) and paste the URL into **URL**. The URL takes effect when you press **Enter** or leave the field (spaces around it are ignored). Changing it while sending keeps the mapping and the running state.
3. Check the **mapping table**: for each ScoreSight field, the right column holds the UNO command (or, in Essentials mode, the field ID) it should drive.
4. Click **Start sending** (or the switch of the UNO row). The button changes to **Stop sending**; click it again to stop.

The UNO row of the **Outputs** list shows whether the values arrive: ● *Sending to app.overlays.uno* with the time of the last update, ◐ while it waits for a value that changed, ▲ *Can't reach app.overlays.uno · retrying* when there's no connection, and ■ with the HTTP error overlays.uno answered (see [Troubleshooting](#troubleshooting)). It never shows the token in your URL.

## Mapping

By default, the standard fields map to these UNO scoreboard commands:

| ScoreSight field | UNO command |
|---|---|
| Time | `SetMatchTime` |
| Home Score | `SetGoalsHome` |
| Away Score | `SetGoalsAway` |
| Period | `SetPeriod` |
| any other field | the field's own name. Change it to a command your overlay supports |

The available commands depend on the overlay. See the API documentation of your overlay's control app in overlays.uno. Edit the right-hand column to change a mapping. Mappings are saved automatically.

## Essentials mode

For overlays that use UNO's content fields ("Essentials"), tick **Essentials** and enter the **Overlay ID** (the UUID of the overlay). In this mode, the mapping column holds the **field ID** of each content field, and ScoreSight sends `SetOverlayContentField` commands.

## What ScoreSight sends

One `PUT` request with a JSON body to the API URL for each field with a new value:

Standard mode:
```json
{"command": "SetGoalsHome", "value": "65"}
```

Essentials mode:
```json
{"command": "SetOverlayContentField", "id": "<Overlay ID>", "fieldId": "<mapping>", "value": "65"}
```

- Only **new** values are sent. Tick **Send Same?** to also resend unchanged values on every cycle.
- Fields whose mapping cell is empty are not sent.
- Requests are sent in the background with a 2-second timeout. If UNO is slow or unreachable, ScoreSight keeps only the latest value of each command, retries with an increasing delay, and sends the latest values when UNO responds again. Any 2xx response counts as success.
- overlays.uno limits how many API calls an account can make. Keep **Send Same?** off and **Update on change** on to stay well within the limits. ScoreSight doesn't throttle UNO requests itself.

{: .new }
ScoreSight 0.2.0 removed the **Rate Limit** field of 0.1.x, which had no effect.

## Troubleshooting

- Look at the UNO row of the **Outputs** list. It says, for example:
  - ■ *HTTP 401: check the UNO URL* (or 403, 404): the URL is wrong or expired. Copy the API URL of your control app again.
  - ▲ *HTTP 429: too many requests*: overlays.uno's limit; the updates over it are dropped. Keep **Send Same?** off and **Update on change** on.
  - ▲ *Enter your UNO API URL*: the URL field still holds the example URL.
  - ▲ *Can't reach app.overlays.uno · retrying*: no internet connection. ScoreSight sends the latest values when it's back.
- The log (**File > View Current Log**) has the details in lines that start with `UNO:`, for example `UNO: OutputError: UNO SetGoalsHome returned HTTP 401: ...`. Errors are logged at most once every 30 seconds.
- Make sure the overlay supports the command you mapped, and that the values have the format the overlay expects (for example `mm:ss` for match time). Use the box's [Format](box-settings.md#format) setting to enforce it.
