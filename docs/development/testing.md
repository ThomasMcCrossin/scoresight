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
| (none) | Only the Python dependencies | storage, defaults, file and HTTP output formats |
| `ocr` | `tesserocr` and the bundled models in `tesseract/tessdata` | recognition of synthetic digit images |
| `qt` | Qt, running offscreen | widgets and dialogs |

Select or skip groups with `-m`:

```bash
python -m pytest -m "not ocr"            # skip OCR tests
python -m pytest -m "not ocr and not qt" # fastest: pure-Python tests only
python -m pytest tests/test_storage.py -q
```

Qt tests run without a display. If you run them on a headless machine and they can't find a display, set `QT_QPA_PLATFORM=offscreen`.

The tests use temporary folders for settings and logs (see `tests/conftest.py`), so they don't touch your real ScoreSight configuration.

## The self-test

`--self-test` checks a complete installation without opening a window: it imports every module, initializes the OCR engine with each bundled model, reads a synthetic digit image, prints `SELF-TEST OK` and exits with code 0. Otherwise it exits with a non-zero code.

```bash
QT_QPA_PLATFORM=offscreen python src/main.py --self-test
```

CI runs the same check against the frozen (PyInstaller) app on every platform, to catch missing modules or data files in the package.

## Code style: ruff

ScoreSight uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting (configured in `pyproject.toml`, targeting Python 3.13). The generated `src/ui_*.py` files are excluded.

```bash
ruff check .            # lint
ruff check --fix .      # lint and apply safe fixes
ruff format .           # format
ruff format --check .   # what CI runs
```

CI fails if `ruff check .` or `ruff format --check .` reports anything, so run them before you push.

## pre-commit (recommended)

[pre-commit](https://pre-commit.com/) runs ruff and other checks automatically on every commit:

```bash
pre-commit install          # once per clone
pre-commit run --all-files  # check everything now
```

## Continuous integration

Every pull request and push to `main` runs the CI workflow (`.github/workflows/ci.yml`): ruff, the test suite and test builds of the app. Pull requests from forks build without signing secrets. A pull request should be green before review.

## Writing tests

- Put tests in `tests/test_<area>_*.py` and use the fixtures from `tests/conftest.py`.
- Mark tests that need Tesseract with `@pytest.mark.ocr`, and tests that create Qt widgets with `@pytest.mark.qt`.
- Don't open real cameras, network ports or user folders. Use temporary paths, synthetic images (`numpy`/`cv2`) and local test servers.
- For a bug fix, add a test that fails without the fix.
