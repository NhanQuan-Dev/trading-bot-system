
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
        test_end = datetime(2024, 6, 1, tzinfo=timezone.utc)
        
        print("Fetching 1m candles for BTCUSDT (First Half 2024)...")
        candles = await candle_repo.find_by_symbol_and_interval(
            symbol="BTCUSDT",
            interval=CandleInterval.ONE_MINUTE,
            start_time=start_dt,
            end_time=test_end
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
        
        # Strategy Indicators (1d)
        rsi_period = 14
        breakout_lookback = 20
        df_1d["rsi"] = ta.rsi(df_1d["close"], length=rsi_period)
        df_1d["breakout_high"] = df_1d["close"].rolling(window=breakout_lookback).max().shift(1)
        
        # Backtest Engine constants
        leverage = 20.0
        liquidation_pct = 1 / leverage # 0.05 (5%)
        # For simulation, 100% ROI TP is actually just 5% price move up
        tp_pct = 0.05
        
        is_in_position = False
        entry_price = 0
        cooldown_until = None
        trade_count = 0
        
        # We start checking signals from day 21 (after indicators are ready)
        # Note: In engine, signal generated at day N close is processed at day N+1 start.
        for i in range(20, len(df_1d)):
            current_date = df_1d.index[i]
            
            if cooldown_until and current_date < cooldown_until:
                continue
            
            if not is_in_position:
                # Check Signal from PREVIOUS day (simulating engine delay)
                rsi = df_1d.iloc[i-1]["rsi"]
                close = df_1d.iloc[i-1]["close"]
                b_high = df_1d.iloc[i-1]["breakout_high"]
                
                if rsi <= 30 or close > b_high:
                    is_in_position = True
                    # Entry is at current day's open (approximated by previous day close)
                    entry_price = df_1d.iloc[i-1]["close"]
                    trade_count += 1
                    print(f"Trade #{trade_count}: ENTRY on {current_date} at {entry_price:.2f}")
            else:
                # Check for Exit on current day
                day_low = df_1d.iloc[i]["low"]
                day_high = df_1d.iloc[i]["high"]
                
                liq_price = entry_price * (1 - liquidation_pct)
                tp_price = entry_price * (1 + tp_pct)
                
                if day_low <= liq_price:
                    is_in_position = False
                    cooldown_until = current_date + pd.Timedelta(days=20)
                    print(f"EXIT on {current_date}: LIQUIDATION at {liq_price:.2f}")
                    print(f"Cooldown until {cooldown_until}")
                elif day_high >= tp_price:
                    is_in_position = False
                    print(f"EXIT on {current_date}: TP at {tp_price:.2f}")

        print(f"\nTotal Simulated Trades (First Half 2024): {trade_count}")

if __name__ == "__main__":
    asyncio.run(main())
