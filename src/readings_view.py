"""The Value column of the boxes list (tableWidget_boxes): each box's last good
reading, drawn large, with the state of its latest reading and how long ago the
good one was read.

MainWindow.ocrResult() stores every reading in the box's Value item with
record_reading(), and ReadingDelegate paints the item. The item's text
(DisplayRole) is always the box's last good reading (Success or SameNoChange):
a rejected or empty reading doesn't replace it, it shows as a note under it.

The state is shown by a glyph in a coloured disc (✓ new, = same, ! rejected,
∅ empty) and a word, so it never depends on colour alone.
"""

import time
from dataclasses import dataclass

from PySide6.QtCore import QCoreApplication, QEvent, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidgetItem,
    QToolTip,
)

import theme
from text_detection_target import TextDetectionTargetWithResult

ResultState = TextDetectionTargetWithResult.ResultState

# Data roles of the Value items (column 1). Column 0 keeps its UserRole (the
# placement: "checked", "unchecked" or "templatefield").
STATE_ROLE = Qt.ItemDataRole.UserRole + 1  # ResultState name of the latest reading
LAST_GOOD_TIME_ROLE = (
    Qt.ItemDataRole.UserRole + 2
)  # monotonic time of the last good one
REJECTED_TEXT_ROLE = Qt.ItemDataRole.UserRole + 3  # text of the latest rejected one

# the readings the outputs send
GOOD_STATES = (ResultState.Success, ResultState.SameNoChange)

# A good reading older than this (seconds) is stale: its age is highlighted.
# MainWindow raises it for slow detection cadences (20 detection cycles).
MIN_STALE_AFTER_S = 10.0

# state: (theme colour, glyph)
_STATE_LOOK = {
    ResultState.Success: ("new", "check"),
    ResultState.SameNoChange: ("same", "equals"),
    ResultState.FailedFilter: ("rejected", "exclamation"),
    ResultState.Empty: ("empty", "empty"),
}
# the glyphs as text, for tooltips and accessibility
_GLYPH_TEXT = {"check": "✓", "equals": "=", "exclamation": "!", "empty": "∅"}

# padding inside a cell, in pixels
_PAD_X = 6
_PAD_Y = 3


@dataclass(frozen=True)
class Reading:
    """What the Value cell of a box shows."""

    state: ResultState | None  # of the latest reading; None before the first
    value: str  # the last good reading ("" before the first)
    rejected: str  # the text of the latest rejected reading
    age: float | None  # seconds since the last good reading
    stale: bool  # the last good reading is old


def record_reading(
    item: QTableWidgetItem, state: ResultState, text: str, now: float | None = None
):
    """Store a box's latest reading in its Value item."""
    now = time.monotonic() if now is None else now
    text = "" if text is None else str(text)
    if state in GOOD_STATES:
        item.setText(text)
        item.setData(LAST_GOOD_TIME_ROLE, now)
    elif state == ResultState.FailedFilter:
        item.setData(REJECTED_TEXT_ROLE, text)
    item.setData(STATE_ROLE, state.name)
    rejected = text if state == ResultState.FailedFilter else ""
    reading = Reading(state, item.text(), rejected, None, False)
    item.setData(Qt.ItemDataRole.AccessibleTextRole, accessible_text(reading))


def clear_reading(item: QTableWidgetItem):
    """Forget a box's readings (it was taken off the picture)."""
    item.setText("")
    for role in (
        STATE_ROLE,
        LAST_GOOD_TIME_ROLE,
        REJECTED_TEXT_ROLE,
        Qt.ItemDataRole.AccessibleTextRole,
    ):
        item.setData(role, None)


