from __future__ import annotations

import logging
import queue
import threading
import time
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import requests

if TYPE_CHECKING:
    from beacon_sdk.models import Span

logger = logging.getLogger("beacon_sdk")

HTTP_TIMEOUT_SECONDS: int = 5
DEFAULT_BATCH_SIZE: int = 50
DEFAULT_FLUSH_INTERVAL_MS: int = 1000


@runtime_checkable
class SpanExporter(Protocol):
    def export(self, spans: list[Span]) -> None: ...


@runtime_checkable
class FlushableExporter(Protocol):
    """Extended exporter protocol with lifecycle management."""

    def export(self, spans: list[Span]) -> None: ...
    def flush(self) -> None: ...
    def shutdown(self) -> None: ...


class HttpSpanExporter:
    """Exports spans to the Beacon backend via HTTP POST."""

    def __init__(self, backend_url: str) -> None:
        self._endpoint = f"{backend_url.rstrip('/')}/v1/spans"

    def export(self, spans: list[Span]) -> None:
        payload = {"spans": [span.to_dict() for span in spans]}
        try:
            response = requests.post(
                self._endpoint,
                json=payload,
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.ConnectionError:
            logger.debug(
                "Beacon: backend unreachable at %s (spans dropped)",
                self._endpoint,
            )
        except requests.Timeout:
            logger.debug(
                "Beacon: backend timeout after %ds (spans dropped)",
                HTTP_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.debug("Beacon: failed to export spans: %s", exc)


class AsyncBatchExporter:
    """Batches spans and exports them on a background thread.

    Spans are queued via export() (non-blocking) and flushed to the
    backend either when batch_size is reached or flush_interval_ms
    has elapsed, whichever comes first.
    """

    def __init__(
        self,
        backend_url: str,
        batch_size: int = DEFAULT_BATCH_SIZE,
        flush_interval_ms: int = DEFAULT_FLUSH_INTERVAL_MS,
    ) -> None:
        self._endpoint: str = f"{backend_url.rstrip('/')}/v1/spans"
        self._batch_size: int = batch_size
        self._flush_interval_s: float = flush_interval_ms / 1000.0
        self._queue: queue.Queue[Span] = queue.Queue()
        self._flush_event: threading.Event = threading.Event()
        self._shutdown_flag: bool = False
        self._worker: threading.Thread = threading.Thread(
            target=self._run,
            name="beacon-batch-exporter",
            daemon=True,
        )
        self._worker.start()

    def export(self, spans: list[Span]) -> None:
        """Queue spans for batched export. Non-blocking, thread-safe."""
        if self._shutdown_flag:
            return
        for span in spans:
            self._queue.put(span)
        if self._queue.qsize() >= self._batch_size:
            self._flush_event.set()

    def flush(self) -> None:
        """Force an immediate flush of all queued spans. Blocks until drained."""
        if self._shutdown_flag:
            return
        self._flush_event.set()
        deadline = time.monotonic() + 5.0
        while not self._queue.empty() and time.monotonic() < deadline:
            time.sleep(0.01)

    def shutdown(self) -> None:
        """Flush remaining spans and stop the background thread. Idempotent."""
        if self._shutdown_flag:
            return
        self._shutdown_flag = True
        self._flush_event.set()
        self._worker.join(timeout=10.0)

    def _run(self) -> None:
        """Background worker loop."""
        while not self._shutdown_flag:
            self._flush_event.wait(timeout=self._flush_interval_s)
            self._flush_event.clear()
            self._drain_and_send()
        # Final drain after shutdown signal
        self._drain_and_send()

    def _drain_and_send(self) -> None:
        """Drain the queue and send all spans in one batch."""
        batch: list[Span] = []
        while True:
            try:
                span = self._queue.get_nowait()
                batch.append(span)
            except queue.Empty:
                break
        if not batch:
            return
        self._send_batch(batch)

    def _send_batch(self, batch: list[Span]) -> None:
        """HTTP POST a batch of spans. Silent failure on errors."""
        payload = {"spans": [span.to_dict() for span in batch]}
        try:
            response = requests.post(
                self._endpoint,
                json=payload,
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.ConnectionError:
            logger.debug(
                "Beacon: backend unreachable at %s (%d spans dropped)",
                self._endpoint,
                len(batch),
            )
        except requests.Timeout:
            logger.debug(
                "Beacon: backend timeout after %ds (%d spans dropped)",
                HTTP_TIMEOUT_SECONDS,
                len(batch),
            )
        except Exception as exc:
            logger.debug("Beacon: failed to export %d spans: %s", len(batch), exc)
