"""Market data service implementation."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

from ..exchange.binance_adapter import BinanceAdapter

logger = logging.getLogger(__name__)

class MarketDataService:
    """Service to fetch market data."""
    
    def __init__(self, exchange_adapter: BinanceAdapter):
        self.adapter = exchange_adapter
    
    async def get_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1500
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical candles from exchange.
        
        Args:
            symbol: Trading symbol (e.g. BTC/USDT or BTCUSDT)
            timeframe: Candle timeframe (e.g. 1h)
            start_date: Start datetime
            end_date: End datetime
            limit: Max candles to fetch
            
        Returns:
            List of dictionaries containing candle data:
            {
                "timestamp": datetime,
                "open": Decimal,
                "high": Decimal,
                "low": Decimal,
                "close": Decimal,
                "volume": Decimal
            }
        """
        # Normalize symbol format for Binance (remove "/")
        # Convert "BTC/USDT" to "BTCUSDT"
        normalized_symbol = symbol.replace("/", "")
        
        # Convert datetimes to milliseconds timestamp
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        try:
            # Fetch klines from adapter
            raw_klines = await self.adapter.get_klines(
                symbol=normalized_symbol,
                interval=timeframe,
                start_time=start_ts,
                end_time=end_ts,
                limit=limit
            )
            
            # Format data
            candles = []
            for k in raw_klines:
                # Binance Futures Kline format:
                # [
                #   0: Open time,
                #   1: Open,
                #   2: High,
                #   3: Low,
                #   4: Close,
                #   5: Volume,
                #   ...
                # ]
                candles.append({
                    "timestamp": datetime.fromtimestamp(k[0] / 1000),
                    "open": Decimal(k[1]),
                    "high": Decimal(k[2]),
                    "low": Decimal(k[3]),
                    "close": Decimal(k[4]),
                    "volume": Decimal(k[5]),
                })
                
            logger.info(f"Fetched {len(candles)} candles for {symbol} ({normalized_symbol})")
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching historical candles for {symbol}: {e}")
            raise
