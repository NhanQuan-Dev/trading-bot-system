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
    
    async def connect(self, websocket: WebSocket, user_id: str) -> Optional[str]:
        """
        Accept WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            user_id: Authenticated user ID
            
        Returns:
            connection_id if successful, None if failed
        """
        try:
            # generating connection ID
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
            logger.error(f"WebSocket connection failed: {e}")
            await websocket.close(code=1008, reason="Connection failed")
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
            logger.info(f"WS Message Received [{connection_id}]: {message_type}")
            
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

    async def subscribe_user(self, user_id: str, channels: List[str]):
        """Subscribe user to a list of channels."""
        for channel in channels:
            try:
                stream_type = None
                symbol = None
                
                if ":" in channel:
                    type_str, symbol = channel.split(":", 1)
                    if type_str == "positions":
                        stream_type = StreamType.POSITIONS
                    elif type_str == "orders":
                        stream_type = StreamType.ORDERS
                    elif type_str == "trades":
                        stream_type = StreamType.TRADES
                    elif type_str == "orderbook":
                        stream_type = StreamType.ORDERBOOK
                
                    if stream_type:
                        subscription = Subscription(
                            user_id=user_id,
                            stream_type=stream_type,
                            symbol=symbol,
                            filters={},
                            status=SubscriptionStatus.CONNECTED,
                            created_at=datetime.utcnow()
                        )
                        self.connection_manager.add_subscription(user_id, subscription)
                        logger.info(f"User {user_id} subscribed to {channel} (Parsed: {stream_type}:{symbol})")
            except Exception as e:
                logger.error(f"Error subscribing user {user_id} to {channel}: {e}")

    async def unsubscribe_user(self, user_id: str, channels: List[str]):
        """Unsubscribe user from a list of channels."""
        for channel in channels:
            try:
                if ":" in channel:
                    type_str, symbol = channel.split(":", 1)
                    stream_type = None
                    if type_str == "positions":
                        stream_type = StreamType.POSITIONS
                    elif type_str == "orders":
                        stream_type = StreamType.ORDERS
                    elif type_str == "trades":
                        stream_type = StreamType.TRADES
                    elif type_str == "orderbook":
                        stream_type = StreamType.ORDERBOOK
                    
                    if stream_type:
                        self.connection_manager.remove_subscription(user_id, stream_type, symbol)
                        logger.info(f"User {user_id} unsubscribed from {channel}")
            except Exception as e:
                logger.error(f"Error unsubscribing user {user_id} from {channel}: {e}")

    async def subscribe_to_price_updates(self, user_id: str, symbol: str):
        """Subscribe user to price updates for a symbol."""
        try:
            subscription = Subscription(
                user_id=user_id,
                stream_type=StreamType.PRICE,
                symbol=symbol,
                filters={},
                status=SubscriptionStatus.CONNECTED,
                created_at=datetime.utcnow()
            )
            self.connection_manager.add_subscription(user_id, subscription)
        except Exception as e:
            logger.error(f"Error subscribing user {user_id} to price updates for {symbol}: {e}")

    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]):
        """Broadcast message to a channel."""
        try:
            stream_type = None
            symbol = None
            
            if ":" in channel:
                type_str, symbol = channel.split(":", 1)
                if type_str == "positions":
                    stream_type = StreamType.POSITIONS
                elif type_str == "orders":
                    stream_type = StreamType.ORDERS
            
            if stream_type:
                logger.debug(f"Manager BroadCasting to {stream_type} : {symbol}")
                stream_message = StreamMessage(
                    stream_type=stream_type,
                    symbol=symbol,
                    data=message.get("data", message), # Unwrap 'data' if present, else use whole message
                    timestamp=datetime.utcnow()
                )
                
                # Manual broadcast since ConnectionManager is sync and has stubbed method
                subscribers = self.connection_manager.get_subscribers(stream_type, symbol)
                
                for user_id in subscribers:
                    connections = self.connection_manager.get_user_connections(user_id)
                    for websocket in connections:
                        try:
                            await websocket.send_text(stream_message.to_json())
                        except Exception as e:
                            logger.error(f"Error sending to user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error broadcasting to channel {channel}: {e}")
    
    async def _handle_subscribe(self, connection_id: str, websocket: WebSocket, message: Dict[str, Any]):
        """Handle subscription request."""
        try:
            # Support both "channels" list (new) and single "stream_type"/"symbol" (legacy)
            channels = message.get("channels", [])
            
            # If legacy format
            if not channels and "stream_type" in message:
                stream_type = message.get("stream_type")
                symbol = message.get("symbol")
                if stream_type:
                    channels.append(f"{stream_type}:{symbol}" if symbol else stream_type)

            # Get user ID from connection
            user_id = self.connection_manager.connection_users.get(connection_id)
            if not user_id:
                await self._send_error(websocket, "Invalid connection")
                return

            subscribed_channels = []
            
            for channel in channels:
                try:
                    stream_type = None
                    symbol = None
                    
                    if ":" in channel:
                        type_str, symbol = channel.split(":", 1)
                    else:
                        type_str = channel
                        
                    # Map string type to Enum
                    # We need to map "positions" -> StreamType.POSITIONS
                    # Assuming StreamType values match the string prefixes
                    # Let's check StreamType enum in connection_manager.py
                    # Based on existing code: "positions" -> StreamType.POSITIONS
                    
                    if type_str == "positions":
                        stream_type = StreamType.POSITIONS
                    elif type_str == "orders":
                        stream_type = StreamType.ORDERS
                    elif type_str == "trades":
                        stream_type = StreamType.TRADES
                    elif type_str == "orderbook":
                        stream_type = StreamType.ORDERBOOK
                    elif type_str == "BOT_STATS":
                        stream_type = StreamType.BOT_STATS
                    elif type_str == "BOT_STATUS":
                        stream_type = StreamType.BOT_STATUS
                    elif type_str == "RISK_ALERTS":
                        stream_type = StreamType.RISK_ALERTS
                    # Add other types if needed
                    
                    if stream_type:
                         # Create subscription
                        subscription = Subscription(
                            user_id=user_id,
                            stream_type=stream_type,
                            symbol=symbol,
                            filters=message.get("filters", {}),
                            status=SubscriptionStatus.CONNECTED,
                            created_at=datetime.utcnow()
                        )
                        
                        # Add subscription
                        self.connection_manager.add_subscription(user_id, subscription)
                        subscribed_channels.append(channel)
                        logger.info(f"User {user_id} subscribed to {channel} SUCCESS")
                        
                except Exception as e:
                    logger.error(f"Failed to subscribe to {channel}: {e}")

            # Send confirmation
            await self._send_message(websocket, {
                "type": "subscription",
                "status": "subscribed",
                "channels": subscribed_channels,
                "timestamp": datetime.utcnow().isoformat()
            })
            
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
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.utcnow().isoformat()
    
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
    
    async def broadcast_bot_stats_update(self, user_id: str, bot_id: str, stats: Dict[str, Any]):
        """
        Broadcast bot statistics update to specific user.
        
        Called when a trade closes and bot stats are updated.
        Stats dict should contain: total_pnl, win_rate, total_trades, 
        winning_trades, losing_trades, and streak counters.
        """
        message = StreamMessage(
            stream_type=StreamType.BOT_STATS,
            symbol=None,  # Bot stats are not symbol-specific
            data={
                "bot_id": bot_id,
                **stats
            },
            timestamp=datetime.utcnow(),
            user_id=user_id
        )
        
        # Send to user's connections
        connections = self.connection_manager.get_user_connections(user_id)
        for websocket in connections:
            try:
                await websocket.send_text(message.to_json())
            except Exception as e:
                logger.error(f"Error sending bot stats to user {user_id}: {e}")
    
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