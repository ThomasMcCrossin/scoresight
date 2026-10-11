"""The texts of the viewer column's source bar and of the messages around the
picture: what the source combo box shows for the open source, the source error
banner, the four-corner picking banner, the playback speeds, the zoom readout,
the first-run card's links, and whether macOS lets ScoreSight record the
screen.

MainWindow owns the widgets (they are in mainwindow.ui); this module words
and computes what they show, so it can be tested without a window.
CompactToolRow fits the source bar into narrow windows.
"""

import platform

from PySide6.QtCore import QCoreApplication, QEvent, QObject, Qt
from PySide6.QtWidgets import QToolButton, QWidget

from camera_info import CameraInfo
from status_bar import without_credentials

DOCS_URL = "https://royshil.github.io/scoresight/"
QUICKSTART_URL = DOCS_URL + "quickstart.html"
SOURCE_TROUBLESHOOTING_URL = DOCS_URL + "troubleshooting.html#source-problems"
# System Settings > Privacy & Security > Screen Recording
MACOS_SCREEN_RECORDING_SETTINGS_URL = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
)

# the playback speeds of a video file, in the order the speed button cycles
PLAYBACK_SPEEDS = (1, 2, 4, 8, 16, 32)

# the window id of a screen capture of the whole screen
ENTIRE_SCREEN = -1


def _translate(text: str) -> str:
    return QCoreApplication.translate("SourceBar", text)


def file_name(path) -> str:
    path = str(path)
    return path.replace("\\", "/").rsplit("/", 1)[-1] or path


def screen_title(window_id, window_title: str | None = None) -> str:
    """The name of a screen capture's window ("Entire screen" for the whole
    screen)."""
    if window_id == ENTIRE_SCREEN or window_id is None:
        return _translate("Entire screen")
    return window_title or _translate("Window {id}").format(id=window_id)


def source_combo_text(
    camera_info: CameraInfo | None, window_title: str | None = None
) -> str | None:
    """What the source combo box shows while a video file, a stream or a
    screen capture is open ("Video file: game.mp4"), or None for the other
    sources (a camera's item already shows its name)."""
    if camera_info is None:
        return None
    if camera_info.type == CameraInfo.CameraType.FILE:
        return _translate("Video file: {name}").format(name=file_name(camera_info.id))
    if camera_info.type == CameraInfo.CameraType.URL:
        return _translate("Stream: {url}").format(
            url=without_credentials(str(camera_info.id))
        )
    if camera_info.type == CameraInfo.CameraType.SCREEN_CAPTURE:
        return _translate("Screen: {window}").format(
            window=screen_title(camera_info.id, window_title)
        )
    return None


def source_full_name(
    camera_info: CameraInfo | None, window_title: str | None = None
) -> str:
    """The open source in full: a file's path, a stream's URL (without its
    password), a captured window's title, or a camera's name."""
    if camera_info is None:
        return ""
    if camera_info.type == CameraInfo.CameraType.FILE:
        return str(camera_info.id)
    if camera_info.type == CameraInfo.CameraType.URL:
        return without_credentials(str(camera_info.id))
    if camera_info.type == CameraInfo.CameraType.SCREEN_CAPTURE:
        return screen_title(camera_info.id, window_title)
    return str(camera_info.description)


def chooser_texts() -> tuple[str, str, str, str]:
    """The source combo box's first items: no source, and the choosers of a
    video file, a stream URL and a screen capture."""
    return (
        QCoreApplication.translate("MainWindow", "No source"),
        QCoreApplication.translate("MainWindow", "Video file…"),
        QCoreApplication.translate("MainWindow", "Stream URL (RTSP, HTTP)…"),
        QCoreApplication.translate("MainWindow", "Screen capture…"),
    )


def source_error_text(
    camera_info: CameraInfo | None, window_title: str | None = None
) -> tuple[str, str]:
    """(What failed, what to do) for a source that can't be opened or read."""
    if camera_info is None:
        return _translate("The source can't be read."), ""
    name = source_full_name(camera_info, window_title)
    kind = camera_info.type
    if kind == CameraInfo.CameraType.FILE:
        return (
            _translate("Can't play the video file {name}.").format(
                name=file_name(camera_info.id)
            ),
            _translate(
                "It may have been moved, be damaged or use a format that can't be "
                "read (MP4 and AVI work best)."
            ),
        )
    if kind == CameraInfo.CameraType.URL:
        return (
            _translate("Can't open the stream {url}.").format(url=name),
            _translate(
                "Check the address, the user name and password, and that the camera "
                "or server is on and reachable from this computer. A stream gets "
                "5 seconds to answer."
            ),
        )
    if kind == CameraInfo.CameraType.SCREEN_CAPTURE:
        return (
            _translate("Can't capture {window}.").format(window=name),
            _translate("The window may have been closed or minimized."),
        )
    if kind == CameraInfo.CameraType.NDI:
        return (
            _translate("Can't receive the NDI source {name}.").format(name=name),
            _translate(
                "Check that it is still on the network, then Retry or reload the "
                "sources."
            ),
        )
    return (
        _translate("Can't open {name}.").format(name=name),
        _translate(
            "It may be unplugged or used by another program: close that program, "
            "then Retry."
        ),
    )


