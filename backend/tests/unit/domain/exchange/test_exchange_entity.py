"""Unit tests for ExchangeConnection entity."""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from src.trading.domain.exchange import (
    ExchangeConnection,
    ExchangeType,
    ConnectionStatus,
    APICredentials,
    ExchangePermissions,
)


class TestExchangeConnection:
    """Test ExchangeConnection entity."""
    
    def test_create_exchange_connection(self):
        """Test creating exchange connection with factory method."""
        user_id = uuid4()
        credentials = APICredentials(
            api_key="encrypted_key",
            secret_key="encrypted_secret"
        )
        permissions = ExchangePermissions(spot_trade=True)
        
        connection = ExchangeConnection.create(
            user_id=user_id,
            exchange_type=ExchangeType.BINANCE,
            name="My Binance Connection",
            credentials=credentials,
            permissions=permissions,
            is_testnet=True,
        )
        
        assert connection.id is not None
        assert connection.user_id == user_id
        assert connection.exchange_type == ExchangeType.BINANCE
        assert connection.name == "My Binance Connection"
        assert connection.credentials == credentials
        assert connection.permissions == permissions
        assert connection.is_testnet is True
        assert connection.is_active is True
        assert connection.status == ConnectionStatus.DISCONNECTED
        assert connection.created_at is not None
    
    def test_create_connection_mainnet(self):
        """Test creating mainnet connection."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Mainnet Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(futures_trade=True),
            is_testnet=False,
        )
        
        assert connection.is_testnet is False
    
    def test_activate_connection(self):
        """Test activating connection."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Test Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(spot_trade=True),
        )
        
        # Deactivate first
        connection.deactivate()
        assert connection.is_active is False
        
        # Then activate
        connection.activate()
        assert connection.is_active is True
    
    def test_deactivate_connection(self):
        """Test deactivating connection."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Test Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(spot_trade=True),
        )
        
        connection.deactivate()
        
        assert connection.is_active is False
        assert connection.status == ConnectionStatus.DISCONNECTED
    
    def test_mark_connected(self):
        """Test marking connection as connected."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Test Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(spot_trade=True),
        )
        
        connection.mark_connected()
        
        assert connection.status == ConnectionStatus.CONNECTED
        assert connection.last_used_at is not None
    
    def test_mark_connected_inactive_connection_fails(self):
        """Test that inactive connection cannot be marked as connected."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Test Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(spot_trade=True),
        )
        
        connection.deactivate()
        
        with pytest.raises(ValueError, match="Cannot connect inactive connection"):
            connection.mark_connected()
    
    def test_mark_disconnected(self):
        """Test marking connection as disconnected."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Test Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(spot_trade=True),
        )
        
        connection.mark_connected()
        assert connection.status == ConnectionStatus.CONNECTED
        
        connection.mark_disconnected()
        assert connection.status == ConnectionStatus.DISCONNECTED
    
    def test_mark_error(self):
        """Test marking connection as error."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Test Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(spot_trade=True),
        )
        
        connection.mark_error()
        
        assert connection.status == ConnectionStatus.ERROR
    
    def test_mark_connecting(self):
        """Test marking connection as connecting."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Test Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(spot_trade=True),
        )
        
        connection.mark_connecting()
        
        assert connection.status == ConnectionStatus.CONNECTING
    
    def test_mark_connecting_inactive_connection_fails(self):
        """Test that inactive connection cannot be marked as connecting."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Test Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(spot_trade=True),
        )
        
        connection.deactivate()
        
        with pytest.raises(ValueError, match="Cannot connect inactive connection"):
            connection.mark_connecting()
    
    def test_update_last_used(self):
        """Test updating last used timestamp."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Test Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(spot_trade=True),
        )
        
        assert connection.last_used_at is None
        
        connection.update_last_used()
        
        assert connection.last_used_at is not None
    
    def test_can_trade_when_active_and_connected(self):
        """Test that active and connected connection with permissions can trade."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Test Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(spot_trade=True),
        )
        
        connection.mark_connected()
        
        assert connection.can_trade() is True
    
    def test_cannot_trade_when_disconnected(self):
        """Test that disconnected connection cannot trade."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Test Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(spot_trade=True),
        )
        
        # Disconnected by default
        assert connection.can_trade() is False
    
    def test_cannot_trade_when_inactive(self):
        """Test that inactive connection cannot trade."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Test Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(spot_trade=True),
        )
        
        connection.deactivate()
        
        assert connection.can_trade() is False
    
    def test_cannot_trade_without_permissions(self):
        """Test that connection without trade permissions cannot trade."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Test Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(read_only=True),  # No trade permissions
        )
        
        connection.mark_connected()
        
        assert connection.can_trade() is False
    
    def test_connection_string_representation(self):
        """Test connection string representation."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="My Connection",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(spot_trade=True),
        )
        
        repr_str = repr(connection)
        assert "ExchangeConnection" in repr_str
        assert "BINANCE" in repr_str
        assert "My Connection" in repr_str
        assert connection.status.value in repr_str
    
    def test_connection_lifecycle(self):
        """Test complete connection lifecycle."""
        connection = ExchangeConnection.create(
            user_id=uuid4(),
            exchange_type=ExchangeType.BINANCE,
            name="Lifecycle Test",
            credentials=APICredentials(api_key="key", secret_key="secret"),
            permissions=ExchangePermissions(futures_trade=True),
        )
        
        # Initial state
        assert connection.is_active is True
        assert connection.status == ConnectionStatus.DISCONNECTED
        assert connection.can_trade() is False
        
        # Connecting
        connection.mark_connecting()
        assert connection.status == ConnectionStatus.CONNECTING
        
        # Connected
        connection.mark_connected()
        assert connection.status == ConnectionStatus.CONNECTED
        assert connection.can_trade() is True
        
        # Use it
        connection.update_last_used()
        assert connection.last_used_at is not None
        
        # Error occurred
        connection.mark_error()
        assert connection.status == ConnectionStatus.ERROR
        assert connection.can_trade() is False
        
        # Reconnect
        connection.mark_connecting()
        connection.mark_connected()
        assert connection.can_trade() is True
        
        # Deactivate
        connection.deactivate()
        assert connection.is_active is False
        assert connection.status == ConnectionStatus.DISCONNECTED
        assert connection.can_trade() is False
