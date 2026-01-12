from decimal import Decimal
from typing import Any, Dict, Optional
import time
import logging
from ..base import StrategyBase

logger = logging.getLogger(__name__)

class DCAStrategy(StrategyBase):
    name = "DCA"
    description = "Reduces the impact of volatility by buying a fixed amount of asset at regular intervals, regardless of price."

    def __init__(self, exchange, config: Dict[str, Any]):
        super().__init__(exchange, config)
        self.amount = Decimal(str(config.get("amount", "10")))
        self.interval_seconds = int(config.get("interval_seconds", "3600")) # e.g. 1 hour
        self.last_buy_time = 0

    async def on_tick(self, market_data: Any):
        """
        DCA Logic: Buy if enough time has passed.
        
        Args:
            market_data: List of klines/candles from exchange (OHLCV)
        """
        current_time = int(time.time())
        # Symbol is in self.config, not market_data list
        symbol = self.config.get("symbol")
        
        if current_time - self.last_buy_time >= self.interval_seconds:
            logger.info(f"[DCA] Triggering buy for {symbol}")
            
            # Execute Market Buy
            try:
                await self.buy(
                    symbol=symbol,
                    quantity=self.amount
                )
                self.last_buy_time = current_time
            except Exception as e:
                logger.error(f"[DCA] Buy failed: {e}")

    def calculate_signal(self, candle: Dict, idx: int, position: Any) -> Optional[Dict]:
        """
        Backtest-compatible signal calculation.
        Uses candle timestamp instead of system time.
        """
        # Parse timestamp (handle various formats if needed, assuming ISO string or int)
        ts = candle.get('timestamp')
        if isinstance(ts, str):
            # Simple ISO parse if needed, but usually handled by engine data loader?
            # Or assume engine passes datetime? 
            # Engine passes whatever data_feed returns.
            # Let's assume iso format string from typical backtest data
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                current_time = dt.timestamp()
            except:
                current_time = 0
        elif isinstance(ts, (int, float)):
             current_time = float(ts)
        else:
             from datetime import datetime
             if isinstance(ts, datetime):
                 current_time = ts.timestamp()
             else:
                 current_time = 0

        # Check if enough time passed
        if current_time - self.last_buy_time >= self.interval_seconds:
            self.last_buy_time = current_time
            
            # Metadata for the 'Eye' icon feature
            entry_reason = {
                "strategy": "DCA",
                "interval_seconds": self.interval_seconds,
                "amount": float(self.amount),
                "trigger_time": ts,
                "reason": "Time Interval Reached"
            }
            
            # In DCA, we typically just Buy (Long)
            # If position exists, 'add_long' might be better, but 'open_long' works if flat
            # The engine treats 'open_long' as valid even if position exists?
            # No, engine checks `if not self.current_position`.
            # If we want to ADD to position (DCA), we should use 'add_long' if position exists.
            
            signal_type = "add_long" if position else "open_long"
            
            return {
                "type": signal_type,
                "quantity": float(self.amount), # Optional override
                "metadata": entry_reason
            }
            
        return None
