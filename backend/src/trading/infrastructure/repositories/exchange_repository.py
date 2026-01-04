"""SQLAlchemy implementation of Exchange repository."""
from typing import Optional, List
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet
import os

from ...domain.exchange import (
    ExchangeConnection,
    ExchangeType,
    ConnectionStatus,
    APICredentials,
    ExchangePermissions,
)
from ...domain.exchange.repository import IExchangeRepository
from ..persistence.models.core_models import APIConnectionModel, ExchangeModel


class ExchangeRepository(IExchangeRepository):
    """SQLAlchemy implementation of exchange repository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
        # Initialize Fernet for encryption/decryption
        encryption_key = os.getenv("ENCRYPTION_KEY", "")
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY environment variable must be set")
        self._cipher = Fernet(encryption_key.encode())
    
    def _encrypt(self, value: str) -> str:
        """Encrypt a string value."""
        return self._cipher.encrypt(value.encode()).decode()
    
    def _decrypt(self, encrypted_value: str) -> str:
        """Decrypt a string value."""
        return self._cipher.decrypt(encrypted_value.encode()).decode()
    
    async def save(self, connection: ExchangeConnection) -> None:
        """Save or update exchange connection."""
        # Get exchange_id from exchange_type
        stmt = select(ExchangeModel).where(ExchangeModel.code == connection.exchange_type.value)
        result = await self._session.execute(stmt)
        exchange = result.scalar_one_or_none()
        
        if not exchange:
            raise ValueError(f"Exchange {connection.exchange_type.value} not found in database")
        
        # Check if connection exists
        stmt = select(APIConnectionModel).where(APIConnectionModel.id == connection.id)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.name = connection.name
            existing.is_testnet = connection.is_testnet
            existing.api_key_encrypted = self._encrypt(connection.credentials.api_key)
            existing.secret_key_encrypted = self._encrypt(connection.credentials.secret_key)
            if connection.credentials.passphrase:
                existing.passphrase_encrypted = self._encrypt(connection.credentials.passphrase)
            # Store testnet keys if provided (from meta_data)
            if hasattr(connection, 'testnet_credentials') and connection.testnet_credentials:
                existing.testnet_api_key_encrypted = self._encrypt(connection.testnet_credentials.get('api_key', ''))
                existing.testnet_secret_key_encrypted = self._encrypt(connection.testnet_credentials.get('secret_key', ''))
            existing.is_active = connection.is_active
            existing.permissions = {
                "spot_trade": connection.permissions.spot_trade,
                "futures_trade": connection.permissions.futures_trade,
                "margin_trade": connection.permissions.margin_trade,
                "read_only": connection.permissions.read_only,
                "withdraw": connection.permissions.withdraw,
            }
            existing.last_used_at = connection.last_used_at
        else:
            # Create new
            model = APIConnectionModel(
                id=connection.id,
                user_id=connection.user_id,
                exchange_id=exchange.id,
                name=connection.name,
                is_testnet=connection.is_testnet,
                api_key_encrypted=self._encrypt(connection.credentials.api_key),
                secret_key_encrypted=self._encrypt(connection.credentials.secret_key),
                passphrase_encrypted=self._encrypt(connection.credentials.passphrase) if connection.credentials.passphrase else None,
                is_active=connection.is_active,
                permissions={
                    "spot_trade": connection.permissions.spot_trade,
                    "futures_trade": connection.permissions.futures_trade,
                    "margin_trade": connection.permissions.margin_trade,
                    "read_only": connection.permissions.read_only,
                    "withdraw": connection.permissions.withdraw,
                },
                last_used_at=connection.last_used_at,
            )
            # Store testnet keys if provided
            if hasattr(connection, 'testnet_credentials') and connection.testnet_credentials:
                model.testnet_api_key_encrypted = self._encrypt(connection.testnet_credentials.get('api_key', ''))
                model.testnet_secret_key_encrypted = self._encrypt(connection.testnet_credentials.get('secret_key', ''))
            self._session.add(model)
        
        await self._session.flush()
    
    async def find_by_id(self, connection_id: uuid.UUID) -> Optional[ExchangeConnection]:
        """Find connection by ID."""
        stmt = (
            select(APIConnectionModel, ExchangeModel)
            .join(ExchangeModel, APIConnectionModel.exchange_id == ExchangeModel.id)
            .where(
                APIConnectionModel.id == connection_id,
                APIConnectionModel.deleted_at.is_(None)
            )
        )
        result = await self._session.execute(stmt)
        row = result.first()
        
        if not row:
            return None
        
        model, exchange = row
        return self._to_domain(model, exchange.code)
    
    async def find_by_user(self, user_id: uuid.UUID) -> List[ExchangeConnection]:
        """Find all connections for a user."""
        stmt = (
            select(APIConnectionModel, ExchangeModel)
            .join(ExchangeModel, APIConnectionModel.exchange_id == ExchangeModel.id)
            .where(
                APIConnectionModel.user_id == user_id,
                APIConnectionModel.deleted_at.is_(None)
            )
            .order_by(APIConnectionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        
        connections = []
        for model, exchange in result:
            connections.append(self._to_domain(model, exchange.code))
        
        return connections
    
    async def find_by_user_and_exchange(
        self, 
        user_id: uuid.UUID, 
        exchange_type: ExchangeType
    ) -> List[ExchangeConnection]:
        """Find user's connections for specific exchange."""
        stmt = (
            select(APIConnectionModel, ExchangeModel)
            .join(ExchangeModel, APIConnectionModel.exchange_id == ExchangeModel.id)
            .where(
                APIConnectionModel.user_id == user_id,
                ExchangeModel.code == exchange_type.value,
                APIConnectionModel.deleted_at.is_(None)
            )
            .order_by(APIConnectionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        
        connections = []
        for model, exchange in result:
            connections.append(self._to_domain(model, exchange.code))
        
        return connections
    
    async def find_active_by_user(self, user_id: uuid.UUID) -> List[ExchangeConnection]:
        """Find active connections for a user."""
        stmt = (
            select(APIConnectionModel, ExchangeModel)
            .join(ExchangeModel, APIConnectionModel.exchange_id == ExchangeModel.id)
            .where(
                APIConnectionModel.user_id == user_id,
                APIConnectionModel.is_active == True,
                APIConnectionModel.deleted_at.is_(None)
            )
            .order_by(APIConnectionModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        
        connections = []
        for model, exchange in result:
            connections.append(self._to_domain(model, exchange.code))
        
        return connections
    
    async def delete(self, connection_id: uuid.UUID) -> None:
        """Delete (soft delete) connection."""
        stmt = select(APIConnectionModel).where(APIConnectionModel.id == connection_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model:
            model.soft_delete()
            await self._session.flush()
    
    def _to_domain(self, model: APIConnectionModel, exchange_code: str) -> ExchangeConnection:
        """Convert model to domain entity."""
        permissions_data = model.permissions or {}
        
        # Determine testnet mode: respect stored flag, fall back to presence of testnet keys
        has_testnet_keys = (
            model.testnet_api_key_encrypted is not None 
            and model.testnet_secret_key_encrypted is not None
        )

        # If DB explicitly sets is_testnet, honor it; otherwise infer from testnet keys
        is_testnet = bool(getattr(model, 'is_testnet', False)) or has_testnet_keys

        # Select credentials: prefer testnet keys when flag is set and testnet keys exist
        if is_testnet and has_testnet_keys:
            api_key = self._decrypt(model.testnet_api_key_encrypted)
            secret_key = self._decrypt(model.testnet_secret_key_encrypted)
        else:
            api_key = self._decrypt(model.api_key_encrypted)
            secret_key = self._decrypt(model.secret_key_encrypted)
        
        connection = ExchangeConnection(
            id=model.id,
            user_id=model.user_id,
            exchange_type=ExchangeType(exchange_code),
            name=model.name,
            credentials=APICredentials(
                api_key=api_key,
                secret_key=secret_key,
                passphrase=self._decrypt(model.passphrase_encrypted) if model.passphrase_encrypted else None,
            ),
            permissions=ExchangePermissions(
                spot_trade=permissions_data.get("spot_trade", False),
                futures_trade=permissions_data.get("futures_trade", False),
                margin_trade=permissions_data.get("margin_trade", False),
                read_only=permissions_data.get("read_only", False),
                withdraw=permissions_data.get("withdraw", False),
            ),
            is_testnet=is_testnet,
            is_active=model.is_active,
            status=ConnectionStatus.CONNECTED if model.is_active else ConnectionStatus.DISCONNECTED,
            last_used_at=model.last_used_at,
            created_at=model.created_at,
        )
        
        # Attach both mainnet and testnet credentials for future use
        if has_testnet_keys:
            connection.mainnet_credentials = {
                'api_key': self._decrypt(model.api_key_encrypted),
                'secret_key': self._decrypt(model.secret_key_encrypted),
            }
        
        return connection
