from PySide6.QtCore import QThread, Signal, Slot

import atexit
import ctypes
import math
import os
import platform
import sys
import time
import cv2
import threading

from base_video_capture import BaseVideoCapture
from camera_info import CameraInfo
from ndi import NDICapture
from screen_capture_source import ScreenCapture
from storage import (
    SETTINGS_FILE,
    TextDetectionTargetMemoryStorage,
    fetch_data,
    subscribe_to_data,
    unsubscribe_from_data,
)
from tesseract import TextDetector, global_binarization, render_binary_view
from text_detection_target import TextDetectionTargetWithResult
from sc_logging import logger
from frame_stabilizer import FrameStabilizer
from ocr_training_data import ocr_training_data_options

# "Detections / s" (detection_cadence): the default, and the lowest rate the
# capture thread accepts (one detection every 10 s); 0 or less is clamped to it.
DEFAULT_DETECTION_CADENCE = 5
MIN_DETECTION_CADENCE = 0.1
MAX_UPDATE_FRAME_INTERVAL_MS = 1000.0 / MIN_DETECTION_CADENCE

# Open and read timeouts for URL (network stream) sources, so that a stalled
# stream can't block the capture thread (and closing it) for FFmpeg's default
# 30 s per call.
URL_CAPTURE_TIMEOUT_MS = 5000
URL_CAPTURE_PARAMS = [
    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
    URL_CAPTURE_TIMEOUT_MS,
    cv2.CAP_PROP_READ_TIMEOUT_MSEC,
    URL_CAPTURE_TIMEOUT_MS,
]

FFMPEG_CAPTURE_OPTIONS_ENV = "OPENCV_FFMPEG_CAPTURE_OPTIONS"
DEFAULT_FFMPEG_CAPTURE_OPTIONS = "rtsp_transport;tcp"

# How long closing a source waits for its capture thread to stop before letting
# it finish in the background.
STOP_TIMEOUT_MS = 3000

# A frame processing error that repeats on every frame is reported at most this often.
ERROR_REPORT_INTERVAL_S = 5.0


def set_process_env(name: str, value: str | None):
    """Set (or with None, remove) an environment variable for this process,
    including for OpenCV's FFmpeg backend."""
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    if sys.platform == "win32":
        # OpenCV's FFmpeg plugin (opencv_videoio_ffmpeg*.dll) reads its options
        # with getenv() from msvcrt.dll, which keeps its own copy of the
        # environment that os.environ (the UCRT's) doesn't update.
        try:
            ctypes.cdll.msvcrt._putenv(f"{name}={value or ''}".encode())
        except (OSError, AttributeError):
            logger.debug("Unable to set %s for msvcrt", name, exc_info=True)


def ensure_ffmpeg_capture_options():
    """Use RTSP over TCP for URL sources: FFmpeg's UDP transport fails behind
    NAT, firewalls and VPNs. A user-provided OPENCV_FFMPEG_CAPTURE_OPTIONS is
    left alone."""
    if os.environ.get(FFMPEG_CAPTURE_OPTIONS_ENV) is not None:
        return
    set_process_env(FFMPEG_CAPTURE_OPTIONS_ENV, DEFAULT_FFMPEG_CAPTURE_OPTIONS)


def cadence_to_interval_ms(cadence) -> float:
    """The time between detections, in ms, for a detection_cadence in detections
    per second (clamped to at least MIN_DETECTION_CADENCE)."""
    try:
        cadence = float(cadence)
    except (TypeError, ValueError):
        cadence = DEFAULT_DETECTION_CADENCE
    if math.isnan(cadence):
        cadence = DEFAULT_DETECTION_CADENCE
    return 1000.0 / max(cadence, MIN_DETECTION_CADENCE)


def _clamp_interval_ms(interval_ms) -> float:
    try:
        interval_ms = float(interval_ms)
    except (TypeError, ValueError):
        return cadence_to_interval_ms(DEFAULT_DETECTION_CADENCE)
    if math.isnan(interval_ms):
        return cadence_to_interval_ms(DEFAULT_DETECTION_CADENCE)
    return min(max(interval_ms, 0.0), MAX_UPDATE_FRAME_INTERVAL_MS)


