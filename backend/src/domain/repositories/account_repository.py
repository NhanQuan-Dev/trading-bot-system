from abc import ABC, abstractmethod
from typing import Dict, Any

class AccountRepository(ABC):
    @abstractmethod
    async def fetch_account_data(self):
        """Fetch account data from external source"""
        pass

    @abstractmethod
    def get_positions(self) -> Dict[tuple, Dict[str, Any]]:
        """Get current positions"""
        pass

    @abstractmethod
    def get_listen_key(self) -> str:
        """Get listen key for user data stream"""
        pass