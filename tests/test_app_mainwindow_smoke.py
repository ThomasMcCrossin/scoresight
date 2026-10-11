"""Construct the real MainWindow headless (QT_QPA_PLATFORM=offscreen).

The HTTP server, camera enumeration (DirectShow/AVFoundation/V4L + NDI
discovery) and the update check are patched out so the tests need no network,
devices or ports. Sources are opened with a fake viewer (no capture thread).
"""

import csv
import threading

import pytest

pytestmark = pytest.mark.qt
pytest.importorskip("tesserocr")  # MainWindow imports the OCR pipeline

from PySide6 import QtCore  # noqa: E402
from PySide6.QtCore import (  # noqa: E402
    QCoreApplication,
    QEvent,
    QObject,
    QTranslator,
    Signal,
)
from PySide6.QtGui import QKeySequence  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from camera_info import CameraInfo  # noqa: E402
from storage import fetch_data, store_data  # noqa: E402
from update_check import UpdateCheckResult  # noqa: E402
from version import __version__  # noqa: E402


class FakeViewer(QWidget):
    """Stands in for source_view.ImageViewer (which starts a capture thread)."""

    first_frame_received_signal = Signal()
    error_signal = Signal(str)

    def __init__(
        self, camera_info, fourCornersApplied, storage, itemSelected, start=True
    ):
        super().__init__()
        self.camera_info = camera_info
        self.timerThread = None
        self.four_corner_calls = []

    def startCapture(self):
        pass

    def toggleFourCorner(self, state):
        self.four_corner_calls.append(state)

    def toggleBinary(self):
        pass

    def selectBox(self, name):
        pass

    def getCameraInfo(self):
        return self.camera_info


class FakeTimerThread(QObject):
    ocr_result_signal = Signal(list)
    update_error = Signal(str)


class FakeObsClient:
    def __init__(self):
        self.disconnected = False

    def disconnect(self):
        self.disconnected = True


@pytest.fixture
def patched(monkeypatch):
    """Patch the main window's external dependencies; returns the call logs."""
    import mainwindow

    calls = {"http": [], "camera_threads": [], "obs": [], "http_port_busy": False}
    cameras = []

    def fake_get_camera_info():
        calls["camera_threads"].append(threading.current_thread())
        return list(cameras)

    def fake_get_http_server_port():
        # the port of the last start, or None as if that port had been busy
        if not calls["http"] or calls["http_port_busy"]:
            return None
        return calls["http"][-1]["port"]

    monkeypatch.setattr(
        mainwindow, "start_http_server", lambda **k: calls["http"].append(k)
    )
    monkeypatch.setattr(mainwindow, "get_http_server_port", fake_get_http_server_port)
    monkeypatch.setattr(mainwindow, "get_camera_info", fake_get_camera_info)
    monkeypatch.setattr(mainwindow, "check_for_updates", lambda *a, **k: False)
    monkeypatch.setattr(mainwindow, "ImageViewer", FakeViewer)
    monkeypatch.setattr(
        mainwindow,
        "update_text_source",
        lambda client, source, text: calls["obs"].append((client, source, text)),
    )
    calls["cameras"] = cameras
    return calls


@pytest.fixture
def make_window(qapp, qtbot, patched, memory_storage):
    import mainwindow

    windows = []

    def _make(**kwargs):
        window = mainwindow.MainWindow(QTranslator(), qapp, **kwargs)
        windows.append(window)
        # source discovery runs on a worker thread
        qtbot.waitUntil(lambda: not window.sources_discovery_running)
        return window

    yield _make
    for window in windows:
        window.close()
        qapp.removeTranslator(window.translator)
        window.deleteLater()
    qapp.processEvents()
    # processEvents() outside an event loop doesn't delete them
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture(autouse=True)
def windows_do_not_outlive_their_test(qapp):
    """A closed MainWindow that outlived its test kept its storage connections
    and its box save timer, and wrote its (empty) boxes into a later test's
    settings."""
    yield
    import mainwindow

    alive = [
        widget
        for widget in QApplication.topLevelWidgets()
        if isinstance(widget, mainwindow.MainWindow)
    ]
    assert alive == []


@pytest.fixture
def main_window(make_window):
    return make_window()


def test_main_window_constructs_shows_and_closes(make_window, patched, qapp):
    from defaults import default_boxes

    threads_before = set(threading.enumerate())
    main_window = make_window()

    assert main_window.windowTitle() == f"ScoreSight - v{__version__}"
    assert main_window.ui.tableWidget_boxes.rowCount() >= len(default_boxes)
    assert main_window.ui.comboBox_camera_source.count() > 0
    assert patched["http"] == [{"port": 18099}]

    main_window.show()
    qapp.processEvents()
    assert main_window.isVisible()

    main_window.close()
    qapp.processEvents()
    assert not main_window.isVisible()
    # closing persists the boxes
    assert isinstance(fetch_data("scoresight.json", "boxes"), list)
    # nothing (e.g. a server or capture thread) was left running
    leftover = [t for t in set(threading.enumerate()) - threads_before if not t.daemon]
    assert leftover == []


def test_closing_the_window_closes_its_parentless_dialogs(make_window, qapp):
    # a visible dialog without a parent keeps Qt's event loop (and the app)
    # running after the main window closed
    window = make_window()
    window.show()
    window.openOBSConnectModal()
    assert window.obs_connect_modal.isVisible()
    window.close()
    qapp.processEvents()
    assert not window.obs_connect_modal.isVisible()


def test_title_shows_the_profile(make_window, monkeypatch):
    monkeypatch.setenv("SCORESIGHT_PROFILE", "court2")
    window = make_window()
    assert window.windowTitle() == f"ScoreSight - v{__version__} [court2]"


# --- background work (#33) -----------------------------------------------------------


def test_sources_are_discovered_off_the_gui_thread(make_window, patched):
    patched["cameras"].append(
        CameraInfo("USB Camera", "0", 0, CameraInfo.CameraType.OPENCV)
    )
    window = make_window()
    assert patched["camera_threads"]
    assert threading.main_thread() not in patched["camera_threads"]
    combo = window.ui.comboBox_camera_source
    assert combo.itemText(combo.count() - 1) == "USB Camera"
    assert window.ui.pushButton_refresh_sources.isEnabled()


def test_obs_auto_connect_runs_off_the_gui_thread(make_window, monkeypatch, qtbot):
    import mainwindow

    client = FakeObsClient()
    threads = []

    def fake_open(info):
        threads.append(threading.current_thread())
        assert info == {"ip": "localhost", "port": "4455", "password": "x"}
        return client

    monkeypatch.setattr(mainwindow, "open_obs_websocket", fake_open)
    store_data(
        "scoresight.json", "obs", {"ip": "localhost", "port": "4455", "password": "x"}
    )
    window = make_window()
    qtbot.waitUntil(lambda: window.obs_websocket_client is client)
    assert threads and threads[0] is not threading.main_thread()
    assert window.ui.pushButton_createOBSScene.isEnabled()
    window.close()
    # closed with obs_websocket.close_obs_websocket, off the GUI thread
    qtbot.waitUntil(lambda: client.disconnected)


