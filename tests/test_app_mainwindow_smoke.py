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

from PySide6.QtCore import QObject, QTranslator, Signal  # noqa: E402
from PySide6.QtWidgets import QWidget  # noqa: E402

from camera_info import CameraInfo  # noqa: E402
from storage import fetch_data, store_data  # noqa: E402


class FakeViewer(QWidget):
    """Stands in for source_view.ImageViewer (which starts a capture thread)."""

    first_frame_received_signal = Signal()
    error_signal = Signal(str)

    def __init__(self, camera_info, fourCornersApplied, storage, itemSelected):
        super().__init__()
        self.camera_info = camera_info
        self.timerThread = None
        self.four_corner_calls = []

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

    calls = {"http": [], "camera_threads": [], "obs": []}
    cameras = []

    def fake_get_camera_info():
        calls["camera_threads"].append(threading.current_thread())
        return list(cameras)

    monkeypatch.setattr(
        mainwindow, "start_http_server", lambda **k: calls["http"].append(k)
    )
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


@pytest.fixture
def main_window(make_window):
    return make_window()


def test_main_window_constructs_shows_and_closes(make_window, patched, qapp):
    from defaults import default_boxes

    threads_before = set(threading.enumerate())
    main_window = make_window()

    assert main_window.windowTitle().startswith("ScoreSight")
    assert main_window.ui.tableWidget_boxes.rowCount() >= len(default_boxes)
    assert main_window.ui.comboBox_camera_source.count() > 0

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
    assert client.disconnected


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


# --- boxes ------------------------------------------------------------------------------


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


# --- menus, appearance (#50), dialogs ---------------------------------------------------------
