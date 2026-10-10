---
title: Settings, Files & Command Line
parent: Reference
nav_order: 2
description: "Where ScoreSight stores settings and logs, command-line options, environment variables and the keys in scoresight.json."
---

# Settings, Files & Command Line
{: .no_toc }

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Where ScoreSight keeps its files

| | Windows | macOS | Linux |
|---|---|---|---|
| Settings folder | `%LOCALAPPDATA%\scoresight\scoresight` | `~/Library/Application Support/scoresight` | `~/.local/share/scoresight` |
| Log folder | `%LOCALAPPDATA%\scoresight\scoresight\Logs` | `~/Library/Logs/scoresight` | `~/.local/state/scoresight/log` |

On Windows, `%LOCALAPPDATA%` is usually `C:\Users\<you>\AppData\Local`. Paste the path into the File Explorer address bar to open it.

The settings folder contains:

| File / folder | Content |
|---|---|
| `scoresight.json` | All settings of the default profile: source, boxes, view tools and outputs |
| `scoresight-<profile>.json` | The settings of a named [profile](profiles.md) |
| `scoresight.json.corrupt-<timestamp>` | A backup ScoreSight made of a settings file it could not read (see below) |
| `ocr_training_data/` | The default folder for [OCR training data](data_annotation.md) |

**File > Open Configuration Folder** opens the settings folder. **File > View Current Log** shows the live log. Its **Open Log Folder** button opens the log folder, and **Open on startup** shows the log window every time ScoreSight starts.

Both folders can be moved with [environment variables](#environment-variables).

### Settings are saved automatically

ScoreSight saves changes as you make them. Settings files are written atomically (to a temporary file that then replaces the old one), so a crash or power loss can't leave a half-written file.

If a settings file is damaged anyway, for example by a full disk or manual editing, ScoreSight doesn't wipe your settings silently. It renames the damaged file to `<name>.corrupt-<timestamp>`, logs a warning and starts with defaults. You can open the backup in a text editor to recover your boxes, for example by copying the `boxes` list into an exported configuration file and importing it.

### Logs

Each run creates two log files: `scoresight_<date>_<time>.log` (ScoreSight's own log) and `scoresight_std_<date>_<time>.log` (messages from libraries). ScoreSight keeps the most recent logs and deletes older ones automatically. Attach both files from the session that had the problem when you [report a bug](troubleshooting.md#collect-logs-first).

## Command-line options

| Option | Description |
|---|---|
| `--profile NAME` | Use the settings file `scoresight-NAME.json` instead of `scoresight.json`. See [Multiple Instances & Profiles](profiles.md). |
| `--port N` | Run the [HTTP server](http_server.md) on port `N` (default `18099`). |
| `--self-test` | Run a quick self-check without opening a window: load all modules and every bundled OCR model, and read a test image. Prints `SELF-TEST OK` and exits with code 0 on success, or exits with a non-zero code. Useful to check an installation or a build. |

Examples:

```powershell
# Windows
& "C:\Program Files\ScoreSight\scoresight.exe" --profile court2 --port 18100
```

```bash
# macOS (start an additional instance with options)
open -n -a ScoreSight --args --profile court2 --port 18100

# Linux, or running from source
./scoresight/scoresight --profile court2 --port 18100
python src/main.py --self-test
```

## Environment variables

| Variable | Effect |
|---|---|
| `SCORESIGHT_PROFILE` | Same as `--profile`: use `scoresight-<value>.json`. |
| `SCORESIGHT_DATA_DIR` | Use this folder instead of the default settings folder. |
| `SCORESIGHT_LOG_DIR` | Write logs to this folder instead of the default log folder. |
| `SCORESIGHT_DEBUG` | If set (to any value), also print the log to the console and enable more detailed server logging. |
| `OPENCV_FFMPEG_CAPTURE_OPTIONS` | Options for OpenCV's FFmpeg backend. Set it to `rtsp_transport;tcp` to force [RTSP over TCP](sources.md#rtsp-over-tcp). |
| `QT_QPA_PLATFORM` | Qt platform plugin. `offscreen` runs without a display, for example for `--self-test` on a server. |

When running from source, ScoreSight also reads a `.env` file in the repository root, which is handy for `SCORESIGHT_DEBUG=1`.

{: .tip }
`SCORESIGHT_DATA_DIR` makes a portable setup possible: keep ScoreSight's settings on a USB stick or a shared drive that you take from venue to venue.

## Import and export

**File > Export Configuration** writes the current boxes (names, positions, settings) to a `.json` file, and **File > Import Configuration** loads them. Other settings (source, crop, 4-corner correction, outputs) are not included. To keep complete, separate setups, use [profiles](profiles.md) or copy the profile's settings file.

## Settings keys in `scoresight.json`

You normally never edit this file: everything is set through the UI. This list helps when reading a file someone sent you, or when troubleshooting. Close ScoreSight before editing the file by hand.

### Source and view

| Key | Meaning |
|---|---|
| `source_selected` | The last source (camera name, file path, URL or window) |
| `four_corners` | The four corner points of the perspective correction |
| `crop_mode`, `left_crop`, `top_crop`, `right_crop`, `bottom_crop` | Crop on/off and crop amounts in pixels |
| `rotation` | `0`, `90`, `180` or `270` |
| `box_display_style` | `0` No Box, `1` Outline, `2` Names, `3` All |
| `fps`, `width`, `height`, `fourcc`, `backend` | Camera [Video Settings](sources.md#cameras-and-capture-cards) |

### Recognition

| Key | Meaning |
|---|---|
| `boxes` | The list of boxes: `name`, `rect` (`x`, `y`, `width`, `height`), `settings` (see [Per-Box Settings](box-settings.md)) and `mini_rects` |
| `custom_boxes_names` | Names of your custom fields |
| `ocr_model` | `0` Daktronics, `1` General Scoreboard, `2` General Fonts (English), `3` General Scoreboard Large, or the path of an external `.traineddata` file |
| `detection_cadence` | Detections / s (1–15) |
| `update_on_change` | Update on change on/off |

### Outputs

| Key | Meaning |
|---|---|
| `output_folder`, `save_csv`, `save_xml`, `append_method`, `aggs_per_second` | [Text Files](text-files.md) tab (`append_method`: `0` CSV, `1` TXT, `2` both, `3` don't append; `aggs_per_second`: Save / s) |
| `obs` | OBS connection: `ip`, `port`, `password` |
| `vmix_host`, `vmix_port`, `vmix_input`, `vmix_mapping`, `vmix_send_same` | [vMix](vmix.md) tab |
| `uno_url`, `uno_mapping`, `uno_send_same`, `uno_essentials`, `uno_essentials_id` | [UNO](uno.md) tab |
| `enable_out_api`, `out_api_url`, `out_api_method`, `out_api_encoding` | [API](out_api.md) tab |

### Application

| Key | Meaning |
|---|---|
| `color_scheme` | **File > Appearance**: System, Light or Dark |
| `open_on_startup` | Show the log window at startup |
| `save_ocr_training_data`, `ocr_training_data_folder`, `ocr_training_data_max_size` | [OCR training data](data_annotation.md) collection |

{: .warning }
`scoresight.json` stores the OBS WebSocket password and the UNO and API URLs (which may contain access tokens) in plain text. Don't share the file publicly. Exported configurations contain only boxes, but check them before sharing anyway.