# --- outputs ---------------------------------------------------------------------------


def test_obs_updates_without_an_output_folder(main_window, patched, make_result):
    # obs-updates-gated-by-output-folder: OBS was only updated after the
    # output-folder check and at the file-save rate.
    client = FakeObsClient()
    main_window.obs_websocket_client = client
    assert main_window.out_folder is None

    main_window.ocrResult([make_result("Home Score", "12")])
    main_window.ocrResult([make_result("Home Score", "12", "SameNoChange")])
    main_window.ocrResult([make_result("Home Score", "8B", "FailedFilter")])
    main_window.ocrResult([make_result("Home Score", "13")])
    # a custom box has no OBS source
    main_window.ocrResult([make_result("Custom 1", "99")])
    assert patched["obs"] == [
        (client, "Home score", "12"),
        (client, "Home score", "13"),
    ]


def test_create_obs_scene_sends_every_current_value_again(
    main_window, patched, make_result, monkeypatch
):
    # Creating the scene replaces the text sources with the scene collection's
    # placeholder texts ("24", "18", ...); unchanged values were never sent to
    # them, so OBS showed the placeholders until each box's value changed.
    import mainwindow

    scenes = []
    monkeypatch.setattr(
        mainwindow,
        "create_obs_scene_from_export",
        lambda client, name: scenes.append((client, name)),
    )
    client = FakeObsClient()
    main_window.obs_websocket_client = client
    main_window.ocrResult([make_result("Home Score", "3")])
    main_window.ui.lineEdit_sceneName.setText("ScoreSight Scene")
    main_window.createOBSScene()
    assert scenes == [(client, "ScoreSight Scene")]
    main_window.ocrResult([make_result("Home Score", "3", "SameNoChange")])
    assert patched["obs"] == [
        (client, "Home score", "3"),
        (client, "Home score", "3"),
    ]


def test_template_fields_report_changes_only(main_window, make_result):
    # template-uses-failed-results: every template was reported as a new
    # Success on every cycle (defeating "update on change"), and filled with
    # rejected readings.
    def cycle(home, away):
        template = make_result(
            "Score",
            "",
            "Empty",
            templatefield=True,
            templatefield_text="{{Home Score}} - {{Away Score}}",
        )
        results = [make_result("Home Score", *home), make_result("Away Score", *away)]
        main_window.ocrResult([*results, template])
        return template.result, template.result_state.name

    assert cycle(("12", "Success"), ("7", "Success")) == ("12 - 7", "Success")
    assert cycle(("12", "SameNoChange"), ("7", "SameNoChange")) == (
        "12 - 7",
        "SameNoChange",
    )
    assert cycle(("8B", "FailedFilter"), ("7", "SameNoChange")) == (
        "12 - 7",
        "SameNoChange",
    )
    assert cycle(("13", "Success"), ("7", "SameNoChange")) == ("13 - 7", "Success")


def test_stop_updates_pauses_outputs(main_window, patched, make_result):
    main_window.obs_websocket_client = FakeObsClient()
    main_window.ui.pushButton_stopUpdates.setChecked(True)
    main_window.ocrResult([make_result("Home Score", "12")])
    assert patched["obs"] == []


def test_file_outputs_flush_the_last_change_when_the_throttle_opens(
    main_window, make_result, tmp_path, qtbot
):
    # #6: a change that arrives inside the "Save / s" window is written as
    # soon as the window opens, even if no other result arrives.
    main_window.ui.horizontalSlider_aggsPerSecond.setValue(2)
    main_window.setOutputFolder(str(tmp_path))
    home = tmp_path / "Home Score.txt"

    main_window.ocrResult([make_result("Home Score", "1")])
    assert home.read_text(encoding="utf-8") == "1"
    main_window.ocrResult([make_result("Home Score", "2")])
    main_window.ocrResult([make_result("Home Score", "2", "SameNoChange")])
    assert home.read_text(encoding="utf-8") == "1"  # throttled
    qtbot.waitUntil(lambda: home.read_text(encoding="utf-8") == "2", timeout=3000)


