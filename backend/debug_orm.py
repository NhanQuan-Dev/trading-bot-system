import asyncio
import os
import sys
from uuid import UUID
from sqlalchemy import select, desc, text

sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from trading.infrastructure.persistence.database import get_db_context
from trading.infrastructure.persistence.models.backtest_models import BacktestTradeModel, BacktestResultModel

# "Test3" Backtest ID
BACKTEST_ID = "74a222c5-6d5b-4f83-b801-aa5964bcf794"

async def main():
    async with get_db_context() as session:
        print(f"Checking ORM for Backtest: {BACKTEST_ID}")
        
        # 1. Get Result ID and User ID
        res = await session.execute(text("SELECT user_id FROM backtest_runs WHERE id = :id"), {"id": BACKTEST_ID})
        user_id = res.scalar_one_or_none()
        print(f"User ID: {user_id}")
        
        result_query = select(BacktestResultModel.id).where(
            BacktestResultModel.backtest_run_id == BACKTEST_ID
        )
        result_result = await session.execute(result_query)
        result_id = result_result.scalar_one_or_none()
        
        if not result_id:
            print("Result ID not found!")
            return

        print(f"Result ID: {result_id}")

        # 2. Get Trades (Same logic as Repository)
        query = select(BacktestTradeModel).where(
            BacktestTradeModel.result_id == result_id
        ).order_by(desc(BacktestTradeModel.entry_time)).limit(5)
        
        result = await session.execute(query)
        trades = result.scalars().all()
        
        print(f"Found {len(trades)} trades via ORM.")
        for i, trade in enumerate(trades):
            print(f"--- Trade {i} ---")
            print(f"Symbol: {trade.symbol}")
            
            # Check attributes existence and value
            maker = getattr(trade, 'maker_fee', 'MISSING')
            taker = getattr(trade, 'taker_fee', 'MISSING')
            funding = getattr(trade, 'funding_fee', 'MISSING')
            
            print(f"Maker Fee: {maker} (Type: {type(maker)})")
            print(f"Taker Fee: {taker} (Type: {type(taker)})")
            print(f"Funding Fee: {funding} (Type: {type(funding)})")
            
            # Simulate Controller Logic
            try:
                val = float(trade.taker_fee) if getattr(trade, "taker_fee", None) is not None else 0.0
                print(f"Controller Logic Result (Taker): {val}")
            except Exception as e:
                print(f"Controller Logic Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
