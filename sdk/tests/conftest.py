from __future__ import annotations

import pytest

from beacon_sdk.models import Span
from beacon_sdk.tracer import BeaconTracer


class InMemoryExporter:
    """Captures exported spans in memory for test assertions."""

    def __init__(self) -> None:
        self.spans: list[Span] = []

    def export(self, spans: list[Span]) -> None:
        self.spans.extend(spans)


@pytest.fixture()
def exporter() -> InMemoryExporter:
    return InMemoryExporter()


@pytest.fixture()
def tracer(exporter: InMemoryExporter) -> BeaconTracer:
    return BeaconTracer(exporter=exporter, enabled=True)  # type: ignore[arg-type]
