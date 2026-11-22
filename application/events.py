"""Observer pattern: event bus with synchronous and asynchronous publishing.

Subscribers: structured JSON console logger and optional JSONL file sink.
All logging is structured; no operational print() calls in domain/persistence.

The bus is thread-safe and supports async delivery via a bounded queue drained
by a daemon worker thread - suitable for high-concurrency scenarios where event
sinks (disk, network) should not block the caller. ``emit`` enqueues by default;
``emit_sync`` delivers inline; ``flush`` waits for queued events (used by tests).
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List

MAX_QUEUE = 10000


@dataclass
class Event:
    name: str
    data: dict
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        return json.dumps(
            {"event": self.name, "timestamp": self.timestamp, "data": self.data},
            ensure_ascii=False, sort_keys=True,
        )


class EventBus:
    """Observer bus with subscriber registry and async delivery worker."""

    def __init__(self, async_mode: bool = True):
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self._lock = threading.RLock()
        self._queue: queue.Queue = queue.Queue(maxsize=MAX_QUEUE)
        self._async_mode = async_mode
        self._worker: threading.Thread | None = None
        self._done = threading.Event()
        self._pending = threading.Condition()
        self._inflight = 0
        if async_mode:
            self._start_worker()

    def _start_worker(self) -> None:
        self._worker = threading.Thread(
            target=self._drain, name="event-bus-worker", daemon=True)
        self._worker.start()

    def _drain(self) -> None:
        while not self._done.is_set():
            try:
                evt = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self._deliver(evt)
            finally:
                with self._pending:
                    self._inflight -= 1
                    if self._inflight == 0:
                        self._pending.notify_all()
                self._queue.task_done()

    def subscribe(self, event: str, handler: Callable[[Event], None]) -> None:
        with self._lock:
            self._subscribers.setdefault(event, []).append(handler)

    def _deliver(self, evt: Event) -> None:
        with self._lock:
            handlers = list(self._subscribers.get(evt.name, []))
            handlers += list(self._subscribers.get("*", []))
        for handler in handlers:
            try:
                handler(evt)
            except Exception:
                pass

    def emit(self, event: str, data: dict | None = None) -> Event:
        """Publish asynchronously (non-blocking). Falls back to sync if full."""
        evt = Event(event, data or {})
        if not self._async_mode:
            self._deliver(evt)
            return evt
        with self._pending:
            self._inflight += 1
        try:
            self._queue.put_nowait(evt)
        except queue.Full:
            # Sink back-pressure: deliver inline rather than drop the event.
            with self._pending:
                self._inflight -= 1
            self._deliver(evt)
        return evt

    def emit_sync(self, event: str, data: dict | None = None) -> Event:
        """Publish inline (deterministic, used by tests/critical paths)."""
        evt = Event(event, data or {})
        self._deliver(evt)
        return evt

    def flush(self, timeout: float = 5.0) -> bool:
        """Wait until all queued events have been delivered."""
        if not self._async_mode:
            return True
        with self._pending:
            if self._inflight == 0:
                return True
            return self._pending.wait_for(lambda: self._inflight == 0, timeout)

    def shutdown(self, timeout: float = 5.0) -> None:
        """Drain remaining events and stop the worker."""
        self.flush(timeout)
        self._done.set()
        if self._worker is not None:
            self._worker.join(timeout=1.0)


def _console_sink(evt: Event) -> None:
    print(evt.to_json(), file=sys.stderr)


class FileSink:
    """Append structured JSON events to a JSONL file."""

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()

    def __call__(self, evt: Event) -> None:
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with self._lock:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(evt.to_json() + "\n")
        except OSError:
            pass


bus = EventBus()
bus.subscribe("*", _console_sink)
