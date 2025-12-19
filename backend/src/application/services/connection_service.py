"""
Connection Service - Quản lý kết nối API với các sàn giao dịch.

Mục đích:
- Lấy, tạo, cập nhật, xóa kết nối API của user với exchanges như Binance.
- Validate và test kết nối để đảm bảo hoạt động.

Liên quan đến file nào:
- Sử dụng models từ trading/infrastructure/persistence/models/core_models.py (APIConnectionModel, ExchangeModel).
- Khi gặp bug: Kiểm tra DB connection trong infrastructure/config/, test API keys với infrastructure/binance/auth.py, hoặc log errors trong shared/exceptions/.
"""

"""Connection Service for managing exchange API connections."""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
import uuid
import asyncio

from trading.infrastructure.persistence.models.core_models import APIConnectionModel, ExchangeModel


class ConnectionService:
    """Service for managing exchange API connections."""
    
    def __init__(self, session: AsyncSession):
        # Khởi tạo với DB session để truy cập dữ liệu
        self._session = session
    
    async def get_all_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all user's exchange connections - Lấy tất cả kết nối của user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of connection data
        """
        # Query DB để lấy connections chưa bị xóa, kèm exchange info
        stmt = select(APIConnectionModel).where(
            and_(
                APIConnectionModel.user_id == user_id,
                APIConnectionModel.deleted_at.is_(None)
            )
        ).options(
            selectinload(APIConnectionModel.exchange)
        ).order_by(APIConnectionModel.created_at.desc())
        
        result = await self._session.execute(stmt)
        connections = result.scalars().all()
        
        connections_data = []
        for conn in connections:
            # Ẩn API key, chỉ show 4 ký tự cuối
            masked_key = ""
            if conn.api_key:
                masked_key = "*" * (len(conn.api_key) - 4) + conn.api_key[-4:]
            
            connections_data.append({
                "id": str(conn.id),
                "exchange_id": conn.exchange_id,
                "exchange_name": conn.exchange.name if conn.exchange else "Unknown",
                "name": conn.name,
                "api_key": masked_key,
                "status": conn.status,
                "is_testnet": conn.is_testnet,
                "created_at": conn.created_at.isoformat(),
                "last_used_at": conn.last_used_at.isoformat() if conn.last_used_at else None
            })
        
        return connections_data
    
    async def create_connection(
        self,
        user_id: str,
        exchange_id: int,
        api_key: str,
        api_secret: str,
        api_passphrase: Optional[str] = None,
        name: Optional[str] = None,
        is_testnet: bool = False
    ) -> Dict[str, Any]:
        """
        Create new exchange connection - Tạo kết nối mới.
        
        Args:
            user_id: User UUID
            exchange_id: Exchange ID
            api_key: API key
            api_secret: API secret
            api_passphrase: API passphrase (for some exchanges)
            name: Connection name (optional)
            is_testnet: Whether this is testnet connection
            
        Returns:
            Created connection data
        """
        # Kiểm tra exchange có tồn tại không
        exchange_stmt = select(ExchangeModel).where(ExchangeModel.id == exchange_id)
        exchange_result = await self._session.execute(exchange_stmt)
        exchange = exchange_result.scalar_one_or_none()
        
        if not exchange:
            raise ValueError(f"Exchange with ID {exchange_id} not found")
        
        # Tạo connection mới trong DB
        connection = APIConnectionModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id),
            exchange_id=exchange_id,
            name=name or f"{exchange.name} Connection",
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
            is_testnet=is_testnet,
            status="inactive",  # Bắt đầu inactive, cần test
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self._session.add(connection)
        await self._session.commit()
        await self._session.refresh(connection)
        
        # Ẩn API key
        masked_key = "*" * (len(api_key) - 4) + api_key[-4:]
        
        return {
            "id": str(connection.id),
            "exchange_id": connection.exchange_id,
            "exchange_name": exchange.name,
            "name": connection.name,
            "api_key": masked_key,
            "status": connection.status,
            "is_testnet": connection.is_testnet,
            "created_at": connection.created_at.isoformat()
        }
    
    async def update_connection(
        self,
        connection_id: str,
        user_id: str,
        name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        api_passphrase: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update exchange connection.
        
        Args:
            connection_id: Connection UUID
            user_id: User UUID
            name: New name (optional)
            api_key: New API key (optional)
            api_secret: New API secret (optional)
            api_passphrase: New API passphrase (optional)
            status: New status (optional)
            
        Returns:
            Updated connection data
        """
        # Get connection
        stmt = select(APIConnectionModel).where(
            and_(
                APIConnectionModel.id == uuid.UUID(connection_id),
                APIConnectionModel.user_id == user_id,
                APIConnectionModel.deleted_at.is_(None)
            )
        ).options(selectinload(APIConnectionModel.exchange))
        
        result = await self._session.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        # Update fields
        if name is not None:
            connection.name = name
        if api_key is not None:
            connection.api_key = api_key
        if api_secret is not None:
            connection.api_secret = api_secret
        if api_passphrase is not None:
            connection.api_passphrase = api_passphrase
        if status is not None:
            connection.status = status
        
        connection.updated_at = datetime.utcnow()
        
        await self._session.commit()
        await self._session.refresh(connection)
        
        # Mask API key
        masked_key = "*" * (len(connection.api_key) - 4) + connection.api_key[-4:] if connection.api_key else ""
        
        return {
            "id": str(connection.id),
            "exchange_id": connection.exchange_id,
            "exchange_name": connection.exchange.name if connection.exchange else "Unknown",
            "name": connection.name,
            "api_key": masked_key,
            "status": connection.status,
            "is_testnet": connection.is_testnet,
            "updated_at": connection.updated_at.isoformat()
        }
    
    async def delete_connection(self, connection_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete exchange connection.
        
        Args:
            connection_id: Connection UUID
            user_id: User UUID
            
        Returns:
            Success message
        """
        # Get connection
        stmt = select(APIConnectionModel).where(
            and_(
                APIConnectionModel.id == uuid.UUID(connection_id),
                APIConnectionModel.user_id == user_id,
                APIConnectionModel.deleted_at.is_(None)
            )
        )
        
        result = await self._session.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        # Check if connection is used by active bots
        from trading.infrastructure.persistence.models.bot_models import BotModel
        bots_stmt = select(BotModel).where(
            and_(
                BotModel.exchange_connection_id == uuid.UUID(connection_id),
                BotModel.status.in_(["ACTIVE", "STARTING"]),
                BotModel.deleted_at.is_(None)
            )
        )
        bots_result = await self._session.execute(bots_stmt)
        active_bots = bots_result.scalars().all()
        
        if active_bots:
            raise ValueError(
                f"Cannot delete connection: {len(active_bots)} active bot(s) are using it. "
                "Please stop the bots first."
            )
        
        # Soft delete
        connection.deleted_at = datetime.utcnow()
        connection.updated_at = datetime.utcnow()
        
        await self._session.commit()
        
        return {
            "message": f"Connection {connection.name} deleted successfully",
            "id": str(connection.id)
        }
    
    async def test_connection(
        self,
        exchange_id: int,
        api_key: str,
        api_secret: str,
        api_passphrase: Optional[str] = None,
        is_testnet: bool = False
    ) -> Dict[str, Any]:
        """
        Test exchange API credentials.
        
        Args:
            exchange_id: Exchange ID
            api_key: API key
            api_secret: API secret
            api_passphrase: API passphrase (optional)
            is_testnet: Whether this is testnet
            
        Returns:
            Test result with success status and balance (if successful)
        """
        # Get exchange info
        exchange_stmt = select(ExchangeModel).where(ExchangeModel.id == exchange_id)
        exchange_result = await self._session.execute(exchange_stmt)
        exchange = exchange_result.scalar_one_or_none()
        
        if not exchange:
            return {
                "success": False,
                "error": f"Exchange with ID {exchange_id} not found"
            }
        
        # Try to connect and fetch balance (with timeout)
        try:
            # Import ccxt here to avoid circular imports
            import ccxt.async_support as ccxt
            
            # Create exchange instance
            exchange_class = getattr(ccxt, exchange.name.lower(), None)
            if not exchange_class:
                return {
                    "success": False,
                    "error": f"Exchange {exchange.name} not supported by CCXT"
                }
            
            # Configure exchange
            config = {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "timeout": 10000,  # 10 seconds
            }
            
            if api_passphrase:
                config["password"] = api_passphrase
            
            if is_testnet:
                config["sandbox"] = True
            
            exchange_instance = exchange_class(config)
            
            # Test connection by fetching balance
            balance = await asyncio.wait_for(
                exchange_instance.fetch_balance(),
                timeout=10.0
            )
            
            await exchange_instance.close()
            
            # Extract total balances
            total_balance = {}
            if "total" in balance:
                total_balance = {
                    asset: amount 
                    for asset, amount in balance["total"].items() 
                    if amount > 0
                }
            
            return {
                "success": True,
                "balance": total_balance,
                "message": f"Successfully connected to {exchange.name}"
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Connection timeout (10 seconds)"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection failed: {str(e)}"
            }
    
    async def refresh_connection(self, connection_id: str, user_id: str) -> Dict[str, Any]:
        """
        Refresh connection status by testing it.
        
        Args:
            connection_id: Connection UUID
            user_id: User UUID
            
        Returns:
            Updated connection data with new status
        """
        # Get connection
        stmt = select(APIConnectionModel).where(
            and_(
                APIConnectionModel.id == uuid.UUID(connection_id),
                APIConnectionModel.user_id == user_id,
                APIConnectionModel.deleted_at.is_(None)
            )
        ).options(selectinload(APIConnectionModel.exchange))
        
        result = await self._session.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        # Test connection
        test_result = await self.test_connection(
            exchange_id=connection.exchange_id,
            api_key=connection.api_key,
            api_secret=connection.api_secret,
            api_passphrase=connection.api_passphrase,
            is_testnet=connection.is_testnet
        )
        
        # Update status based on test result
        new_status = "active" if test_result["success"] else "error"
        connection.status = new_status
        connection.last_used_at = datetime.utcnow()
        connection.updated_at = datetime.utcnow()
        
        await self._session.commit()
        
        # Mask API key
        masked_key = "*" * (len(connection.api_key) - 4) + connection.api_key[-4:]
        
        return {
            "id": str(connection.id),
            "exchange_name": connection.exchange.name if connection.exchange else "Unknown",
            "name": connection.name,
            "api_key": masked_key,
            "status": connection.status,
            "test_result": test_result,
            "updated_at": connection.updated_at.isoformat()
        }
