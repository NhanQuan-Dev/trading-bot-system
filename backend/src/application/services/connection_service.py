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
import os
from cryptography.fernet import Fernet

from trading.infrastructure.persistence.models.core_models import APIConnectionModel, ExchangeModel


class ConnectionService:
    """Service for managing exchange API connections."""
    
    def __init__(self, session: AsyncSession):
        # Khởi tạo với DB session để truy cập dữ liệu
        self._session = session
        
    def _decrypt(self, encrypted_value: str) -> str:
        """Decrypt a string value."""
        if not encrypted_value:
            return ""
        encryption_key = os.getenv("ENCRYPTION_KEY", "")
        if not encryption_key:
            return ""
        try:
            cipher = Fernet(encryption_key.encode())
            return cipher.decrypt(encrypted_value.encode()).decode()
        except Exception:
            return ""

    def _encrypt(self, value: str) -> str:
        """Encrypt a string value."""
        if not value:
            return ""
        encryption_key = os.getenv("ENCRYPTION_KEY", "")
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY environment variable not set")
        cipher = Fernet(encryption_key.encode())
        return cipher.encrypt(value.encode()).decode()
    
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
            if conn.api_key_encrypted:
                raw_key = self._decrypt(conn.api_key_encrypted)
                masked_key = "*" * max(0, len(raw_key) - 4) + raw_key[-4:] if raw_key else "****"
            
            connections_data.append({
                "id": str(conn.id),
                "exchange_id": conn.exchange_id,
                "exchange_name": conn.exchange.name if conn.exchange else "Unknown",
                "name": conn.name,
                "api_key": masked_key,
                "status": "active" if conn.is_active else "inactive",
                "is_testnet": conn.is_testnet,
                "created_at": conn.created_at.isoformat() if conn.created_at else None,
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
            api_key_encrypted=self._encrypt(api_key),
            secret_key_encrypted=self._encrypt(api_secret),
            passphrase_encrypted=self._encrypt(api_passphrase) if api_passphrase else None,
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
            connection.api_key_encrypted = self._encrypt(api_key)
        if api_secret is not None:
            connection.secret_key_encrypted = self._encrypt(api_secret)
        if api_passphrase is not None:
            connection.passphrase_encrypted = self._encrypt(api_passphrase)
        if status is not None:
            connection.status = status
        
        connection.updated_at = datetime.utcnow()
        
        await self._session.commit()
        await self._session.refresh(connection)
        
        # Mask API key
        raw_key = api_key or (self._decrypt(connection.api_key_encrypted) if connection.api_key_encrypted else "")
        masked_key = "*" * max(0, len(raw_key) - 4) + raw_key[-4:] if raw_key else "****"
        
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
            # Use direct Binance API adapter instead of CCXT
            if exchange.code == "BINANCE" or "BINANCE" in exchange.name.upper():
                from src.trading.infrastructure.exchange.binance_adapter import BinanceAdapter
                
                # Select base URL based on testnet flag
                base_url = "https://demo-fapi.binance.com" if is_testnet else "https://fapi.binance.com"
                
                adapter = BinanceAdapter(
                    api_key=api_key,
                    api_secret=api_secret,
                    base_url=base_url,
                    testnet=is_testnet
                )
                
                # Test connectivity first
                is_connected = await asyncio.wait_for(
                    adapter.test_connectivity(),
                    timeout=10.0
                )
                
                if not is_connected:
                    await adapter.close()
                    return {
                        "success": False,
                        "error": "Failed to connect to Binance API"
                    }
                
                # Get account info
                account_info = await asyncio.wait_for(
                    adapter.get_account_info(),
                    timeout=10.0
                )
                
                await adapter.close()
                
                # Extract balances
                total_balance = {
                    b.asset: float(b.free + b.locked)
                    for b in account_info.balances
                    if (b.free + b.locked) > 0
                }
                
                return {
                    "success": True,
                    "balance": total_balance,
                    "message": f"Successfully connected to Binance {'Testnet' if is_testnet else 'Mainnet'}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Exchange {exchange.name} is not supported yet"
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
        
        # Decrypt keys
        api_key = self._decrypt(connection.api_key_encrypted)
        secret_key = self._decrypt(connection.secret_key_encrypted)
        passphrase = self._decrypt(connection.passphrase_encrypted) if connection.passphrase_encrypted else None
        
        # Test connection
        test_result = await self.test_connection(
            exchange_id=connection.exchange_id,
            api_key=api_key,
            api_secret=secret_key,
            api_passphrase=passphrase,
            is_testnet=connection.is_testnet
        )
        
        # Update status based on test result
        new_status = "active" if test_result["success"] else "error"
        connection.status = new_status
        connection.last_used_at = datetime.utcnow()
        connection.updated_at = datetime.utcnow()
        
        await self._session.commit()
        
        # Mask API key (using decrypted key)
        masked_key = "*" * max(0, len(api_key) - 4) + api_key[-4:] if api_key else "****"
        
        return {
            "id": str(connection.id),
            "exchange_name": connection.exchange.name if connection.exchange else "Unknown",
            "name": connection.name,
            "api_key": masked_key,
            "status": connection.status,
            "test_result": test_result,
            "updated_at": connection.updated_at.isoformat()
        }

    async def get_connection_credentials(self, connection_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get decrypted connection credentials for internal use.
        
        Args:
            connection_id: Connection UUID
            user_id: User UUID
            
        Returns:
            Dict containing api_key, api_secret, api_passphrase, is_testnet, exchange_code
        """
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
            
        return {
            "api_key": self._decrypt(connection.api_key_encrypted),
            "api_secret": self._decrypt(connection.secret_key_encrypted),
            "api_passphrase": self._decrypt(connection.passphrase_encrypted) if connection.passphrase_encrypted else None,
            "is_testnet": connection.is_testnet,
            "exchange_code": connection.exchange.code if connection.exchange else None,
            "exchange_name": connection.exchange.name if connection.exchange else None,
            "exchange_id": connection.exchange_id
        }
