
import pandas as pd
import pandas_ta as ta
import asyncio
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

# Add backend/src to path
sys.path.insert(0, os.path.abspath("backend/src"))

from trading.infrastructure.persistence.database import get_db_context
from trading.infrastructure.persistence.repositories.market_data_repository import CandleRepository
from trading.domain.market_data import CandleInterval

class ScaleInStrategyWithStateBug:
    def __init__(self, config=None):
        self.config = config or {}
        self.rsi_period = 14
        self.rsi_entry = 30
        self.breakout_lookback = 20
        self.cooldown_candles = 20
        
        # INDICATORS
        self.rsi_values = []
        self.breakout_highs = []
        
        # STATE - This is the crucial part. 
        # In many dynamic strategies, these are NOT reset by the engine automatically.
        self.last_trade_idx = None
        self.scaled_in = False
        self.initial_quantity = None

    def pre_calculate(self, candles, htf_candles=None):
        candles_1d = htf_candles.get("1d", []) if htf_candles else []
        if not candles_1d: return
        df = pd.DataFrame(candles_1d)
        rsi_series = ta.rsi(df["close"], length=self.rsi_period)
        self.rsi_values = rsi_series.tolist()
        df["high_max"] = df["high"].rolling(window=self.breakout_lookback).max()
        self.breakout_highs = df["high_max"].shift(1).tolist()

    def calculate_signal(self, candle, idx, position=None):
        # 1. Check Cooldown
        if self.last_trade_idx is not None and (idx - self.last_trade_idx) < self.cooldown_candles:
            return None
            
        rsi = self.rsi_values[idx]
        if pd.isna(rsi): return None
        
        close = float(candle["close"])
        b_high = self.breakout_highs[idx]
        if pd.isna(b_high): return None
        
        if position:
            # SCALE IN LOGIC (only if not already scaled in)
            if not self.scaled_in:
                 # ROI check (simplified)
                 leverage = 20.0
                 avg_price = float(getattr(position, 'avg_entry_price', entry_price))
                 price_move = (close - avg_price) / avg_price
                 roi = price_move * leverage * 100
                 if roi >= 50.0:
                     self.scaled_in = True
                     print(f"   [SCALE IN] {candle['timestamp']} at {close} (ROI: {roi:.2f}%)")
                     return "ADD"
            return None
        else:
            # ENTRY LOGIC
            # IMPORTANT: Many users forget to reset state when looking for NEW entry
            if rsi <= self.rsi_entry or close > b_high:
                 self.last_trade_idx = idx
                 # BUG: Not resetting self.scaled_in = False here? 
                 # Let's see what happens if we DON'T reset it.
                 return "BUY"
        return None

async def main():
    async with get_db_context() as session:
        candle_repo = CandleRepository(session)
        start_dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_dt = datetime(2025, 12, 31, tzinfo=timezone.utc)
        
        print("Fetching 1m candles for BTCUSDT (Full Range)...")
        candles = await candle_repo.find_by_symbol_and_interval(
            symbol="BTCUSDT",
            interval=CandleInterval.ONE_MINUTE,
            start_time=start_dt,
            end_time=end_dt
        )
        
        if not candles: return
        df_1m = pd.DataFrame([{
            "high": float(c.high_price), "low": float(c.low_price), "close": float(c.close_price), "timestamp": c.open_time
        } for c in sorted(candles, key=lambda x: x.open_time)])
        df_1m.set_index("timestamp", inplace=True)
        df_1d = df_1m.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
        htf_candles = {"1d": df_1d.reset_index().to_dict('records')}
        
        strategy = ScaleInStrategyWithStateBug()
        strategy.pre_calculate(None, htf_candles=htf_candles)
        
        trades = 0
        is_in_position = False
        entry_price = 0
        cooldown_idx = None
        
        for i in range(1, len(df_1d)):
            if cooldown_idx is not None and i < cooldown_idx: continue
            
            # Simulate high-timeframe day i-1 closed, processing signal at start of day i
            current_day_data = htf_candles["1d"][i]
            prev_day_data = htf_candles["1d"][i-1]
            
            if not is_in_position:
                signal = strategy.calculate_signal(prev_day_data, i-1)
                if signal == "BUY":
                    is_in_position = True
                    entry_price = prev_day_data["close"]
                    trades += 1
                    print(f"Trade #{trades}: Entry on {current_day_data['timestamp']} at {entry_price:.2f}")
            else:
                # 1. Check for Scale-In signal within the position
                # (Processed at start of day i based on day i-1 close)
                scale_signal = strategy.calculate_signal(prev_day_data, i-1, position=True)
                
                # 2. Check for Exit during day i
                day_low = current_day_data["low"]
                day_high = current_day_data["high"]
                liq_price = entry_price * 0.95
                tp_price = entry_price * 1.05
                
                if day_low <= liq_price:
                    is_in_position = False
                    cooldown_idx = i + 20
                    print(f" - EXIT on {current_day_data['timestamp']}: LIQUIDATION at {liq_price:.2f}")
                elif day_high >= tp_price:
                    is_in_position = False
                    print(f" - EXIT on {current_day_data['timestamp']}: TP at {tp_price:.2f}")

        print(f"\nFinal Simulated Trades: {trades}")

if __name__ == "__main__":
    asyncio.run(main())
