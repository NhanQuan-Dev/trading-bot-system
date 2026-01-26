
import asyncio
import time
import cProfile
import pstats
from datetime import datetime, timedelta
from decimal import Decimal
import random
from typing import List, Dict
import sys
import os

# Add backend to path so 'src' imports work
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock classes to avoid full dependency tree loading for benchmark
from src.trading.domain.backtesting import BacktestConfig, BacktestRun, BacktestStatus
from src.trading.infrastructure.backtesting.backtest_engine import BacktestEngine
from src.trading.infrastructure.backtesting.market_simulator import MarketSimulator
from src.trading.strategies.backtest_adapter import get_strategy_function

def generate_candles(count: int) -> List[Dict]:
    """Generate synthetic 1m candles."""
    candles = []
    base_price = 50000.0
    start_time = datetime(2024, 1, 1)
    
    current_price = base_price
    for i in range(count):
        change = random.uniform(-0.001, 0.001)
        current_price *= (1 + change)
        high = current_price * (1 + random.uniform(0, 0.0005))
        low = current_price * (1 - random.uniform(0, 0.0005))
        
        candles.append({
            "timestamp": (start_time + timedelta(minutes=i)).isoformat(),
            "open": current_price,
            "high": high,
            "low": low,
            "close": current_price,
            "volume": random.uniform(10, 100)
        })
    return candles

async def run_benchmark():
    # 1. Setup
    print("Generating 525,600 candles (1 Year of 1m data)...")
    candles = generate_candles(525600) 
    
    config = BacktestConfig(
        symbol="BTC/USDT",
        initial_capital=Decimal("10000.0"),
        leverage=20, # User specified leverage
        signal_timeframe="1h", 
        commission_model="fixed_rate",
        commission_percent=Decimal("0.001"),
        slippage_model="fixed",
        slippage_percent=Decimal("0.001"),
        position_sizing="percent_equity",
        position_size_value=Decimal("0.1") # 10% initial size per trade
    )
    
    # Mock Strategy with Scale-In logic
    def strategy(candle, idx, position, multi_tf_context=None):
        if not position:
            # Random entry
            if random.random() < 0.001:
                return {"type": "ENTRY_LONG"}
        else:
            # Scale In logic
            current_price = Decimal(str(candle['close']))
            entry_price = position.avg_entry_price
            
            # If price drops 1%, scale in (Martingale-ish)
            # Just verify quantity is not too huge to simulate limits
            if current_price < entry_price * Decimal("0.99") and position.quantity < Decimal("1.0"): 
                 if random.random() < 0.1: # Don't scale continuously, just sometimes
                    return {"type": "SCALE_IN_LONG", "amount_percent": 0.1}
            
            # TP at 50% (Leveraged) -> 2.5% price move
            if current_price > entry_price * Decimal("1.025"):
                 return {"type": "EXIT_LONG", "reason": "TP 50%"}
                 
        return None

    engine = BacktestEngine(config)
    
    # Mock BacktestRun
    backtest_run_mock = BacktestRun(
        id="bench_1year",
        user_id="bench", 
        strategy_id="bench",
        exchange_connection_id="bench",
        exchange_name="bench",
        symbol="BTC/USDT",
        timeframe="1m",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2025, 1, 1),
        config=config,
        status=BacktestStatus.PENDING
    )
    backtest_run_mock.start = lambda: None
    backtest_run_mock.update_progress = lambda x: None
    backtest_run_mock.complete = lambda x: None
    backtest_run_mock.fail = lambda x: None

    # 2. Run Benchmark
    print("Starting Benchmark...")
    start_time = time.time()
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    # try:
    await engine.run_backtest(candles, strategy, backtest_run_mock)
    # except Exception as e:
    #     print(f"Error: {e}")
        
    profiler.disable()
    end_time = time.time()
    
    print(f"Time taken: {end_time - start_time:.4f} seconds")
    
    # 3. Analyze
    stats = pstats.Stats(profiler).sort_stats('cumtime')
    stats.print_stats(30) # Show top 30 to get more detail

if __name__ == "__main__":
    asyncio.run(run_benchmark())
