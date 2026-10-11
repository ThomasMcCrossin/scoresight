"""File outputs: a .txt file per box, results.csv and results.xml in the output
folder.

Writes are state-based rather than edge-based. FileOutput keeps the last good
reading of every box (record) and, whenever the files are flushed, (re)writes a
file only if what it should contain differs from what was last written to it or
the file is missing. A change that arrives between two flushes is therefore
never lost: the next flush writes the latest value. Only good readings (Success
or SameNoChange) are written, so a rejected or empty reading never overwrites a
good value.

Files that are overwritten are replaced atomically (a temp file in the same
folder, then os.replace), so programs polling them (OBS, vMix, CasparCG...)
never see a truncated file. results.csv is written with the csv module and has
exactly one header row; results.xml is built with ElementTree, so it is always
well-formed.
"""

import csv
import datetime
import io
import os
import re
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from sc_logging import logger
from text_detection_target import TextDetectionTargetWithResult

ResultState = TextDetectionTargetWithResult.ResultState

# The good reading states: Success (a new value) and SameNoChange (the value is
# unchanged since the last Success).
GOOD_STATES = (ResultState.Success, ResultState.SameNoChange)

# comboBox_appendMethod indices
APPEND_CSV = 0
APPEND_TXT = 1
APPEND_BOTH = 2
APPEND_NONE = 3

CSV_FILE_NAME = "results.csv"
XML_FILE_NAME = "results.xml"
CSV_TIMESTAMP_COLUMN = "Timestamp"

# characters that are not allowed in file names on Windows (and "/" anywhere)
_INVALID_FILE_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# characters that are not allowed in XML 1.0 documents
_INVALID_XML_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


def is_good_reading(result: TextDetectionTargetWithResult) -> bool:
    """A reading worth publishing: Success or SameNoChange with a text, and not
    an empty text on a box with "Skip Empty Values" on."""
    if result.result is None or result.result_state not in GOOD_STATES:
        return False
    settings = result.settings or {}
    if settings.get("skip_empty", False) and len(result.result) == 0:
        return False
    return True


def text_file_name(box_name: str) -> str:
    """The .txt file name for a box. Characters that can't be used in a file name
    are replaced with "_"."""
    return _INVALID_FILE_NAME_CHARS.sub("_", box_name) + ".txt"


def _replace_with_retry(src: str, dst: str, attempts: int = 3, delay: float = 0.01):
    # On Windows os.replace fails with PermissionError while a reader (OBS, an
    # antivirus) has the destination open. Retry briefly: this runs on the GUI
    # thread, and a failed write is retried by the next flush anyway.
    for attempt in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)


def write_text_atomic(path: str, text: str, newline: str | None = None):
    """Replace path with text (UTF-8) atomically: write a temp file in the same
    folder, then move it over path."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(
        prefix="." + os.path.basename(path) + ".", suffix=".tmp", dir=directory
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as f:
            f.write(text)
        _replace_with_retry(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def _read_text(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def _read_last_line(path: str, max_bytes: int = 4096) -> str | None:
    """The last non-empty line of a text file (read from its end only)."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    lines = [line for line in tail.splitlines() if line != ""]
    return lines[-1] if lines else None


