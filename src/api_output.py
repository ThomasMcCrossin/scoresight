"""Outbound HTTP API: sends the readings of every detection cycle to a
user-configured URL (POST/PUT as JSON, XML or CSV, or GET query parameters).

update_out_api() is called on the GUI thread. It builds the request from a
snapshot of the results and hands it to a background OutputWorker, which keeps
only the most recent request: a slow or unreachable endpoint never makes
requests (or threads) pile up, and never blocks the caller.
"""

import csv
import io
import json
import xml.etree.ElementTree as ET
from typing import NamedTuple
from urllib.parse import quote, urlencode, urlparse

import requests

from output_worker import (
    HTTP_TIMEOUT,
    OutputWorker,
    ThrottledErrorLog,
    check_http_response,
)
from sc_logging import logger
from storage import fetch_data, subscribe_to_data
from text_detection_target import TextDetectionTargetWithResult

ENCODING_JSON_FULL = "JSON (Full)"
ENCODING_JSON_SIMPLE = "JSON (Simple key-value)"
ENCODING_XML = "XML"
ENCODING_CSV = "CSV"
ENCODINGS = (ENCODING_JSON_FULL, ENCODING_JSON_SIMPLE, ENCODING_XML, ENCODING_CSV)
METHODS = ("GET", "POST", "PUT")

# Formats without a per-reading state (JSON simple key-value and GET) carry only
# these: a receiver couldn't tell a rejected or empty reading from a real one.
GOOD_STATES = (
    TextDetectionTargetWithResult.ResultState.Success,
    TextDetectionTargetWithResult.ResultState.SameNoChange,
)

out_api_url = fetch_data("scoresight.json", "out_api_url", None)
out_api_encoding = fetch_data("scoresight.json", "out_api_encoding", ENCODING_JSON_FULL)
out_api_method = fetch_data("scoresight.json", "out_api_method", "POST")


def is_valid_url_urllib(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


# A request waiting to be sent, or being retried while the endpoint is
# unreachable, was built for the settings at that time: it is dropped when they
# change or the output is turned off (the next cycle builds a new one). The
# status (what was sent, what failed) starts over too.


def _restart():
    _worker.clear()
    _worker.reset_status()


def setup_out_api_url(url):
    global out_api_url
    out_api_url = url
    _restart()


def setup_out_api_encoding(encoding):
    global out_api_encoding
    out_api_encoding = encoding
    _restart()


def setup_out_api_method(method):
    global out_api_method
    out_api_method = method
    _restart()


def setup_out_api_enabled(enabled):
    if not enabled:
        _restart()


def out_api_status():
    """The sending's WorkerStatus (see output_worker)."""
    return _worker.status()


subscribe_to_data("scoresight.json", "out_api_url", setup_out_api_url)
subscribe_to_data("scoresight.json", "out_api_encoding", setup_out_api_encoding)
subscribe_to_data("scoresight.json", "out_api_method", setup_out_api_method)
subscribe_to_data("scoresight.json", "enable_out_api", setup_out_api_enabled)


class ApiRequest(NamedTuple):
    method: str
    url: str
    headers: dict[str, str]
    body: bytes | None


def good_values(data: list[TextDetectionTargetWithResult]) -> dict[str, str]:
    """{name: text} of the readings in a good state (Success, SameNoChange)."""
    return {r.name: r.result for r in data if r.result_state in GOOD_STATES}


def _xml_body(data: list[TextDetectionTargetWithResult]) -> bytes:
    root = ET.Element("root")
    for targetWithResult in data:
        resultEl = ET.SubElement(root, "result")
        resultEl.set("name", targetWithResult.name)
        resultEl.set("result", targetWithResult.result)
        resultEl.set("result_state", targetWithResult.result_state.name)
        resultEl.set("x", str(targetWithResult.x()))
        resultEl.set("y", str(targetWithResult.y()))
        resultEl.set("width", str(targetWithResult.width()))
        resultEl.set("height", str(targetWithResult.height()))
    return ET.tostring(root, encoding="utf-8")


def _csv_body(data: list[TextDetectionTargetWithResult]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Text", "State", "X", "Y", "Width", "Height"])
    for result in data:
        writer.writerow(
            [
                result.name,
                result.result,
                result.result_state.name,
                result.x(),
                result.y(),
                result.width(),
                result.height(),
            ]
        )
    return output.getvalue().encode("utf-8")


def build_request(
    data: list[TextDetectionTargetWithResult], url: str, method: str, encoding: str
) -> ApiRequest | None:
    """The request for one detection cycle, or None if there is nothing to send.

    GET and "JSON (Simple key-value)" carry no state, so they contain only the
    readings in a good state, and nothing is sent when there are none. The other
    encodings send every box with its state.
    """
    if method == "GET":
        values = good_values(data)
        if not values:
            return None
        separator = "&" if "?" in url else "?"
        # spaces as %20: not every receiver decodes "+" as a space
        query = urlencode(values, quote_via=quote)
        return ApiRequest("GET", url + separator + query, {}, None)

    if encoding == ENCODING_JSON_SIMPLE:
        values = good_values(data)
        if not values:
            return None
        body = json.dumps(values).encode("utf-8")
        content_type = "application/json"
    elif encoding == ENCODING_XML:
        body = _xml_body(data)
        content_type = "application/xml"
    elif encoding == ENCODING_CSV:
        body = _csv_body(data)
        content_type = "text/csv"
    else:  # ENCODING_JSON_FULL
        body = json.dumps([result.to_dict() for result in data]).encode("utf-8")
        content_type = "application/json"
    return ApiRequest(method, url, {"Content-Type": content_type}, body)


_session = requests.Session()  # used only by the worker thread


def _send_request(_key, request: ApiRequest) -> None:
    response = _session.request(
        request.method,
        request.url,
        headers=request.headers,
        data=request.body,
        timeout=HTTP_TIMEOUT,
    )
    check_http_response(response, f"{request.method} {request.url}")
    logger.debug("Output API: %s %s sent", request.method, request.url)


_worker = OutputWorker(
    "Output API",
    _send_request,
    retry_on=(requests.ConnectionError, requests.Timeout),
)
# settings problems are reported on every cycle; log them at most every 30 s
_settings_log = ThrottledErrorLog("Output API")
_unknown_encodings_reported: set[str] = set()


def update_out_api(data: list[TextDetectionTargetWithResult]):
    """Send this cycle's readings to the configured URL in the background."""
    url, method, encoding = out_api_url, out_api_method, out_api_encoding
    if not url:
        _settings_log.error("no URL set")
        return
    if not is_valid_url_urllib(url):
        _settings_log.error(f"Invalid URL: {url}")
        return
    if method not in METHODS:
        _settings_log.error(f"Invalid method: {method}")
        return
    if method != "GET" and encoding not in ENCODINGS:
        if encoding not in _unknown_encodings_reported:
            _unknown_encodings_reported.add(encoding)
            logger.warning(
                "Output API: unknown encoding %r, sending %s",
                encoding,
                ENCODING_JSON_FULL,
            )
        encoding = ENCODING_JSON_FULL

    request = build_request(data, url, method, encoding)
    if request is None:
        logger.debug("Output API: no good readings to send")
        return
    _worker.submit("request", request)
