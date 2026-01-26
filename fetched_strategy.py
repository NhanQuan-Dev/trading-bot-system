
import pandas as pd
import pandas_ta as ta
from decimal import Decimal
from trading.strategies.base import StrategyBase
import logging

# Ensure we get the logger
logger = logging.getLogger("dynamic_strategy")

class ScaleInStrategy(StrategyBase):
    """
    Scale-In Strategy:
    - Entry: RSI Oversold or Breakout
    - Initial: TP=100% ROI, NO SL
    - When profit reaches 50% ROI: Add to position with same quantity as initial
    """
    
    name = "Scale-In at 50% TP"
    description = "RSI/Breakout with scale-in at 50% ROI profit, no stop loss"
    
    def __init__(self, exchange=None, config=None, on_order=None):
        super().__init__(exchange, config or {}, on_order)
        self.rsi_period = 14
        self.rsi_entry = 30
        self.breakout_lookback = 20
        self.cooldown_candles = 3
        self.quantity = Decimal("0.001")
        
        # TP ROI percentage (no SL)
        self.take_profit_roi = 100.0  # 100% ROI
        self.scale_in_roi_threshold = 50.0  # 50% ROI - trigger point for adding
        
        # State
        self.closes = []
        self.last_trade_idx = None
        self.scaled_in = False  # Track if we already added to position
        self.initial_quantity = None  # Store initial quantity

    async def on_tick(self, market_data):
        pass

    def calculate_signal(self, candle, idx, position):
        close_price = float(candle["close"])
        self.closes.append(close_price)

        if len(self.closes) < max(self.rsi_period, self.breakout_lookback):
            return None

        if self.last_trade_idx is not None:
            if idx - self.last_trade_idx < self.cooldown_candles:
                return None

        rsi_series = ta.rsi(pd.Series(self.closes), length=self.rsi_period)
        rsi = float(rsi_series.iloc[-1])
        recent_high = max(self.closes[-self.breakout_lookback:])

        # ENTRY LOGIC
        if not position:
            self.scaled_in = False
            self.initial_quantity = float(self.quantity)
            
            if rsi < self.rsi_entry:
                self.last_trade_idx = idx
                return {
                    "type": "open_long",
                    "quantity": self.initial_quantity,
                    # "take_profit_percent": self.take_profit_roi, # REVERTED
                    "metadata": {
                        "reason": "RSI_OVERSOLD",
                        "rsi": round(rsi, 2)
                    }
                }

            if close_price >= recent_high:
                self.last_trade_idx = idx
                return {
                    "type": "open_long",
                    "quantity": self.initial_quantity,
                    # "take_profit_percent": self.take_profit_roi, # REVERTED
                    "metadata": {
                        "reason": "BREAKOUT",
                        "recent_high": recent_high
                    }
                }
        
        # SCALE-IN LOGIC
        else:
            if not self.scaled_in and hasattr(position, "avg_entry_price"):
                entry_price = float(position.avg_entry_price)
                price_move_pct = (close_price - entry_price) / entry_price
                
                # Use leverage from config to calculate ROI
                leverage = float(self.config.get("leverage", 1.0))
                current_roi = price_move_pct * leverage * 100
                
                # Debug logging - LIMIT LOGGING FREQUENCY
                if idx % 5 == 0:
                     logger.info(f"DEBUG_SCALEIN: ID={idx}, Lev={leverage}, ROI={current_roi:.2f}%, Thresh={self.scale_in_roi_threshold}, Price={close_price}, Entry={entry_price}")

                # If ROI reaches 50%, add to position
                if current_roi >= self.scale_in_roi_threshold:
                    self.scaled_in = True
                    logger.info(f"DEBUG_SCALEIN: TRIGGERED at ROI {current_roi}%")
                    
                    return {
                        "type": "add_long",
                        "quantity": self.initial_quantity,
                        "metadata": {
                            "reason": "SCALE_IN_AT_50PCT_ROI",
                            "roi_pct": round(current_roi, 2)
                        }
                    }

        return None
