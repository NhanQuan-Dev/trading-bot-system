
import asyncio
import os
import sys
from sqlalchemy import text

# Add backend/src to path
sys.path.insert(0, os.path.abspath("backend/src"))

from trading.infrastructure.persistence.database import get_db_context

async def fix_strategy():
    code = """
import pandas as pd
import pandas_ta as ta
import numpy as np
from decimal import Decimal
from trading.strategies.base import StrategyBase
import logging
from typing import List, Dict, Any, Optional

# Ensure we get the logger
logger = logging.getLogger("dynamic_strategy")

class MartingaleRSI15mFilter(StrategyBase):
    name = "Martingale RSI 15m Filter"
    description = "Always-In logic with Martingale sizing, Step-Up SL, and 15m RSI (35-65) Filtered entry."
    
    @property
    def timeframe_mode(self) -> str:
        return "multi"

    @property
    def required_timeframes(self) -> List[str]:
        return ["15m"]
    
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
        
        self.rsi_period = int(self.params.get("rsi_period", 14))
        self.rsi_min = float(self.params.get("rsi_min", 35))
        self.rsi_max = float(self.params.get("rsi_max", 65))
        
        # Pre-calculated filters (Vectorized Maps)
        self.rsi_15m_map = {}

    def pre_calculate(self, candles: List[Dict[str, Any]], htf_candles: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> None:
        if not htf_candles:
            logger.warning("No HTF candles provided for 15m RSI pre-calculation!")
            return
            
        logger.info(f"Starting 15m RSI pre-calculation...")
        
        if "15m" in htf_candles:
            df_15m = pd.DataFrame(htf_candles["15m"])
            rsi_15m = ta.rsi(df_15m["close"], length=self.rsi_period)
            self.rsi_15m_map = {int(ts.timestamp()): val for ts, val in zip(df_15m["timestamp"], rsi_15m)}

        logger.info(f"15m RSI Pre-calculation finished. Filter map prepared.")

    async def on_tick(self, market_data: Any):
        \"\"\"Live trading tick handler (not used in backtest)\"\"\"
        pass

    def calculate_signal(self, candle, idx, position, multi_tf_context=None):
        close_price = float(candle["close"])
        high_price = float(candle["high"])
        low_price = float(candle["low"])
        leverage = float(self.config.get("leverage", 1))

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

        if not position:
            if not multi_tf_context or not multi_tf_context.current_candles:
                return None
            last_15m = multi_tf_context.current_candles.get("15m")
            if not last_15m: return None
            
            ts_15m = int(last_15m["timestamp"].timestamp())
            rsi_15m = self.rsi_15m_map.get(ts_15m)
            if rsi_15m is None or pd.isna(rsi_15m): return None
            
            is_neutral = (rsi_15m >= self.rsi_min) and (rsi_15m <= self.rsi_max)
            if not is_neutral: return None
            
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
                    "reason": f"MARTINGALE_RSI_FILTER_{self.next_direction}",
                    "current_qty": float(self.next_qty),
                    "rsi_15m": round(rsi_15m, 2)
                }
            }
        else:
            if not hasattr(self, "current_tp_stage"): self.current_tp_stage = 1
            entry_price = float(position.avg_entry_price)
            trigger_roi_pct = (self.current_tp_stage * 100) - 10
            trigger_price_dist_pct = (trigger_roi_pct / 100.0) / leverage
            hit_trigger = False
            if position.is_long():
                target_price = entry_price * (1 + trigger_price_dist_pct)
                if high_price >= target_price: hit_trigger = True
            elif position.is_short():
                target_price = entry_price * (1 - trigger_price_dist_pct)
                if low_price <= target_price: hit_trigger = True
            if hit_trigger:
                old_tp_roi = self.current_tp_stage * 100
                new_sl_roi = old_tp_roi - 50.0 
                new_tp_roi = old_tp_roi + 100.0
                new_sl_price = entry_price * (1 + (new_sl_roi / 100.0 / leverage)) if position.is_long() else entry_price * (1 - (new_sl_roi / 100.0 / leverage))
                new_tp_price = entry_price * (1 + (new_tp_roi / 100.0 / leverage)) if position.is_long() else entry_price * (1 - (new_tp_roi / 100.0 / leverage))
                self.current_tp_stage += 1
                return {
                    "type": "update_levels",
                    "stop_loss": new_sl_price, "take_profit": new_tp_price,
                    "metadata": {"reason": f"DYNAMIC_STEP_UP_STAGE_{self.current_tp_stage}", "new_sl_roi": new_sl_roi, "new_tp_roi": new_tp_roi}
                }
        return None
"""
    async with get_db_context() as session:
        await session.execute(
            text("UPDATE strategies SET code_content = :code WHERE name = :name"),
            {"code": code, "name": "Martingale RSI 15m Filter"}
        )
        await session.commit()
    print("Strategy fixed successfully.")

if __name__ == "__main__":
    asyncio.run(fix_strategy())
