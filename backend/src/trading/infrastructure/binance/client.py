"""Binance Futures REST API client."""
import hmac
import hashlib
import time
from typing import Dict, Any, Optional, List
from decimal import Decimal
import httpx
from urllib.parse import urlencode


class BinanceClient:
    """Binance Futures API client."""
    
    # API Endpoints
    TESTNET_BASE_URL = "https://testnet.binancefuture.com"
    MAINNET_BASE_URL = "https://fapi.binance.com"
    
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        testnet: bool = True,
        timeout: int = 30,
    ):
        """
        Initialize Binance client.
        
        Args:
            api_key: API key
            secret_key: Secret key
            testnet: Use testnet (default True)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = self.TESTNET_BASE_URL if testnet else self.MAINNET_BASE_URL
        self.timeout = timeout
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"X-MBX-APIKEY": api_key},
        )
        # Debug: print base_url and masked api key (never print secret)
        try:
            masked = self.api_key[:6] + "..." + self.api_key[-4:] if self.api_key and len(self.api_key) > 10 else "(masked)"
        except Exception:
            masked = "(masked)"
        print(f"[BINANCE-CLIENT] base_url={self.base_url} api_key={masked}")
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature."""
        query_string = urlencode(params)
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature
    
    def _add_timestamp(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add timestamp to parameters."""
        params["timestamp"] = int(time.time() * 1000)
        return params
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """
        Make API request.
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether to sign the request
        
        Returns:
            API response as dictionary
        """
        params = params or {}
        
        if signed:
            params = self._add_timestamp(params)
            # Debug: show signed request keys and timestamp (do not print secret or raw signature)
            try:
                ts = params.get("timestamp")
                keys = ",".join(sorted(params.keys()))
                print(f"[BINANCE-CLIENT] signed request endpoint={endpoint} keys={keys} timestamp={ts}")
            except Exception:
                pass
            params["signature"] = self._generate_signature(params)
        
        if method == "GET":
            response = await self.client.get(endpoint, params=params)
        elif method == "POST":
            response = await self.client.post(endpoint, params=params)
        elif method == "DELETE":
            response = await self.client.delete(endpoint, params=params)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    # Account Endpoints
    
    async def get_account(self) -> Dict[str, Any]:
        """
        Get account information including balances and positions.
        
        Returns:
            Account data with balances, positions, etc.
        """
        return await self._request("GET", "/fapi/v2/account", signed=True)
    
    async def get_balance(self) -> List[Dict[str, Any]]:
        """
        Get account balance.
        
        Returns:
            List of asset balances
        """
        return await self._request("GET", "/fapi/v2/balance", signed=True)
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current positions.
        
        Returns:
            List of positions
        """
        return await self._request("GET", "/fapi/v2/positionRisk", signed=True)
    
    # Order Endpoints
    
    async def place_order(
        self,
        symbol: str,
        side: str,  # BUY or SELL
        order_type: str,  # MARKET, LIMIT, etc.
        quantity: Decimal,
        price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        position_side: str = "BOTH",  # BOTH, LONG, SHORT (for hedge mode)
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Place a new order.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            side: Order side (BUY or SELL)
            order_type: Order type (MARKET, LIMIT, STOP_MARKET, etc.)
            quantity: Order quantity
            price: Limit price (required for LIMIT orders)
            time_in_force: Time in force (GTC, IOC, FOK)
            reduce_only: Reduce only flag
            position_side: Position side for hedge mode
            **kwargs: Additional parameters
        
        Returns:
            Order response
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
            "positionSide": position_side,
            "reduceOnly": "true" if reduce_only else "false",
        }
        
        if order_type == "LIMIT":
            if price is None:
                raise ValueError("Price is required for LIMIT orders")
            params["price"] = str(price)
            params["timeInForce"] = time_in_force
        
        # Add any additional parameters
        params.update(kwargs)
        
        return await self._request("POST", "/fapi/v1/order", params=params, signed=True)
    
    async def cancel_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        orig_client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Cancel an order.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID (either this or orig_client_order_id required)
            orig_client_order_id: Client order ID
        
        Returns:
            Cancellation response
        """
        params = {"symbol": symbol}
        
        if order_id:
            params["orderId"] = order_id
        elif orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id
        else:
            raise ValueError("Either order_id or orig_client_order_id is required")
        
        return await self._request("DELETE", "/fapi/v1/order", params=params, signed=True)
    
    async def get_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        orig_client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get order information.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID
            orig_client_order_id: Client order ID
        
        Returns:
            Order information
        """
        params = {"symbol": symbol}
        
        if order_id:
            params["orderId"] = order_id
        elif orig_client_order_id:
            params["origClientOrderId"] = orig_client_order_id
        else:
            raise ValueError("Either order_id or orig_client_order_id is required")
        
        return await self._request("GET", "/fapi/v1/order", params=params, signed=True)
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all open orders.
        
        Args:
            symbol: Filter by symbol (optional)
        
        Returns:
            List of open orders
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        return await self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)
    
    # Market Data Endpoints
    
    async def get_ticker_price(self, symbol: Optional[str] = None) -> Any:
        """
        Get ticker price.
        
        Args:
            symbol: Trading symbol (optional, returns all if not provided)
        
        Returns:
            Ticker price or list of prices
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        return await self._request("GET", "/fapi/v1/ticker/price", params=params)
    
    async def get_exchange_info(self) -> Dict[str, Any]:
        """
        Get exchange information including symbols, leverage tiers, etc.
        
        Returns:
            Exchange information
        """
        return await self._request("GET", "/fapi/v1/exchangeInfo")
    
    async def ping(self) -> Dict[str, Any]:
        """
        Test connectivity.
        
        Returns:
            Empty dict if successful
        """
        return await self._request("GET", "/fapi/v1/ping")
    
    async def get_server_time(self) -> Dict[str, Any]:
        """
        Get server time.
        
        Returns:
            Server time
        """
        return await self._request("GET", "/fapi/v1/time")
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
