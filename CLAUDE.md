# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

ScoreSight is a PySide6 (Qt6) desktop app that runs real-time Tesseract OCR on user-defined boxes over a live video source (camera, NDI, screen capture, URL/RTSP, video file) and pushes the results to outputs (files, a built-in HTTP server, OBS, vMix, UNO, and generic HTTP APIs). The README marks the project as stalled (not under active development).

## Setup and commands

Requires Python 3.11. Install `requirements.txt`, plus `requirements-win.txt` or `requirements-mac.txt` for your platform. `tesserocr` usually can't be installed straight from pip: on Windows CI installs a prebuilt wheel from `simonflueckiger/tesserocr-windows_build`, and on macOS it's built against Homebrew `tesseract` (see README and `.github/workflows/build.yaml`).

- **Windows only:** build the native DirectShow device enumerator before running: `cd src/win32DeviceEnum && python setup.py build_ext --inplace`
- **Compile Qt Designer UI files:** `./scripts/compile_ui.ps1` turns each `src/*.ui` into `src/ui_*.py`. Never hand-edit `ui_*.py`. Edit the `.ui` file and recompile. Prefer the `.ps1` script, because `compile_ui.sh` omits `--star-imports` and produces output that doesn't match the committed files.
- **Run from source:** run `python src/main.py` from the **repo root**. The README says `python main.py`, but `resource_path()` resolves `tesseract/`, `translations/` and `icons/` against the current working directory in dev mode, so launching from `src/` breaks model and translation loading.
- **Format check (the only CI gate besides the build):** `black --check ./src --exclude '/ui_.*\.py'`. Run `black ./src --exclude '/ui_.*\.py'` to fix.
- **Tests:** there is no test suite.
- **Build executable:** `pyinstaller --clean --noconfirm scoresight.spec -- --win` (or `-- --mac_osx`; no flag for Linux; add `--debug` for a console build on Windows).
- **Translations:** `scripts/update_translations.ps1` runs `pyside6-lupdate` to refresh the `.ts` files, and `scripts/compile_translations.ps1` runs `pyside6-lrelease` to produce `.qm` files. The compiled `.qm` files are committed and bundled.

### `.env`

`.env` is gitignored but required: `scoresight.spec` bundles it, and it's loaded at startup.

| Variable | Purpose |
|---|---|
| `LOCAL_RELEASE_TAG` | Shown in the window title. |
| `LOCAL_RELEASE_DATE` | Set alongside the tag by CI. |
| `SCORESIGHT_DEBUG` | Optional. Any value mirrors logs to the console and turns on uvicorn debug logging. |

CI writes this file in `build.yaml`.

## Architecture

All app code is a flat set of modules in `src/` that import each other by bare module name (`from storage import ...`), not as a package. Running `src/main.py` puts `src/` on `sys.path`.

### Frame → OCR → outputs pipeline

1. **Source discovery:** `get_camera_info.py` enumerates devices per OS (DirectShow `.pyd` on Windows, AVFoundation on macOS, `/dev/video*` on Linux, plus NDI) into `CameraInfo` objects. `CameraInfo.CameraType` covers OpenCV, NDI, file, URL and screen capture.
2. **Capture thread:** `source_view.ImageViewer` extends `camera_view.CameraView` (a `QGraphicsView`), which owns a `camera_thread.TimerThread` (a `QThread`). The thread picks a `BaseVideoCapture` implementation:
   - `OpenCVVideoCaptureWithSettings`, which uses `CAP_DSHOW` on Windows
   - `ndi.NDICapture`
   - `screen_capture_source.ScreenCapture`, which resolves to a mac or Windows implementation, or a dummy on Linux
