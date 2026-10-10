---
title: Tests & Code Style
parent: Developer Guide
nav_order: 3
description: "Run ScoreSight's pytest suite and self-test, and keep the code ruff-clean with pre-commit."
---

# Tests & Code Style
{: .no_toc }

<details open markdown="block">
  <summary>On this page</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Running the tests

The test suite lives in `tests/` and uses pytest (configured in `pyproject.toml`). With the dev requirements installed (see [Building from Source](building.md)):

```bash
python -m pytest
```

Tests are grouped with markers:

| Marker | Needs | Example |
|---|---|---|
| (none) | Only the Python dependencies | storage, defaults, file and HTTP output formats, packaging (`tests/test_packaging.py`) |
| `ocr` | `tesserocr` and the bundled models in `tesseract/tessdata` | recognition of synthetic digit images |
| `qt` | Qt, running offscreen | widgets and dialogs |

`tests/test_packaging.py` checks the release machinery without building: version parsing and the tag check, CHANGELOG section extraction and `scripts/bump_version.py`, the smoke-test runner, that `DATA_GLOBS` in `scoresight.spec` covers every resource the code loads, the installer's invariants, and that the workflows agree on the package names.

Select or skip groups with `-m`:

```bash
python -m pytest -m "not ocr"            # skip OCR tests
python -m pytest -m "not ocr and not qt" # fastest: pure-Python tests only
python -m pytest tests/test_storage.py -q
```

Qt tests run without a display. If you run them on a headless machine and they can't find a display, set `QT_QPA_PLATFORM=offscreen`.

The tests use temporary folders for settings and logs (see `tests/conftest.py`), so they don't touch your real ScoreSight configuration.

## The self-test

`--self-test` checks a complete installation without showing a window. It:

1. prints the settings file and log file paths,
2. imports every app module (the list in `SELF_TEST_MODULES` in `src/main.py`; a test checks that it covers every module in `src/`),
3. checks that the bundled files exist,
4. builds the main window UI off-screen and loads a translation,
5. loads all four bundled OCR models and requires the English model to read a rendered "45",
6. resolves uvicorn's dynamic imports,
7. enumerates the video sources. A failure here (for example the Windows camera enumerator wasn't built) is only a warning when running from source, but fails a packaged build.

It prints `SELF-TEST OK` and exits with code 0, or prints the failure and exits with code 1. It sets `QT_QPA_PLATFORM=offscreen` if that isn't set, so it works on machines without a display:

```bash
python src/main.py --self-test
```

CI runs the same check against the frozen (PyInstaller) app on every platform with `scripts/ci/smoke_test.py`, to catch missing modules or data files in the package (see [Building from Source](building.md#package-with-pyinstaller)).

## Code style: ruff

ScoreSight uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting (configured in `pyproject.toml`, targeting Python 3.13). The generated `src/ui_*.py` files are excluded.

```bash
ruff check .            # lint
ruff check --fix .      # lint and apply safe fixes
ruff format .           # format
ruff format --check .   # what CI runs
python scripts/compile_ui.py --check   # are the generated src/ui_*.py up to date?
```

CI fails if `ruff check .`, `ruff format --check .` or `scripts/compile_ui.py --check` reports anything, so run them before you push.

## pre-commit (recommended)

[pre-commit](https://pre-commit.com/) runs the checks automatically on every commit: ruff (lint with `--fix`, and format, on Python files only), YAML and TOML syntax, merge-conflict markers, trailing whitespace and end-of-file fixes, and a check for large files. The ruff version in `.pre-commit-config.yaml` must match `requirements-dev.txt` (a test checks this).

```bash
pre-commit install          # once per clone
pre-commit run --all-files  # check everything now
```

## Continuous integration

Three workflows in `.github/workflows/` run on GitHub Actions:

| Workflow | Runs on | What it does |
|---|---|---|
| `ci.yml` | Every pull request, every push to `main`, manual runs | **Lint**: `ruff check`, `ruff format --check`, `scripts/compile_ui.py --check`, and a check that no file links to the lapsed `scoresight[.]live` domain. **Test**: `pytest` with Python 3.13 on Ubuntu 24.04 and Windows. macOS runs the tests only on pushes to `main`, to save scarce macOS runners. An extra Python 3.14 leg on Ubuntu is allowed to fail |
| `build.yml` | Pull requests that change packaging files (`scoresight.spec`, `scoresight.iss`, `entitlements.plist`, the `requirements*.txt` files except dev/tools, `scripts/ci/`, `src/main.py`, `src/resource_path.py`, `src/version.py`, `src/win32DeviceEnum/`, the workflow itself), manual runs (**Actions > Build > Run workflow**), and release tags through `release.yml` | Builds Windows x64, macOS arm64, macOS x86_64 and Linux x86_64 with PyInstaller, runs the frozen app's `--self-test`, and packages the installer, portable zip, disk images and archive. On Windows it also installs the installer silently, self-tests the installed app and uninstalls it. The packages are uploaded as workflow artifacts |
| `release.yml` | Version tags only | See [Releasing](releasing.md) |

Pull request builds, including those from forks, are unsigned. A pull request should be green before review. Test packages from a pull request or a manual run are named `scoresight-<version>-<short commit>-<platform>...`.

## Writing tests

- Put tests in `tests/test_<area>_*.py` and use the fixtures from `tests/conftest.py`.
- Mark tests that need Tesseract with `@pytest.mark.ocr`, and tests that create Qt widgets with `@pytest.mark.qt`.
- Don't open real cameras, network ports or user folders. Use temporary paths, synthetic images (`numpy`/`cv2`) and local test servers.
- For a bug fix, add a test that fails without the fix.
