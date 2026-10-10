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
        },
        {
            "name": "Time",
            "text": "SIM",
            "state": "FailedFilter",
            "rect": {"x": 1.0, "y": 2.0, "width": 3.0, "height": 4.0},
        },
    ]


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
