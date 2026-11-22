"""Observer pattern: event bus with subscribers.

Subscribers: structured JSON console logger and optional JSONL file sink.
All logging is structured; no operational print() calls in domain/persistence.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List


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
    """Simple synchronous observer bus, thread-safe for subscription."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event: str, handler: Callable[[Event], None]) -> None:
        with self._lock:
            self._subscribers.setdefault(event, []).append(handler)

    def emit(self, event: str, data: dict | None = None) -> Event:
        evt = Event(event, data or {})
        for handler in list(self._subscribers.get(event, [])):
            try:
                handler(evt)
            except Exception:
                pass
        for handler in list(self._subscribers.get("*", [])):
            try:
                handler(evt)
            except Exception:
                pass
        return evt


def _console_sink(evt: Event) -> None:
    # Structured JSON to stderr (never stdout, which is reserved for data).
    print(evt.to_json(), file=sys.stderr)


class FileSink:
    """Append structured JSON events to a JSONL file."""

    def __init__(self, path: str):
        self.path = path

    def __call__(self, evt: Event) -> None:
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(evt.to_json() + "\n")
        except OSError:
            pass


bus = EventBus()
bus.subscribe("*", _console_sink)
