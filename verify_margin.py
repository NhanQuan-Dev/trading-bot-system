
import asyncio
import os
import sys
from decimal import Decimal
from datetime import datetime, timedelta

# Add backend/src to path
sys.path.insert(0, os.path.abspath("backend/src"))

from trading.infrastructure.backtesting.backtest_engine import BacktestEngine
from trading.domain.backtesting.value_objects import BacktestConfig
from trading.domain.backtesting.entities import BacktestRun
from trading.domain.backtesting.enums import TradeDirection

async def verify_margin_update():
    config = BacktestConfig(
        symbol="BTCUSDT",
        initial_capital=Decimal("10000"),
        leverage=10,
        taker_fee_rate=Decimal("0.0006"),
        maker_fee_rate=Decimal("0.0002"),
    )
    
    engine = BacktestEngine(config)
    run = BacktestRun(config=config)
    
    # 1. Open Long Position
    # Entry=10000, Qty=1, Initial Margin=1000
    # Liq Price = 10000 * (1 + 0.005) - 1000/1 = 10050 - 1000 = 9050
    
    signal_open = {
        "type": "open_long",
        "quantity": 1,
        "metadata": "Test Entry"
    }
    candle = {"close": 10000, "high": 10000, "low": 10000, "timestamp": datetime.now()}
    
    engine.backtest_run_id = run.id
    engine._process_signal(signal_open, candle)
    
    pos = engine.current_position
    print(f"Initial Position: Entry={pos.avg_entry_price}, Margin={pos.isolated_margin}")
    
    engine._check_liquidation(Decimal("10000"), Decimal("10000"))
    print(f"Initial Liq Price: {pos.liquidation_price}")
    
    if pos.liquidation_price != Decimal("9050"):
        print(f"ERROR: Expected 9050, got {pos.liquidation_price}")
    else:
        print("SUCCESS: Initial Liq Price is correct.")

    # 2. Add Margin
    # Add 500 margin. Total Margin = 1500
    # Liq Price = 10050 - 1500/1 = 8550
    signal_add = {
        "type": "update_margin",
        "amount": 500,
        "metadata": "Add Margin"
    }
    engine._process_signal(signal_add, candle)
    print(f"Update: Margin={pos.isolated_margin}, Equity={engine.equity}")
    
    engine._check_liquidation(Decimal("10000"), Decimal("10000"))
    print(f"New Liq Price: {pos.liquidation_price}")
    
    if pos.liquidation_price != Decimal("8550"):
        print(f"ERROR: Expected 8550, got {pos.liquidation_price}")
    else:
        print("SUCCESS: Liq Price decreased after adding margin.")

    # 3. Remove Margin
    # Remove 200 margin. Total Margin = 1300
    # Liq Price = 10050 - 1300/1 = 8750
    signal_remove = {
        "type": "update_margin",
        "amount": -200,
        "metadata": "Remove Margin"
    }
    engine._process_signal(signal_remove, candle)
    print(f"Update: Margin={pos.isolated_margin}, Equity={engine.equity}")
    
    engine._check_liquidation(Decimal("10000"), Decimal("10000"))
    print(f"Final Liq Price: {pos.liquidation_price}")
    
    if pos.liquidation_price != Decimal("8750"):
        print(f"ERROR: Expected 8750, got {pos.liquidation_price}")
    else:
        print("SUCCESS: Liq Price increased after removing margin.")

if __name__ == "__main__":
    asyncio.run(verify_margin_update())
