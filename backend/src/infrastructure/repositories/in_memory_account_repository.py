from typing import Dict, Any
from domain.entities.account import Account, Balance
from domain.repositories.account_repository import AccountRepository
from infrastructure.binance.rest_client import RestClient

class InMemoryAccountRepository(AccountRepository):
    def __init__(self, rest_client: RestClient):
        self.rest_client = rest_client
        self.account_data: Dict[str, Any] = {}

    async def fetch_account_data(self) -> Account:
        """Fetch account data from Binance API"""
        data = self.rest_client.signed_get("/fapi/v2/account", {})
        
        total_wallet_balance = float(data.get("totalWalletBalance", 0))
        available_balance = float(data.get("availableBalance", 0))
        
        account = Account(
            total_wallet_balance=total_wallet_balance,
            available_balance=available_balance
        )
        
        # Add balances
        for asset in data.get("assets", []):
            if float(asset.get("walletBalance", 0)) > 0:
                account.add_balance(
                    asset=asset["asset"],
                    wallet_balance=float(asset["walletBalance"]),
                    cross_wallet_balance=float(asset.get("crossWalletBalance", 0))
                )
        
        self.account_data = data
        return account
    
    def get_positions(self) -> Dict[tuple, Dict[str, Any]]:
        """Extract positions from stored account data"""
        positions = {}
        for pos in self.account_data.get("positions", []):
            symbol = pos["symbol"]
            pos_amt = float(pos["positionAmt"])
            position_side = pos.get("positionSide", "BOTH")
            
            if abs(pos_amt) > 1e-8:
                key = (symbol, position_side)
                positions[key] = {
                    "positionAmt": pos["positionAmt"],
                    "entryPrice": pos["entryPrice"],
                    "leverage": pos.get("leverage", "0"),
                    "unrealizedPnL": pos.get("unrealizedProfit", "0"),
                    "marginType": pos.get("marginType", "cross"),
                    "positionSide": position_side,
                }
        return positions
    
    def get_listen_key(self) -> str:
        """Get listen key for user data stream"""
        import requests
        url = f"{self.rest_client.base_url}/fapi/v1/listenKey"
        headers = {"X-MBX-APIKEY": self.rest_client.api_key}
        resp = requests.post(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()["listenKey"]