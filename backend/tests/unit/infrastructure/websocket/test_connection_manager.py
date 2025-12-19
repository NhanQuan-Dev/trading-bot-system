"""Test cases for WebSocket ConnectionManager."""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from src.trading.infrastructure.websocket.connection_manager import (
    ConnectionManager,
    StreamType,
    SubscriptionStatus,
    StreamMessage,
    Subscription
)


class TestStreamType:
    """Test StreamType enum."""

    def test_stream_type_values(self):
        """Test all stream type enum values."""
        assert StreamType.PRICE == "PRICE"
        assert StreamType.ORDERBOOK == "ORDERBOOK"
        assert StreamType.TRADES == "TRADES"
        assert StreamType.USER_DATA == "USER_DATA"
        assert StreamType.BOT_STATUS == "BOT_STATUS"
        assert StreamType.RISK_ALERTS == "RISK_ALERTS"
        assert StreamType.ORDER_UPDATES == "ORDER_UPDATES"


class TestSubscriptionStatus:
    """Test SubscriptionStatus enum."""

    def test_subscription_status_values(self):
        """Test all subscription status enum values."""
        assert SubscriptionStatus.PENDING == "PENDING"
        assert SubscriptionStatus.CONNECTED == "CONNECTED"
        assert SubscriptionStatus.DISCONNECTED == "DISCONNECTED"
        assert SubscriptionStatus.ERROR == "ERROR"
        assert SubscriptionStatus.RECONNECTING == "RECONNECTING"


