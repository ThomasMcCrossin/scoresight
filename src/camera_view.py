from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtCore import Signal

import warnings

import numpy as np
import cv2

from camera_info import CameraInfo
from storage import (
    TextDetectionTargetMemoryStorage,
    subscribe_to_data,
    unsubscribe_from_data,
)
from sc_logging import logger
from camera_thread import STOP_TIMEOUT_MS, TimerThread

# A four-corner selection must cover at least this many square pixels.
MIN_FOUR_CORNER_AREA = 100.0


def compute_four_corner_homography(corners) -> np.ndarray | None:
    """The homography that maps the quad given by four (x, y) corners (in
    clockwise order, starting top-left) onto its bounding rectangle, or None if
    the corners don't form a usable quad: repeated or collinear points, a
    self-intersecting or concave shape, or a tiny area would make every frame
    garbage."""
    if corners is None or len(corners) != 4:
        return None
    try:
        corners_as_array = np.array(corners, dtype=np.float32).reshape(4, 2)
    except (TypeError, ValueError):
        return None
    if not np.all(np.isfinite(corners_as_array)):
        return None
    if not cv2.isContourConvex(corners_as_array):
        return None
    # Calculate bounding rectangle
    x, y, w, h = cv2.boundingRect(corners_as_array)
    area = abs(cv2.contourArea(corners_as_array))
    # a sliver (nearly collinear points) would be stretched to a whole rectangle
    if area < MIN_FOUR_CORNER_AREA or area < 0.1 * w * h:
        return None
    # Destination points (corners of the bounding rectangle)
    dst_points = np.array(
        [[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.float32
    )
    # calculate the homography from the corners to the rect
    homography, _ = cv2.findHomography(corners_as_array, dst_points)
    if homography is None or not np.all(np.isfinite(homography)):
        return None
    if abs(np.linalg.det(homography)) < 1e-6:
        return None
    return homography


class CameraView(QGraphicsView):
    first_frame_received_signal = Signal()
    error_signal = Signal(str)

    def __init__(
        self,
        camera_index: CameraInfo,
        detectionTargetsStorage: TextDetectionTargetMemoryStorage | None = None,
        start: bool = True,
    ):
        """start=False leaves the capture thread stopped until startCapture(),
        so that a caller can connect to its signals first: a reading the thread
        emits before a slot is connected never reaches that slot."""
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.camera_info = camera_index
        self.timerThread = TimerThread(camera_index, detectionTargetsStorage)
        self.timerThread.update_signal.connect(self.update_pixmap)
        self.timerThread.update_error.connect(self.error_event)
        self.timerThread.processing_error.connect(self.show_error_text)
        self._capture_started = False
        self.scenePixmapItem = None
        self.detectionTargetsStorage = detectionTargetsStorage
        self.firstFrameReceived = False
        self.fps_text = None
        self.error_text = None
        self.showOSD = True
        self.camera_width = 0
        self.camera_height = 0
        subscribe_to_data("scoresight.json", "video_settings", self.resetFrame)
        if start:
            self.startCapture()

    def startCapture(self):
        """Start the capture thread (once)."""
        if self.timerThread is None or self._capture_started:
            return
        self._capture_started = True
        self.timerThread.start()

    def resetFrame(self, data):
        self.firstFrameReceived = False

    def getCameraCapture(self):
        if self.timerThread is None:
            return None
        return self.timerThread.video_capture

    def getCameraInfo(self):
        return self.camera_info

    def setUpdateOnChange(self, updateOnChange):
        if self.timerThread is not None:
            self.timerThread.updateOnChange = updateOnChange

    def toggleOSD(self, state):
        self.showOSD = state
        if self.fps_text is not None:
            self.fps_text.setVisible(state)

    def update_pixmap(self, frame):
        if self.timerThread is None:
            return

        # check if frame is not contiguous
        if not frame.flags["C_CONTIGUOUS"]:
            frame = np.ascontiguousarray(frame)

        # Create a QImage from the frame data
        image = QImage(
            frame.data,
            frame.shape[1],
            frame.shape[0],
            frame.strides[0],
            (
                QImage.Format.Format_Grayscale8
                if frame.ndim == 2
                else (
                    QImage.Format.Format_BGR888
                    if frame.shape[2] == 3
                    else QImage.Format.Format_RGBA8888
                )
            ),
        )

        # Create a QPixmap from the QImage
        pixmap = QPixmap.fromImage(image)

        if self.scenePixmapItem is None:
            self.scenePixmapItem = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.scenePixmapItem)
            self.scenePixmapItem.setZValue(0)
            self.fitInView(self.scenePixmapItem, Qt.AspectRatioMode.KeepAspectRatio)
        else:
            refit = False
            # check if the pixmap is the same size as the current one
            if self.scenePixmapItem.pixmap().size() != pixmap.size():
                logger.info(f"scene size: {self.scene.sceneRect()}")
                refit = True
            self.scenePixmapItem.setPixmap(pixmap)
            if refit:
                self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
                logger.info(f"scene size: {self.scene.sceneRect()}")
                logger.info(f"Refitting view to new pixmap size: {pixmap.size()}")
                self.fitInView(self.scenePixmapItem, Qt.AspectRatioMode.KeepAspectRatio)
                self.centerOn(self.scenePixmapItem)

        # the source's resolution, as read by the capture thread (asking the
        # capture would wait for its current read)
        self.camera_width, self.camera_height = self.timerThread.frame_size

        if not self.firstFrameReceived:
            self.firstFrameReceived = True
            self.first_frame_received_signal.emit()

        # update the fps text
        fps_text = f"Frames/s: {self.timerThread.fps:.2f}\nUpdates/s: {self.timerThread.ups:.2f}\nPreviews/s: {self.timerThread.pps:.2f}\nResolution: {int(self.camera_width)}x{int(self.camera_height)}"
        if self.fps_text is None:
            self.fps_text = self.scene.addText(fps_text)
            self.fps_text.setPos(0, 0)
            self.fps_text.setZValue(2)
            self.fps_text.setDefaultTextColor(Qt.GlobalColor.white)
            self.fps_text.setVisible(self.showOSD)
        else:
            self.fps_text.setPlainText(fps_text)
        # scale the text according to the view size so its always the same size
        self.fps_text.setScale(0.0015 * self.scenePixmapItem.boundingRect().width())

    def show_error_text(self, error):
        """Show an error message at the bottom of the view (None clears it),
        without reporting it through error_signal: for messages that don't mean
        the source failed, e.g. an invalid four-corner selection or an error
        processing a frame."""
        if self.error_text is not None:
            self.scene.removeItem(self.error_text)
            self.error_text = None
        if error is not None:
            # add the error to the scene
            self.error_text = self.scene.addText(f"⚠️ {error}")
            self.error_text.setDefaultTextColor(Qt.GlobalColor.red)
            self.error_text.setScale(0.004 * self.width())
            # diplay error on the bottom of the video view
            self.error_text.setPos(
                0, self.height() - self.error_text.boundingRect().height() - 10
            )

    def error_event(self, error):
        """A source error (e.g. it can't be played): shown in the view and
        reported through error_signal, which disables the main window's view
        tools."""
        self.show_error_text(error)
        if error is not None:
            logger.error("Error: %s", error)
            self.error_signal.emit(error)

    def setFourCornersForHomography(self, corners: list[tuple[int]]) -> bool:
        """Warp the frames so the quad given by four corners becomes a rectangle.
        Returns False (and turns the warp off) if corners is None or isn't a
        usable quad."""
        homography = None
        if corners is not None and len(corners) == 4:
            homography = compute_four_corner_homography(corners)
            if homography is None:
                logger.warning("Ignoring an invalid four-corner selection: %s", corners)
        if self.timerThread is not None:
            self.timerThread.homography = homography
        return homography is not None

    def stopCapture(self):
        """Stop the capture thread and disconnect from it and from the settings.
        Waits up to STOP_TIMEOUT_MS; a thread still blocked on its source after
        that finishes in the background, disconnected from the UI."""
        thread = self.timerThread
        if thread is None:
            return
        self.timerThread = None
        unsubscribe_from_data("scoresight.json", "video_settings", self.resetFrame)
        # nothing a stopping thread still emits may reach the UI
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            for signal in (
                thread.update_signal,
                thread.update_error,
                thread.processing_error,
                thread.ocr_result_signal,
            ):
                try:
                    signal.disconnect()
                except (RuntimeError, TypeError):
                    pass
        thread.cleanup()
        thread.stop(STOP_TIMEOUT_MS)

    def closeEvent(self, event):
        logger.debug("Close")
        self.stopCapture()

        # Call the base class closeEvent method
        super().closeEvent(event)