def _clamp_margin(value, limit: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(value, limit))


def crop_frame(frame, top, bottom, left, right):
    """Crop the given margins off the frame. The margins are clamped to the
    frame so at least one row and column remain, e.g. when a crop set for a
    larger source is applied to a smaller (or rotated) one."""
    height, width = frame.shape[:2]
    top = _clamp_margin(top, height - 1)
    bottom = _clamp_margin(bottom, height - 1 - top)
    left = _clamp_margin(left, width - 1)
    right = _clamp_margin(right, width - 1 - left)
    return frame[top : height - bottom, left : width - right]


def to_gray(frame):
    if frame.ndim == 2:
        return frame
    if frame.shape[2] == 4:
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def fourcc_code(fourcc) -> int | None:
    """The FOURCC int for a stored 4-character code, or None if it isn't one."""
    if not isinstance(fourcc, str) or len(fourcc) != 4 or fourcc == "NULL":
        return None
    return cv2.VideoWriter_fourcc(*fourcc)


def _positive(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(value) or value <= 0:
        return None
    return value


# Function to set the resolution
def set_resolution(cap, width, height):
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)


# Function to get the resolution
def get_resolution(cap):
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    return width, height


# Function to set the camera to the highest resolution
def set_camera_highest_resolution(cap):
    # List of common resolutions to try
    resolutions = [(1920, 1080), (1280, 720), (1024, 768), (800, 600), (640, 480)]

    # grab one frame to make sure the camera is initialized
    ret, _ = cap.read()
    if not ret:
        logger.warning("Error: camera not initialized")
        return

    # grab the current resolution
    width, height = get_resolution(cap)

    # If the current resolution is already the highest, return
    if width >= resolutions[0][0] and height >= resolutions[0][1]:
        logger.info(
            "Camera is already at the highest resolution: %d x %d", width, height
        )
        return

    # Try each resolution and select the highest one that works
    highest_res = resolutions[0]
    for resolution in resolutions:
        logger.debug("Trying camera resolution: %d x %d", resolution[0], resolution[1])
        set_resolution(cap, *resolution)
        test_width, test_height = get_resolution(cap)
        logger.debug("Found camera resolution: %d x %d", test_width, test_height)
        # if found resolution is within close range of the target resolution, use it
        if (
            abs(test_width - resolution[0]) < 100
            and abs(test_height - resolution[1]) < 100
        ):
            logger.debug(
                "Camera highest resolution set to: %d x %d", test_width, test_height
            )
            highest_res = (test_width, test_height)
            break

    # Set the highest resolution
    logger.info("Setting camera resolution to: %d x %d", highest_res[0], highest_res[1])
    set_resolution(cap, *highest_res)


class FrameCropAndRotation:
    def __init__(self):
        self.isCropSet = fetch_data(SETTINGS_FILE, "crop_mode", False)
        self.cropTop = fetch_data(SETTINGS_FILE, "top_crop", 0)
        self.cropBottom = fetch_data(SETTINGS_FILE, "bottom_crop", 0)
        self.cropLeft = fetch_data(SETTINGS_FILE, "left_crop", 0)
        self.cropRight = fetch_data(SETTINGS_FILE, "right_crop", 0)
        self.rotation = fetch_data(SETTINGS_FILE, "rotation", 0)
        self._subscriptions = [
            ("crop_mode", self.setCropMode),
            ("top_crop", self.setCropTop),
            ("bottom_crop", self.setCropBottom),
            ("left_crop", self.setCropLeft),
            ("right_crop", self.setCropRight),
            ("rotation", self.setRotation),
        ]
        for document_name, callback in self._subscriptions:
            subscribe_to_data(SETTINGS_FILE, document_name, callback)

    def close(self):
        """Stop following the crop and rotation settings."""
        for document_name, callback in self._subscriptions:
            unsubscribe_from_data(SETTINGS_FILE, document_name, callback)

    def setCropMode(self, crop_mode):
        self.isCropSet = crop_mode

    def setCropTop(self, crop_top):
        self.cropTop = crop_top

    def setCropBottom(self, crop_bottom):
        self.cropBottom = crop_bottom

    def setCropLeft(self, crop_left):
        self.cropLeft = crop_left

    def setCropRight(self, crop_right):
        self.cropRight = crop_right

    def setRotation(self, rotation):
        self.rotation = rotation