def _read_csv_header(path: str) -> list[str] | None:
    """The header row of a CSV file, [] for an empty file, None if unreadable."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            return next(csv.reader(f), [])
    except (OSError, csv.Error):
        return None


def _rotated_csv_path(path: str) -> str:
    base, ext = os.path.splitext(path)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = f"{base}-{stamp}{ext}"
    counter = 1
    while os.path.exists(candidate):
        candidate = f"{base}-{stamp}-{counter}{ext}"
        counter += 1
    return candidate


def _xml_text(value) -> str:
    return _INVALID_XML_CHARS.sub("", str(value))


@dataclass(frozen=True)
class _Reading:
    text: str
    state: str


@dataclass(frozen=True)
class _Box:
    """A plain snapshot of one result (the result objects are shared with the
    OCR thread, so they are not kept)."""

    name: str
    state: str
    rect: tuple[float, float, float, float]


@dataclass(frozen=True)
class FileOutputStatus:
    """What FileOutput.status() reports about the writing."""

    folder: str | None = None  # the folder of the last flush
    files: int = 0  # files written to that folder in this session
    last_write_at: float | None = None  # (FileOutput's clock)
    # the names of the files whose last write failed, and the latest error
    failing: tuple[str, ...] = ()
    last_error: str | None = None
    last_error_at: float | None = None


class FileOutput:
    """Writes the box readings to the output folder; see the module docstring.

    record() is called with every OCR result list; flush() writes the files.
    The caller throttles flushes with seconds_until_flush() (the "Save / s"
    setting) and must flush again once the throttle opens, so the latest
    recorded values always reach the files.
    """

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._boxes: list[_Box] = []
        # last good reading of each box, by name
        self._latest: dict[str, _Reading] = {}
        self._last_flush: float | None = None
        self._append_txt: bool | None = None
        # what is known to be in each file: {path: value / last row / snapshot}
        self._txt_written: dict[str, str | None] = {}
        self._csv_header: dict[str, list[str]] = {}
        self._csv_written: dict[str, tuple] = {}
        self._xml_written: dict[str, tuple] = {}
        # files whose last write failed (logged once until they succeed again)
        self._failing: set[str] = set()
        # for status(): the folder of the last flush and the files written to it
        self._folder: str | None = None
        self._written: set[str] = set()
        self._last_write_at: float | None = None
        self._last_error: str | None = None
        self._last_error_at: float | None = None

    def status(self) -> FileOutputStatus:
        """What was written, and what failed. FileOutput is used on one thread
        (the GUI thread), which also reads this."""
        return FileOutputStatus(
            folder=self._folder,
            files=len(self._written),
            last_write_at=self._last_write_at,
            failing=tuple(sorted(os.path.basename(path) for path in self._failing)),
            last_error=self._last_error if self._failing else None,
            last_error_at=self._last_error_at if self._failing else None,
        )

    def _wrote(self, path: str):
        self._written.add(path)
        self._last_write_at = self._clock()

    def record(self, results: list[TextDetectionTargetWithResult]):
        """Remember the boxes and the good readings of an OCR result list."""
        self._boxes = [
            _Box(r.name, r.result_state.name, (r.x(), r.y(), r.width(), r.height()))
            for r in results
        ]
        for result in results:
            if is_good_reading(result):
                self._latest[result.name] = _Reading(
                    result.result, result.result_state.name
                )

    def latest_text(self, box_name: str) -> str | None:
        reading = self._latest.get(box_name)
        return reading.text if reading else None

    def seconds_until_flush(self, min_interval: float) -> float:
        """How long until the next flush is allowed (0 if it is allowed now)."""
        if self._last_flush is None:
            return 0.0
        return max(0.0, self._last_flush + min_interval - self._clock())

    def flush(
        self,
        out_folder: str,
        append_method: int = APPEND_NONE,
        save_csv: bool = False,
        save_xml: bool = False,
    ):
        """Write every file whose content differs from what was last written, or
        that is missing."""
        if not out_folder or not self._boxes:
            return
        self._last_flush = self._clock()
        if out_folder != self._folder:
            self._folder = out_folder
            self._written.clear()
            self._failing.clear()
            self._last_write_at = None
        self._write_text_files(out_folder, append_method in (APPEND_TXT, APPEND_BOTH))
        if save_csv:
            self._write_csv(out_folder, append_method in (APPEND_CSV, APPEND_BOTH))
        if save_xml:
            self._write_xml(out_folder)

    # --- error reporting -------------------------------------------------------

    def _write_failed(self, path: str, error: Exception):
        self._last_error = f"{os.path.basename(path)}: {error}"
        self._last_error_at = self._clock()
        if path not in self._failing:
            self._failing.add(path)
            logger.error("Error writing to %s: %s", path, error)

    def _write_succeeded(self, path: str):
        if path in self._failing:
            self._failing.discard(path)
            logger.info("Writing to %s works again", path)

    # --- per-box .txt files ------------------------------------------------------

    def _write_text_files(self, out_folder: str, append: bool):
        if append != self._append_txt:
            # The append mode changed: compare with the files' current content.
            self._append_txt = append
            self._txt_written.clear()
        for box in self._boxes:
            reading = self._latest.get(box.name)
            if reading is None:
                continue
            path = os.path.join(out_folder, text_file_name(box.name))
            if not os.path.exists(path):
                self._txt_written.pop(path, None)
            elif path not in self._txt_written:
                # first write to this file in this session: compare with the disk
                self._txt_written[path] = (
                    _read_last_line(path) if append else _read_text(path)
                )
            if path in self._txt_written and self._txt_written[path] == reading.text:
                continue
            try:
                if append:
                    with open(path, "a", encoding="utf-8") as f:
                        f.write(reading.text + "\n")
                else:
                    write_text_atomic(path, reading.text)
            except OSError as e:
                self._write_failed(path, e)
                continue
            self._write_succeeded(path)
            self._wrote(path)
            self._txt_written[path] = reading.text

    # --- results.csv ----------------------------------------------------------------

    def _write_csv(self, out_folder: str, append: bool):
        path = os.path.join(out_folder, CSV_FILE_NAME)
        names = [box.name for box in self._boxes]
        try:
            if append:
                self._append_csv_row(path, names)
            else:
                self._overwrite_csv(path, names)
        except (OSError, csv.Error) as e:
            self._write_failed(path, e)
            return
        self._write_succeeded(path)

    def _values(self, names: list[str]) -> tuple[str, ...]:
        return tuple(self.latest_text(name) or "" for name in names)

    def _overwrite_csv(self, path: str, names: list[str]):
        values = self._values(names)
        snapshot = (tuple(names), values)
        if os.path.exists(path) and self._csv_written.get(path) == snapshot:
            return
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([CSV_TIMESTAMP_COLUMN, *names])
        writer.writerow([datetime.datetime.now().isoformat(), *values])
        write_text_atomic(path, output.getvalue(), newline="")
        self._wrote(path)
        self._csv_written[path] = snapshot
        self._csv_header[path] = [CSV_TIMESTAMP_COLUMN, *names]

    def _append_csv_row(self, path: str, names: list[str]):
        header = None
        if os.path.exists(path) and os.path.getsize(path) > 0:
            header = self._csv_header.get(path)
            if header is None:
                header = _read_csv_header(path)
            columns = header[1:] if header else []
            if (
                not header
                or header[0] != CSV_TIMESTAMP_COLUMN
                or sorted(columns) != sorted(names)
            ):
                # The boxes changed (or the file isn't ours): keep the existing
                # log under a new name and start a new file, so that every file
                # is a consistent table with a single header.
                rotated = _rotated_csv_path(path)
                os.replace(path, rotated)
                logger.info("The boxes changed: %s was renamed to %s", path, rotated)
                self._csv_written.pop(path, None)
                header = None
        # keep the column order of an existing file
        columns = header[1:] if header else names
        values = self._values(columns)
        if header is not None and self._csv_written.get(path) == values:
            return
        with open(path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if header is None:
                writer.writerow([CSV_TIMESTAMP_COLUMN, *columns])
            writer.writerow([datetime.datetime.now().isoformat(), *values])
        self._wrote(path)
        self._csv_header[path] = [CSV_TIMESTAMP_COLUMN, *columns]
        self._csv_written[path] = values

    # --- results.xml ----------------------------------------------------------------

    def _write_xml(self, out_folder: str):
        path = os.path.join(out_folder, XML_FILE_NAME)
        snapshot = tuple(
            (box.name, self.latest_text(box.name) or "", box.rect)
            for box in self._boxes
        )
        if os.path.exists(path) and self._xml_written.get(path) == snapshot:
            return

        root = ET.Element("data")
        for box in self._boxes:
            reading = self._latest.get(box.name)
            result = ET.SubElement(root, "result")
            ET.SubElement(result, "name").text = _xml_text(box.name)
            ET.SubElement(result, "text").text = _xml_text(
                reading.text if reading else ""
            )
            ET.SubElement(result, "state").text = (
                reading.state if reading else box.state
            )
            rect = ET.SubElement(result, "rect")
            for key, value in zip(("x", "y", "width", "height"), box.rect):
                ET.SubElement(rect, key).text = str(value)
        ET.indent(root)
        content = ET.tostring(root, encoding="unicode", xml_declaration=False)
        try:
            write_text_atomic(
                path, '<?xml version="1.0" encoding="UTF-8"?>\n' + content + "\n"
            )
        except OSError as e:
            self._write_failed(path, e)
            return
        self._write_succeeded(path)
        self._wrote(path)
        self._xml_written[path] = snapshot
