---
title: Building from Source
parent: Developer Guide
nav_order: 2
description: "Set up a ScoreSight development environment with uv and Python 3.13, run from source, and package with PyInstaller."
---

# Building from Source
{: .no_toc }

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Prerequisites

- **Python 3.13** (64-bit). 3.14 is also tested in CI.
- **git**
- **[uv](https://docs.astral.sh/uv/)** (recommended): a fast Python package and environment manager. Plain `python -m venv` + `pip` works too.
- **Windows**: [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) ("Desktop development with C++") to build the camera enumerator.
- **macOS**: Xcode Command Line Tools (`xcode-select --install`).
- **Linux**: the X11/xcb libraries Qt needs, for example on Debian/Ubuntu `sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libegl1`.

## Requirements files

| File | Contents |
|---|---|
| `requirements.txt` | Runtime dependencies for all platforms (with environment markers) |
| `requirements-win.txt` | Windows extras, including the prebuilt Windows `tesserocr` wheel |
| `requirements-mac.txt` | macOS extras (PyObjC frameworks for camera enumeration and screen capture) |
| `requirements-dev.txt` | `-r requirements.txt` plus pytest, pytest-qt, ruff and pre-commit |
| `requirements-build.txt` | Packaging tools: PyInstaller, pyinstaller-hooks-contrib, pybind11, setuptools |
| `requirements-tools.txt` | Dependencies of the standalone scripts in `scripts/` (training-data utilities) |

`tesserocr` comes as a binary wheel with Tesseract included: from PyPI on macOS and Linux, and from the [simonflueckiger/tesserocr-windows_build](https://github.com/simonflueckiger/tesserocr-windows_build) releases on Windows (referenced in `requirements-win.txt`). You don't need a system-wide Tesseract installation.

{: .note }
The macOS `tesserocr` wheels target macOS 15 or newer. On older macOS versions, install Tesseract with Homebrew (`brew install tesseract`) and build tesserocr from source: `pip install --no-binary tesserocr tesserocr`.

## Set up the environment

```bash
git clone https://github.com/royshil/scoresight.git
cd scoresight
uv venv --python 3.13
```

Activate it:

```powershell
.venv\Scripts\activate          # Windows (PowerShell)
```
```bash
source .venv/bin/activate        # macOS / Linux
```

Install the dependencies for your platform:

```bash
uv pip install -r requirements-dev.txt -r requirements-win.txt   # Windows
uv pip install -r requirements-dev.txt -r requirements-mac.txt   # macOS
uv pip install -r requirements-dev.txt                           # Linux
```

Without uv, use `python -m venv .venv` and `pip install -r ...` with the same files.

### Windows: build the camera enumerator

On Windows, ScoreSight lists cameras through a small C++ extension (`src/win32DeviceEnum`). Build it once per Python version:

```powershell
uv pip install -r requirements-build.txt
cd src\win32DeviceEnum
python setup.py build_ext --inplace
cd ..\..
```

This produces `win32DeviceEnumBind.cp313-win_amd64.pyd` (the name depends on your Python version) next to `setup.py`.

### Compile the UI files

The Qt Designer files `src/*.ui` are compiled into `src/ui_*.py`:

```bash
python scripts/compile_ui.py
```

(`scripts/compile_ui.ps1` and `scripts/compile_ui.sh` are thin wrappers around it.)

{: .important }
Never edit `src/ui_*.py` by hand. Change the `.ui` file in Qt Designer (`pyside6-designer`), run `scripts/compile_ui.py`, and commit both files. The generated files are excluded from ruff.

## Run from source

```bash
python src/main.py
```

You can run it from any working directory. Useful variations:

```bash
python src/main.py --profile dev --port 18199   # separate settings and port while developing
python src/main.py --self-test                  # headless sanity check, prints SELF-TEST OK
SCORESIGHT_DEBUG=1 python src/main.py           # log to the console too (macOS/Linux)
```

On Windows PowerShell, set the variable first with `$env:SCORESIGHT_DEBUG = "1"`. You can also put `SCORESIGHT_DEBUG=1` in a `.env` file in the repository root.

{: .tip }
Use a `--profile` while developing so you don't change the settings of the ScoreSight you use for real productions.

## Package with PyInstaller

The app is packaged with PyInstaller using `scoresight.spec`. Install the build requirements first:

```bash
uv pip install -r requirements-build.txt
```

Then build on the target platform (PyInstaller can't cross-compile):

```bash
# Windows (build the camera enumerator first, see above)
pyinstaller --clean --noconfirm scoresight.spec -- --win

# macOS
pyinstaller --clean --noconfirm scoresight.spec -- --mac_osx

# Linux
pyinstaller --clean --noconfirm scoresight.spec
```

Options after `--` are passed to the spec file. On Windows, add `--debug` to build a console version that shows the log output. The build workflows in `.github/workflows/` are the reference for the exact commands and flags CI uses. If they differ from this page, the workflow wins.

The output goes to `dist/`. Smoke-test the frozen app with its self-test:

```bash
QT_QPA_PLATFORM=offscreen dist/scoresight/scoresight --self-test
```

Adjust the path to your platform's output, for example `dist\scoresight\scoresight.exe` on Windows, or the executable in the app bundle's `Contents/MacOS/` folder on macOS.

### Windows installer

The Windows installer is built from `scoresight.iss` with [Inno Setup](https://jrsoftware.org/isinfo.php) after the PyInstaller build:

```powershell
iscc scoresight.iss
```

See the Windows job in `.github/workflows/` for how CI passes the version number to the installer.

### macOS signing and notarization

Release builds of the macOS app are signed with a Developer ID certificate and notarized by Apple in CI, when the signing secrets are configured in the repository. Local and pull-request builds are unsigned. Run them via **System Settings** > **Privacy & Security** > **Open Anyway**, or remove the quarantine attribute with `xattr -dr com.apple.quarantine ScoreSight.app`. Camera and other permissions are declared in `entitlements.plist`.

## Standalone scripts

`scripts/` also contains standalone Tk/OpenCV utilities for preparing OCR training data (`imagecropper.py`, `images_pespective_cropper.py`, `imageannotator.py`, `video_cropper.py`). They are not part of the app. Install their dependencies with `uv pip install -r requirements-tools.txt`.
