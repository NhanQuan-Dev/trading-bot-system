"""Exchange API schemas."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from .....domain.exchange import ExchangeType, ConnectionStatus


class CreateConnectionRequest(BaseModel):
    """Create exchange connection request."""
    
    exchange_type: ExchangeType = Field(..., description="Exchange type")
    name: str = Field(..., min_length=1, max_length=100, description="Connection name")
    
    # Mainnet credentials
    api_key: str = Field(..., min_length=10, description="Mainnet API key")
    secret_key: str = Field(..., min_length=10, description="Mainnet secret key")
    passphrase: Optional[str] = Field(None, description="Passphrase (for some exchanges)")
    
    # Testnet credentials (optional)
    testnet_api_key: Optional[str] = Field(None, min_length=10, description="Testnet API key (optional)")
    testnet_secret_key: Optional[str] = Field(None, min_length=10, description="Testnet secret key (optional)")
    
    is_testnet: bool = Field(True, description="Use testnet by default")
    
    # Permissions
    spot_trade: bool = Field(False, description="Spot trading permission")
    futures_trade: bool = Field(True, description="Futures trading permission")
    margin_trade: bool = Field(False, description="Margin trading permission")
    read_only: bool = Field(False, description="Read-only permission")
    withdraw: bool = Field(False, description="Withdrawal permission")


class ConnectionResponse(BaseModel):
    """Exchange connection response."""
    
    id: uuid.UUID = Field(..., description="Connection ID")
    exchange_type: str = Field(..., description="Exchange type")
    name: str = Field(..., description="Connection name")
    is_testnet: bool = Field(..., description="Is testnet")
    is_active: bool = Field(..., description="Is active")
    status: str = Field(..., description="Connection status")
    last_used_at: Optional[datetime] = Field(None, description="Last used timestamp")
    created_at: datetime = Field(..., description="Created timestamp")
    
    # Permissions
    permissions: Dict[str, bool] = Field(..., description="API permissions")
    
    # Masked credentials
    api_key_masked: str = Field(..., description="Masked API key")
    
    # Frontend compatibility fields
    api_key: str = Field(..., description="Masked API key (for frontend compatibility)")
    exchange: str = Field(..., description="Exchange code (for frontend compatibility)")
    
    class Config:
        """Pydantic config."""
        from_attributes = True


class TestConnectionRequest(BaseModel):
    """Test connection request."""
    
    connection_id: uuid.UUID = Field(..., description="Connection ID")


class TestConnectionResponse(BaseModel):
    """Test connection response."""
    
    success: bool = Field(..., description="Connection successful")
    message: str = Field(..., description="Result message")
    account_info: Optional[Dict[str, Any]] = Field(None, description="Account information if successful")


class AccountInfoResponse(BaseModel):
    """Account information response."""
    
    total_wallet_balance: str = Field(..., description="Total wallet balance")
    total_unrealized_pnl: str = Field(..., description="Total unrealized P&L")
    total_margin_balance: str = Field(..., description="Total margin balance")
    available_balance: str = Field(..., description="Available balance")
    max_withdraw_amount: str = Field(..., description="Max withdraw amount")
    assets: list = Field(..., description="Asset balances")
    positions: list = Field(..., description="Open positions")
