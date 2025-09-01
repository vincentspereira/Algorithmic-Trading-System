
from typing import Dict, List
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[UUID, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, backtest_id: UUID):
        """Connect a client"""
        await websocket.accept()
        if backtest_id not in self.active_connections:
            self.active_connections[backtest_id] = []
        self.active_connections[backtest_id].append(websocket)

    def disconnect(self, websocket: WebSocket, backtest_id: UUID):
        """Disconnect a client"""
        if backtest_id in self.active_connections:
            self.active_connections[backtest_id].remove(websocket)
            if not self.active_connections[backtest_id]:
                del self.active_connections[backtest_id]

    async def broadcast_update(self, backtest_id: UUID, message: dict):
        """Broadcast update to all connected clients"""
        if backtest_id in self.active_connections:
            for connection in self.active_connections[backtest_id]:
                try:
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    self.disconnect(connection, backtest_id)
