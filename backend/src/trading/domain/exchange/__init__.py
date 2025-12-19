"""Exchange domain models - Value Objects and Entities."""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from datetime import timezone as dt_timezone
from enum import Enum
import uuid


class ExchangeType(str, Enum):
    """Supported exchange types."""
    BINANCE = "BINANCE"
    BYBIT = "BYBIT"
    OKX = "OKX"


class ConnectionStatus(str, Enum):
    """Exchange connection status."""
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    ERROR = "ERROR"


@dataclass(frozen=True)
class APICredentials:
    """Encrypted API credentials value object."""
    
    api_key: str  # Encrypted
    secret_key: str  # Encrypted
    passphrase: Optional[str] = None  # Encrypted, for some exchanges
    
    def __str__(self) -> str:
        return f"APICredentials(api_key=***{self.api_key[-4:]}, secret_key=***)"


@dataclass(frozen=True)
class ExchangePermissions:
    """Exchange API permissions."""
    
    spot_trade: bool = False
    futures_trade: bool = False
    margin_trade: bool = False
    read_only: bool = False
    withdraw: bool = False
    
    def can_trade(self) -> bool:
        """Check if can execute trades."""
        return (self.spot_trade or self.futures_trade or self.margin_trade) and not self.read_only
    
    def is_safe(self) -> bool:
        """Check if permissions are safe (no withdraw)."""
        return not self.withdraw


class ExchangeConnection:
    """Exchange API connection entity."""
    
    def __init__(
        self,
        id: uuid.UUID,
        user_id: uuid.UUID,
        exchange_type: ExchangeType,
        name: str,
        credentials: APICredentials,
        permissions: ExchangePermissions,
        is_testnet: bool = True,
        is_active: bool = True,
        status: ConnectionStatus = ConnectionStatus.DISCONNECTED,
        last_used_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.user_id = user_id
        self.exchange_type = exchange_type
        self.name = name
        self.credentials = credentials
        self.permissions = permissions
        self.is_testnet = is_testnet
        self.is_active = is_active
        self.status = status
        self.last_used_at = last_used_at
        self.created_at = created_at or datetime.now(dt_timezone.utc)
        self.updated_at = datetime.now(dt_timezone.utc)
    
    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        exchange_type: ExchangeType,
        name: str,
        credentials: APICredentials,
        permissions: ExchangePermissions,
        is_testnet: bool = True,
    ) -> "ExchangeConnection":
        """Create a new exchange connection."""
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            exchange_type=exchange_type,
            name=name,
            credentials=credentials,
            permissions=permissions,
            is_testnet=is_testnet,
        )
    
    def activate(self) -> None:
        """Activate connection."""
        self.is_active = True
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate connection."""
        self.is_active = False
        self.status = ConnectionStatus.DISCONNECTED
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def mark_connected(self) -> None:
        """Mark connection as connected."""
        if not self.is_active:
            raise ValueError("Cannot connect inactive connection")
        self.status = ConnectionStatus.CONNECTED
        self.last_used_at = datetime.now(dt_timezone.utc)
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def mark_disconnected(self) -> None:
        """Mark connection as disconnected."""
        self.status = ConnectionStatus.DISCONNECTED
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def mark_error(self) -> None:
        """Mark connection as error state."""
        self.status = ConnectionStatus.ERROR
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def mark_connecting(self) -> None:
        """Mark connection as connecting."""
        if not self.is_active:
            raise ValueError("Cannot connect inactive connection")
        self.status = ConnectionStatus.CONNECTING
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def update_last_used(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.now(dt_timezone.utc)
        self.updated_at = datetime.now(dt_timezone.utc)
    
    def can_trade(self) -> bool:
        """Check if connection can be used for trading."""
        return (
            self.is_active
            and self.status == ConnectionStatus.CONNECTED
            and self.permissions.can_trade()
        )
    
    def __repr__(self) -> str:
        return f"ExchangeConnection(id={self.id}, exchange={self.exchange_type.value}, name={self.name}, status={self.status.value})"
