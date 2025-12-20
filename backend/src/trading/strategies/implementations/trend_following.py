from decimal import Decimal
from typing import Any, Dict, List
import pandas as pd
import pandas_ta as ta
import logging
from ..base import StrategyBase

logger = logging.getLogger(__name__)

class TrendFollowingStrategy(StrategyBase):
    name = "Trend Following"
    description = "Identifies and follows market momentum. Buys when the trend is up (Golden Cross) and sells when it reverses."

    def __init__(self, exchange, config: Dict[str, Any]):
        super().__init__(exchange, config)
        self.fast_period = int(config.get("fast_period", "50"))
        self.slow_period = int(config.get("slow_period", "200"))
        self.quantity = Decimal(str(config.get("quantity", "0.001")))
        # Need history to calculate indicators
        self.history: List[Dict] = [] 
        self.min_history = self.slow_period + 10

    async def on_tick(self, market_data: Any):
        """
        Trend Following Logic: Golden Cross / Death Cross
        """
        symbol = market_data.get("symbol")
        price = float(market_data.get("price"))
        
        # Append to history (simplified: assuming tick is a close price for this example)
        # In prod, we'd use kline websocket updates
        self.history.append({"close": price})
        
        # Keep buffer manageable
        if len(self.history) > self.min_history * 2:
            self.history.pop(0)

        if len(self.history) < self.min_history:
            return

        # Create DataFrame
        df = pd.DataFrame(self.history)
        
        # Calculate Indicators
        df["fast_ma"] = ta.sma(df["close"], length=self.fast_period)
        df["slow_ma"] = ta.sma(df["close"], length=self.slow_period)
        
        # Get last two rows to check crossover
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Check Crossover
        crossover_up = (prev_row["fast_ma"] <= prev_row["slow_ma"]) and (last_row["fast_ma"] > last_row["slow_ma"])
        crossover_down = (prev_row["fast_ma"] >= prev_row["slow_ma"]) and (last_row["fast_ma"] < last_row["slow_ma"])
        
        if crossover_up:
            logger.info(f"[Trend] Golden Cross detected on {symbol}. BUY.")
            await self.buy(symbol, self.quantity)
            
        elif crossover_down:
            logger.info(f"[Trend] Death Cross detected on {symbol}. SELL.")
            await self.sell(symbol, self.quantity)
