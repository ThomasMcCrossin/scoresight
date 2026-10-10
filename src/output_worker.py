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
"""

import threading
import time
import weakref
from collections.abc import Callable, Hashable

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
    ):
        self.name = name
        self._send = send
        self._retry_on = retry_on
        self._initial_backoff = initial_backoff
        self._max_backoff = max_backoff
        self.error_log = error_log or ThrottledErrorLog(name)
        self._cond = threading.Condition()
        self._pending: dict[Hashable, object] = {}
        self._thread: threading.Thread | None = None
        self._busy = False
        self._stopped = False
        self._retry_failures = 0  # consecutive "unreachable" failures
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
        """Drop the items that haven't been sent yet."""
        with self._cond:
            self._pending.clear()
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

    def stop(self, timeout: float = 2.0) -> bool:
        """Drop pending items and stop the thread, waiting up to timeout seconds
        for a request in flight to finish. Returns True if the thread ended."""
        with self._cond:
            self._stopped = True
            self._pending.clear()
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
                self._busy = True
            try:
                unreachable = self._send_batch(list(batch.items()))
            except Exception:  # never let the thread die
                logger.exception("%s: unexpected error in output thread", self.name)
                unreachable = False
            finally:
                with self._cond:
                    self._busy = False
                    self._cond.notify_all()
            if unreachable:
                delay = min(
                    self._initial_backoff * 2 ** (self._retry_failures - 1),
                    self._max_backoff,
                )
                with self._cond:
                    self._cond.wait_for(lambda: self._stopped, delay)

    def _send_batch(self, items: list[tuple[Hashable, object]]) -> bool:
        """Send items in order. Returns True if the endpoint was unreachable (the
        unsent items were put back for a retry)."""
        for index, (key, item) in enumerate(items):
            if self._stopped:
                return False
            try:
                self._send(key, item)
            except self._retry_on as e:
                self._retry_failures += 1
                self.error_log.error(_describe(e))
                with self._cond:
                    if not self._stopped:
                        for k, v in items[index:]:
                            # a newer item submitted meanwhile wins
                            self._pending.setdefault(k, v)
                return True
            except Exception as e:
                self.error_log.error(_describe(e))
            else:
                if self._retry_failures:
                    logger.info("%s: connection restored", self.name)
                    self._retry_failures = 0
                    self.error_log.reset()
        return False


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
