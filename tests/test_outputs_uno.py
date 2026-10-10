import logging
import threading
import time
from types import SimpleNamespace

import pytest

import storage
from output_worker import HTTP_TIMEOUT
from storage import fetch_data, store_data
from uno_output import UNOAPI

SETTINGS = "scoresight.json"
URL = "https://app.overlays.uno/apiv2/controlapps/abc/api"


class FakeResponse:
    def __init__(self, status_code=200, headers=None):
        self.status_code = status_code
        self.text = ""
        self.headers = headers or {}


class FakeSession:
    def __init__(self, status_code=200, delay=0.0):
        self.status_code = status_code
        self.delay = delay
        self.calls = []
        self.lock = threading.Lock()

    def put(self, url, json=None, timeout=None):
        with self.lock:
            self.calls.append({"url": url, "json": json, "timeout": timeout})
        if self.delay:
            time.sleep(self.delay)
        return FakeResponse(self.status_code)


@pytest.fixture
def make_uno():
    created = []

    def _make(endpoint=URL, mapping=None, session=None):
        api = UNOAPI(endpoint, mapping or {})
        api._session = session or FakeSession()
        created.append(api)
        return api

    yield _make
    for api in created:
        api.close()


def flush(api):
    assert api._worker.wait_idle(10)


def test_sends_put_with_timeout(make_uno, make_result):
    api = make_uno(mapping={"Home Score": "SetGoalsHome", "Time": "SetMatchTime"})
    api.start()
    api.update_uno(
        [
            make_result("Home Score", "3", "Success"),
            make_result("Time", "12:00", "SameNoChange"),
            make_result("Away Score", "1", "Success"),  # not mapped
        ]
    )
    flush(api)
    assert api._session.calls == [
        {
            "url": URL,
            "json": {"command": "SetGoalsHome", "value": "3"},
            "timeout": HTTP_TIMEOUT,
        }
    ]


def test_unchanged_values_are_sent_once_on_request(make_uno, make_result):
    # after the outputs were paused (see MainWindow.ocrResult)
    api = make_uno(mapping={"Time": "SetMatchTime"})
    api.start()
    results = [make_result("Time", "12:00", "SameNoChange")]
    api.update_uno(results, include_unchanged=True)
    api.update_uno(results)
    flush(api)
    assert [call["json"] for call in api._session.calls] == [
        {"command": "SetMatchTime", "value": "12:00"}
    ]


def test_essentials_payload(make_uno, make_result):
    store_data(SETTINGS, "uno_essentials", True)
    store_data(SETTINGS, "uno_essentials_id", "overlay-1")
    api = make_uno(mapping={"Time": "clock"})
    api.start()
    api.update_uno([make_result("Time", "1:00", "Success")])
    flush(api)
    assert api._session.calls[0]["json"] == {
        "command": "SetOverlayContentField",
        "value": "1:00",
        "fieldId": "clock",
        "id": "overlay-1",
    }


def test_update_never_blocks_and_keeps_latest_per_command(make_uno, make_result):
    session = FakeSession(delay=0.25)
    api = make_uno(mapping={"Time": "SetMatchTime", "Home Score": "SetGoalsHome"})
    api._session = session
    api.start()

    start = time.monotonic()
    api.update_uno([make_result("Home Score", "3", "Success")])
    for second in range(59, -1, -1):
        api.update_uno([make_result("Time", f"0:{second:02}", "Success")])
    assert time.monotonic() - start < 1.0  # blocking would take 15 s+

    flush(api)
    sent = [(c["json"]["command"], c["json"]["value"]) for c in session.calls]
    assert ("SetGoalsHome", "3") in sent  # an older change is never dropped
    assert sent[-1] == ("SetMatchTime", "0:00")
    assert len(sent) <= 10  # of 61 submitted (typically 3)


@pytest.mark.parametrize("status", [200, 201, 204])
def test_any_2xx_is_success(make_uno, make_result, caplog, status):
    api = make_uno(mapping={"Time": "SetMatchTime"}, session=FakeSession(status))
    api.start()
    with caplog.at_level(logging.ERROR):
        api.update_uno([make_result("Time", "1:00", "Success")])
        flush(api)
    assert caplog.records == []


def test_error_status_is_logged(make_uno, make_result, caplog):
    api = make_uno(mapping={"Time": "SetMatchTime"}, session=FakeSession(429))
    api.start()
    with caplog.at_level(logging.ERROR):
        api.update_uno([make_result("Time", "1:00", "Success")])
        flush(api)
    assert "returned HTTP 429" in caplog.text


