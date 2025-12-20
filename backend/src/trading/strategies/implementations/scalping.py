from decimal import Decimal
from typing import Any, Dict, List
import pandas as pd
import pandas_ta as ta
import logging
from ..base import StrategyBase

logger = logging.getLogger(__name__)

class ScalpingStrategy(StrategyBase):
    name = "Scalping"
    description = "Executes multiple high-speed trades to capture small price changes using tight moving average crossovers."

    def __init__(self, exchange, config: Dict[str, Any]):
        super().__init__(exchange, config)
        self.ema_fast = int(config.get("ema_fast", "5"))
        self.ema_slow = int(config.get("ema_slow", "13"))
        self.tp_percentage = float(config.get("take_profit_pct", "0.5")) # 0.5%
        self.sl_percentage = float(config.get("stop_loss_pct", "0.2")) # 0.2%
        self.quantity = Decimal(str(config.get("quantity", "0.001")))
        
        self.history: List[Dict] = []
        self.min_history = self.ema_slow + 5

    async def on_tick(self, market_data: Any):
        symbol = market_data.get("symbol")
        price = float(market_data.get("price"))
        
        # In scalping, efficiency is key. 
        # Here we check if we have an open position to manage TP/SL
        # (This implies we need position tracking in StrategyBase better, but for now we simulate signal)
        
        self.history.append({"close": price})
        if len(self.history) > self.min_history * 2:
            self.history.pop(0)

        if len(self.history) < self.min_history:
            return

        df = pd.DataFrame(self.history)
        df["fast"] = ta.ema(df["close"], length=self.ema_fast)
        df["slow"] = ta.ema(df["close"], length=self.ema_slow)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Fast crossover Slow UP -> Buy
        if (prev["fast"] <= prev["slow"]) and (last["fast"] > last["slow"]):
            logger.info(f"[Scalp] Signal BUY on {symbol} @ {price}")
            await self.buy(symbol, self.quantity)
            # In real world: Place OCO order (TP + SL) immediately
            
        # Fast crossover Slow DOWN -> Sell
        elif (prev["fast"] >= prev["slow"]) and (last["fast"] < last["slow"]):
            logger.info(f"[Scalp] Signal SELL on {symbol} @ {price}")
            await self.sell(symbol, self.quantity)
