from decimal import Decimal
from typing import Any, Dict, List
import pandas as pd
import pandas_ta as ta
import logging
from ..base import StrategyBase

logger = logging.getLogger(__name__)

class MeanReversionStrategy(StrategyBase):
    name = "MEAN_REVERSION"
    description = "Assumes high/low prices will return to the average. Buys when oversold (RSI < 30) and sells when overbought (RSI > 70)."

    def __init__(self, exchange, config: Dict[str, Any]):
        super().__init__(exchange, config)
        self.rsi_period = int(config.get("rsi_period", "14"))
        self.rsi_lower = float(config.get("rsi_lower", "30")) # Buy signal
        self.rsi_upper = float(config.get("rsi_upper", "70")) # Sell signal
        self.quantity = Decimal(str(config.get("quantity", "0.001")))
        self.history: List[Dict] = []
        self.min_history = self.rsi_period + 20

    async def on_tick(self, market_data: Any):
        symbol = market_data.get("symbol")
        price = float(market_data.get("price"))
        
        self.history.append({"close": price})
        if len(self.history) > self.min_history * 2:
            self.history.pop(0)

        if len(self.history) < self.min_history:
            return

        df = pd.DataFrame(self.history)
        
        # Calculate RSI
        df["rsi"] = ta.rsi(df["close"], length=self.rsi_period)
        
        current_rsi = df.iloc[-1]["rsi"]
        
        if current_rsi < self.rsi_lower:
            logger.info(f"[MeanRev] RSI Oversold ({current_rsi:.2f} < {self.rsi_lower}). BUY.")
            await self.buy(symbol, self.quantity)
            
        elif current_rsi > self.rsi_upper:
            logger.info(f"[MeanRev] RSI Overbought ({current_rsi:.2f} > {self.rsi_upper}). SELL.")
            await self.sell(symbol, self.quantity)
