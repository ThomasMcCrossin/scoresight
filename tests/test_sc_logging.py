import ast
import os
import subprocess
import sys
from pathlib import Path

import sc_logging

SRC_DIR = Path(__file__).resolve().parent.parent / "src"


def make_logs(directory, prefix, days):
    names = [f"{prefix}2020-01-{day:02d}_10-00-00.log" for day in days]
    for name in names:
        (directory / name).write_text("old", encoding="utf-8")
    return names


def test_get_log_dir_honours_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SCORESIGHT_LOG_DIR", str(tmp_path / "logs"))
    assert sc_logging.get_log_dir() == str(tmp_path / "logs")
    monkeypatch.delenv("SCORESIGHT_LOG_DIR")
    assert sc_logging.get_log_dir()  # the platform default


def test_rotation_keeps_newest_of_each_kind(tmp_path):
    main_logs = make_logs(tmp_path, "scoresight_", range(1, 16))
    std_logs = make_logs(tmp_path, "scoresight_std_", range(1, 16))
    unrelated = tmp_path / "notes.txt"
    unrelated.write_text("keep", encoding="utf-8")

    sc_logging.rotate_logs(str(tmp_path), keep=10)

    remaining = set(os.listdir(tmp_path))
    assert remaining == set(main_logs[-10:]) | set(std_logs[-10:]) | {"notes.txt"}


def test_rotation_never_deletes_current_session_logs(tmp_path):
    # The current session's logs sort before the old ones here (e.g. the clock
    # went backwards); they must survive anyway.
    current_main = tmp_path / "scoresight_2000-01-01_00-00-00.log"
    current_std = tmp_path / "scoresight_std_2000-01-01_00-00-00.log"
    current_main.write_text("now", encoding="utf-8")
    current_std.write_text("now", encoding="utf-8")
    make_logs(tmp_path, "scoresight_", range(1, 13))
    make_logs(tmp_path, "scoresight_std_", range(1, 13))

    sc_logging.rotate_logs(
        str(tmp_path), keep=10, current_paths=(str(current_main), str(current_std))
    )

    assert current_main.exists() and current_std.exists()
    names = os.listdir(tmp_path)
    assert len([n for n in names if n.startswith("scoresight_std_")]) == 11
    assert len([n for n in names if not n.startswith("scoresight_std_")]) == 11


def test_many_std_logs_do_not_evict_main_logs(tmp_path):
    # Regression: sorting both kinds together put every "scoresight_2..." log
    # before every "scoresight_std_..." log, so main logs were all deleted.
    main_logs = make_logs(tmp_path, "scoresight_", range(20, 23))
    make_logs(tmp_path, "scoresight_std_", range(1, 25))
    sc_logging.rotate_logs(str(tmp_path), keep=10)
    assert set(main_logs) <= set(os.listdir(tmp_path))


def run_logging_setup(log_dir, extra_env=None):
    code = (
        "import sys, logging; sys.path.insert(0, sys.argv[1]); import sc_logging; "
        "sc_logging.logger.info('hello from the test'); "
        "print(repr(sc_logging.log_file_path)); "
        "print(type(sc_logging.file_handler).__name__)"
    )
    env = dict(os.environ, SCORESIGHT_LOG_DIR=str(log_dir), **(extra_env or {}))
    env.pop("SCORESIGHT_DEBUG", None)
    return subprocess.run(
        [sys.executable, "-c", code, str(SRC_DIR)],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )


def test_setup_creates_logs_in_log_dir_and_rotates(tmp_path):
    make_logs(tmp_path, "scoresight_", range(1, 13))
    make_logs(tmp_path, "scoresight_std_", range(1, 13))

    result = run_logging_setup(tmp_path)

    log_file = Path(ast.literal_eval(result.stdout.splitlines()[0]))
    assert log_file.parent == tmp_path
    assert "hello from the test" in log_file.read_text(encoding="utf-8")
    names = os.listdir(tmp_path)
    assert log_file.name in names
    assert len(names) == 20  # 10 of each kind, including this session's


def test_setup_falls_back_to_stderr_when_log_dir_unusable(tmp_path):
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("x", encoding="utf-8")

    # must not raise, and `logger`/`file_handler`/`log_file_path` stay importable
    result = run_logging_setup(blocker / "logs")

    log_file_path, handler_type = result.stdout.splitlines()[:2]
    assert log_file_path == "None"
    assert handler_type == "StreamHandler"
    assert "hello from the test" in result.stderr
