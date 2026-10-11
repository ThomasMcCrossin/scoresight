"""Semantic colours of the main window (reading states, the paused state), with
a light and a dark variant.

The variant follows the palette, so the colours change with File > Appearance
and with a dark system theme alike. Every colour is at least 4.5:1 against the
palette's base colour of its variant, and the states are also told apart by a
glyph or a word: colour is never the only cue.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QPixmap,
)

# name: (light, dark)
_COLORS = {
    "new": ("#1A7F37", "#3FB950"),  # a new reading (Success)
    "same": ("#57606A", "#8B949E"),  # the same as the last good one (SameNoChange)
    "rejected": ("#9A6700", "#D29922"),  # rejected by the filters (FailedFilter)
    "empty": ("#CF222E", "#F85149"),  # nothing read (Empty)
    "paused": ("#BC4C00", "#F0883E"),  # outputs paused
}

# (light, dark) background tint of the paused banner
_PAUSED_TINT = ("#FFF1E5", "#3D2410")


def _palette(palette: QPalette | None) -> QPalette:
    return palette if palette is not None else QGuiApplication.palette()


def is_dark(palette: QPalette | None = None) -> bool:
    """Whether the palette is a dark one (light text on a dark window)."""
    palette = _palette(palette)
    return palette.color(QPalette.ColorRole.Window).lightness() < 128


def color(name: str, palette: QPalette | None = None) -> QColor:
    """The colour for name ("new", "same", "rejected", "empty", "paused")."""
    light, dark = _COLORS[name]
    return QColor(dark if is_dark(palette) else light)


def on_color(palette: QPalette | None = None) -> QColor:
    """The colour of text and glyphs drawn on a filled color() background."""
    return QColor("#1B1F24" if is_dark(palette) else "#FFFFFF")


def paused_tint(palette: QPalette | None = None) -> QColor:
    """A light (or, in a dark palette, dark) amber background for paused UI."""
    light, dark = _PAUSED_TINT
    return QColor(dark if is_dark(palette) else light)


def media_icon(kind: str, color: QColor, size: int = 16) -> QIcon:
    """A "play", "pause" or "stop" icon drawn in color, so it stays visible on
    light and dark buttons (the style's media icons are dark)."""
    ratio = 2.0  # sharp on high-DPI screens
    pixmap = QPixmap(round(size * ratio), round(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    unit = size / 16.0
    if kind == "play":
        path = QPainterPath(QPointF(4.5 * unit, 3 * unit))
        path.lineTo(QPointF(13 * unit, 8 * unit))
        path.lineTo(QPointF(4.5 * unit, 13 * unit))
        path.closeSubpath()
        painter.drawPath(path)
    elif kind == "pause":
        painter.drawRect(QRectF(4 * unit, 3 * unit, 3 * unit, 10 * unit))
        painter.drawRect(QRectF(9 * unit, 3 * unit, 3 * unit, 10 * unit))
    elif kind == "stop":
        painter.drawRect(QRectF(4 * unit, 4 * unit, 8 * unit, 8 * unit))
    painter.end()
    return QIcon(pixmap)


def button_text_color(palette: QPalette | None = None) -> QColor:
    return _palette(palette).color(QPalette.ColorRole.ButtonText)
