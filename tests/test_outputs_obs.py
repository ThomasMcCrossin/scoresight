import json
import logging
import os
import threading
import time
from types import SimpleNamespace

import pytest
import websocket
from obsws_python.error import OBSSDKRequestError

import obs_websocket


class FakeWebSocket:
    def __init__(self):
        self.closed = False

    def shutdown(self):
        self.closed = True


def new_base(**kwargs):
    """Stands in for ReqClient.base_client: connection parameters + websocket."""
    return SimpleNamespace(ws=FakeWebSocket(), **kwargs)


class FakeClient:
    """Stands in for obsws_python.ReqClient."""

    def __init__(self, delay=0.0, gate=None):
        self.delay = delay
        self.gate = gate
        self.started = threading.Event()
        self.calls = []
        self.errors = []  # exceptions to raise on the next calls, in order
        self.base_client = new_base(host="obs-pc", port=4455, password="pw", timeout=3)
        self.disconnected = False

    def set_input_settings(self, name, settings, overlay):
        self.started.set()
        if self.gate is not None:
            assert self.gate.wait(5)
        if self.delay:
            time.sleep(self.delay)
        if self.base_client.ws.closed:
            # like websocket-client after the socket was closed
            raise websocket.WebSocketConnectionClosedException("closed")
        if self.errors:
            raise self.errors.pop(0)
        self.calls.append((name, settings["text"], overlay))

    def get_scene_list(self):
        self.calls.append(("get_scene_list",))
        return SimpleNamespace(scenes=[])

    def disconnect(self):
        self.disconnected = True
        # like ReqClient.disconnect(): later requests fail on the closed socket
        self.base_client.ws.shutdown()


@pytest.fixture(autouse=True)
def idle_worker():
    worker = obs_websocket._text_worker
    worker.error_log.reset()
    worker._retry_failures = 0
    yield
    worker.clear()
    assert worker.wait_idle(10)


def flush():
    assert obs_websocket._text_worker.wait_idle(10)


def test_update_text_source_sets_the_text_in_the_background():
    client = FakeClient()
    obs_websocket.update_text_source(client, "Home Score", "12")
    flush()
    assert client.calls == [("Home Score", "12", True)]


def test_update_never_blocks_and_keeps_latest_text_per_source():
    # the old code called OBS on the GUI thread with a 10 s timeout
    client = FakeClient(delay=0.25)
    start = time.monotonic()
    obs_websocket.update_text_source(client, "Home Score", "3")
    for second in range(59, -1, -1):
        obs_websocket.update_text_source(client, "Time", f"0:{second:02}")
    assert time.monotonic() - start < 1.0  # blocking would take 15 s+

    flush()
    assert ("Home Score", "3", True) in client.calls
    assert client.calls[-1] == ("Time", "0:00", True)
    assert len(client.calls) <= 10  # of 61 submitted (typically 3)


@pytest.mark.parametrize("source_name", ["", None])
def test_boxes_without_a_source_name_are_skipped(source_name):
    client = FakeClient()
    obs_websocket.update_text_source(client, source_name, "12")
    obs_websocket.update_text_source(None, "Home Score", "12")
    flush()
    assert client.calls == []


def test_failed_request_is_logged_and_others_still_update(caplog):
    client = FakeClient()
    client.errors = [OBSSDKRequestError("SetInputSettings", 600, "No source")]
    with caplog.at_level(logging.ERROR):
        obs_websocket.update_text_source(client, "Missing", "1")
        obs_websocket.update_text_source(client, "Time", "1:00")
        flush()
    assert client.calls == [("Time", "1:00", True)]
    assert "No source" in caplog.text


def test_lost_connection_is_reestablished(monkeypatch, caplog):
    client = FakeClient()
    old_ws = client.base_client.ws
    client.errors = [websocket.WebSocketConnectionClosedException("closed")]
    fresh_base = new_base(host="obs-pc", port=4455, password="pw", timeout=3)
    created = []

    def fake_req_client(**kwargs):
        created.append(kwargs)
        return SimpleNamespace(base_client=fresh_base)

    monkeypatch.setattr(obs_websocket.obs, "ReqClient", fake_req_client)
    with caplog.at_level(logging.INFO):
        obs_websocket.update_text_source(client, "Time", "1:00")
        flush()

    assert created == [{"host": "obs-pc", "port": 4455, "password": "pw", "timeout": 3}]
    assert old_ws.closed
    assert client.base_client is fresh_base
    assert client.calls == [("Time", "1:00", True)]
    assert "reconnected" in caplog.text


def test_a_close_frame_from_obs_is_a_lost_connection(monkeypatch):
    # OBS shutting down (or restarting its websocket server) sends a close frame:
    # the next request reads an empty message, which obsws-python fails to parse.
    # That update used to be dropped, and it wasn't sent again until it changed.
    client = FakeClient()
    client.errors = [json.JSONDecodeError("Expecting value", "", 0)]
    created = []

    def fake_req_client(**kwargs):
        created.append(kwargs)
        return SimpleNamespace(base_client=new_base(**kwargs))

    monkeypatch.setattr(obs_websocket.obs, "ReqClient", fake_req_client)
    obs_websocket.update_text_source(client, "Home Score", "12")
    flush()
    assert len(created) == 1
    assert client.calls == [("Home Score", "12", True)]


