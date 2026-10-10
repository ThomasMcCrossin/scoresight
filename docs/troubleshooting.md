---
title: Troubleshooting
nav_order: 6
description: "Fixes for common ScoreSight problems: RTSP streams, macOS freezes and quit hangs, vMix and OBS not updating, bad recognition, low performance, missing files and more."
---

# Troubleshooting
{: .no_toc }

Each section describes a symptom, its usual causes and the fix. The issue numbers link to the original GitHub reports. If your problem isn't covered, see the [FAQ](faq.md) or [open an issue](https://github.com/royshil/scoresight/issues/new/choose) and attach your logs.

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Collect logs first

The log almost always shows what went wrong.

1. Open **File** > **View Current Log** to watch the log live. Its **Open Log Folder** button opens the folder with all log files.
2. Or open the folder directly:

   | OS | Log folder |
   |---|---|
   | Windows | `%LOCALAPPDATA%\scoresight\scoresight\Logs` |
   | macOS | `~/Library/Logs/scoresight` |
   | Linux | `~/.local/state/scoresight/log` |

3. Each session writes `scoresight_<date>_<time>.log` and `scoresight_std_<date>_<time>.log`. Attach **both** files from the session with the problem to your issue.

{: .warning }
Logs can contain host names, URLs and, depending on the version, connection details such as the OBS WebSocket password. Look through them and remove secrets before posting them publicly.

