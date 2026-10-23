"""The HTTP server's endpoints, exercised over HTTP against a real server on a
free port."""

import csv
import io
import xml.etree.ElementTree as ET
from xml.parsers import expat

import pytest
import requests

import http_server


@pytest.fixture(scope="module")
def base_url():
    http_server.start_http_server(port=0)
    port = http_server.get_http_server_port()
    assert port
    yield f"http://127.0.0.1:{port}"
    http_server.stop_http_server()
    http_server.update_http_server([])


@pytest.fixture
def publish(make_result):
    def _publish(*readings):
        http_server.update_http_server([make_result(*r) for r in readings])

    yield _publish
    http_server.update_http_server([])


def get(base_url, path):
    response = requests.get(base_url + path, timeout=5)
    assert response.status_code == 200, response.text
    return response


def parse_xml(text: str) -> ET.Element:
    # expat enforces well-formedness, including valid element names
    parser = expat.ParserCreate()
    parser.Parse(text, True)
    return ET.fromstring(text)


def test_empty_before_first_reading(base_url):
    http_server.update_http_server([])
    assert get(base_url, "/json").json() == []
    assert get(base_url, "/json?pivot").json() == {}
    assert parse_xml(get(base_url, "/xml").text).tag == "data"
    assert get(base_url, "/csv").text.splitlines() == ["Name,Text,X,Y,Width,Height"]


def test_json(base_url, publish):
    publish(
        ("Home Score", "12", "Success", (10, 20, 30, 40)),
        ("Time", "SIM", "FailedFilter", (1, 2, 3, 4)),
    )
    assert get(base_url, "/json").json() == [
        {
            "name": "Home Score",
            "text": "12",
            "state": "Success",
            "rect": {"x": 10.0, "y": 20.0, "width": 30.0, "height": 40.0},
            "captured_at": None,
            "latency_ms": None,
        },
        {
            "name": "Time",
            "text": "SIM",
            "state": "FailedFilter",
            "rect": {"x": 1.0, "y": 2.0, "width": 3.0, "height": 4.0},
            "captured_at": None,
            "latency_ms": None,
        },
    ]


def test_json_carries_when_each_frame_was_captured_and_how_late(base_url, make_result):
    """captured_at is the wall-clock time of the frame the readings came from
    (ISO-8601 with its offset) and latency_ms is how long from reading that
    frame to publishing them, so a consumer can tell what it is looking at and
    how old it is."""
    from datetime import datetime, timezone

    captured = datetime(2026, 10, 23, 9, 10, 22, 500_000, tzinfo=timezone.utc)
    http_server.update_http_server(
        [make_result("Home Score", "12", captured_at=captured, latency_ms=42.25)]
    )
    try:
        [reading] = get(base_url, "/json").json()
        assert reading["captured_at"] == "2026-10-23T09:10:22.500+00:00"
        assert reading["latency_ms"] == 42.2
        # a reading with no provenance says so
        http_server.update_http_server([make_result("Away Score", "3")])
        [reading] = get(base_url, "/json").json()
        assert reading["captured_at"] is None
        assert reading["latency_ms"] is None
    finally:
        http_server.update_http_server([])


# --- /health ----------------------------------------------------------------------


def test_health_is_not_ok_without_a_source(base_url):
    http_server.update_health(http_server.HealthSnapshot())
    try:
        body = get(base_url, "/health").json()
        assert body["ok"] is False
        assert body["source_open"] is False
        assert body["stale"] is True
        assert body["age_s"] is None
        assert body["engine"] is None
    finally:
        http_server.update_health(http_server.HealthSnapshot())


def test_health_reports_a_fresh_running_source(base_url):
    import time

    now = time.monotonic()
    http_server.update_health(
        http_server.HealthSnapshot(
            last_cycle_at="2026-10-23T09:10:22.500+00:00",
            last_cycle_monotonic=now,
            fps=5.0,
            nominal_fps=5.0,
            retry_count=0,
            detection_interval_s=0.5,
            engine={"model": "ppocr:auto", "state": "ready"},
            source_open=True,
        )
    )
    try:
        body = get(base_url, "/health").json()
        assert body["ok"] is True
        assert body["stale"] is False
        assert 0 <= body["age_s"] < 1
        assert body["fps"] == 5.0 and body["nominal_fps"] == 5.0
        assert body["retry_count"] == 0
        assert body["last_cycle_at"] == "2026-10-23T09:10:22.500+00:00"
        assert body["engine"] == {"model": "ppocr:auto", "state": "ready"}
    finally:
        http_server.update_health(http_server.HealthSnapshot())