def test_unreachable_obs_is_retried_until_it_is_back(monkeypatch, caplog):
    client = FakeClient()
    client.errors = [ConnectionResetError("reset")]
    attempts = []

    def fake_req_client(**kwargs):
        attempts.append(kwargs)
        if len(attempts) < 3:
            raise ConnectionRefusedError("OBS is closed")
        return SimpleNamespace(base_client=new_base(**kwargs))

    monkeypatch.setattr(obs_websocket.obs, "ReqClient", fake_req_client)
    monkeypatch.setattr(obs_websocket._text_worker, "_initial_backoff", 0.01)
    with caplog.at_level(logging.ERROR):
        obs_websocket.update_text_source(client, "Time", "1:00")
        obs_websocket.update_text_source(client, "Time", "0:59")
        deadline = time.monotonic() + 10
        while not client.calls and time.monotonic() < deadline:
            time.sleep(0.01)
        flush()
    assert len(attempts) == 3
    assert client.calls == [("Time", "0:59", True)]
    assert "OBS is closed" in caplog.text


def test_closed_client_is_not_updated_or_reconnected():
    client = FakeClient()
    obs_websocket.close_obs_websocket(client)
    assert client.disconnected
    obs_websocket.update_text_source(client, "Time", "1:00")
    flush()
    assert client.calls == []


def test_a_client_closed_while_an_update_waits_is_not_reconnected(monkeypatch):
    # The update passed the "closed" check, then waited for the client's lock
    # while close_obs_websocket disconnected the client. It used to see the
    # closed socket as a lost connection and reconnect the closed client.
    client = FakeClient()
    created = []

    def fake_req_client(**kwargs):
        created.append(kwargs)
        return SimpleNamespace(base_client=new_base(**kwargs))

    monkeypatch.setattr(obs_websocket.obs, "ReqClient", fake_req_client)
    real_client_lock = obs_websocket.client_lock
    waiting = threading.Event()

    def spying_client_lock(obs_client):
        if threading.current_thread().name == "output-OBS":
            waiting.set()  # past the first "closed" check
        return real_client_lock(obs_client)

    monkeypatch.setattr(obs_websocket, "client_lock", spying_client_lock)
    with real_client_lock(client):  # e.g. a scene function running
        obs_websocket.update_text_source(client, "Time", "1:00")
        assert waiting.wait(5)
        obs_websocket.close_obs_websocket(client)
    flush()
    assert client.disconnected
    assert created == []
    assert client.calls == []


def test_scene_functions_wait_for_a_text_update_in_flight():
    # the websocket client isn't thread-safe: requests from the GUI thread
    # (scene creation) and the output thread must not interleave
    gate = threading.Event()
    client = FakeClient(gate=gate)
    obs_websocket.update_text_source(client, "Time", "1:00")
    assert client.started.wait(5)

    done = threading.Event()
    thread = threading.Thread(
        target=lambda: (obs_websocket.get_all_sources(client), done.set())
    )
    thread.start()
    assert not done.wait(0.2)  # blocked on the client's lock
    gate.set()
    assert done.wait(5)
    thread.join(5)
    assert client.calls == [("Time", "1:00", True), ("get_scene_list",)]


def test_obsws_does_not_log_the_password():
    # obsws-python logs "Connecting with parameters: ... password='...'" at INFO
    for name in ("obsws_python", "obsws_python.baseclient.ObsClient"):
        assert logging.getLogger(name).getEffectiveLevel() > logging.INFO


def test_open_obs_websocket(monkeypatch):
    calls = []

    class FakeReqClient:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def get_version(self):
            return SimpleNamespace(obs_version="31.0.0")

    monkeypatch.setattr(obs_websocket.obs, "ReqClient", FakeReqClient)
    client = obs_websocket.open_obs_websocket(
        {"ip": "localhost", "port": "4455", "password": "pw"}
    )
    assert isinstance(client, FakeReqClient)
    assert calls == [
        {
            "host": "localhost",
            "port": "4455",
            "password": "pw",
            "timeout": obs_websocket.OBS_TIMEOUT,
        }
    ]

    def refuse(**kwargs):
        raise ConnectionRefusedError("refused")

    monkeypatch.setattr(obs_websocket.obs, "ReqClient", refuse)
    assert (
        obs_websocket.open_obs_websocket({"ip": "x", "port": "1", "password": ""})
        is None
    )


def test_create_obs_scene_points_image_sources_at_the_bundled_images(caplog):
    class SceneClient:
        def __init__(self):
            self.inputs = []
            self.filters = []

        def get_scene_list(self):
            return SimpleNamespace(scenes=[])

        def create_scene(self, name):
            pass

        def create_input(self, sceneName, inputName, inputKind, inputSettings, **kw):
            self.inputs.append(inputSettings)

        def get_scene_item_id(self, scene, name):
            return SimpleNamespace(scene_item_id=1)

        def set_scene_item_transform(self, scene, item_id, transform):
            pass

        def create_source_filter(self, source, name, kind, settings):
            self.filters.append(settings)

    client = SceneClient()
    with caplog.at_level(logging.ERROR, logger=obs_websocket.logger.name):
        obs_websocket.create_obs_scene_from_export(client, "ScoreSight")
    assert not caplog.records

    images = [s["file"] for s in client.inputs if "file" in s]
    images += [s["image_path"] for s in client.filters if "image_path" in s]
    assert images
    for image in images:
        assert os.path.isfile(image), image
