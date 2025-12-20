from decimal import Decimal
from typing import Any, Dict
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
        """
        current_time = int(time.time())
        symbol = market_data.get("symbol")
        
        if current_time - self.last_buy_time >= self.interval_seconds:
            logger.info(f"[DCA] Triggering buy for {symbol}")
            
            # Execute Market Buy
            await self.buy(
                symbol=symbol,
                quantity=self.amount
            )
            
            self.last_buy_time = current_time