def test_health_is_not_ok_when_the_readings_are_stale():
    """No processed frame for more than 3 detection intervals (or 5 s, if that
    is longer) is stale: the source delivers nothing ScoreSight can read."""
    import time

    now = time.monotonic()
    # 10 detections per second: the floor of 5 s applies
    snapshot = http_server.HealthSnapshot(
        last_cycle_monotonic=now - 4.0, detection_interval_s=0.1, source_open=True
    )
    assert http_server.health_dict(snapshot, now)["ok"] is True
    assert http_server.health_dict(snapshot, now)["stale_after_s"] == 5.0
    stale = http_server.HealthSnapshot(
        last_cycle_monotonic=now - 6.0, detection_interval_s=0.1, source_open=True
    )
    body = http_server.health_dict(stale, now)
    assert body["ok"] is False and body["stale"] is True
    # 0.1 detections per second: 3 intervals (30 s) is the limit
    slow = http_server.HealthSnapshot(
        last_cycle_monotonic=now - 20.0, detection_interval_s=10.0, source_open=True
    )
    assert http_server.health_dict(slow, now)["ok"] is True
    assert http_server.health_dict(slow, now)["stale_after_s"] == 30.0


def test_health_is_not_ok_when_the_source_failed():
    import time

    body = http_server.health_dict(
        http_server.HealthSnapshot(
            last_cycle_monotonic=time.monotonic(),
            source_open=True,
            source_error="Error: Unable to play video stream",
        )
    )
    assert body["ok"] is False
    assert body["source_error"] == "Error: Unable to play video stream"


def test_pivot_variants_contain_only_good_readings(base_url, publish):
    publish(
        ("Home Score", "12", "Success"),
        ("Away Score", "7", "SameNoChange"),
        ("Time", "SIM", "FailedFilter"),
        ("Period", "", "Empty"),
    )
    assert get(base_url, "/json?pivot").json() == {
        "Home Score": "12",
        "Away Score": "7",
    }

    root = parse_xml(get(base_url, "/xml?pivot").text)
    assert [(el.tag, el.text) for el in root] == [
        ("HomeScore", "12"),
        ("AwayScore", "7"),
    ]

    rows = list(csv.reader(io.StringIO(get(base_url, "/csv?pivot").text)))
    assert rows == [["Home Score", "Away Score"], ["12", "7"]]


def test_csv_has_numeric_geometry(base_url, publish):
    # used to contain "<built-in method x of ...>" instead of the numbers
    publish(
        ("Home Score", "12", "Success", (10.5, 20, 30, 40)),
        ("Name, with comma", 'say "hi"', "Success", (1, 2, 3, 4)),
    )
    response = get(base_url, "/csv")
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == ["Name", "Text", "X", "Y", "Width", "Height"]
    assert rows[1] == ["Home Score", "12", "10.5", "20.0", "30.0", "40.0"]
    assert rows[2] == ["Name, with comma", 'say "hi"', "1.0", "2.0", "3.0", "4.0"]
    for row in rows[1:]:
        [float(value) for value in row[2:]]


def test_xml_full(base_url, publish):
    publish(("Home Score", "1 < 2 & \x01", "SameNoChange", (1, 2, 3, 4)))
    response = get(base_url, "/xml")
    assert response.headers["content-type"].startswith("text/xml")
    root = parse_xml(response.text)
    assert [el.attrib for el in root] == [
        {
            "name": "Home Score",
            "result": "1 < 2 & ",
            "result_state": "SameNoChange",
            "x": "1.0",
            "y": "2.0",
            "width": "3.0",
            "height": "4.0",
        }
    ]


