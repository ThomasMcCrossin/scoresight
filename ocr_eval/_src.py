"""Access to ScoreSight's own modules (src/), which import each other by bare
module name, from the harness.

defaults.py is a pure module and can be imported at any time. Importing the rest
of the app (e.g. tesseract.py, which imports storage and sc_logging) touches the
settings and log directories at import time, so isolate_app_state() points them
at a throw-away directory first, the way tests/conftest.py does.
"""

import atexit
import logging
import os
import shutil
import sys
import tempfile

from ocr_eval import REPO_ROOT

SRC_DIR = REPO_ROOT / "src"

_isolated_dir: str | None = None


def ensure_src_on_path() -> None:
    src = str(SRC_DIR)
    if src not in sys.path:
        sys.path.insert(0, src)


def isolate_app_state() -> None:
    """Point SCORESIGHT_DATA_DIR and SCORESIGHT_LOG_DIR at a temporary directory
    (removed at exit) unless they are set (e.g. by the test suite, or by a user
    who chose them), and drop any profile, so that an evaluation doesn't read or
    write the user's default settings and logs. Call before importing app
    modules other than defaults."""
    global _isolated_dir
    ensure_src_on_path()
    if _isolated_dir is not None:
        return
    _isolated_dir = tempfile.mkdtemp(prefix="scoresight-ocr-eval-")
    os.environ.setdefault("SCORESIGHT_DATA_DIR", os.path.join(_isolated_dir, "data"))
    os.environ.setdefault("SCORESIGHT_LOG_DIR", os.path.join(_isolated_dir, "logs"))
    os.environ.pop("SCORESIGHT_PROFILE", None)
    atexit.register(_cleanup)


def _cleanup() -> None:
    # close the log files sc_logging opened so they can be deleted on Windows
    logging.shutdown()
    if _isolated_dir is not None:
        shutil.rmtree(_isolated_dir, ignore_errors=True)


def import_defaults():
    """ScoreSight's defaults module (field types, box presets, whitelists)."""
    ensure_src_on_path()
    import defaults

    return defaults
