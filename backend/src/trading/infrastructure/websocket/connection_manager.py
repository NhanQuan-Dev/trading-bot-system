from enum import Enum
from typing import Dict, Set, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class StreamType(str, Enum):
    """Types of WebSocket streams."""
    PRICE = "PRICE"
    ORDERBOOK = "ORDERBOOK"
    TRADES = "TRADES"
    USER_DATA = "USER_DATA"
    BOT_STATUS = "BOT_STATUS"
    BOT_STATS = "BOT_STATS"  # NEW: Real-time bot statistics (P&L, win rate, streaks)
    RISK_ALERTS = "RISK_ALERTS"
    ORDER_UPDATES = "ORDER_UPDATES"
    POSITIONS = "POSITIONS"
    ORDERS = "ORDERS"


class SubscriptionStatus(str, Enum):
    """WebSocket subscription status."""
    PENDING = "PENDING"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    RECONNECTING = "RECONNECTING"


@dataclass
class StreamMessage:
    """WebSocket stream message structure."""
    stream_type: StreamType
    symbol: Optional[str]
    data: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps({
            "stream_type": self.stream_type.value,
            "symbol": self.symbol,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id
        })


@dataclass
class Subscription:
    """WebSocket subscription details."""
    user_id: str
    stream_type: StreamType
    symbol: Optional[str]
    filters: Dict[str, Any]
    status: SubscriptionStatus
    created_at: datetime
    last_update: Optional[datetime] = None
    
    @property
    def subscription_key(self) -> str:
        """Generate unique subscription key."""
        symbol_part = f":{self.symbol}" if self.symbol else ""
        return f"{self.stream_type.value}{symbol_part}"


class ConnectionManager:
    """Manages WebSocket connections and subscriptions."""
    
    def __init__(self):
        # Active connections: connection_id -> websocket
        self.active_connections: Dict[str, Any] = {}
        
        # User subscriptions: user_id -> Set[subscription_key]
        self.user_subscriptions: Dict[str, Set[str]] = {}
        
        # Stream subscriptions: subscription_key -> Set[user_id]
        self.stream_subscriptions: Dict[str, Set[str]] = {}
        
        # Connection to user mapping
        self.connection_users: Dict[str, str] = {}
        
        # User to connections mapping (user can have multiple connections)
        self.user_connections: Dict[str, Set[str]] = {}
    
    def add_connection(self, connection_id: str, websocket: Any, user_id: str):
        """Add a new WebSocket connection."""
        self.active_connections[connection_id] = websocket
        self.connection_users[connection_id] = user_id
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
    
    def remove_connection(self, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id in self.active_connections:
            user_id = self.connection_users.get(connection_id)
            
            # Remove connection
            del self.active_connections[connection_id]
            del self.connection_users[connection_id]
            
            if user_id:
                # Remove from user connections
                if user_id in self.user_connections:
                    self.user_connections[user_id].discard(connection_id)
                    
                    # If user has no more connections, cleanup subscriptions
                    if not self.user_connections[user_id]:
                        self._cleanup_user_subscriptions(user_id)
                        del self.user_connections[user_id]
    
    def add_subscription(self, user_id: str, subscription: Subscription):
        """Add a subscription for a user."""
        subscription_key = subscription.subscription_key
        
        # Add to user subscriptions
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
        self.user_subscriptions[user_id].add(subscription_key)
        
        # Add to stream subscriptions
        if subscription_key not in self.stream_subscriptions:
            self.stream_subscriptions[subscription_key] = set()
        self.stream_subscriptions[subscription_key].add(user_id)
    
    def remove_subscription(self, user_id: str, stream_type: StreamType, symbol: Optional[str] = None):
        """Remove a subscription for a user."""
        symbol_part = f":{symbol}" if symbol else ""
        subscription_key = f"{stream_type.value}{symbol_part}"
        
        # Remove from user subscriptions
        if user_id in self.user_subscriptions:
            self.user_subscriptions[user_id].discard(subscription_key)
        
        # Remove from stream subscriptions
        if subscription_key in self.stream_subscriptions:
            self.stream_subscriptions[subscription_key].discard(user_id)
            
            # Clean up empty stream subscriptions
            if not self.stream_subscriptions[subscription_key]:
                del self.stream_subscriptions[subscription_key]
    
    def _cleanup_user_subscriptions(self, user_id: str):
        """Clean up all subscriptions for a disconnected user."""
        if user_id in self.user_subscriptions:
            for subscription_key in self.user_subscriptions[user_id]:
                if subscription_key in self.stream_subscriptions:
                    self.stream_subscriptions[subscription_key].discard(user_id)
                    if not self.stream_subscriptions[subscription_key]:
                        del self.stream_subscriptions[subscription_key]
            del self.user_subscriptions[user_id]
    
    def get_subscribers(self, stream_type: StreamType, symbol: Optional[str] = None) -> Set[str]:
        """Get all users subscribed to a specific stream."""
        symbol_part = f":{symbol}" if symbol else ""
        subscription_key = f"{stream_type.value}{symbol_part}"
        return self.stream_subscriptions.get(subscription_key, set())
    
    def get_user_connections(self, user_id: str) -> List[Any]:
        """Get all WebSocket connections for a user."""
        connection_ids = self.user_connections.get(user_id, set())
        return [self.active_connections[conn_id] for conn_id in connection_ids 
                if conn_id in self.active_connections]
    
    def broadcast_to_subscribers(self, message: StreamMessage):
        """Broadcast message to all subscribers of a stream."""
        subscribers = self.get_subscribers(message.stream_type, message.symbol)
        
        for user_id in subscribers:
            connections = self.get_user_connections(user_id)
            for websocket in connections:
                try:
                    # This would be an async send in practice
                    # await websocket.send_text(message.to_json())
                    pass
                except Exception:
                    # Handle connection errors
                    pass
    
    def send_to_user(self, user_id: str, message: StreamMessage):
        """Send message to a specific user."""
        connections = self.get_user_connections(user_id)
        for websocket in connections:
            try:
                # This would be an async send in practice
                # await websocket.send_text(message.to_json())
                pass
            except Exception:
                # Handle connection errors
                pass
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.active_connections)
    
    def get_subscription_count(self) -> int:
        """Get total number of active subscriptions."""
        return sum(len(subs) for subs in self.user_subscriptions.values())
    
    async def cleanup(self):
        """Clean up all connections and subscriptions."""
        logger.info("Cleaning up connection manager...")
        
        # Close all active connections
        for connection_id, websocket in list(self.active_connections.items()):
            try:
                await websocket.close()
            except Exception as e:
                logger.error(f"Error closing connection {connection_id}: {e}")
        
        # Clear all data structures
        self.active_connections.clear()
        self.connection_users.clear()
        self.user_connections.clear()
        self.user_subscriptions.clear()
        self.stream_subscriptions.clear()
        
        logger.info("Connection manager cleanup completed")


# Global connection manager instance
connection_manager = ConnectionManager()