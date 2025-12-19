"""Exchange manager for handling multiple exchange connections."""
from typing import Dict, Any
import logging

from ...domain.exchange import ExchangeType
from ..binance.client import BinanceClient
from ...shared.exceptions.business import ExchangeConnectionError

logger = logging.getLogger(__name__)


class ExchangeManager:
    """Manager for handling different exchange clients."""
    
    def __init__(self):
        self._clients: Dict[ExchangeType, Any] = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize exchange clients."""
        self._clients[ExchangeType.BINANCE] = BinanceClient()
        # Add other exchanges here in the future
        # self._clients[ExchangeType.BYBIT] = BybitClient()
        # self._clients[ExchangeType.OKX] = OkxClient()
    
    def get_client(self, exchange_type: ExchangeType):
        """Get client for specific exchange."""
        if exchange_type not in self._clients:
            raise ExchangeConnectionError(f"Exchange {exchange_type} not supported")
        
        return self._clients[exchange_type]
    
    async def test_connection(self, exchange_type: ExchangeType, api_key: str, secret_key: str, testnet: bool = True) -> bool:
        """Test connection to exchange."""
        try:
            client = self.get_client(exchange_type)
            await client.set_credentials(api_key, secret_key, testnet)
            
            # Test connection by getting account info
            await client.get_account()
            return True
            
        except Exception as e:
            logger.error(f"Failed to test connection to {exchange_type}: {e}")
            return False
    
    def get_supported_exchanges(self) -> list[ExchangeType]:
        """Get list of supported exchanges."""
        return list(self._clients.keys())