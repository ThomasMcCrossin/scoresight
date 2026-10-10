"""CameraView / ImageViewer (src/camera_view.py, src/source_view.py): stopping
the capture thread, teardown and the four-corner homography."""

import threading
import time

import numpy as np
import pytest

pytest.importorskip("tesserocr")  # the views run the OCR pipeline

import camera_thread  # noqa: E402
import camera_view  # noqa: E402
import storage  # noqa: E402
from camera_info import CameraInfo  # noqa: E402
from camera_view import CameraView, compute_four_corner_homography  # noqa: E402
from storage import fetch_data, store_data  # noqa: E402

pytestmark = pytest.mark.qt


# --- four-corner homography ---------------------------------------------------------------

VALID_QUAD = [(100, 100), (500, 120), (480, 400), (90, 380)]


def test_valid_four_corners_give_a_homography():
    homography = compute_four_corner_homography(VALID_QUAD)
    assert homography is not None
    assert abs(np.linalg.det(homography)) > 1e-3


@pytest.mark.parametrize(
    "corners",
    [
        None,
        [],
        VALID_QUAD[:3],
        # the same corner clicked twice
        [(100, 100), (100, 100), (480, 400), (90, 380)],
        # four points along one edge
        [(100, 100), (200, 100), (300, 100), (400, 100)],
        # nearly collinear: a diagonal sliver that would be stretched to a square
        [(100, 100), (102, 98), (500, 500), (498, 502)],
        # self-intersecting (corners out of order)
        [(100, 100), (480, 400), (500, 120), (90, 380)],
        # concave
        [(100, 100), (500, 100), (300, 120), (100, 400)],
        # tiny
        [(10, 10), (14, 10), (14, 14), (10, 14)],
        [(0, 0), (1, float("nan")), (2, 2), (3, 3)],
    ],
)
def test_unusable_four_corners_are_rejected(corners):
    assert compute_four_corner_homography(corners) is None


# --- stopping the capture thread ----------------------------------------------------------


class BlockingCapture:
    """A source whose read() blocks (like a stalled network stream) until
    `unblock` is set."""

    def __init__(self):
        self.reading = threading.Event()
        self.unblock = threading.Event()
        self.released = False

    def isOpened(self):
        return True

    def read(self):
        self.reading.set()
        self.unblock.wait(10)
        return True, np.zeros((48, 64, 3), np.uint8)

    def get(self, prop):
        return 0.0

    def set(self, prop, value):
        pass

    def release(self):
        self.released = True


class FrameCapture(BlockingCapture):
    def read(self):
        time.sleep(0.01)
        return True, np.full((48, 64, 3), 200, np.uint8)


@pytest.fixture
def capture_factory(monkeypatch):
    """Make the views' capture threads use the given capture object."""
    captures = []

    def install(capture):
        captures.append(capture)
        monkeypatch.setattr(
            camera_thread.TimerThread, "_create_video_capture", lambda self: capture
        )
        return capture

    yield install
    for capture in captures:
        capture.unblock.set()


def file_source(name="stub"):
    return CameraInfo(name, name, name, CameraInfo.CameraType.FILE)


def test_close_does_not_wait_forever_for_a_blocked_capture(
    qtbot, monkeypatch, memory_storage, capture_factory
):
    monkeypatch.setattr(camera_view, "STOP_TIMEOUT_MS", 200)
    capture = capture_factory(BlockingCapture())
    view = CameraView(file_source(), memory_storage)
    thread = view.timerThread
    assert capture.reading.wait(5)

    started = time.monotonic()
    view.close()
    assert time.monotonic() - started < 2
    assert view.timerThread is None
    # the thread is kept alive until it finishes, and no longer reaches the UI
    assert thread.isRunning() and thread in camera_thread._active_threads
    assert storage.data_subscribers == {}

    capture.unblock.set()
    qtbot.waitUntil(lambda: thread not in camera_thread._active_threads, timeout=5000)
    assert capture.released


def test_close_stops_a_running_capture(qtbot, memory_storage, capture_factory):
    capture = capture_factory(FrameCapture())
    view = CameraView(file_source(), memory_storage)
    with qtbot.waitSignal(view.first_frame_received_signal, timeout=5000):
        pass
    thread = view.timerThread
    view.close()
    assert thread.isFinished()
    assert capture.released
    assert thread not in camera_thread._active_threads
    assert storage.data_subscribers == {}


