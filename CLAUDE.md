# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

ScoreSight is a PySide6 (Qt6) desktop app that runs real-time Tesseract OCR on user-defined boxes over a live video source (camera, NDI, screen capture, URL/RTSP, video file) and pushes the results to outputs (files, a built-in HTTP server, OBS, vMix, UNO, and generic HTTP APIs).

## Setup and commands

Python **3.13**. Dependencies are pinned exactly in requirements files: `requirements.txt` (runtime, with env markers), `requirements-win.txt` / `requirements-mac.txt` (platform extras), `requirements-build.txt` (PyInstaller, setuptools, pybind11), `requirements-dev.txt` (runtime + pytest, pytest-qt, ruff, pre-commit) and `requirements-tools.txt` (the standalone `scripts/*.py` tools; they need GUI OpenCV, so use a separate venv). `tesserocr` comes from PyPI on macOS/Linux (wheels bundle Tesseract) and from a pinned `simonflueckiger/tesserocr-windows_build` wheel URL on Windows.

```sh
uv python install 3.13
uv venv --python 3.13 .venv
# Windows (use .venv/bin/python and requirements-mac.txt on macOS; no platform file on Linux)
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt -r requirements-win.txt -r requirements-build.txt
```

- **Windows only:** build the native DirectShow device enumerator (needs MSVC) before running: `cd src/win32DeviceEnum && python setup.py build_ext --inplace`
- **Run from source:** `python src/main.py`, from any working directory (`resource_path()` resolves `tesseract/`, `translations/`, `icons/` against the repo root). Set `QT_QPA_PLATFORM=offscreen` to run headless.
- **Tests:** `python -m pytest` (config in `pyproject.toml`; `src/` is on the path). Single test: `python -m pytest tests/test_storage.py::test_unsubscribe`. Markers: `ocr` (real Tesseract with the bundled models; auto-skipped if `tesserocr` is missing) and `qt` (offscreen Qt widgets), e.g. `-m "not ocr"`.
- **Lint/format:** `python -m ruff check .` and `python -m ruff format .` (CI runs `ruff format --check .`). Rules are ruff's defaults (E4/E7/E9/F), no import sorting; `src/ui_*.py` is excluded.
- **Compile Qt Designer UI files:** `python scripts/compile_ui.py` turns each `src/*.ui` into `src/ui_*.py` with the venv's `pyside6-uic` (`compile_ui.ps1`/`.sh` are wrappers). `--check` fails if a committed `ui_*.py` is stale. Never hand-edit `ui_*.py`: edit the `.ui` file and recompile.
- **Build executable:** `pyinstaller --clean --noconfirm scoresight.spec -- --win` (or `-- --mac_osx`; no flag for Linux; add `--debug` for a console build on Windows).
- **Translations:** `scripts/update_translations.ps1` runs `pyside6-lupdate` to refresh the `.ts` files, and `scripts/compile_translations.ps1` runs `pyside6-lrelease` to produce `.qm` files. The compiled `.qm` files are committed and bundled.

### Version and environment variables

`src/version.py` (`__version__`) is the single source of truth for the version. `.env` (gitignored, optional) is loaded at startup and is only needed for `SCORESIGHT_DEBUG`.

| Variable | Purpose |
|---|---|
| `SCORESIGHT_DATA_DIR` | Overrides the settings directory (default `platformdirs.user_data_dir("scoresight")`). |
| `SCORESIGHT_LOG_DIR` | Overrides the log directory (default `platformdirs.user_log_dir("scoresight")`). |
| `SCORESIGHT_PROFILE` | Named profile: settings live in `scoresight-<profile>.json` instead of `scoresight.json`. |
| `SCORESIGHT_DEBUG` | Any value mirrors logs to the console and turns on uvicorn debug logging (env or `.env`). |

## Architecture

All app code is a flat set of modules in `src/` that import each other by bare module name (`from storage import ...`), not as a package. Running `src/main.py` puts `src/` on `sys.path`.

### Frame → OCR → outputs pipeline

1. **Source discovery:** `get_camera_info.py` enumerates devices per OS (DirectShow `.pyd` on Windows, AVFoundation on macOS, `/dev/video*` on Linux, plus NDI via `cyndilib`) into `CameraInfo` objects. `CameraInfo.CameraType` covers OpenCV, NDI, file, URL and screen capture.
2. **Capture thread:** `source_view.ImageViewer` extends `camera_view.CameraView` (a `QGraphicsView`), which owns a `camera_thread.TimerThread` (a `QThread`). The thread picks a `BaseVideoCapture` implementation:
   - `OpenCVVideoCaptureWithSettings`, which uses `CAP_DSHOW` on Windows
   - `ndi.NDICapture`
   - `screen_capture_source.ScreenCapture`, which resolves to a mac or Windows (win32gui) implementation, or a dummy on Linux
