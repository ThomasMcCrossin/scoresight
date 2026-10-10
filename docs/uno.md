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

2. In ScoreSight, open the **UNO** tab and paste the URL into **URL**.
3. Check the **mapping table**: for each ScoreSight field, the right column holds the UNO command (or, in Essentials mode, the field ID) it should drive.
4. Click **▶️** to start sending. The button turns into **🛑**; click it again to stop.

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
- Requests are sent in the background with a timeout. If UNO is slow or unreachable, ScoreSight keeps only the latest values.
- overlays.uno limits how many API calls an account can make. Keep **Send Same?** off and **Update on change** on to stay well within the limits. The **Rate Limit** field in the tab is informational in this version and doesn't throttle requests.

## Troubleshooting

- Open the log (**File > View Current Log**) and look for "Failed to send data to UNO API". The status code is a clue: `401` or `403` usually means a wrong or expired URL, and `429` means too many requests.
- Make sure the overlay supports the command you mapped, and that the values have the format the overlay expects (for example `mm:ss` for match time). Use the box's [Format](box-settings.md#format) setting to enforce it.