def test_first_frame_uses_the_threads_frame_size(
    qtbot, memory_storage, capture_factory
):
    capture_factory(FrameCapture())
    view = CameraView(file_source(), memory_storage)
    try:
        with qtbot.waitSignal(view.first_frame_received_signal, timeout=5000):
            pass
        assert (view.camera_width, view.camera_height) == (64, 48)
    finally:
        view.close()


# --- ImageViewer -----------------------------------------------------------------------------


def make_viewer(memory_storage, applied=None):
    from source_view import ImageViewer

    return ImageViewer(
        file_source(),
        applied.append if applied is not None else (lambda corners: None),
        memory_storage,
        lambda name: None,
    )


def test_closed_viewer_is_disconnected(qtbot, memory_storage, capture_factory):
    from PySide6.QtCore import QMetaMethod

    capture_factory(FrameCapture())
    viewer = make_viewer(memory_storage)
    data_changed = QMetaMethod.fromSignal(memory_storage.data_changed)
    assert memory_storage.isSignalConnected(data_changed)
    viewer.close()
    assert not memory_storage.isSignalConnected(data_changed)
    assert storage.data_subscribers == {}


def test_invalid_stored_four_corners_are_dropped(
    qtbot, memory_storage, capture_factory
):
    capture_factory(FrameCapture())
    store_data(
        "scoresight.json",
        "four_corners",
        [(100, 100), (100, 100), (480, 400), (90, 380)],
    )
    applied = []
    viewer = make_viewer(memory_storage, applied)
    try:
        assert viewer.timerThread.homography is None
        assert applied == []
        assert fetch_data("scoresight.json", "four_corners") is None
    finally:
        viewer.close()


def test_valid_stored_four_corners_are_applied(qtbot, memory_storage, capture_factory):
    capture_factory(FrameCapture())
    store_data("scoresight.json", "four_corners", VALID_QUAD)
    applied = []
    viewer = make_viewer(memory_storage, applied)
    try:
        assert viewer.timerThread.homography is not None
        assert len(applied) == 1
    finally:
        viewer.close()


def click(viewer, x, y):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    position = QPointF(x, y)
    viewer.mousePressEvent(
        QMouseEvent(
            QEvent.Type.MouseButtonPress,
            position,
            position,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )


def test_an_invalid_four_corner_selection_is_not_a_source_error(
    qtbot, memory_storage, capture_factory
):
    # error_signal makes the main window disable the view tools (with the
    # four-corner button) until the source is reopened
    capture_factory(FrameCapture())
    viewer = make_viewer(memory_storage)
    errors = []
    viewer.error_signal.connect(errors.append)
    try:
        with qtbot.waitSignal(viewer.first_frame_received_signal, timeout=5000):
            pass
        viewer.toggleFourCorner(True)
        # the same corner clicked twice
        for x, y in [(50, 50), (50, 50), (400, 300), (40, 290)]:
            click(viewer, x, y)
        assert "Invalid four-corner selection" in viewer.error_text.toPlainText()
        assert errors == []
        # the selection starts over
        assert viewer.fourCornerSelectionMode
        assert viewer.fourCorners == []
        assert viewer.timerThread.homography is None

        for x, y in [(50, 50), (400, 60), (390, 300), (40, 290)]:
            click(viewer, x, y)
        assert viewer.timerThread.homography is not None
        assert viewer.error_text is None
        assert errors == []
    finally:
        viewer.close()


def test_a_frame_processing_error_is_shown_but_not_a_source_error(
    qtbot, memory_storage, capture_factory
):
    capture_factory(FrameCapture())
    view = CameraView(file_source(), memory_storage)
    errors = []
    view.error_signal.connect(errors.append)
    try:
        view.timerThread.processing_error.emit("Error: unable to process the frame")
        assert "unable to process" in view.error_text.toPlainText()
        assert errors == []
        # a source error is still reported
        view.timerThread.update_error.emit("Error: Unable to play video stream")
        assert errors == ["Error: Unable to play video stream"]
    finally:
        view.close()
