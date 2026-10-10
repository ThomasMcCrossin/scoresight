import logging
import threading
import time

import pytest

from output_worker import OutputWorker, ThrottledErrorLog, stop_all_workers


class Recorder:
    """send() callable that records calls and can be held on an Event."""

    def __init__(self, gate: threading.Event | None = None, errors=None):
        self.calls = []
        self.gate = gate
        self.started = threading.Event()
        # {call index: exception to raise}
        self.errors = dict(errors or {})
        self.lock = threading.Lock()

    def __call__(self, key, item):
        with self.lock:
            index = len(self.calls)
            self.calls.append((key, item))
        self.started.set()
        if self.gate is not None:
            assert self.gate.wait(5), "test gate never opened"
        if index in self.errors:
            raise self.errors[index]


@pytest.fixture
def make_worker():
    workers = []

    def _make(send, **kwargs):
        worker = OutputWorker("test", send, **kwargs)
        workers.append(worker)
        return worker

    yield _make
    for worker in workers:
        worker.stop(2)


def test_submit_does_not_block_on_a_slow_endpoint(make_worker):
    gate = threading.Event()
    send = Recorder(gate)
    worker = make_worker(send)

    start = time.monotonic()
    for i in range(200):
        worker.submit("field", i)
    elapsed = time.monotonic() - start
    assert send.started.wait(2)
    assert elapsed < 0.5  # the "endpoint" is stuck, the caller is not

    gate.set()
    assert worker.wait_idle(5)


def test_latest_value_wins_per_key(make_worker):
    gate = threading.Event()
    send = Recorder(gate)
    worker = make_worker(send)

    worker.submit("a", 0)
    assert send.started.wait(2)  # the worker is now stuck sending a=0
    for i in range(1, 100):
        worker.submit("a", i)
    worker.submit("b", "only")
    assert worker.pending() == {"a": 99, "b": "only"}  # bounded backlog

    gate.set()
    assert worker.wait_idle(5)
    assert send.calls == [("a", 0), ("a", 99), ("b", "only")]


def test_other_keys_are_not_lost_when_one_key_is_overwritten(make_worker):
    # vMix/UNO only send changed fields: a field changed in an older cycle must
    # still be sent even if a newer cycle (without that field) replaced it.
    gate = threading.Event()
    send = Recorder(gate)
    worker = make_worker(send)

    worker.submit("Time", "1:00")
    assert send.started.wait(2)
    worker.submit("Home Score", "12")  # cycle 2: score and clock changed
    worker.submit("Time", "0:59")
    worker.submit("Time", "0:58")  # cycle 3: only the clock changed
    gate.set()
    assert worker.wait_idle(5)
    assert send.calls == [("Time", "1:00"), ("Home Score", "12"), ("Time", "0:58")]


def test_unreachable_endpoint_is_retried_with_the_latest_value(make_worker, caplog):
    send = Recorder(errors={0: ConnectionError("refused")})
    worker = make_worker(
        send, retry_on=(ConnectionError,), initial_backoff=0.01, max_backoff=0.01
    )

    with caplog.at_level(logging.INFO):
        worker.submit("a", 1)
        worker.submit("b", 2)
        assert worker.wait_idle(5)

    # a=1 failed as "unreachable", so a and b were both kept and retried
    assert send.calls == [("a", 1), ("a", 1), ("b", 2)]
    messages = [r.getMessage() for r in caplog.records]
    assert any("ConnectionError: refused" in m for m in messages)
    assert any("connection restored" in m for m in messages)


def test_newer_value_replaces_a_failed_one(make_worker):
    gate = threading.Event()
    send = Recorder(gate, errors={0: ConnectionError("down")})
    worker = make_worker(
        send, retry_on=(ConnectionError,), initial_backoff=0.01, max_backoff=0.01
    )

    worker.submit("a", "old")
    assert send.started.wait(2)
    worker.submit("a", "new")  # arrives while "old" is failing
    gate.set()
    assert worker.wait_idle(5)
    assert send.calls == [("a", "old"), ("a", "new")]


def test_other_errors_drop_only_that_item(make_worker, caplog):
    send = Recorder(errors={0: ValueError("HTTP 500")})
    worker = make_worker(send, retry_on=(ConnectionError,))

    with caplog.at_level(logging.ERROR):
        worker.submit("a", 1)
        worker.submit("b", 2)
        assert worker.wait_idle(5)

    assert send.calls == [("a", 1), ("b", 2)]
    assert any("HTTP 500" in r.getMessage() for r in caplog.records)


def test_worker_survives_errors_and_keeps_sending(make_worker):
    send = Recorder(errors={i: RuntimeError("boom") for i in range(5)})
    worker = make_worker(send)
    for i in range(10):
        worker.submit(i, i)
        assert worker.wait_idle(5)
    assert [item for _, item in send.calls] == list(range(10))
    assert worker.is_running


def test_clear_drops_pending_items_and_the_rest_of_the_batch(make_worker):
    # e.g. the user clicks "Stop vMix" while a batch of fields is being sent
    x_gate, a_started, a_gate = threading.Event(), threading.Event(), threading.Event()
    calls = []

    def send(key, item):
        calls.append(key)
        if key == "x":
            assert x_gate.wait(5)
        if key == "a":
            a_started.set()
            assert a_gate.wait(5)

    worker = make_worker(send)
    worker.submit("x", 0)
    deadline = time.monotonic() + 5
    while not calls and time.monotonic() < deadline:
        time.sleep(0.01)
    for key in "abc":
        worker.submit(key, 1)  # the next batch: a, b, c
    x_gate.set()
    assert a_started.wait(5)

    worker.clear()
    a_gate.set()
    assert worker.wait_idle(5)
    assert calls == ["x", "a"]


def test_thread_starts_lazily_is_daemon_and_stops(make_worker):
    send = Recorder()
    worker = make_worker(send)
    assert not worker.is_running

    worker.submit("a", 1)
    assert worker.wait_idle(5)
    thread = worker._thread
    assert thread.daemon
    assert thread.name == "output-test"

    assert worker.stop(2)
    assert not thread.is_alive()
    worker.submit("a", 2)  # ignored after stop
    assert worker.pending() == {}
    assert send.calls == [("a", 1)]


def test_stop_is_bounded_while_a_request_hangs(make_worker):
    gate = threading.Event()
    send = Recorder(gate)
    worker = make_worker(send)
    worker.submit("a", 1)
    assert send.started.wait(2)
    try:
        start = time.monotonic()
        assert worker.stop(0.2) is False
        assert time.monotonic() - start < 1.0
    finally:
        gate.set()
    worker._thread.join(2)
    assert not worker._thread.is_alive()


def test_stop_all_workers(make_worker):
    first = make_worker(Recorder())
    second = make_worker(Recorder())
    first.submit("a", 1)
    second.submit("a", 1)
    assert first.wait_idle(5) and second.wait_idle(5)

    assert stop_all_workers(2)
    assert not first.is_running
    assert not second.is_running


def test_throttled_error_log(caplog):
    now = [100.0]
    log = ThrottledErrorLog("vMix", interval=30, clock=lambda: now[0])

    with caplog.at_level(logging.ERROR):
        assert log.error("down")
        for _ in range(5):
            now[0] += 1
            assert not log.error("down")
        now[0] += 30
        assert log.error("still down")
        log.reset()
        assert log.error("down again")

    messages = [r.getMessage() for r in caplog.records]
    assert messages == [
        "vMix: down",
        "vMix: still down (5 more error(s) since the last report were not logged)",
        "vMix: down again",
    ]