class OpenCVVideoCaptureWithSettings(BaseVideoCapture):
    """A cv2.VideoCapture shared by the capture thread (read) and the GUI thread
    (the Video Settings dialog), guarded by video_capture_mutex.

    With apply_video_settings (camera devices), the stored Video Settings are
    used when the device opens: its backend, then FOURCC, resolution and fps.
    When they change later (stored from the dialog, on the GUI thread) they are
    applied by the capture thread right before its next read(), so the GUI
    thread never reopens the device. release() stops following the settings.
    """

    def __init__(
        self,
        capture_id: int | str,
        capture_backend: int = cv2.CAP_ANY,
        params: list[int] | None = None,
        apply_video_settings: bool = False,
    ):
        super().__init__(capture_id, capture_backend)
        self.video_capture_mutex = threading.Lock()
        self.params = list(params) if params else []
        self.apply_video_settings = apply_video_settings
        self.default_backend = capture_backend
        self.backend = capture_backend
        self.fps = None
        self.width = None
        self.height = None
        self.fourcc = None
        self._reopen_requested = False
        self._apply_requested = False
        self._subscriptions = []
        if apply_video_settings:
            self.fps = fetch_data(SETTINGS_FILE, "fps", None)
            self.width = fetch_data(SETTINGS_FILE, "width", None)
            self.height = fetch_data(SETTINGS_FILE, "height", None)
            self.fourcc = fetch_data(SETTINGS_FILE, "fourcc", None)
            self.backend = self._effective_backend(
                fetch_data(SETTINGS_FILE, "backend", None)
            )
            self._subscriptions = [
                ("fps", self.setFps),
                ("width", self.setWidth),
                ("height", self.setHeight),
                ("fourcc", self.setFourcc),
                ("backend", self.setBackend),
            ]
            for document_name, callback in self._subscriptions:
                subscribe_to_data(SETTINGS_FILE, document_name, callback)
        with self.video_capture_mutex:
            self.video_capture = self._open()

    def _effective_backend(self, backend) -> int:
        # A stored backend of "Auto" (CAP_ANY) or none means the platform default.
        try:
            backend = int(backend)
        except (TypeError, ValueError):
            return self.default_backend
        return backend if backend != cv2.CAP_ANY else self.default_backend

    def _open(self):
        if self.params:
            capture = cv2.VideoCapture(self.capture_id, self.backend, self.params)
        else:
            capture = cv2.VideoCapture(self.capture_id, self.backend)
        if self.apply_video_settings and capture.isOpened():
            self._apply_settings(capture, opening=True)
        return capture

    def _apply_settings(self, capture, opening: bool):
        # FOURCC first: e.g. MJPG is what unlocks the high resolutions and frame
        # rates on many USB cameras.
        code = fourcc_code(self.fourcc)
        if code is not None:
            capture.set(cv2.CAP_PROP_FOURCC, code)
        width = _positive(self.width)
        height = _positive(self.height)
        if width is not None and height is not None:
            set_resolution(capture, int(width), int(height))
        elif opening:
            set_camera_highest_resolution(capture)
        fps = _positive(self.fps)
        if fps is not None:
            capture.set(cv2.CAP_PROP_FPS, fps)

    def _apply_pending_changes(self):
        # called by the reading thread with the mutex held
        if self._reopen_requested:
            self._reopen_requested = False
            self._apply_requested = False
            logger.info(
                "Reopening capture %s with backend %s", self.capture_id, self.backend
            )
            self.video_capture.release()
            self.video_capture = self._open()
        elif self._apply_requested:
            self._apply_requested = False
            self._apply_settings(self.video_capture, opening=False)

    def setFps(self, fps):
        self.fps = fps
        self._apply_requested = True

    def setWidth(self, width):
        self.width = width
        self._apply_requested = True

    def setHeight(self, height):
        self.height = height
        self._apply_requested = True

    def setFourcc(self, fourcc: str):
        self.fourcc = fourcc
        self._apply_requested = True

    def setBackend(self, backend):
        backend = self._effective_backend(backend)
        if backend == self.backend:
            return
        self.backend = backend
        self._reopen_requested = True

    def isOpened(self):
        with self.video_capture_mutex:
            return self.video_capture.isOpened()

    def read(self):
        with self.video_capture_mutex:
            self._apply_pending_changes()
            return self.video_capture.read()

    def release(self):
        for document_name, callback in self._subscriptions:
            unsubscribe_from_data(SETTINGS_FILE, document_name, callback)
        self._subscriptions = []
        with self.video_capture_mutex:
            self.video_capture.release()

    def set(self, propId, value):
        with self.video_capture_mutex:
            self.video_capture.set(propId, value)

    def get(self, propId):
        with self.video_capture_mutex:
            return self.video_capture.get(propId)

    def run_locked(self, function):
        """Call function(cv2.VideoCapture) with the mutex held, e.g. to get or
        set many properties while waiting for the reading thread only once."""
        with self.video_capture_mutex:
            return function(self.video_capture)


