"""WebSocket endpoints for real-time monitoring"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to a specific client"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            
            # Handle client requests (e.g., subscribe to specific workflow)
            try:
                message = json.loads(data)
                if message.get("type") == "subscribe":
                    workflow_id = message.get("workflow_id")
                    await manager.send_personal_message({
                        "type": "subscribed",
                        "workflow_id": workflow_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }, websocket)
            except json.JSONDecodeError:
                pass
            
            # Send heartbeat
            await asyncio.sleep(30)  # Send updates every 30 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)


async def broadcast_execution_update(execution_data: Dict[str, Any]) -> None:
    """Broadcast execution update to all connected clients"""
    await manager.broadcast({
        "type": "execution_update",
        "data": execution_data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_agent_health_update(health_data: Dict[str, Any]) -> None:
    """Broadcast agent health update to all connected clients"""
    await manager.broadcast({
        "type": "agent_health_update",
        "data": health_data,
        "timestamp": datetime.utcnow().isoformat()
    })

