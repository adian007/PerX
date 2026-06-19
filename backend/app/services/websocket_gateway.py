"""In-memory WebSocket connection registry for hackathon realtime events."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketGateway:
    """Broadcast JSON events to connected employee or employer clients."""

    def __init__(self) -> None:
        self._employee_connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._employer_connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect_employee(self, employee_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._employee_connections[employee_id].add(websocket)

    async def connect_employer(self, employer_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._employer_connections[employer_id].add(websocket)

    def disconnect_employee(self, employee_id: str, websocket: WebSocket) -> None:
        connections = self._employee_connections.get(employee_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            del self._employee_connections[employee_id]

    def disconnect_employer(self, employer_id: str, websocket: WebSocket) -> None:
        connections = self._employer_connections.get(employer_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            del self._employer_connections[employer_id]

    async def _broadcast(self, connections: set[WebSocket], event: str, payload: dict[str, Any]) -> None:
        message = json.dumps({"event": event, "data": payload})
        stale: list[WebSocket] = []
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception as exc:  # noqa: BLE001 — drop broken sockets
                logger.debug("WebSocket send failed: %s", exc)
                stale.append(websocket)
        for websocket in stale:
            connections.discard(websocket)

    async def broadcast_to_employee(
        self,
        employee_id: str,
        event: str,
        payload: dict[str, Any],
    ) -> None:
        connections = self._employee_connections.get(employee_id)
        if not connections:
            return
        await self._broadcast(connections, event, payload)

    async def broadcast_to_employer(
        self,
        employer_id: str,
        event: str,
        payload: dict[str, Any],
    ) -> None:
        connections = self._employer_connections.get(employer_id)
        if not connections:
            return
        await self._broadcast(connections, event, payload)


_gateway = WebSocketGateway()


def get_websocket_gateway() -> WebSocketGateway:
    """Return the process-wide WebSocket gateway singleton."""

    return _gateway