def reading_at(index, now: float | None = None, stale_after: float = MIN_STALE_AFTER_S):
    """The Reading stored in a Value item (a QModelIndex)."""
    now = time.monotonic() if now is None else now
    state_name = index.data(STATE_ROLE)
    try:
        state = ResultState[state_name] if state_name else None
    except KeyError:
        state = None
    last_good = index.data(LAST_GOOD_TIME_ROLE)
    age = max(0.0, now - last_good) if isinstance(last_good, (int, float)) else None
    return Reading(
        state=state,
        value=index.data(Qt.ItemDataRole.DisplayRole) or "",
        rejected=index.data(REJECTED_TEXT_ROLE) or "",
        age=age,
        stale=age is not None and age > stale_after,
    )


def state_glyph(state: ResultState | None) -> str:
    """✓, =, ! or ∅ for a state ("" for none)."""
    if state not in _STATE_LOOK:
        return ""
    return _GLYPH_TEXT[_STATE_LOOK[state][1]]


def state_text(reading: Reading) -> str:
    """One or two words for the state of the latest reading."""
    if reading.state == ResultState.Success:
        return QCoreApplication.translate("ReadingDelegate", "new")
    if reading.state == ResultState.SameNoChange:
        return QCoreApplication.translate("ReadingDelegate", "same")
    if reading.state == ResultState.FailedFilter:
        if reading.rejected:
            return QCoreApplication.translate(
                "ReadingDelegate", "rejected ‘{text}’"
            ).format(text=reading.rejected)
        return QCoreApplication.translate("ReadingDelegate", "rejected")
    if reading.state == ResultState.Empty:
        return QCoreApplication.translate("ReadingDelegate", "no reading")
    return ""


def format_age(seconds: float) -> str:
    """A short age: "4 s", "12 min", "2 h"."""
    seconds = int(seconds)
    if seconds < 60:
        return QCoreApplication.translate("ReadingDelegate", "{seconds} s").format(
            seconds=seconds
        )
    if seconds < 3600:
        return QCoreApplication.translate("ReadingDelegate", "{minutes} min").format(
            minutes=seconds // 60
        )
    return QCoreApplication.translate("ReadingDelegate", "{hours} h").format(
        hours=seconds // 3600
    )


def reading_note(reading: Reading) -> str:
    """The line under the value, e.g. "new · 3 s" or "rejected ‘2l’ · 8 s"."""
    parts = [state_text(reading)]
    if reading.age is not None:
        parts.append(format_age(reading.age))
    return " · ".join(part for part in parts if part)


def accessible_text(reading: Reading) -> str:
    """The value and the state, for screen readers (no age: it isn't live)."""
    return ", ".join(part for part in (reading.value, state_text(reading)) if part)


def reading_tooltip(reading: Reading) -> str:
    lines = []
    if reading.value:
        if reading.age is not None:
            lines.append(
                QCoreApplication.translate(
                    "ReadingDelegate", "Last good reading: {value} ({age} ago)"
                ).format(value=reading.value, age=format_age(reading.age))
            )
        else:
            lines.append(
                QCoreApplication.translate(
                    "ReadingDelegate", "Last good reading: {value}"
                ).format(value=reading.value)
            )
    if reading.state is not None:
        lines.append(
            QCoreApplication.translate(
                "ReadingDelegate", "Latest reading: {glyph} {state}"
            ).format(glyph=state_glyph(reading.state), state=state_text(reading))
        )
    if reading.stale:
        lines.append(
            QCoreApplication.translate(
                "ReadingDelegate",
                "No good reading for a while: check the box and its settings.",
            )
        )
    return "\n".join(lines)


