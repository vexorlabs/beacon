from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import requests

if TYPE_CHECKING:
    from beacon_sdk.models import Span

logger = logging.getLogger("beacon_sdk")

HTTP_TIMEOUT_SECONDS: int = 5


@runtime_checkable
class SpanExporter(Protocol):
    def export(self, spans: list[Span]) -> None: ...


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