3. **Per-frame processing in `TimerThread.run()`:** rotate and crop → optional stabilization (`frame_stabilizer.py`) → optional perspective homography from the user's four corners → grayscale plus a global Otsu binary → `TextDetector.detect_multi_text()`. The loop throttles OCR to the "detection cadence" setting and emits the preview frame about once per second.
4. **OCR (`tesseract.py`):** `TextDetector` holds a single `tesserocr` API instance guarded by a lock. It uses PSM 8 (single word), and the models live in `tesseract/tessdata/*.traineddata`. For each box it applies the preprocessing that box's settings dict selects (binarization method, cleanup, vscale, skew, dilate, invert, autocrop, rescale, dot detector), sets a character whitelist from `FieldType`, and then post-filters the text (regex, confidence threshold, smoothing, leading zeros, ordinal suffix). The results are `TextDetectionResult` objects, which `TimerThread` wraps into `TextDetectionTargetWithResult` and emits through `ocr_result_signal`. `tesserocr` (2.10+) must first be imported on the main thread; keep its import at module level.
5. **Fan-out (`MainWindow.ocrResult` in `mainwindow.py`):**
   - It first evaluates template fields (`template_fields.py` substitutes `{{Box Name}}`).
   - It then sends the results to every output: `http_server.update_http_server` (a FastAPI/uvicorn server on port **18099** in a background thread), `api_output.update_out_api`, the vMix and UNO updaters (owned by `vmix_ui_handler` and `uno_ui_handler`), OBS text sources via `obs_websocket.update_text_source`, and `file_output` (txt/csv/xml).
   - OBS and file output are rate-limited by the "aggs per second" slider.

`mainwindow.py` is the central hub. It wires the UI, sources, the OBS connection, configuration import/export, and language switching.

### Detection boxes and their settings

- `TextDetectionTarget` (in `text_detection_target.py`) subclasses `QRectF` and adds a `name`, a `settings` dict and optional `mini_rects`.
- All boxes live in `storage.TextDetectionTargetMemoryStorage`, a singleton `QObject` whose `data_changed` signal drives both the main window's box table and the viewer overlay.
- The predefined boxes (Home Score, Away Score, Time and others) and their regex presets are in `defaults.py`. Every other name is a "custom" box.
- **To add a per-box setting**, update `defaults.normalize_settings_dict` (the canonical keys and defaults; `getBoxesForStorage` serializes exactly its output, and `tests/test_storage.py` checks that), `box_settings_ui_handler.py` (the UI binding) and `tesseract.py`, if the setting affects processing.

### Persistence and settings pub/sub

`storage.py` keeps app state in JSON as named documents in `scoresight.json` (or the profile's file) under `storage.get_data_dir()`. Use `store_data`, `fetch_data` and `remove_data`: writes are atomic (temp file + `os.replace`) and serialized by a module lock, and a corrupt file is moved aside as `<name>.corrupt-<timestamp>` instead of being overwritten. `subscribe_to_data(file, key, callback)` registers a callback that runs **after** the write, **synchronously, on whichever thread does the store**; a failing callback is logged and doesn't affect the store. Components that subscribe must call `unsubscribe_from_data(file, key, callback)` when they're torn down. Many components (the capture thread, the video settings, the output modules) read their settings once at construction and then stay current through these subscriptions.

Logging goes through `from sc_logging import logger`. Each session writes `scoresight_<ts>.log` (the app's DEBUG log, shown by the log viewer) and `scoresight_std_<ts>.log` (root logger, INFO) to `sc_logging.get_log_dir()`, keeping the newest 10 of each. If the log files can't be created, logging falls back to stderr and `log_file_path` is `None`.

### Tests

`tests/conftest.py` points `SCORESIGHT_DATA_DIR`/`SCORESIGHT_LOG_DIR` at temp dirs and sets `QT_QPA_PLATFORM=offscreen` before any app module is imported (importing `sc_logging` creates log files), so tests never touch the user's settings. The autouse `data_dir` fixture gives each test its own settings dir and an empty subscriber registry. Other fixtures: `memory_storage`, `make_target`, `make_result`, `text_detector`, plus pytest-qt's `qapp`/`qtbot`. `tests/synthetic_images.py` renders 7-segment and Hershey-font digits for OCR tests. Patch `mainwindow.start_http_server`, `mainwindow.get_camera_info` and `mainwindow.check_for_updates` before constructing `MainWindow` (see `tests/test_app_mainwindow_smoke.py`).

### Packaging gotchas

- `scoresight.spec` lists every source module (`sources`) and every bundled asset (`datas`) **explicitly**. A new `.py` file in `src/`, a new icon, a new tessdata model or a new translation must be added there, or it will be missing from the built app even though it works from source.
- Platform-specific modules (`screen_capture_source_windows.py`, `screen_capture_source_mac.py`, the win32 `.pyd`) are added conditionally by the `--win` and `--mac_osx` flags.
- Bundled resources must be loaded through `resource_path(...)`, which resolves against `sys._MEIPASS` when frozen and the repo root otherwise.
- `tesserocr` (via `cysignals`) and `cyndilib` import some submodules from compiled code, which PyInstaller can't see; they need hidden imports in the spec.

### Releases

Releases are manual: bump `src/version.py`, move the CHANGELOG's `## [Unreleased]` section to the new version, and push a tag `X.Y.Z` (or `X.Y.Z-beta.N` / `X.Y.Z-rc.N`). The tag-triggered workflow builds Windows, macOS (arm64 and x86_64) and Linux, checks the tag against `src/version.py`, and creates a **draft** GitHub release.

### Other directories

- `scripts/*.py`: standalone tkinter/OpenCV tools for cropping and annotating OCR training data. They're not part of the app (see `docs/data_annotation.md`).
- `obs_data/`: the OBS scene collection and images used by "Create OBS Scene".
- `docs/`: user-facing guides for the HTTP server, vMix, outbound APIs and installation.
