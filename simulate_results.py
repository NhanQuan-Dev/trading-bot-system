
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
        candles = await candle_repo.find_by_symbol_and_interval(
            symbol="BTCUSDT",
            interval=CandleInterval.ONE_MINUTE,
            start_time=start_dt,
            end_time=end_dt
        )
        
        if not candles:
            return
            
        # Strategy uses 1d for signals, but we need 1m for intra-day liquidation/TP checks
        # For simulation, we aggregate to 1d for ENTRY signals, but check EXITs on 1d too (simplified)
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
        target_roi = 100.0 # 100% ROI
        liquidation_pct = 1 / leverage # 0.05 (5%)
        
        trades = []
        is_in_position = False
        entry_price = 0
        entry_date = None
        cooldown_until = None
        
        for i in range(len(df_1d)):
            current_date = df_1d.index[i]
            
            if cooldown_until and current_date < cooldown_until:
                continue
                
            if not is_in_position:
                # Check for Entry
                if pd.isna(df_1d.iloc[i]["rsi"]) or pd.isna(df_1d.iloc[i]["breakout_high"]):
                    continue
                    
                rsi = df_1d.iloc[i]["rsi"]
                close = df_1d.iloc[i]["close"]
                b_high = df_1d.iloc[i]["breakout_high"]
                
                if rsi <= 30 or close > b_high:
                    is_in_position = True
                    entry_price = close
                    entry_date = current_date
                    print(f"ENTRY on {current_date} at {entry_price:.2f}")
            else:
                # Check for Exit (TP or Liquidation)
                low = df_1d.iloc[i]["low"]
                high = df_1d.iloc[i]["high"]
                
                # Check Liquidation first (Low price drops 5%)
                liq_price = entry_price * (1 - liquidation_pct)
                if low <= liq_price:
                    trades.append({"entry": entry_date, "exit": current_date, "result": "LIQUIDATION"})
                    is_in_position = False
                    cooldown_until = current_date + pd.Timedelta(days=20)
                    print(f"EXIT on {current_date}: LIQUIDATION at {liq_price:.2f}")
                    continue
                
                # Check TP (High price reaches 5% move for 100% ROI)
                move_for_tp = (target_roi / 100.0) / leverage # 1.0 / 20 = 0.05
                tp_price = entry_price * (1 + move_for_tp)
                if high >= tp_price:
                    trades.append({"entry": entry_date, "exit": current_date, "result": "TP"})
                    is_in_position = False
                    print(f"EXIT on {current_date}: TP at {tp_price:.2f}")
        
        print(f"\nTotal Simulated Trades: {len(trades)}")

if __name__ == "__main__":
    asyncio.run(main())