def screen_recording_permission_text() -> tuple[str, str]:
    """(What's wrong, what to do) when macOS doesn't let ScoreSight record the
    screen: the capture then shows only the desktop."""
    return (
        _translate("ScoreSight isn't allowed to record the screen."),
        _translate(
            "macOS shows only the desktop to apps without the Screen Recording "
            "permission. Allow ScoreSight in System Settings, then restart it."
        ),
    )


def screen_recording_allowed() -> bool | None:
    """Whether macOS lets this app record the screen: True or False on macOS
    10.15 and later, None where there's no such permission or it can't be
    told (CGPreflightScreenCaptureAccess doesn't ask the user)."""
    if platform.system() != "Darwin":
        return None
    try:
        import Quartz  # pyobjc, on macOS only

        preflight = getattr(Quartz, "CGPreflightScreenCaptureAccess", None)
        if preflight is None:
            return None
        return bool(preflight())
    except Exception:
        return None


def four_corner_banner_text(picked: int, has_correction: bool) -> str:
    """The four-corner picking banner: how many corners were clicked, and what
    Esc does."""
    text = _translate(
        "<b>Click the 4 corners of the scoreboard:</b> {picked} of 4."
    ).format(picked=picked)
    if has_correction:
        text += " " + _translate("Esc cancels and keeps the previous correction.")
    else:
        text += " " + _translate("Esc cancels.")
    return text


def next_speed(speed) -> int:
    """The playback speed after speed (1, 2, 4 ... 32, then 1 again)."""
    try:
        index = PLAYBACK_SPEEDS.index(speed)
    except ValueError:
        return PLAYBACK_SPEEDS[0]
    return PLAYBACK_SPEEDS[(index + 1) % len(PLAYBACK_SPEEDS)]


def speed_text(speed) -> str:
    return f"×{speed}"


def zoom_text(scale: float) -> str:
    """The zoom readout: the size of an image pixel on screen, in percent."""
    return QCoreApplication.translate("MainWindow", "{zoom}%").format(
        zoom=round(scale * 100)
    )


def rotate_text(angle) -> str:
    """The Rotate button: what a click does, and the current angle."""
    return QCoreApplication.translate("MainWindow", "Rotate 90° · {angle}°").format(
        angle=int(angle or 0) % 360
    )


def quickstart_link() -> str:
    return '<a href="{url}">{text}</a> ↗'.format(
        url=QUICKSTART_URL,
        text=QCoreApplication.translate("MainWindow", "5-minute Quickstart"),
    )


class CompactToolRow(QObject):
    """Fits a row of tool buttons into less room. Narrower than its buttons
    need with their texts, the row shows them with their icons only (the texts
    stay their tooltips and accessible names) and hides its labels. The window
    can then be narrower than the row with its texts."""

    def __init__(self, row: QWidget, buttons: list[QToolButton], labels: list[QWidget]):
        super().__init__(row)
        self.row = row
        self.buttons = list(buttons)
        self.labels = list(labels)
        self.compact = False
        # the row's width with the texts
        self.fullWidth = 0
        for label in self.labels:
            # they hide instead of keeping the window wide
            label.setMinimumWidth(1)
        row.installEventFilter(self)
        self.refresh()

    def eventFilter(self, watched, event):
        if watched is self.row and event.type() == QEvent.Type.Resize:
            self.update()
        return False

    def refresh(self):
        """Measure the row with its texts again (after the texts changed, e.g.
        with the language)."""
        self.setCompact(False)
        for button in self.buttons:
            # the room it can be squeezed to: its icon
            button.setMinimumWidth(0)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            icon_only = button.sizeHint().width()
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.setMinimumWidth(icon_only)
        self.update()

    def update(self):
        if not self.compact:
            self.fullWidth = self.row.layout().sizeHint().width()
        self.setCompact(self.row.width() < self.fullWidth)

    def setCompact(self, compact: bool):
        if compact == self.compact:
            return
        self.compact = compact
        style = (
            Qt.ToolButtonStyle.ToolButtonIconOnly
            if compact
            else Qt.ToolButtonStyle.ToolButtonTextOnly
        )
        for button in self.buttons:
            button.setToolButtonStyle(style)
        for label in self.labels:
            label.setVisible(not compact)