class TestStreamMessage:
    """Test StreamMessage dataclass."""

    def test_create_stream_message_with_symbol(self):
        """Test creating stream message with symbol."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        message = StreamMessage(
            stream_type=StreamType.PRICE,
            symbol="BTCUSDT",
            data={"price": "50000.00", "volume": "1.5"},
            timestamp=timestamp,
            user_id="user123"
        )
        
        assert message.stream_type == StreamType.PRICE
        assert message.symbol == "BTCUSDT"
        assert message.data == {"price": "50000.00", "volume": "1.5"}
        assert message.timestamp == timestamp
        assert message.user_id == "user123"

    def test_create_stream_message_without_symbol(self):
        """Test creating stream message without symbol."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        message = StreamMessage(
            stream_type=StreamType.RISK_ALERTS,
            symbol=None,
            data={"alert_type": "POSITION_LIMIT_EXCEEDED"},
            timestamp=timestamp
        )
        
        assert message.symbol is None
        assert message.user_id is None

    def test_stream_message_to_json(self):
        """Test converting stream message to JSON."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        message = StreamMessage(
            stream_type=StreamType.PRICE,
            symbol="BTCUSDT",
            data={"price": "50000.00"},
            timestamp=timestamp,
            user_id="user123"
        )
        
        json_str = message.to_json()
        
        assert '"stream_type": "PRICE"' in json_str
        assert '"symbol": "BTCUSDT"' in json_str
        assert '"user_id": "user123"' in json_str
        assert "2024-01-01T12:00:00" in json_str


class TestSubscription:
    """Test Subscription dataclass."""

    def test_create_subscription_with_symbol(self):
        """Test creating subscription with symbol."""
        created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        subscription = Subscription(
            user_id="user123",
            stream_type=StreamType.PRICE,
            symbol="BTCUSDT",
            filters={"interval": "1m"},
            status=SubscriptionStatus.CONNECTED,
            created_at=created_at
        )
        
        assert subscription.user_id == "user123"
        assert subscription.stream_type == StreamType.PRICE
        assert subscription.symbol == "BTCUSDT"
        assert subscription.filters == {"interval": "1m"}
        assert subscription.status == SubscriptionStatus.CONNECTED
        assert subscription.last_update is None

    def test_subscription_key_with_symbol(self):
        """Test subscription key generation with symbol."""
        subscription = Subscription(
            user_id="user123",
            stream_type=StreamType.PRICE,
            symbol="BTCUSDT",
            filters={},
            status=SubscriptionStatus.CONNECTED,
            created_at=datetime.now(timezone.utc)
        )
        
        assert subscription.subscription_key == "PRICE:BTCUSDT"

    def test_subscription_key_without_symbol(self):
        """Test subscription key generation without symbol."""
        subscription = Subscription(
            user_id="user123",
            stream_type=StreamType.RISK_ALERTS,
            symbol=None,
            filters={},
            status=SubscriptionStatus.CONNECTED,
            created_at=datetime.now(timezone.utc)
        )
        
        assert subscription.subscription_key == "RISK_ALERTS"


class TestConnectionManager:
    """Test ConnectionManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager instance for each test."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket object."""
        ws = Mock()
        ws.close = AsyncMock()
        return ws

    def test_initial_state(self, manager):
        """Test ConnectionManager initial state."""
        assert len(manager.active_connections) == 0
        assert len(manager.user_subscriptions) == 0
        assert len(manager.stream_subscriptions) == 0
        assert len(manager.connection_users) == 0
        assert len(manager.user_connections) == 0
        assert manager.get_connection_count() == 0
        assert manager.get_subscription_count() == 0

    def test_add_single_connection(self, manager, mock_websocket):
        """Test adding a single WebSocket connection."""
        connection_id = "conn-1"
        user_id = "user123"
        
        manager.add_connection(connection_id, mock_websocket, user_id)
        
        assert connection_id in manager.active_connections
        assert manager.active_connections[connection_id] == mock_websocket
        assert manager.connection_users[connection_id] == user_id
        assert user_id in manager.user_connections
        assert connection_id in manager.user_connections[user_id]
        assert manager.get_connection_count() == 1

    def test_add_multiple_connections_same_user(self, manager):
        """Test adding multiple connections for the same user."""
        user_id = "user123"
        ws1 = Mock()
        ws2 = Mock()
        
        manager.add_connection("conn-1", ws1, user_id)
        manager.add_connection("conn-2", ws2, user_id)
        
        assert manager.get_connection_count() == 2
        assert len(manager.user_connections[user_id]) == 2
        assert "conn-1" in manager.user_connections[user_id]
        assert "conn-2" in manager.user_connections[user_id]

    def test_add_multiple_connections_different_users(self, manager):
        """Test adding connections for different users."""
        ws1 = Mock()
        ws2 = Mock()
        
        manager.add_connection("conn-1", ws1, "user1")
        manager.add_connection("conn-2", ws2, "user2")
        
        assert manager.get_connection_count() == 2
        assert "user1" in manager.user_connections
        assert "user2" in manager.user_connections
        assert len(manager.user_connections["user1"]) == 1
        assert len(manager.user_connections["user2"]) == 1

    def test_remove_connection(self, manager, mock_websocket):
        """Test removing a WebSocket connection."""
        connection_id = "conn-1"
        user_id = "user123"
        
        manager.add_connection(connection_id, mock_websocket, user_id)
        assert manager.get_connection_count() == 1
        
        manager.remove_connection(connection_id)
        
        assert connection_id not in manager.active_connections
        assert connection_id not in manager.connection_users
        assert user_id not in manager.user_connections
        assert manager.get_connection_count() == 0

    def test_remove_connection_with_remaining_connections(self, manager):
        """Test removing one connection while user has others."""
        user_id = "user123"
        ws1 = Mock()
        ws2 = Mock()
        
        manager.add_connection("conn-1", ws1, user_id)
        manager.add_connection("conn-2", ws2, user_id)
        
        manager.remove_connection("conn-1")
        
        assert manager.get_connection_count() == 1
        assert "conn-1" not in manager.active_connections
        assert "conn-2" in manager.active_connections
        assert user_id in manager.user_connections
        assert "conn-1" not in manager.user_connections[user_id]
        assert "conn-2" in manager.user_connections[user_id]

    def test_add_subscription(self, manager):
        """Test adding a subscription."""
        user_id = "user123"
        subscription = Subscription(
            user_id=user_id,
            stream_type=StreamType.PRICE,
            symbol="BTCUSDT",
            filters={},
            status=SubscriptionStatus.CONNECTED,
            created_at=datetime.now(timezone.utc)
        )
        
        manager.add_subscription(user_id, subscription)
        
        assert user_id in manager.user_subscriptions
        assert "PRICE:BTCUSDT" in manager.user_subscriptions[user_id]
        assert "PRICE:BTCUSDT" in manager.stream_subscriptions
        assert user_id in manager.stream_subscriptions["PRICE:BTCUSDT"]
        assert manager.get_subscription_count() == 1

    def test_add_multiple_subscriptions_same_user(self, manager):
        """Test adding multiple subscriptions for same user."""
        user_id = "user123"
        
        sub1 = Subscription(
            user_id=user_id,
            stream_type=StreamType.PRICE,
            symbol="BTCUSDT",
            filters={},
            status=SubscriptionStatus.CONNECTED,
            created_at=datetime.now(timezone.utc)
        )
        
        sub2 = Subscription(
            user_id=user_id,
            stream_type=StreamType.ORDERBOOK,
            symbol="ETHUSDT",
            filters={},
            status=SubscriptionStatus.CONNECTED,
            created_at=datetime.now(timezone.utc)
        )
        
        manager.add_subscription(user_id, sub1)
        manager.add_subscription(user_id, sub2)
        
        assert len(manager.user_subscriptions[user_id]) == 2
        assert manager.get_subscription_count() == 2

    def test_remove_subscription(self, manager):
        """Test removing a subscription."""
        user_id = "user123"
        subscription = Subscription(
            user_id=user_id,
            stream_type=StreamType.PRICE,
            symbol="BTCUSDT",
            filters={},
            status=SubscriptionStatus.CONNECTED,
            created_at=datetime.now(timezone.utc)
        )
        
        manager.add_subscription(user_id, subscription)
        assert manager.get_subscription_count() == 1
        
        manager.remove_subscription(user_id, StreamType.PRICE, "BTCUSDT")
        
        assert "PRICE:BTCUSDT" not in manager.user_subscriptions.get(user_id, set())
        assert "PRICE:BTCUSDT" not in manager.stream_subscriptions
        assert manager.get_subscription_count() == 0

    def test_get_subscribers_with_symbol(self, manager):
        """Test getting subscribers for a stream with symbol."""
        sub1 = Subscription(
            user_id="user1",
            stream_type=StreamType.PRICE,
            symbol="BTCUSDT",
            filters={},
            status=SubscriptionStatus.CONNECTED,
            created_at=datetime.now(timezone.utc)
        )
        
        sub2 = Subscription(
            user_id="user2",
            stream_type=StreamType.PRICE,
            symbol="BTCUSDT",
            filters={},
            status=SubscriptionStatus.CONNECTED,
            created_at=datetime.now(timezone.utc)
        )
        
        manager.add_subscription("user1", sub1)
        manager.add_subscription("user2", sub2)
        
        subscribers = manager.get_subscribers(StreamType.PRICE, "BTCUSDT")
        
        assert len(subscribers) == 2
        assert "user1" in subscribers
        assert "user2" in subscribers

    def test_get_subscribers_without_symbol(self, manager):
        """Test getting subscribers for a stream without symbol."""
        subscription = Subscription(
            user_id="user1",
            stream_type=StreamType.RISK_ALERTS,
            symbol=None,
            filters={},
            status=SubscriptionStatus.CONNECTED,
            created_at=datetime.now(timezone.utc)
        )
        
        manager.add_subscription("user1", subscription)
        
        subscribers = manager.get_subscribers(StreamType.RISK_ALERTS)
        
        assert len(subscribers) == 1
        assert "user1" in subscribers

    def test_get_user_connections(self, manager):
        """Test getting all connections for a user."""
        user_id = "user123"
        ws1 = Mock()
        ws2 = Mock()
        
        manager.add_connection("conn-1", ws1, user_id)
        manager.add_connection("conn-2", ws2, user_id)
        
        connections = manager.get_user_connections(user_id)
        
        assert len(connections) == 2
        assert ws1 in connections
        assert ws2 in connections

    def test_cleanup_user_subscriptions_on_disconnect(self, manager, mock_websocket):
        """Test that subscriptions are cleaned up when user disconnects."""
        user_id = "user123"
        connection_id = "conn-1"
        
        # Add connection
        manager.add_connection(connection_id, mock_websocket, user_id)
        
        # Add subscription
        subscription = Subscription(
            user_id=user_id,
            stream_type=StreamType.PRICE,
            symbol="BTCUSDT",
            filters={},
            status=SubscriptionStatus.CONNECTED,
            created_at=datetime.now(timezone.utc)
        )
        manager.add_subscription(user_id, subscription)
        
        assert manager.get_subscription_count() == 1
        
        # Remove connection (should cleanup subscriptions)
        manager.remove_connection(connection_id)
        
        assert user_id not in manager.user_subscriptions
        assert "PRICE:BTCUSDT" not in manager.stream_subscriptions
        assert manager.get_subscription_count() == 0

    def test_no_cleanup_when_user_has_remaining_connections(self, manager):
        """Test that subscriptions are not cleaned up when user still has connections."""
        user_id = "user123"
        ws1 = Mock()
        ws2 = Mock()
        
        # Add two connections
        manager.add_connection("conn-1", ws1, user_id)
        manager.add_connection("conn-2", ws2, user_id)
        
        # Add subscription
        subscription = Subscription(
            user_id=user_id,
            stream_type=StreamType.PRICE,
            symbol="BTCUSDT",
            filters={},
            status=SubscriptionStatus.CONNECTED,
            created_at=datetime.now(timezone.utc)
        )
        manager.add_subscription(user_id, subscription)
        
        # Remove one connection
        manager.remove_connection("conn-1")
        
        # Subscriptions should still exist
        assert user_id in manager.user_subscriptions
        assert manager.get_subscription_count() == 1

    @pytest.mark.asyncio
    async def test_cleanup_all_connections(self, manager):
        """Test cleanup of all connections and subscriptions."""
        # Add multiple connections
        ws1 = Mock()
        ws1.close = AsyncMock()
        ws2 = Mock()
        ws2.close = AsyncMock()
        
        manager.add_connection("conn-1", ws1, "user1")
        manager.add_connection("conn-2", ws2, "user2")
        
        # Add subscriptions
        sub1 = Subscription(
            user_id="user1",
            stream_type=StreamType.PRICE,
            symbol="BTCUSDT",
            filters={},
            status=SubscriptionStatus.CONNECTED,
            created_at=datetime.now(timezone.utc)
        )
        manager.add_subscription("user1", sub1)
        
        assert manager.get_connection_count() == 2
        assert manager.get_subscription_count() == 1
        
        # Cleanup all
        await manager.cleanup()
        
        # Verify all websockets were closed
        ws1.close.assert_called_once()
        ws2.close.assert_called_once()
        
        # Verify all data cleared
        assert manager.get_connection_count() == 0
        assert manager.get_subscription_count() == 0
        assert len(manager.active_connections) == 0
        assert len(manager.connection_users) == 0
        assert len(manager.user_connections) == 0
        assert len(manager.user_subscriptions) == 0
        assert len(manager.stream_subscriptions) == 0
