
import pandas as pd
import pandas_ta as ta
import numpy as np
from decimal import Decimal
from trading.strategies.base import StrategyBase
import logging
from typing import List, Dict, Any, Optional

# Ensure we get the logger
logger = logging.getLogger("dynamic_strategy")

class MartingaleSmartMTF(StrategyBase):
    name = "Martingale Smart MTF (Fixed SL)"
    description = "Always-In logic with Martingale sizing, Step-Up SL, and 1h/4h Trend Filtered entry (Vectorized)."
    
    @property
    def timeframe_mode(self) -> str:
        return "multi"

    @property
    def required_timeframes(self) -> List[str]:
        return ["1h", "4h"]
    
    def __init__(self, exchange=None, config=None, on_order=None):
        super().__init__(exchange, config or {}, on_order)
        self.params = config.get("parameters", {})
        self.base_qty = Decimal(str(self.params.get("base_order_size", "0.001")))
        self.cumulative_loss_qty = Decimal("0")
        self.next_qty = self.base_qty
        
        # State tracking
        self.next_direction = "LONG"
        self.last_pos_active = False
        self.last_entry_price = 0.0
        self.last_side = None
        self.last_qty = Decimal("0")
        self.current_tp_stage = 1
        
        self.trend_ma_period_4h = int(self.params.get("trend_ma_period_4h", 20))
        self.trend_ma_period_1h = int(self.params.get("trend_ma_period_1h", 10))
        
        # Pre-calculated filters (Vectorized Maps)
        self.ma_4h_map = {}
        self.ma_1h_map = {}
        self.closes_4h_map = {}
        self.closes_1h_map = {}

    def pre_calculate(self, candles: List[Dict[str, Any]], htf_candles: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> None:
        """Vectorized indicator calculation for MTF (Cách 1)"""
        if not htf_candles:
            logger.warning("No HTF candles provided for MTF pre-calculation!")
            return
            
        logger.info(f"Starting MTF pre-calculation...")
        
        # 1. 4H Trend Indicators
        if "4h" in htf_candles:
            df_4h = pd.DataFrame(htf_candles["4h"])
            # SMA using pandas_ta
            ma_4h = ta.sma(df_4h["close"], length=self.trend_ma_period_4h)
            # Create timestamp-indexed maps for O(1) lookup
            self.ma_4h_map = {int(ts.timestamp()): val for ts, val in zip(df_4h["timestamp"], ma_4h)}
            self.closes_4h_map = {int(ts.timestamp()): val for ts, val in zip(df_4h["timestamp"], df_4h["close"])}
            
        # 2. 1H Trend Indicators
        if "1h" in htf_candles:
            df_1h = pd.DataFrame(htf_candles["1h"])
            ma_1h = ta.sma(df_1h["close"], length=self.trend_ma_period_1h)
            self.ma_1h_map = {int(ts.timestamp()): val for ts, val in zip(df_1h["timestamp"], ma_1h)}
            self.closes_1h_map = {int(ts.timestamp()): val for ts, val in zip(df_1h["timestamp"], df_1h["close"])}

        logger.info(f"MTF Pre-calculation finished. Filter maps prepared.")

    async def on_tick(self, market_data):
        pass

    def calculate_signal(self, candle, idx, position, multi_tf_context=None):
        close_price = float(candle["close"])
        high_price = float(candle["high"])
        low_price = float(candle["low"])
        leverage = float(self.config.get("leverage", 1))

        # 1. POSITION CLOSURE LOGIC - UPDATE SIZING & DIRECTION
        if not position and self.last_pos_active:
            is_win = (close_price > self.last_entry_price) if self.last_side == "LONG" else (close_price < self.last_entry_price)
            
            if is_win:
                self.cumulative_loss_qty = Decimal("0")
                self.next_qty = self.base_qty
                self.next_direction = self.last_side
            else:
                self.cumulative_loss_qty += self.last_qty
                self.next_qty = self.cumulative_loss_qty * Decimal("2")
                self.next_direction = "SHORT" if self.last_side == "LONG" else "LONG"
            
            self.last_pos_active = False

        # 2. ENTRY LOGIC: Always-In + MTF FILTER
        if not position:
            if not multi_tf_context or not multi_tf_context.current_candles:
                return None
                
            last_4h = multi_tf_context.current_candles.get("4h")
            last_1h = multi_tf_context.current_candles.get("1h")
            
            if not last_4h or not last_1h:
                return None
                
            # VECTORIZED LOOKUP (O(1)) instead of rolling mean in loop
            ts_4h = int(last_4h["timestamp"].timestamp())
            ts_1h = int(last_1h["timestamp"].timestamp())
            
            ma_4h = self.ma_4h_map.get(ts_4h)
            close_4h = self.closes_4h_map.get(ts_4h)
            
            ma_1h = self.ma_1h_map.get(ts_1h)
            close_1h = self.closes_1h_map.get(ts_1h)
            
            if ma_4h is None or ma_1h is None or pd.isna(ma_4h) or pd.isna(ma_1h):
                return None
            
            # Entry condition: Trend must align with next_direction
            is_bullish = (close_4h > ma_4h) and (close_1h > ma_1h)
            is_bearish = (close_4h < ma_4h) and (close_1h < ma_1h)
            
            can_entry = False
            if self.next_direction == "LONG" and is_bullish:
                can_entry = True
            elif self.next_direction == "SHORT" and is_bearish:
                can_entry = True
                
            if not can_entry:
                return None

            # Proceed with Entry
            self.current_tp_stage = 1
            self.last_pos_active = True
            self.last_entry_price = close_price
            self.last_side = self.next_direction
            self.last_qty = self.next_qty
            
            entry_move_pct = 1.0 / leverage
            signal_type = "open_long" if self.next_direction == "LONG" else "open_short"
            
            tp_price = close_price * (1 + entry_move_pct) if self.next_direction == "LONG" else close_price * (1 - entry_move_pct)
            sl_price = close_price * (1 - entry_move_pct) if self.next_direction == "LONG" else close_price * (1 + entry_move_pct)

            return {
                "type": signal_type,
                "quantity": float(self.next_qty),
                "take_profit": tp_price,
                "stop_loss": sl_price,
                "metadata": {
                    "reason": f"MARTINGALE_MTF_ALIGN_{self.next_direction}",
                    "current_qty": float(self.next_qty),
                    "ma_4h": round(ma_4h, 2),
                    "ma_1h": round(ma_1h, 2)
                }
            }
        
        # 3. FIXED DYNAMIC SL ADJUSTMENT LOGIC (Step-Up)
        else:
            if not hasattr(self, "current_tp_stage"):
                self.current_tp_stage = 1
            
            entry_price = float(position.avg_entry_price)
            trigger_roi_pct = (self.current_tp_stage * 100) - 10
            trigger_price_dist_pct = (trigger_roi_pct / 100.0) / leverage
            
            hit_trigger = False
            
            if position.is_long():
                target_price = entry_price * (1 + trigger_price_dist_pct)
                if high_price >= target_price:
                    hit_trigger = True
            elif position.is_short():
                target_price = entry_price * (1 - trigger_price_dist_pct)
                if low_price <= target_price:
                    hit_trigger = True

            if hit_trigger:
                old_tp_roi = self.current_tp_stage * 100
                new_sl_roi = old_tp_roi - 50.0 
                new_tp_roi = old_tp_roi + 100.0
                
                new_sl_price = 0.0
                new_tp_price = 0.0
                
                if position.is_long():
                    new_sl_price = entry_price * (1 + (new_sl_roi / 100.0 / leverage))
                    new_tp_price = entry_price * (1 + (new_tp_roi / 100.0 / leverage))
                elif position.is_short():
                    new_sl_price = entry_price * (1 - (new_sl_roi / 100.0 / leverage))
                    new_tp_price = entry_price * (1 - (new_tp_roi / 100.0 / leverage))
                
                self.current_tp_stage += 1
                
                return {
                    "type": "update_levels",
                    "stop_loss": new_sl_price,
                    "take_profit": new_tp_price,
                    "metadata": {
                        "reason": f"DYNAMIC_STEP_UP_STAGE_{self.current_tp_stage}",
                        "new_sl_roi": new_sl_roi,
                        "new_tp_roi": new_tp_roi
                    }
                }

        return None
