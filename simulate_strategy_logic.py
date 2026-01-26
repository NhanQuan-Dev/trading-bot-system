
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
from trading.strategies.implementations.grid_trading import StrategyBase # Need path dummy

# We manually reconstruct the strategy class from the code_content in DB to avoid import issues
# or just import it if it's on disk. Let's see if it's in implementations.
# Based on prev grep, it's not a standard implementation.

class ScaleInStrategy:
    def __init__(self, config=None):
        self.config = config or {}
        self.rsi_period = 14
        self.rsi_entry = 30
        self.breakout_lookback = 20
        self.cooldown_candles = 20
        self.quantity = Decimal("0.001")
        self.take_profit_roi = 100.0
        self.scale_in_roi_threshold = 50.0
        self.rsi_values = []
        self.breakout_highs = []
        self.last_trade_idx = None

    def pre_calculate(self, candles, htf_candles=None):
        # Use HTF candles (1d)
        candles_1d = htf_candles.get("1d", []) if htf_candles else []
        if not candles_1d:
            return
            
        df = pd.DataFrame(candles_1d)
        rsi_series = ta.rsi(df["close"], length=self.rsi_period)
        self.rsi_values = rsi_series.tolist()
        
        # Strategy specific: breakout_highs is rolling max of HIGH, not close!
        df["high_max"] = df["high"].rolling(window=self.breakout_lookback).max()
        self.breakout_highs = df["high_max"].shift(1).tolist()

    def calculate_signal(self, candle, idx, position=None):
        if idx >= len(self.rsi_values) or idx >= len(self.breakout_highs):
            return None
            
        # Cooldown check
        if self.last_trade_idx is not None and (idx - self.last_trade_idx) < self.cooldown_candles:
            return None
            
        rsi = self.rsi_values[idx]
        if pd.isna(rsi): return None
        
        # Strategy logic: compare Current Close to Previous Highs
        close = float(candle["close"])
        b_high = self.breakout_highs[idx]
        if pd.isna(b_high): return None
        
        is_rsi_buy = rsi <= self.rsi_entry
        is_breakout_buy = close > b_high
        
        if is_rsi_buy or is_breakout_buy:
             self.last_trade_idx = idx
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
        
        if not candles:
            return
            
        df_1m = pd.DataFrame([{
            "high": float(c.high_price),
            "low": float(c.low_price),
            "close": float(c.close_price),
            "timestamp": c.open_time
        } for c in sorted(candles, key=lambda x: x.open_time)])
        df_1m.set_index("timestamp", inplace=True)
        
        df_1d = df_1m.resample("1D").agg({
            "high": "max",
            "low": "min",
            "close": "last"
        }).dropna()
        
        htf_candles = {"1d": df_1d.reset_index().to_dict('records')}
        
        strategy = ScaleInStrategy()
        strategy.pre_calculate(None, htf_candles=htf_candles)
        
        trades = 0
        is_in_position = False
        entry_price = 0
        cooldown_idx = None
        
        for i in range(len(df_1d)):
            if cooldown_idx is not None and i < cooldown_idx:
                continue
                
            if not is_in_position:
                # Engine Delay: process day i-1 signal at day i
                if i > 0:
                     signal = strategy.calculate_signal(htf_candles["1d"][i-1], i-1)
                     if signal == "BUY":
                         is_in_position = True
                         entry_price = htf_candles["1d"][i-1]["close"]
                         trades += 1
                         print(f"Trade #{trades}: Entry on {df_1d.index[i]} at {entry_price:.2f}")
            else:
                 # Check Exit on day i
                 day_low = df_1d.iloc[i]["low"]
                 day_high = df_1d.iloc[i]["high"]
                 
                 liq_price = entry_price * 0.95
                 tp_price = entry_price * 1.05
                 
                 if day_low <= liq_price:
                     is_in_position = False
                     cooldown_idx = i + 20
                     print(f" - EXIT on {df_1d.index[i]}: LIQUIDATION at {liq_price:.2f}")
                 elif day_high >= tp_price:
                     is_in_position = False
                     print(f" - EXIT on {df_1d.index[i]}: TP at {tp_price:.2f}")

        print(f"\nFinal Simulated Trades: {trades}")

if __name__ == "__main__":
    asyncio.run(main())
