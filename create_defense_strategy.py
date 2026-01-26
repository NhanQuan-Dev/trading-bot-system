
import psycopg2
import uuid
import json

def create_margin_defense_strategy():
    strategy_id = str(uuid.uuid4())
    name = "Martingale RSI 1h Margin Defense"
    description = "Martingale 1h RSI strategy with Margin Defense: Doubles margin and moves SL to -200% when ROI hits -70%."
    
    code_content = """
import pandas as pd
import pandas_ta as ta
import numpy as np
from decimal import Decimal
from trading.strategies.base import StrategyBase
import logging
from typing import List, Dict, Any, Optional

# Ensure we get the logger
logger = logging.getLogger("dynamic_strategy")

class MartingaleRSI1hMarginDefense(StrategyBase):
    name = "Martingale RSI 1h Margin Defense"
    description = "Always-In logic with Martingale sizing, Step-Up SL, and 1h RSI (35-65) Filtered entry. Includes Margin Defense at -70% ROI."
    
    @property
    def timeframe_mode(self) -> str:
        return "multi"

    @property
    def required_timeframes(self) -> List[str]:
        return ["1h"]
    
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
        self.defense_triggered = False
        
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
            df_1h['rsi'] = ta.rsi(df_1h['close'], length=self.rsi_period)
            
            # Create a map for fast lookup
            for i, row in df_1h.iterrows():
                if not np.isnan(row['rsi']):
                    self.rsi_1h_map[int(row['timestamp'].timestamp())] = row['rsi']
            
            logger.info(f"Pre-calculated RSI for {len(self.rsi_1h_map)} 1h candles.")

    def on_tick(self, candle: Dict[str, Any], position: Optional[Any] = None) -> None:
        pass

    def calculate_signal(self, candle: Dict[str, Any], candle_idx: int, position: Optional[Any] = None, **kwargs) -> Optional[Dict[str, Any]]:
        current_price = float(candle['close'])
        high_price = float(candle.get('high', current_price))
        low_price = float(candle.get('low', current_price))
        timestamp = candle['timestamp']
        
        # Get leverage from config or default to 10
        leverage = float(getattr(self.exchange, 'config', {}).leverage if hasattr(self.exchange, 'config') else 10)

        # 1. POSITION CLOSURE LOGIC & RESET
        if not position and self.last_pos_active:
            pnl = 0.0
            if self.last_side == "LONG":
                pnl = (current_price - self.last_entry_price) * float(self.last_qty)
            else:
                pnl = (self.last_entry_price - current_price) * float(self.last_qty)
            
            if pnl < 0:
                self.cumulative_loss_qty += self.last_qty
                self.next_qty = self.base_qty + self.cumulative_loss_qty
                self.next_direction = self.last_side # Re-enter same direction
            else:
                self.cumulative_loss_qty = Decimal("0")
                self.next_qty = self.base_qty
                self.next_direction = "SHORT" if self.last_side == "LONG" else "LONG"
            
            self.last_pos_active = False
            self.current_tp_stage = 1
            self.defense_triggered = False # Reset defense for next position
            logger.info(f"Position closed. PnL: {pnl}. Next Qty: {self.next_qty}, Next Direction: {self.next_direction}")

        # 2. MARGIN DEFENSE LOGIC
        if position:
            entry_price = float(position.avg_entry_price)
            qty = float(position.quantity)
            
            # Calculate current ROI
            if position.is_long():
                pnl_per_unit = current_price - entry_price
            else:
                pnl_per_unit = entry_price - current_price
            
            # ROI = (PnL / Margin) * 100 where Margin = (Entry * Qty) / Leverage
            # Simplified: ROI = (pnl_per_unit / entry_price) * leverage * 100
            roi = (pnl_per_unit / entry_price) * leverage * 100
            
            if roi <= -70.0 and not self.defense_triggered:
                self.defense_triggered = True
                # Double margin: add amount equal to current initial margin
                initial_margin = (Decimal(str(entry_price)) * Decimal(str(qty))) / Decimal(str(leverage))
                
                # New SL at -200% ROI
                # Price = Entry * (1 - 2.0/Lev) for Long
                new_sl_roi = -200.0
                if position.is_long():
                    new_sl_price = entry_price * (1 + (new_sl_roi / 100.0 / leverage))
                else:
                    new_sl_price = entry_price * (1 - (new_sl_roi / 100.0 / leverage))
                
                logger.info(f"MARGIN DEFENSE TRIGGERED! ROI: {roi}%. Adding Margin: {initial_margin}, New SL: {new_sl_price}")
                
                return {
                    "type": "update_margin",
                    "amount": float(initial_margin),
                    "stop_loss": float(new_sl_price),
                    "metadata": {
                        "reason": "MARGIN_DEFENSE_TRIGGERED",
                        "roi_at_trigger": round(roi, 2)
                    }
                }

        # 3. ENTRY LOGIC
        if not position:
            # Check 1h RSI Filter
            ctx = kwargs.get('multi_tf_context')
            if not ctx or '1h' not in ctx.current_candles or ctx.current_candles['1h'] is None:
                return None
                
            htf_candle = ctx.current_candles['1h']
            htf_ts = int(htf_candle['timestamp'].timestamp())
            rsi_1h = self.rsi_1h_map.get(htf_ts)
            
            if rsi_1h is None or not (self.rsi_min <= rsi_1h <= self.rsi_max):
                return None
            
            # Entry
            self.last_pos_active = True
            self.last_entry_price = current_price
            self.last_side = self.next_direction
            self.last_qty = self.next_qty
            
            entry_move_pct = 1.0 / leverage
            tp_price = current_price * (1 + entry_move_pct) if self.next_direction == "LONG" else current_price * (1 - entry_move_pct)
            sl_price = current_price * (1 - entry_move_pct) if self.next_direction == "LONG" else current_price * (1 + entry_move_pct)
            
            return {
                "type": "open_" + self.next_direction.lower(),
                "quantity": float(self.next_qty),
                "take_profit": tp_price,
                "stop_loss": sl_price,
                "metadata": {
                    "reason": f"MARTINGALE_RSI_FILTER_{self.next_direction}",
                    "rsi_1h": round(rsi_1h, 2)
                }
            }
        
        # 4. STEP-UP SL
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

    conn = psycopg2.connect("postgresql://qwe:qwe@localhost:5432/trading_bot")
    cur = conn.cursor()
    
    cur.execute(
        "INSERT INTO strategies (id, name, description, code_content, is_active) VALUES (%s, %s, %s, %s, %s)",
        (strategy_id, name, description, code_content, True)
    )
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"Strategy {name} created with ID: {strategy_id}")

if __name__ == "__main__":
    create_margin_defense_strategy()
