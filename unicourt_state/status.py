"""Thread-safe progress reporting for the CLI.

Event lines ("25STCV01  saved pdfs/...") are printed as they happen. In a
terminal a one-line status bar is kept at the bottom and redrawn every second;
when stderr is not a terminal (piped, logged) the status line is printed as a
plain line every ``quiet_interval`` seconds instead, so logs stay readable.
"""

from __future__ import annotations

import sys
import threading
import time
from typing import TextIO


class Status:
    COUNTERS = ("done", "active", "ordering", "pdfs", "texts", "failed")

    def __init__(
        self,
        stream: TextIO | None = None,
        live: bool | None = None,
        interval: float = 1.0,
        quiet_interval: float = 30.0,
    ):
        self.stream = stream or sys.stderr
        self.live = self.stream.isatty() if live is None else live
        self.interval = interval if self.live else quiet_interval
        self.phase = ""
        self.total = 0
        self.counts = dict.fromkeys(self.COUNTERS, 0)
        self._lock = threading.Lock()
        self._shown = False
        self._start = time.monotonic()
        self._stop = threading.Event()
        self._ticker: threading.Thread | None = None

    # -- lifecycle -----------------------------------------------------------

    def start(self, phase: str, total: int) -> "Status":
        with self._lock:
            self.phase, self.total = phase, total
            self.counts = dict.fromkeys(self.COUNTERS, 0)
            self._start = time.monotonic()
        self._stop.clear()
        self._ticker = threading.Thread(target=self._tick, name="status", daemon=True)
        self._ticker.start()
        self._draw()
        return self

    def finish(self) -> None:
        """Stop the ticker and leave the final status as a normal line."""
        self._stop.set()
        if self._ticker:
            self._ticker.join()
        with self._lock:
            self._clear()
            self.stream.write(self.line() + "\n")
            self.stream.flush()

    def _tick(self) -> None:
        while not self._stop.wait(self.interval):
            self._draw(periodic=True)

    # -- reporting -----------------------------------------------------------

    def log(self, message: str) -> None:
        with self._lock:
            self._clear()
            self.stream.write(message + "\n")
            self._redraw()
            self.stream.flush()

    def add(self, **deltas: int) -> None:
        with self._lock:
            for key, delta in deltas.items():
                self.counts[key] += delta
        if self.live:
            self._draw()

    def line(self) -> str:
        c = self.counts
        elapsed = int(time.monotonic() - self._start)
        parts = [f"{self.phase}: {c['done']}/{self.total} cases", f"{c['active']} active"]
        if c["ordering"]:
            parts.append(f"{c['ordering']} waiting on court orders")
        if c["pdfs"] or c["texts"]:
            parts.append(f"{c['pdfs']} PDFs, {c['texts']} with text")
        if c["failed"]:
            parts.append(f"{c['failed']} failed")
        parts.append(f"{elapsed // 60}m{elapsed % 60:02d}s")
        return "[" + " | ".join(parts) + "]"

    # -- drawing (call with the lock held, except _draw) ------------------------

    def _draw(self, periodic: bool = False) -> None:
        with self._lock:
            if self.live:
                self._clear()
                self._redraw()
            elif periodic:
                self.stream.write(self.line() + "\n")
            self.stream.flush()

    def _clear(self) -> None:
        if self.live and self._shown:
            self.stream.write("\r\033[K")
            self._shown = False

    def _redraw(self) -> None:
        if self.live and self.phase and not self._stop.is_set():
            self.stream.write(self.line())
            self._shown = True
