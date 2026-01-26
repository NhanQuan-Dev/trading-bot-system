
import pandas as pd
import pandas_ta as ta
import asyncio
import os
import sys
from datetime import datetime
from decimal import Decimal

# Add backend/src to path
sys.path.insert(0, os.path.abspath("backend/src"))

from trading.infrastructure.persistence.database import get_db_context
from trading.infrastructure.persistence.repositories.market_data_repository import CandleRepository
from trading.domain.market_data import CandleInterval

async def main():
    async with get_db_context() as session:
        candle_repo = CandleRepository(session)
        
        start_dt = datetime(2024, 1, 1)
        end_dt = datetime(2025, 12, 31)
        
        print("Fetching 1d candles for BTCUSDT...")
        # We need 1d candles because the strategy signal_timeframe is 1d
        candles = await candle_repo.find_by_symbol_and_interval(
            symbol="BTCUSDT",
            interval=CandleInterval.ONE_DAY,
            start_time=start_dt,
            end_time=end_dt
        )
        
        print(f"Fetched {len(candles)} candles.")
        if not candles:
            return
            
        df = pd.DataFrame([{
            "open": float(c.open_price),
            "high": float(c.high_price),
            "low": float(c.low_price),
            "close": float(c.close_price),
            "volume": float(c.volume),
            "timestamp": c.open_time
        } for c in sorted(candles, key=lambda x: x.open_time)])
        
        # Strategy Logic
        rsi_period = 14
        rsi_entry = 30
        breakout_lookback = 20
        
        df["rsi"] = ta.rsi(df["close"], length=rsi_period)
        df["breakout_high"] = df["high"].rolling(window=breakout_lookback).max().shift(1)
        
        # Find signals
        signals = []
        for i in range(len(df)):
            if pd.isna(df.iloc[i]["rsi"]) or pd.isna(df.iloc[i]["breakout_high"]):
                continue
                
            rsi = df.iloc[i]["rsi"]
            close = df.iloc[i]["close"]
            b_high = df.iloc[i]["breakout_high"]
            
            is_rsi_buy = rsi <= rsi_entry
            is_breakout_buy = close > b_high
            
            if is_rsi_buy or is_breakout_buy:
                signals.append({
                    "date": df.iloc[i]["timestamp"],
                    "rsi": rsi,
                    "close": close,
                    "breakout_high": b_high,
                    "type": "RSI" if is_rsi_buy else "BREAKOUT"
                })
        
        print(f"\nTotal potential signals (without cooldowns or position monitoring): {len(signals)}")
        for s in signals[:10]:
            print(f"Signal on {s['date']}: {s['type']} (RSI: {s['rsi']:.2f}, Close: {s['close']:.2f}, High: {s['breakout_high']:.2f})")
        if len(signals) > 10:
            print("...")

if __name__ == "__main__":
    asyncio.run(main())
