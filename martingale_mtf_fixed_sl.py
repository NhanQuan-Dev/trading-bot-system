
import pandas as pd
from decimal import Decimal
from trading.strategies.base import StrategyBase

class MartingaleSmartMultiTimeframeFixedSLStrategy(StrategyBase):
    """
    Martingale Smart Multi-Timeframe Strategy (Fixed SL):
    
    1. Core Logic: Same as 'Martingale Smart Always-In (Fixed SL)'.
    2. MTF Filter: 
       - Uses a higher timeframe (e.g., 1h) Moving Average to filter INITIAL entries.
       - Only enters a new sequence (Base Qty) if direction aligns with HTF Trend.
       - RECOVERY trades (Doubled Qty) ignore the filter to ensure recovery.
       
    3. ROI/SL Logic:
       - New SL = Old TP - 50.0%
       
    Parameters:
       - htf_timeframe: Timeframe for trend filter (e.g., '1h', '4h'). Default: '1h'.
       - htf_ma_period: Period for HTF SMA. Default: 20.
    """
    
    name = "Martingale Smart MTF (Fixed SL)"
    description = "Martingale with HTF Trend Filter and Corrected Step-Up (SL = Old TP - 50%)"
    
    def __init__(self, exchange=None, config=None, on_order=None):
        super().__init__(exchange, config or {}, on_order)
        self.base_qty = Decimal("0.001")
        self.cumulative_loss_qty = Decimal("0")
        self.next_qty = Decimal("0.001")
        
        # State tracking
        self.next_direction = "LONG"
        self.last_pos_active = False
        self.last_entry_price = 0.0
        self.last_side = None
        self.last_qty = Decimal("0")
        self.current_tp_stage = 1
        
        # MTF Config
        self.htf_timeframe = self.config.get("parameters", {}).get("htf_timeframe", "1h")
        self.htf_ma_period = int(self.config.get("parameters", {}).get("htf_ma_period", 20))

    async def on_tick(self, market_data):
        pass

    def calculate_signal(self, candle, idx, position, multi_tf_context=None):
        # Support both signatures for compatibility
        # If multi_tf_context is not passed (older adapter), we fallback or warn?
        # But we are designing this for the new adapter.
        
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

        # 2. ENTRY LOGIC
        if not position:
            
            # --- MTF FILTER LOGIC START ---
            # Only apply filter if starting a new sequence (Base Qty)
            if self.next_qty == self.base_qty and multi_tf_context:
                htf_history = multi_tf_context.history.get(self.htf_timeframe, [])
                
                # We need enough history for MA
                if len(htf_history) >= self.htf_ma_period:
                    # Calculate SMA
                    # Note: htf_history[-1] is the *last closed* candle.
                    closes = [float(c["close"]) for c in htf_history[-self.htf_ma_period:]]
                    sma_value = sum(closes) / len(closes)
                    
                    # Current 1m Close vs HTF SMA
                    # (Using current 1m close as proxy for "Current Price")
                    
                    is_bullish = close_price > sma_value
                    
                    if self.next_direction == "LONG" and not is_bullish:
                        # Trend mismatch, WAIT
                        return None
                    
                    if self.next_direction == "SHORT" and is_bullish:
                        # Trend mismatch, WAIT
                        return None
            # --- MTF FILTER LOGIC END ---

            self.current_tp_stage = 1
            self.last_pos_active = True
            self.last_entry_price = close_price
            self.last_side = self.next_direction
            self.last_qty = self.next_qty
            
            entry_move_pct = 1.0 / leverage
            signal_type = "open_long" if self.next_direction == "LONG" else "open_short"
            
            tp_price = 0.0
            sl_price = 0.0
            
            if self.next_direction == "LONG":
                tp_price = close_price * (1 + entry_move_pct)
                sl_price = close_price * (1 - entry_move_pct)
            else:
                tp_price = close_price * (1 - entry_move_pct)
                sl_price = close_price * (1 + entry_move_pct)

            return {
                "type": signal_type,
                "quantity": float(self.next_qty),
                "take_profit": tp_price,
                "stop_loss": sl_price,
                "metadata": {
                    "reason": f"MARTINGALE_MTF_FIXED_{self.next_direction}",
                    "current_qty": float(self.next_qty),
                    "htf": self.htf_timeframe,
                    "filter_active": (self.next_qty == self.base_qty)
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
            curr_roi_pct = 0.0
            
            if position.is_long():
                target_price = entry_price * (1 + trigger_price_dist_pct)
                if high_price >= target_price:
                    hit_trigger = True
                    curr_roi_pct = ((high_price - entry_price) / entry_price) * leverage * 100
            elif position.is_short():
                target_price = entry_price * (1 - trigger_price_dist_pct)
                if low_price <= target_price:
                    hit_trigger = True
                    curr_roi_pct = ((entry_price - low_price) / entry_price) * leverage * 100

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
                        "reason": f"DYNAMIC_STEP_UP_FIXED_SL_STAGE_{self.current_tp_stage}",
                        "achieved_roi": round(curr_roi_pct, 2),
                        "new_sl_roi": new_sl_roi,
                        "new_tp_roi": new_tp_roi
                    }
                }

        return None
