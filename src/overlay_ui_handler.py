"""The browser overlays on the HTTP server's page (Outputs > HTTP server): pick
an overlay (built-in or from the overlays folder), its fields, theme and scale,
and copy or open its URL (overlays.overlay_url builds it)."""

from collections.abc import Callable

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPoint, Qt, QUrl
from PySide6.QtGui import QActionGroup, QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QMenu, QStyle, QToolTip

import overlays
from sc_logging import logger
from storage import fetch_data, store_data

SETTINGS_KEY = "overlay_builder"
CUSTOM = "custom"
LOCALHOST = "localhost"
# the fields button's text is elided to this many average characters
FIELDS_TEXT_CHARS = 26


def kind_names() -> dict[str, str]:
    """The built-in overlays' names, translated."""
    return {
        overlays.SCOREBUG: QCoreApplication.translate("OverlayBuilder", "Scorebug"),
        overlays.LOWER_THIRD: QCoreApplication.translate(
            "OverlayBuilder", "Lower third"
        ),
        overlays.CLOCK: QCoreApplication.translate("OverlayBuilder", "Clock"),
        overlays.FIELD: QCoreApplication.translate("OverlayBuilder", "Single field"),
    }


class _StayOpenMenu(QMenu):
    """A menu that stays open when a checkable item is clicked (to pick several
    fields)."""

    def mouseReleaseEvent(self, event):
        action = self.activeAction()
        if action is not None and action.isEnabled() and action.isCheckable():
            action.trigger()
            return
        super().mouseReleaseEvent(event)


