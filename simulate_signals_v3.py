
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

async def main():
    async with get_db_context() as session:
        candle_repo = CandleRepository(session)
        
        start_dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_dt = datetime(2025, 12, 31, tzinfo=timezone.utc)
        
        print("Fetching 1m candles for BTCUSDT (Full Range)...")
        # Fetching all at once might be slow, but 1M rows in memory is ~100MB, acceptable.
        candles = await candle_repo.find_by_symbol_and_interval(
            symbol="BTCUSDT",
            interval=CandleInterval.ONE_MINUTE,
            start_time=start_dt,
            end_time=end_dt
        )
        
        print(f"Fetched {len(candles)} 1m candles.")
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
        
        # Aggregate to 1d
        df.set_index("timestamp", inplace=True)
        df_1d = df.resample("1D").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna()
        
        print(f"Aggregated to {len(df_1d)} days.")
        
        # Strategy Logic
        rsi_period = 14
        rsi_entry = 30
        breakout_lookback = 20
        
        df_1d["rsi"] = ta.rsi(df_1d["close"], length=rsi_period)
        df_1d["breakout_high"] = df_1d["close"].rolling(window=breakout_lookback).max().shift(1)
        
        # Find signals with 20-day cooldown logic
        signals = []
        last_signal_date = None
        
        for i in range(len(df_1d)):
            if pd.isna(df_1d.iloc[i]["rsi"]) or pd.isna(df_1d.iloc[i]["breakout_high"]):
                continue
            
            # Simplified cooldown logic (20 days)
            if last_signal_date and (df_1d.index[i] - last_signal_date).days < 20:
                continue
                
            rsi = df_1d.iloc[i]["rsi"]
            close = df_1d.iloc[i]["close"]
            b_high = df_1d.iloc[i]["breakout_high"]
            
            is_rsi_buy = rsi <= rsi_entry
            is_breakout_buy = close > b_high
            
            if is_rsi_buy or is_breakout_buy:
                signals.append({
                    "date": df_1d.index[i],
                    "rsi": rsi,
                    "close": close,
                    "breakout_high": b_high,
                    "type": "RSI" if is_rsi_buy else "BREAKOUT"
                })
                last_signal_date = df_1d.index[i]
        
        print(f"\nFinal potential signals (with 20-day cooldown): {len(signals)}")
        for s in signals:
            print(f"Signal on {s['date']}: {s['type']} (RSI: {s['rsi']:.2f}, Close: {s['close']:.2f}, High: {s['breakout_high']:.2f})")

if __name__ == "__main__":
    asyncio.run(main())
