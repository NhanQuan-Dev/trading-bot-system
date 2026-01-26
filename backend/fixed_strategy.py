
import pandas as pd
import pandas_ta as ta
from decimal import Decimal
from trading.strategies.base import StrategyBase
import logging

# Ensure we get the logger
logger = logging.getLogger("dynamic_strategy")

class ScaleInStrategy(StrategyBase):
    """
    Scale-In Strategy (Vectorized - Cách 1):
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
        
        # Pre-calculated data
        self.rsi_values = []
        self.breakout_highs = []
        
        # State
        self.last_trade_idx = None
        self.scaled_in = False  # Track if we already added to position
        self.initial_quantity = None  # Store initial quantity

    def pre_calculate(self, candles, htf_candles=None):
        """Vectorized indicator calculation (Cách 1)"""
        if not candles:
            return
            
        logger.info(f"Starting pre-calculation for {len(candles)} candles...")
        
        # 1. Convert to DataFrame once
        df = pd.DataFrame(candles)
        
        # 2. Calculate RSI for all candles
        rsi_series = ta.rsi(df["close"], length=self.rsi_period)
        self.rsi_values = rsi_series.tolist() # Keep NaNs to handle warmup
        
        # 3. Calculate Rolling Max (Breakout) for all candles
        highs_series = df["close"].rolling(window=self.breakout_lookback).max()
        self.breakout_highs = highs_series.tolist() # Keep NaNs
        
        logger.info(f"Pre-calculation finished. Ready for {len(self.rsi_values)} candles.")

    async def on_tick(self, market_data):
        pass

    def calculate_signal(self, candle, idx, position):
        """
        Calculates signal at a specific index using pre-calculated values.
        Complexity: O(1)
        """
        # Warmup Check (Matches original logic: max(14, 20) = 20)
        warmup = max(self.rsi_period, self.breakout_lookback)
        if idx < warmup - 1:
            return None

        # Data lookup
        if idx >= len(self.rsi_values):
             return None
             
        rsi = self.rsi_values[idx]
        recent_high = self.breakout_highs[idx]
        
        # Skip if indicator is NaN
        if pd.isna(rsi) or pd.isna(recent_high):
            return None

        close_price = float(candle["close"])

        # Entry Cooldown check
        if self.last_trade_idx is not None:
            if idx - self.last_trade_idx < self.cooldown_candles:
                return None

        # ENTRY LOGIC
        if not position:
            self.scaled_in = False
            self.initial_quantity = float(self.quantity)
            
            # RSI Entry
            if rsi < self.rsi_entry:
                self.last_trade_idx = idx
                return {
                    "type": "open_long",
                    "quantity": self.initial_quantity,
                    "metadata": {
                        "reason": "RSI_OVERSOLD",
                        "rsi": round(float(rsi), 2)
                    }
                }

            # Breakout Entry
            if close_price >= recent_high and recent_high > 0:
                self.last_trade_idx = idx
                return {
                    "type": "open_long",
                    "quantity": self.initial_quantity,
                    "metadata": {
                        "reason": "BREAKOUT",
                        "recent_high": round(float(recent_high), 2)
                    }
                }
        
        # SCALE-IN LOGIC
        else:
            avg_entry_price = getattr(position, "avg_entry_price", None)
            
            if not self.scaled_in and avg_entry_price:
                entry_price = float(avg_entry_price)
                price_move_pct = (close_price - entry_price) / entry_price
                
                # Use leverage from config to calculate ROI
                leverage = float(self.config.get("leverage", 1.0))
                current_roi = price_move_pct * leverage * 100
                
                # If ROI reaches 50%, add to position
                if current_roi >= self.scale_in_roi_threshold:
                    self.scaled_in = True
                    logger.info(f"DEBUG_SCALEIN: TRIGGERED at ROI {current_roi}% (idx={idx})")
                    
                    return {
                        "type": "add_long",
                        "quantity": self.initial_quantity,
                        "metadata": {
                            "reason": "SCALE_IN_AT_50PCT_ROI",
                            "roi_pct": round(current_roi, 2)
                        }
                    }

        return None
