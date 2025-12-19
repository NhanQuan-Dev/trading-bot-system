"""Connection Controller for managing exchange API connections."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from trading.infrastructure.persistence.database import get_db
from application.services.connection_service import ConnectionService
from trading.interfaces.dependencies.auth import get_current_user

router = APIRouter(prefix="/api/connections", tags=["Connections"])


# Request/Response schemas
class CreateConnectionRequest(BaseModel):
    """Create connection request schema."""
    exchange_id: int = Field(..., description="Exchange ID")
    api_key: str = Field(..., min_length=10, description="API key")
    api_secret: str = Field(..., min_length=10, description="API secret")
    api_passphrase: Optional[str] = Field(None, description="API passphrase (required for some exchanges)")
    name: Optional[str] = Field(None, max_length=100, description="Connection name (optional)")
    is_testnet: bool = Field(False, description="Whether this is testnet connection")


class UpdateConnectionRequest(BaseModel):
    """Update connection request schema."""
    name: Optional[str] = Field(None, max_length=100, description="New connection name")
    api_key: Optional[str] = Field(None, min_length=10, description="New API key")
    api_secret: Optional[str] = Field(None, min_length=10, description="New API secret")
    api_passphrase: Optional[str] = Field(None, description="New API passphrase")
    status: Optional[str] = Field(None, description="New status (active/inactive/error)")


class TestConnectionRequest(BaseModel):
    """Test connection request schema."""
    exchange_id: int = Field(..., description="Exchange ID")
    api_key: str = Field(..., min_length=10, description="API key")
    api_secret: str = Field(..., min_length=10, description="API secret")
    api_passphrase: Optional[str] = Field(None, description="API passphrase")
    is_testnet: bool = Field(False, description="Whether this is testnet")


def get_connection_service(db: AsyncSession = Depends(get_db)) -> ConnectionService:
    """Dependency to get connection service."""
    return ConnectionService(db)


@router.get("")
async def get_all_connections(
    current_user = Depends(get_current_user),
    service: ConnectionService = Depends(get_connection_service)
):
    """
    Get all user's exchange connections.
    
    Returns list of connections with:
        - id: Connection UUID
        - exchange_id: Exchange ID
        - exchange_name: Exchange name
        - name: Connection name
        - api_key: Masked API key (last 4 chars visible)
        - status: Connection status (active/inactive/error)
        - is_testnet: Whether this is testnet
        - created_at: Creation timestamp
        - last_used_at: Last usage timestamp
    """
    user_id = str(current_user.id)
    return await service.get_all_connections(user_id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_connection(
    request: CreateConnectionRequest,
    current_user = Depends(get_current_user),
    service: ConnectionService = Depends(get_connection_service)
):
    """
    Create new exchange connection.
    
    Request Body:
        - exchange_id: Exchange ID (required)
        - api_key: API key (required, min 10 chars)
        - api_secret: API secret (required, min 10 chars)
        - api_passphrase: API passphrase (optional, required for some exchanges like OKX)
        - name: Connection name (optional)
        - is_testnet: Whether this is testnet connection (default false)
    
    Returns:
        Created connection data
    """
    user_id = str(current_user.id)
    
    try:
        return await service.create_connection(
            user_id=user_id,
            exchange_id=request.exchange_id,
            api_key=request.api_key,
            api_secret=request.api_secret,
            api_passphrase=request.api_passphrase,
            name=request.name,
            is_testnet=request.is_testnet
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{connection_id}")
async def update_connection(
    connection_id: str,
    request: UpdateConnectionRequest,
    current_user = Depends(get_current_user),
    service: ConnectionService = Depends(get_connection_service)
):
    """
    Update exchange connection.
    
    Path Params:
        - connection_id: Connection UUID
    
    Request Body (all optional):
        - name: New connection name
        - api_key: New API key
        - api_secret: New API secret
        - api_passphrase: New API passphrase
        - status: New status
    
    Returns:
        Updated connection data
    """
    user_id = str(current_user.id)
    
    try:
        return await service.update_connection(
            connection_id=connection_id,
            user_id=user_id,
            name=request.name,
            api_key=request.api_key,
            api_secret=request.api_secret,
            api_passphrase=request.api_passphrase,
            status=request.status
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{connection_id}")
async def delete_connection(
    connection_id: str,
    current_user = Depends(get_current_user),
    service: ConnectionService = Depends(get_connection_service)
):
    """
    Delete exchange connection.
    
    Path Params:
        - connection_id: Connection UUID
    
    Notes:
        - Soft delete (sets deleted_at)
        - Cannot delete if active bots are using this connection
    
    Returns:
        Success message
    """
    user_id = str(current_user.id)
    
    try:
        return await service.delete_connection(connection_id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/test")
async def test_connection(
    request: TestConnectionRequest,
    current_user = Depends(get_current_user),
    service: ConnectionService = Depends(get_connection_service)
):
    """
    Test exchange API credentials.
    
    Request Body:
        - exchange_id: Exchange ID
        - api_key: API key
        - api_secret: API secret
        - api_passphrase: API passphrase (optional)
        - is_testnet: Whether this is testnet
    
    Returns:
        - success: Whether test succeeded
        - balance: Account balance (if successful)
        - error: Error message (if failed)
        - message: Success message (if successful)
    
    Notes:
        - Timeout: 10 seconds
        - Rate limited: 10 requests per minute
    """
    return await service.test_connection(
        exchange_id=request.exchange_id,
        api_key=request.api_key,
        api_secret=request.api_secret,
        api_passphrase=request.api_passphrase,
        is_testnet=request.is_testnet
    )


@router.post("/{connection_id}/refresh")
async def refresh_connection(
    connection_id: str,
    current_user = Depends(get_current_user),
    service: ConnectionService = Depends(get_connection_service)
):
    """
    Refresh connection status by testing it.
    
    Path Params:
        - connection_id: Connection UUID
    
    Returns:
        - Updated connection data
        - test_result: Test result details
    
    Notes:
        - Tests the connection and updates status
        - Status becomes 'active' if test succeeds, 'error' if fails
    """
    user_id = str(current_user.id)
    
    try:
        return await service.refresh_connection(connection_id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