3. **Per-frame processing in `TimerThread.run()`:** rotate and crop → optional stabilization (`frame_stabilizer.py`) → optional perspective homography from the user's four corners → grayscale plus a global Otsu binary → `TextDetector.detect_multi_text()`. The loop throttles OCR to the "detection cadence" setting and emits the preview frame about once per second.
4. **OCR (`tesseract.py`):** `TextDetector` holds a single `tesserocr` API instance guarded by a lock. It uses PSM 8 (single word), and the models live in `tesseract/tessdata/*.traineddata`. For each box it applies the preprocessing that box's settings dict selects (binarization method, cleanup, vscale, skew, dilate, invert, autocrop, rescale, dot detector), sets a character whitelist from `FieldType`, and then post-filters the text (regex, confidence threshold, smoothing, leading zeros, ordinal suffix). The results are `TextDetectionResult` objects, which `TimerThread` wraps into `TextDetectionTargetWithResult` and emits through `ocr_result_signal`.
5. **Fan-out (`MainWindow.ocrResult` in `mainwindow.py`):**
   - It first evaluates template fields (`template_fields.py` substitutes `{{Box Name}}`).
   - It then sends the results to every output: `http_server.update_http_server` (a FastAPI/uvicorn server on port **18099** in a background thread), `api_output.update_out_api`, the vMix and UNO updaters (owned by `vmix_ui_handler` and `uno_ui_handler`), OBS text sources via `obs_websocket.update_text_source`, and `file_output` (txt/csv/xml).
   - OBS and file output only run when an output folder is set, and they're rate-limited by the "aggs per second" slider.

`mainwindow.py` is the central hub. It wires the UI, sources, the OBS connection, configuration import/export, and language switching.

### Detection boxes and their settings

- `TextDetectionTarget` (in `text_detection_target.py`) subclasses `QRectF` and adds a `name`, a `settings` dict and optional `mini_rects`.
- All boxes live in `storage.TextDetectionTargetMemoryStorage`, a singleton `QObject` whose `data_changed` signal drives both the main window's box table and the viewer overlay.
- The predefined boxes (Home Score, Away Score, Time and others) and their regex presets are in `defaults.py`. Every other name is a "custom" box.
- **Per-box settings are listed explicitly in several places.** To add a new setting, update:
  - `defaults.normalize_settings_dict` (the canonical keys and defaults)
  - `storage.TextDetectionTargetMemoryStorage.getBoxesForStorage` (the serialized key list)
  - `box_settings_ui_handler.py` (the UI binding)
  - `tesseract.py`, if the setting affects processing

### Persistence and settings pub/sub

`storage.py` keeps app state in JSON under `platformdirs.user_data_dir("scoresight")/scoresight.json`, as named documents. Use `store_data`, `fetch_data` and `remove_data`. `subscribe_to_data(file, key, callback)` registers a callback that `store_data` calls **synchronously, on whichever thread does the store**. Many components (the capture thread, the video settings, the output modules) read their settings once at construction and then stay current through these subscriptions. Logging goes through `from sc_logging import logger`, which writes to `user_log_dir("scoresight")` and keeps the last 10 log files.

### Packaging gotchas

- `scoresight.spec` lists every source module (`sources`) and every bundled asset (`datas`) **explicitly**. A new `.py` file in `src/`, a new icon, a new tessdata model or a new translation must be added there, or it will be missing from the built app even though it works from source.
- Platform-specific modules (`screen_capture_source_windows.py`, `screen_capture_source_mac.py`, the win32 `.pyd`) are added conditionally by the `--win` and `--mac_osx` flags.
- Bundled resources must be loaded through `resource_path(...)`, which resolves against `sys._MEIPASS` when frozen.

### Releases

`release.yaml` runs the build on every push to `main`. Pushing a tag like `X.Y.Z` or `X.Y.Z-beta1` / `X.Y.Z-rc1` also creates a **draft** GitHub release with the Windows installer (built from the Inno Setup file `scoresight.iss`), macOS DMGs (signed and notarized) and a Linux tarball.

### Other directories

- `scripts/*.py`: standalone tkinter/OpenCV tools for cropping and annotating OCR training data. They're not part of the app (see `docs/data_annotation.md`).
- `obs_data/`: the OBS scene collection and images used by "Create OBS Scene".
- `docs/`: user-facing guides for the HTTP server, vMix, outbound APIs and installation.
