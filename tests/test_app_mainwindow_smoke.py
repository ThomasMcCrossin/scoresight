"""Construct the real MainWindow headless (QT_QPA_PLATFORM=offscreen).

The HTTP server, camera enumeration (DirectShow/AVFoundation/V4L + NDI
discovery) and the update check are patched out so the test needs no network,
devices or ports.
"""

import threading

import pytest

pytestmark = pytest.mark.qt
pytest.importorskip("tesserocr")  # MainWindow imports the OCR pipeline


@pytest.fixture
def main_window(qapp, monkeypatch, memory_storage):
    from PySide6.QtCore import QTranslator

    import mainwindow

    monkeypatch.setattr(mainwindow, "start_http_server", lambda *a, **k: None)
    monkeypatch.setattr(mainwindow, "get_camera_info", lambda *a, **k: [])
    monkeypatch.setattr(mainwindow, "check_for_updates", lambda *a, **k: False)

    window = mainwindow.MainWindow(QTranslator(), qapp)
    yield window
    window.close()
    window.deleteLater()
    qapp.processEvents()


def test_main_window_constructs_shows_and_closes(main_window, qapp):
    from defaults import default_boxes
    from storage import fetch_data

    threads_before = set(threading.enumerate())

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
