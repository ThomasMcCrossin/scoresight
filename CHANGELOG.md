# Changelog

All notable changes to ScoreSight are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Release tags are the bare version number (for example `0.1.0`).

## [Unreleased]

ScoreSight is actively maintained again. This release modernizes the whole
stack, fixes the most reported problems, and adds profiles for running
multiple instances.

### Added

- Profiles for running several ScoreSight instances side by side, for example
  one per camera ([#8](https://github.com/royshil/scoresight/issues/8)):
  - `--profile NAME` (or the `SCORESIGHT_PROFILE` environment variable) uses
    the settings file `scoresight-NAME.json` instead of `scoresight.json`.
  - `--port N` serves the HTTP API on port `N` instead of 18099.
- `--self-test` command-line option: a headless check that loads all modules
  and every bundled OCR model, reads a test image, prints `SELF-TEST OK` and
  exits with code 0. Release builds are smoke-tested with it.
- `SCORESIGHT_DATA_DIR` and `SCORESIGHT_LOG_DIR` environment variables to move
  the settings and log folders.
- **File > Appearance** with System, Light and Dark colour schemes,
  remembered between runs ([#50](https://github.com/royshil/scoresight/issues/50)).
- A damaged settings file is now backed up as `<name>.corrupt-<timestamp>`
  instead of being silently replaced by defaults.
- New documentation site at <https://royshil.github.io/scoresight/>:
  quickstart, installation (including macOS permissions and Linux), video
  sources (including RTSP over TCP,
  [#10](https://github.com/royshil/scoresight/issues/10)), boxes and template
  fields, a per-box settings reference, recognition and performance tuning
  guides ([#20](https://github.com/royshil/scoresight/issues/20),
  [#30](https://github.com/royshil/scoresight/issues/30)), an HTTP API
  reference, OBS, vMix, UNO and outbound API guides, troubleshooting, FAQ and a
  developer guide.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, GitHub issue forms and
  a pull request template.
- Automated tests (pytest) and linting/formatting (ruff) in continuous
  integration, plus `scripts/compile_ui.py` to compile the Qt Designer files
  on every platform.
- Every release now includes a `SHA256SUMS.txt` file for verifying downloads.

### Changed

- The vMix output now defaults to port **8088**, the vMix Web API (Web
  Controller). A previously saved port 8099 (the vMix TCP API, which ScoreSight
  never supported) is changed to 8088 automatically
  ([#55](https://github.com/royshil/scoresight/issues/55)).
- OBS, vMix, UNO and outbound API updates are sent from background workers with
  network timeouts. Only the latest values are sent when a target falls behind,
  so a slow or unreachable target no longer freezes the ScoreSight window
  ([#33](https://github.com/royshil/scoresight/issues/33)).
- OBS text sources are updated even when no output folder is set
  ([#30](https://github.com/royshil/scoresight/issues/30)).
- File outputs are state-based and atomic. Each `.txt` file is written whenever
  its value differs from what is on disk or the file is missing, and replaced
  in one step so readers never see a partial file. `results.csv` is written
  with proper CSV quoting and a single header row, and `results.xml` is
  properly escaped ([#6](https://github.com/royshil/scoresight/issues/6),
  [#29](https://github.com/royshil/scoresight/issues/29)).
- Settings are saved atomically and safely from any thread.
- Updated to Python 3.13 with current dependencies: PySide6-Essentials 6.12
  (Qt 6.12), NumPy 2, OpenCV (headless), tesserocr 2.11 / Tesseract 5.5,
  cyndilib 0.1 (NDI), and current FastAPI, uvicorn and obsws-python.
- Release builds for Windows x64, macOS Apple Silicon, macOS Intel and Linux
  x86_64. The macOS app now requires macOS 15 or newer.
- The version number comes from a single place (`src/version.py`), so the
  window title always shows the real version.
- ScoreSight can be started from source from any working directory
  (`python src/main.py`).
- Code style is enforced with ruff instead of black.

### Fixed

- Setting **Detections / s** to 1 stopped all processing and froze the
  preview, and the UI could stay disabled after a restart. Elapsed time is now
  computed correctly at every rate
  ([#53](https://github.com/royshil/scoresight/issues/53),
  [#20](https://github.com/royshil/scoresight/issues/20)).
- The **Save Folder** chosen in **OCR Training Data Setup** was ignored
  ([#52](https://github.com/royshil/scoresight/issues/52)).
- ScoreSight hung or showed "Not Responding" when quitting on macOS. The
  built-in HTTP server now stops in-process
  ([#7](https://github.com/royshil/scoresight/issues/7),
  [#33](https://github.com/royshil/scoresight/issues/33)).
- vMix received no data with the default settings
  ([#55](https://github.com/royshil/scoresight/issues/55)).
- Per-box `.txt` files were sometimes never written
  ([#6](https://github.com/royshil/scoresight/issues/6)).
- The CSV header was repeated on every appended row, and `results.xml` could be
  malformed ([#29](https://github.com/royshil/scoresight/issues/29)).
- OBS text sources didn't update unless an output folder was set
  ([#30](https://github.com/royshil/scoresight/issues/30)).
- A box's **Type** (Number/Time/Text) was lost after a restart or a
  configuration export ([#22](https://github.com/royshil/scoresight/issues/22)).

### Removed

- The unauthenticated `GET /shutdown` endpoint of the built-in HTTP server.
- All links to the former `scoresight[.]live` website, download server and
  e-mail addresses, and the expired Discord invite.
- The `pygetwindow` and pinned `websockets` dependencies.

### Security

- Removed `GET /shutdown`, which let any device that could reach port 18099
  close ScoreSight.
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
