from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Any
import json
import asyncio
import logging
import uuid
from datetime import datetime

from .connection_manager import ConnectionManager, StreamMessage, StreamType, Subscription, SubscriptionStatus
from ..auth import verify_access_token
from ..cache import cache_service, price_cache, user_session_cache

logger = logging.getLogger(__name__)


class WebSocketManager:
    """High-level WebSocket manager for real-time features."""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.cache = cache_service
        self.price_cache = price_cache
        self.session_cache = user_session_cache
    
    async def connect(self, websocket: WebSocket, token: str) -> Optional[str]:
        """
        Accept WebSocket connection and authenticate user.
        
        Returns:
            connection_id if successful, None if authentication failed
        """
        try:
            # Authenticate user from token
            user_id = verify_access_token(token)
            
            # Accept connection
            await websocket.accept()
            
            # Generate connection ID
            connection_id = str(uuid.uuid4())
            
            # Register connection
            self.connection_manager.add_connection(connection_id, websocket, str(user_id))
            
            logger.info(f"WebSocket connected: {connection_id} for user {user_id}")
            
            # Send connection confirmation
            await self._send_message(websocket, {
                "type": "connection",
                "status": "connected",
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return connection_id
            
        except Exception as e:
            logger.error(f"WebSocket authentication failed: {e}")
            await websocket.close(code=1008, reason="Authentication failed")
            return None
    
    async def disconnect(self, connection_id: str):
        """Handle WebSocket disconnection."""
        try:
            self.connection_manager.remove_connection(connection_id)
            
            # Cancel any active tasks for this connection
            if connection_id in self.active_tasks:
                self.active_tasks[connection_id].cancel()
                del self.active_tasks[connection_id]
            
            logger.info(f"WebSocket disconnected: {connection_id}")
            
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {e}")
    
    async def handle_message(self, connection_id: str, websocket: WebSocket, message: Dict[str, Any]):
        """Handle incoming WebSocket message."""
        try:
            message_type = message.get("type")
            
            if message_type == "subscribe":
                await self._handle_subscribe(connection_id, websocket, message)
            elif message_type == "unsubscribe":
                await self._handle_unsubscribe(connection_id, websocket, message)
            elif message_type == "ping":
                await self._handle_ping(websocket)
            else:
                await self._send_error(websocket, f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self._send_error(websocket, "Invalid message format")
    
    async def _handle_subscribe(self, connection_id: str, websocket: WebSocket, message: Dict[str, Any]):
        """Handle subscription request."""
        try:
            stream_type = StreamType(message.get("stream_type"))
            symbol = message.get("symbol")
            filters = message.get("filters", {})
            
            # Get user ID from connection
            user_id = self.connection_manager.connection_users.get(connection_id)
            if not user_id:
                await self._send_error(websocket, "Invalid connection")
                return
            
            # Create subscription
            subscription = Subscription(
                user_id=user_id,
                stream_type=stream_type,
                symbol=symbol,
                filters=filters,
                status=SubscriptionStatus.CONNECTED,
                created_at=datetime.utcnow()
            )
            
            # Add subscription
            self.connection_manager.add_subscription(user_id, subscription)
            
            # Send confirmation
            await self._send_message(websocket, {
                "type": "subscription",
                "status": "subscribed",
                "stream_type": stream_type.value,
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"User {user_id} subscribed to {stream_type.value}:{symbol}")
            
        except ValueError as e:
            await self._send_error(websocket, f"Invalid stream type: {e}")
        except Exception as e:
            logger.error(f"Subscription error: {e}")
            await self._send_error(websocket, "Subscription failed")
    
    async def _handle_unsubscribe(self, connection_id: str, websocket: WebSocket, message: Dict[str, Any]):
        """Handle unsubscription request."""
        try:
            stream_type = StreamType(message.get("stream_type"))
            symbol = message.get("symbol")
            
            # Get user ID from connection
            user_id = self.connection_manager.connection_users.get(connection_id)
            if not user_id:
                await self._send_error(websocket, "Invalid connection")
                return
            
            # Remove subscription
            self.connection_manager.remove_subscription(user_id, stream_type, symbol)
            
            # Send confirmation
            await self._send_message(websocket, {
                "type": "subscription",
                "status": "unsubscribed",
                "stream_type": stream_type.value,
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"User {user_id} unsubscribed from {stream_type.value}:{symbol}")
            
        except ValueError as e:
            await self._send_error(websocket, f"Invalid stream type: {e}")
        except Exception as e:
            logger.error(f"Unsubscription error: {e}")
            await self._send_error(websocket, "Unsubscription failed")
    
    async def _handle_ping(self, websocket: WebSocket):
        """Handle ping message."""
        await self._send_message(websocket, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def _send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to WebSocket."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
    
    async def _send_error(self, websocket: WebSocket, error: str):
        """Send error message to WebSocket."""
        await self._send_message(websocket, {
            "type": "error",
            "message": error,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def broadcast_price_update(self, symbol: str, price_data: Dict[str, Any]):
        """Broadcast price update to subscribers."""
        message = StreamMessage(
            stream_type=StreamType.PRICE,
            symbol=symbol,
            data=price_data,
            timestamp=datetime.utcnow()
        )
        
        # Get subscribers for this symbol
        subscribers = self.connection_manager.get_subscribers(StreamType.PRICE, symbol)
        
        # Send to all subscribers
        for user_id in subscribers:
            connections = self.connection_manager.get_user_connections(user_id)
            for websocket in connections:
                try:
                    await websocket.send_text(message.to_json())
                except Exception as e:
                    logger.error(f"Error broadcasting price to user {user_id}: {e}")
    
    async def broadcast_order_update(self, user_id: str, order_data: Dict[str, Any]):
        """Broadcast order update to specific user."""
        message = StreamMessage(
            stream_type=StreamType.ORDER_UPDATES,
            symbol=order_data.get("symbol"),
            data=order_data,
            timestamp=datetime.utcnow(),
            user_id=user_id
        )
        
        # Send to user's connections
        connections = self.connection_manager.get_user_connections(user_id)
        for websocket in connections:
            try:
                await websocket.send_text(message.to_json())
            except Exception as e:
                logger.error(f"Error sending order update to user {user_id}: {e}")
    
    async def broadcast_risk_alert(self, user_id: str, alert_data: Dict[str, Any]):
        """Broadcast risk alert to specific user."""
        message = StreamMessage(
            stream_type=StreamType.RISK_ALERTS,
            symbol=alert_data.get("symbol"),
            data=alert_data,
            timestamp=datetime.utcnow(),
            user_id=user_id
        )
        
        # Send to user's connections
        connections = self.connection_manager.get_user_connections(user_id)
        for websocket in connections:
            try:
                await websocket.send_text(message.to_json())
            except Exception as e:
                logger.error(f"Error sending risk alert to user {user_id}: {e}")
    
    async def broadcast_bot_status_update(self, user_id: str, bot_data: Dict[str, Any]):
        """Broadcast bot status update to specific user."""
        message = StreamMessage(
            stream_type=StreamType.BOT_STATUS,
            symbol=bot_data.get("symbol"),
            data=bot_data,
            timestamp=datetime.utcnow(),
            user_id=user_id
        )
        
        # Send to user's connections
        connections = self.connection_manager.get_user_connections(user_id)
        for websocket in connections:
            try:
                await websocket.send_text(message.to_json())
            except Exception as e:
                logger.error(f"Error sending bot status to user {user_id}: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get WebSocket statistics."""
        return {
            "total_connections": self.connection_manager.get_connection_count(),
            "total_subscriptions": self.connection_manager.get_subscription_count(),
            "active_users": len(self.connection_manager.user_connections),
            "active_streams": len(self.connection_manager.stream_subscriptions)
        }
    
    async def initialize(self):
        """Initialize the WebSocket manager."""
        logger.info("WebSocket manager initialized")
        # Add any initialization logic here if needed
    
    async def cleanup(self):
        """Clean up the WebSocket manager."""
        logger.info("Cleaning up WebSocket manager...")
        
        # Use connection manager's cleanup
        await self.connection_manager.cleanup()
        
        logger.info("WebSocket manager cleanup completed")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()