# Changelog

All notable changes to ScoreSight are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Release tags are the bare version number (for example `0.1.0`).

## [Unreleased]

ScoreSight is actively maintained again. This release modernizes the whole
stack, fixes the most reported problems, keeps the window responsive whatever
your outputs and sources do, and adds profiles for running several instances.

### Added

- Profiles for running several ScoreSight instances side by side, for example
  one per camera ([#8](https://github.com/royshil/scoresight/issues/8)):
  - `--profile NAME` (or the `SCORESIGHT_PROFILE` environment variable) uses
    the settings file `scoresight-NAME.json` instead of `scoresight.json`. The
    window title shows the active profile.
  - `--port N` serves the HTTP API on port `N` instead of 18099. The
    **Browser** tab shows the links for the port in use.
- `--self-test` command-line option: a headless check of the installation
  (all modules, the bundled files, the main window and every bundled OCR model
  reading a test image) that prints `SELF-TEST OK` and exits with code 0.
- Ctrl+C, `SIGTERM` and Ctrl+Break (Windows) quit ScoreSight cleanly, saving
  the boxes and stopping the HTTP server, even with a dialog open. This is how
  to stop an instance that runs without a window (`-platform offscreen`).
- **File > Appearance** with System, Light and Dark colour schemes,
  remembered between runs ([#50](https://github.com/royshil/scoresight/issues/50)).
- **File > Check for Updates** checks GitHub Releases and always shows the
  result. The check at startup shows a dialog only when a newer version
  exists, and can be turned off in that dialog.
- A `/csv?pivot` endpoint on the built-in HTTP server: a header row with the
  box names and one row with their current good values.
- `SCORESIGHT_DATA_DIR` and `SCORESIGHT_LOG_DIR` environment variables to move
  the settings and log folders.
- A damaged settings file is now backed up as `<name>.corrupt-<timestamp>`
  instead of being silently replaced by defaults.
- Release downloads for every platform, each with the version in its file
  name: a Windows installer and a portable zip, macOS disk images for Apple
  Silicon and Intel, and a Linux `.tar.gz`, plus `SHA256SUMS.txt` for verifying
  them.
- Every packaged build is tested with `--self-test` on Windows, macOS and
  Linux before it is released, and the Windows installer is test-installed.
- New documentation site at <https://royshil.github.io/scoresight/>:
  quickstart, installation (including the portable version, macOS permissions
  and Linux), video sources (including RTSP,
  [#10](https://github.com/royshil/scoresight/issues/10)), boxes and template
  fields, a per-box settings reference, recognition and performance tuning
  guides ([#20](https://github.com/royshil/scoresight/issues/20),
  [#30](https://github.com/royshil/scoresight/issues/30)), an HTTP API
  reference, file, OBS, vMix, UNO and outbound API guides, troubleshooting,
  FAQ and a developer guide.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, GitHub issue forms and
  a pull request template.
- For contributors: an automated test suite (pytest) and linting/formatting
  (ruff) in continuous integration, pre-commit hooks, Dependabot updates,
  `scripts/compile_ui.py` to compile the Qt Designer files on every platform,
  `scripts/update_translations.py` to refresh the translation sources from
  `src/` only, and `scripts/bump_version.py` to prepare a release.
- A status bar: the source with its resolution and frame rate, how many times
  per second the boxes are read against the **Detections / s** setting (orange
  when the computer can't keep up), **PAUSED** while the outputs are paused,
  and the HTTP server's address on your network with a **Copy** button.
- Keyboard shortcuts: **Ctrl+Shift+P** pauses and resumes the outputs,
  **Ctrl+B** toggles **Binary View**, **Ctrl+0** fits the picture to the
  window and **F5** reloads the sources (**⌘** on macOS). The buttons'
  tooltips show them.
- Every slider shows its value next to it (*Off* when the setting is off), and
  every control has a tooltip.

### Changed

- The vMix output now defaults to port **8088**, the vMix Web API (Web
  Controller), and sends `SetText` as an HTTP GET request. A previously saved
  port 8099 (the vMix TCP API, which ScoreSight never supported) is changed to
  8088 once, and the log explains when a port answers like the vMix TCP API
  ([#55](https://github.com/royshil/scoresight/issues/55)).
- OBS, vMix, UNO and the outbound HTTP API send from background threads with
  timeouts, keeping only the latest value of each field. A slow or unreachable
  target no longer freezes the ScoreSight window or builds up a backlog of old
  values ([#33](https://github.com/royshil/scoresight/issues/33)). Any 2xx
  response counts as success.
- Repeated output errors are logged at most once every 30 seconds per output,
  with a count of the errors that were not logged, and recovery is logged once.
- OBS text sources are updated as soon as a box's good value changes, even when
  no output folder is set and independently of **Save / s**
  ([#30](https://github.com/royshil/scoresight/issues/30)). The OBS connection
  is re-established automatically after OBS restarts or the connection drops,
  and boxes without an OBS source name are skipped.
- Video sources (including NDI discovery), the saved OBS connection and the
  update check are handled in the background, so the window appears
  immediately and no longer freezes
  ([#33](https://github.com/royshil/scoresight/issues/33)).
- ScoreSight remembers the type of the last source and reopens URL/RTSP
  streams, video files, cameras, NDI sources and screen capture at the next
  start ([#10](https://github.com/royshil/scoresight/issues/10)).
- The per-box confidence threshold (**Conf. Th**) is the minimum Tesseract
  confidence in percent and is off (0) by default. Boxes saved by an older
  version get a threshold of 0 once, because the setting had no effect before
  (see Fixed), so existing setups read exactly as before. The settings file
  records this as `"boxes_schema_version": 2`, and the log mentions it.
- Template fields use each box's last good reading, stay empty until every box
  they use has had a good reading, are reported as a new value only when their
  text changes, and can use other template fields.
- File outputs are state-based and atomic. Each file is written when its
  content changes or the file is missing, from the last good reading of each
  box, and replaced in one step so readers never see a partial file. Output is
  UTF-8, and characters that aren't allowed in file names are replaced with
  `_` ([#6](https://github.com/royshil/scoresight/issues/6),
  [#29](https://github.com/royshil/scoresight/issues/29)).
- In an append mode, `results.csv` gets a row when a value changes, and a new
  file is started (the old one is renamed `results-<timestamp>.csv`) when the
  set of boxes changes ([#29](https://github.com/royshil/scoresight/issues/29)).
  `results.xml` has a documented structure with one `<result>` element per box.
- Outbound HTTP API: *JSON (Simple key-value)* and *GET* send only good
  readings (Success or SameNoChange), and nothing is sent when there are none.
- **Average Output** votes on whole values over the last 5 accepted readings
  instead of character by character.
- **Skip Similar Image** compares the digits rather than the whole box, and a
  skipped box repeats its last good value as an unchanged reading instead of
  showing a yellow `SIM`.
- Saved **Video Settings** apply to camera sources only; their **Auto** backend
  means the platform default (DirectShow on Windows). **Capture Backend** lists
  only the backends ScoreSight's OpenCV includes, and a saved backend that
  can't open the camera falls back to the default one.
- ScoreSight remembers the language chosen in **File > Language**, and regional
  system locales (for example `de_AT` or `fr_CA`) now get the matching
  translation.
- In the Training Dojo, the next/back/remove-approval shortcuts are now
  Ctrl+N, Ctrl+B and Ctrl+U (⌘ on macOS), so N, B and U can be typed in
  annotations.
- On Linux, cameras are listed with their names and device nodes, for example
  `HD Webcam (/dev/video0)`.
- The window title shows the real version (and the profile), and the About
  dialog shows the version. The version number comes from a single place
  (`src/version.py`).
- The About and update dialogs link to the GitHub repository, the
  documentation site and GitHub Issues.
- The macOS app is now a regular app bundle that starts much faster, because
  it no longer unpacks itself on every launch
  ([#33](https://github.com/royshil/scoresight/issues/33)). It requires macOS 15
  or newer and is no longer slowed down by App Nap in the background.
- The Windows installer upgrades an existing ScoreSight installation in place,
  can install for all users or only the current user, and requires Windows 10
  version 1809 or newer.
- The Linux download is a compressed folder build (`scoresight/scoresight`)
  that needs glibc 2.35 or newer (Ubuntu 22.04+, Debian 12+). It includes
  `libxcb-cursor0` and the other xcb libraries Qt needs on X11.
- Updated to Python 3.13 with current dependencies: PySide6-Essentials 6.12
  (Qt 6.12), NumPy 2, OpenCV (headless), tesserocr 2.11 / Tesseract 5.5,
  cyndilib 0.1 (NDI), and current FastAPI, uvicorn and obsws-python.
- Settings are saved atomically and safely from any thread.
- ScoreSight can be started from source from any working directory
  (`python src/main.py`).
- For contributors: code style is enforced with ruff instead of black, the
  Windows camera enumerator builds with pybind11 from `requirements-build.txt`
  from any directory, and the PyInstaller spec builds every platform with the
  same command.
- The window fits small screens and long languages. The left column scrolls
  (with **Pause outputs** at its top and **Detections / s** at its bottom
  always in view), a divider between it and the picture can be dragged (its
  position is remembered), and the window opens at a size that fits the
  screen. Its minimum size is about 870×200 pixels in English and 960×200 in
  German (it was 1016×750 and 1158×750), so it fits a 1366×768 laptop.
- The boxes list shows the readings: each box's last good value in large type,
  a symbol and a word for the state of its latest reading (✓ new, = same,
  ! rejected, with the rejected text, ∅ no reading) and how long ago the last
  good reading was made, highlighted when it's old. A rejected or empty
  reading no longer greys out or hides the value, the list is tall enough for
  every standard box, and a click on a value selects its box.
- **Stop Updates** is now **Pause outputs** / **Resume outputs**, at the top
  of the left column. While the outputs are paused, the button is orange, a
  banner over the picture shows since when (with a **Resume outputs**
  button), the values in the boxes list are marked *not sent*, the window
  title starts with ⏸ and the status bar shows how long they have been paused.
- The **File** menu is translated, and **File > Language** lists each language
  in its own language (Deutsch, Français, 日本語, ...) with the current one
  ticked.
- **Connect to OBS** hides the password (with **Show password**), has a
  **Cancel** button and stays in front of the main window.
- The vMix and UNO start buttons show a text and an icon instead of emoji:
  **Start vMix** / **Stop vMix** and **Start sending** / **Stop sending**.
- Long camera names no longer make the window wider: the source list is kept
  narrow, and its drop-down shows the whole names.

### Fixed

- Setting **Detections / s** to 1 froze the video and could leave the controls
  disabled. The preview and the first reading now start on the first frame,
  and the preview refreshes about once a second at any detection rate
  ([#53](https://github.com/royshil/scoresight/issues/53),
  [#20](https://github.com/royshil/scoresight/issues/20)).
- The first readings after a source opened were lost. A value that never
  changed (for example a score after a restart) then didn't show in the boxes
  list, and vMix and UNO didn't receive it until it changed (unless **Send
  Same?** was on).
- A value that changed while the outputs were paused didn't reach vMix and UNO
  after resuming until it changed again (unless **Send Same?** was on). After
  resuming, they now get each box's next good value even if it is unchanged.
- Closing the **Connect to OBS** dialog without connecting left **Create OBS
  Scene** disabled, even with OBS connected.
- Saved **Video Settings** (capture backend, video format, resolution, frame
  rate) were not applied when a camera opened, and pressing **OK** in Video
  Settings reopened the camera and threw them away
  ([#20](https://github.com/royshil/scoresight/issues/20)).
- The Video Settings resolution list offered `1980x1080` instead of
  `1920x1080`.
- RTSP/HTTP stream sources could block for about 30 seconds when unreachable.
  They now open with FFmpeg and give up after 5 seconds, and spaces around the
  URL are ignored ([#10](https://github.com/royshil/scoresight/issues/10)).
- ScoreSight hung or showed "Not Responding" when quitting on macOS. The
  built-in HTTP server now stops in-process within a few seconds
  ([#7](https://github.com/royshil/scoresight/issues/7),
  [#33](https://github.com/royshil/scoresight/issues/33)).
- Switching sources or quitting no longer hangs while a stream is stalled: the
  capture gets up to 3 seconds to stop
  ([#7](https://github.com/royshil/scoresight/issues/7),
  [#33](https://github.com/royshil/scoresight/issues/33)).
- Closing the main window while **Video Settings** or **Connect to OBS** was
  open left ScoreSight running until that window was closed too.
- If the HTTP server port is already in use, ScoreSight logs an error and keeps
  running without the server, and closing an instance never affects another
  instance's server ([#8](https://github.com/royshil/scoresight/issues/8)).
- The HTTP `/csv` endpoint returned the box positions as method names instead
  of numbers ([#29](https://github.com/royshil/scoresight/issues/29)).
  `/xml?pivot` always produces valid XML, even for box names such as
  "1st Half", and the XML endpoints are sent as UTF-8.
- The `/scoresight` demo page didn't work when opened from another computer or
  with a different `--port`.
- vMix received no data with the default settings
  ([#55](https://github.com/royshil/scoresight/issues/55)).
- Editing the vMix host, port or input, or the UNO URL, could stop the output
  silently or lose the field mapping. Changes now apply when you press Enter
  or leave the field. The vMix field mapping shown in the table is used even
  before any cell is edited.
- Per-box `.txt` files were sometimes never written, because a change that
  arrived between two file saves was dropped
  ([#6](https://github.com/royshil/scoresight/issues/6)).
- The CSV header was repeated before every row, values with commas broke the
  columns, and `results.xml` could be malformed
  ([#29](https://github.com/royshil/scoresight/issues/29)).
- Clicking a box or changing a box setting emptied `results.csv`.
- OBS text sources didn't update unless an output folder was set
  ([#30](https://github.com/royshil/scoresight/issues/30)).
- After **Create OBS Scene**, the new text sources could keep the scene's
  placeholder values until each box's value changed. Every box's current value
  is now sent with the next reading.
- The per-box confidence threshold had no effect, because Tesseract's 0–100
  confidence was compared with a 0–1 threshold. It now works, and when
  Tesseract reports a confidence of 0 for a non-empty reading, the average of
  the character confidences is used
  ([#30](https://github.com/royshil/scoresight/issues/30)).
- A box over plain background produced invented digits with the scoreboard
  models. It now reads as empty
  ([#30](https://github.com/royshil/scoresight/issues/30)).
- A **Dot Counter** box over a blank area could count one dot, for example with
  **Local** or **Adaptive** binarization. It now reports 0.
- Template fields could show rejected readings such as `SIM`, and were sent as
  a new value on every cycle, which defeated **Update on change**.
- **Dilate** didn't reach the OCR with every binarization method, and
  overlapping boxes affected each other's reading.
- A box reaching past the edge of the picture was read as empty, or moved and
  shrunk in the saved settings. It is now read from its visible part and left
  as it is.
- **Average Output** could show mixed values such as `92` when the number of
  digits changed, and **Skip Similar Image** ignored one-digit changes.
- With **Skip Similar Image** on, a new value whose first reading was rejected
  or empty wasn't read again until the image changed once more. The image is
  now compared with the box's last accepted reading.
- Video processing stopped silently on an oversized crop, a very short box with
  vertical scaling, a black frame while stabilization was on, an OCR model
  change in the middle of a reading, or a box deleted while it was being read.
- Selecting an invalid custom OCR model now keeps the current model working.
- Stabilization fed the OCR blended frames while it warmed up.
- An invalid four-corner selection (for example the same corner clicked twice)
  corrupted every frame. It is now rejected and you can click again.
- NDI sources disappeared when **Reload** was clicked again, and refreshing
  paused for a second.
- Clicking **Reload** while a camera was selected opened the Screen Capture
  dialog, and with two cameras could switch to the other camera.
- In a translated interface, cancelling **Open a Video File** left the source
  list on that entry, with the field list and the view tools disabled.
- On Linux, device nodes that can't capture video were listed, and cameras
  could open with the wrong device number.
- **Capture the entire screen** didn't work on macOS.
- Closed sources stayed in memory and could be reopened in the background by a
  later Video Settings change.
- Each Video Settings change made every OCR result be processed and sent to
  the outputs once more.
- Box setting changes, new or removed boxes and renames were lost when
  switching or reloading the source.
- Renaming a custom field that had a box removed it from the field list until
  another box changed or ScoreSight restarted, although its box was still read.
- Clicking **-** with a predefined field such as *Home Score* selected deleted
  its box and box settings. Predefined fields can't be removed, and the button
  now leaves them alone.
- A box's **Type** (Number/Time/Text) was lost after a restart or a
  configuration export ([#22](https://github.com/royshil/scoresight/issues/22)).
- The **Stop Updates**/**Resume Updates** button went blank in non-English
  languages.
- Switching the language reset the vMix connection, the UNO URL and the
  template field text.
- The Output API encoding was blank on a fresh install, so POST/PUT output
  never sent anything.
- The **Save Folder** chosen in **OCR Training Data Setup** was ignored
  ([#52](https://github.com/royshil/scoresight/issues/52)). It is now used and
  remembered, configurations from 0.1.x keep working, and the default folder
  follows `SCORESIGHT_DATA_DIR`.
- With **Save OCR Training Data** on and a template field defined, recognition
  could silently stop after a few frames. Saving samples can no longer stop
  recognition.
- Saving OCR training data scanned the whole folder on every detection and
  flooded the log when the folder was full. The size limit is now logged once,
  and saving resumes when there is room again.
- OCR training data couldn't be saved to folders with non-ASCII characters in
  their path on Windows.
- **Open Folder** in OCR Training Data Setup didn't work on macOS and Linux.
- Training Dojo: with **Only Undone** on, Enter skipped an image; clicking a
  filtered list item opened the wrong item; an empty folder, a missing
  annotation file or a damaged `approved_annotations.json` crashed it;
  Ctrl+Up/Down discarded the text being typed; unapproved items were
  unreadable in dark mode.
- The log viewer failed when the log file couldn't be created, didn't read
  logs as UTF-8, lost the scroll position with Auto Scroll off, and kept
  polling while closed.
- The standalone training-data tools in `scripts/` crashed or hung when
  cancelled or when their window was closed, didn't handle empty or missing
  folders and non-ASCII paths, and required undocumented corner click orders.
  They now also have `--help`.
- The packaged app re-ran most of its modules at startup and again after the
  window closed.

### Removed

- The unauthenticated `GET /shutdown` endpoint of the built-in HTTP server (see
  Security).
- The **File > Theme** menu (replaced by **File > Appearance**), the **Force
  Format** checkbox and the UNO **Rate Limit** field, which had no effect.
- All links to the former `scoresight[.]live` website, download server and
  e-mail addresses, in the app and the documentation, and the expired Discord
  invite.
- The `.env` file and the unused NDI UWP and DirectShow libraries from the
  packaged app (about 66 MB smaller).
- The `pygetwindow` and pinned `websockets` dependencies.

### Security

- Removed `GET /shutdown`, which let any device that could reach port 18099,
  or any web page open in a browser, close ScoreSight. Closing a second
  instance also shut down the first one.
- The OBS WebSocket password is no longer written to the log.
- The HTTP server's CORS policy allows only `GET` requests, without
  credentials.
- The About and Update dialogs of 0.1.x and older link to `scoresight[.]live`, a
  domain the project no longer controls. Download ScoreSight only from
  [GitHub Releases](https://github.com/royshil/scoresight/releases) and verify
  it against `SHA256SUMS.txt`.
- Added `SECURITY.md`, which describes how to report vulnerabilities and the
  app's network exposure (the HTTP server listens on all interfaces without
  authentication).

## [0.1.0] - 2024-11-07

### Added

- overlays.uno **Essentials** API support (content fields with an overlay ID)
  ([#44](https://github.com/royshil/scoresight/pull/44)).
- Experimental **Composite (Per-Character)** boxes: draw and save one sub-box
  per character ([#48](https://github.com/royshil/scoresight/pull/48)).
- Application style (theme) selection
  ([#51](https://github.com/royshil/scoresight/pull/51)).

### Changed

- Cameras open at their highest supported resolution
  ([#51](https://github.com/royshil/scoresight/pull/51)).
- Main window layout and translation updates
  ([#47](https://github.com/royshil/scoresight/pull/47)).

## [0.0.17] - 2024-10-15

### Added

- Load an external Tesseract OCR model (`.traineddata`)
  ([#46](https://github.com/royshil/scoresight/pull/46)).

### Fixed

- UI improvements and bug fixes, including a loading issue on macOS
  ([#45](https://github.com/royshil/scoresight/pull/45)).

## [0.0.16] - 2024-10-09

### Added

- overlays.uno (UNO) API output
  ([#42](https://github.com/royshil/scoresight/pull/42)).
- Detection box display styles, such as outline only
  ([#42](https://github.com/royshil/scoresight/pull/42)).
- Resize handles and select/deselect for detection boxes.

### Changed

- UI refactoring and bug fixes
  ([#43](https://github.com/royshil/scoresight/pull/43)).

## [0.0.15] - 2024-10-04

### Added

- Choice of HTTP method (POST, PUT, GET) for outbound API requests
  ([#39](https://github.com/royshil/scoresight/pull/39)).

### Changed

- Source files moved into `src/`, and major code refactoring
  ([#40](https://github.com/royshil/scoresight/pull/40),
  [#41](https://github.com/royshil/scoresight/pull/41)).

### Fixed

- NDI capture disabling the UI
  ([#41](https://github.com/royshil/scoresight/pull/41)).

## [0.0.14] - 2024-09-25

### Added

- **OCR Training Dojo** for annotating collected training data
  ([#38](https://github.com/royshil/scoresight/pull/38)).
- Playback speed control for video files
  ([#38](https://github.com/royshil/scoresight/pull/38)).

### Fixed

- A critical bug in screen capture mode
  ([#37](https://github.com/royshil/scoresight/pull/37)).

## [0.0.13] - 2024-09-23

### Added

- **Video Settings** dialog for cameras (FPS, resolution, format, capture
  backend) ([#36](https://github.com/royshil/scoresight/pull/36)).
- OCR training data collection.
- Sending readings to external HTTP APIs (outbound API).

## [0.0.12] - 2024-09-18

### Added

- Image rotation ([#35](https://github.com/royshil/scoresight/pull/35)).

### Fixed

- RTSP/URL sources on Windows were opened with DirectShow and could not play.
- The Detections / s setting wasn't loaded correctly at startup.

### Removed

- The unused status bar.

## [0.0.11] - 2024-09-10

### Added

- **Template fields** that combine other fields with a prefix or suffix
  ([#34](https://github.com/royshil/scoresight/pull/34)).

### Fixed

- A 4-corner correction bug.
- Duplicate entries when renaming custom fields.

## [0.0.10] - 2024-08-13

### Fixed

- vMix integration ([#28](https://github.com/royshil/scoresight/pull/28)).
- A logging error after closing the app
  ([#26](https://github.com/royshil/scoresight/pull/26)).

## [0.0.9] - 2024-07-20

### Added

- Crop function ([#21](https://github.com/royshil/scoresight/pull/21)).

### Fixed

- Loading custom boxes ([#23](https://github.com/royshil/scoresight/pull/23)).

## [0.0.8] - 2024-06-30

### Fixed

- Real-time updates of the built-in HTML scoreboard page.
- JSON pivot output.
- Camera enumeration on Linux
  ([#14](https://github.com/royshil/scoresight/pull/14)).

## [0.0.7] - 2024-06-17

### Added

- **Dot counter**, for example for counting baseball balls, strikes and outs
  ([#15](https://github.com/royshil/scoresight/pull/15)).
- Interface translations into more than 10 languages
  ([#11](https://github.com/royshil/scoresight/pull/11)).

### Changed

- Updated Tesseract and other dependencies
  ([#13](https://github.com/royshil/scoresight/pull/13)).
- UI improvements.

### Fixed

- The built-in HTTP service.

## [0.0.6] - 2024-05-23

### Fixed

- Various bug fixes.

## [0.0.5] - 2024-05-23

### Fixed

- UI bugs and the handling of result states for detection boxes
  ([#9](https://github.com/royshil/scoresight/pull/9)).

## [0.0.4] - 2024-04-28

### Added

- **Update on change**: send a value only when it changes.

## [0.0.3] - 2024-04-26

### Added

- Separate macOS builds for Intel (x86) and Apple Silicon (arm64)
  ([#2](https://github.com/royshil/scoresight/pull/2)).

## [0.0.2] - 2024-04-25

### Changed

- Packaging and build fixes.

## [0.0.1] - 2024-04-25

- First open-source release of ScoreSight.

[Unreleased]: https://github.com/royshil/scoresight/compare/0.1.0...HEAD
[0.1.0]: https://github.com/royshil/scoresight/compare/0.0.17...0.1.0
[0.0.17]: https://github.com/royshil/scoresight/compare/0.0.16...0.0.17
[0.0.16]: https://github.com/royshil/scoresight/compare/0.0.15...0.0.16
[0.0.15]: https://github.com/royshil/scoresight/compare/0.0.14...0.0.15
[0.0.14]: https://github.com/royshil/scoresight/compare/0.0.13...0.0.14
[0.0.13]: https://github.com/royshil/scoresight/compare/0.0.12...0.0.13
[0.0.12]: https://github.com/royshil/scoresight/compare/0.0.11...0.0.12
[0.0.11]: https://github.com/royshil/scoresight/compare/0.0.10...0.0.11
[0.0.10]: https://github.com/royshil/scoresight/compare/0.0.9...0.0.10
[0.0.9]: https://github.com/royshil/scoresight/compare/0.0.8...0.0.9
[0.0.8]: https://github.com/royshil/scoresight/compare/0.0.7...0.0.8
[0.0.7]: https://github.com/royshil/scoresight/compare/0.0.6...0.0.7
[0.0.6]: https://github.com/royshil/scoresight/compare/0.0.5...0.0.6
[0.0.5]: https://github.com/royshil/scoresight/compare/0.0.4...0.0.5
[0.0.4]: https://github.com/royshil/scoresight/compare/0.0.3...0.0.4
[0.0.3]: https://github.com/royshil/scoresight/compare/0.0.2...0.0.3
[0.0.2]: https://github.com/royshil/scoresight/compare/0.0.1...0.0.2
[0.0.1]: https://github.com/royshil/scoresight/releases/tag/0.0.1
