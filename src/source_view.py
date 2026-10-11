import math
from PySide6.QtCore import QCoreApplication, QPointF, QRectF, QSizeF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QKeyEvent, QMouseEvent, QPen, QPolygonF
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPolygonItem,
)

from camera_info import CameraInfo
from camera_view import CameraView, compute_four_corner_homography
from storage import (
    TextDetectionTargetMemoryStorage,
    fetch_data,
    remove_data,
    store_data,
    subscribe_to_data,
    unsubscribe_from_data,
)
from text_detection_target import TextDetectionTarget, TextDetectionTargetWithResult
from sc_logging import logger
from resizable_rect import ResizableRectWithNameTypeAndResult, place_label

# Zoom steps (Ctrl+scroll, Ctrl+= and Ctrl+-) and limits, in screen pixels per
# picture pixel; a picture fitted to the viewer may be outside the limits.
WHEEL_ZOOM_FACTOR = 1.05
KEY_ZOOM_FACTOR = 1.25
MIN_ZOOM = 0.33
MAX_ZOOM = 4.0
# The arrow keys move the selected box by this many picture pixels (with
# Shift: NUDGE_LARGE_PX).
NUDGE_PX = 1
NUDGE_LARGE_PX = 10
# A four-corner point on screen, in pixels
CORNER_MARKER_PX = 10
CORNER_COLOR = QColor("#FF3B30")

_NUDGE_KEYS = {
    Qt.Key.Key_Left: (-1, 0),
    Qt.Key.Key_Right: (1, 0),
    Qt.Key.Key_Up: (0, -1),
    Qt.Key.Key_Down: (0, 1),
}


def sort_points_clockwise(points: list[QGraphicsItem]) -> list[QGraphicsItem]:
    # Calculate the center point
    center_x = sum(point.x() for point in points) / len(points)
    center_y = sum(point.y() for point in points) / len(points)
    center = QPointF(center_x, center_y)

    # Define a function to calculate the angle between a point and the center
    def angle_from_center(point):
        return math.atan2(point.y() - center.y(), point.x() - center.x())

    # Sort the points based on their angles
    sorted_points = sorted(points, key=angle_from_center)

    # Rotate the list so that the top-left point comes first
    top_left = min(sorted_points, key=lambda p: p.x() + p.y())
    while sorted_points[0] != top_left:
        sorted_points = sorted_points[1:] + [sorted_points[0]]

    return sorted_points


def nudged_rect(rect: QRectF, dx: float, dy: float, bounds: QRectF) -> QRectF:
    """rect moved by (dx, dy), kept inside bounds when it fits there (a box
    larger than the picture stays where it is on that axis)."""
    moved = rect.translated(dx, dy)
    if bounds.isValid():
        if rect.width() <= bounds.width():
            moved.moveLeft(
                min(max(moved.left(), bounds.left()), bounds.right() - rect.width())
            )
        else:
            moved.moveLeft(rect.left())
        if rect.height() <= bounds.height():
            moved.moveTop(
                min(max(moved.top(), bounds.top()), bounds.bottom() - rect.height())
            )
        else:
            moved.moveTop(rect.top())
    return moved


