"""
FastAPI service for backtest management with WebSocket support.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4
import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from kafka import KafkaProducer
import redis
from celery import Celery

# Models
class TimeFrame(str, Enum):
    """Trading timeframes"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    
class MAStrategy(BaseModel):
    """Moving Average Strategy Parameters"""
    symbol: str
    start_date: datetime
    end_date: datetime
    timeframe: TimeFrame
    fast_ma: int = Field(default=20, gt=0)
    slow_ma: int = Field(default=50, gt=0)
    initial_capital: float = Field(default=100000.0, gt=0)
    
class BacktestStatus(str, Enum):
    """Backtest execution status"""
    PENDING = "pending"
    FETCHING_DATA = "fetching_data"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    
class BacktestRequest(BaseModel):
    """Backtest request model"""
    strategy: MAStrategy
    request_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
class BacktestResult(BaseModel):
    """Backtest result model"""
    request_id: UUID
    status: BacktestStatus
    metrics: Optional[Dict] = None
    trades: Optional[List[Dict]] = None
    equity_curve: Optional[List[Dict]] = None
    error: Optional[str] = None

# WebSocket connection manager
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

# Initialize components
app = FastAPI(title="Backtest Service")
manager = ConnectionManager()

# Configure Kafka producer
kafka_producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Configure Redis
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)

# Configure Celery
celery_app = Celery(
    'backtest_tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# API Routes
@app.post("/api/backtest", response_model=BacktestResult)
async def create_backtest(request: BacktestRequest):
    """Create a new backtest"""
    try:
        # Store request in Redis
        redis_client.set(
            f"backtest:{request.request_id}",
            request.json(),
            ex=3600  # 1 hour expiry
        )
        
        # Publish to Kafka
        kafka_producer.send(
            'backtest_requests',
            value={
                'request_id': str(request.request_id),
                'strategy': request.strategy.dict()
            }
        )
        
        # Create initial result
        result = BacktestResult(
            request_id=request.request_id,
            status=BacktestStatus.PENDING
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create backtest: {str(e)}"
        )
        
@app.get("/api/backtest/{backtest_id}", response_model=BacktestResult)
async def get_backtest_status(backtest_id: UUID):
    """Get backtest status"""
    try:
        result = redis_client.get(f"backtest_result:{backtest_id}")
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Backtest not found"
            )
            
        return BacktestResult.parse_raw(result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get backtest status: {str(e)}"
        )
        
@app.websocket("/ws/backtest/{backtest_id}")
async def websocket_endpoint(websocket: WebSocket, backtest_id: UUID):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket, backtest_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, backtest_id)
        
# Celery task for handling backtest updates
@celery_app.task
def process_backtest_result(backtest_id: str, result: dict):
    """Process and store backtest result"""
    try:
        # Store in Redis for quick access
        redis_client.set(
            f"backtest_result:{backtest_id}",
            json.dumps(result),
            ex=3600  # 1 hour expiry
        )
        
        # TODO: Store in ClickHouse for permanent storage
        
    except Exception as e:
        print(f"Error processing backtest result: {str(e)}")
        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
