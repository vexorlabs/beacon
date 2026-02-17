from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and trace-level subscriptions.

    Clients start in ``active_connections`` (receive all events).
    On ``subscribe_trace``, they move to ``trace_subscriptions`` (filtered).
    On ``unsubscribe_trace``, they move back to ``active_connections``.
    """

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self.trace_subscriptions: dict[str, set[WebSocket]] = {}

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active_connections.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active_connections.discard(ws)
        for sockets in self.trace_subscriptions.values():
            sockets.discard(ws)

    async def broadcast_span(self, span_dict: dict[str, Any]) -> None:
        """Send span_created to unsubscribed clients + clients watching this trace."""
        trace_id = span_dict.get("trace_id", "")
        targets = self._targets_for_trace(trace_id)
        await self._send_to(
            targets, {"event": "span_created", "span": span_dict}
        )

    async def broadcast_span_updated(
        self,
        span_id: str,
        trace_id: str,
        updates: dict[str, Any],
    ) -> None:
        """Send span_updated to relevant clients."""
        targets = self._targets_for_trace(trace_id)
        await self._send_to(
            targets,
            {"event": "span_updated", "span_id": span_id, "updates": updates},
        )

    async def broadcast_trace_created(
        self, trace_dict: dict[str, Any]
    ) -> None:
        """Send trace_created to all unfiltered clients."""
        await self._send_to(
            set(self.active_connections),
            {"event": "trace_created", "trace": trace_dict},
        )

    def _targets_for_trace(self, trace_id: str) -> set[WebSocket]:
        """Return unsubscribed clients + clients subscribed to this trace."""
        return set(self.active_connections) | self.trace_subscriptions.get(
            trace_id, set()
        )

    async def _send_to(
        self, targets: set[WebSocket], payload: dict[str, Any]
    ) -> None:
        for ws in list(targets):
            try:
                await ws.send_json(payload)
            except Exception:
                logger.debug(
                    "WebSocket send failed, disconnecting client",
                    exc_info=True,
                )
                self.disconnect(ws)


ws_manager = ConnectionManager()

ws_router = APIRouter()


@ws_router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except ValueError:
                await websocket.send_json({"error": "Invalid JSON"})
                continue
            action = data.get("action")
            if action == "subscribe_trace":
                trace_id = data.get("trace_id")
                if trace_id:
                    ws_manager.active_connections.discard(websocket)
                    ws_manager.trace_subscriptions.setdefault(
                        trace_id, set()
                    ).add(websocket)
            elif action == "unsubscribe_trace":
                trace_id = data.get("trace_id")
                if trace_id and trace_id in ws_manager.trace_subscriptions:
                    ws_manager.trace_subscriptions[trace_id].discard(
                        websocket
                    )
                    ws_manager.active_connections.add(websocket)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