class OverlayBuilder(QObject):
    """Binds the overlay widgets of the HTTP server's page.

    field_names() gives the boxes' names (in the fields list's order);
    base_urls() the server's URLs ("http://host:port"), the LAN address first,
    or () when the server isn't running."""

    def __init__(
        self,
        ui,
        field_names: Callable[[], list[str]],
        base_urls: Callable[[], tuple[str, ...]],
    ):
        super().__init__(ui.groupBox_overlays)
        self.ui = ui
        self.fieldNames = field_names
        self.baseUrls = base_urls
        stored = fetch_data("scoresight.json", SETTINGS_KEY, {}) or {}
        if not isinstance(stored, dict):
            stored = {}
        self.kind = stored.get("kind") if isinstance(stored.get("kind"), str) else ""
        self.customName = stored.get("custom") or ""
        # the chosen fields for the multi-field overlays (None: the overlay's
        # defaults) and the single field's
        fields = stored.get("fields")
        self.fields: list[str] | None = (
            [str(name) for name in fields] if isinstance(fields, list) else None
        )
        self.singleField = str(stored.get("field") or "")
        self.host = str(stored.get("host") or "")
        self.loading = True

        ui.toolButton_overlaysFolder.setIcon(
            ui.toolButton_overlaysFolder.style().standardIcon(
                QStyle.StandardPixmap.SP_DirOpenIcon
            )
        )
        theme = stored.get("theme")
        if theme in overlays.THEMES:
            ui.comboBox_overlayTheme.setCurrentIndex(overlays.THEMES.index(theme))
        scale = stored.get("scale")
        if isinstance(scale, (int, float)):
            ui.doubleSpinBox_overlayScale.setValue(float(scale))

        self.fieldsMenu = _StayOpenMenu(ui.toolButton_overlayFields)
        self.fieldsMenu.aboutToShow.connect(self.fillFieldsMenu)
        ui.toolButton_overlayFields.setMenu(self.fieldsMenu)

        self.fillKinds()
        self.loading = False
        ui.comboBox_overlayKind.currentIndexChanged.connect(self.kindChanged)
        ui.comboBox_overlayTheme.currentIndexChanged.connect(self.optionsChanged)
        ui.doubleSpinBox_overlayScale.valueChanged.connect(self.optionsChanged)
        ui.comboBox_overlayHost.currentIndexChanged.connect(self.hostChanged)
        ui.toolButton_overlaysFolder.clicked.connect(self.openFolder)
        ui.pushButton_copyOverlayUrl.clicked.connect(self.copyUrl)
        ui.pushButton_openOverlayUrl.clicked.connect(self.openUrl)
        # the overlays folder may have new files when the list is opened
        ui.comboBox_overlayKind.installEventFilter(self)
        self.refresh()

    # --- state ---------------------------------------------------------------

    @staticmethod
    def kindKey(kind: str, custom: str = "") -> str:
        """An overlay list item's data: the built-in overlay, or "custom:" and
        the file."""
        return f"{CUSTOM}:{custom}" if kind == CUSTOM else kind

    def currentKind(self) -> tuple[str, str]:
        """(kind, custom file): kind is a built-in overlay or CUSTOM."""
        data = self.ui.comboBox_overlayKind.currentData()
        if isinstance(data, str):
            if data.startswith(f"{CUSTOM}:"):
                return (CUSTOM, data[len(CUSTOM) + 1 :])
            if data in overlays.OVERLAY_KINDS:
                return (data, "")
        return (overlays.SCOREBUG, "")

    def selectedFields(self) -> list[str]:
        """The fields in the URL ([] for the overlay's defaults)."""
        kind, _ = self.currentKind()
        if kind == overlays.FIELD:
            return [self.singleField] if self.singleField else []
        return list(self.fields) if self.fields is not None else []

    def theme(self) -> str:
        return overlays.THEMES[max(0, self.ui.comboBox_overlayTheme.currentIndex())]

    def url(self) -> str:
        """The overlay's URL on the chosen address, or "" when the server isn't
        running."""
        base = self.ui.comboBox_overlayHost.currentData()
        if not base:
            return ""
        kind, custom = self.currentKind()
        if kind == CUSTOM:
            return overlays.custom_overlay_url(base, custom)
        return overlays.overlay_url(
            base,
            kind,
            self.selectedFields(),
            theme=self.theme(),
            scale=self.ui.doubleSpinBox_overlayScale.value(),
        )

    def save(self):
        if self.loading:
            return
        kind, custom = self.currentKind()
        store_data(
            "scoresight.json",
            SETTINGS_KEY,
            {
                "kind": kind,
                "custom": custom,
                "fields": self.fields,
                "field": self.singleField,
                "theme": self.theme(),
                "scale": self.ui.doubleSpinBox_overlayScale.value(),
                "host": self.host,
            },
        )

    # --- the widgets -----------------------------------------------------------

    def fillKinds(self):
        """The overlay list: the built-in ones, then the overlays folder's HTML
        files. Keeps the selection."""
        combo = self.ui.comboBox_overlayKind
        if combo.count():
            self.kind, self.customName = self.currentKind()
        names = kind_names()
        try:
            overlays.ensure_overlays_dir()
            custom = overlays.custom_overlays()
        except OSError as e:
            logger.warning("Could not list the overlays folder: %s", e)
            custom = []
        wanted = self.kindKey(self.kind, self.customName)
        combo.blockSignals(True)
        combo.clear()
        for kind in overlays.OVERLAY_KINDS:
            combo.addItem(names[kind], kind)
        if custom:
            combo.insertSeparator(combo.count())
        for name in custom:
            combo.addItem(name, self.kindKey(CUSTOM, name))
            combo.setItemData(combo.count() - 1, name, Qt.ItemDataRole.ToolTipRole)
        index = combo.findData(wanted)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def fillHosts(self):
        """The addresses: the network address first, then localhost (the choice
        is kept as "localhost" or "network", so it survives a new address or
        port)."""
        combo = self.ui.comboBox_overlayHost
        urls = self.baseUrls()
        combo.blockSignals(True)
        combo.clear()
        index = 0 if urls else -1
        for base in urls:
            address = base.removeprefix("http://")
            if self.host == LOCALHOST and address.startswith(f"{LOCALHOST}:"):
                index = combo.count()
            combo.addItem(address, base)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def fillFieldsMenu(self):
        """The fields menu, made when it opens (the boxes may have changed)."""
        menu = self.fieldsMenu
        menu.clear()
        kind, _ = self.currentKind()
        names = self.fieldNames()
        if kind == overlays.FIELD:
            group = QActionGroup(menu)
            group.setExclusive(True)
            current = self.singleField or overlays.DEFAULT_FIELDS[kind][0]
            for name in self.withMissing(names, [current]):
                action = menu.addAction(name.replace("&", "&&"))
                action.setCheckable(True)
                action.setChecked(name == current)
                action.setActionGroup(group)
                action.triggered.connect(lambda _=False, n=name: self.pickField(n))
            return
        default = menu.addAction(
            QCoreApplication.translate("OverlayBuilder", "Standard fields")
        )
        default.setCheckable(True)
        default.setChecked(self.fields is None)
        default.setToolTip(", ".join(overlays.DEFAULT_FIELDS[kind]))
        default.triggered.connect(self.useDefaultFields)
        menu.addSeparator()
        chosen = self.fields if self.fields is not None else []
        for name in self.withMissing(names, chosen):
            action = menu.addAction(name.replace("&", "&&"))
            action.setCheckable(True)
            action.setChecked(name in chosen)
            action.toggled.connect(lambda on, n=name: self.toggleField(n, on))

    @staticmethod
    def withMissing(names: list[str], chosen: list[str]) -> list[str]:
        """The boxes' names, then chosen names that are no box (any more)."""
        return list(names) + [name for name in chosen if name not in names]

    def updateFieldsButton(self):
        button = self.ui.toolButton_overlayFields
        kind, _ = self.currentKind()
        standard = QCoreApplication.translate("OverlayBuilder", "Standard fields")
        if kind == CUSTOM:
            # a custom overlay chooses its fields itself
            button.setText("–")
            button.setToolTip("")
            return
        if kind == overlays.FIELD:
            names = [self.singleField or overlays.DEFAULT_FIELDS[kind][0]]
            text = names[0]
        elif self.fields is None:
            names = list(overlays.DEFAULT_FIELDS[kind])
            text = standard
        else:
            names = self.fields
            text = ", ".join(names) or standard
        metrics = button.fontMetrics()
        text = metrics.elidedText(
            text,
            Qt.TextElideMode.ElideRight,
            metrics.averageCharWidth() * FIELDS_TEXT_CHARS,
        )
        button.setText(text.replace("&", "&&"))
        button.setToolTip(
            QCoreApplication.translate(
                "OverlayBuilder",
                "The fields the overlay shows, in this order: {fields}",
            ).format(fields=", ".join(names))
        )

    def refresh(self):
        """Update the widgets and the URL (after any change, the server's
        address or a language change)."""
        self.fillHosts()
        kind, _ = self.currentKind()
        builtin = kind != CUSTOM
        for widget in (
            self.ui.toolButton_overlayFields,
            self.ui.comboBox_overlayTheme,
            self.ui.doubleSpinBox_overlayScale,
            self.ui.label_overlayFields,
            self.ui.label_overlayTheme,
            self.ui.label_overlayScale,
        ):
            widget.setEnabled(builtin)
        self.updateFieldsButton()
        url = self.url()
        running = bool(url)
        line = self.ui.lineEdit_overlayUrl
        line.setText(url)
        line.setCursorPosition(0)
        line.setToolTip(url)
        line.setPlaceholderText(
            ""
            if running
            else QCoreApplication.translate(
                "OverlayBuilder", "The HTTP server is not running"
            )
        )
        self.ui.pushButton_copyOverlayUrl.setEnabled(running)
        self.ui.pushButton_openOverlayUrl.setEnabled(running)
        self.ui.comboBox_overlayHost.setEnabled(running)

    def retranslate(self):
        """After a language change (retranslateUi keeps the theme's index)."""
        self.loading = True
        self.fillKinds()
        self.loading = False
        self.refresh()

    # --- user actions ------------------------------------------------------------

    def kindChanged(self):
        self.kind, self.customName = self.currentKind()
        self.refresh()
        self.save()

    def optionsChanged(self):
        self.refresh()
        self.save()

    def hostChanged(self):
        address = self.ui.comboBox_overlayHost.currentText()
        self.host = LOCALHOST if address.startswith(f"{LOCALHOST}:") else "network"
        self.refresh()
        self.save()

    def useDefaultFields(self):
        self.fields = None
        self.fieldsMenu.close()
        self.optionsChanged()

    def toggleField(self, name: str, on: bool):
        chosen = set(self.fields or [])
        if on:
            chosen.add(name)
        else:
            chosen.discard(name)
        # in the fields list's order (then names that are no box any more)
        order = self.withMissing(self.fieldNames(), list(self.fields or []) + [name])
        self.fields = [n for n in order if n in chosen] or None
        # the "Standard fields" item follows
        actions = self.fieldsMenu.actions()
        if actions:
            actions[0].setChecked(self.fields is None)
        self.optionsChanged()

    def pickField(self, name: str):
        self.singleField = name
        self.optionsChanged()

    def copyUrl(self):
        url = self.url()
        if not url:
            return
        QGuiApplication.clipboard().setText(url)
        button = self.ui.pushButton_copyOverlayUrl
        QToolTip.showText(
            button.mapToGlobal(QPoint(0, button.height())),
            QCoreApplication.translate("OverlayBuilder", "Copied"),
            button,
        )

    def openUrl(self):
        url = self.url()
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def openFolder(self):
        folder = overlays.ensure_overlays_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def eventFilter(self, watched, event):
        if (
            watched is self.ui.comboBox_overlayKind
            and event.type() == QEvent.Type.MouseButtonPress
        ):
            self.fillKinds()
            self.refresh()
        return False
