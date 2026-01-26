
import asyncio
import os
import sys
from sqlalchemy import text

# Add backend/src to path
sys.path.insert(0, os.path.abspath("backend/src"))

from trading.infrastructure.persistence.database import get_db_context

async def save_1h_strategy():
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

class MartingaleRSI1hFilter(StrategyBase):
    name = "Martingale RSI 1h Filter"
    description = "Always-In logic with Martingale sizing, Step-Up SL, and 1h RSI (35-65) Filtered entry."
    
    @property
    def timeframe_mode(self) -> str:
        return "multi"

    @property
    def required_timeframes(self) -> List[str]:
        return ["1h"]
    
    def __init__(self, exchange=None, config=None, on_order=None):
        super().__init__(exchange, config or {}, on_order)
        self.params = config.get("parameters", {})\n        self.base_qty = Decimal(str(self.params.get("base_order_size", "0.001")))
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
        self.rsi_1h_map = {}

    def pre_calculate(self, candles: List[Dict[str, Any]], htf_candles: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> None:
        if not htf_candles:
            logger.warning("No HTF candles provided for 1h RSI pre-calculation!")
            return
            
        logger.info(f"Starting 1h RSI pre-calculation...")
        
        if "1h" in htf_candles:
            df_1h = pd.DataFrame(htf_candles["1h"])
            rsi_1h = ta.rsi(df_1h["close"], length=self.rsi_period)
            self.rsi_1h_map = {int(ts.timestamp()): val for ts, val in zip(df_1h["timestamp"], rsi_1h)}

        logger.info(f"1h RSI Pre-calculation finished. Filter map prepared.")

    async def on_tick(self, market_data: Any):
        \"\"\"Live trading tick handler (not used in backtest)\"\"\"
        pass

    def calculate_signal(self, candle, idx, position, multi_tf_context=None):
        close_price = float(candle["close"])
        high_price = float(candle["high"])
        low_price = float(candle["low"])
        leverage = float(self.config.get("leverage", 1))

        # 1. POSITION CLOSURE LOGIC
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

        # 2. ENTRY LOGIC
        if not position:
            if not multi_tf_context or not multi_tf_context.current_candles:
                return None
            last_1h = multi_tf_context.current_candles.get("1h")
            if not last_1h: return None
            
            ts_1h = int(last_1h["timestamp"].timestamp())
            rsi_1h = self.rsi_1h_map.get(ts_1h)
            
            if rsi_1h is None or pd.isna(rsi_1h): return None
            
            # RSI Filter Condition (35-65)
            is_neutral = (rsi_1h >= self.rsi_min) and (rsi_1h <= self.rsi_max)
            
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
                    "rsi_1h": round(rsi_1h, 2)
                }
            }
        
        # 3. STEP-UP SL
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
        # Check if already exists
        result = await session.execute(text("SELECT id FROM strategies WHERE name = :name"), {"name": "Martingale RSI 1h Filter"})
        existing = result.fetchone()
        
        if existing:
            await session.execute(
                text("UPDATE strategies SET code_content = :code WHERE name = :name"),
                {"code": code, "name": "Martingale RSI 1h Filter"}
            )
        else:
            await session.execute(
                text("INSERT INTO strategies (id, user_id, name, strategy_type, description, parameters, code_content, is_active, created_at, updated_at) "
                     "VALUES (gen_random_uuid(), '5330ceed-d8e9-4bc7-a11c-c4e3487802b1', :name, 'CUSTOM', :desc, :params, :code, true, NOW(), NOW())"),
                {
                    "name": "Martingale RSI 1h Filter",
                    "desc": "Martingale sizing with Step-Up SL and 1h RSI (35-65) entry filter.",
                    "params": '{"base_order_size": "0.001", "rsi_period": 14, "rsi_min": 35, "rsi_max": 65}',
                    "code": code
                }
            )
        await session.commit()
    print("Strategy Martingale RSI 1h Filter saved successfully.")

if __name__ == "__main__":
    asyncio.run(save_1h_strategy())