# Capture threads that were started and haven't finished. Holding them here
# keeps a running QThread from being garbage collected (which aborts the
# process) when its view lets go of it without waiting for it to stop.
_active_threads: set["TimerThread"] = set()


def _stop_active_threads_at_exit():
    threads = list(_active_threads)
    for thread in threads:
        thread.should_stop = True
    deadline = time.monotonic() + STOP_TIMEOUT_MS / 1000.0
    for thread in threads:
        remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
        if not thread.wait(remaining_ms):
            logger.warning("Camera thread is still running at exit")


atexit.register(_stop_active_threads_at_exit)


class TimerThread(QThread):
    update_signal = Signal(object)
    update_error = Signal(object)
    ocr_result_signal = Signal(list)

    def __init__(
        self,
        camera_info: CameraInfo,
        detectionTargetsStorage: TextDetectionTargetMemoryStorage,
    ):
        super().__init__()
        self.camera_info = camera_info
        self.homography = None
        self.detectionTargetsStorage = detectionTargetsStorage
        self.textDetector = TextDetector()  # initialize tesseract
        self.show_binary = False
        self.retry_count = 0
        self.retry_count_max = 50
        self.retry_high_water_mark = 25
        self.stabilizationEnabled = False
        self.framestabilizer = FrameStabilizer()
        self.video_capture: BaseVideoCapture | None = None
        self.should_stop = False
        # monotonic clock (seconds); replaceable in tests
        self._clock = time.monotonic
        self.frame_interval = 30
        self.update_frame_interval = cadence_to_interval_ms(
            fetch_data(SETTINGS_FILE, "detection_cadence", DEFAULT_DETECTION_CADENCE)
        )
        subscribe_to_data(
            SETTINGS_FILE, "detection_cadence", self.setUpdateFrameInterval
        )
        self.preview_frame_interval = 1000
        self.fps = 1000 / self.frame_interval  # frames per second
        self.pps = 1000 / self.preview_frame_interval  # previews per second
        self.ups = 1000 / max(self.update_frame_interval, 1)  # updates per second
        self.fps_alpha = 0.1  # Smoothing factor
        self.updateOnChange = True
        self.crop = FrameCropAndRotation()
        self.speed = 1
        # (width, height) of the last frame read from the source
        self.frame_size = (0, 0)
        self.last_frame_timestamp = None
        self.last_update_timestamp = None
        self.last_emit_time = None
        self._iteration_start = None
        self._last_error_report = None
        self.finished.connect(self._on_finished)

    @property
    def update_frame_interval(self) -> float:
        """Time between OCR passes in ms (1000 / detection_cadence)."""
        return self._update_frame_interval

    @update_frame_interval.setter
    def update_frame_interval(self, interval_ms):
        # also set directly by the main window when the cadence slider moves
        self._update_frame_interval = _clamp_interval_ms(interval_ms)

    def getSpeed(self):
        return self.speed

    def setSpeed(self, speed):
        self.speed = speed

    def setUpdateFrameInterval(self, cadence):
        self.update_frame_interval = cadence_to_interval_ms(cadence)

    def start(self, *args, **kwargs):
        _active_threads.add(self)
        super().start(*args, **kwargs)

    @Slot()
    def _on_finished(self):
        # Queued to the thread that owns this object (the GUI thread) after
        # run() returned.
        self.wait()
        _active_threads.discard(self)

    def stop(self, timeout_ms: int = STOP_TIMEOUT_MS) -> bool:
        """Ask the thread to stop and wait up to timeout_ms for it. Returns False
        if it is still busy (e.g. blocked reading a stream); it then finishes in
        the background."""
        self.should_stop = True
        if self.wait(int(timeout_ms)):
            _active_threads.discard(self)
            return True
        logger.warning(
            "Camera thread for '%s' did not stop within %d ms; it will finish in "
            "the background",
            self.camera_info.description,
            timeout_ms,
        )
        return False

    def cleanup(self):
        """Stop following settings changes. Safe to call more than once, from
        any thread."""
        unsubscribe_from_data(
            SETTINGS_FILE, "detection_cadence", self.setUpdateFrameInterval
        )
        self.crop.close()

    def _create_video_capture(self) -> BaseVideoCapture:
        camera_type = self.camera_info.type
        if camera_type == CameraInfo.CameraType.NDI:
            return NDICapture(self.camera_info.uuid)
        if camera_type == CameraInfo.CameraType.SCREEN_CAPTURE:
            return ScreenCapture(self.camera_info.id)
        if camera_type == CameraInfo.CameraType.URL:
            url = str(self.camera_info.id).strip()
            ensure_ffmpeg_capture_options()
            return OpenCVVideoCaptureWithSettings(
                url, cv2.CAP_FFMPEG, params=URL_CAPTURE_PARAMS
            )
        if camera_type == CameraInfo.CameraType.FILE:
            return OpenCVVideoCaptureWithSettings(self.camera_info.id)
        # a camera device: on windows use the dshow backend by default
        backend = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY
        return OpenCVVideoCaptureWithSettings(
            self.camera_info.id, backend, apply_video_settings=True
        )

    def connect_video_capture(self) -> bool:
        try:
            self.video_capture = self._create_video_capture()
        except Exception:
            logger.exception("Error: unable to open the video source")
            self.video_capture = None
            self.update_error.emit("Error: Unable to play video stream")
            return False

        if self.retry_count != self.retry_high_water_mark:
            # at the high water mark this is a reconnect
            self.retry_count = 0

        if not self.video_capture.isOpened():
            logger.warning(
                "Error: unable to open camera. Check if the camera is connected."
            )
            self.update_error.emit("Error: Unable to play video stream")
            return False

        return True

    def _release_capture(self):
        capture, self.video_capture = self.video_capture, None
        if capture is not None:
            try:
                capture.release()
            except Exception:
                logger.exception("Error releasing the video capture")

    def run(self):
        description_ascii = (
            self.camera_info.description.encode("ascii", errors="ignore").decode()
            if isinstance(self.camera_info.description, str)
            else str(self.camera_info.description)
        )
        logger.info("Starting camera thread for: '%s'", description_ascii)

        try:
            if not self.connect_video_capture():
                self.should_stop = True
                return
            while not self.should_stop:
                self.run_once()
        except Exception:
            logger.exception("Camera thread failed")
            self.update_error.emit("Error: Unable to play video stream")
        finally:
            self._release_capture()
            self.cleanup()
            logger.info("Camera thread stopped")

    def run_once(self):
        """One iteration of the capture loop: read a frame (reconnecting or
        giving up after repeated failures) and process it."""
        self._iteration_start = self._clock()
        if self.video_capture is None:
            logger.warning("Error: video capture is None")
            self.should_stop = True
            return

        if self.retry_count == self.retry_high_water_mark:
            logger.warning("Error: retry high water mark exceeded")
            # reconnect the video cap
            self._release_capture()
            if not self.connect_video_capture():
                self.should_stop = True
                return
            self.sleep_fps_target()
            self.retry_count += 1
            return
        if self.retry_count > self.retry_count_max:
            logger.warning("Error: retry count exceeded")
            self.should_stop = True
            self.update_error.emit("Error: Unable to play video stream")
            return

        # Read the frame from the camera
        ret, frame_rgb = None, None
        try:
            ret, frame_rgb = self.video_capture.read()
        except Exception as e:
            self.retry_count += 1
            logger.exception(
                "Error: unable to read frame from camera (retry count: %d), exception %s",
                self.retry_count,
                e,
            )
            self.sleep_fps_target()
            return

        if self.camera_info.type == CameraInfo.CameraType.FILE:
            if self.speed != 1:
                self.video_capture.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    self.video_capture.get(cv2.CAP_PROP_POS_FRAMES) + self.speed,
                )

        if not ret or frame_rgb is None or frame_rgb.size == 0:
            self.retry_count += 1
            if self.camera_info.type == CameraInfo.CameraType.FILE:
                logger.debug("Restarting video file")
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.sleep_fps_target()
                return
            logger.warning(
                "Error: unable to read frame from camera, return value False (retry count: %d)",
                self.retry_count,
            )
            self.sleep_fps_target()
            return

        self.retry_count = 0  # good frame, reset the retry count
        try:
            self.process_frame(frame_rgb)
        except Exception as e:
            self._report_processing_error(e)
        self.sleep_fps_target()

    def _report_processing_error(self, error):
        # Called from an except block. Keeps the thread (and the capture) alive;
        # an error that repeats on every frame is reported once in a while.
        now = self._clock()
        if (
            self._last_error_report is not None
            and now - self._last_error_report < ERROR_REPORT_INTERVAL_S
        ):
            return
        self._last_error_report = now
        logger.exception("Error: unable to process the video frame")
        self.update_error.emit(f"Error: unable to process the video frame: {error}")

    def process_frame(self, frame_rgb):
        """Process a frame read from the source: on the detection cadence run
        OCR on it, and about once a second emit it as the preview. The two are
        independent, so the preview (and with it the first-frame signal that
        enables the UI) comes at any detection cadence."""
        now = self._clock()
        self.frame_size = (frame_rgb.shape[1], frame_rgb.shape[0])

        # calculate the frame rate
        if self.last_frame_timestamp is not None:
            time_diff_ms = (now - self.last_frame_timestamp) * 1000.0
            if time_diff_ms > 0:
                self.fps = (
                    self.fps_alpha * (1000 / time_diff_ms)
                    + (1.0 - self.fps_alpha) * self.fps
                )
        self.last_frame_timestamp = now

        # check that enough time has passed since the last update and preview
        update_due = (
            self.last_update_timestamp is None
            or (now - self.last_update_timestamp) * 1000.0 >= self.update_frame_interval
        )
        preview_due = (
            self.last_emit_time is None
            or (now - self.last_emit_time) * 1000.0 >= self.preview_frame_interval
        )
        if not update_due and not preview_due:
            # dump this frame since not enough time has passed
            return

        frame_rgb = self.transform_frame(frame_rgb)
        show_binary = self.show_binary
        save_training_data = ocr_training_data_options.save_ocr_training_data
        targets = None
        gray = None
        display = None

        if update_due:
            if self.last_update_timestamp is not None:
                time_diff_ms = (now - self.last_update_timestamp) * 1000.0
                if time_diff_ms > 0:
                    self.ups = (
                        self.fps_alpha * (1000 / time_diff_ms)
                        + (1.0 - self.fps_alpha) * self.ups
                    )
            self.last_update_timestamp = now

            # One snapshot of the boxes per frame: the GUI thread may add or
            # remove boxes while the OCR runs.
            targets = self._snapshot_targets()
            if targets:
                gray = to_gray(frame_rgb)
                binary = None
                if (show_binary and preview_due) or save_training_data:
                    binary = global_binarization(gray)
                    display = binary.copy()
                try:
                    # binary=None: the OCR computes the global binarization
                    # only if a box uses it
                    texts = self.textDetector.detect_multi_text(
                        binary, gray, targets, display=display
                    )
                    self._publish_results(targets, texts, display, gray)
                except Exception as e:
                    # still emit the preview below
                    self._report_processing_error(e)

        if preview_due:
            if self.last_emit_time is not None:
                time_diff_ms = (now - self.last_emit_time) * 1000.0
                if time_diff_ms > 0:
                    self.pps = (
                        self.fps_alpha * (1000 / time_diff_ms)
                        + (1.0 - self.fps_alpha) * self.pps
                    )
            self.last_emit_time = now
            if show_binary:
                if display is None:
                    if gray is None:
                        gray = to_gray(frame_rgb)
                    if targets is None:
                        targets = self._snapshot_targets()
                    display = render_binary_view(
                        global_binarization(gray), gray, targets
                    )
                self.update_signal.emit(display)
            else:
                self.update_signal.emit(frame_rgb)

    def _snapshot_targets(self):
        if self.detectionTargetsStorage is None:
            return []
        return list(self.detectionTargetsStorage.get_data())

    def _publish_results(self, targets, texts, display, gray):
        if len(texts) == 0 or len(targets) != len(texts):
            return
        # augment the text detection targets with the results
        results = []
        for target, result in zip(targets, texts):
            if self.updateOnChange:
                if target.last_text is not None and target.last_text == result.text:
                    result.state = (
                        TextDetectionTargetWithResult.ResultState.SameNoChange
                    )

            results.append(
                TextDetectionTargetWithResult(
                    target,
                    result.text,
                    result.state,
                    result.rect,
                    result.extra,
                )
            )
            target.last_text = result.text

        # emit the results
        self.ocr_result_signal.emit(results)

        if ocr_training_data_options.save_ocr_training_data and display is not None:
            # save the image and the text
            ocr_training_data_options.save_ocr_results_to_folder(display, gray, results)

    def transform_frame(self, frame_rgb):
        """Apply the rotation, crop, stabilization and four-corner homography."""
        crop = self.crop
        rotation = crop.rotation
        # apply rotation if set
        if rotation != 0:
            # use cv2.rotate to rotate the frame
            rotateCode = (
                cv2.ROTATE_90_CLOCKWISE
                if rotation == 90
                else (
                    cv2.ROTATE_90_COUNTERCLOCKWISE
                    if rotation == 270
                    else cv2.ROTATE_180
                )
            )
            frame_rgb = cv2.rotate(frame_rgb, rotateCode)

        # apply top-level crop if set
        if crop.isCropSet:
            frame_rgb = crop_frame(
                frame_rgb, crop.cropTop, crop.cropBottom, crop.cropLeft, crop.cropRight
            )

        # Stabilize the frame
        if self.stabilizationEnabled:
            frame_rgb = self.framestabilizer.stabilize_frame(frame_rgb)

        # Apply the homography to the frame
        homography = self.homography
        if homography is not None:
            frame_rgb = cv2.warpPerspective(
                frame_rgb, homography, (frame_rgb.shape[1], frame_rgb.shape[0])
            )
        return frame_rgb

    def sleep_fps_target(self):
        # cap the loop at about 1000 / frame_interval iterations per second
        if self._iteration_start is None:
            return
        time_diff_ms = (self._clock() - self._iteration_start) * 1000.0
        if time_diff_ms < self.frame_interval:
            time.sleep((self.frame_interval - time_diff_ms) / 1000.0)

    def toggleStabilization(self, state):
        self.stabilizationEnabled = state
        if not state:
            self.framestabilizer.reset()