def _draw_glyph(painter: QPainter, rect: QRectF, glyph: str, color):
    """Draw a glyph (check, equals, exclamation, empty) as lines in rect, so it
    looks the same with every font."""
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

    def at(fx, fy):
        return QPointF(x + fx * w, y + fy * h)

    pen = QPen(color, max(1.5, w / 8.0))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if glyph == "check":
        path = QPainterPath(at(0.28, 0.53))
        path.lineTo(at(0.44, 0.69))
        path.lineTo(at(0.73, 0.35))
        painter.drawPath(path)
    elif glyph == "equals":
        painter.drawLine(at(0.3, 0.4), at(0.7, 0.4))
        painter.drawLine(at(0.3, 0.6), at(0.7, 0.6))
    elif glyph == "exclamation":
        painter.drawLine(at(0.5, 0.25), at(0.5, 0.55))
        painter.drawPoint(at(0.5, 0.74))
    elif glyph == "empty":
        painter.drawEllipse(QRectF(at(0.31, 0.31), at(0.69, 0.69)))
        painter.drawLine(at(0.27, 0.73), at(0.73, 0.27))


class ReadingDelegate(QStyledItemDelegate):
    """Paints a Value item: the state disc on the left, the last good reading
    large on the right, and the state and age under it."""

    def __init__(self, parent=None, clock=time.monotonic):
        super().__init__(parent)
        self.clock = clock
        self.stale_after = MIN_STALE_AFTER_S
        # outputs are paused: the values on screen are not being sent
        self.paused = False

    def setStaleAfter(self, seconds: float):
        self.stale_after = max(MIN_STALE_AFTER_S, float(seconds))

    def setPaused(self, paused: bool):
        self.paused = paused

    @staticmethod
    def valueFont(font: QFont) -> QFont:
        value_font = QFont(font)
        size = font.pointSizeF()
        if size > 0:
            value_font.setPointSizeF(size * 1.4)
        else:
            value_font.setPixelSize(round(font.pixelSize() * 1.4))
        value_font.setWeight(QFont.Weight.DemiBold)
        # digits of equal width, so a running clock doesn't jitter
        value_font.setFeature(QFont.Tag("tnum"), 1)
        return value_font

    @staticmethod
    def noteFont(font: QFont) -> QFont:
        note_font = QFont(font)
        size = font.pointSizeF()
        if size > 0:
            note_font.setPointSizeF(max(7.0, size * 0.85))
        return note_font

    def rowHeight(self, font: QFont) -> int:
        """The height of a row that fits the value and the note."""
        return (
            QFontMetrics(self.valueFont(font)).height()
            + QFontMetrics(self.noteFont(font)).height()
            + 2 * _PAD_Y
        )

    def discSize(self, font: QFont) -> int:
        return QFontMetrics(self.noteFont(font)).height() + 3

    def sizeHint(self, option, index):
        reading = reading_at(index, self.clock(), self.stale_after)
        value_metrics = QFontMetrics(self.valueFont(option.font))
        note_metrics = QFontMetrics(self.noteFont(option.font))
        width = max(
            value_metrics.horizontalAdvance(reading.value or "00"),
            note_metrics.horizontalAdvance(reading_note(reading)),
        )
        return QSize(
            width + self.discSize(option.font) + 3 * _PAD_X,
            self.rowHeight(option.font),
        )

    def _rowSelected(self, option, index) -> bool:
        # the Value items aren't selectable: show the row's selection (its
        # name item) across the whole row
        view = option.widget
        selection = view.selectionModel() if view is not None else None
        return bool(selection and selection.isSelected(index.siblingAtColumn(0)))

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        if self._rowSelected(opt, index):
            opt.state |= QStyle.StateFlag.State_Selected
        opt.text = ""
        widget = opt.widget
        style = widget.style() if widget is not None else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)

        reading = reading_at(index, self.clock(), self.stale_after)
        if reading.state is None and not reading.value:
            return

        palette = opt.palette
        enabled = bool(opt.state & QStyle.StateFlag.State_Enabled)
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        group = QPalette.ColorGroup.Normal if enabled else QPalette.ColorGroup.Disabled
        text_color = palette.color(
            group,
            QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text,
        )
        muted_color = (
            text_color
            if selected
            else palette.color(group, QPalette.ColorRole.PlaceholderText)
        )

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(opt.rect).adjusted(_PAD_X, _PAD_Y, -_PAD_X, -_PAD_Y)

        # The first line, right-aligned: the value, large, and left of it the
        # state disc (and "not sent" while the outputs are paused)
        value_font = self.valueFont(opt.font)
        value_metrics = QFontMetrics(value_font)
        note_font = self.noteFont(opt.font)
        note_metrics = QFontMetrics(note_font)
        line = QRectF(rect.left(), rect.top(), rect.width(), value_metrics.height())
        disc_size = self.discSize(opt.font) if reading.state in _STATE_LOOK else 0
        disc_room = disc_size + _PAD_X if disc_size else 0
        # no good reading yet: a dash in the value's place
        value = reading.value or "–"
        value = value_metrics.elidedText(
            value, Qt.TextElideMode.ElideRight, int(max(0.0, line.width() - disc_room))
        )
        value_width = value_metrics.horizontalAdvance(value)
        painter.setFont(value_font)
        painter.setPen(text_color if reading.value else muted_color)
        painter.drawText(
            line, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, value
        )
        left = line.right() - value_width

        if disc_size:
            color_name, glyph = _STATE_LOOK[reading.state]
            disc = QRectF(
                left - _PAD_X - disc_size,
                line.center().y() - disc_size / 2,
                disc_size,
                disc_size,
            )
            disc_color = theme.color(color_name, palette) if enabled else muted_color
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(disc_color)
            painter.drawEllipse(disc)
            _draw_glyph(painter, disc, glyph, theme.on_color(palette))
            left = disc.left()

        painter.setFont(note_font)
        # outputs paused: the value isn't being sent
        if self.paused and reading.value:
            marker = QCoreApplication.translate("ReadingDelegate", "not sent")
            marker_width = note_metrics.horizontalAdvance(marker)
            if left - line.left() >= marker_width + _PAD_X:
                painter.setPen(
                    text_color if selected else theme.color("paused", palette)
                )
                painter.drawText(
                    QRectF(
                        left - _PAD_X - marker_width,
                        line.top(),
                        marker_width,
                        line.height(),
                    ),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    marker,
                )

        # the state and the age, small, under the value
        note_rect = QRectF(
            rect.left(), line.bottom(), rect.width(), note_metrics.height()
        )
        state_part = state_text(reading)
        age_part = format_age(reading.age) if reading.age is not None else ""
        if selected or not enabled:
            state_color = age_color = muted_color
        else:
            state_color = muted_color
            if reading.state == ResultState.FailedFilter:
                state_color = theme.color("rejected", palette)
            elif reading.state == ResultState.Empty:
                state_color = theme.color("empty", palette)
            age_color = (
                theme.color("rejected", palette) if reading.stale else muted_color
            )
        segments = [(age_part, age_color)]
        if state_part and age_part:
            segments.insert(0, (" · ", muted_color))
        segments.insert(0, (state_part, state_color))
        segments = [(text, color) for text, color in segments if text]
        total = sum(note_metrics.horizontalAdvance(text) for text, _ in segments)
        if total > note_rect.width():
            # too narrow: one elided line in the muted colour
            painter.setPen(muted_color)
            painter.drawText(
                note_rect,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                note_metrics.elidedText(
                    reading_note(reading),
                    Qt.TextElideMode.ElideLeft,
                    int(note_rect.width()),
                ),
            )
        else:
            right = note_rect.right()
            for text, color in reversed(segments):
                width = note_metrics.horizontalAdvance(text)
                painter.setPen(color)
                painter.drawText(
                    QRectF(right - width, note_rect.top(), width, note_rect.height()),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    text,
                )
                right -= width
        painter.restore()

    def helpEvent(self, event, view, option, index):
        if event.type() == QEvent.Type.ToolTip and index.isValid():
            text = reading_tooltip(reading_at(index, self.clock(), self.stale_after))
            if text:
                QToolTip.showText(event.globalPos(), text, view)
                return True
        return super().helpEvent(event, view, option, index)
