from __future__ import annotations

from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


class ConnectionManager:
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
        """Broadcast a span event to all connections watching this trace."""
        trace_id = span_dict.get("trace_id", "")
        targets = (
            self.trace_subscriptions.get(trace_id, set())
            | self.active_connections
        )
        for ws in list(targets):
            try:
                await ws.send_json(
                    {"event": "span_created", "span": span_dict}
                )
            except Exception:
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
                    ws_manager.trace_subscriptions.setdefault(
                        trace_id, set()
                    ).add(websocket)
            elif action == "unsubscribe_trace":
                trace_id = data.get("trace_id")
                if trace_id and trace_id in ws_manager.trace_subscriptions:
                    ws_manager.trace_subscriptions[trace_id].discard(
                        websocket
                    )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