def test_xml_pivot_with_names_that_are_not_valid_xml(base_url, publish):
    names = ["1st Half", "Score (H)", "Home/Away", "-", "Tore Gäste", "Shot Clock"]
    publish(*[(name, str(i), "Success") for i, name in enumerate(names)])
    root = parse_xml(get(base_url, "/xml?pivot").text)  # used to be malformed
    assert [(el.tag, el.text) for el in root] == [
        ("_1StHalf", "0"),
        ("ScoreH", "1"),
        ("HomeAway", "2"),
        ("_-", "3"),
        ("ToreGäste", "4"),
        ("ShotClock", "5"),
    ]


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Home Score", "HomeScore"),
        ("Time", "Time"),
        ("shot  clock", "ShotClock"),
        ("1st Half", "_1StHalf"),
        ("", "_"),
        ("a:b", "AB"),
        ("x.y-z_1", "X.Y-Z_1"),
    ],
)
def test_xml_element_name(name, expected):
    tag = http_server.xml_element_name(name)
    assert tag == expected
    parse_xml(f"<{tag}/>")


def test_results_are_snapshotted(base_url, make_result):
    result = make_result("Home Score", "12", "Success")
    http_server.update_http_server([result])
    result.result = "99"  # e.g. MainWindow reusing the object afterwards
    assert get(base_url, "/json?pivot").json() == {"Home Score": "12"}
    http_server.update_http_server([])


def test_html_page_uses_a_relative_url(base_url):
    page = get(base_url, "/scoresight").text
    assert "fetch('/json')" in page
    assert "localhost" not in page
    assert "18099" not in page


def test_shutdown_endpoint_is_gone(base_url):
    response = requests.get(base_url + "/shutdown", timeout=5)
    assert response.status_code in (404, 405)
    # and the server is still serving
    assert get(base_url, "/json").status_code == 200


def test_cors_allows_any_origin(base_url):
    response = requests.get(
        base_url + "/json", headers={"Origin": "http://example.com"}, timeout=5
    )
    assert response.headers["access-control-allow-origin"] == "*"


def test_requests_are_counted(base_url):
    # the window shows "http://... · 2 clients" and when the last request came
    before = http_server.http_server_stats()
    for path in ("/json", "/xml?pivot", "/scoresight"):
        get(base_url, path)
    stats = http_server.http_server_stats()
    assert stats.requests == before.requests + 3
    assert stats.last_request_at is not None
    assert before.last_request_at is None or stats.last_request_at > (
        before.last_request_at
    )
    assert stats.recent_clients >= 1  # 127.0.0.1
    assert stats.start_error is None
    # a client that has been quiet for a while no longer counts as connected
    later = http_server.http_server_stats(
        now=stats.last_request_at + http_server.RECENT_CLIENT_S + 1
    )
    assert later.recent_clients == 0
    assert later.requests == stats.requests


def test_api_docs_are_served(base_url):
    assert get(base_url, "/openapi.json").json()["paths"].keys() >= {
        "/json",
        "/xml",
        "/csv",
        "/scoresight",
    }
    assert "/shutdown" not in get(base_url, "/openapi.json").json()["paths"]


# --- shapes for programs that poll (all opt-in) ------------------------------


def test_existing_pivot_bodies_are_unchanged(base_url, publish):
    # the new shapes are opt-in: the bodies of the existing URLs stay the same
    publish(
        ("Home Score", "12", "Success"),
        ("Away Score", "7", "SameNoChange"),
        ("Time", "SIM", "FailedFilter"),
        ("Period", "", "Empty"),
    )
    assert get(base_url, "/json?pivot").content == (
        b'{"Home Score":"12","Away Score":"7"}'
    )
    assert get(base_url, "/xml?pivot").content == (
        b"<data><HomeScore>12</HomeScore><AwayScore>7</AwayScore></data>"
    )
    assert get(base_url, "/csv?pivot").content == b"Home Score,Away Score\r\n12,7\r\n"
    assert get(base_url, "/csv").content.startswith(
        b"Name,Text,X,Y,Width,Height\r\nHome Score,12,1.0,2.0,3.0,4.0\r\n"
    )


