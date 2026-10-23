"""Run ScoreSight headless on a clip, once, and collect its readings.

The clip is pushed at real-time pace over a local UDP port (``ffmpeg -re``)
rather than opened as a File source: a File source is consumed as fast as the
capture loop can read it, so /game's clock timings and the detection latencies
would be measured against a source running many times faster than the board.

Three preprocessing variants:

* ``filtered`` -- ``format=gray,lut=y='clip((val-150)*3.6,0,255)'``, the
  ghost-segment suppression the live feed applies before ScoreSight sees it.
* ``raw`` -- the recorder's crop, untouched.
* ``levels`` -- the recorder's crop untouched, with the same ghost-segment
  suppression done inside ScoreSight (its picture levels): black point 150,
  white point 221 and gamma 1.0 in the profile, which is the affine stretch
  ``clip((v-150)*255/(221-150),0,255)`` -- the ffmpeg lut's ``*3.6`` to
  within 0.2%. Only the fork has picture levels; ``levels`` refuses to run
  against a build without them, so it can never silently equal ``raw``.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
# the build under test: this harness's own tree, unless configure() picks another
# (the qualification replays upstream 0.4.1 from a throwaway worktree with the
# same harness)
SCORESIGHT_ROOT = os.environ.get("SCORESIGHT_BUILD_ROOT") or os.path.dirname(HERE)
VENV_PYTHON = os.path.join(SCORESIGHT_ROOT, ".venv", "bin", "python")
MAKE_PROFILE = os.path.expanduser("~/.local/share/canteen-scoresight/make_profile.py")


def configure(build_root=None):
    """Point the harness at another ScoreSight checkout (its src/ and .venv)."""
    global SCORESIGHT_ROOT, VENV_PYTHON
    SCORESIGHT_ROOT = os.path.abspath(build_root or os.path.dirname(HERE))
    VENV_PYTHON = os.path.join(SCORESIGHT_ROOT, ".venv", "bin", "python")
    return SCORESIGHT_ROOT

# the live deployment's frame preprocessing (feed.sh)
FILTERED_VF = "format=gray,lut=y='clip((val-150)*3.6\\,0\\,255)',format=yuv420p"
RAW_VF = "format=yuv420p"

# the ffmpeg lut as ScoreSight's picture levels: black point 150, and the white
# point where clip((v-150)*3.6) reaches 255 (150 + 255/3.6 = 220.8), gamma 1
LEVELS_SETTINGS = {
    "picture_levels": True,
    "picture_black_point": 150,
    "picture_white_point": 221,
    "picture_gamma": 1.0,
}
VARIANTS = {
    "filtered": FILTERED_VF,
    "raw": RAW_VF,
    "levels": RAW_VF,
}

BOXES = ("Time", "Home Score", "Away Score", "Period")

# the engine names the harness accepts, as the profile's ocr_model value
ENGINES = {
    "ppocr": "ppocr:auto",
    "tesseract": 1,
}


class RunError(RuntimeError):
    pass


def _require_picture_levels():
    """Refuse the ``levels`` variant on a build without picture levels.

    Upstream (0.4.1) has no adjust_frame levels at all, so a profile asking for
    them would be ignored and the run would silently measure ``raw``. The
    check imports the build's own camera_thread and defaults, the way the app
    does, and requires both the setting names and the lookup-table builder.
    """
    probe = (
        "import sys\n"
        "import defaults, camera_thread\n"
        "names = ('PICTURE_LEVELS_ENABLED', 'PICTURE_BLACK_POINT', "
        "'PICTURE_WHITE_POINT', 'PICTURE_GAMMA')\n"
        "missing = [n for n in names if not hasattr(defaults, n)]\n"
        "assert not missing, 'no picture-level settings: %s' % missing\n"
        "assert hasattr(camera_thread, 'picture_levels_lut'), "
        "'no picture_levels_lut'\n"
        "assert hasattr(camera_thread, 'PictureLevels'), 'no PictureLevels'\n"
        "print('ok')\n"
    )
    source = os.path.join(SCORESIGHT_ROOT, "src")
    result = subprocess.run(
        ["nice", "-n", "15", VENV_PYTHON, "-c", probe],
        cwd=source,
        env=dict(os.environ, PYTHONPATH=source),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RunError(
            "the levels variant needs a build with picture levels "
            f"({SCORESIGHT_ROOT}); {result.stderr.strip() or result.stdout.strip()}"
        )


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _http(port, path, timeout=5.0):
    url = f"http://127.0.0.1:{port}{path}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class Feed:
    """ffmpeg pushing a clip to a local UDP port at real-time pace."""

    def __init__(self, clip, port, variant, start=0.0, duration=None, progress=None):
        self.clip = clip
        self.port = port
        self.variant = variant
        self.start = start
        self.duration = duration
        self.progress = progress
        self.process = None
        self.started_wall = None

    @property
    def vf(self):
        return VARIANTS[self.variant]

    def start_feed(self):
        cmd = [
            "ffmpeg",
            "-nostdin",
            "-loglevel",
            "error",
        ]
        if self.progress:
            # out_time vs wall clock, for a media-time mapping of the run's
            # readings without a journal reference
            cmd += ["-progress", self.progress, "-stats_period", "0.5"]
        cmd += [
            "-ss",
            f"{self.start:.3f}",
        ]
        if self.duration is not None:
            cmd += ["-t", f"{self.duration:.3f}"]
        cmd += [
            "-re",
            "-i",
            self.clip,
            "-an",
            "-vf",
            self.vf,
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "zerolatency",
            "-g",
            "5",
            "-threads",
            "1",
            "-f",
            "mpegts",
            f"udp://127.0.0.1:{self.port}?pkt_size=1316",
        ]
        self.process = subprocess.Popen(
            ["nice", "-n", "15"] + cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        return self.process

    def stop(self):
        process, self.process = self.process, None
        if process is None:
            return
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


class ScoreSight:
    """A headless ScoreSight reading the feed, on its own port and data dir."""

    def __init__(self, name, variant, engine, cadence, workdir, feed_url):
        self.name = name
        self.variant = variant
        self.engine = engine
        self.cadence = cadence
        self.workdir = workdir
        self.feed_url = feed_url
        self.port = free_port()
        self.data_dir = os.path.join(workdir, "data")
        self.log_dir = os.path.join(workdir, "logs")
        self.process = None
        self.log_path = os.path.join(workdir, "scoresight.out")

    def write_profile(self):
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        if self.variant == "levels":
            _require_picture_levels()
        cmd = [
            VENV_PYTHON,
            MAKE_PROFILE,
            "--data-dir",
            self.data_dir,
            "--profile",
            self.name,
            "--url",
            self.feed_url,
            "--cadence",
            str(self.cadence),
        ]
        if self.engine:
            cmd += ["--ocr-model", str(ENGINES[self.engine])]
        subprocess.run(
            ["nice", "-n", "15"] + cmd, check=True, stdout=subprocess.DEVNULL
        )
        profile = os.path.join(self.data_dir, f"scoresight-{self.name}.json")
        with open(profile) as handle:
            settings = json.load(handle)
        if self.engine:
            settings["ocr_model"] = ENGINES[self.engine]
        # keep the live deployment's settings that the generator leaves at defaults
        settings["update_on_change"] = True
        settings["sport"] = "hockey"
        settings["disable_update_checks"] = True
        if self.variant == "levels":
            settings.update(LEVELS_SETTINGS)
        with open(profile, "w") as handle:
            json.dump(settings, handle, indent=2)
        return profile

    def start(self, timeout=150.0):
        self.write_profile()
        env = dict(os.environ)
        env.update(
            QT_QPA_PLATFORM="offscreen",
            SCORESIGHT_DATA_DIR=self.data_dir,
            SCORESIGHT_LOG_DIR=self.log_dir,
            SCORESIGHT_PPOCR_THREADS="1",
            OPENCV_FFMPEG_CAPTURE_OPTIONS="fifo_size;1000000|overrun_nonfatal;1",
        )
        self.log = open(self.log_path, "w")
        self.process = subprocess.Popen(
            [
                "nice",
                "-n",
                "15",
                VENV_PYTHON,
                os.path.join(SCORESIGHT_ROOT, "src", "main.py"),
                "--profile",
                self.name,
                "--port",
                str(self.port),
            ],
            cwd=SCORESIGHT_ROOT,
            env=env,
            stdout=self.log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RunError(
                    f"ScoreSight exited with {self.process.returncode}; "
                    f"see {self.log_path}"
                )
            try:
                _http(self.port, "/game", timeout=2.0)
                return
            except (urllib.error.URLError, OSError, json.JSONDecodeError):
                time.sleep(0.3)
        raise RunError(f"ScoreSight did not answer on :{self.port} in {timeout}s")

    def stop(self, timeout=15.0):
        process, self.process = self.process, None
        if process is not None and process.poll() is None:
            # SIGTERM: the app's own clean shutdown (see its CLAUDE.md)
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        log = getattr(self, "log", None)
        if log is not None:
            log.close()
            self.log = None

    # --- sampling ---------------------------------------------------------

    def sample(self, since_event):
        """One poll of /json and /game; returns (readings, game, wall time)."""
        json_rows = _http(self.port, "/json")
        game = _http(self.port, f"/game?since={since_event}")
        return json_rows, game, time.time()

    def readings(self):
        """{box name: (text, state)} from /json."""
        rows = _http(self.port, "/json")
        return {
            str(row.get("name")): (str(row.get("text", "")), str(row.get("state")))
            for row in rows
        }


def collect(run, duration, since_event=0):
    """Sample /json and /game at ~1 Hz for duration seconds from a running run.

    Returns the samples and the highest event id seen.
    """
    samples = []
    last_event = since_event
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        t0 = time.monotonic()
        try:
            rows, game, wall = run.sample(last_event)
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            samples.append({"error": str(exc), "wall": time.time()})
            time.sleep(1.0)
            continue
        for event in game.get("events") or []:
            last_event = max(last_event, int(event.get("id") or 0))
        samples.append(
            {
                "wall": wall,
                "readings": {
                    str(r.get("name")): {
                        "text": str(r.get("text", "")),
                        "state": str(r.get("state", "")),
                    }
                    for r in rows
                },
                "game": {
                    "home": (game.get("home") or {}).get("score"),
                    "away": (game.get("away") or {}).get("score"),
                    "period": game.get("period"),
                    "clock": game.get("clock"),
                    "clock_running": game.get("clock_running"),
                    "final": game.get("final"),
                },
                "events": list(game.get("events") or []),
            }
        )
        # 1 Hz sampling, without letting a slow request shorten the run
        time.sleep(max(0.0, 1.0 - (time.monotonic() - t0)))
    return samples, last_event


def make_run_dir(base, name):
    path = os.path.join(base, name)
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)
    return path