def test_box_changes_do_not_truncate_the_csv_log(
    main_window, make_result, make_target, tmp_path
):
    # csv-truncated-on-any-box-change: any data_changed (a click on a box, a
    # settings tweak) emptied results.csv.
    main_window.ui.comboBox_appendMethod.setCurrentIndex(0)  # append to .csv
    main_window.ui.checkBox_saveCsv.setChecked(True)
    main_window.ui.horizontalSlider_aggsPerSecond.setValue(10)
    main_window.setOutputFolder(str(tmp_path))
    storage = main_window.detectionTargetsStorage
    storage.add_item(make_target("Home Score"))

    main_window.ocrResult([make_result("Home Score", "1")])
    main_window.flushFileOutputs()
    main_window.ocrResult([make_result("Home Score", "2")])
    main_window.flushFileOutputs()

    box = storage.find_item_by_name("Home Score")
    box.settings["smoothing"] = True
    storage.edit_item("Home Score", box)

    with open(tmp_path / "results.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["Timestamp", "Home Score"]
    assert [row[1] for row in rows[1:]] == ["1", "2"]


def test_api_output_encoding_defaults_to_json_full(main_window):
    # api-encoding-blank-on-fresh-install: the default "JSON" matched no item,
    # so "" was stored and POST/PUT output never sent anything.
    assert main_window.ui.comboBox_api_encode.currentIndex() == 0
    assert fetch_data("scoresight.json", "out_api_encoding") == "JSON (Full)"
    assert fetch_data("scoresight.json", "out_api_method") == "POST"


@pytest.mark.parametrize(
    ("stored", "index", "expected"),
    [("", 0, "JSON (Full)"), ("XML", 2, "XML"), ("JSON (Simple key-value)", 1, None)],
)
def test_api_output_encoding_is_restored_or_repaired(
    make_window, stored, index, expected
):
    store_data("scoresight.json", "out_api_encoding", stored)
    window = make_window()
    assert window.ui.comboBox_api_encode.currentIndex() == index
    assert fetch_data("scoresight.json", "out_api_encoding") == (expected or stored)
    window.ui.comboBox_api_encode.setCurrentIndex(3)
    assert fetch_data("scoresight.json", "out_api_encoding") == "CSV"


def test_language_change_keeps_settings_and_texts(main_window, qapp, caplog):
    main_window.ui.comboBox_api_encode.setCurrentIndex(2)
    main_window.ui.lineEdit_vmixPort.setText("8123")
    main_window.ui.lineEdit_vmixPort.editingFinished.emit()
    main_window.reset_playing_source()  # e.g. the sources were reloaded
    main_window.changeLanguage("de_DE")
    try:
        # retranslateUi stopped half-way at a label deleted by a source change
        assert "Error retranslating UI" not in caplog.text
        assert main_window.ui.label_12.isVisibleTo(main_window)
        assert fetch_data("scoresight.json", "language") == "de_DE"
        # retranslateUi used to store the translated item text / reset fields
        assert fetch_data("scoresight.json", "out_api_encoding") == "XML"
        assert main_window.ui.lineEdit_vmixPort.text() == "8123"
        assert main_window.windowTitle() == f"ScoreSight - v{__version__}"
    finally:
        qapp.removeTranslator(main_window.translator)


def test_language_change_keeps_the_runtime_texts(main_window, qapp, qtbot, make_result):
    # retranslateUi resets every text to the .ui's: the paused banner, the
    # slider readouts and the window title are set again
    ui = main_window.ui
    main_window.show()
    ui.horizontalSlider_conf_thresh.setValue(45)
    main_window.ocrResult([make_result("Home Score", "21")])
    ui.pushButton_stopUpdates.setChecked(True)
    main_window.changeLanguage("de_DE")
    try:
        assert ui.pushButton_stopUpdates.isChecked()
        assert ui.pushButton_stopUpdates.text() == "Resume outputs"
        assert ui.frame_pausedBanner.isVisibleTo(main_window)
        assert ui.label_pausedBanner.text() != ""
        assert main_window.windowTitle().startswith("⏸ ")
        assert ui.label_confThreshValue.text() == "45 %"
        assert ui.label_detectionCadenceValue.text() == "5 /s"
        shortcut = QKeySequence("Ctrl+Shift+P").toString(
            QKeySequence.SequenceFormat.NativeText
        )
        assert f"({shortcut})" in ui.pushButton_stopUpdates.toolTip()
        assert box_value(main_window, "Home Score") == "21"
        assert main_window.statusBarWidgets.label_http.text() != ""
        checked = [
            a.data() for a in main_window.language_actions.actions() if a.isChecked()
        ]
        assert checked == ["de_DE"]
        # the left column becomes as wide as its (German) content
        qtbot.waitUntil(
            lambda: (
                ui.scrollArea_left.minimumWidth() >= ui.frame.minimumSizeHint().width()
            )
        )
    finally:
        qapp.removeTranslator(main_window.translator)


def test_language_change_keeps_the_output_controls(main_window, qapp, monkeypatch):
    # retranslateUi reset the vMix/UNO start buttons to their .ui texts
    # ("Start"), the OBS scene name and the playback speed.
    vmix = main_window.vmixUiHandler
    uno = main_window.unoUiHandler
    monkeypatch.setattr(vmix.vmixUpdater, "start", lambda: None, raising=False)
    monkeypatch.setattr(uno.unoUpdater, "start", lambda: None, raising=False)
    vmix_text = main_window.ui.pushButton_startvmix.text()
    uno_text = main_window.ui.toolButton_toggleUno.text()
    main_window.ui.lineEdit_sceneName.setText("Court 2")
    main_window.ui.toolButton_speed.setText("x4")
    main_window.changeLanguage("de_DE")
    try:
        assert main_window.ui.pushButton_startvmix.text() == vmix_text
        assert main_window.ui.toolButton_toggleUno.text() == uno_text
        assert main_window.ui.lineEdit_sceneName.text() == "Court 2"
        assert main_window.ui.toolButton_speed.text() == "x4"
    finally:
        qapp.removeTranslator(main_window.translator)


def test_pause_outputs_button_text_with_a_translation(main_window, qapp):
    # stop-updates-button-blank-i18n: QTranslator.translate returns "" for a
    # missing translation, which blanked the button in every non-English UI.
    assert main_window.ui.pushButton_stopUpdates.text() == "Pause outputs"
    main_window.changeLanguage("de_DE")
    try:
        button = main_window.ui.pushButton_stopUpdates
        button.setChecked(True)
        paused_text = button.text()
        button.setChecked(False)
        assert paused_text not in ("", button.text())
        assert button.text() != ""
    finally:
        qapp.removeTranslator(main_window.translator)
    main_window.ui.pushButton_stopUpdates.setChecked(True)
    assert main_window.ui.pushButton_stopUpdates.text() == "Resume outputs"


def test_browser_tab_shows_the_http_port(make_window, patched):
    window = make_window(http_port=18100)
    assert patched["http"] == [{"port": 18100}]
    text = window.ui.label_8.text()
    assert "http://localhost:18100/json" in text
    assert "http://localhost:18100/csv" in text
    assert "?pivot" in text
    assert "18099" not in text
    assert "color:#" not in text


def test_browser_tab_says_when_the_http_port_is_busy(make_window, patched):
    patched["http_port_busy"] = True
    window = make_window(http_port=18100)
    text = window.ui.label_8.text()
    assert "not running" in text
    assert "18100" in text
    assert "--port" in text
    assert "http://localhost" not in text


# --- boxes ------------------------------------------------------------------------------


def box_rows(window):
    table = window.ui.tableWidget_boxes
    return [table.item(row, 0).text() for row in range(table.rowCount())]


def box_name_item(window, name):
    """A box's item in the boxes list's Field column."""
    table = window.ui.tableWidget_boxes
    [item] = [
        item
        for item in table.findItems(name, QtCore.Qt.MatchFlag.MatchExactly)
        if item.column() == 0
    ]
    return item


def box_value_item(window, name):
    """A box's item in the boxes list's Value column."""
    return window.ui.tableWidget_boxes.item(box_name_item(window, name).row(), 1)


def box_value(window, name):
    """The text in the boxes list's Value column for a box."""
    return box_value_item(window, name).text()


def select_box_row(window, name):
    item = box_name_item(window, name)
    window.ui.tableWidget_boxes.setCurrentItem(item)
    return item


def test_renaming_a_made_custom_box_keeps_its_row(main_window, monkeypatch):
    import mainwindow

    main_window.addBox()
    [name] = fetch_data("scoresight.json", "custom_boxes_names")
    item = select_box_row(main_window, name)
    main_window.makeBox()
    monkeypatch.setattr(
        mainwindow.QInputDialog,
        "getText",
        lambda *args, **kwargs: ("Shot Clock 2", True),
    )
    main_window.editBoxName(item)
    assert "Shot Clock 2" in box_rows(main_window)
    assert name not in box_rows(main_window)
    [renamed] = main_window.ui.tableWidget_boxes.findItems(
        "Shot Clock 2", QtCore.Qt.MatchFlag.MatchExactly
    )
    assert renamed.data(QtCore.Qt.ItemDataRole.UserRole) == "checked"
    storage = main_window.detectionTargetsStorage
    assert [box.name for box in storage.get_data()] == ["Shot Clock 2"]
    assert fetch_data("scoresight.json", "custom_boxes_names") == ["Shot Clock 2"]


def test_the_remove_button_does_not_delete_a_default_box(main_window):
    select_box_row(main_window, "Home Score")
    main_window.makeBox()
    storage = main_window.detectionTargetsStorage
    home = storage.find_item_by_name("Home Score")
    home.settings["conf_thresh"] = 0.4  # a tuned box
    main_window.removeCustomBox()
    assert storage.find_item_by_name("Home Score") is home
    assert "Home Score" in box_rows(main_window)
    main_window.saveBoxes()
    [stored] = fetch_data("scoresight.json", "boxes")
    assert (stored["name"], stored["settings"]["conf_thresh"]) == ("Home Score", 0.4)

    # a custom box is removed
    main_window.addBox()
    [name] = fetch_data("scoresight.json", "custom_boxes_names")
    select_box_row(main_window, name)
    main_window.makeBox()
    main_window.removeCustomBox()
    assert name not in box_rows(main_window)
    assert storage.find_item_by_name(name) is None
    assert fetch_data("scoresight.json", "custom_boxes_names") == []


def test_box_edits_are_saved_without_a_viewer_click(main_window, make_target, qtbot):
    # box-edits-lost-on-source-switch (part 1): only a click in the viewer or
    # closing the window saved the boxes.
    main_window.detectionTargetsStorage.add_item(make_target("Custom 1", type=2))
    qtbot.waitUntil(
        lambda: fetch_data("scoresight.json", "boxes") is not None, timeout=3000
    )
    [box] = fetch_data("scoresight.json", "boxes")
    assert box["name"] == "Custom 1"
    assert box["settings"]["type"] == 2


def test_new_source_keeps_unsaved_box_edits(make_window, make_target, qtbot):
    # box-edits-lost-on-source-switch (part 2): every new viewer reloaded the
    # boxes from disk, dropping in-memory edits.
    store_data(
        "scoresight.json",
        "boxes",
        [{"name": "Home Score", "rect": {"x": 1, "y": 2, "width": 3, "height": 4}}],
    )
    window = make_window()
    storage = window.detectionTargetsStorage
    box = storage.find_item_by_name("Home Score")
    assert box is not None  # loaded at startup
    box.settings["format_regex"] = "^edited$"
    storage.edit_item("Home Score", box)

    window.image_viewer = FakeViewer(None, None, None, None)
    window.cameraConnectedEnableUI()
    assert storage.find_item_by_name("Home Score").settings["format_regex"] == (
        "^edited$"
    )

    def saved_regex():
        [saved] = fetch_data("scoresight.json", "boxes")
        return saved.get("settings", {}).get("format_regex")

    qtbot.waitUntil(lambda: saved_regex() == "^edited$", timeout=3000)


def test_viewer_is_connected_once(main_window, monkeypatch):
    # The first-frame signal (and so cameraConnectedEnableUI) fires again after
    # e.g. a video settings change; each call used to add another connection,
    # so every OCR result was handled (and sent to every output) again.
    import mainwindow

    http_updates = []
    monkeypatch.setattr(mainwindow, "update_http_server", http_updates.append)
    viewer = FakeViewer(None, None, None, None)
    viewer.timerThread = FakeTimerThread()
    main_window.image_viewer = viewer
    main_window.cameraConnectedEnableUI()
    main_window.cameraConnectedEnableUI()
    main_window.ui.pushButton_fourCorner.setChecked(True)
    viewer.timerThread.ocr_result_signal.emit([])
    assert viewer.four_corner_calls == [True]
    assert http_updates == [[]]

    # a new viewer replaces the old one's connections
    new_viewer = FakeViewer(None, None, None, None)
    main_window.image_viewer = new_viewer
    main_window.cameraConnectedEnableUI()
    main_window.ui.pushButton_fourCorner.setChecked(False)
    assert viewer.four_corner_calls == [True]
    assert new_viewer.four_corner_calls == [False]


def test_readings_from_the_start_of_the_capture_reach_the_window(
    make_window, monkeypatch, make_result
):
    # The window connected to the capture thread only when the first preview
    # frame arrived, so the readings made before it were lost. For a box whose
    # value doesn't change those were its only Success (the later ones are
    # SameNoChange): its value never showed in the boxes list, and vMix and UNO
    # (which send only Success unless "Send Same?" is on) never got it.
    import mainwindow

    http_updates = []
    monkeypatch.setattr(mainwindow, "update_http_server", http_updates.append)

    class StartingViewer(FakeViewer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.timerThread = FakeTimerThread()
            self.timerThread.textDetector = None

        def startCapture(self):
            self.timerThread.ocr_result_signal.emit([make_result("Home Score", "21")])

    monkeypatch.setattr(mainwindow, "ImageViewer", StartingViewer)
    store_data("scoresight.json", "source_selected", "rtsp://10.0.1.200:554/11")
    window = make_window()
    assert [[result.result for result in update] for update in http_updates] == [["21"]]
    assert box_value(window, "Home Score") == "21"


def test_the_boxes_list_shows_the_last_good_reading(main_window, make_result):
    main_window.ocrResult([make_result("Home Score", "21", state="SameNoChange")])
    assert box_value(main_window, "Home Score") == "21"
    main_window.ocrResult([make_result("Home Score", "2l", state="FailedFilter")])
    main_window.ocrResult([make_result("Home Score", "", state="Empty")])
    assert box_value(main_window, "Home Score") == "21"


def test_the_boxes_list_shows_every_reading_state(main_window, make_result):
    # The Value column was greyed out (NoItemFlags) and showed only new
    # (Success) readings: now it shows the state of every reading, and a
    # rejected or empty one keeps the last good value
    from readings_view import REJECTED_TEXT_ROLE, STATE_ROLE, reading_at

    item = box_value_item(main_window, "Home Score")
    assert item.flags() & QtCore.Qt.ItemFlag.ItemIsEnabled
    assert not item.flags() & QtCore.Qt.ItemFlag.ItemIsSelectable
    table = main_window.ui.tableWidget_boxes
    for state, text in (
        ("Success", "21"),
        ("SameNoChange", "21"),
        ("FailedFilter", "2l"),
        ("Empty", ""),
    ):
        main_window.ocrResult([make_result("Home Score", text, state=state)])
        assert item.data(STATE_ROLE) == state
        reading = reading_at(table.indexFromItem(item))
        assert (reading.value, reading.age is not None) == ("21", True)
    assert item.data(REJECTED_TEXT_ROLE) == "2l"
    assert table.itemDelegateForColumn(1) is main_window.readingDelegate
    main_window.show()
    table.grab()  # paints every row


def test_a_click_on_a_reading_selects_its_box(main_window, make_result):
    ui = main_window.ui
    select_box_row(main_window, "Home Score")
    main_window.makeBox()
    main_window.ocrResult([make_result("Home Score", "21")])
    value = box_value_item(main_window, "Home Score")
    ui.tableWidget_boxes.setCurrentItem(value)
    main_window.listItemClicked(value)
    # the name stays the current item: the settings, rename and remove use it
    assert ui.tableWidget_boxes.currentItem().text() == "Home Score"
    assert ui.label_selectedInfo.text() == "Home Score"
    # (the list is disabled until a source opens)
    assert ui.pushButton_removeBox.isEnabledTo(ui.groupBox_sb_info)

    # taken off the picture: its last reading isn't shown as current
    main_window.removeBox()
    assert box_value(main_window, "Home Score") == ""


def test_the_boxes_list_matches_names_not_values(main_window, make_result):
    # a reading that equals another box's name doesn't confuse the list
    main_window.ocrResult([make_result("Home Score", "Period", state="Success")])
    main_window.ocrResult([make_result("Period", "2")])
    assert box_value(main_window, "Home Score") == "Period"
    assert box_value(main_window, "Period") == "2"


def test_pausing_the_outputs_shows_everywhere(main_window, patched, make_result):
    ui = main_window.ui
    main_window.show()
    assert ui.pushButton_stopUpdates.text() == "Pause outputs"
    assert not ui.frame_pausedBanner.isVisibleTo(main_window)
    assert main_window.statusBarWidgets.label_paused.isHidden()

    main_window.ui.actionPauseOutputs.trigger()  # Ctrl+Shift+P
    assert ui.pushButton_stopUpdates.isChecked()
    assert ui.pushButton_stopUpdates.text() == "Resume outputs"
    assert ":checked" in ui.pushButton_stopUpdates.styleSheet()
    assert ui.frame_pausedBanner.isVisibleTo(main_window)
    assert "Outputs paused" in ui.label_pausedBanner.text()
    assert main_window.windowTitle() == f"⏸ ScoreSight - v{__version__}"
    chip = main_window.statusBarWidgets.label_paused
    assert not chip.isHidden() and chip.text().startswith("PAUSED 00:0")
    assert main_window.readingDelegate.paused
    # the readings keep updating, the outputs don't get them
    main_window.obs_websocket_client = FakeObsClient()
    main_window.ocrResult([make_result("Home Score", "12")])
    assert box_value(main_window, "Home Score") == "12"
    assert patched["obs"] == []

    ui.pushButton_resumeOutputs.click()  # the banner's Resume
    assert not ui.pushButton_stopUpdates.isChecked()
    assert not ui.frame_pausedBanner.isVisibleTo(main_window)
    assert main_window.windowTitle() == f"ScoreSight - v{__version__}"
    assert chip.isHidden()
    assert not main_window.readingDelegate.paused


def test_the_keyboard_shortcuts(main_window, qtbot):
    ui = main_window.ui
    shortcuts = {
        action.objectName(): action.shortcut().toString()
        for action in main_window.actions()
    }
    assert shortcuts == {
        "actionPauseOutputs": "Ctrl+Shift+P",
        "actionBinaryView": "Ctrl+B",
        "actionFitPicture": "Ctrl+0",
        "actionReloadSources": "F5",
    }
    from PySide6.QtTest import QTest

    with qtbot.waitActive(main_window):
        main_window.show()
        main_window.activateWindow()
    # through the window, as a real key press (shortcuts are matched there)
    QTest.keyClick(
        main_window.windowHandle(),
        QtCore.Qt.Key.Key_P,
        QtCore.Qt.KeyboardModifier.ControlModifier
        | QtCore.Qt.KeyboardModifier.ShiftModifier,
    )
    assert ui.pushButton_stopUpdates.isChecked()
    # the tooltip shows the shortcut as the platform writes it (⌘B on macOS)
    native = QKeySequence.SequenceFormat.NativeText
    assert QKeySequence("Ctrl+B").toString(native) in ui.pushButton_binary.toolTip()
    # the buttons do nothing while they are disabled (no source yet)
    assert not ui.widget_viewTools.isEnabled()
    ui.actionBinaryView.trigger()
    assert not ui.pushButton_binary.isChecked()


def test_resuming_sends_unchanged_values_to_vmix_and_uno(
    main_window, make_result, make_target
):
    # A value that changed while the outputs were paused is an unchanged
    # (SameNoChange) reading after resuming, which vMix and UNO don't send.
    # Each box's first good reading after resuming is sent anyway.
    calls = []
    vmix = main_window.vmixUiHandler.vmixUpdater
    uno = main_window.unoUiHandler.unoUpdater
    vmix.update_vmix = lambda results, resend_unchanged=(): calls.append(
        ("vmix", set(resend_unchanged))
    )
    uno.update_uno = lambda results, resend_unchanged=(): calls.append(
        ("uno", set(resend_unchanged))
    )
    storage = main_window.detectionTargetsStorage
    storage.add_item(make_target("Home Score"))
    storage.add_item(make_target("Time"))

    def cycle(home, time):
        calls.clear()
        main_window.ocrResult(
            [make_result("Home Score", *home), make_result("Time", *time)]
        )
        return calls[:]

    assert cycle(("12", "Success"), ("1:00", "Success")) == [
        ("vmix", set()),
        ("uno", set()),
    ]
    main_window.ui.pushButton_stopUpdates.setChecked(True)
    assert cycle(("13", "Success"), ("0:45", "Success")) == []  # paused
    main_window.ui.pushButton_stopUpdates.setChecked(False)
    # the clock's first reading after resuming is rejected: it stays pending
    both = {"Home Score", "Time"}
    assert cycle(("13", "SameNoChange"), ("0:4S", "FailedFilter")) == [
        ("vmix", both),
        ("uno", both),
    ]
    assert cycle(("13", "SameNoChange"), ("0:45", "SameNoChange")) == [
        ("vmix", {"Time"}),
        ("uno", {"Time"}),
    ]
    assert cycle(("13", "SameNoChange"), ("0:45", "SameNoChange")) == [
        ("vmix", set()),
        ("uno", set()),
    ]


class FakeCaptureThread(FakeTimerThread):
    def __init__(self):
        super().__init__()
        import time

        self.frame_size = (1280, 720)
        self.fps = 29.97
        self.ups = 4.8
        self.update_frame_interval = 200
        self.last_frame_timestamp = time.monotonic()
        self.textDetector = None


def test_the_status_bar(make_window, monkeypatch, patched):
    import mainwindow

    class RunningViewer(FakeViewer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.timerThread = FakeCaptureThread()
            self.firstFrameReceived = True

    monkeypatch.setattr(mainwindow, "ImageViewer", RunningViewer)
    monkeypatch.setattr(mainwindow, "primary_lan_address", lambda: "192.168.1.20")
    store_data("scoresight.json", "source_selected", "rtsp://user:pw@10.0.1.200:554/11")
    window = make_window(http_port=18100)
    window.refreshLiveStatus()
    bar = window.statusBarWidgets
    assert "rtsp://10.0.1.200:554/11 · 1280×720 · 30.0 fps" in bar.label_source.text()
    assert "pw" not in bar.label_source.text()
    assert bar.label_ocr.text() == "Reading 4.8/s of 5"
    assert bar.label_http.text() == "http://192.168.1.20:18100"
    assert "http://localhost:18100" in bar.label_http.toolTip()

    window.updateError("Unable to play the stream")
    window.refreshLiveStatus()
    assert "can't be read" in bar.label_source.text()
    window.reset_playing_source()
    window.refreshLiveStatus()
    assert "No source" in bar.label_source.text()


def test_the_status_bar_when_the_http_port_is_busy(make_window, patched):
    patched["http_port_busy"] = True
    window = make_window(http_port=18100)
    bar = window.statusBarWidgets
    assert "not running (port 18100 busy)" in bar.label_http.text()
    assert bar.button_copy.isHidden()


@pytest.fixture
def reference_font(qapp):
    """Segoe UI 9 pt (the Windows UI font) where it's installed; the offscreen
    platform doesn't find the system fonts by itself."""
    import os
    import sys

    from PySide6.QtGui import QFont, QFontDatabase

    previous = qapp.font()
    path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "segoeui.ttf")
    loaded = sys.platform == "win32" and QFontDatabase.addApplicationFont(path) >= 0
    if loaded:
        qapp.setFont(QFont("Segoe UI", 9))
    yield loaded
    qapp.setFont(previous)


# the reference text for scaling the size limit with another font
SIZE_REFERENCE_TEXT = "Detections / s Update on change Binary View 4-corner Correction"


def test_the_window_fits_a_small_screen(make_window, qapp, qtbot, reference_font):
    # The window needed 1016x750 (1158 wide in German): more than a 1366x768
    # laptop shows. The left column now scrolls, and a splitter divides the
    # space. The limit is for Segoe UI 9 pt; a wider font (Linux, the
    # offscreen fallback font) widens it in proportion.
    from PySide6.QtGui import QFontMetricsF

    window = make_window()
    width_ratio = 1.0
    if not reference_font:
        # Segoe UI 9 pt draws the reference text 342 px wide
        width_ratio = max(
            1.0, QFontMetricsF(qapp.font()).horizontalAdvance(SIZE_REFERENCE_TEXT) / 342
        )
    ui = window.ui
    window.show()
    for language in ("en_US", "de_DE"):
        window.changeLanguage(language)
        # the left column doesn't scroll sideways: it becomes as wide as its
        # content
        qtbot.waitUntil(
            lambda: (
                ui.scrollArea_left.minimumWidth() >= ui.frame.minimumSizeHint().width()
            )
        )
        qapp.processEvents()
        hint = window.minimumSizeHint()
        assert hint.width() <= 1024 * width_ratio, (language, hint)
        assert hint.height() <= 640, (language, hint)
    qapp.removeTranslator(window.translator)


def test_the_splitter_sizes_are_kept(make_window, qtbot):
    def settled(window):
        # wide enough for any font, laid out
        window.resize(max(2000, window.minimumSizeHint().width() + 400), 800)
        window.show()
        ui = window.ui
        qtbot.waitUntil(
            lambda: (
                ui.scrollArea_left.minimumWidth() >= ui.frame.minimumSizeHint().width()
            )
        )
        return window.ui.splitter_main

    window = make_window()
    splitter = settled(window)
    left = window.ui.widget_leftPane.minimumSizeHint().width() + 60
    splitter.setSizes([left, splitter.width() - left])
    assert splitter.sizes()[0] == left
    window.close()
    assert fetch_data("scoresight.json", "main_splitter_state")

    restored = settled(make_window())
    qtbot.waitUntil(lambda: restored.sizes()[0] == left)


def test_slider_readouts(main_window, make_target):
    ui = main_window.ui
    storage = main_window.detectionTargetsStorage
    storage.add_item(make_target("Home Score", conf_thresh=0, skew=-3, vscale=8))
    main_window.itemSelected("Home Score")
    assert ui.label_confThreshValue.text() == "Off"
    assert ui.label_skewValue.text() == "\u22123"
    assert ui.label_vscaleValue.text() == "80 %"
    assert ui.label_dilateValue.text() == "1"
    assert ui.label_cleanupValue.text() == "Off"
    ui.horizontalSlider_conf_thresh.setValue(45)
    assert ui.label_confThreshValue.text() == "45 %"
    assert ui.horizontalSlider_conf_thresh.accessibleDescription() == "45 %"
    ui.horizontalSlider_detectionCadence.setValue(12)
    assert ui.label_detectionCadenceValue.text() == "12 /s"
    ui.horizontalSlider_aggsPerSecond.setValue(3)
    assert ui.label_aggsPerSecondValue.text() == "3 /s"


def test_controls_have_tooltips(main_window):
    # the controls the design critique found without one
    for name in (
        "checkBox_smoothing",
        "horizontalSlider_vscale",
        "horizontalSlider_skew",
        "horizontalSlider_dilate",
        "horizontalSlider_cleanup",
        "checkBox_compositeBox",
        "comboBox_binarizationMethod",
        "checkBox_autocrop",
        "checkBox_skip_similar_image",
        "pushButton_stopUpdates",
        "horizontalSlider_detectionCadence",
        "comboBox_ocrModel",
        "pushButton_saveOCRTrainingData",
        "toolButton_videoSettings",
        "toolButton_addBox",
        "toolButton_removeBox",
    ):
        assert getattr(main_window.ui, name).toolTip(), name


def test_output_buttons_have_text_and_no_emoji(main_window):
    for button in (
        main_window.ui.pushButton_startvmix,
        main_window.ui.toolButton_toggleUno,
    ):
        text = button.text()
        assert text in ("Start vMix", "Start sending")
        assert not button.icon().isNull()
        assert not any(ord(c) > 0x2000 for c in text)


def test_the_obs_dialog(main_window, qapp):
    from PySide6.QtWidgets import QLineEdit

    store_data(
        "scoresight.json", "obs", {"ip": "localhost", "port": "4455", "password": "x"}
    )
    main_window.show()
    main_window.openOBSConnectModal()
    dialog = main_window.obs_connect_modal
    ui = main_window.obs_modal_ui
    # a child of the main window: it stays in front of it
    assert dialog.parent() is main_window
    assert ui.lineEdit_password.echoMode() == QLineEdit.EchoMode.Password
    ui.checkBox_showPassword.setChecked(True)
    assert ui.lineEdit_password.echoMode() == QLineEdit.EchoMode.Normal
    assert not main_window.ui.pushButton_createOBSScene.isEnabled()

    # connected meanwhile, then Cancel: the scene controls work again
    main_window.obs_websocket_client = FakeObsClient()
    ui.pushButton_cancel.click()
    assert not dialog.isVisible()
    assert main_window.ui.pushButton_createOBSScene.isEnabled()
    main_window.obs_websocket_client = None

    # opening it again while it's open doesn't make a second one
    main_window.openOBSConnectModal()
    second = main_window.obs_connect_modal
    main_window.openOBSConnectModal()
    assert main_window.obs_connect_modal is second


def test_cancel_while_connecting_to_obs(main_window, monkeypatch, qtbot):
    # Cancel didn't stop the connection attempt: when it succeeded later, it
    # replaced the current connection and stored the cancelled settings
    import mainwindow

    release = threading.Event()
    finished = threading.Event()
    client = FakeObsClient()

    def slow_open(info):
        release.wait(5)
        finished.set()
        return client

    monkeypatch.setattr(mainwindow, "open_obs_websocket", slow_open)
    main_window.show()
    main_window.openOBSConnectModal()
    ui = main_window.obs_modal_ui
    ui.lineEdit_ip.setText("other-pc")
    ui.pushButton_connect.click()
    assert not ui.pushButton_connect.isEnabled()  # connecting
    ui.pushButton_cancel.click()
    release.set()
    assert finished.wait(5)
    # the (ignored) client is closed off the GUI thread
    qtbot.waitUntil(lambda: client.disconnected)
    assert main_window.obs_websocket_client is None
    assert fetch_data("scoresight.json", "obs") is None


def test_the_file_menu_is_translatable(main_window, qapp):
    # The File menu was made in code without tr(): never translated
    from PySide6.QtCore import QTranslator

    class Marking(QTranslator):
        def translate(self, context, source, disambiguation=None, n=-1):
            return f"«{source}»" if context == "MainWindow" else ""

    translator = Marking()
    qapp.installTranslator(translator)
    try:
        main_window.ui.retranslateUi(main_window)
        main_window.applyRuntimeTexts()
        assert main_window.ui.menuFile.title() == "«File»"
        assert "«Check for Updates»" in menu_titles(main_window)
        assert "«Appearance»" in menu_titles(main_window)
        appearance = [a.text() for a in main_window.appearance_actions.actions()]
        assert appearance == ["«System»", "«Light»", "«Dark»"]
    finally:
        qapp.removeTranslator(translator)
        main_window.ui.retranslateUi(main_window)
    # the languages in their own language, not translated
    languages = [a.text() for a in main_window.language_actions.actions()]
    assert "Deutsch" in languages and "日本語" in languages and "Français" in languages
    assert len(languages) == 13


def test_replaced_viewers_are_deleted(make_window, qapp):
    # A replaced viewer was removed from the layout and closed, but stayed a
    # child widget of the main window for the rest of the session.
    from PySide6.QtCore import QCoreApplication, QEvent
    from shiboken6 import isValid

    store_data("scoresight.json", "source_selected", "rtsp://10.0.1.200:554/11")
    window = make_window()
    first = window.image_viewer
    assert first is not None
    window.sourceSelectionSucessful()  # open the source again
    second = window.image_viewer
    assert second is not first
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert not isValid(first)
    assert isValid(second)
    window.reset_playing_source()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert not isValid(second)
    assert window.image_viewer is None


# --- sources (#10) -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "stored",
    [
        {"type": "URL", "value": "rtsp://10.0.1.200:554/11"},
        "rtsp://10.0.1.200:554/11",  # 0.1.x stored the bare URL
    ],
)
def test_url_source_is_restored(make_window, stored):
    store_data("scoresight.json", "source_selected", stored)
    window = make_window()
    assert window.ui.comboBox_camera_source.currentIndex() == 2
    camera_info = window.image_viewer.camera_info
    assert (camera_info.type, camera_info.id) == ("URL", "rtsp://10.0.1.200:554/11")
    assert fetch_data("scoresight.json", "source_selected") == {
        "type": "URL",
        "value": "rtsp://10.0.1.200:554/11",
    }


def test_sources_found_after_closing_do_not_reopen_the_source(make_window):
    store_data("scoresight.json", "source_selected", "rtsp://10.0.1.200:554/11")
    window = make_window()
    assert window.image_viewer is not None
    window.close()
    assert window.image_viewer is None
    window.update_sources.emit([])  # a late source discovery result
    assert window.image_viewer is None


def test_file_source_is_restored(make_window, tmp_path):
    video = tmp_path / "game.mp4"
    video.write_bytes(b"")
    store_data("scoresight.json", "source_selected", str(video))
    window = make_window()
    assert window.ui.comboBox_camera_source.currentIndex() == 1
    assert window.image_viewer.camera_info.type == "File"
    assert window.image_viewer.camera_info.id == str(video)


def test_missing_file_source_is_not_restored(make_window, tmp_path):
    store_data(
        "scoresight.json",
        "source_selected",
        {"type": "File", "value": str(tmp_path / "gone.mp4")},
    )
    window = make_window()
    assert window.ui.comboBox_camera_source.currentIndex() == 0
    assert window.image_viewer is None


def test_camera_source_is_stored_and_restored(make_window, patched):
    patched["cameras"].extend(
        [
            CameraInfo("Capture Card", "0", 0, CameraInfo.CameraType.OPENCV),
            CameraInfo(
                "NDI Scoreboard", "NDI Scoreboard", 0, CameraInfo.CameraType.NDI
            ),
        ]
    )
    window = make_window()
    combo = window.ui.comboBox_camera_source
    combo.setCurrentIndex(combo.count() - 1)  # the user picks the NDI source
    assert fetch_data("scoresight.json", "source_selected") == {
        "type": "NDI",
        "value": "NDI Scoreboard",
        "description": "NDI Scoreboard",
    }
    window.close()

    restored = make_window()
    assert restored.ui.comboBox_camera_source.currentText() == "NDI Scoreboard"
    assert restored.image_viewer.camera_info.type == "NDI"


@pytest.fixture
def no_dialogs(monkeypatch):
    """Record (instead of showing) the modal dialogs the main window opens."""
    from PySide6.QtWidgets import QDialog

    shown = []
    monkeypatch.setattr(
        QDialog, "exec", lambda self: shown.append(self.windowTitle()) or 0
    )
    return shown


@pytest.mark.parametrize("cameras", [1, 2])
def test_refreshing_the_sources_keeps_the_selected_camera(
    make_window, patched, qtbot, no_dialogs, cameras
):
    # Removing the current camera's item during a refresh ran sourceChanged: it
    # opened the Screen Capture dialog, and with two cameras switched to (and
    # stored) the other one.
    patched["cameras"].extend(
        CameraInfo(f"Cam {n}", f"uuid-{n}", n, CameraInfo.CameraType.OPENCV)
        for n in range(cameras)
    )
    window = make_window()
    combo = window.ui.comboBox_camera_source
    combo.setCurrentIndex(combo.findText("Cam 0"))
    stored = fetch_data("scoresight.json", "source_selected")
    assert stored["value"] == "uuid-0"

    window.getSources()  # the refresh button
    qtbot.waitUntil(lambda: not window.sources_discovery_running)
    assert no_dialogs == []
    assert combo.currentText() == "Cam 0"
    assert window.image_viewer.camera_info.uuid == "uuid-0"
    assert fetch_data("scoresight.json", "source_selected") == stored

    # the camera was unplugged: no source, and still no dialog
    patched["cameras"].pop(0)
    window.getSources()
    qtbot.waitUntil(lambda: not window.sources_discovery_running)
    assert no_dialogs == []
    assert combo.currentIndex() == 0
    assert window.image_viewer is None
    assert fetch_data("scoresight.json", "source_selected") == stored


def test_cancelling_the_file_dialog_in_a_translated_ui(
    make_window, monkeypatch, no_dialogs
):
    # The cancel selected "Select a source" by its English text, which a
    # translated combo box doesn't have: it stayed on "Open a Video File" with
    # the boxes table and view tools disabled.
    import mainwindow

    store_data("scoresight.json", "source_selected", "rtsp://10.0.1.200:554/11")
    window = make_window()
    assert window.image_viewer is not None
    combo = window.ui.comboBox_camera_source
    combo.setItemText(0, "Wählen Sie eine Quelle")
    monkeypatch.setattr(
        mainwindow.QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("", "")
    )
    combo.setCurrentIndex(1)  # "Open a Video File", then Cancel
    assert combo.currentIndex() == 0
    assert window.image_viewer is None  # as in English


# --- menus, appearance (#50), dialogs ---------------------------------------------------------


def menu_titles(window):
    [file_menu] = [a.menu() for a in window.menuBar().actions() if a.menu()]
    return [action.text() for action in file_menu.actions()]


def test_menubar_stays_visible_after_the_window_is_deactivated(main_window, qapp):
    # The docs team reported that the File menu disappears when the window loses
    # focus. QWidget never forwards WindowDeactivate to changeEvent (only
    # ActivationChange), so the old hide-on-deactivate branch never ran; it was
    # removed. This pins the behavior.
    main_window.show()
    qapp.processEvents()
    for event_type in (QEvent.Type.WindowDeactivate, QEvent.Type.ActivationChange):
        QApplication.sendEvent(main_window, QEvent(event_type))
    qapp.processEvents()
    assert main_window.menuBar().isVisible()
    assert "Appearance" in menu_titles(main_window)
    assert "Theme" not in menu_titles(main_window)


class FakeStyleHints:
    def __init__(self):
        self.calls = []

    def setColorScheme(self, scheme):
        self.calls.append(scheme)

    def unsetColorScheme(self):
        self.calls.append("unset")


@pytest.fixture
def style_hints(monkeypatch):
    import mainwindow

    hints = FakeStyleHints()

    class FakeGuiApplication:
        @staticmethod
        def styleHints():
            return hints

    monkeypatch.setattr(mainwindow, "QGuiApplication", FakeGuiApplication)
    return hints


def test_apply_color_scheme(style_hints):
    from PySide6.QtCore import Qt

    from mainwindow import apply_color_scheme

    assert apply_color_scheme("Dark") == "Dark"
    assert apply_color_scheme("Light") == "Light"
    assert apply_color_scheme("System") == "System"
    assert apply_color_scheme(None) == "System"
    assert apply_color_scheme("Solarized") == "System"
    assert style_hints.calls == [
        Qt.ColorScheme.Dark,
        Qt.ColorScheme.Light,
        "unset",
        "unset",
        "unset",
    ]


def test_appearance_menu_applies_and_persists(main_window, style_hints):
    from PySide6.QtCore import Qt

    actions = {a.data(): a for a in main_window.appearance_actions.actions()}
    assert list(actions) == ["System", "Light", "Dark"]
    assert actions["System"].isChecked()

    actions["Dark"].trigger()
    assert fetch_data("scoresight.json", "color_scheme") == "Dark"
    assert style_hints.calls == [Qt.ColorScheme.Dark]
    assert actions["Dark"].isChecked() and not actions["System"].isChecked()


def test_appearance_menu_shows_the_stored_scheme(make_window):
    store_data("scoresight.json", "color_scheme", "Light")
    window = make_window()
    checked = [a.data() for a in window.appearance_actions.actions() if a.isChecked()]
    assert checked == ["Light"]


def test_about_dialog_shows_the_version_and_no_dead_links(main_window):
    dialog = main_window.createAboutDialog()
    assert __version__ in dialog.ui.label_version.text()
    text = dialog.ui.label.text()
    assert "scoresight.live" not in text
    assert "https://github.com/royshil/scoresight/issues" in text
    assert "https://royshil.github.io/scoresight/" in text
    assert "color:#" not in text
    dialog.deleteLater()


def test_startup_update_check_shows_an_available_update(
    make_window, monkeypatch, qtbot
):
    import mainwindow

    threads = []

    def fake_check():
        threads.append(threading.current_thread())
        return UpdateCheckResult("0.2.0", "0.3.0", update_available=True)

    monkeypatch.setattr(mainwindow, "check_for_updates", fake_check)
    window = make_window()
    qtbot.waitUntil(lambda: window.update_dialog is not None)
    assert threads[0] is not threading.main_thread()
    assert not window.update_dialog.ui.label_newVersion.isHidden()
    window.update_dialog.close()


def test_startup_update_check_respects_the_setting(make_window, monkeypatch):
    # pytest.fail() in the (background) check only killed that thread with a
    # warning, so this passed even when the setting was ignored. The check is
    # started (or not) synchronously by the constructor.
    import mainwindow

    calls = []
    monkeypatch.setattr(
        mainwindow,
        "check_for_updates",
        lambda: calls.append(1) or UpdateCheckResult(__version__, __version__),
    )
    started = []
    real_run_in_background = mainwindow.run_in_background

    def run_in_background(name, function, on_done):
        started.append(name)
        return real_run_in_background(name, function, on_done)

    monkeypatch.setattr(mainwindow, "run_in_background", run_in_background)
    store_data("scoresight.json", "disable_update_checks", True)
    window = make_window()
    assert "update check" not in started
    assert "source discovery" in started  # the background jobs are seen
    assert calls == []
    assert window.update_dialog is None


def test_manual_update_check_always_shows_the_result(make_window, monkeypatch, qtbot):
    import mainwindow

    monkeypatch.setattr(
        mainwindow, "check_for_updates", lambda: UpdateCheckResult("0.2.0", "0.2.0")
    )
    store_data("scoresight.json", "disable_update_checks", True)
    window = make_window()
    window.checkForUpdates(True)
    qtbot.waitUntil(lambda: window.update_dialog is not None)
    assert not window.update_dialog.ui.label_noNewVersion.isHidden()
    window.update_dialog.close()


def test_a_manual_check_during_the_startup_check_shows_its_result(
    make_window, monkeypatch, qtbot
):
    # File > Check for Updates while the startup check was still running did
    # nothing, and the startup check shows no dialog when there is no update.
    import mainwindow

    release = threading.Event()
    calls = []

    def slow_check():
        calls.append(threading.current_thread())
        release.wait(5)
        return UpdateCheckResult(__version__, __version__)

    monkeypatch.setattr(mainwindow, "check_for_updates", slow_check)
    window = make_window()
    assert window.update_check_running
    window.checkForUpdates(True)
    release.set()
    qtbot.waitUntil(lambda: window.update_dialog is not None)
    assert len(calls) == 1
    assert not window.update_dialog.ui.label_noNewVersion.isHidden()
    window.update_dialog.close()
    assert not window.update_check_manual_pending


def test_confidence_threshold_slider(main_window, make_target):
    ui = main_window.ui
    assert "Tesseract" in ui.horizontalSlider_conf_thresh.toolTip()
    assert "%" in ui.label_3.toolTip()
    handler = main_window.boxSettingsUiHandler
    handler.populateSettings("")  # no box selected: the default, off
    assert ui.horizontalSlider_conf_thresh.value() == 0

    storage = main_window.detectionTargetsStorage
    storage.add_item(make_target("Home Score", conf_thresh=0.29))
    main_window.itemSelected("Home Score")
    assert ui.horizontalSlider_conf_thresh.value() == 29
    ui.horizontalSlider_conf_thresh.setValue(45)
    assert storage.find_item_by_name("Home Score").settings["conf_thresh"] == 0.45
