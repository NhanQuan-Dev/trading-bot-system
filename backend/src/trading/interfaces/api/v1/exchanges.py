"""Exchange API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .schemas.exchange import (
    CreateConnectionRequest,
    ConnectionResponse,
    TestConnectionRequest,
    TestConnectionResponse,
    AccountInfoResponse,
)
from ....infrastructure.persistence.database import get_db
from ....infrastructure.repositories.exchange_repository import ExchangeRepository
from ....infrastructure.binance import BinanceClient
from ...dependencies.auth import get_current_active_user
from ....domain.user import User
from ....domain.exchange import (
    ExchangeConnection,
    ExchangeType,
    APICredentials,
    ExchangePermissions,
    ConnectionStatus,
)


router = APIRouter(prefix="/exchanges", tags=["Exchanges"])


@router.post("/connections", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    request: CreateConnectionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new exchange API connection.
    
    Args:
        request: Connection details (mainnet + optional testnet keys)
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Created connection
    """
    exchange_repo = ExchangeRepository(db)
    
    # Create connection entity
    connection = ExchangeConnection.create(
        user_id=current_user.id,
        exchange_type=request.exchange_type,
        name=request.name,
        credentials=APICredentials(
            api_key=request.api_key,
            secret_key=request.secret_key,
            passphrase=request.passphrase,
        ),
        permissions=ExchangePermissions(
            spot_trade=request.spot_trade,
            futures_trade=request.futures_trade,
            margin_trade=request.margin_trade,
            read_only=request.read_only,
            withdraw=request.withdraw,
        ),
        is_testnet=request.is_testnet,
    )
    
    # Attach testnet credentials if provided
    testnet_creds = {}
    if request.testnet_api_key and request.testnet_secret_key:
        testnet_creds = {
            'api_key': request.testnet_api_key,
            'secret_key': request.testnet_secret_key,
        }
    connection.testnet_credentials = testnet_creds
    
    # Save to database
    await exchange_repo.save(connection)
    await db.commit()
    
    return ConnectionResponse(
        id=connection.id,
        exchange_type=connection.exchange_type.value,
        name=connection.name,
        is_testnet=connection.is_testnet,
        is_active=connection.is_active,
        status=connection.status.value,
        last_used_at=connection.last_used_at,
        created_at=connection.created_at,
        permissions={
            "spot_trade": connection.permissions.spot_trade,
            "futures_trade": connection.permissions.futures_trade,
            "margin_trade": connection.permissions.margin_trade,
            "read_only": connection.permissions.read_only,
            "withdraw": connection.permissions.withdraw,
        },

        api_key_masked=f"***{connection.credentials.api_key[-4:]}",
        api_key=f"***{connection.credentials.api_key[-4:]}",
        exchange=connection.exchange_type.value,
    )


