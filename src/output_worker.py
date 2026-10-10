"""Background senders for the network outputs (vMix, UNO, OBS, outbound HTTP API).

OCR results reach MainWindow.ocrResult on the GUI thread several times a second.
Network calls must never run there: a slow or unreachable endpoint would freeze
the UI, and the queued results would pile up behind it.

Each output owns an OutputWorker. Callers hand it (key, item) pairs with submit(),
which never blocks. A single daemon thread per worker sends them. Pending items
are coalesced per key: a newer item for a key replaces an older one that hasn't
been sent yet, so the backlog is bounded by the number of keys (e.g. mapped
fields) and the endpoint always receives the latest values. Keys let outputs
that only send changed values (vMix, UNO, OBS) keep every field's latest value,
while snapshot outputs (the outbound API) use a single key.

Items must be plain, immutable snapshots (strings, tuples): the worker thread
reads them after the caller has moved on.

status() returns a WorkerStatus: what was sent, what failed and whether the
endpoint is being retried. It is a snapshot taken under the worker's lock, so
the GUI can read it at any time (output_status.py turns it into what the
window shows).
"""

import threading
import time
import weakref
from collections.abc import Callable, Hashable
from dataclasses import dataclass

from sc_logging import logger

# (connect, read) timeout in seconds for every HTTP request an output makes.
# Outputs send through one requests.Session each, used only by their worker
# thread, so connections (and TLS sessions) are reused between requests.
HTTP_TIMEOUT = (2.0, 2.0)


class ThrottledErrorLog:
    """Logs repeated errors at most once per interval, with the number of errors
    that were not logged in between, so a failing output doesn't flood the log
    on every detection cycle."""

    def __init__(self, label: str, interval: float = 30.0, clock=time.monotonic):
        self.label = label
        self.interval = interval
        self._clock = clock
        self._lock = threading.Lock()
        self._last_logged: float | None = None
        self._suppressed = 0

    def error(self, message: str) -> bool:
        """Log message as an error unless one was logged within the interval.
        Returns True if it was logged."""
        with self._lock:
            now = self._clock()
            if (
                self._last_logged is not None
                and now - self._last_logged < self.interval
            ):
                self._suppressed += 1
                return False
            suppressed, self._suppressed = self._suppressed, 0
            self._last_logged = now
        if suppressed:
            message += (
                f" ({suppressed} more error(s) since the last report were not logged)"
            )
        logger.error("%s: %s", self.label, message)
        return True

    def reset(self) -> None:
        """Forget the throttling state, so the next error is logged immediately."""
        with self._lock:
            self._last_logged = None
            self._suppressed = 0


class SendSkipped(Exception):
    """Raised by a send function for an item it deliberately didn't send (e.g.
    its connection was closed meanwhile): neither a success nor a failure."""


