"""Binance Futures adapter implementation"""
import time
import hmac
import hashlib
from typing import Dict, Any, List, Optional
from decimal import Decimal

from .exchange_gateway import (
    ExchangeGateway,
    AccountInfoData,
    BalanceData,
    PositionData
)
from src.trading.shared.errors.infrastructure_errors import ExternalAPIError as ExchangeAPIError


class BinanceAdapter(ExchangeGateway):
    """
    Binance Futures API adapter.
    
    Implements ExchangeGateway interface for Binance Futures.
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://fapi.binance.com",
        testnet: bool = False
    ):
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url
        self._testnet = testnet
        
        # Use performance-optimized HTTP client if available
        try:
            from src.trading.performance.http_pool import HTTPPoolManager
            self._http = HTTPPoolManager(pool_size=10)
        except ImportError:
            # Fallback to basic implementation
            import aiohttp
            self._session = None
            
    def _normalize_symbol(self, symbol: str) -> str:
        """Convert BTC/USDT to BTCUSDT"""
        if not symbol:
            return symbol
        return symbol.replace("/", "").upper()
    
    async def get_account_info(self) -> AccountInfoData:
        """
        Get account info from Binance Futures.
        
        Returns:
            AccountInfoData with balances and positions
        """
        try:
            # Call Binance API - Account for Balances, PositionRisk for Positions (markPrice)
            # Parallel execution could be better but sequential is safer for now
            account_response = await self._signed_request("GET", "/fapi/v2/account")
            positions_response = await self._signed_request("GET", "/fapi/v2/positionRisk")
            
            # Parse balances
            balances = []
            for asset_data in account_response.get("assets", []):
                balance = Decimal(asset_data["walletBalance"])
                if balance > 0:  # Only include non-zero balances
                    balances.append(
                        BalanceData(
                            asset=asset_data["asset"],
                            free=Decimal(asset_data["availableBalance"]),
                            locked=balance - Decimal(asset_data["availableBalance"])
                        )
                    )
            
            # Parse positions from positionRisk
            positions = []
            # positions_response is a list for positionRisk, not a dict with "positions" key
            raw_positions = positions_response if isinstance(positions_response, list) else []
            
            for pos_data in raw_positions:
                quantity = Decimal(pos_data["positionAmt"])
                if quantity != 0:  # Only include open positions
                    positions.append(
                        PositionData(
                            symbol=pos_data["symbol"],
                            side="LONG" if quantity > 0 else "SHORT",
                            quantity=abs(quantity),
                            entry_price=Decimal(pos_data["entryPrice"]),
                            mark_price=Decimal(pos_data["markPrice"]),
                            leverage=int(pos_data["leverage"]),
                            # Note: positionRisk uses 'unRealizedProfit' (capital R), account used 'unrealizedProfit'
                            # We check both just in case
                            unrealized_pnl=Decimal(pos_data.get("unRealizedProfit") or pos_data.get("unrealizedProfit") or "0"),
                            margin_type=pos_data.get("marginType", "cross")
                        )
                    )
            
            return AccountInfoData(
                account_id=account_response.get("accountAlias", "main"),
                balances=balances,
                positions=positions,
                total_balance=Decimal(account_response.get("totalWalletBalance", "0")),
                available_balance=Decimal(account_response.get("availableBalance", "0"))
            )
            
        except Exception as e:
            raise ExchangeAPIError(f"Failed to get account info: {str(e)}") from e

    async def get_position_risk(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get position risk (leverage, margin type) from Binance.
        
        Args:
            symbol: Optional symbol to filter by
            
        Returns:
            List of position risk data
        """
        params = {}
        if symbol:
            params["symbol"] = self._normalize_symbol(symbol)
            
        return await self._signed_request("GET", "/fapi/v2/positionRisk", params)

    
    async def get_balance(self, asset: str) -> BalanceData:
        """Get balance for specific asset"""
        account_info = await self.get_account_info()
        
        for balance in account_info.balances:
            if balance.asset == asset.upper():
                return balance
        
        # Return zero balance if not found
        return BalanceData(asset=asset.upper(), free=Decimal(0), locked=Decimal(0))
    
    async def test_connectivity(self) -> bool:
        """Test Binance API connectivity"""
        try:
            await self._request("GET", "/fapi/v1/ping")
            return True
        except Exception:
            return False
    
    async def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create new order"""
        params = {
            "symbol": self._normalize_symbol(symbol),
            "side": side,
            "type": type,
            "quantity": str(quantity),
        }
        
        # Add positionSide for Hedge Mode compatibility
        # BUY -> LONG, SELL -> SHORT (for opening positions)
        if "positionSide" not in kwargs:
            params["positionSide"] = "LONG" if side == "BUY" else "SHORT"
        
        # Add any extra params
        params.update(kwargs)
        
        if price:
            params["price"] = str(price)
            # LIMIT orders require timeInForce
            if type == "LIMIT" and "timeInForce" not in params:
                params["timeInForce"] = "GTC"
            
        print(f"DEBUG [BinanceAdapter]: Sending order params: {params}")
        return await self._signed_request("POST", "/fapi/v1/order", params)

    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        params = {
            "symbol": self._normalize_symbol(symbol),
            "orderId": order_id
        }
        return await self._signed_request("DELETE", "/fapi/v1/order", params)

    async def get_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Get order details"""
        params = {
            "symbol": self._normalize_symbol(symbol),
            "orderId": order_id
        }
        return await self._signed_request("GET", "/fapi/v1/order", params)
        
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get open orders"""
        params = {}
        if symbol:
            params["symbol"] = self._normalize_symbol(symbol)
        return await self._signed_request("GET", "/fapi/v1/openOrders", params)

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500  # BINANCE API LIMIT: Max 500 per request
        # TODO: Implement pagination loop for requests >500 to fetch complete datasets
        # For now, callers must handle pagination themselves or accept truncated data
    ) -> List[List[Any]]:
        """
        Get kline/candlestick data from Binance Futures.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Result limit (default 500, max 1500)
            
        Returns:
            List of kline data arrays
        """
        params = {
            "symbol": self._normalize_symbol(symbol),
            "interval": interval,
            "limit": limit
        }
        
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
            
        # Klines endpoint is public, use _request (unsigned)
        return await self._request("GET", "/fapi/v1/klines", params)

    async def get_ticker_price(self, symbol: str) -> Decimal:
        """Get current price"""
        params = {"symbol": self._normalize_symbol(symbol)}
        response = await self._request("GET", "/fapi/v1/ticker/price", params)
        return Decimal(response["price"])

    async def get_earliest_valid_timestamp(self, symbol: str, interval: str) -> int:
        """Get earliest valid timestamp for symbol"""
        # Fetch first available candle by requesting from start_time=0
        klines = await self.get_klines(
            symbol=self._normalize_symbol(symbol),
            interval=interval,
            start_time=0,
            limit=1
        )
        
        if klines and len(klines) > 0:
            # Return open time of first candle (index 0)
            return int(klines[0][0])
            
        return 0
    
    # Private methods
    
    async def _request(self, method: str, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Make unsigned request"""
        url = f"{self._base_url}{endpoint}"
        
        # Use optimized HTTP client if available
        if hasattr(self, '_http'):
            response = await self._http.get(url, params=params)
            return response
        else:
            # Fallback to aiohttp
            if self._session is None:
                import aiohttp
                self._session = aiohttp.ClientSession()
            
            async with self._session.request(method, url, params=params) as response:
                response.raise_for_status()
                return await response.json()
    
    async def _signed_request(self, method: str, endpoint: str, params: Dict = None) -> Dict[str, Any]:
        """Make signed request (requires authentication)"""
        from urllib.parse import urlencode
        
        if params is None:
            params = {}
        
        # Add timestamp
        params["timestamp"] = int(time.time() * 1000)
        
        # Create signature - Binance requires UNSORTED params with urlencode
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        params["signature"] = signature
        
        # Add API key to headers
        headers = {"X-MBX-APIKEY": self._api_key}
        
        # Make request
        url = f"{self._base_url}{endpoint}"
        print(f"DEBUG [BinanceAdapter]: {method} {url}")
        print(f"DEBUG [BinanceAdapter]: Params (without signature): {list(params.keys())}")
        
        if hasattr(self, '_http'):
            response = await self._http.get(url, params=params, headers=headers)
            return response
        else:
            if self._session is None:
                import aiohttp
                self._session = aiohttp.ClientSession()
            
            async with self._session.request(
                method, url, params=params, headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ExchangeAPIError(
                        f"Binance API error {response.status}: {error_text}"
                    )
                return await response.json()
    
    async def start_user_data_stream(self) -> str:
        """
        Start a new user data stream.
        
        Returns:
            listenKey for the stream
        """
        response = await self._signed_request("POST", "/fapi/v1/listenKey")
        return response["listenKey"]
    
    async def keep_alive_user_data_stream(self, listen_key: str):
        """
        Keep alive a user data stream to prevent timeout.
        Stream expires after 60 minutes if not kept alive.
        """
        params = {"listenKey": listen_key}
        await self._signed_request("PUT", "/fapi/v1/listenKey", params)
        
    async def close_user_data_stream(self, listen_key: str):
        """Close a user data stream."""
        params = {"listenKey": listen_key}
        await self._signed_request("DELETE", "/fapi/v1/listenKey", params)

    async def close(self):
        """Close HTTP session"""
        if hasattr(self, '_session') and self._session:
            await self._session.close()