@router.get("/connections", response_model=List[ConnectionResponse])
async def list_connections(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all exchange connections for current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of connections
    """
    exchange_repo = ExchangeRepository(db)
    connections = await exchange_repo.find_by_user(current_user.id)
    
    return [
        ConnectionResponse(
            id=conn.id,
            exchange_type=conn.exchange_type.value,
            name=conn.name,
            is_testnet=conn.is_testnet,
            is_active=conn.is_active,
            status=conn.status.value,
            last_used_at=conn.last_used_at,
            created_at=conn.created_at,
            permissions={
                "spot_trade": conn.permissions.spot_trade,
                "futures_trade": conn.permissions.futures_trade,
                "margin_trade": conn.permissions.margin_trade,
                "read_only": conn.permissions.read_only,
                "withdraw": conn.permissions.withdraw,
            },


            api_key_masked=f"***{conn.credentials.api_key[-4:]}",
            api_key=f"***{conn.credentials.api_key[-4:]}",
            exchange=conn.exchange_type.value,
        )
        for conn in connections
    ]


@router.post("/connections/test", response_model=TestConnectionResponse)
async def test_connection(
    request: TestConnectionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test exchange API connection.
    
    Args:
        request: Test request with connection ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Test result
    """
    exchange_repo = ExchangeRepository(db)
    
    # Find connection
    connection = await exchange_repo.find_by_id(request.connection_id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    
    # Verify ownership
    if connection.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this connection",
        )
    
    # Test connection based on exchange type
    if connection.exchange_type == ExchangeType.BINANCE:
        # Determine credentials and testnet flag from domain object.
        # ExchangeRepository now persists `is_testnet` so we can rely on it.
        use_testnet = bool(getattr(connection, 'is_testnet', False))
        creds = connection.credentials

        # Debug: show which credentials and URL mode will be used (masked API key)
        try:
            try:
                masked = creds.api_key[:6] + "..." + creds.api_key[-4:] if creds and creds.api_key else "(no-key)"
            except Exception:
                masked = "(invalid-key)"
            print(f"[TEST-CONN] connection_id={connection.id} use_testnet={use_testnet} api_key={masked}")
        except Exception:
            # ensure debug doesn't break flow
            pass

        try:
            async with BinanceClient(
                api_key=creds.api_key,
                secret_key=creds.secret_key,
                testnet=use_testnet,
            ) as client:
                # Test ping
                await client.ping()
                
                # Get account info
                account = await client.get_account()
                
                # Update connection status
                connection.mark_connected()
                await exchange_repo.save(connection)
                await db.commit()
                
                return TestConnectionResponse(
                    success=True,
                    message="Connection successful",
                    account_info={
                        "total_wallet_balance": account.get("totalWalletBalance", "0"),
                        "available_balance": account.get("availableBalance", "0"),
                    },
                )
        except Exception as e:
            # Mark connection as error
            connection.mark_error()
            await exchange_repo.save(connection)
            await db.commit()
            
            return TestConnectionResponse(
                success=False,
                message=f"Connection failed: {str(e)}",
                account_info=None,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Exchange {connection.exchange_type.value} not yet supported",
        )


@router.get("/connections/{connection_id}/account", response_model=AccountInfoResponse)
async def get_account_info(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get account information from exchange.
    
    Args:
        connection_id: Connection ID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Account information
    """
    from uuid import UUID
    
    exchange_repo = ExchangeRepository(db)
    
    # Find connection
    connection = await exchange_repo.find_by_id(UUID(connection_id))
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    
    # Verify ownership
    if connection.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this connection",
        )
    
    if connection.exchange_type == ExchangeType.BINANCE:
        try:
            async with BinanceClient(
                api_key=connection.credentials.api_key,
                secret_key=connection.credentials.secret_key,
                testnet=connection.is_testnet,
            ) as client:
                account = await client.get_account()
                
                # Update last used
                connection.update_last_used()
                await exchange_repo.save(connection)
                await db.commit()
                
                return AccountInfoResponse(
                    total_wallet_balance=account.get("totalWalletBalance", "0"),
                    total_unrealized_pnl=account.get("totalUnrealizedProfit", "0"),
                    total_margin_balance=account.get("totalMarginBalance", "0"),
                    available_balance=account.get("availableBalance", "0"),
                    max_withdraw_amount=account.get("maxWithdrawAmount", "0"),
                    assets=account.get("assets", []),
                    positions=account.get("positions", []),
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch account info: {str(e)}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Exchange {connection.exchange_type.value} not yet supported",
        )


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete exchange connection.
    
    Args:
        connection_id: Connection ID
        current_user: Current authenticated user
        db: Database session
    """
    from uuid import UUID
    
    exchange_repo = ExchangeRepository(db)
    
    # Find connection
    connection = await exchange_repo.find_by_id(UUID(connection_id))
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    
    # Verify ownership
    if connection.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this connection",
        )
    
    # Soft delete
    await exchange_repo.delete(UUID(connection_id))
    await db.commit()
