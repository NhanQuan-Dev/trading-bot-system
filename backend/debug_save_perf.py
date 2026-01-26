
import asyncio
import time
from uuid import uuid4
from decimal import Decimal
from datetime import datetime

from src.trading.domain.backtesting import BacktestRun, BacktestConfig, BacktestStatus
from src.trading.infrastructure.backtesting.repository import BacktestRepository
from src.trading.infrastructure.persistence.database import get_session_factory, create_tables

async def run_debug():
    print("Setting up DB...")
    # Ensure tables exist (mock/lite or actual)
    # We'll use the actual DB connection if possible
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        repo = BacktestRepository(session)
        
        # Create Mock Backtest
        config = BacktestConfig(
            symbol="BTC/USDT",
            initial_capital=Decimal("10000"),
            leverage=20,
            signal_timeframe="1h",
            commission_percent=Decimal("0.001"),
            slippage_percent=Decimal("0.001")
        )
        
        run = BacktestRun(
            id=uuid4(),
            user_id=uuid4(),
            strategy_id=uuid4(),
            config=config,
            symbol="BTC/USDT",
            timeframe="1m",
            start_date=datetime.now(),
            end_date=datetime.now(),
            status=BacktestStatus.PENDING
        )
        
        print("Initial Save...")
        t0 = time.time()
        await repo.save(run)
        print(f"Initial Save took: {time.time() - t0:.4f}s")
        
        # Simulate Progress Updates
        print("Simulating 10 progress updates...")
        for i in range(1, 11):
            run.update_progress(i * 10, f"Processing {i*10}%")
            
            t_start = time.time()
            await repo.save(run)
            duration = time.time() - t_start
            print(f"Update {i*10}% took: {duration:.4f}s")
            
            if duration > 1.0:
                print("WARNING: Slow Save Detected!")

if __name__ == "__main__":
    # Assuming run from backend/ directory to resolve imports
    # Need to set PYTHONPATH
    import sys
    import os
    sys.path.append(os.getcwd())
    
    asyncio.run(run_debug())
