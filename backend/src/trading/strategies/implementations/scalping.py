from decimal import Decimal
from typing import Any, Dict, List, Optional
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

    def calculate_signal(self, candle: Dict, idx: int, position: Any) -> Optional[Dict]:
        """Backtest signal calculation."""
        # 1. Update History
        close_price = float(candle['close'])
        self.history.append({"close": close_price})
        
        # Keep history buffer reasonable
        if len(self.history) > self.min_history * 5:
            self.history.pop(0)

        # 2. Check Data Sufficiency
        if len(self.history) < self.min_history:
            return None

        # 3. Calculate Indicators
        # We re-calculate on every tick for simplicity in this template. 
        # For production, optimize to only calc last few.
        df = pd.DataFrame(self.history)
        df["fast"] = ta.ema(df["close"], length=self.ema_fast)
        df["slow"] = ta.ema(df["close"], length=self.ema_slow)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        fast_val = float(last["fast"])
        slow_val = float(last["slow"])
        
        # 4. Logic
        signal = None
        
        # Cross UP -> LONG
        if (prev["fast"] <= prev["slow"]) and (last["fast"] > last["slow"]):
            signal = "open_long"
            
        # Cross DOWN -> SHORT (or close long)
        elif (prev["fast"] >= prev["slow"]) and (last["fast"] < last["slow"]):
            # If we are long, we flip to short or just close? 
            # Scalping usually flips.
            signal = "open_short" 
            if position:
                # If we have a position, we should check direction
                # But for simple scalping, let's just emit the directional signal
                # The engine handles "open_short" when Long by ignoring or we can use "flip_short"
                signal = "flip_short" if position.direction == "LONG" else "open_short"

        if signal:
            return {
                "type": signal,
                "quantity": float(self.quantity),
                "stop_loss": self.sl_percentage,
                "take_profit": self.tp_percentage,
                "metadata": {
                    "strategy": "Scalping EMA",
                    "fast_ema": fast_val,
                    "slow_ema": slow_val,
                    "crossover": "UP" if signal in ("open_long", "flip_long") else "DOWN"
                }
            }
            
        return None