class ImageViewer(CameraView):
    # the four-corner picking started, got a corner or ended, or the
    # correction changed
    four_corner_changed = Signal()

    def __init__(
        self,
        camera_index: CameraInfo,
        fourCornersAppliedCallback: callable,
        detectionTargetsStorage: TextDetectionTargetMemoryStorage | None,
        itemSelectedCallback: callable,
        start: bool = True,
    ):
        # the capture starts once this viewer is connected to the thread (and
        # with start=False, when the caller calls startCapture())
        super().__init__(camera_index, detectionTargetsStorage, start=False)
        self.setMouseTracking(True)
        # the arrow keys move the selected box, Esc deselects it
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.fourCornerSelectionMode = False
        self.fourCorners = []
        self.fourCornerPolygon = None
        self.fourCornersAppliedCallback = fourCornersAppliedCallback
        self.itemSelectedCallback = itemSelectedCallback
        # the name of the selected box (None: none is)
        self.selectedBoxName = None
        self.first_frame_received_signal.connect(self.detectionTargetsChanged)
        self.detectionTargetsStorage.data_changed.connect(self.detectionTargetsChanged)
        self.timerThread.ocr_result_signal.connect(self.ocrResult)
        self.zoom_changed.connect(self.layoutLabels)
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
        stored_corners = fetch_data("scoresight.json", "four_corners")
        if stored_corners:
            if self.setFourCorners(stored_corners):
                self.fourCornersAppliedCallback(self.fourCorners)
            else:
                # e.g. saved by an older version that didn't validate them
                remove_data("scoresight.json", "four_corners")
        self._isScaling = False
        self._isPanning = False
        self._lastMousePosition = QPointF()

        self.boxDisplayStyleSetting: int = fetch_data(
            "scoresight.json", "box_display_style", 3
        )
        subscribe_to_data("scoresight.json", "box_display_style", self.boxDisplayStyle)
        if start:
            self.startCapture()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._isScaling or not self.fitted:
            # scrollbars appearing while zooming, or a banner over the viewer
            # while zoomed in: keep the zoom
            return
        self.fitPicture()
        self.detectionTargetsChanged()

    def boxItems(self) -> list[ResizableRectWithNameTypeAndResult]:
        return [
            item
            for item in self.scene.items(Qt.SortOrder.AscendingOrder)
            if isinstance(item, ResizableRectWithNameTypeAndResult)
        ]

    def boxDisplayStyle(self, state: int):
        self.boxDisplayStyleSetting = state
        for item in self.boxItems():
            item.setBoxDisplayStyle(state)
        self.layoutLabels()

    def toggleStabilization(self, state):
        if self.firstFrameReceived and self.timerThread:
            self.timerThread.toggleStabilization(state)

    def toggleBinary(self):
        if self.firstFrameReceived and self.timerThread:
            self.timerThread.show_binary = not self.timerThread.show_binary

    # --- four-corner correction -----------------------------------------------------

    def hasFourCornerCorrection(self) -> bool:
        """Whether the picture is corrected with four corners."""
        return self.timerThread is not None and self.timerThread.homography is not None

    def fourCornersPicked(self) -> int:
        """How many corners were clicked while picking."""
        return len(self.fourCorners) if self.fourCornerSelectionMode else 0

    def startFourCornerSelection(self):
        """Pick new corners. The picture is shown without the current
        correction (the corners are clicked on it), but the correction stays in
        effect, also for the OCR, until the 4th valid click replaces it.
        cancelFourCornerSelection() (Esc) keeps it."""
        self.clearFourCornerItems()
        self.show_error_text(None)
        self.fourCornerSelectionMode = True
        # the boxes sit on the corrected picture: hidden while it isn't shown
        self.setBoxesSuppressed(True)
        if self.timerThread is not None:
            self.timerThread.preview_uncorrected = True
            self.timerThread.requestPreview()
        self.four_corner_changed.emit()

    def cancelFourCornerSelection(self):
        """Stop picking corners; the correction (if any) stays as it was."""
        if not self.fourCornerSelectionMode:
            return
        self.fourCornerSelectionMode = False
        self.clearFourCornerItems()
        self.show_error_text(None)
        self.endUncorrectedPreview()
        self.four_corner_changed.emit()

    def removeFourCornerCorrection(self):
        """Show the picture without perspective correction."""
        self.cancelFourCornerSelection()
        self.setFourCorners(None)
        remove_data("scoresight.json", "four_corners")
        if self.timerThread is not None:
            self.timerThread.requestPreview()
        self.four_corner_changed.emit()

    def endUncorrectedPreview(self):
        self.setBoxesSuppressed(False)
        if self.timerThread is not None:
            self.timerThread.preview_uncorrected = False
            self.timerThread.requestPreview()

    def setFourCorners(self, corners) -> bool:
        self.clearFourCornerItems()
        return self.setFourCornersForHomography(corners)

    def clearFourCornerItems(self):
        for corner in self.fourCorners:
            self.scene.removeItem(corner)
        if self.fourCornerPolygon is not None:
            self.scene.removeItem(self.fourCornerPolygon)
        self.fourCorners = []
        self.fourCornerPolygon = None

    def addFourCornerPoint(self, scene_pos: QPointF):
        """A click while picking: add a corner, and with the 4th one replace the
        correction (or, if the 4 corners don't make a usable quad, start the
        picking over and keep the correction)."""
        half = CORNER_MARKER_PX / 2
        point = QGraphicsEllipseItem(-half, -half, CORNER_MARKER_PX, CORNER_MARKER_PX)
        point.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        point.setPos(scene_pos)
        point.setBrush(QBrush(CORNER_COLOR))
        point.setPen(QPen(QColor("white"), 1.5))
        point.setZValue(10)
        self.scene.addItem(point)
        self.fourCorners.append(point)
        self.fourCorners = sort_points_clockwise(self.fourCorners)
        if len(self.fourCorners) >= 2:
            if not self.fourCornerPolygon:
                self.fourCornerPolygon = QGraphicsPolygonItem()
                pen = QPen(CORNER_COLOR, 2)
                pen.setCosmetic(True)
                self.fourCornerPolygon.setPen(pen)
                self.fourCornerPolygon.setZValue(9)
                self.scene.addItem(self.fourCornerPolygon)
            self.fourCornerPolygon.setPolygon(
                QPolygonF([corner.pos() for corner in self.fourCorners])
            )
        if len(self.fourCorners) == 4:
            corners = [(corner.x(), corner.y()) for corner in self.fourCorners]
            if compute_four_corner_homography(corners) is None:
                # e.g. the same point clicked twice: start the picking over,
                # the previous correction stays
                self.clearFourCornerItems()
                # a message only: the source is fine, so the view tools stay
                # enabled (error_event would disable them)
                self.show_error_text(
                    QCoreApplication.translate(
                        "ImageViewer",
                        "Invalid four-corner selection: click the four corners "
                        "of the scoreboard",
                    )
                )
            else:
                self.show_error_text(None)
                self.fourCornerSelectionMode = False
                self.clearFourCornerItems()
                self.setFourCornersForHomography(corners)
                store_data("scoresight.json", "four_corners", corners)
                self.endUncorrectedPreview()
                self.fourCornersAppliedCallback(corners)
        self.four_corner_changed.emit()

    # --- boxes ------------------------------------------------------------------------

    def setBoxesSuppressed(self, suppressed: bool):
        for item in self.boxItems():
            item.setSuppressed(suppressed)

    def detectionTargetsChanged(self):
        if not self.firstFrameReceived:
            return

        # get the detection targets from the storage
        detectionTargets: list[TextDetectionTarget] = (
            self.detectionTargetsStorage.get_data()
        )
        done_targets = []
        # add the boxes to the scene
        for detectionTarget in detectionTargets:
            done_targets.append(detectionTarget.name)
            if detectionTarget.settings["templatefield"]:
                # do not show the template fields
                continue
            boxFound = self.findBox(detectionTarget.name)
            if boxFound is None:
                boxFound = ResizableRectWithNameTypeAndResult(
                    detectionTarget,
                    # image size
                    self.scene.sceneRect().width(),
                    onCenter=False,
                    boxChangedCallback=self.boxChanged,
                    itemSelectedCallback=self.itemSelectedCallback,
                    boxDisplayStyle=self.boxDisplayStyleSetting,
                )
                boxFound.setSuppressed(self.fourCornerSelectionMode)
                boxFound.setSelected(detectionTarget.name == self.selectedBoxName)
                self.scene.addItem(boxFound)
            else:
                boxFound.setRect(
                    detectionTarget.x() - boxFound.x(),
                    detectionTarget.y() - boxFound.y(),
                    detectionTarget.width(),
                    detectionTarget.height(),
                )
            boxFound.setMiniRectMode(detectionTarget.settings["composite_box"])

        # remove the boxes that are not in the storage
        for item in self.boxItems():
            if item.name not in done_targets:
                self.scene.removeItem(item)
        self.layoutLabels()

    def layoutLabels(self, *_):
        """Place each shown box's label pill: below the box (else above it,
        else inside it), where it covers no other box and no other label. The
        labels have a fixed size on screen, so this depends on the zoom."""
        items = [item for item in self.boxItems() if item.isVisible()]
        if not items:
            return
        scale = self.zoomLevel() or 1.0
        picture = (
            self.scene.sceneRect() if self.scenePixmapItem is not None else QRectF()
        )
        boxes = {id(item): item.sceneBoxRect() for item in items}
        placed = []
        # top to bottom, left to right: the same order every time
        for item in sorted(
            items, key=lambda i: (boxes[id(i)].top(), boxes[id(i)].left())
        ):
            if not item.label.isVisibleTo(item):
                continue
            others = [rect for key, rect in boxes.items() if key != id(item)]
            size = item.label.size()
            placement = place_label(
                boxes[id(item)],
                QSizeF(size.width() / scale, size.height() / scale),
                picture,
                others + placed,
                3.0 / scale,
            )
            item.setLabelPlacement(placement)
            placed.append(item.labelRectInScene(placement, scale))

    def boxChanged(self, name: str, rect: QRectF, mini_rects: list[QRectF]):
        # update the detection target in the storage
        detectionTargets: list[TextDetectionTarget] = (
            self.detectionTargetsStorage.get_data()
        )
        for detectionTarget in detectionTargets:
            if detectionTarget.name == name:
                detectionTarget.setX(rect.x())
                detectionTarget.setY(rect.y())
                detectionTarget.setWidth(rect.width())
                detectionTarget.setHeight(rect.height())
                self.detectionTargetsStorage.edit_item(
                    detectionTarget.name, detectionTarget
                )
                detectionTarget.mini_rects = mini_rects
                break

    def nudgeSelectedBox(self, dx: float, dy: float) -> bool:
        """Move the selected box by (dx, dy) picture pixels, within the
        picture. Returns False if no box is selected."""
        if self.selectedBoxName is None or self.detectionTargetsStorage is None:
            return False
        target = self.detectionTargetsStorage.find_item_by_name(self.selectedBoxName)
        if target is None or target.settings.get("templatefield"):
            return False
        bounds = (
            self.scene.sceneRect() if self.scenePixmapItem is not None else QRectF()
        )
        moved = nudged_rect(QRectF(target), dx, dy, bounds)
        target.moveTo(moved.topLeft())
        self.detectionTargetsStorage.edit_item(target.name, target)
        return True

    def findBox(self, name):
        # find the box with the name
        for item in self.boxItems():
            if item.name == name:
                return item
        return None

    def removeBox(self, name):
        # find the box with the name
        item = self.findBox(name)
        if item:
            self.scene.removeItem(item)

    def selectBox(self, name):
        # deselect all the boxes and select the one with the name
        self.selectedBoxName = name
        for item in self.boxItems():
            item.setSelected(item.name == name)
        self.layoutLabels()

    # --- mouse and keyboard ----------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._isPanning = True
            self._lastMousePosition = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif (
            self.fourCornerSelectionMode and event.button() == Qt.MouseButton.LeftButton
        ):
            self.addFourCornerPoint(self.mapToScene(event.position().toPoint()))
        else:
            # deselect all the boxes
            self.selectBox(None)
            self.itemSelectedCallback(None)
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._isPanning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)
            self.detectionTargetsStorage.saveBoxesToStorage()

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        if self._isPanning:
            delta = event.position() - self._lastMousePosition
            self._lastMousePosition = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
        else:
            super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        key = event.key()
        if key == Qt.Key.Key_Escape:
            if self.fourCornerSelectionMode:
                # the previous correction stays
                self.cancelFourCornerSelection()
            else:
                self.selectBox(None)
                self.itemSelectedCallback(None)
            event.accept()
            return
        modifiers = event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        if (
            key in _NUDGE_KEYS
            and not self.fourCornerSelectionMode
            and modifiers
            in (Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.ShiftModifier)
        ):
            step = (
                NUDGE_LARGE_PX
                if modifiers == Qt.KeyboardModifier.ShiftModifier
                else NUDGE_PX
            )
            dx, dy = _NUDGE_KEYS[key]
            if self.nudgeSelectedBox(dx * step, dy * step):
                event.accept()
                return
        super().keyPressEvent(event)

    # --- zoom --------------------------------------------------------------------------

    def zoomBy(self, factor: float) -> bool:
        """Zoom in (factor > 1) or out, within MIN_ZOOM and MAX_ZOOM (or the
        fitted zoom, if it is outside them)."""
        zoom = self.zoomLevel()
        if factor > 1:
            target = min(zoom * factor, max(MAX_ZOOM, zoom))
        else:
            target = max(zoom * factor, min(MIN_ZOOM, zoom))
        if abs(target - zoom) < 1e-9:
            return False
        self._isScaling = True
        self.fitted = False
        self.scale(target / zoom, target / zoom)
        # the resize events of the scrollbars appearing come first
        QTimer.singleShot(0, self.resetScalingFlag)
        self.emitZoom()
        return True

    def zoomIn(self):
        return self.zoomBy(KEY_ZOOM_FACTOR)

    def zoomOut(self):
        return self.zoomBy(1 / KEY_ZOOM_FACTOR)

    def wheelEvent(self, event):
        # check for ctrl key
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoomBy(WHEEL_ZOOM_FACTOR)
            else:
                self.zoomBy(1 / WHEEL_ZOOM_FACTOR)
        else:
            # scroll the scene
            super().wheelEvent(event)

    def resetZoom(self):
        self.fitPicture()

    def resetScalingFlag(self):
        self._isScaling = False  # Reset the flag after potential resizeEvent

    def ocrResult(self, results: list[TextDetectionTargetWithResult]):
        if not self.firstFrameReceived:
            return
        resized = False
        # update the rect with the result
        for targetWithResult in results:
            if targetWithResult.settings["templatefield"]:
                # do not update template fields
                continue
            item = self.findBox(targetWithResult.name)
            if item:
                resized |= item.updateResult(targetWithResult)
            else:
                logger.debug(f"Could not find item with name {targetWithResult.name}")
        if resized:
            # a longer or shorter reading: its label may now cover something
            self.layoutLabels()

    def closeEvent(self, event):
        logger.debug("Close")
        # stop following the boxes and settings, so a closed viewer is neither
        # kept alive nor updated by them
        unsubscribe_from_data(
            "scoresight.json", "box_display_style", self.boxDisplayStyle
        )
        if self.detectionTargetsStorage is not None:
            try:
                self.detectionTargetsStorage.data_changed.disconnect(
                    self.detectionTargetsChanged
                )
            except (RuntimeError, TypeError):
                pass
        super().closeEvent(event)
