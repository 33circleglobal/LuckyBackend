import json
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self._price_clients: list[WebSocket] = []  # ws1 — price stream
        self._game_clients: list[WebSocket] = []  # ws2 — game events

    # ── connections ──

    def add_price_client(self, ws: WebSocket):
        self._price_clients.append(ws)

    def remove_price_client(self, ws: WebSocket):
        (
            self._price_clients.discard(ws)
            if hasattr(self._price_clients, "discard")
            else self._price_clients.remove(ws) if ws in self._price_clients else None
        )

    def add_game_client(self, ws: WebSocket):
        self._game_clients.append(ws)

    def remove_game_client(self, ws: WebSocket):
        if ws in self._game_clients:
            self._game_clients.remove(ws)

    # ── broadcasting ──

    async def _broadcast(self, clients: list[WebSocket], payload: dict):
        message = json.dumps(payload)
        dead = []
        for client in clients:
            try:
                await client.send_text(message)
            except Exception:
                dead.append(client)
        for client in dead:
            if client in clients:
                clients.remove(client)

    async def broadcast_price(self, payload: dict):
        await self._broadcast(self._price_clients, payload)

    async def broadcast_game(self, payload: dict):
        await self._broadcast(self._game_clients, payload)

    # ── targeted send ──

    async def send_to(self, ws: WebSocket, payload: dict):
        try:
            await ws.send_text(json.dumps(payload))
        except Exception as e:
            logger.warning(f"[WS] send_to failed: {e}")


# Singleton
ws_manager = WebSocketManager()
