---
title: Video Sources
parent: Guides
nav_order: 1
description: "Connect USB cameras, capture cards, NDI, RTSP/HTTP streams, screen capture and video files to ScoreSight."
---

# Video Sources
{: .no_toc }

ScoreSight reads one video source per window. Choose it from the **Source** drop-down at the top of the main window. To read two different sources at the same time, run two instances (see [Multiple Instances & Profiles](profiles.md)).

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Supported sources

| Source | Windows | macOS | Linux | Notes |
|---|:---:|:---:|:---:|---|
| USB camera / capture card (UVC, HDMI/SDI capture) | ✔ | ✔ | ✔ | DirectShow on Windows, AVFoundation on macOS, `/dev/video*` on Linux |
| NDI® | ✔ | ✔ | ✔ | Sources on your network are discovered automatically |
| URL: RTSP / HTTP stream | ✔ | ✔ | ✔ | IP cameras, MediaMTX, encoders, HLS/HTTP streams that FFmpeg can open |
| Screen Capture (window or whole screen) | ✔ | ✔ | ✘ | macOS needs the Screen Recording permission |
| Video file (`.mp4`, `.avi`, `.mov`) | ✔ | ✔ | ✔ | Loops automatically; playback speed x1 to x32 |

ScoreSight remembers the last source and reopens it at the next start.

## Cameras and capture cards

Cameras and capture cards appear in the **Source** list by name (on Linux as *Camera 0*, *Camera 1*, ...). If you plugged one in after starting ScoreSight, click **Reload**.

**Video Settings** (enabled only for camera sources) lets you request a specific format from the device:

| Setting | Use it to |
|---|---|
| **FPS** | Request a frame rate. |
| **Resolution** | Request a resolution. 1280x720 or 1920x1080 is plenty for most scoreboards. |
| **Video Format** (FOURCC) | Choose the pixel format, for example `MJPG` (compressed, allows higher frame rates over USB) or `YUY2`/`YUYV` (uncompressed). Only formats the device accepts are listed. |
| **Capture Backend** | Choose the capture API: *Auto*, plus *DShow*, *Microsoft Media Foundation* or *Microsoft Windows Runtime* on Windows, *V4L* or *GStreamer* on Linux, and *AVFoundation* on macOS. |

These settings apply to camera sources and are remembered for the next start. The dialog also lists all the properties the device reports, which is handy for troubleshooting.

{: .tip }
Most USB cameras can be used by only one application at a time. Close OBS, Zoom, Teams or any other app that is using the camera, or share the feed through NDI or OBS's Virtual Camera instead.

On macOS, ScoreSight needs the **Camera** permission. On Linux, your user needs access to `/dev/video*` (usually via the `video` group). See [Installation](INSTALL.md).

## NDI

NDI sources on your local network are listed automatically. Discovery takes about a second when the source list is built, so click **Reload** if a source started after ScoreSight. ScoreSight receives the highest-bandwidth stream and signals a *program* (on-air) tally to the sender.

If NDI sources don't appear:

- Make sure the sender and ScoreSight are on the same network and subnet, and that the firewall allows NDI (mDNS on UDP 5353 plus the NDI ports).
- On macOS, allow the **Local Network** permission for ScoreSight.
- Test the source in NDI Studio Monitor or OBS first.

## URL sources (RTSP and HTTP)

Choose **URL Source (HTTP, RTSP)** and enter the stream address, for example:

```
rtsp://user:password@192.168.1.50:554/stream1
rtsp://10.0.1.200:554/11
http://192.168.1.60:8080/video
```

URL sources are opened with OpenCV's FFmpeg backend on every platform, so anything FFmpeg can play (RTSP, RTMP pulled over HTTP, HLS, MJPEG over HTTP) usually works.

### RTSP over TCP

By default FFmpeg tries RTSP over UDP. UDP is often blocked by firewalls, NAT, VPNs and Wi-Fi, which shows up as "Unable to play video stream", a grey or frozen picture, or heavy corruption. To force RTSP over **TCP**, set this environment variable before you start ScoreSight:

Windows (PowerShell, for this session):
```powershell
$env:OPENCV_FFMPEG_CAPTURE_OPTIONS = "rtsp_transport;tcp"
& "C:\Program Files\ScoreSight\scoresight.exe"
```

Windows (permanently, for your user): run `setx OPENCV_FFMPEG_CAPTURE_OPTIONS "rtsp_transport;tcp"` once, then start ScoreSight from the Start menu as usual.

macOS / Linux:
```bash
OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp" /path/to/scoresight
```

### Checklist for streams that won't open

1. Test the exact URL in VLC (**Media** > **Open Network Stream**) or with `ffprobe -rtsp_transport tcp "rtsp://..."`. If it doesn't play there, the URL, credentials or network are the problem.
2. Include the port and path, and URL-encode special characters in the password (for example `@` becomes `%40`).
3. Try RTSP over TCP (above).
4. Many cameras offer a lower-resolution "sub stream" (often `/stream2` or `/102`). A 720p sub stream is enough for most scoreboards and is easier on the network and CPU.
5. As a fallback, open the stream in OBS and send it to ScoreSight with NDI or OBS's Virtual Camera.

See also [Troubleshooting: RTSP stream won't open](troubleshooting.md#rtsp-or-url-stream-wont-open-10).

## Screen capture

Choose **Screen Capture** and pick a window from the list, or **Capture the entire screen**. This lets you read a score from a game, a web page, a scoreboard-controller app or a TV graphics preview.

- **Windows**: captures the selected window or the whole screen.
- **macOS**: requires the **Screen Recording** permission (System Settings > Privacy & Security > Screen & System Audio Recording). After granting it, quit and restart ScoreSight.
- **Linux**: not supported. Use OBS (with its screen capture) plus NDI or the virtual camera.

{: .tip }
Keep the captured window at a fixed size and position. Boxes are positioned in pixels, so resizing the window moves the content out from under them.

## Video files

Choose **Open a Video File** to load an `.mp4`, `.avi` or `.mov` file. The file loops when it reaches the end, which makes it ideal for tuning your boxes on a recording before the game.

The **Speed** button (x1, x2, x4, x8, x16, x32) skips frames to fast-forward through long recordings. Speed does not change how often boxes are read (that is **Detections / s**).

## Switching and reloading sources

- Selecting a different source closes the current one and opens the new one. Your boxes stay in place.
- **Reload** re-scans cameras and NDI sources.
- Rotation, crop and 4-corner correction are global settings, not per-source settings. If you switch to a source with a different framing, adjust them again.
