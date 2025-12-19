import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from decimal import Decimal

from .base_cache import BaseCache

logger = logging.getLogger(__name__)


class MarketDataCache(BaseCache):
    """Cache for market data (prices, order books, trades)."""
    
    def __init__(self):
        super().__init__(prefix="market", default_ttl=60)  # 1 minute default TTL
    
    async def set_symbol_price(
        self, 
        symbol: str, 
        price_data: Dict[str, Any], 
        ttl: int = 30
    ) -> bool:
        """Set current price for a symbol."""
        key = f"price:{symbol}"
        
        # Add timestamp if not present
        if "timestamp" not in price_data:
            price_data["timestamp"] = datetime.utcnow().isoformat()
        
        return await self.set(key, price_data, ttl)
    
    async def get_symbol_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current price for a symbol."""
        key = f"price:{symbol}"
        return await self.get(key)
    
    async def set_symbol_prices(
        self, 
        prices: Dict[str, Dict[str, Any]], 
        ttl: int = 30
    ) -> Dict[str, bool]:
        """Set prices for multiple symbols."""
        results = {}
        for symbol, price_data in prices.items():
            results[symbol] = await self.set_symbol_price(symbol, price_data, ttl)
        return results
    
    async def get_symbol_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get prices for multiple symbols."""
        result = {}
        for symbol in symbols:
            price = await self.get_symbol_price(symbol)
            if price:
                result[symbol] = price
        return result
    
    async def set_order_book(
        self, 
        symbol: str, 
        order_book: Dict[str, Any], 
        ttl: int = 10
    ) -> bool:
        """Set order book for a symbol."""
        key = f"orderbook:{symbol}"
        
        # Add timestamp
        if "timestamp" not in order_book:
            order_book["timestamp"] = datetime.utcnow().isoformat()
        
        return await self.set(key, order_book, ttl)
    
    async def get_order_book(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get order book for a symbol."""
        key = f"orderbook:{symbol}"
        return await self.get(key)
    
    async def set_trade(
        self, 
        symbol: str, 
        trade_data: Dict[str, Any], 
        ttl: int = 300
    ) -> bool:
        """Set recent trade for a symbol."""
        key = f"trade:{symbol}:latest"
        
        # Add timestamp
        if "timestamp" not in trade_data:
            trade_data["timestamp"] = datetime.utcnow().isoformat()
        
        return await self.set(key, trade_data, ttl)
    
    async def get_trade(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get latest trade for a symbol."""
        key = f"trade:{symbol}:latest"
        return await self.get(key)
    
    async def add_trade_history(
        self, 
        symbol: str, 
        trade_data: Dict[str, Any], 
        max_trades: int = 100
    ) -> bool:
        """Add trade to history list."""
        list_key = self._make_key(f"trades:{symbol}")
        
        try:
            # Add trade to list
            trade_json = self._serialize(trade_data)
            await self.redis.lpush(list_key, trade_json)
            
            # Trim list to max size
            await self.redis.ltrim(list_key, 0, max_trades - 1)
            
            # Set expiration
            await self.redis.expire(list_key, 3600)  # 1 hour
            
            return True
        except Exception as e:
            logger.error(f"Error adding trade history for {symbol}: {e}")
            return False
    
    async def get_trade_history(
        self, 
        symbol: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get trade history for a symbol."""
        list_key = self._make_key(f"trades:{symbol}")
        
        try:
            trades = await self.redis.lrange(list_key, 0, limit - 1)
            return [self._deserialize(trade) for trade in trades]
        except Exception as e:
            logger.error(f"Error getting trade history for {symbol}: {e}")
            return []
    
    async def set_24h_stats(
        self, 
        symbol: str, 
        stats: Dict[str, Any], 
        ttl: int = 300
    ) -> bool:
        """Set 24h statistics for a symbol."""
        key = f"stats24h:{symbol}"
        
        # Add timestamp
        if "timestamp" not in stats:
            stats["timestamp"] = datetime.utcnow().isoformat()
        
        return await self.set(key, stats, ttl)
    
    async def get_24h_stats(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get 24h statistics for a symbol."""
        key = f"stats24h:{symbol}"
        return await self.get(key)
    
    async def set_kline_data(
        self, 
        symbol: str, 
        interval: str, 
        klines: List[Dict[str, Any]], 
        ttl: int = 600
    ) -> bool:
        """Set kline/candlestick data."""
        key = f"klines:{symbol}:{interval}"
        
        data = {
            "symbol": symbol,
            "interval": interval,
            "klines": klines,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.set(key, data, ttl)
    
    async def get_kline_data(
        self, 
        symbol: str, 
        interval: str
    ) -> Optional[Dict[str, Any]]:
        """Get kline/candlestick data."""
        key = f"klines:{symbol}:{interval}"
        return await self.get(key)
    
    async def set_symbol_info(
        self, 
        symbol: str, 
        info: Dict[str, Any], 
        ttl: int = 3600
    ) -> bool:
        """Set symbol information (static data)."""
        key = f"info:{symbol}"
        return await self.set(key, info, ttl)
    
    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information."""
        key = f"info:{symbol}"
        return await self.get(key)
    
    async def get_all_symbols(self) -> List[str]:
        """Get list of all cached symbols."""
        try:
            price_keys = await self.redis.keys(self._make_key("price:*"))
            symbols = []
            for key in price_keys:
                # Extract symbol from key like "market:price:BTCUSDT"
                symbol = key.split(":")[-1]
                symbols.append(symbol)
            return sorted(symbols)
        except Exception as e:
            logger.error(f"Error getting all symbols: {e}")
            return []
    
    async def is_price_fresh(self, symbol: str, max_age_seconds: int = 60) -> bool:
        """Check if cached price is fresh enough."""
        price_data = await self.get_symbol_price(symbol)
        if not price_data or "timestamp" not in price_data:
            return False
        
        try:
            price_time = datetime.fromisoformat(price_data["timestamp"].replace('Z', '+00:00'))
            age = (datetime.utcnow() - price_time.replace(tzinfo=None)).total_seconds()
            return age <= max_age_seconds
        except (ValueError, TypeError):
            return False
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """Clean up expired market data."""
        cleaned = {
            "prices": 0,
            "orderbooks": 0,
            "trades": 0,
            "stats": 0
        }
        
        try:
            # Clean expired price data (older than 5 minutes)
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)
            
            price_keys = await self.redis.keys(self._make_key("price:*"))
            for key in price_keys:
                data = await self.redis.get(key)
                if data:
                    parsed_data = self._deserialize(data)
                    if isinstance(parsed_data, dict) and "timestamp" in parsed_data:
                        try:
                            data_time = datetime.fromisoformat(
                                parsed_data["timestamp"].replace('Z', '+00:00')
                            )
                            if data_time.replace(tzinfo=None) < cutoff_time:
                                await self.redis.delete(key)
                                cleaned["prices"] += 1
                        except (ValueError, TypeError):
                            # Invalid timestamp, delete
                            await self.redis.delete(key)
                            cleaned["prices"] += 1
            
            return cleaned
        except Exception as e:
            logger.error(f"Error cleaning up market data: {e}")
            return cleaned


# Global market data cache instance
market_data_cache = MarketDataCache()