class OutputError(Exception):
    """The endpoint answered, but with an error (e.g. an HTTP error status)."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def check_http_response(response, request_description: str) -> None:
    """Raise OutputError unless response (a requests.Response) has a 2xx status."""
    if 200 <= response.status_code < 300:
        return
    body = " ".join((response.text or "").split())[:200]
    raise OutputError(
        f"{request_description} returned HTTP {response.status_code}"
        + (f": {body}" if body else ""),
        status_code=response.status_code,
    )


@dataclass(frozen=True)
class ErrorInfo:
    """A failure, without the exception object (which would keep the frames of
    its traceback alive)."""

    type: type
    message: str
    # an HTTP status (OutputError) or another numeric code of the error (e.g.
    # the code of an OBS request error)
    code: int | None = None
    # the endpoint couldn't be reached (the item is kept for a retry)
    unreachable: bool = False

    @classmethod
    def of(cls, error: BaseException, unreachable: bool = False) -> "ErrorInfo":
        code = getattr(error, "status_code", None)
        if code is None:
            code = getattr(error, "code", None)
        if isinstance(code, bool) or not isinstance(code, int):
            code = None
        return cls(type(error), str(error), code, unreachable)

    def __str__(self) -> str:
        name = self.type.__name__
        return f"{name}: {self.message}" if self.message else name


@dataclass(frozen=True)
class WorkerStatus:
    """A snapshot of an OutputWorker (see OutputWorker.status())."""

    name: str
    pending: int = 0  # items waiting to be sent
    busy: bool = False  # a batch is being sent
    sent: int = 0  # items sent successfully
    failed: int = 0  # items that failed
    consecutive_failures: int = 0  # failures since the last success
    # the endpoint couldn't be reached and nothing was sent since: the unsent
    # items are retried every retry_delay seconds
    retrying: bool = False
    retry_delay: float | None = None
    # keys (e.g. fields) whose latest item was sent, or failed and was dropped
    ok_keys: int = 0
    failing_keys: int = 0
    # times (of the worker's clock, time.monotonic by default)
    last_success_at: float | None = None
    last_failure_at: float | None = None
    last_error: ErrorInfo | None = None


_workers: "weakref.WeakSet[OutputWorker]" = weakref.WeakSet()
_workers_lock = threading.Lock()


class OutputWorker:
    """Sends submitted items from one background daemon thread.

    send(key, item) is called on the worker thread and reports a failure by
    raising. Exceptions of a type in retry_on mean the endpoint is unreachable
    (connection refused, timeout): the item and the rest of the batch are kept
    for a retry (unless a newer item for the same key arrives first) and the
    worker waits with exponential backoff before trying again. Any other
    exception drops that one item. Failures are logged through a
    ThrottledErrorLog; recovery from an unreachable endpoint is logged once.
    status() tells how the sending goes.
    """

    def __init__(
        self,
        name: str,
        send: Callable[[Hashable, object], None],
        *,
        retry_on: tuple[type[BaseException], ...] = (),
        initial_backoff: float = 0.5,
        max_backoff: float = 5.0,
        error_log: ThrottledErrorLog | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.name = name
        self._send = send
        self._retry_on = retry_on
        self._initial_backoff = initial_backoff
        self._max_backoff = max_backoff
        self.error_log = error_log or ThrottledErrorLog(name)
        self._clock = clock
        self._cond = threading.Condition()
        self._pending: dict[Hashable, object] = {}
        self._thread: threading.Thread | None = None
        self._busy = False
        self._stopped = False
        # incremented by clear(): the rest of a batch being sent is dropped too
        self._generation = 0
        self._retry_failures = 0  # consecutive "unreachable" failures
        # for status(), written with the lock held
        self._sent = 0
        self._failed = 0
        self._consecutive_failures = 0
        self._key_ok: dict[Hashable, bool] = {}  # latest result per key
        self._last_success_at: float | None = None
        self._last_failure_at: float | None = None
        self._last_error: ErrorInfo | None = None
        self._last_error_key: Hashable | None = None
        with _workers_lock:
            _workers.add(self)

    def submit(self, key: Hashable, item: object) -> None:
        """Queue item for key, replacing an unsent item for the same key.
        Never blocks on the network. Ignored after stop()."""
        with self._cond:
            if self._stopped:
                return
            self._pending[key] = item
            if self._thread is None:
                self._thread = threading.Thread(
                    target=self._run, name=f"output-{self.name}", daemon=True
                )
                self._thread.start()
            self._cond.notify_all()

    def clear(self) -> None:
        """Drop the items that haven't been sent yet (a request already in
        flight still completes)."""
        with self._cond:
            self._pending.clear()
            self._generation += 1
            self._cond.notify_all()

    def pending(self) -> dict[Hashable, object]:
        """A copy of the items waiting to be sent."""
        with self._cond:
            return dict(self._pending)

    def wait_idle(self, timeout: float | None = None) -> bool:
        """Wait until nothing is pending or being sent. Returns False on timeout."""
        with self._cond:
            return self._cond.wait_for(
                lambda: self._stopped or (not self._pending and not self._busy),
                timeout,
            )

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def status(self) -> WorkerStatus:
        """A snapshot of what was sent and what failed (thread-safe, never
        blocks on the network)."""
        with self._cond:
            error = self._last_error
            retrying = bool(
                self._retry_failures and error is not None and error.unreachable
            )
            return WorkerStatus(
                name=self.name,
                pending=len(self._pending),
                busy=self._busy,
                sent=self._sent,
                failed=self._failed,
                consecutive_failures=self._consecutive_failures,
                retrying=retrying,
                retry_delay=self._backoff_delay() if retrying else None,
                ok_keys=sum(1 for ok in self._key_ok.values() if ok),
                failing_keys=sum(1 for ok in self._key_ok.values() if not ok),
                last_success_at=self._last_success_at,
                last_failure_at=self._last_failure_at,
                last_error=error,
            )

    def reset_status(self) -> None:
        """Forget what was sent and what failed, e.g. when the output is turned
        off or sends somewhere else. The next error is logged right away."""
        with self._cond:
            self._sent = self._failed = self._consecutive_failures = 0
            self._retry_failures = 0
            self._key_ok.clear()
            self._last_success_at = self._last_failure_at = None
            self._last_error = self._last_error_key = None
        self.error_log.reset()

    def forget_keys(self, predicate: Callable[[Hashable], bool]) -> None:
        """Forget the results of the keys for which predicate(key) is true, e.g.
        the text sources of an OBS connection that was closed."""
        with self._cond:
            for key in [key for key in self._key_ok if predicate(key)]:
                del self._key_ok[key]
            if self._last_error_key is not None and predicate(self._last_error_key):
                self._last_error = self._last_error_key = None
                self._consecutive_failures = 0
                self._retry_failures = 0

    def stop(self, timeout: float = 2.0) -> bool:
        """Drop pending items and stop the thread, waiting up to timeout seconds
        for a request in flight to finish. Returns True if the thread ended."""
        with self._cond:
            self._stopped = True
            self._pending.clear()
            self._generation += 1
            self._cond.notify_all()
            thread = self._thread
        if thread is None or thread is threading.current_thread():
            return True
        thread.join(timeout)
        if thread.is_alive():
            logger.warning(
                "%s: output thread still busy after %.1fs; leaving it (daemon)",
                self.name,
                timeout,
            )
            return False
        return True

    # --- worker thread ----------------------------------------------------

    def _run(self) -> None:
        while True:
            with self._cond:
                self._cond.wait_for(lambda: self._stopped or self._pending)
                if self._stopped:
                    return
                batch, self._pending = self._pending, {}
                generation = self._generation
                self._busy = True
            try:
                unreachable = self._send_batch(list(batch.items()), generation)
            except Exception:  # never let the thread die
                logger.exception("%s: unexpected error in output thread", self.name)
                unreachable = False
            finally:
                with self._cond:
                    self._busy = False
                    self._cond.notify_all()
            if unreachable:
                with self._cond:
                    self._cond.wait_for(lambda: self._stopped, self._backoff_delay())

    def _backoff_delay(self) -> float:
        """The wait before retrying after self._retry_failures consecutive
        "unreachable" failures."""
        # cap the exponent: the failures go on for as long as the endpoint is
        # down, and 2 ** 1024 doesn't fit in a float (OverflowError would end
        # the thread, and with it the output, for the rest of the session)
        exponent = min(self._retry_failures - 1, 32)
        return min(self._initial_backoff * 2**exponent, self._max_backoff)

    def _send_batch(
        self, items: list[tuple[Hashable, object]], generation: int
    ) -> bool:
        """Send items in order. Returns True if the endpoint was unreachable (the
        unsent items were put back for a retry)."""
        for index, (key, item) in enumerate(items):
            if self._generation != generation:  # cleared or stopped meanwhile
                return False
            try:
                self._send(key, item)
            except SendSkipped:
                continue
            except self._retry_on as e:
                self._record_failure(key, e, generation, unreachable=True)
                self.error_log.error(_describe(e))
                with self._cond:
                    if self._generation == generation:
                        # retry the unsent items first; a newer item submitted
                        # meanwhile for the same key replaces the old one
                        retry = dict(items[index:])
                        retry.update(self._pending)
                        self._pending = retry
                return True
            except Exception as e:
                self._record_failure(key, e, generation, unreachable=False)
                self.error_log.error(_describe(e))
            else:
                if self._record_success(key, generation):
                    logger.info("%s: connection restored", self.name)
                    self.error_log.reset()
        return False

    def _record_failure(
        self, key: Hashable, error: Exception, generation: int, unreachable: bool
    ) -> None:
        with self._cond:
            if unreachable:
                self._retry_failures += 1
            if self._generation != generation:
                # cleared meanwhile (e.g. the output was turned off): the result
                # of a request that was in flight doesn't count
                return
            self._failed += 1
            self._consecutive_failures += 1
            if not unreachable:
                # dropped: the key's latest value didn't arrive
                self._key_ok[key] = False
            self._last_failure_at = self._clock()
            self._last_error = ErrorInfo.of(error, unreachable)
            self._last_error_key = key

    def _record_success(self, key: Hashable, generation: int) -> bool:
        """Returns True if the endpoint was unreachable until now."""
        with self._cond:
            restored = self._retry_failures > 0
            self._retry_failures = 0
            if self._generation == generation:
                self._sent += 1
                self._consecutive_failures = 0
                self._key_ok[key] = True
                self._last_success_at = self._clock()
            return restored


def _describe(e: BaseException) -> str:
    text = str(e)
    return f"{type(e).__name__}: {text}" if text else type(e).__name__


def stop_all_workers(timeout: float = 2.0) -> bool:
    """Stop every OutputWorker, sharing one timeout. Returns True if all ended."""
    with _workers_lock:
        workers = list(_workers)
    deadline = time.monotonic() + timeout
    all_stopped = True
    for worker in workers:
        remaining = max(0.0, deadline - time.monotonic())
        all_stopped = worker.stop(remaining) and all_stopped
    return all_stopped
