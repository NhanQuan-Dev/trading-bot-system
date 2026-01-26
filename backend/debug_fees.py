import asyncio
import os
import sys
from uuid import UUID
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from trading.infrastructure.persistence.database import get_db_context

BACKTEST_ID = "74a222c5-6d5b-4f83-b801-aa5964bcf794"

async def main():
    async with get_db_context() as session:
        print(f"Checking Backtest: {BACKTEST_ID}")
        
        # 1. Check Config
        res = await session.execute(text("SELECT config FROM backtest_runs WHERE id = :id"), {"id": BACKTEST_ID})
        row = res.fetchone()
        if row:
            print(f"Config: {row[0]}")
        else:
            print("Backtest Run NOT FOUND")
            return

        # 2. Check Specific Trade
        TRADE_ID = "ad45a1bc-4652-4c5e-84f1-1d523e84bc9c"
        print(f"Checking Trade: {TRADE_ID}")
        res = await session.execute(text("""
            SELECT symbol, maker_fee, taker_fee, funding_fee, commission, exit_reason
            FROM backtest_trades 
            WHERE id = :id
        """), {"id": TRADE_ID})
        
        row = res.fetchone()
        if row:
            print(f"Trade Data: {row}")
        else:
            print("Trade NOT FOUND")
            
        return

if __name__ == "__main__":
    asyncio.run(main())