def test_set_endpoint_keeps_mapping_and_running_state(make_uno, make_result):
    api = make_uno(mapping={"Time": "SetMatchTime"})
    api.start()
    api.set_endpoint("https://example.test/api")
    assert api.running
    assert api.field_mapping == {"Time": "SetMatchTime"}
    api.update_uno([make_result("Time", "1:00", "Success")])
    flush(api)
    assert api._session.calls[0]["url"] == "https://example.test/api"


def test_close_unsubscribes_from_settings(make_uno):
    api = make_uno()
    api.close()
    subscribers = storage.data_subscribers.get(SETTINGS, {})
    for name in ("uno_send_same", "uno_essentials", "uno_essentials_id"):
        assert name not in subscribers


# --- the UNO tab -------------------------------------------------------------


@pytest.fixture
def uno_ui(qapp):
    from PySide6.QtWidgets import (
        QCheckBox,
        QLineEdit,
        QTableView,
        QToolButton,
        QWidget,
    )

    ui = SimpleNamespace(
        lineEdit_unoUrl=QLineEdit(),
        toolButton_toggleUno=QToolButton(),
        tableView_unoMapping=QTableView(),
        checkBox_uno_send_same=QCheckBox(),
        checkBox_uno_essentials=QCheckBox(),
        widget_uno_essentials_details=QWidget(),
        lineEdit_uno_essentials_id=QLineEdit(),
    )
    ui.toolButton_toggleUno.setCheckable(True)
    return ui


@pytest.fixture
def handler(uno_ui):
    from uno_ui_handler import UNOUIHandler

    store_data(SETTINGS, "uno_url", URL)
    handler = UNOUIHandler(uno_ui)
    handler.unoUpdater._session = FakeSession()
    yield handler
    handler.unoUpdater.close()


@pytest.mark.qt
def test_url_edit_keeps_running_state_and_mapping(handler, uno_ui, make_target):
    updater = handler.unoUpdater
    handler.updateUNOTable([make_target("Home Score"), make_target("Time")])
    uno_ui.toolButton_toggleUno.setChecked(True)
    assert updater.running

    uno_ui.lineEdit_unoUrl.setText("https://example.test/new ")
    uno_ui.lineEdit_unoUrl.editingFinished.emit()

    assert handler.unoUpdater is updater
    assert updater.running  # used to be reset while the button showed "stop"
    assert uno_ui.toolButton_toggleUno.isChecked()
    assert updater.endpoint == "https://example.test/new"
    assert updater.field_mapping == {
        "Home Score": "SetGoalsHome",
        "Time": "SetMatchTime",
    }
    assert fetch_data(SETTINGS, "uno_url") == "https://example.test/new"


@pytest.mark.qt
def test_typing_alone_does_not_reconfigure(handler, uno_ui):
    uno_ui.lineEdit_unoUrl.setText("https://exa")
    assert handler.unoUpdater.endpoint == URL
    assert fetch_data(SETTINGS, "uno_url") == URL


@pytest.mark.qt
def test_editing_a_mapping_cell_stores_and_applies_it(handler, uno_ui, make_target):
    handler.updateUNOTable([make_target("Time")])
    assert fetch_data(SETTINGS, "uno_mapping") is None
    uno_ui.tableView_unoMapping.model().item(0, 1).setText("SetClock")
    assert fetch_data(SETTINGS, "uno_mapping") == {"Time": "SetClock"}
    assert handler.unoUpdater.field_mapping == {"Time": "SetClock"}


@pytest.mark.qt
def test_restore_ui_state(handler, uno_ui):
    uno_ui.toolButton_toggleUno.setChecked(True)
    uno_ui.lineEdit_unoUrl.setText("https://app.overlays.uno/apiv2/controlapps/.../api")
    uno_ui.toolButton_toggleUno.setText("x")

    handler.restoreUiState()
    assert uno_ui.lineEdit_unoUrl.text() == URL
    # a text and an icon, no emoji (#M4)
    assert uno_ui.toolButton_toggleUno.text() == "Stop sending"
    assert not uno_ui.toolButton_toggleUno.icon().isNull()
    assert handler.unoUpdater.running
    uno_ui.toolButton_toggleUno.setChecked(False)
    assert uno_ui.toolButton_toggleUno.text() == "Start sending"