For even more detail, start ScoreSight with the environment variable `SCORESIGHT_DEBUG=1` (see [Environment variables](configuration.md#environment-variables)).

## Source problems

### RTSP or URL stream won't open (#10)

**Symptoms**: "Error: Unable to play video stream", a black picture, or (in old versions) `VIDEOIO(DSHOW): backend is generally available but can't be used to capture by name` in the log ([#10](https://github.com/royshil/scoresight/issues/10)).

**Fix**:

1. Make sure you run a current version. Versions before 0.0.12 tried to open URLs with DirectShow on Windows, which can never work.
2. Test the exact URL in VLC (**Media** > **Open Network Stream**). If VLC can't play it, fix the URL, the credentials or the network first.
3. Include user, password, port and path: `rtsp://user:password@192.168.1.50:554/stream1`. URL-encode special characters in the password.
4. Force **RTSP over TCP**: set `OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp` before starting ScoreSight (see [RTSP over TCP](sources.md#rtsp-over-tcp)). This fixes most streams that work in VLC but not in ScoreSight, especially across VPNs, Wi-Fi or NAT.
5. Try the camera's sub stream (lower resolution).
6. Fallback: open the stream in OBS and send it to ScoreSight with NDI or OBS's Virtual Camera.

### Camera not listed or black picture

- Click **Reload** after plugging in a camera.
- Close other apps that use the camera (OBS, Zoom, Teams, the camera vendor's software). Most cameras serve only one app at a time.
- **macOS**: allow **Camera** access in System Settings > Privacy & Security > Camera.
- **Linux**: add your user to the `video` group and log in again.
- Open **Video Settings** and try another **Capture Backend** or **Video Format** (`MJPG` vs `YUY2`).
- Capture cards: make sure the input signal is present (a resolution and frame rate the card supports), and try it in the vendor's own software.

### NDI source not listed

- Click **Reload**. Sources that start after ScoreSight appear only after a reload.
- Make sure both computers are on the same network and subnet, and that the firewall allows NDI.
- **macOS**: allow **Local Network** access for ScoreSight in System Settings > Privacy & Security.

### Screen capture shows nothing

- **macOS**: allow **Screen Recording** (System Settings > Privacy & Security > Screen & System Audio Recording), then **quit and restart** ScoreSight.
- **Linux**: screen capture isn't supported. Use OBS with NDI or the virtual camera.
- Minimized windows can't be captured. Keep the window visible and at a fixed size.

## macOS: slow start, freezes, or hang when quitting (#33, #7)

**Symptoms**: in ScoreSight 0.1.x and older on macOS, the app took up to a minute to appear ([#33](https://github.com/royshil/scoresight/issues/33)), the window froze ("beach ball") for long periods, or it showed "Not Responding" when quitting and had to be force-quit ([#7](https://github.com/royshil/scoresight/issues/7)).

**Causes and fixes in 0.2.0**:

- The quit hang came from the built-in HTTP server, which didn't shut down cleanly on macOS. ScoreSight 0.2.0 stops it internally, so quitting is immediate.
- Freezes during use came from network outputs (OBS, vMix, UNO) waiting for slow or unreachable targets on the main thread. In 0.2.0, all outputs run in the background with timeouts.

**If you still see it**:

- Update to the latest release.
- Turn off outputs whose target is offline (stop vMix/UNO, disconnect OBS).
- Collect the logs and, for hangs, a sample from **Activity Monitor** (select ScoreSight > the "..." menu > **Sample Process**), and [open an issue](https://github.com/royshil/scoresight/issues/new/choose).

Force-quitting doesn't damage your settings: they are saved as you work.

## Output problems

### vMix shows no data (#55, #25)

**Symptom**: vMix titles don't change. The log shows `Failed to send data to http://localhost:8099/api/... BadStatusLine('VERSION OK ...')` ([#55](https://github.com/royshil/scoresight/issues/55), [#25](https://github.com/royshil/scoresight/issues/25)).

**Cause**: port 8099 is vMix's TCP API. ScoreSight uses vMix's HTTP **Web API**, which listens on port **8088**.

**Fix**:

1. In vMix, enable **Settings** > **Web Controller** (port 8088).
2. In ScoreSight's **VMix** tab, set the port to **8088**. ScoreSight 0.2.0 does this automatically if you had 8099 saved.
3. Use the exact field names from the vMix Title Editor, **including `.Text`** (for example `Home Score.Text`).
4. Check the **Input** number, and click **Start**.

Full guide: [vMix](vmix.md).

### OBS text doesn't update (#30)

- In ScoreSight 0.1.x, OBS updates only worked when an output folder was set in the **Text Files** tab. 0.2.0 removed that requirement. Update, or set a folder as a workaround.
- The OBS text sources must be named exactly `Home score`, `Away score`, `Clock`, `Period`, `#Home Fouls`, `#Away Fouls` or `shotclock`, or use **Create OBS Scene**. Custom fields don't update OBS by default (see [OBS: Custom fields](obs.md#custom-fields)).
- If updates stop after a few minutes ([#30](https://github.com/royshil/scoresight/issues/30)), check whether OBS restarted or the WebSocket dropped (the log shows "unable to update text source"). Reconnect with **Connect OBS**. A [Browser Source](http_server.md) overlay is a robust alternative.
- On macOS, keep ScoreSight visible on screen or prevent your Mac from sleeping during a stream. macOS can slow down apps that are completely hidden.

### Text files are not written (#6)

**Symptom**: `results.csv` and `results.xml` appear, but no `<Box Name>.txt` files ([#6](https://github.com/royshil/scoresight/issues/6)).

**Cause (0.1.x)**: `.txt` files were written only at the exact moment a value changed. If that moment fell between two file saves, the file wasn't written until the next change.

**Fix**: ScoreSight 0.2.0 writes each file whenever its value differs from what's on disk, or when the file is missing. If files are still missing:

- Check that an output folder is set and still exists (ScoreSight forgets a folder that was deleted).
- Check that the box's reading is green or light green. Rejected (yellow) and empty readings aren't written.
- Look for "Error writing to file" in the log (permissions, a full disk, or a folder synced by OneDrive/Dropbox).

### CSV doesn't update in real time (#29)

In ScoreSight 0.2.0, `results.csv` is updated atomically with the current values (header once, values properly quoted). For a live data file, use **Don't append results**. For a game log, use **Results in .csv file**. See [Text, CSV & XML Files](text-files.md) and [#29](https://github.com/royshil/scoresight/issues/29).

### HTTP server not reachable

- **Port 18099 is already in use**: another ScoreSight instance (or another program) uses the port. Close it, or start this instance with `--port 18100` (see [profiles](profiles.md)).
- From another computer: use the ScoreSight computer's IP address and allow ScoreSight through its firewall.

## Recognition problems

### Wrong or unstable readings (#30)

Readings come from the picture, so start there ([#30](https://github.com/royshil/scoresight/issues/30) is a good example of a low-contrast stadium board):

1. Look at the box in **Binary View**. Digits must be solid and clearly separated from the background.
2. Crop to the scoreboard and use **4-corner Correction** for angled cameras.
3. Set **Binarize** to **Local** or **Adaptive** for low-contrast boards or dark surroundings.
4. Set the **Type** and a strict **Format** so impossible values are rejected.
5. Use **Remove leading 0s** for zero-padded scores, and consider one box per digit for very poor boards.
6. Try another **OCR Model**.

The full method is in [Recognition Tuning](recognition-tuning.md).

### Readings are yellow even though they look right

The reading failed the box's **Format** (the raw text didn't fully match) or the **Conf. Th** confidence threshold. Check the format (for example *Shotclock 0-39* needs two digits) and lower the threshold a little. `SIM` means **Skip Similar Image** skipped an unchanged image, which is normal.

## Performance problems

### Low Frames/s, Updates/s or Previews/s (#20)

([#20](https://github.com/royshil/scoresight/issues/20))

- **Previews/s ≈ 1 is by design**: the preview refreshes once per second to save CPU. It doesn't affect readings.
- **Updates/s** follows the **Detections / s** slider (default 5, maximum 15). Raise the slider if you need more.
- **Frames/s** is capped at about 33. Lower values mean the source delivers fewer frames or the CPU is busy with OCR. Reduce the number of boxes, crop the picture, enable **Skip Similar Image**, and lower the camera resolution.

See [Performance Tuning](performance.md).

### Video freezes when Detections / s is at 1 (#53)

In ScoreSight 0.1.x, setting **Detections / s** to 1 stopped all processing, and the UI could stay disabled after a restart ([#53](https://github.com/royshil/scoresight/issues/53)). This is fixed in 0.2.0. On older versions, set the slider to 2 or higher.

### The window is slow or freezes when a vMix/UNO/API target is offline

Fixed in 0.2.0: outputs send in the background with timeouts. On older versions, stop vMix/UNO and disable the API output when the target is offline.

## Other problems

### OCR training data goes to the wrong folder (#52)

In 0.1.x, a changed **Save Folder** in **OCR Training Data Setup** was ignored ([#52](https://github.com/royshil/scoresight/issues/52)). This is fixed in 0.2.0: the chosen folder is used. See [OCR Training Data](data_annotation.md).

### The interface is too light or hard to read (#50)

Use **File** > **Appearance** to choose **Dark**, **Light** or **System** (follow the operating system) ([#50](https://github.com/royshil/scoresight/issues/50)).

### The File menu disappeared

In ScoreSight 0.1.x on Windows and Linux, the menu bar could disappear after the window lost focus. Restart ScoreSight to get it back, and update to the latest version.

### Two cameras at once (#8)

Run two instances with different profiles and ports, for example `--profile shotclock --port 18100`. See [Multiple Instances & Profiles](profiles.md) and [#8](https://github.com/royshil/scoresight/issues/8).

### Antivirus or SmartScreen warnings (Windows)

The Windows installer isn't code-signed yet, and unsigned PyInstaller apps are sometimes flagged as false positives. Download only from the [Releases page](https://github.com/royshil/scoresight/releases/latest) and [verify the checksum](INSTALL.md#verify-your-download-recommended). Then allow that specific file (don't disable your antivirus), and report the false positive to your antivirus vendor. See [Installation](INSTALL.md#if-your-browser-or-antivirus-blocks-the-download).

### Linux: "Could not load the Qt platform plugin xcb"

Install the X11/xcb runtime libraries, for example on Debian/Ubuntu `sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libegl1`.

### Start over with clean settings

1. Quit ScoreSight.
2. Optionally use **File > Export Configuration** first to keep your boxes.
3. Rename or delete the [settings folder](configuration.md#where-scoresight-keeps-its-files) (or only `scoresight.json`).
4. Start ScoreSight. It starts with defaults.

### Still stuck?

[Open an issue](https://github.com/royshil/scoresight/issues/new/choose). The bug report form asks for your version, OS, source type, outputs and logs, which is everything needed to help you.
