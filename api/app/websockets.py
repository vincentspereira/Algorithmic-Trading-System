
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import WebSocket
import structlog

logger = structlog.get_logger()

class ConnectionManager:
    """WebSocket connection manager for real-time data streaming"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.symbol_subscriptions: Dict[str, List[WebSocket]] = {}
        self.client_info: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_info[websocket] = {
            "client_id": client_id,
            "connected_at": datetime.now(timezone.utc),
            "subscriptions": []
        }
        logger.info("WebSocket connected", client_id=client_id, total_connections=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

            # Remove from symbol subscriptions
            client_info = self.client_info.get(websocket, {})
            for symbol in client_info.get("subscriptions", []):
                if symbol in self.symbol_subscriptions:
                    if websocket in self.symbol_subscriptions[symbol]:
                        self.symbol_subscriptions[symbol].remove(websocket)

            if websocket in self.client_info:
                del self.client_info[websocket]

            logger.info("WebSocket disconnected", total_connections=len(self.active_connections))

    async def subscribe_symbol(self, websocket: WebSocket, symbol: str):
        """Subscribe client to symbol updates"""
        if symbol not in self.symbol_subscriptions:
            self.symbol_subscriptions[symbol] = []

        if websocket not in self.symbol_subscriptions[symbol]:
            self.symbol_subscriptions[symbol].append(websocket)

            if websocket in self.client_info:
                self.client_info[websocket]["subscriptions"].append(symbol)

        logger.info("Symbol subscription added", symbol=symbol,
                   subscribers=len(self.symbol_subscriptions[symbol]))

    async def broadcast_to_symbol(self, symbol: str, message: dict):
        """Broadcast message to all subscribers of a symbol"""
        if symbol in self.symbol_subscriptions:
            disconnected = []
            for websocket in self.symbol_subscriptions[symbol]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error("Failed to send message", symbol=symbol, error=str(e))
                    disconnected.append(websocket)

            # Clean up disconnected clients
            for websocket in disconnected:
                self.disconnect(websocket)

    async def broadcast_all(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error("Failed to broadcast message", error=str(e))
                disconnected.append(websocket)

        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)