def test_pivot_all_has_every_box_with_its_last_good_value(base_url, publish):
    # with only the good readings of the latest cycle, a box whose reading is
    # rejected for a moment drops out, and column readers (XPression DataLinq,
    # vMix) blank the field or lose the column
    publish(
        ("Home Score", "12", "Success"),
        ("Away Score", "7", "SameNoChange"),
        ("Time", "SIM", "FailedFilter"),  # no good reading yet
    )
    publish(
        ("Home Score", "13", "FailedFilter"),  # rejected: keeps "12"
        ("Away Score", "8", "Success"),
        ("Time", "4:59", "Success"),
    )
    expected = {"Home Score": "12", "Away Score": "8", "Time": "4:59"}
    assert get(base_url, "/json?pivot&all").json() == expected
    # the plain pivot still has only this cycle's good readings
    assert get(base_url, "/json?pivot").json() == {"Away Score": "8", "Time": "4:59"}
    rows = list(csv.reader(io.StringIO(get(base_url, "/csv?pivot&all").text)))
    assert rows == [["Home Score", "Away Score", "Time"], ["12", "8", "4:59"]]
    root = parse_xml(get(base_url, "/xml?pivot&all").text)
    assert [(el.tag, el.text) for el in root] == [
        ("HomeScore", "12"),
        ("AwayScore", "8"),
        ("Time", "4:59"),
    ]


def test_pivot_all_before_the_first_good_reading(base_url, publish):
    publish(("Home Score", "SIM", "FailedFilter"), ("Period", "", "Empty"))
    assert get(base_url, "/json?pivot&all").json() == {"Home Score": "", "Period": ""}
    rows = list(csv.reader(io.StringIO(get(base_url, "/csv?pivot&all").text)))
    assert rows == [["Home Score", "Period"], ["", ""]]


def test_a_removed_box_is_forgotten(base_url, publish):
    publish(("Home Score", "12", "Success"), ("Logo", "x", "Success"))
    publish(("Home Score", "12", "SameNoChange"))
    assert get(base_url, "/json?pivot&all").json() == {"Home Score": "12"}
    publish(("Home Score", "12", "SameNoChange"), ("Logo", "?", "FailedFilter"))
    assert get(base_url, "/json?pivot&all").json() == {"Home Score": "12", "Logo": ""}


def test_json_array_for_vmix_data_sources(base_url, publish):
    # vMix JSON Data Sources read an array of row objects, not one object
    publish(
        ("Home Score", "12", "Success"),
        ("Time", "SIM", "FailedFilter"),
    )
    expected = [{"Home Score": "12", "Time": ""}]
    assert get(base_url, "/json?pivot&array").json() == expected
    assert get(base_url, "/json?array").json() == expected
    http_server.update_http_server([])
    assert get(base_url, "/json?pivot&array").json() == [{}]


@pytest.mark.parametrize(
    "path",
    [
        "/json",
        "/json?pivot",
        "/json?pivot&array",
        "/xml?pivot",
        "/csv?pivot&all",
        "/scoresight",
    ],
)
def test_data_is_never_cached(base_url, path):
    # pollers with an HTTP cache (Windows components, proxies) would show a
    # stale score
    headers = get(base_url, path).headers
    assert "no-store" in headers["cache-control"]
    assert "no-cache" in headers["cache-control"]
    assert headers["pragma"] == "no-cache"
    assert headers["expires"] == "0"


def test_cors_preflight_from_a_public_page(base_url):
    # a page on a public https site reading ScoreSight on the local network:
    # Chromium's Private Network Access preflight
    response = requests.options(
        base_url + "/json?pivot",
        headers={
            "Origin": "https://graphics.example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Private-Network": "true",
        },
        timeout=5,
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert response.headers["access-control-allow-private-network"] == "true"
    assert "GET" in response.headers["access-control-allow-methods"]


def test_game(base_url, make_result):
    import sports
    from game_state import GameEngine, GameState

    assert get(base_url, "/game").json()["sport"] == "none"
    engine = GameEngine(sports.BASKETBALL)
    for score in ("0", "0", "3", "3"):
        engine.update(
            [
                make_result("Home Score", score),
                make_result("Away Score", "0"),
                make_result("Period", "1"),
            ]
        )
    http_server.update_game_state(engine.state())
    try:
        data = get(base_url, "/game").json()
        assert data["sport"] == "basketball"
        assert data["home"]["score"] == 3 and data["away"]["score"] == 0
        assert data["period_label"] == "Q1"
        assert [event["text"] for event in data["events"]] == ["Home +3 (3–0)"]
        # only the events after an id
        since = data["events"][-1]["id"]
        assert get(base_url, f"/game?since={since}").json()["events"] == []
    finally:
        http_server.update_game_state(GameState(sport="none", roles={}))
