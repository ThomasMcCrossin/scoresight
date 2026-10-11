from datetime import datetime
from functools import partial
import html
import math
import os
import platform
import threading
import time
from typing import Callable
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStyle,
    QStyleOptionComboBox,
    QTableWidgetItem,
)
from PySide6.QtGui import (
    QActionGroup,
    QDesktopServices,
    QFontMetrics,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QPalette,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    Slot,
    QByteArray,
    QSize,
    QTimer,
    QTranslator,
    QObject,
    QCoreApplication,
    QEvent,
    QMetaMethod,
    QUrl,
)
from os import path

from api_output import out_api_status, update_out_api
from box_settings_ui_handler import BoxSettingsUIHandler
from camera_info import CameraInfo
from destinations_view import STATUS_ROLE, DestinationDelegate, DestinationsModel
from get_camera_info import get_camera_info
from http_server import (
    get_http_server_port,
    http_server_stats,
    start_http_server,
    update_http_server,
)
from ocr_training_data import OCRTrainingDataDialog, ocr_training_data_options
import output_status
from output_status import (
    STATE_COLORS,
    STATE_GLYPHS,
    DestinationStatus,
    describe_error,
    status_tooltip,
)
from output_worker import ErrorInfo
from readings_view import ReadingDelegate, clear_reading, record_reading
from resource_path import resource_path
import source_bar
from source_view import ImageViewer
from status_bar import (
    SOURCE_NONE,
    MainStatusBar,
    StatusSnapshot,
    http_server_urls,
    primary_lan_address,
    source_display_name,
    source_look,
    source_state,
    source_state_description,
)
import theme
from defaults import (
    default_boxes,
    default_info_for_box_name,
    normalize_settings_dict,
)

from storage import (
    TextDetectionTargetMemoryStorage,
    fetch_data,
    get_data_dir,
    get_profile,
    remove_data,
    store_data,
    store_custom_box_name,
    rename_custom_box_name_in_storage,
    remove_custom_box_name_in_storage,
    fetch_custom_box_names,
)
from obs_websocket import (
    close_obs_websocket,
    create_obs_scene_from_export,
    last_connect_error,
    obs_client_address,
    obs_output_status,
    open_obs_websocket,
    update_text_source,
)

import startup_timing
from template_fields import apply_template_fields
from text_detection_target import TextDetectionTarget, TextDetectionTargetWithResult
from sc_logging import logger
from uno_ui_handler import UNOUIHandler
from update_check import (
    UpdateCheckResult,
    check_for_updates,
    show_update_dialog,
    update_checks_enabled,
)
from log_view import LogViewerDialog
import file_output
from version import __version__
from video_settings import VideoSettingsDialog
from ui_mainwindow import Ui_MainWindow
from ui_about import Ui_Dialog as Ui_About
from ui_connect_obs import Ui_Dialog as Ui_ConnectObs
from ui_url_source import Ui_Dialog as Ui_UrlSource
from ui_screen_capture import Ui_Dialog as Ui_ScreenCapture
from vmix_ui_handler import VMixUIHanlder

DEFAULT_HTTP_PORT = 18099

# File > Appearance choices, persisted as the "color_scheme" setting
COLOR_SCHEMES = {
    "System": Qt.ColorScheme.Unknown,
    "Light": Qt.ColorScheme.Light,
    "Dark": Qt.ColorScheme.Dark,
}
DEFAULT_COLOR_SCHEME = "System"

# The values api_output understands, in the order of comboBox_api_encode and
# comboBox_outApiMethod. The settings store these, not the (translated) item text.
OUT_API_ENCODINGS = ("JSON (Full)", "JSON (Simple key-value)", "XML", "CSV")
OUT_API_METHODS = ("POST", "PUT", "GET")

# comboBox_camera_source items before the discovered cameras
SOURCE_INDEX_NONE = 0
SOURCE_INDEX_FILE = 1
SOURCE_INDEX_URL = 2
SOURCE_INDEX_SCREEN_CAPTURE = 3
FIRST_CAMERA_SOURCE_INDEX = 4
# the items that open a chooser (a file dialog, the URL or the window)
CHOOSER_SOURCE_INDEXES = (
    SOURCE_INDEX_FILE,
    SOURCE_INDEX_URL,
    SOURCE_INDEX_SCREEN_CAPTURE,
)

# Box edits are written to the settings this long after the last change.
BOXES_SAVE_DELAY_MS = 500

# File > Language: (locale, the language's name in that language)
LANGUAGES = (
    ("en_US", "English (US)"),
    ("fr_FR", "Français"),
    ("es_ES", "Español"),
    ("de_DE", "Deutsch"),
    ("it_IT", "Italiano"),
    ("ja_JP", "日本語"),
    ("ko_KR", "한국어"),
    ("nl_NL", "Nederlands"),
    ("pl_PL", "Polski"),
    ("pt_BR", "Português (Brasil)"),
    ("pt_PT", "Português (Portugal)"),
    ("ru_RU", "Русский"),
    ("zh_CN", "简体中文"),
)

# The sizes of the boxes list | viewer splitter (QSplitter.saveState, base64).
SPLITTER_STATE_SETTING = "main_splitter_state"
# The status bar, the readings' ages and the paused time are refreshed this often.
STATUS_INTERVAL_MS = 1000
# View > Statistics overlay (camera_view reads it too)
SHOW_OSD_SETTING = "show_osd"
# Tools > Collect OCR training data (ocr_training_data reads it too)
COLLECT_TRAINING_DATA_SETTING = "save_ocr_training_data"
# The boxes list shows at most this many rows without scrolling.
BOXES_LIST_MAX_VISIBLE_ROWS = 8
# The window's default size, made smaller on smaller screens.
DEFAULT_WINDOW_SIZE = (1280, 800)
# False after OBS was disconnected: the saved connection ("obs") isn't opened
# at startup until the user connects again
OBS_AUTO_CONNECT_SETTING = "obs_auto_connect"


def apply_color_scheme(name: str | None) -> str:
    """Apply a File > Appearance choice ("System", "Light" or "Dark") to the
    running application and return the choice applied. Unknown values mean
    "System" (follow the operating system)."""
    if name not in COLOR_SCHEMES:
        name = DEFAULT_COLOR_SCHEME
    style_hints = QGuiApplication.styleHints()
    if name == DEFAULT_COLOR_SCHEME:
        style_hints.unsetColorScheme()
    else:
        style_hints.setColorScheme(COLOR_SCHEMES[name])
    return name


def run_in_background(name: str, function: Callable, on_done: Callable):
    """Run function() on a daemon thread, then on_done(result) on that thread.

    on_done should emit a signal of a QObject that lives in the GUI thread: the
    signal is then delivered there (queued), so the result is handled on the GUI
    thread. If function raises, on_done gets None.
    """

    def target():
        try:
            result = function()
        except Exception:
            logger.exception("%s failed", name)
            result = None
        try:
            on_done(result)
        except RuntimeError:
            # the receiving window was destroyed while the call was running
            logger.debug("%s finished after its window was closed", name)

    thread = threading.Thread(target=target, name=name, daemon=True)
    thread.start()
    return thread


def stored_source_value(stored) -> dict | None:
    """Normalize the "source_selected" setting to {"type", "value", ...}.

    0.1.x stored a bare file path or URL (and nothing for cameras)."""
    if isinstance(stored, dict) and stored.get("type"):
        return stored
    if isinstance(stored, str) and stored.strip():
        stored = stored.strip()
        if path.exists(stored):
            return {"type": CameraInfo.CameraType.FILE, "value": stored}
        if "://" in stored:
            return {"type": CameraInfo.CameraType.URL, "value": stored}
    return None


