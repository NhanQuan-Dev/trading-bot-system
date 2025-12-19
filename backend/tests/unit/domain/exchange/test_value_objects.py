"""Unit tests for Exchange domain value objects."""

import pytest
from uuid import uuid4

from src.trading.domain.exchange import (
    ExchangeType,
    ConnectionStatus,
    APICredentials,
    ExchangePermissions,
)


class TestExchangeType:
    """Test ExchangeType enum."""
    
    def test_exchange_types(self):
        """Test all supported exchange types."""
        assert ExchangeType.BINANCE == "BINANCE"
        assert ExchangeType.BYBIT == "BYBIT"
        assert ExchangeType.OKX == "OKX"
    
    def test_exchange_type_as_string(self):
        """Test exchange type string conversion."""
        # Enum str() includes class name, use .value for plain string
        assert ExchangeType.BINANCE.value == "BINANCE"


class TestConnectionStatus:
    """Test ConnectionStatus enum."""
    
    def test_connection_statuses(self):
        """Test all connection statuses."""
        assert ConnectionStatus.CONNECTED == "CONNECTED"
        assert ConnectionStatus.DISCONNECTED == "DISCONNECTED"
        assert ConnectionStatus.CONNECTING == "CONNECTING"
        assert ConnectionStatus.ERROR == "ERROR"


class TestAPICredentials:
    """Test APICredentials value object."""
    
    def test_create_credentials_basic(self):
        """Test creating basic API credentials."""
        credentials = APICredentials(
            api_key="test_api_key_encrypted",
            secret_key="test_secret_key_encrypted"
        )
        
        assert credentials.api_key == "test_api_key_encrypted"
        assert credentials.secret_key == "test_secret_key_encrypted"
        assert credentials.passphrase is None
    
    def test_create_credentials_with_passphrase(self):
        """Test creating credentials with passphrase."""
        credentials = APICredentials(
            api_key="test_api_key",
            secret_key="test_secret_key",
            passphrase="test_passphrase"
        )
        
        assert credentials.passphrase == "test_passphrase"
    
    def test_credentials_immutable(self):
        """Test that credentials are immutable (frozen dataclass)."""
        credentials = APICredentials(
            api_key="test_api_key",
            secret_key="test_secret_key"
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            credentials.api_key = "new_key"
    
    def test_credentials_string_representation_masks_secrets(self):
        """Test that string representation masks sensitive data."""
        credentials = APICredentials(
            api_key="test_api_key_12345678",
            secret_key="test_secret_key_encrypted"
        )
        
        str_repr = str(credentials)
        assert "5678" in str_repr  # Last 4 chars shown
        assert "test_api_key_12345678" not in str_repr  # Full key not shown
        assert "***" in str_repr  # Masked
    
    def test_credentials_equality(self):
        """Test credentials equality."""
        creds1 = APICredentials(
            api_key="key1",
            secret_key="secret1"
        )
        creds2 = APICredentials(
            api_key="key1",
            secret_key="secret1"
        )
        creds3 = APICredentials(
            api_key="key2",
            secret_key="secret2"
        )
        
        assert creds1 == creds2
        assert creds1 != creds3


class TestExchangePermissions:
    """Test ExchangePermissions value object."""
    
    def test_default_permissions(self):
        """Test default permissions are all False."""
        perms = ExchangePermissions()
        
        assert perms.spot_trade is False
        assert perms.futures_trade is False
        assert perms.margin_trade is False
        assert perms.read_only is False
        assert perms.withdraw is False
    
    def test_spot_trading_permissions(self):
        """Test spot trading permissions."""
        perms = ExchangePermissions(spot_trade=True)
        
        assert perms.spot_trade is True
        assert perms.can_trade() is True
        assert perms.is_safe() is True  # No withdraw
    
    def test_futures_trading_permissions(self):
        """Test futures trading permissions."""
        perms = ExchangePermissions(futures_trade=True)
        
        assert perms.futures_trade is True
        assert perms.can_trade() is True
    
    def test_read_only_cannot_trade(self):
        """Test that read-only permissions prevent trading."""
        perms = ExchangePermissions(
            spot_trade=True,
            read_only=True
        )
        
        assert perms.can_trade() is False
    
    def test_withdraw_permissions_not_safe(self):
        """Test that withdraw permissions are marked as not safe."""
        perms = ExchangePermissions(
            spot_trade=True,
            withdraw=True
        )
        
        assert perms.is_safe() is False
        assert perms.withdraw is True
    
    def test_multiple_trading_permissions(self):
        """Test multiple trading permissions."""
        perms = ExchangePermissions(
            spot_trade=True,
            futures_trade=True,
            margin_trade=True
        )
        
        assert perms.can_trade() is True
    
    def test_permissions_without_trading_rights(self):
        """Test permissions without any trading rights."""
        perms = ExchangePermissions(read_only=True)
        
        assert perms.can_trade() is False
    
    def test_permissions_immutable(self):
        """Test that permissions are immutable."""
        perms = ExchangePermissions(spot_trade=True)
        
        with pytest.raises(Exception):  # FrozenInstanceError
            perms.spot_trade = False
    
    def test_safe_trading_configuration(self):
        """Test safe trading configuration (no withdraw)."""
        perms = ExchangePermissions(
            spot_trade=True,
            futures_trade=True,
            withdraw=False
        )
        
        assert perms.can_trade() is True
        assert perms.is_safe() is True
    
    def test_unsafe_configuration(self):
        """Test unsafe configuration (with withdraw)."""
        perms = ExchangePermissions(
            spot_trade=True,
            withdraw=True
        )
        
        assert perms.is_safe() is False