class MainWindow(QMainWindow):
    # add a signal to update sources
    update_sources = Signal(list)
    get_sources = Signal()
    # results of the work done on background threads, delivered on the GUI thread
    obs_connection_result = Signal(object, int, bool, object)
    update_check_finished = Signal(object, bool)

    def __init__(
        self,
        translator: QTranslator,
        parent: QObject,
        http_port: int = DEFAULT_HTTP_PORT,
    ):
        super(MainWindow, self).__init__()
        self.parent_object = parent
        self.http_port = http_port
        self.ui = Ui_MainWindow()
        logger.info("Starting ScoreSight %s", __version__)
        self.ui.setupUi(self)
        # the HTTP server page's text, before the real port and address are
        # filled in
        self.browserEndpointsTemplate = self.ui.label_8.text()
        # this computer's address on the network (for the HTTP server's URLs)
        self.lanAddress = primary_lan_address()
        self.lanAddressCheckedAt = time.monotonic()
        self.translator = translator
        # when the outputs were paused (Pause outputs), None while they run
        self.outputsPausedAt: datetime | None = None
        self.outputsPausedMonotonic: float | None = None
        # After the outputs are resumed, vMix and UNO get each of these boxes'
        # next good reading, even an unchanged one (they normally send only
        # changed values)
        self.resendAfterPause: set[str] = set()
        self.updateWindowTitle()
        if platform.system() == "Windows":
            # set the icon
            self.setWindowIcon(QIcon(resource_path("icons", "Windows-icon-open.ico")))

        self.update_check_running = False
        # a manual check was asked for while another check was running
        self.update_check_manual_pending = False
        self.update_dialog = None
        self.update_check_finished.connect(self.updateCheckFinished)
        self.setupMenus()

        # handle the Escape key (deselect the current box)
        self.installEventFilter(self)

        self.ui.pushButton_connectObs.clicked.connect(self.openOBSConnectModal)
        self.ui.pushButton_disconnectObs.clicked.connect(self.disconnectObs)

        self.vmixUiHandler = VMixUIHanlder(self.ui)
        self.unoUiHandler = UNOUIHandler(self.ui)
        # the start/stop buttons show the same texts from the start as after a
        # toggle or a language change
        self.vmixUiHandler.restoreUiState()
        self.unoUiHandler.restoreUiState()
        self.boxSettingsUiHandler = BoxSettingsUIHandler(self.ui)

        self.ui.checkBox_templatefield.toggled.connect(self.makeTemplateField)

        start_http_server(port=self.http_port)
        self.updateBrowserEndpoints()

        self.ui.pushButton_stabilize.setEnabled(True)
        self.ui.pushButton_stabilize.clicked.connect(self.toggleStabilize)

        self.ui.toolButton_topCrop.clicked.connect(self.cropMode)
        # check configuation if crop is enabled
        self.ui.toolButton_topCrop.setChecked(
            fetch_data("scoresight.json", "crop_mode", False)
        )
        self.ui.widget_cropPanel.setVisible(self.ui.toolButton_topCrop.isChecked())
        self.ui.widget_cropPanel.setEnabled(self.ui.toolButton_topCrop.isChecked())
        self.ui.spinBox_leftCrop.valueChanged.connect(
            partial(self.globalSettingsChanged, "left_crop")
        )
        self.ui.spinBox_leftCrop.setValue(fetch_data("scoresight.json", "left_crop", 0))
        self.ui.spinBox_rightCrop.valueChanged.connect(
            partial(self.globalSettingsChanged, "right_crop")
        )
        self.ui.spinBox_rightCrop.setValue(
            fetch_data("scoresight.json", "right_crop", 0)
        )
        self.ui.spinBox_topCrop.valueChanged.connect(
            partial(self.globalSettingsChanged, "top_crop")
        )
        self.ui.spinBox_topCrop.setValue(fetch_data("scoresight.json", "top_crop", 0))
        self.ui.spinBox_bottomCrop.valueChanged.connect(
            partial(self.globalSettingsChanged, "bottom_crop")
        )
        self.ui.spinBox_bottomCrop.setValue(
            fetch_data("scoresight.json", "bottom_crop", 0)
        )
        self.ui.checkBox_enableOutAPI.toggled.connect(
            partial(self.globalSettingsChanged, "enable_out_api")
        )
        self.ui.checkBox_enableOutAPI.setChecked(
            fetch_data("scoresight.json", "enable_out_api", False)
        )

        # connect toolButton_rotate
        self.ui.toolButton_rotate.clicked.connect(self.rotateImage)

        self.ui.widget_detectionCadence.setVisible(True)
        self.ui.horizontalSlider_detectionCadence.setValue(
            fetch_data("scoresight.json", "detection_cadence", 5)
        )
        self.ui.horizontalSlider_detectionCadence.valueChanged.connect(
            self.detectionCadenceChanged
        )
        self.ui.toolButton_addBox.clicked.connect(self.addBox)
        self.ui.toolButton_removeBox.clicked.connect(self.removeCustomBox)

        self.video_settings_dialog = None
        self.ui.toolButton_videoSettings.clicked.connect(self.openVideoSettings)

        self.ui.lineEdit_api_url.textChanged.connect(
            partial(self.globalSettingsChanged, "out_api_url")
        )
        self.ui.lineEdit_api_url.setText(
            fetch_data("scoresight.json", "out_api_url", "")
        )

        self.setupChoiceSetting(
            self.ui.comboBox_api_encode, "out_api_encoding", OUT_API_ENCODINGS
        )
        self.setupChoiceSetting(
            self.ui.comboBox_outApiMethod, "out_api_method", OUT_API_METHODS
        )

        self.obs_websocket_client = None
        # the text last sent to each OBS text source
        self.obs_last_sent: dict[str, str] = {}
        self.obs_connect_attempt = 0
        self.obs_connection_result.connect(self.obsConnectionResult)
        # for the OBS status: "host:port" of the connection, of an attempt
        # running, and why the last attempt failed
        self.obsAddress: str | None = None
        self.obsConnectedAt: float | None = None
        self.obsConnecting: str | None = None
        self.obsConnectError: ErrorInfo | None = None
        self.obsConnectTarget: str | None = None

        ocr_models = [
            "Daktronics",
            "General Scoreboard",
            "General Fonts (English)",
            "General Scoreboard Large",
            "Load External OCR Model",
        ]
        self.ui.comboBox_ocrModel.addItems(ocr_models)
        # default to General Scoreboard
        ocr_model_from_storage = fetch_data("scoresight.json", "ocr_model", 1)
        if isinstance(ocr_model_from_storage, str):
            ocr_model_from_storage = 4
        self.ui.comboBox_ocrModel.setCurrentIndex(ocr_model_from_storage)

        self.ui.frame_source_view.setEnabled(False)
        self.ui.groupBox_target_settings.setEnabled(False)
        self.ui.pushButton_makeBox.clicked.connect(self.makeBox)
        self.ui.pushButton_removeBox.clicked.connect(self.removeBox)
        self.ui.tableWidget_boxes.itemClicked.connect(self.listItemClicked)
        # connect the edit triggers
        self.ui.tableWidget_boxes.itemDoubleClicked.connect(self.editBoxName)
        # the current item is always a box's name: the box settings, removing
        # and renaming use its text
        self.ui.tableWidget_boxes.currentCellChanged.connect(self.keepNameCellCurrent)
        self.setupBoxesList()
        self.ui.pushButton_refresh_sources.clicked.connect(
            lambda: self.get_sources.emit()
        )
        self.detectionTargetsStorage = TextDetectionTargetMemoryStorage()
        self.detectionTargetsStorage.data_changed.connect(self.detectionTargetsChanged)
        # Box edits (settings panel, add/remove, rename, template fields) are
        # persisted shortly after they happen, not only on a click in the viewer.
        self.boxesSaveTimer = QTimer(self)
        self.boxesSaveTimer.setSingleShot(True)
        self.boxesSaveTimer.setInterval(BOXES_SAVE_DELAY_MS)
        self.boxesSaveTimer.timeout.connect(self.saveBoxes)
        self.ui.pushButton_createOBSScene.clicked.connect(self.createOBSScene)
        self.ui.pushButton_selectFolder.clicked.connect(self.selectOutputFolder)
        self.ui.toolButton_trashFolder.clicked.connect(self.clearOutputFolder)
        self.ui.pushButton_stopUpdates.toggled.connect(self.toggleStopUpdates)
        self.ui.comboBox_ocrModel.currentIndexChanged.connect(self.ocrModelChanged)
        self.ui.comboBox_boxDisplayStyle.currentIndexChanged.connect(
            partial(self.globalSettingsChanged, "box_display_style")
        )
        box_display_style = fetch_data("scoresight.json", "box_display_style", 3)
        self.ui.comboBox_boxDisplayStyle.setCurrentIndex(
            box_display_style if isinstance(box_display_style, int) else 3
        )

        self.ui.checkBox_updateOnchange.toggled.connect(self.toggleUpdateOnChange)

        # populate the tableWidget_boxes with the default and custom boxes
        custom_boxes_names = fetch_custom_box_names()

        for box_name in [box["name"] for box in default_boxes] + custom_boxes_names:
            item = self.appendBoxRow(box_name)
            item.setIcon(QIcon(resource_path("icons", "circle-x.svg")))
            item.setData(Qt.ItemDataRole.UserRole, "unchecked")

        # The boxes are app state (not per source): load them once at startup.
        # From now on the in-memory storage is the source of truth, and changes
        # are written back by saveBoxes.
        self.detectionTargetsStorage.loadBoxesFromStorage()
        self.detectionTargetsStorage.data_changed.connect(self.scheduleBoxesSave)

        self.image_viewer = None
        self.connected_viewer = None
        self.obs_connect_modal = None
        self.source_name = None
        # the title of the window a screen capture shows
        self.sourceWindowTitle: str | None = None
        self.sources_discovery_running = False
        self.closing = False
        self.updateOCRResults = True
        self.log_dialog = None
        if fetch_data("scoresight.json", "open_on_startup", False):
            logger.info("Opening log dialog on startup")
            self.openLogsDialog()

        if fetch_data("scoresight.json", "obs") and fetch_data(
            "scoresight.json", OBS_AUTO_CONNECT_SETTING, True
        ):
            self.connectObs()

        # the output folder that was found missing (the files output stopped)
        self.outputFolderLost: str | None = None
        self.out_folder = fetch_data("scoresight.json", "output_folder")
        if self.out_folder:
            if not path.exists(self.out_folder):
                logger.warning("Output folder does not exist: %s", self.out_folder)
                self.outputFolderLost = self.out_folder
                self.out_folder = None
                remove_data("scoresight.json", "output_folder")
            else:
                self.ui.lineEdit_folder.setText(self.out_folder)

        # .txt/.csv/.xml outputs; flushed at most "Save / s" times per second
        self.fileOutput = file_output.FileOutput()
        self.fileOutputTimer = QTimer(self)
        self.fileOutputTimer.setSingleShot(True)
        self.fileOutputTimer.timeout.connect(self.flushFileOutputs)
        self.ui.checkBox_saveCsv.toggled.connect(
            partial(self.globalSettingsChanged, "save_csv")
        )
        self.ui.checkBox_saveCsv.setChecked(
            fetch_data("scoresight.json", "save_csv", False)
        )
        self.ui.checkBox_saveXML.toggled.connect(
            partial(self.globalSettingsChanged, "save_xml")
        )
        self.ui.checkBox_saveXML.setChecked(
            fetch_data("scoresight.json", "save_xml", False)
        )
        self.ui.comboBox_appendMethod.currentIndexChanged.connect(
            partial(self.globalSettingsChanged, "append_method")
        )
        self.ui.horizontalSlider_aggsPerSecond.valueChanged.connect(
            partial(self.globalSettingsChanged, "aggs_per_second")
        )
        self.ui.comboBox_appendMethod.setCurrentIndex(
            fetch_data("scoresight.json", "append_method", 3)
        )
        self.ui.horizontalSlider_aggsPerSecond.setValue(
            fetch_data("scoresight.json", "aggs_per_second", 5)
        )
        self.ui.checkBox_updateOnchange.setChecked(
            fetch_data("scoresight.json", "update_on_change", True)
        )
        self.ui.checkBox_vmix_send_same.setChecked(
            fetch_data("scoresight.json", "vmix_send_same", False)
        )
        self.ui.checkBox_vmix_send_same.toggled.connect(
            partial(self.globalSettingsChanged, "vmix_send_same")
        )

        # Pause outputs: the banner over the viewer, the status bar chip
        self.ui.frame_pausedBanner.hide()
        self.ui.pushButton_resumeOutputs.clicked.connect(
            lambda: self.ui.pushButton_stopUpdates.setChecked(False)
        )
        self.ui.horizontalSlider_detectionCadence.valueChanged.connect(
            self.updateSliderReadouts
        )
        self.ui.horizontalSlider_aggsPerSecond.valueChanged.connect(
            self.updateSliderReadouts
        )

        # the outputs' list (with their status) over their settings pages
        self.setupDestinations()

        # the source, OCR rate, the outputs and the HTTP address, and the
        # readings' ages
        self.sourceError = None
        self.statusBarWidgets = MainStatusBar(self.ui.statusbar)
        self.statusBarWidgets.destination_clicked.connect(self.showDestination)
        self.statusTimer = QTimer(self)
        self.statusTimer.setInterval(STATUS_INTERVAL_MS)
        self.statusTimer.timeout.connect(self.refreshLiveStatus)
        self.statusTimer.start()

        # the source bar, view tools, picture adjustments, banners and the
        # first-run card around the picture
        self.setupViewer()
        # the left column is as wide as its content
        self.ui.frame.installEventFilter(self)

        self.setupLayout()
        self.applyRuntimeTexts()

        self.update_sources.connect(self.updateSources)
        self.get_sources.connect(self.getSources)
        self.get_sources.emit()

        self.checkForUpdates(False)

    # --- layout, menus and texts set at runtime ---------------------------------

    def setupMenus(self):
        """Connect the File menu's actions (defined in the .ui, so they are
        translated), fill the Language and Appearance submenus, and add the
        window's keyboard shortcuts."""
        ui = self.ui
        ui.actionCheckForUpdates.triggered.connect(lambda: self.checkForUpdates(True))
        ui.actionAbout.triggered.connect(self.openAboutDialog)
        ui.actionViewLog.triggered.connect(self.openLogsDialog)
        ui.actionImportConfiguration.triggered.connect(self.importConfiguration)
        ui.actionExportConfiguration.triggered.connect(self.exportConfiguration)
        ui.actionOpenConfigurationFolder.triggered.connect(self.openConfigurationFolder)
        ui.actionOCRTrainingDataSetup.triggered.connect(self.openOCRTrainingDataDialog)

        # File > Language, each language in its own language
        self.language_actions = QActionGroup(self)
        self.language_actions.setExclusive(True)
        current_locale = self.currentLocale()
        for locale, name in LANGUAGES:
            action = ui.menuLanguage.addAction(name)
            action.setCheckable(True)
            action.setChecked(locale == current_locale)
            action.setData(locale)
            action.triggered.connect(
                lambda checked=False, locale=locale: self.changeLanguage(locale)
            )
            self.language_actions.addAction(action)

        # File > Appearance: System / Light / Dark color scheme (#50)
        self.appearance_actions = QActionGroup(self)
        self.appearance_actions.setExclusive(True)
        current_scheme = fetch_data("scoresight.json", "color_scheme")
        if current_scheme not in COLOR_SCHEMES:
            current_scheme = DEFAULT_COLOR_SCHEME
        for scheme in COLOR_SCHEMES:
            action = ui.menuAppearance.addAction(scheme)
            action.setCheckable(True)
            action.setChecked(scheme == current_scheme)
            action.setData(scheme)
            action.triggered.connect(
                lambda checked=False, scheme=scheme: self.setColorScheme(scheme)
            )
            self.appearance_actions.addAction(action)

        # shortcuts of the window (they also work while the menu bar is
        # hidden, e.g. with the macOS global menu bar)
        ui.actionZoomIn.setShortcuts(
            [QKeySequence("Ctrl+="), QKeySequence(QKeySequence.StandardKey.ZoomIn)]
        )
        for action in (
            ui.actionPauseOutputs,
            ui.actionBinaryView,
            ui.actionFitPicture,
            ui.actionZoomIn,
            ui.actionZoomOut,
            ui.actionReloadSources,
        ):
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            self.addAction(action)
        ui.actionPauseOutputs.triggered.connect(ui.pushButton_stopUpdates.toggle)
        ui.pushButton_stopUpdates.toggled.connect(ui.actionPauseOutputs.setChecked)
        # through the buttons: they do nothing while disabled (no source yet, a
        # reload running)
        ui.actionBinaryView.triggered.connect(self.triggerBinaryView)
        ui.pushButton_binary.toggled.connect(ui.actionBinaryView.setChecked)
        ui.actionFitPicture.triggered.connect(ui.toolButton_zoomReset.click)
        ui.actionReloadSources.triggered.connect(ui.pushButton_refresh_sources.click)

    def currentLocale(self) -> str | None:
        """The locale of the loaded translation (e.g. "de_DE"), if any."""
        loaded = path.basename(self.translator.filePath() or "")
        if loaded.startswith("scoresight_") and loaded.endswith(".qm"):
            return loaded[len("scoresight_") : -len(".qm")]
        return None

    def setupBoxesList(self):
        """The boxes list: names, and the readings drawn by ReadingDelegate."""
        table = self.ui.tableWidget_boxes
        self.readingDelegate = ReadingDelegate(table)
        table.setItemDelegateForColumn(1, self.readingDelegate)
        header = table.verticalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        model = table.model()
        model.rowsInserted.connect(self.updateBoxesListHeight)
        model.rowsRemoved.connect(self.updateBoxesListHeight)
        self.updateBoxesListHeight()

    def updateBoxesListHeight(self, *_):
        """Size the rows for the readings, and make the list tall enough to show
        every box (up to BOXES_LIST_MAX_VISIBLE_ROWS) without scrolling: the
        readings are the window's main live information."""
        table = self.ui.tableWidget_boxes
        row_height = self.readingDelegate.rowHeight(table.font())
        table.verticalHeader().setDefaultSectionSize(row_height)
        rows = max(3, min(table.rowCount(), BOXES_LIST_MAX_VISIBLE_ROWS))
        header_height = table.horizontalHeader().sizeHint().height()
        table.setMinimumHeight(
            header_height + rows * row_height + 2 * table.frameWidth()
        )

    def setupLayout(self):
        """Fit the window to the screen and restore the splitter's sizes."""
        splitter = self.ui.splitter_main
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.fitLeftPaneWidth()

        screen = self.screen()
        width, height = DEFAULT_WINDOW_SIZE
        if screen is not None:
            available = screen.availableGeometry()
            # leave room for the title bar and the window frame
            width = min(width, available.width() - 16)
            height = min(height, available.height() - 48)
        self.resize(width, height)

        stored = fetch_data("scoresight.json", SPLITTER_STATE_SETTING)
        restored = isinstance(stored, str) and splitter.restoreState(
            QByteArray.fromBase64(stored.encode("ascii", "ignore"))
        )
        if not restored:
            left = self.ui.widget_leftPane.minimumSizeHint().width()
            splitter.setSizes([left, max(1, self.width() - left)])
        self.splitterSaveTimer = QTimer(self)
        self.splitterSaveTimer.setSingleShot(True)
        self.splitterSaveTimer.setInterval(BOXES_SAVE_DELAY_MS)
        self.splitterSaveTimer.timeout.connect(self.saveSplitterState)
        splitter.splitterMoved.connect(lambda *_: self.splitterSaveTimer.start())

    def saveSplitterState(self):
        self.splitterSaveTimer.stop()
        state = bytes(self.ui.splitter_main.saveState().toBase64()).decode("ascii")
        if fetch_data("scoresight.json", SPLITTER_STATE_SETTING) != state:
            self.globalSettingsChanged(SPLITTER_STATE_SETTING, state)

    def fitLeftPaneWidth(self):
        """The left column scrolls vertically, never horizontally: it is at least
        as wide as its content (which depends on the language)."""
        scroll_area = self.ui.scrollArea_left
        content = self.ui.frame.minimumSizeHint().width()
        scrollbar = scroll_area.verticalScrollBar().sizeHint().width()
        width = content + scrollbar + 2 * scroll_area.frameWidth()
        if scroll_area.minimumWidth() != width:
            scroll_area.setMinimumWidth(width)

    def applyRuntimeTexts(self):
        """Set the texts that are made at runtime: at startup and again after a
        language change (retranslateUi resets them to the .ui texts)."""
        self.updateWindowTitle()
        self.updateBrowserEndpoints()
        self.updatePauseUi()
        self.updateSliderReadouts()
        self.boxSettingsUiHandler.updateReadouts()
        self.retranslateMenus()
        self.applyShortcutHints()
        self.updateObsUi()
        self.destinationsModel.retranslate()
        self.updateDestinationsListHeight()
        self.statusBarWidgets.retranslate()
        self.applyViewerTexts()
        self.refreshLiveStatus()
        self.fitLeftPaneWidth()
        self.updateAdjustHintVisibility()

    def retranslateMenus(self):
        names = {
            "System": QCoreApplication.translate("MainWindow", "System"),
            "Light": QCoreApplication.translate("MainWindow", "Light"),
            "Dark": QCoreApplication.translate("MainWindow", "Dark"),
        }
        for action in self.appearance_actions.actions():
            action.setText(names.get(action.data(), action.data()))

    def applyShortcutHints(self):
        """Add the keyboard shortcut to the tooltips of the buttons that have
        one ("... (Ctrl+B)"); ⌘ on macOS."""
        for button, action in (
            (self.ui.pushButton_stopUpdates, self.ui.actionPauseOutputs),
            (self.ui.pushButton_binary, self.ui.actionBinaryView),
            (self.ui.toolButton_zoomReset, self.ui.actionFitPicture),
            (self.ui.pushButton_refresh_sources, self.ui.actionReloadSources),
        ):
            shortcut = action.shortcut().toString(
                QKeySequence.SequenceFormat.NativeText
            )
            tooltip = button.toolTip()
            if shortcut and f"({shortcut})" not in tooltip:
                button.setToolTip(f"{tooltip} ({shortcut})".strip())
        # how to zoom and pan, on the Fit button and the zoom readout
        native = QKeySequence.SequenceFormat.NativeText
        zoom_hint = QCoreApplication.translate(
            "MainWindow",
            "Zoom with Ctrl+scroll or {zoom_in} and {zoom_out}; drag with the "
            "middle mouse button to move the picture.",
        ).format(
            zoom_in=self.ui.actionZoomIn.shortcut().toString(native),
            zoom_out=self.ui.actionZoomOut.shortcut().toString(native),
        )
        for widget in (self.ui.toolButton_zoomReset, self.ui.label_zoom):
            tooltip = widget.toolTip()
            if zoom_hint not in tooltip:
                widget.setToolTip(f"{tooltip}\n{zoom_hint}".strip())

    def updateAdjustHintVisibility(self):
        """Show the hint of the Adjust picture row only when the row has room
        for it: it never makes the window wider."""
        row = self.ui.widget_viewTools
        hint = self.ui.label_adjustHint
        layout = row.layout()
        needed = layout.contentsMargins().left() + layout.contentsMargins().right()
        visible = 0
        for index in range(layout.count()):
            widget = layout.itemAt(index).widget()
            if widget is None or widget is hint or widget.isHidden():
                continue
            needed += widget.sizeHint().width()
            visible += 1
        needed += layout.spacing() * visible + hint.sizeHint().width()
        hint.setVisible(row.width() >= needed)

    def updateWindowTitle(self):
        title = f"ScoreSight - v{__version__}"
        profile = get_profile()
        if profile:
            title += f" [{profile}]"
        if self.outputsPausedAt is not None:
            # visible in the taskbar too
            title = f"⏸ {title}"
        self.setWindowTitle(title)

    def updateBrowserEndpoints(self):
        """Show the HTTP server's real port on its page, and its address for
        other computers, or that the server isn't running (its port was
        busy)."""
        port = get_http_server_port()
        if port is None:
            self.ui.label_8.setText(
                QCoreApplication.translate(
                    "MainWindow",
                    "<p>The HTTP server is not running: port {port} is already "
                    "in use or not available.</p><p>Close the other program, or "
                    "start ScoreSight with <b>--port</b> to use a different port. "
                    "The log has the details.</p>",
                ).format(port=self.http_port)
            )
            return
        # the page's links are written for the default port
        text = self.browserEndpointsTemplate.replace(
            f"localhost:{DEFAULT_HTTP_PORT}", f"localhost:{port}"
        )
        if self.lanAddress:
            url = f"http://{self.lanAddress}:{port}"
            other_computers = QCoreApplication.translate(
                "MainWindow",
                "<p>From other computers on your network, use {url} instead of "
                "http://localhost:{port}.</p>",
            ).format(url=f'<a href="{url}/scoresight">{url}</a>', port=port)
            if "</body>" in text:
                text = text.replace("</body>", other_computers + "</body>", 1)
            else:
                text += other_computers
        self.ui.label_8.setText(text)

    def setupChoiceSetting(self, combo_box, setting_name: str, values: tuple):
        """Bind a combo box whose items are values (their text may be translated)
        to a setting that stores the value itself."""
        stored = fetch_data("scoresight.json", setting_name)
        if stored in values:
            index = values.index(stored)
        else:
            # 0.1.x stored the item text, which could be blank or translated
            index = max(
                combo_box.findText(stored if isinstance(stored, str) else ""), 0
            )
        combo_box.blockSignals(True)
        combo_box.setCurrentIndex(index)
        combo_box.blockSignals(False)
        if stored != values[index]:
            self.globalSettingsChanged(setting_name, values[index])

        def choiceChanged(index: int):
            if 0 <= index < len(values):
                self.globalSettingsChanged(setting_name, values[index])

        combo_box.currentIndexChanged.connect(choiceChanged)

    def setColorScheme(self, scheme: str):
        scheme = apply_color_scheme(scheme)
        self.globalSettingsChanged("color_scheme", scheme)
        for action in self.appearance_actions.actions():
            action.setChecked(action.data() == scheme)

    def toggleSpeed(self):
        """The next playback speed of a video file: x2, x4 ... x32, then x1."""
        if self.image_viewer and self.image_viewer.timerThread is not None:
            speed = source_bar.next_speed(self.image_viewer.timerThread.getSpeed())
            self.image_viewer.timerThread.setSpeed(speed)
            self.ui.toolButton_speed.setText(source_bar.speed_text(speed))

    def openVideoSettings(self):
        # only allow opening the video settings for an OpenCV type source
        if not self.image_viewer or self.image_viewer is None:
            return

        if self.image_viewer.getCameraInfo().type != CameraInfo.CameraType.OPENCV:
            return

        if self.video_settings_dialog is None:
            # open the logs dialog
            self.video_settings_dialog = VideoSettingsDialog()
            self.video_settings_dialog.setWindowTitle("Video Settings")

        self.video_settings_dialog.init_ui(self.image_viewer.getCameraCapture())

        # show the dialog, non modal
        self.video_settings_dialog.show()

    def rotateImage(self):
        # store the rotation in the scoresight.json
        rotation = fetch_data("scoresight.json", "rotation", 0)
        rotation += 90
        if rotation >= 360:
            rotation = 0
        self.globalSettingsChanged("rotation", rotation)
        self.updateRotateText(rotation)

    def cropMode(self):
        # if the toolButton_topCrop is unchecked, go to crop mode
        if self.ui.toolButton_topCrop.isChecked():
            self.ui.widget_cropPanel.setVisible(True)
            self.ui.widget_cropPanel.setEnabled(True)
            self.globalSettingsChanged("crop_mode", True)
        else:
            self.ui.widget_cropPanel.setVisible(False)
            self.ui.widget_cropPanel.setEnabled(False)
            self.globalSettingsChanged("crop_mode", False)

    def globalSettingsChanged(self, settingName, value):
        store_data("scoresight.json", settingName, value)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                viewer = self.image_viewer
                if viewer is not None and viewer.fourCornerSelectionMode:
                    # stop picking corners, the correction stays
                    viewer.cancelFourCornerSelection()
                else:
                    # deselect any selected item
                    self.itemSelected(None)
                    if viewer is not None:
                        viewer.selectBox(None)
        elif event.type() == QEvent.Type.Resize and obj is self.ui.widget_viewTools:
            self.updateAdjustHintVisibility()
        elif (
            event.type() == QEvent.Type.Resize
            and obj is self.ui.comboBox_camera_source
            and hasattr(self, "sourceIndexAtPopup")
        ):
            self.updateSourceBar()
        elif (
            event.type() == QEvent.Type.Show
            and obj is self.ui.comboBox_camera_source.view()
        ):
            # picking the open file, stream or screen again chooses another one
            self.sourceIndexAtPopup = self.ui.comboBox_camera_source.currentIndex()
        elif event.type() == QEvent.Type.LayoutRequest and obj is self.ui.frame:
            # its minimum width changed (fonts, language, a label's text)
            self.fitLeftPaneWidth()
        return super().eventFilter(obj, event)

    def changeEvent(self, event):
        # File > Appearance or the system switched between light and dark: the
        # state colours follow the palette
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
        ) and hasattr(self, "statusBarWidgets"):
            self.updatePauseUi()
            self.applyViewerStyles()
            self.refreshLiveStatus()
        super().changeEvent(event)

    def changeLanguage(self, locale):
        locale_file = resource_path("translations", f"scoresight_{locale}.qm")
        logger.info(f"Changing language to {locale_file}")
        if not self.translator.load(locale_file):
            logger.error(f"Could not load translation for {locale_file}")
            return
        # used at the next start instead of the system language
        self.globalSettingsChanged("language", locale)
        for action in self.language_actions.actions():
            action.setChecked(action.data() == locale)
        appInstance = QApplication.instance()
        if appInstance:
            logger.info(f"installing translator for {locale}")
            appInstance.installTranslator(self.translator)
            scene_name = self.ui.lineEdit_sceneName.text()
            speed = self.ui.toolButton_speed.text()
            try:
                self.ui.retranslateUi(self)
            except Exception as e:
                logger.error(f"Error retranslating UI: {e}")
            # retranslateUi resets these texts to their .ui defaults
            self.browserEndpointsTemplate = self.ui.label_8.text()
            self.ui.lineEdit_sceneName.setText(scene_name)
            self.ui.toolButton_speed.setText(speed)
            self.vmixUiHandler.restoreUiState()
            self.unoUiHandler.restoreUiState()
            self.applyRuntimeTexts()

    def toggleUpdateOnChange(self, value):
        self.globalSettingsChanged("update_on_change", value)
        if self.image_viewer:
            self.image_viewer.setUpdateOnChange(value)

    def importConfiguration(self):
        # open a file dialog to select a configuration file
        file, _ = QFileDialog.getOpenFileName(
            self, "Open Configuration File", "", "Configuration Files (*.json)"
        )
        if not file:
            return
        # load the configuration from the file
        if not self.detectionTargetsStorage.loadBoxesFromFile(file):
            # show an error qmessagebox
            logger.error("Error loading configuration file")
            QMessageBox.critical(
                self,
                "Error",
                "Error loading configuration file",
                QMessageBox.StandardButton.Ok,
            )
            return

    def exportConfiguration(self):
        # open a file dialog to select the output file
        file, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration File", "", "Configuration Files (*.json)"
        )
        if not file:
            return
        # save the configuration to the file
        self.detectionTargetsStorage.saveBoxesToFile(file)

    def openOCRTrainingDataDialog(self):
        # open the OCR training data dialog
        dialog = OCRTrainingDataDialog()
        dialog.exec()

    def openConfigurationFolder(self):
        # open the configuration folder (SCORESIGHT_DATA_DIR aware) in the file
        # explorer
        data_dir = get_data_dir()
        os.makedirs(data_dir, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(data_dir))

    def toggleOSD(self, value):
        """Stats (View > Statistics overlay): the viewer follows the setting."""
        self.ui.actionStatsOverlay.setChecked(value)
        self.globalSettingsChanged(SHOW_OSD_SETTING, bool(value))

    def resetZoom(self):
        if self.image_viewer:
            self.image_viewer.resetZoom()

    def detectionCadenceChanged(self, detections_per_second):
        # the capture thread follows the detection_cadence setting
        self.globalSettingsChanged("detection_cadence", detections_per_second)

    def updateSliderReadouts(self, *_):
        """Show the values of the Detections / s and Save / s sliders."""
        for slider, label in (
            (
                self.ui.horizontalSlider_detectionCadence,
                self.ui.label_detectionCadenceValue,
            ),
            (self.ui.horizontalSlider_aggsPerSecond, self.ui.label_aggsPerSecondValue),
        ):
            text = QCoreApplication.translate("MainWindow", "{value} /s").format(
                value=slider.value()
            )
            widest = QCoreApplication.translate("MainWindow", "{value} /s").format(
                value=slider.maximum()
            )
            label.setText(text)
            label.setMinimumWidth(
                QFontMetrics(label.font()).horizontalAdvance(widest) + 2
            )
            slider.setAccessibleDescription(text)

    def refreshLiveStatus(self):
        """Once a second (and when an output is turned on or off): the
        outputs' statuses, the status bar, and the boxes list (the readings'
        ages)."""
        now = time.monotonic()
        if now - self.lanAddressCheckedAt > 30:
            # the network may have changed (no traffic: a route lookup)
            lan_address = primary_lan_address()
            self.lanAddressCheckedAt = now
            if lan_address != self.lanAddress:
                self.lanAddress = lan_address
                self.updateBrowserEndpoints()
        outputs = self.refreshDestinations(now)
        snapshot = self.statusSnapshot(now, outputs)
        self.statusBarWidgets.update(snapshot)
        self.updateSourceHealth(snapshot.source_state)
        self.updateFirstRunCard(outputs)
        cadence = self.ui.horizontalSlider_detectionCadence.value()
        # stale after 20 detection cycles (at least 10 s)
        self.readingDelegate.setStaleAfter(20.0 / max(cadence, 0.1))
        self.ui.tableWidget_boxes.viewport().update()

    def statusSnapshot(
        self,
        now: float | None = None,
        outputs: list[DestinationStatus] | None = None,
    ) -> StatusSnapshot:
        """What the status bar shows, from what the window already knows."""
        now = time.monotonic() if now is None else now
        if outputs is None:
            outputs = self.destinationStatuses(now)
        values = {"outputs": tuple(outputs), "now": now}
        viewer = self.image_viewer
        if viewer is not None:
            values["source_name"] = source_display_name(viewer.getCameraInfo())
            thread = getattr(viewer, "timerThread", None)
            # the capture thread's counters (written by it, read here)
            values["source_state"] = source_state(
                has_source=True,
                error=bool(self.sourceError),
                first_frame=getattr(viewer, "firstFrameReceived", False),
                now=now,
                last_frame_at=getattr(thread, "last_frame_timestamp", None),
                fps=getattr(thread, "fps", None),
                nominal_fps=getattr(thread, "nominal_fps", None),
                failed_reads=getattr(thread, "retry_count", 0) or 0,
            )
            frame_size = getattr(thread, "frame_size", None)
            if frame_size:
                values["resolution"] = tuple(frame_size)
            values["fps"] = getattr(thread, "fps", None)
            values["nominal_fps"] = getattr(thread, "nominal_fps", None)
            values["ocr_rate"] = getattr(thread, "ups", None)
            interval = getattr(thread, "update_frame_interval", None)
            if interval:
                values["ocr_target"] = round(1000.0 / max(interval, 1), 2)
        else:
            values["source_state"] = SOURCE_NONE
        if self.outputsPausedMonotonic is not None:
            values["paused_seconds"] = now - self.outputsPausedMonotonic
        if self.ui.actionCollectTrainingData.isChecked():
            values["collecting_training_data"] = True
            values["training_data_folder"] = (
                ocr_training_data_options.ocr_training_data_folder
            )
        port = get_http_server_port()
        if port is None:
            values["http_port"] = self.http_port
        else:
            urls = http_server_urls(port, self.lanAddress)
            values["http_url"] = urls[0]
            values["http_urls"] = urls
            values["http_port"] = port
        return StatusSnapshot(**values)

    # --- the outputs: destinations and their status --------------------------------

    def setupDestinations(self):
        """The destinations list: a row per output (with its switch and status)
        that shows the output's page below it."""
        view = self.ui.listView_destinations
        self.destinationsModel = DestinationsModel(self)
        self.destinationDelegate = DestinationDelegate(view)
        view.setModel(self.destinationsModel)
        view.setItemDelegate(self.destinationDelegate)
        view.selectionModel().currentRowChanged.connect(self.destinationSelected)
        view.setCurrentIndex(self.destinationsModel.index(0, 0))
        self.destinationsModel.toggleRequested.connect(self.destinationToggleRequested)
        self.ui.frame_destinationStatus.hide()
        self.updateDestinationsListHeight()
        # the controls the switches mirror: show their changes right away
        for signal in (
            self.ui.pushButton_startvmix.toggled,
            self.ui.toolButton_toggleUno.toggled,
            self.ui.checkBox_enableOutAPI.toggled,
        ):
            signal.connect(lambda *_: self.refreshLiveStatus())

    def updateDestinationsListHeight(self):
        """The destinations list shows every destination without scrolling."""
        view = self.ui.listView_destinations
        row_height = self.destinationDelegate.rowHeight(view.font())
        view.setFixedHeight(
            self.destinationsModel.rowCount() * row_height + 2 * view.frameWidth()
        )

    def destinationSelected(self, current, previous=None):
        if current.isValid():
            self.ui.stackedWidget_outputs.setCurrentIndex(current.row())
        self.updateDestinationDetails()

    def showDestination(self, key: str):
        """Select a destination (e.g. clicked in the status bar): its page shows,
        and the left column scrolls to it."""
        view = self.ui.listView_destinations
        view.setCurrentIndex(
            self.destinationsModel.index(self.destinationsModel.rowOf(key), 0)
        )
        self.ui.scrollArea_left.ensureWidgetVisible(self.ui.widget_outputs, 0, 0)
        view.setFocus(Qt.FocusReason.OtherFocusReason)

    def destinationToggleRequested(self, key: str, on: bool):
        """A destination's switch was clicked: operate the output's own control,
        which stays the source of truth (the switch shows its state)."""
        if key == output_status.FILES:
            if on:
                # a modal dialog: not from inside the list's event handling
                QTimer.singleShot(0, self.selectOutputFolder)
            else:
                self.clearOutputFolder()
        elif key == output_status.OBS:
            if on:
                self.openOBSConnectModal()
            else:
                self.disconnectObs()
        elif key == output_status.VMIX:
            self.ui.pushButton_startvmix.setChecked(on)
        elif key == output_status.UNO:
            self.ui.toolButton_toggleUno.setChecked(on)
        elif key == output_status.API:
            self.ui.checkBox_enableOutAPI.setChecked(on)
        self.refreshLiveStatus()

    def destinationStatuses(self, now: float) -> list[DestinationStatus]:
        """The status of every output, from snapshots (nothing here waits for
        the network)."""
        port = get_http_server_port()
        urls = http_server_urls(port, self.lanAddress) if port is not None else ()
        vmix = self.vmixUiHandler.vmixUpdater
        uno = self.unoUiHandler.unoUpdater
        method_index = self.ui.comboBox_outApiMethod.currentIndex()
        encoding_index = self.ui.comboBox_api_encode.currentIndex()
        return [
            output_status.files_status(
                self.out_folder, self.fileOutput.status(), self.outputFolderLost
            ),
            output_status.http_status(
                port, self.http_port, urls, http_server_stats(now)
            ),
            self.obsDestinationStatus(),
            output_status.vmix_status(
                vmix.running,
                vmix.host,
                vmix.port,
                vmix.input_number,
                vmix.field_mapping,
                vmix.status(),
            ),
            output_status.uno_status(
                uno.running, uno.endpoint, uno.field_mapping, uno.status()
            ),
            output_status.api_status(
                self.ui.checkBox_enableOutAPI.isChecked(),
                self.ui.lineEdit_api_url.text(),
                OUT_API_METHODS[method_index]
                if 0 <= method_index < len(OUT_API_METHODS)
                else "POST",
                OUT_API_ENCODINGS[encoding_index]
                if 0 <= encoding_index < len(OUT_API_ENCODINGS)
                else OUT_API_ENCODINGS[0],
                out_api_status(),
            ),
        ]

    def obsDestinationStatus(self) -> DestinationStatus:
        client = self.obs_websocket_client
        address = None
        if client is not None:
            address = self.obsAddress or obs_client_address(client) or "OBS"
        has_sources = any(
            (box.settings or {}).get("obs_source_name")
            for box in self.detectionTargetsStorage.get_data()
        )
        return output_status.obs_status(
            address,
            self.obsConnecting,
            self.obsConnectError,
            obs_output_status() if client is not None else None,
            connected_at=self.obsConnectedAt,
            has_sources=has_sources,
            connect_target=self.obsConnectTarget,
        )

    def refreshDestinations(self, now: float | None = None) -> list[DestinationStatus]:
        """Show every output's status in the destinations list."""
        now = time.monotonic() if now is None else now
        statuses = self.destinationStatuses(now)
        self.destinationsModel.setStatuses(statuses)
        # the times of the last activity
        self.ui.listView_destinations.viewport().update()
        self.updateDestinationDetails(now)
        return statuses

    def updateDestinationDetails(self, now: float | None = None):
        """Over the selected destination's page: its problem, if it has one, and
        what to do about it."""
        now = time.monotonic() if now is None else now
        frame = self.ui.frame_destinationStatus
        label = self.ui.label_destinationStatus
        index = self.ui.listView_destinations.currentIndex()
        status = index.data(STATUS_ROLE) if index.isValid() else None
        if status is None or not status.has_problem:
            frame.hide()
            return
        palette = self.palette()
        color = theme.color(STATE_COLORS[status.state], palette)
        text = (
            f'<b><span style="color:{color.name()}">{STATE_GLYPHS[status.state]}'
            f"</span> {html.escape(status.detail, quote=False)}</b>"
        )
        if status.hint:
            text += f"<br>{html.escape(status.hint, quote=False)}"
        if label.text() != text:
            label.setText(text)
        label.setToolTip(status_tooltip(status, now))
        label.setAccessibleName(
            f"{output_status.destination_name(status.key)}: {status.detail}"
        )
        style_sheet = (
            "QFrame#frame_destinationStatus {"
            f" background-color: {theme.tint(STATE_COLORS[status.state], palette).name()};"
            f" border: 1px solid {color.name()}; border-left: 4px solid {color.name()};"
            " border-radius: 3px; }"
        )
        if frame.styleSheet() != style_sheet:
            frame.setStyleSheet(style_sheet)
        frame.show()

    def ocrModelChanged(self, index: int | str):
        ocrModel = None
        if index == 4:
            # load a custom OCR model
            file, _ = QFileDialog.getOpenFileName(
                self, "Open OCR Model File", "", "OCR Model Files (*.traineddata)"
            )
            if not file:
                return
            # get absolute file path
            file = path.abspath(file)
            self.globalSettingsChanged("ocr_model", file)
            ocrModel = file
        elif isinstance(index, int):
            self.globalSettingsChanged("ocr_model", index)
            ocrModel = index
        elif isinstance(index, str):
            # check if the index is a valid existing file
            if path.exists(index):
                self.globalSettingsChanged("ocr_model", index)
                ocrModel = index

        # update the ocr model in the text detector
        if (
            self.image_viewer
            and self.image_viewer.timerThread
            and self.image_viewer.timerThread.textDetector
        ):
            self.image_viewer.timerThread.textDetector.setOcrModel(ocrModel)

    def openLogsDialog(self):
        if self.log_dialog is None:
            # open the logs dialog
            self.log_dialog = LogViewerDialog()
            self.log_dialog.setWindowTitle("Logs")

        # show the dialog, non modal
        self.log_dialog.show()

    def checkForUpdates(self, manual: bool):
        """Check GitHub for a newer release on a background thread. The automatic
        check at startup honors "Don't check for updates at startup"; a manual
        check (File > Check for Updates) always runs and always shows a result."""
        if self.update_check_running:
            # the running check shows its result to this request too
            self.update_check_manual_pending |= manual
            return
        if not manual and not update_checks_enabled():
            logger.info("Update checks at startup are disabled")
            return
        self.update_check_running = True
        run_in_background(
            "update check",
            lambda: check_for_updates(),
            lambda result: self.update_check_finished.emit(result, manual),
        )

    @Slot(object, bool)
    def updateCheckFinished(self, result, manual: bool):
        self.update_check_running = False
        manual = manual or self.update_check_manual_pending
        self.update_check_manual_pending = False
        if not isinstance(result, UpdateCheckResult):
            result = UpdateCheckResult(__version__, error="the update check failed")
        if not (manual or result.update_available):
            return
        if self.update_dialog is not None:
            try:
                self.update_dialog.close()
            except RuntimeError:
                pass  # already closed (and deleted)
        self.update_dialog = show_update_dialog(result, self)

    def createAboutDialog(self) -> QDialog:
        about_dialog = QDialog(self)
        about_dialog.ui = Ui_About()
        about_dialog.ui.setupUi(about_dialog)
        about_dialog.setWindowTitle("About ScoreSight")
        about_dialog.ui.label_version.setText(
            QCoreApplication.translate("MainWindow", "Version {version}").format(
                version=__version__
            )
        )
        return about_dialog

    def openAboutDialog(self):
        about_dialog = self.createAboutDialog()
        about_dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        about_dialog.open()

    def toggleStabilize(self):
        if not self.image_viewer:
            return
        # start or stop the stabilization
        self.image_viewer.toggleStabilization(self.ui.pushButton_stabilize.isChecked())

    def toggleStopUpdates(self, value):
        """Pause outputs (checked) or resume them. The readings keep updating in
        the window; only the outputs freeze."""
        self.updateOCRResults = not value
        if value:
            self.outputsPausedAt = datetime.now()
            self.outputsPausedMonotonic = time.monotonic()
            self.resendAfterPause = set()
            logger.info("Outputs paused")
        else:
            if self.outputsPausedAt is not None:
                logger.info("Outputs resumed")
                # values that changed while paused are unchanged readings now
                self.resendAfterPause = {
                    box.name for box in self.detectionTargetsStorage.get_data()
                }
            self.outputsPausedAt = None
            self.outputsPausedMonotonic = None
        self.updatePauseUi()
        self.refreshLiveStatus()

    def updatePauseUi(self):
        """Show whether the outputs are paused: the button (amber while paused),
        the banner over the viewer, the window title and the boxes list."""
        paused = self.ui.pushButton_stopUpdates.isChecked()
        button = self.ui.pushButton_stopUpdates
        # QCoreApplication.translate falls back to the source text when a
        # translation is missing (QTranslator.translate returns "")
        button.setText(
            QCoreApplication.translate("MainWindow", "Resume outputs")
            if paused
            else QCoreApplication.translate("MainWindow", "Pause outputs")
        )
        palette = self.palette()
        amber = theme.color("paused", palette).name()
        on_amber = theme.on_color(palette).name()
        button.setIcon(
            theme.media_icon("play", theme.on_color(palette))
            if paused
            else theme.media_icon("pause", theme.button_text_color(palette))
        )
        button.setStyleSheet(
            "QPushButton#pushButton_stopUpdates:checked {"
            f" background-color: {amber}; color: {on_amber};"
            f" border: 1px solid {amber}; border-radius: 3px;"
            " padding: 4px 8px; font-weight: bold; }"
        )

        banner = self.ui.frame_pausedBanner
        banner.setVisible(paused)
        if paused and self.outputsPausedAt is not None:
            self.ui.label_pausedBanner.setText(
                QCoreApplication.translate(
                    "MainWindow",
                    "<b>Outputs paused</b> since {time}. Your graphics show the "
                    "last values sent; the readings here keep updating.",
                ).format(time=self.outputsPausedAt.strftime("%H:%M:%S"))
            )
        banner.setStyleSheet(
            "QFrame#frame_pausedBanner {"
            f" background-color: {theme.paused_tint(palette).name()};"
            f" border: 1px solid {amber}; border-left: 4px solid {amber}; }}"
        )
        self.ui.pushButton_resumeOutputs.setIcon(
            theme.media_icon("play", theme.button_text_color(palette))
        )
        self.vmixUiHandler.refreshToggleButton()
        self.unoUiHandler.refreshToggleButton()
        self.updateWindowTitle()
        self.readingDelegate.setPaused(paused)
        self.ui.tableWidget_boxes.viewport().update()

    def selectOutputFolder(self):
        # open a Qt dialog to select the output folder
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            fetch_data("scoresight.json", "output_folder", ""),
            options=QFileDialog.Option.ShowDirsOnly,
        )
        if folder and len(folder) > 0:
            self.setOutputFolder(folder)

    def setOutputFolder(self, folder: str):
        self.ui.lineEdit_folder.setText(folder)
        self.out_folder = folder
        self.outputFolderLost = None
        self.globalSettingsChanged("output_folder", folder)
        # write the current values to the new folder right away
        self.scheduleFileOutputFlush()
        self.refreshLiveStatus()

    def clearOutputFolder(self):
        # clear the output folder
        self.ui.lineEdit_folder.setText("")
        self.out_folder = None
        self.outputFolderLost = None
        remove_data("scoresight.json", "output_folder")
        self.refreshLiveStatus()

    # --- the boxes list -------------------------------------------------------------

    def appendBoxRow(self, name: str) -> QTableWidgetItem:
        """Add a row for a box to the boxes list; returns its name item."""
        table = self.ui.tableWidget_boxes
        row = table.rowCount()
        table.insertRow(row)
        item = QTableWidgetItem(name)
        table.setItem(row, 0, item)
        # the reading: enabled (so it isn't drawn greyed out), not selectable
        # or editable (the name item stays the current item)
        valueItem = QTableWidgetItem()
        valueItem.setFlags(Qt.ItemFlag.ItemIsEnabled)
        table.setItem(row, 1, valueItem)
        return item

    def boxNameItem(self, name: str) -> QTableWidgetItem | None:
        """The name item (column 0) of a box in the boxes list. findItems also
        matches the Value column, which may hold the same text."""
        for item in self.ui.tableWidget_boxes.findItems(
            name, Qt.MatchFlag.MatchExactly
        ):
            if item.column() == 0:
                return item
        return None

    def boxValueItem(self, name: str) -> QTableWidgetItem | None:
        """The Value item (column 1) of a box in the boxes list."""
        item = self.boxNameItem(name)
        if item is None:
            return None
        return self.ui.tableWidget_boxes.item(item.row(), 1)

    def nameItemOfRow(self, item: QTableWidgetItem | None) -> QTableWidgetItem | None:
        if item is None or item.column() == 0:
            return item
        return self.ui.tableWidget_boxes.item(item.row(), 0)

    def keepNameCellCurrent(self, row, column, previous_row, previous_column):
        # e.g. a click on a reading or the arrow keys: the row's name becomes
        # the current item
        if column != 0 and row >= 0:
            self.ui.tableWidget_boxes.setCurrentCell(row, 0)

    def detectionTargetsChanged(self, detectionTargets: list[TextDetectionTarget]):
        for box in detectionTargets:
            logger.debug(f"Change: Detection target: {box.name}")
            # change the list icon to green checkmark
            item = self.boxNameItem(box.name)
            if item is None:
                logger.warning(f"Item not found: {box.name}. Adding it to the list.")
                # add the item to the list
                item = self.appendBoxRow(box.name)

            if box.settings is None or not box.settings["templatefield"]:
                # this is a detection target
                item.setIcon(QIcon(resource_path("icons", "circle-check.svg")))
                item.setData(Qt.ItemDataRole.UserRole, "checked")
            else:
                # this is a template field
                item.setIcon(QIcon(resource_path("icons", "template-field.svg")))
                item.setData(Qt.ItemDataRole.UserRole, "templatefield")

        self.vmixUiHandler.updatevMixTable(detectionTargets)
        self.unoUiHandler.updateUNOTable(detectionTargets)
        # Note: results.csv is not touched here. data_changed fires on every box
        # click and settings tweak; file_output starts a new CSV file by itself
        # when the set of boxes changes.

    def scheduleBoxesSave(self, *_):
        # (re)start the timer: a burst of edits (e.g. dragging a slider) is
        # written once
        self.boxesSaveTimer.start()

    def saveBoxes(self):
        self.boxesSaveTimer.stop()
        self.detectionTargetsStorage.saveBoxesToStorage()

    def listItemClicked(self, item):
        # a click on a reading selects its box
        if item.column() != 0:
            item = self.nameItemOfRow(item)
            if item is None:
                return
            self.ui.tableWidget_boxes.setCurrentItem(item)
        user_role = item.data(Qt.ItemDataRole.UserRole)
        if user_role in ["checked", "templatefield"] and item.column() == 0:
            # enable the remove box button and disable the make box button
            self.ui.pushButton_makeBox.setEnabled(False)
            self.ui.pushButton_removeBox.setEnabled(user_role == "checked")
            self.ui.groupBox_target_settings.setEnabled(user_role == "checked")
            self.boxSettingsUiHandler.populateSettings(item.text())
        else:
            # enable the make box button and disable the remove box button
            self.ui.pushButton_removeBox.setEnabled(False)
            self.ui.pushButton_makeBox.setEnabled(item.column() == 0)
            self.ui.groupBox_target_settings.setEnabled(False)
            self.boxSettingsUiHandler.populateSettings("")

        if item.column() == 0:
            # if this is not a default box - enable the template field checkbox
            if item.text() not in [box["name"] for box in default_boxes]:
                self.ui.checkBox_templatefield.setEnabled(True)
                self.ui.lineEdit_templatefield.setEnabled(True)
            else:
                self.ui.checkBox_templatefield.setEnabled(False)
                self.ui.lineEdit_templatefield.setEnabled(False)

        # notify the image viewer to select the box
        if self.image_viewer:
            self.image_viewer.selectBox(item.text())

    def openOBSConnectModal(self):
        if self.obs_connect_modal is not None and self.obs_connect_modal.isVisible():
            self.obs_connect_modal.raise_()
            self.obs_connect_modal.activateWindow()
            return
        if self.obs_connect_modal is not None:
            # a new dialog, in the current language
            self.obs_connect_modal.deleteLater()

        # disable OBS options
        self.ui.lineEdit_sceneName.setEnabled(False)
        self.ui.checkBox_recreate.setEnabled(False)
        self.ui.pushButton_createOBSScene.setEnabled(False)

        # load the ui from "connect_obs.ui"; a child of the main window, so it
        # stays in front of it
        self.obs_modal_ui = Ui_ConnectObs()
        self.obs_connect_modal = QDialog(self)
        self.obs_modal_ui.setupUi(self.obs_connect_modal)
        self.obs_connect_modal.setWindowTitle(
            QCoreApplication.translate("MainWindow", "Connect to OBS")
        )

        # connect the "connect" button to a function
        self.obs_modal_ui.pushButton_connect.clicked.connect(
            lambda: self.connectObs(from_dialog=True)
        )
        password = self.obs_modal_ui.lineEdit_password
        self.obs_modal_ui.checkBox_showPassword.toggled.connect(
            lambda show: password.setEchoMode(
                QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password
            )
        )
        # closed without connecting (Cancel): the scene controls are usable
        # again with the current connection
        self.obs_connect_modal.rejected.connect(self.obsConnectDialogClosed)

        # load the saved data from scoresight.json
        obs_data = fetch_data("scoresight.json", "obs")
        if obs_data:
            self.obs_modal_ui.lineEdit_ip.setText(obs_data["ip"])
            self.obs_modal_ui.lineEdit_port.setText(obs_data["port"])
            self.obs_modal_ui.lineEdit_password.setText(obs_data["password"])
        # show the modal
        self.obs_connect_modal.show()
        # focus the connect button
        self.obs_modal_ui.pushButton_connect.setFocus()

    def obsConnectDialogClosed(self):
        if not self.obs_modal_ui.pushButton_connect.isEnabled():
            # Cancel while connecting: ignore that attempt's result (it would
            # replace the current connection and store the cancelled settings)
            self.obs_connect_attempt += 1
            self.obsConnecting = None
        connected = self.obs_websocket_client is not None
        self.ui.lineEdit_sceneName.setEnabled(connected)
        self.ui.checkBox_recreate.setEnabled(connected)
        self.ui.pushButton_createOBSScene.setEnabled(connected)
        self.updateObsUi()
        self.refreshLiveStatus()

    @staticmethod
    def obsTarget(connection_info) -> str | None:
        """The "host:port" of an OBS connection's settings."""
        if not isinstance(connection_info, dict):
            return None
        host = str(connection_info.get("ip") or "").strip() or "localhost"
        port = str(connection_info.get("port") or "").strip()
        return f"{host}:{port}" if port else host

    def connectObs(self, from_dialog: bool = False):
        """Open a websocket connection to OBS, with the connect dialog's fields or
        the saved connection. Connecting can take seconds (or time out), so it runs
        on a background thread; obsConnectionResult handles the outcome."""
        if from_dialog:
            connection_info = {
                "ip": self.obs_modal_ui.lineEdit_ip.text(),
                "port": self.obs_modal_ui.lineEdit_port.text(),
                "password": self.obs_modal_ui.lineEdit_password.text(),
            }
            self.obs_modal_ui.pushButton_connect.setEnabled(False)
            self.obs_modal_ui.label_error.setText(
                QCoreApplication.translate("MainWindow", "Connecting...")
            )
            self.obs_modal_ui.label_error.setToolTip("")
        else:
            connection_info = fetch_data("scoresight.json", "obs")
            if not connection_info:
                return
        # a newer attempt supersedes the ones still running
        self.obs_connect_attempt += 1
        attempt = self.obs_connect_attempt
        self.obsConnecting = self.obsTarget(connection_info)

        def attempt_connection():
            client = open_obs_websocket(connection_info)
            # why it failed (recorded on this thread)
            return client, None if client else last_connect_error()

        run_in_background(
            "OBS connection",
            attempt_connection,
            lambda result: self.obs_connection_result.emit(
                result, attempt, from_dialog, connection_info
            ),
        )
        self.updateObsUi()
        if hasattr(self, "statusBarWidgets"):
            self.refreshLiveStatus()

    @Slot(object, int, bool, object)
    def obsConnectionResult(self, result, attempt, from_dialog, connection_info):
        client, error = result if isinstance(result, tuple) else (result, None)
        if attempt != self.obs_connect_attempt:
            self.closeObsClient(client)
            return
        self.obsConnecting = None
        if from_dialog and self.obs_connect_modal is not None:
            self.obs_modal_ui.pushButton_connect.setEnabled(True)
        if not client:
            target = self.obsTarget(connection_info)
            self.obsConnectError = error or ErrorInfo(ConnectionError, "")
            self.obsConnectTarget = target
            # show error in label_error
            if from_dialog and self.obs_connect_modal is not None:
                problem = describe_error(
                    output_status.OBS, self.obsConnectError, target
                )
                self.obs_modal_ui.label_error.setText(
                    QCoreApplication.translate("MainWindow", "Cannot connect to OBS")
                    + "\n"
                    + problem.detail
                )
                self.obs_modal_ui.label_error.setToolTip(problem.hint)
            self.updateObsUi()
            self.refreshLiveStatus()
            return

        # connection was successful
        self.closeObsClient(self.obs_websocket_client)
        self.obs_websocket_client = client
        self.obsAddress = obs_client_address(client) or self.obsTarget(connection_info)
        self.obsConnectedAt = time.monotonic()
        self.obsConnectError = None
        # send every current value to the (new) connection
        self.obs_last_sent.clear()
        if from_dialog:
            store_data("scoresight.json", "obs", connection_info)
            if self.obs_connect_modal is not None:
                self.obs_connect_modal.close()
        if fetch_data("scoresight.json", OBS_AUTO_CONNECT_SETTING, True) is not True:
            # connected again after a Disconnect: also at the next start
            store_data("scoresight.json", OBS_AUTO_CONNECT_SETTING, True)

        self.ui.lineEdit_sceneName.setEnabled(True)
        self.ui.checkBox_recreate.setEnabled(True)
        self.ui.pushButton_createOBSScene.setEnabled(True)

        logger.info("OBS: Connected")
        self.updateObsUi()
        self.refreshLiveStatus()

    def disconnectObs(self):
        """Close the connection to OBS (or stop connecting). The saved connection
        is kept for the connect dialog, but isn't opened at the next start until
        the user connects again."""
        # ignore connection attempts that are still running
        self.obs_connect_attempt += 1
        self.obsConnecting = None
        self.obsConnectError = None
        if self.obs_connect_modal is not None and self.obs_connect_modal.isVisible():
            # the dialog's attempt (if any) was cancelled with it
            self.obs_modal_ui.pushButton_connect.setEnabled(True)
            self.obs_modal_ui.label_error.setText("")
        client = self.obs_websocket_client
        self.obs_websocket_client = None
        self.obsAddress = None
        self.obsConnectedAt = None
        self.obs_last_sent.clear()
        self.closeObsClient(client)
        if fetch_data("scoresight.json", OBS_AUTO_CONNECT_SETTING, True) is not False:
            store_data("scoresight.json", OBS_AUTO_CONNECT_SETTING, False)
        if client is not None:
            logger.info("OBS: Disconnected")
        self.ui.lineEdit_sceneName.setEnabled(False)
        self.ui.checkBox_recreate.setEnabled(False)
        self.ui.pushButton_createOBSScene.setEnabled(False)
        self.updateObsUi()
        self.refreshLiveStatus()

    def updateObsUi(self):
        """The OBS page's buttons show the connection: Connect OBS, Connecting...
        or Change connection..., and Disconnect while connected (or
        connecting)."""
        connected = self.obs_websocket_client is not None
        connecting = self.obsConnecting is not None
        button = self.ui.pushButton_connectObs
        if connected:
            button.setText(
                QCoreApplication.translate("MainWindow", "Change connection...")
            )
            button.setToolTip(
                QCoreApplication.translate(
                    "MainWindow",
                    "Connected to OBS at {target}. Click to connect to another OBS.",
                ).format(target=self.obsAddress or "?")
            )
        elif connecting:
            button.setText(QCoreApplication.translate("MainWindow", "Connecting..."))
            button.setToolTip(
                QCoreApplication.translate(
                    "MainWindow", "Connecting to OBS at {target}..."
                ).format(target=self.obsConnecting)
            )
        else:
            button.setText(QCoreApplication.translate("MainWindow", "Connect OBS"))
            button.setToolTip(
                QCoreApplication.translate(
                    "MainWindow", "Connect to the WebSocket server of OBS Studio"
                )
            )
        self.ui.pushButton_disconnectObs.setEnabled(connected or connecting)

    @staticmethod
    def closeObsClient(client):
        """Disconnect an OBS client that is replaced or no longer used, and stop
        its pending text updates. close_obs_websocket waits for an update in
        flight (bounded by the OBS timeout), so it runs off the GUI thread."""
        if client is None:
            return
        run_in_background(
            "OBS disconnect", partial(close_obs_websocket, client), lambda _: None
        )

    @Slot()
    def getSources(self):
        # Device enumeration (DirectShow/AVFoundation/V4L) and NDI discovery
        # take a while: run them on a background thread (#33).
        if self.sources_discovery_running:
            return
        self.sources_discovery_running = True
        self.ui.pushButton_refresh_sources.setEnabled(False)
        run_in_background(
            "source discovery",
            lambda: get_camera_info() or [],
            lambda sources: self.update_sources.emit(sources or []),
        )

    @Slot(list)
    def updateSources(self, camera_sources: list[CameraInfo]):
        # only the first discovery (at startup) counts
        startup_timing.mark("sources_discovered")
        self.sources_discovery_running = False
        if self.closing:
            # the discovery finished after the window was closed: don't reopen
            # the source
            return
        self.ui.pushButton_refresh_sources.setEnabled(True)
        self.reset_playing_source()
        combo = self.ui.comboBox_camera_source
        # Removing the current camera item moves the current index, which would
        # run sourceChanged (opening another camera, or the Screen Capture
        # dialog). Go to "none" instead: the viewer is closed, and
        # restoreSelectedSource reopens the stored source below.
        combo.blockSignals(True)
        combo.setCurrentIndex(SOURCE_INDEX_NONE)
        # clear all the items after "Screen Capture"
        for _ in range(FIRST_CAMERA_SOURCE_INDEX, combo.count()):
            combo.removeItem(FIRST_CAMERA_SOURCE_INDEX)
        # populate the combobox with the sources
        for source in camera_sources:
            combo.addItem(source.description, source)
        combo.blockSignals(False)
        self.updateSourceBar()
        self.fitSourceList()
        self.updateFirstRunCameraMenu()

        self.ui.comboBox_camera_source.setEnabled(True)
        currentIndexChangedSignal = QMetaMethod.fromSignal(
            self.ui.comboBox_camera_source.currentIndexChanged
        )
        if self.ui.comboBox_camera_source.isSignalConnected(currentIndexChangedSignal):
            self.ui.comboBox_camera_source.currentIndexChanged.disconnect()
        self.ui.comboBox_camera_source.currentIndexChanged.connect(self.sourceChanged)

        # enable the source view frame
        self.ui.frame_source_view.setEnabled(True)

        self.restoreSelectedSource()

    def restoreSelectedSource(self):
        """Reopen the source stored in "source_selected", if it is available."""
        source = stored_source_value(fetch_data("scoresight.json", "source_selected"))
        if source is None:
            return
        logger.info("Source selected from storage: %s", source)
        source_type = source["type"]
        value = source.get("value")
        index = None
        if source_type == CameraInfo.CameraType.FILE:
            if isinstance(value, str) and path.exists(value):
                index = SOURCE_INDEX_FILE
        elif source_type == CameraInfo.CameraType.URL:
            if isinstance(value, str) and value.strip():
                index = SOURCE_INDEX_URL
                value = value.strip()
        elif source_type == CameraInfo.CameraType.SCREEN_CAPTURE:
            windows = dict(
                (window_id, title) for title, window_id in self.listScreenCaptures()
            )
            if value == source_bar.ENTIRE_SCREEN or value in windows:
                index = SOURCE_INDEX_SCREEN_CAPTURE
                self.sourceWindowTitle = windows.get(value)
        else:
            index = self.findCameraSourceIndex(source)
        if index is None:
            logger.info("The stored source is not available")
            return

        self.ui.comboBox_camera_source.blockSignals(True)
        self.ui.comboBox_camera_source.setCurrentIndex(index)
        self.ui.comboBox_camera_source.blockSignals(False)
        self.source_name = value if index < FIRST_CAMERA_SOURCE_INDEX else None
        self.sourceSelectionSucessful()

    @staticmethod
    def screenCaptureWindows() -> list:
        """The windows a Screen Capture source can capture, as (title, id)."""
        # imported when first used: it loads pywin32 / pyobjc's Quartz, which
        # would slow down every start
        from screen_capture_source import ScreenCapture

        return ScreenCapture.list_windows()

    @staticmethod
    def listScreenCaptures() -> list:
        """The windows a Screen Capture source can capture, as (title, id), or
        none if they can't be listed."""
        try:
            return list(MainWindow.screenCaptureWindows())
        except Exception:
            logger.exception("Could not list the windows for screen capture")
            return []

    @staticmethod
    def screenCaptureWindowIds() -> list:
        return [window[1] for window in MainWindow.listScreenCaptures()]

    def findCameraSourceIndex(self, source: dict) -> int | None:
        """The combo box index of the discovered camera/NDI source matching a
        stored source: same type and id (uuid) and name, else same type and name."""
        candidates = []
        for index in range(
            FIRST_CAMERA_SOURCE_INDEX, self.ui.comboBox_camera_source.count()
        ):
            camera_info = self.ui.comboBox_camera_source.itemData(index)
            if (
                isinstance(camera_info, CameraInfo)
                and camera_info.type == source["type"]
                and camera_info.description == source.get("description")
            ):
                if camera_info.uuid == source.get("value"):
                    return index
                candidates.append(index)
        return candidates[0] if candidates else None

    @staticmethod
    def sourceToStore(camera_info: CameraInfo) -> dict:
        """The "source_selected" setting for a source."""
        if camera_info.type in (
            CameraInfo.CameraType.FILE,
            CameraInfo.CameraType.URL,
            CameraInfo.CameraType.SCREEN_CAPTURE,
        ):
            return {"type": camera_info.type, "value": camera_info.id}
        return {
            "type": camera_info.type,
            "value": camera_info.uuid,
            "description": camera_info.description,
        }

    def disconnectViewer(self):
        """Disconnect the main window's controls from the current image viewer."""
        viewer = self.connected_viewer
        self.connected_viewer = None
        if viewer is None:
            return
        for signal, slot in (
            (self.ui.pushButton_binary.clicked, viewer.toggleBinary),
            (viewer.four_corner_changed, self.updateFourCornerUi),
            (viewer.zoom_changed, self.updateZoomReadout),
        ):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass

    def closeImageViewer(self):
        """Close and delete the current image viewer.

        Closing stops its capture thread, waiting at most STOP_TIMEOUT_MS; a
        thread still blocked on its source then finishes in the background.
        Deleting the viewer is safe even then: the thread isn't a Qt child of
        the viewer (camera_thread keeps it alive until it finishes), and the
        viewer has already disconnected from it and from the settings."""
        viewer = self.image_viewer
        if viewer is None:
            return
        self.image_viewer = None
        self.sourceError = None
        self.disconnectViewer()
        # remove the image viewer from the layout frame_for_source_view_label
        self.ui.frame_for_source_view_label.layout().removeWidget(viewer)
        viewer.close()
        viewer.deleteLater()
        self.updateSourceBanner()
        self.updateFourCornerUi()
        self.updateZoomReadout()

    def reset_playing_source(self):
        self.closeImageViewer()
        self.sourceWindowTitle = None
        # the first-run card. It is hidden, never deleted: the .ui's
        # retranslateUi sets its texts (label_12 is its title) on a language
        # change.
        self.ui.frame_firstRun.show()
        self.updateSourceBar()
        self.updateFirstRunCard()

    def sourceChanged(self, index):
        # get the source name from the combobox
        self.source_name = None
        # an index change: picking the item again doesn't reopen its chooser
        self.sourceIndexAtPopup = None
        self.ui.groupBox_sb_info.setEnabled(False)
        self.ui.tableWidget_boxes.setEnabled(False)
        self.setViewToolsEnabled(False)
        index = self.ui.comboBox_camera_source.currentIndex()
        if index == SOURCE_INDEX_NONE:
            self.reset_playing_source()
            return
        if index in CHOOSER_SOURCE_INDEXES:
            chosen = self.askSourceValue(index)
            if chosen is None:
                # cancelled: no source (by index: its text is translated)
                self.ui.comboBox_camera_source.setCurrentIndex(SOURCE_INDEX_NONE)
                return
            self.source_name, self.sourceWindowTitle = chosen

        self.sourceSelectionSucessful()

    def askSourceValue(self, index: int) -> tuple | None:
        """Ask for the video file, the stream URL or the window to capture (the
        source combo box's item index): (value, window title or None), or None
        if cancelled."""
        if index == SOURCE_INDEX_FILE:
            logger.info("Open File selection dialog")
            # open a file dialog to select a video file
            file, _ = QFileDialog.getOpenFileName(
                self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mov)"
            )
            if not file or not path.exists(file):
                logger.error("No file selected")
                return None
            logger.info("File selected: %s", file)
            return file, None
        if index == SOURCE_INDEX_URL:
            # open a dialog to enter the url
            url_dialog = QDialog()
            ui_urlsource = Ui_UrlSource()
            ui_urlsource.setupUi(url_dialog)
            url_dialog.setWindowTitle("URL Source")
            # focus on url input
            ui_urlsource.lineEdit_url.setFocus()
            url_dialog.exec()  # wait for the dialog to close
            # check if the dialog was accepted
            if url_dialog.result() != QDialog.DialogCode.Accepted:
                return None
            # pasted URLs often carry spaces or a newline (#10)
            url = ui_urlsource.lineEdit_url.text().strip()
            return (url, None) if url else None
        if index == SOURCE_INDEX_SCREEN_CAPTURE:
            # open a dialog to select the screen
            screen_dialog = QDialog()
            ui_screencapture = Ui_ScreenCapture()
            ui_screencapture.setupUi(screen_dialog)
            # set width and height of the dialog
            screen_dialog.setFixedWidth(400)

            screen_dialog.setWindowTitle(
                QCoreApplication.translate(
                    "MainWindow", "Screen Capture Selection", None
                )
            )
            # populate comboBox_window with the available windows
            ui_screencapture.comboBox_window.clear()
            ui_screencapture.comboBox_window.addItem(
                QCoreApplication.translate(
                    "MainWindow", "Capture the entire screen", None
                ),
                source_bar.ENTIRE_SCREEN,
            )
            for window in self.screenCaptureWindows():
                ui_screencapture.comboBox_window.addItem(window[0], window[1])
            screen_dialog.exec()
            # check if the dialog was accepted
            if screen_dialog.result() != QDialog.DialogCode.Accepted:
                return None
            # get the window ID from the comboBox_window
            window_id = ui_screencapture.comboBox_window.currentData()
            title = (
                None
                if window_id == source_bar.ENTIRE_SCREEN
                else ui_screencapture.comboBox_window.currentText()
            )
            return window_id, title
        return None

    def itemSelected(self, item_name):
        if item_name is None:
            # clear the selected item
            self.ui.tableWidget_boxes.clearSelection()
            self.ui.groupBox_target_settings.setEnabled(False)
            self.boxSettingsUiHandler.populateSettings("")
            return
        # select the item in the tableWidget_boxes
        item = self.boxNameItem(item_name)
        if item is None:
            return
        item.setSelected(True)
        self.ui.tableWidget_boxes.setCurrentItem(item)
        self.listItemClicked(item)

    def fourCornersApplied(self, corners):
        # a correction was restored or picked
        self.updateFourCornerUi()

    def sourceSelectionSucessful(self):
        if self.ui.comboBox_camera_source.currentIndex() == 0:
            return

        self.ui.frame_source_view.setEnabled(False)

        if self.ui.comboBox_camera_source.currentIndex() == 1:
            if self.source_name is None or not path.exists(self.source_name):
                logger.error("No file selected")
                self.ui.comboBox_camera_source.setCurrentIndex(0)
                return
            logger.info("Loading file selected: %s", self.source_name)
            camera_info = CameraInfo(
                self.source_name,
                self.source_name,
                self.source_name,
                CameraInfo.CameraType.FILE,
            )
        elif self.ui.comboBox_camera_source.currentIndex() == 2:
            if self.source_name is None or self.source_name == "":
                logger.error("No url entered")
                self.ui.comboBox_camera_source.setCurrentIndex(0)
                return
            logger.info("Loading url: %s", self.source_name)
            camera_info = CameraInfo(
                self.source_name,
                self.source_name,
                self.source_name,
                CameraInfo.CameraType.URL,
            )
        elif self.ui.comboBox_camera_source.currentIndex() == 3:
            if self.source_name is None:
                logger.error("No screen capture selected")
                self.ui.comboBox_camera_source.setCurrentIndex(0)
                return
            logger.info("Loading screen capture: %s", self.source_name)
            camera_info = CameraInfo(
                self.source_name,
                self.source_name,
                self.source_name,
                CameraInfo.CameraType.SCREEN_CAPTURE,
            )
        else:
            if self.ui.comboBox_camera_source.currentData() is None:
                return

            logger.info(
                "Loading camera: %s", self.ui.comboBox_camera_source.currentText()
            )
            camera_info = self.ui.comboBox_camera_source.currentData()

        # remember the source (with its type) for the next start
        self.globalSettingsChanged("source_selected", self.sourceToStore(camera_info))

        self.closeImageViewer()
        self.ui.frame_firstRun.hide()

        # set the pixmap to the image viewer
        self.image_viewer = ImageViewer(
            camera_info,
            self.fourCornersApplied,
            self.detectionTargetsStorage,
            self.itemSelected,
            start=False,
        )
        # a new capture plays at x1
        self.ui.toolButton_speed.setText(source_bar.speed_text(1))
        self.image_viewer.first_frame_received_signal.connect(
            self.cameraConnectedEnableUI
        )
        self.image_viewer.error_signal.connect(self.updateError)
        # connected before the capture starts: the first readings are often the
        # only Success of a box whose value doesn't change (later ones are
        # SameNoChange), and vMix and UNO only send Success unless "Send Same?"
        self.connectViewer()
        self.ocrModelChanged(fetch_data("scoresight.json", "ocr_model", 1))

        # in the first-run card's place (frame_for_source_view_label's grid)
        self.ui.frame_for_source_view_label.layout().addWidget(self.image_viewer, 0, 0)
        self.updateSourceBar()
        self.updateSourceBanner()
        self.updateFourCornerUi()
        self.updateFirstRunCard()
        self.image_viewer.startCapture()

    def connectViewer(self):
        """Connect the main window to the current image viewer and its capture
        thread. Each viewer is connected only once (the first frame is signalled
        again after e.g. a video settings change), or every result would be
        handled twice."""
        if self.image_viewer is None or self.connected_viewer is self.image_viewer:
            return
        self.disconnectViewer()
        self.connected_viewer = self.image_viewer
        self.ui.pushButton_binary.clicked.connect(self.image_viewer.toggleBinary)
        self.image_viewer.four_corner_changed.connect(self.updateFourCornerUi)
        self.image_viewer.zoom_changed.connect(self.updateZoomReadout)
        if self.image_viewer.timerThread:
            self.image_viewer.timerThread.ocr_result_signal.connect(self.ocrResult)
            self.image_viewer.timerThread.update_error.connect(self.updateError)

    def cameraConnectedEnableUI(self):
        if self.image_viewer is None:
            self.updateError("Image viewer is None")
            return
        self.connectViewer()

        # enable groupBox_sb_info
        self.ui.groupBox_sb_info.setEnabled(True)
        self.ui.tableWidget_boxes.setEnabled(True)
        self.ui.frame_source_view.setEnabled(True)
        self.setViewToolsEnabled(True)

        # The boxes are not reloaded from scoresight.json here: they were loaded
        # at startup and the in-memory boxes may have newer, unsaved edits.
        self.sourceError = None
        self.updateSourceBanner()
        self.updateZoomReadout()
        self.refreshLiveStatus()

    def updateError(self, error):
        """The source failed: the source error banner says so (with Retry),
        and the view tools are disabled until it works again."""
        if not error:
            return
        logger.error(error)
        self.sourceError = error
        self.ui.frame_source_view.setEnabled(True)
        self.setViewToolsEnabled(False)
        self.updateSourceBanner()
        if hasattr(self, "statusBarWidgets"):
            self.refreshLiveStatus()

    # --- the viewer: source bar, view tools, picture adjustments, first run -------

    def setupViewer(self):
        """Connect the viewer column's controls: the source bar, the view tools,
        the Adjust picture row, the banners over the picture and the first-run
        card."""
        ui = self.ui
        # the item index when the source list was opened: picking the open
        # file, stream or screen again asks for another one
        self.sourceIndexAtPopup = None
        # what the source's dot and the first-run card's steps show
        self.sourceHealthLook = None
        self.firstRunLook = None
        self.lastOutputStatuses: list[DestinationStatus] = []
        combo = ui.comboBox_camera_source
        combo.activated.connect(self.sourceActivated)
        combo.view().installEventFilter(self)
        # the open source's name is elided to the combo box's width
        combo.installEventFilter(self)
        ui.toolButton_speed.clicked.connect(self.toggleSpeed)
        ui.toolButton_speed.hide()

        # view tools
        ui.toolButton_zoomReset.clicked.connect(self.resetZoom)
        ui.actionZoomIn.triggered.connect(self.zoomIn)
        ui.actionZoomOut.triggered.connect(self.zoomOut)
        show_osd = self.storedShowOsd()
        ui.toolButton_osd.setChecked(show_osd)
        ui.actionStatsOverlay.setChecked(show_osd)
        ui.toolButton_osd.toggled.connect(self.toggleOSD)
        ui.actionStatsOverlay.toggled.connect(
            lambda checked: ui.toolButton_osd.setChecked(checked)
        )
        # "400%": the readout doesn't change the row's width as it changes
        ui.label_zoom.setMinimumWidth(
            QFontMetrics(ui.label_zoom.font()).horizontalAdvance(
                source_bar.zoom_text(4.0)
            )
            + 4
        )

        # Adjust picture
        ui.pushButton_fourCorner.clicked.connect(self.fourCornerClicked)
        ui.pushButton_cancelFourCorner.clicked.connect(self.cancelFourCornerSelection)
        ui.frame_fourCornerBanner.hide()
        # the row's hint hides when the buttons need its room
        ui.widget_viewTools.installEventFilter(self)
        ui.label_adjustHint.setForegroundRole(QPalette.ColorRole.PlaceholderText)

        # the source error banner
        ui.frame_sourceError.hide()
        ui.pushButton_retrySource.clicked.connect(self.retrySource)
        ui.pushButton_chooseSource.clicked.connect(self.chooseAnotherSource)
        ui.pushButton_sourceTroubleshooting.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(source_bar.SOURCE_TROUBLESHOOTING_URL)
            )
        )
        ui.pushButton_openScreenSettings.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl(source_bar.MACOS_SCREEN_RECORDING_SETTINGS_URL)
            )
        )

        # Tools > Collect OCR training data, and its status bar chip
        ui.actionCollectTrainingData.setChecked(
            bool(fetch_data("scoresight.json", COLLECT_TRAINING_DATA_SETTING, False))
        )
        ui.actionCollectTrainingData.toggled.connect(self.toggleTrainingData)
        self.statusBarWidgets.training_data_clicked.connect(
            self.openOCRTrainingDataDialog
        )

        # the first-run card
        self.firstRunCameraMenu = QMenu(ui.pushButton_firstRunCamera)
        ui.pushButton_firstRunCamera.setMenu(self.firstRunCameraMenu)
        for button, index in (
            (ui.pushButton_firstRunFile, SOURCE_INDEX_FILE),
            (ui.pushButton_firstRunUrl, SOURCE_INDEX_URL),
            (ui.pushButton_firstRunScreen, SOURCE_INDEX_SCREEN_CAPTURE),
        ):
            button.clicked.connect(
                lambda checked=False, index=index: self.chooseSource(index)
            )
        for label in (ui.label_firstRunBoxesHint, ui.label_firstRunOutputsHint):
            label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
        self.sourceBarRow = None
        self.applyViewerStyles()
        # a narrow window: the view tools show their icons only
        self.sourceBarRow = source_bar.CompactToolRow(
            ui.widget_4,
            [ui.pushButton_binary, ui.toolButton_osd, ui.toolButton_zoomReset],
            [ui.label, ui.label_boxDisplayStyle],
        )

    def storedShowOsd(self) -> bool:
        """Whether the statistics overlay is on. Off for new settings (the
        status bar shows the same numbers); settings of a version without the
        choice keep it on, as it was then."""
        stored = fetch_data("scoresight.json", SHOW_OSD_SETTING)
        if isinstance(stored, bool):
            return stored
        show = any(
            fetch_data("scoresight.json", key) is not None
            for key in ("boxes", "source_selected")
        )
        self.globalSettingsChanged(SHOW_OSD_SETTING, show)
        return show

    def applyViewerTexts(self):
        """The viewer column's texts that are made at runtime."""
        self.updateSourceBar()
        self.updateRotateText()
        self.updateZoomReadout()
        self.updateFourCornerUi()
        self.updateSourceBanner()
        self.ui.label_firstRunQuickstart.setText(source_bar.quickstart_link())
        if self.sourceBarRow is not None:
            # the texts' widths changed
            self.sourceBarRow.refresh()
        self.updateFirstRunCameraMenu()
        self.firstRunLook = None
        self.updateFirstRunCard()

    def applyViewerStyles(self):
        """The colours of the viewer column's controls, from the palette (again
        when it changes, e.g. File > Appearance)."""
        if not hasattr(self, "sourceHealthLook"):
            return
        ui = self.ui
        palette = self.palette()
        # a checked toggle (Binary View, Stats, Crop, 4-corner, Stabilize) is
        # filled: on and off are told apart at a glance
        style = theme.tool_button_style(palette)
        for row in (ui.widget_4, ui.widget_viewTools):
            if row.styleSheet() != style:
                row.setStyleSheet(style)
        icon_color = theme.button_text_color(palette)
        for button, kind in (
            (ui.pushButton_refresh_sources, "reload"),
            (ui.toolButton_videoSettings, "settings"),
            (ui.pushButton_binary, "binary"),
            (ui.toolButton_osd, "stats"),
            (ui.toolButton_zoomReset, "fit"),
        ):
            button.setIcon(theme.tool_icon(kind, icon_color))
        red = theme.color("empty", palette).name()
        ui.frame_sourceError.setStyleSheet(
            "QFrame#frame_sourceError {"
            f" background-color: {theme.tint('empty', palette).name()};"
            f" border: 1px solid {red}; border-left: 4px solid {red}; }}"
        )
        highlight = palette.color(QPalette.ColorRole.Highlight)
        ui.frame_fourCornerBanner.setStyleSheet(
            "QFrame#frame_fourCornerBanner {"
            f" background-color: rgba({highlight.red()}, {highlight.green()},"
            f" {highlight.blue()}, 40);"
            f" border: 1px solid {highlight.name()};"
            f" border-left: 4px solid {highlight.name()}; }}"
        )
        ui.frame_firstRun.setStyleSheet(
            "QFrame#frame_firstRun {"
            f" background-color: {palette.color(QPalette.ColorRole.Base).name()};"
            f" border: 1px solid {palette.color(QPalette.ColorRole.Mid).name()};"
            " border-radius: 8px; }"
        )
        # drawn again in the new colours
        self.sourceHealthLook = None
        self.firstRunLook = None
        self.updateFirstRunCard()

    def setViewToolsEnabled(self, enabled: bool):
        """The view tools, the Adjust picture row and the crop values work only
        while the source delivers frames."""
        for widget in (
            self.ui.widget_viewOptions,
            self.ui.widget_viewTools,
            self.ui.widget_cropPanel,
        ):
            widget.setEnabled(enabled)

    def triggerBinaryView(self):
        """View > Binary View (Ctrl+B), through the button."""
        self.ui.pushButton_binary.click()
        # the button does nothing while it's disabled: the action shows its state
        self.ui.actionBinaryView.setChecked(self.ui.pushButton_binary.isChecked())

    # the source bar

    def fitSourceList(self):
        """The source combo box is kept narrow (long camera names don't widen
        the window); its list shows the whole names."""
        view = self.ui.comboBox_camera_source.view()
        view.setMinimumWidth(
            view.sizeHintForColumn(0) + view.verticalScrollBar().sizeHint().width()
        )

    def updateSourceBar(self):
        """The source combo box shows the open file, stream or screen ("Video
        file: game.mp4", the full path in its tooltip). Video settings are for
        cameras only, the playback speed for video files only."""
        ui = self.ui
        combo = ui.comboBox_camera_source
        viewer = self.image_viewer
        camera_info = viewer.getCameraInfo() if viewer is not None else None
        current = combo.currentIndex()
        open_text = source_bar.source_combo_text(camera_info, self.sourceWindowTitle)
        full_name = source_bar.source_full_name(camera_info, self.sourceWindowTitle)
        for index, text in enumerate(source_bar.chooser_texts()):
            if index >= combo.count():
                break
            is_open = bool(open_text) and index == current
            if is_open:
                text = self.elidedSourceText(open_text)
            if combo.itemText(index) != text:
                combo.setItemText(index, text)
            combo.setItemData(
                index, full_name if is_open else None, Qt.ItemDataRole.ToolTipRole
            )
        tooltip = QCoreApplication.translate(
            "MainWindow",
            "The video source: a camera, capture card or NDI source, a video file, "
            "a stream URL or a screen capture",
        )
        combo.setToolTip(f"{full_name}\n{tooltip}" if full_name else tooltip)

        camera = (
            camera_info is not None and camera_info.type == CameraInfo.CameraType.OPENCV
        )
        ui.toolButton_videoSettings.setEnabled(camera)
        ui.toolButton_videoSettings.setToolTip(
            QCoreApplication.translate(
                "MainWindow",
                "Video settings: the resolution, frame rate and format of the "
                "camera or capture card",
            )
            if camera
            else QCoreApplication.translate(
                "MainWindow",
                "Video settings: only for cameras and capture cards",
            )
        )
        ui.toolButton_speed.setVisible(
            camera_info is not None and camera_info.type == CameraInfo.CameraType.FILE
        )

    def elidedSourceText(self, text: str) -> str:
        """text shortened in the middle to fit the source combo box (its tooltip
        has it in full)."""
        combo = self.ui.comboBox_camera_source
        option = QStyleOptionComboBox()
        combo.initStyleOption(option)
        field = combo.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox,
            option,
            QStyle.SubControl.SC_ComboBoxEditField,
            combo,
        )
        if field.width() <= 0:
            return text
        return combo.fontMetrics().elidedText(
            text, Qt.TextElideMode.ElideMiddle, field.width() - 2
        )

    def sourceActivated(self, index: int):
        """An item of the source list was picked. Picking the open video file,
        stream or screen capture again asks for another one (Cancel keeps the
        open one); picking another item is handled by sourceChanged."""
        reopened = index == self.sourceIndexAtPopup
        self.sourceIndexAtPopup = None
        if not reopened or index not in CHOOSER_SOURCE_INDEXES:
            return
        chosen = self.askSourceValue(index)
        if chosen is None:
            return
        self.source_name, self.sourceWindowTitle = chosen
        self.sourceSelectionSucessful()

    def chooseSource(self, index: int):
        """Pick a source item (e.g. from the first-run card), as in the source
        combo box."""
        combo = self.ui.comboBox_camera_source
        if not combo.isEnabled() or not 0 <= index < combo.count():
            return
        if combo.currentIndex() == index:
            self.sourceChanged(index)
        else:
            combo.setCurrentIndex(index)

    def chooseAnotherSource(self):
        combo = self.ui.comboBox_camera_source
        combo.setFocus(Qt.FocusReason.OtherFocusReason)
        combo.showPopup()

    def retrySource(self):
        """Open the failed source again."""
        if self.ui.comboBox_camera_source.currentIndex() == SOURCE_INDEX_NONE:
            return
        logger.info("Opening the source again")
        self.sourceSelectionSucessful()

    def updateSourceBanner(self):
        """The red banner over the picture: why the source can't be read and
        what to do (Retry, Choose another source, Troubleshooting), or that
        macOS doesn't let ScoreSight record the screen."""
        ui = self.ui
        viewer = self.image_viewer
        camera_info = viewer.getCameraInfo() if viewer is not None else None
        permission_missing = bool(
            camera_info is not None
            and camera_info.type == CameraInfo.CameraType.SCREEN_CAPTURE
            and source_bar.screen_recording_allowed() is False
        )
        if self.sourceError:
            headline, hint = source_bar.source_error_text(
                camera_info, self.sourceWindowTitle
            )
        elif permission_missing:
            headline, hint = source_bar.screen_recording_permission_text()
        else:
            ui.frame_sourceError.hide()
            return
        text = f"<b>{html.escape(headline, quote=False)}</b>"
        if hint:
            text += f" {html.escape(hint, quote=False)}"
        ui.label_sourceError.setText(text)
        ui.label_sourceError.setAccessibleName(f"{headline} {hint}".strip())
        ui.pushButton_retrySource.setVisible(bool(self.sourceError))
        ui.pushButton_openScreenSettings.setVisible(permission_missing)
        ui.frame_sourceError.show()

    def updateSourceHealth(self, state: str):
        """The dot before the source: green while frames arrive, amber while the
        source opens, is slow, stalls or reconnects, red when it fails (its
        shape tells the same without colour)."""
        label = self.ui.label_sourceHealth
        shape, color_name = source_look(state)
        palette = self.palette()
        color = (
            theme.color(color_name, palette)
            if color_name
            else theme.muted_color(palette)
        )
        look = (state, color.name())
        if look != self.sourceHealthLook:
            self.sourceHealthLook = look
            label.setPixmap(
                theme.state_icon(shape, color, 10).pixmap(
                    QSize(10, 10), self.devicePixelRatioF()
                )
            )
            description = source_state_description(state)
            label.setToolTip(description)
            label.setAccessibleName(description)

    # the view tools

    def updateZoomReadout(self, *_):
        """The zoom readout ("100%"): the size of a picture pixel on screen."""
        viewer = self.image_viewer
        text = ""
        if viewer is not None and getattr(viewer, "firstFrameReceived", False):
            text = source_bar.zoom_text(viewer.zoomLevel())
        self.ui.label_zoom.setText(text)

    def zoomIn(self):
        if self.image_viewer is not None and self.ui.widget_viewOptions.isEnabled():
            self.image_viewer.zoomIn()

    def zoomOut(self):
        if self.image_viewer is not None and self.ui.widget_viewOptions.isEnabled():
            self.image_viewer.zoomOut()

    # Adjust picture

    def updateRotateText(self, rotation=None):
        if rotation is None:
            rotation = fetch_data("scoresight.json", "rotation", 0)
        self.ui.toolButton_rotate.setText(source_bar.rotate_text(rotation))

    def fourCornerClicked(self):
        """4-corner never removes a correction silently: with one in place it
        offers to redo the corners or (after a confirmation) to remove it.
        While picking, it cancels the picking."""
        viewer = self.image_viewer
        if viewer is not None:
            if viewer.fourCornerSelectionMode:
                viewer.cancelFourCornerSelection()
            elif viewer.hasFourCornerCorrection():
                choice = self.askFourCornerAction()
                if choice == "redo":
                    viewer.startFourCornerSelection()
                elif choice == "remove" and self.confirmRemoveFourCornerCorrection():
                    viewer.removeFourCornerCorrection()
            else:
                viewer.startFourCornerSelection()
        # a click toggled the button: it shows the state again
        self.updateFourCornerUi()

    def askFourCornerAction(self) -> str | None:
        """The 4-corner button's menu when a correction is in place: "redo",
        "remove" or None (Cancel)."""
        menu = QMenu(self)
        redo = menu.addAction(QCoreApplication.translate("MainWindow", "Redo corners…"))
        remove = menu.addAction(
            QCoreApplication.translate("MainWindow", "Remove correction…")
        )
        menu.addSeparator()
        menu.addAction(QCoreApplication.translate("MainWindow", "Cancel"))
        button = self.ui.pushButton_fourCorner
        chosen = menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
        menu.deleteLater()
        if chosen is redo:
            return "redo"
        if chosen is remove:
            return "remove"
        return None

    def confirmRemoveFourCornerCorrection(self) -> bool:
        answer = QMessageBox.question(
            self,
            QCoreApplication.translate("MainWindow", "Remove the 4-corner correction?"),
            QCoreApplication.translate(
                "MainWindow",
                "The picture will no longer be corrected. The boxes were placed on "
                "the corrected picture, so they may have to be moved.",
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return answer == QMessageBox.StandardButton.Yes

    def cancelFourCornerSelection(self):
        if self.image_viewer is not None:
            self.image_viewer.cancelFourCornerSelection()
        self.updateFourCornerUi()

    def updateFourCornerUi(self, *_):
        """The 4-corner button is checked while a correction is in place (or
        corners are picked); while picking, the banner counts the corners."""
        ui = self.ui
        viewer = self.image_viewer
        picking = bool(viewer is not None and viewer.fourCornerSelectionMode)
        if viewer is not None:
            corrected = viewer.hasFourCornerCorrection()
        else:
            corrected = bool(fetch_data("scoresight.json", "four_corners"))
        button = ui.pushButton_fourCorner
        button.setChecked(picking or corrected)
        if picking:
            tooltip = QCoreApplication.translate(
                "MainWindow",
                "Picking the corners: click the 4 corners of the scoreboard. Click "
                "here or press Esc to cancel.",
            )
        elif corrected:
            tooltip = QCoreApplication.translate(
                "MainWindow",
                "The perspective is corrected. Click to redo the corners or to "
                "remove the correction.",
            )
        else:
            tooltip = QCoreApplication.translate(
                "MainWindow",
                "Correct the perspective: click the 4 corners of the scoreboard",
            )
        button.setToolTip(tooltip)
        ui.frame_fourCornerBanner.setVisible(picking)
        if picking:
            ui.label_fourCornerBanner.setText(
                source_bar.four_corner_banner_text(
                    viewer.fourCornersPicked(), corrected
                )
            )

    # Tools > Collect OCR training data

    def toggleTrainingData(self, collecting: bool):
        logger.info(
            "OCR training data collection %s", "started" if collecting else "stopped"
        )
        self.globalSettingsChanged(COLLECT_TRAINING_DATA_SETTING, bool(collecting))
        self.refreshLiveStatus()

    # the first-run card

    def updateFirstRunCameraMenu(self):
        """The first-run card's Camera menu: the cameras, capture cards and NDI
        sources found."""
        menu = self.firstRunCameraMenu
        menu.clear()
        combo = self.ui.comboBox_camera_source
        for index in range(FIRST_CAMERA_SOURCE_INDEX, combo.count()):
            action = menu.addAction(combo.itemText(index))
            action.triggered.connect(
                lambda checked=False, index=index: self.chooseSource(index)
            )
        if menu.isEmpty():
            none = menu.addAction(
                QCoreApplication.translate("MainWindow", "No camera found")
            )
            none.setEnabled(False)
        menu.addSeparator()
        menu.addAction(self.ui.actionReloadSources)

    def firstRunSteps(self) -> tuple[bool, bool, bool]:
        """Which of the first-run card's steps are done: a source is open, a
        box is on the picture, an output is on (the HTTP server always is)."""
        source_open = self.image_viewer is not None
        box_placed = any(
            not (box.settings or {}).get("templatefield")
            for box in self.detectionTargetsStorage.get_data()
        )
        output_on = any(
            status.enabled and status.switchable for status in self.lastOutputStatuses
        )
        return source_open, box_placed, output_on

    def updateFirstRunCard(self, outputs: list[DestinationStatus] | None = None):
        """The card shown while no source is open: three steps, each with a
        check mark once done."""
        ui = self.ui
        if outputs is not None:
            self.lastOutputStatuses = list(outputs)
        visible = self.image_viewer is None
        ui.frame_firstRun.setVisible(visible)
        if not visible:
            return
        steps = self.firstRunSteps()
        if steps != self.firstRunLook:
            self.firstRunLook = steps
            palette = self.palette()
            for number, (label, done) in enumerate(
                zip(
                    (
                        ui.label_firstRunStep1,
                        ui.label_firstRunStep2,
                        ui.label_firstRunStep3,
                    ),
                    steps,
                ),
                start=1,
            ):
                label.setPixmap(theme.step_pixmap(number, done, palette))
                label.setAccessibleName(
                    (
                        QCoreApplication.translate("MainWindow", "Step {number}: done")
                        if done
                        else QCoreApplication.translate("MainWindow", "Step {number}")
                    ).format(number=number)
                )
        # the sources can be picked once they were looked for
        enabled = ui.comboBox_camera_source.isEnabled()
        for button in (
            ui.pushButton_firstRunCamera,
            ui.pushButton_firstRunFile,
            ui.pushButton_firstRunUrl,
            ui.pushButton_firstRunScreen,
        ):
            button.setEnabled(enabled)

    def ocrResult(self, results: list[TextDetectionTargetWithResult]):
        # fill in the template fields from the boxes' last good readings; a
        # template is Success when its text changed, SameNoChange otherwise
        apply_template_fields(results)

        # The boxes list: each box's last good reading (a SameNoChange is its
        # last good reading), and the state of its latest one (a rejected or
        # empty reading is shown, but doesn't replace the value)
        now = time.monotonic()
        for targetWithResult in results:
            item = self.boxValueItem(targetWithResult.name)
            if item is not None:
                record_reading(
                    item, targetWithResult.result_state, targetWithResult.result, now
                )

        if not self.updateOCRResults:
            # the outputs are paused (the readings above keep updating)
            return

        update_http_server(results)

        if self.ui.checkBox_enableOutAPI.isChecked():
            update_out_api(results)

        # update vmix and uno. After a pause they also get the boxes' unchanged
        # values (which may have changed while the outputs were paused), once
        # per box: until the box's first good reading since
        resend = frozenset(self.resendAfterPause)
        if resend:
            self.resendAfterPause -= {
                result.name
                for result in results
                if result.result_state
                in (
                    TextDetectionTargetWithResult.ResultState.Success,
                    TextDetectionTargetWithResult.ResultState.SameNoChange,
                )
            }
        if self.vmixUiHandler.vmixUpdater is not None:
            self.vmixUiHandler.vmixUpdater.update_vmix(results, resend_unchanged=resend)
        if self.unoUiHandler.unoUpdater is not None:
            self.unoUiHandler.unoUpdater.update_uno(results, resend_unchanged=resend)

        # OBS text sources don't depend on the output folder (#30)
        self.updateObsTextSources(results)

        # files: remember the readings, write them at the "Save / s" rate
        self.fileOutput.record(results)
        self.scheduleFileOutputFlush()

    def updateObsTextSources(self, results: list[TextDetectionTargetWithResult]):
        """Send each box's good reading to its OBS text source when it differs
        from what was last sent there."""
        if self.obs_websocket_client is None:
            return
        for targetWithResult in results:
            if not file_output.is_good_reading(targetWithResult):
                continue
            source_name = (targetWithResult.settings or {}).get("obs_source_name")
            if not source_name:
                # custom boxes have no OBS source unless one is set
                continue
            if self.obs_last_sent.get(source_name) == targetWithResult.result:
                continue
            update_text_source(
                self.obs_websocket_client, source_name, targetWithResult.result
            )
            self.obs_last_sent[source_name] = targetWithResult.result

    def scheduleFileOutputFlush(self):
        """Flush the file outputs now, or when the "Save / s" throttle opens, so
        the latest values always reach the files (#6)."""
        if self.out_folder is None:
            return
        interval = 1.0 / max(1, self.ui.horizontalSlider_aggsPerSecond.value())
        delay = self.fileOutput.seconds_until_flush(interval)
        if delay <= 0:
            self.flushFileOutputs()
        elif not self.fileOutputTimer.isActive():
            self.fileOutputTimer.start(math.ceil(delay * 1000))

    def flushFileOutputs(self):
        self.fileOutputTimer.stop()
        if self.out_folder is None:
            return
        if not path.isdir(path.abspath(self.out_folder)):
            logger.warning("Output folder does not exist: %s", self.out_folder)
            # the Text files destination says so until a folder is chosen
            self.outputFolderLost = self.out_folder
            self.out_folder = None
            self.ui.lineEdit_folder.setText("")
            remove_data("scoresight.json", "output_folder")
            return
        self.fileOutput.flush(
            self.out_folder,
            self.ui.comboBox_appendMethod.currentIndex(),
            self.ui.checkBox_saveCsv.isChecked(),
            self.ui.checkBox_saveXML.isChecked(),
        )

    def addBox(self):
        # add a new box to the tableWidget_boxes
        # find the number of custom boxes
        custom_boxes = []
        for i in range(self.ui.tableWidget_boxes.rowCount()):
            item = self.ui.tableWidget_boxes.item(i, 0)
            if item.text() not in [o["name"] for o in default_boxes]:
                custom_boxes.append(item.text())

        i = len(custom_boxes)
        new_box_name = f"Custom {i + 1}"
        custom_boxes_names = fetch_data("scoresight.json", "custom_boxes_names", [])
        # find if the name already exists
        while new_box_name in custom_boxes or new_box_name in custom_boxes_names:
            i += 1
            new_box_name = f"Custom {i + 1}"

        store_custom_box_name(new_box_name)
        item = self.appendBoxRow(new_box_name)
        item.setIcon(QIcon(resource_path("icons", "circle-x.svg")))
        item.setData(Qt.ItemDataRole.UserRole, "unchecked")

    def removeCustomBox(self):
        item = self.ui.tableWidget_boxes.currentItem()
        if not item:
            logger.info("No item selected")
            return
        if item.column() != 0:
            item = self.ui.tableWidget_boxes.item(item.row(), 0)
        # only allow removing custom boxes (before anything is removed: a default
        # box keeps its placement and settings)
        if item.text() in [o["name"] for o in default_boxes]:
            logger.info("Cannot remove default box")
            return
        self.removeBox()
        remove_custom_box_name_in_storage(item.text())
        # remove the selected item from the tableWidget_boxes
        self.ui.tableWidget_boxes.removeRow(item.row())

    def editBoxName(self, item):
        # a double-click on a reading renames its box
        item = self.nameItemOfRow(item)
        if item is None:
            return
        if item.text() in [o["name"] for o in default_boxes]:
            # dont allow editing default boxes
            return
        new_name, ok = QInputDialog.getText(
            self, "Edit Box Name", "New Name:", text=item.text()
        )
        old_name = item.text()
        if ok and new_name != "" and new_name != old_name:
            # check if name doesn't exist already
            for i in range(self.ui.tableWidget_boxes.rowCount()):
                if new_name == self.ui.tableWidget_boxes.item(i, 0).text():
                    logger.info("Name '%s' already exists", new_name)
                    return
            # rename the item in the tableWidget_boxes
            rename_custom_box_name_in_storage(old_name, new_name)
            item.setText(new_name)
            # rename the item in the detectionTargetsStorage (a box that isn't
            # made yet isn't there). The row was renamed in place above, and
            # detectionTargetsChanged keeps its icon and role.
            if not self.detectionTargetsStorage.rename_item(old_name, new_name):
                logger.info("Error renaming item in application storage")

    def makeBox(self):
        item = self.ui.tableWidget_boxes.currentItem()
        if not item:
            return
        # create a new box on self.image_viewer with the name of the selected item from the tableWidget_boxes
        # change the list icon to green checkmark
        item.setIcon(QIcon(resource_path("icons/circle-check.svg")))
        item.setData(Qt.ItemDataRole.UserRole, "checked")
        self.listItemClicked(item)

        # get the size of the box from the name
        info = default_info_for_box_name(item.text())

        self.detectionTargetsStorage.add_item(
            TextDetectionTarget(
                info["x"],
                info["y"],
                info["width"],
                info["height"],
                item.text(),
                normalize_settings_dict({}, info),
            )
        )

    def removeBox(self):
        item = self.ui.tableWidget_boxes.currentItem()
        if not item:
            return
        item = self.nameItemOfRow(item)
        # change the list icon to red x
        item.setIcon(QIcon(resource_path("icons", "circle-x.svg")))
        item.setData(Qt.ItemDataRole.UserRole, "unchecked")
        # it isn't read any more: don't show its last reading as current
        clear_reading(self.ui.tableWidget_boxes.item(item.row(), 1))
        self.listItemClicked(item)
        self.detectionTargetsStorage.remove_item(item.text())

    def makeTemplateField(self, toggled: bool):
        item = self.ui.tableWidget_boxes.currentItem()
        if not item:
            return

        if not toggled:
            self.removeBox()
            return

        # create a new box on self.image_viewer with the name of the selected item from the tableWidget_boxes
        # change the list icon to green checkmark
        item.setIcon(QIcon(resource_path("icons", "template-field.svg")))
        item.setData(Qt.ItemDataRole.UserRole, "templatefield")

        self.detectionTargetsStorage.add_item(
            TextDetectionTarget(
                0,
                0,
                0,
                0,
                item.text(),
                normalize_settings_dict({"templatefield": True}, None),
            )
        )

        self.listItemClicked(item)

    def createOBSScene(self):
        # get the scene name from the lineEdit_sceneName
        scene_name = self.ui.lineEdit_sceneName.text()
        # clear or create a new scene
        create_obs_scene_from_export(self.obs_websocket_client, scene_name)
        # the new text sources show the scene's placeholder texts (and updates
        # sent before they existed failed): send every current value again
        self.obs_last_sent.clear()

    # on destroy, close the OBS connection
    def closeEvent(self, event):
        logger.info("Closing")
        self.closing = True
        self.statusTimer.stop()
        self.saveSplitterState()
        self.closeImageViewer()

        if self.log_dialog:
            self.log_dialog.close()
            self.log_dialog = None
        # dialogs without a parent would keep the app running
        for dialog in (self.video_settings_dialog, self.obs_connect_modal):
            if dialog is not None:
                dialog.close()

        # write pending file outputs and store the boxes to scoresight.json
        self.flushFileOutputs()
        self.saveBoxes()
        # ignore OBS connection attempts that are still running
        self.obs_connect_attempt += 1
        if self.obs_websocket_client:
            self.closeObsClient(self.obs_websocket_client)
            self.obs_websocket_client = None

        super().closeEvent(event)
