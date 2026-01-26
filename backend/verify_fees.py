import asyncio
import os
import sys
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from trading.infrastructure.persistence.database import get_db_context
from sqlalchemy import text

async def main():
    print("Verifying Fee Columns...")
    async with get_db_context() as session:
        # Check Columns via SQL
        try:
            result = await session.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'backtest_trades' AND column_name IN ('maker_fee', 'taker_fee', 'funding_fee')"
            ))
            columns = [row[0] for row in result.fetchall()] # fetchall returns tuples/rows
            print(f"Found columns: {columns}")
            
            required = {'maker_fee', 'taker_fee', 'funding_fee'}
            found = set(columns)
            
            if required.issubset(found):
                print("SUCCESS: All fee columns present in DB.")
            else:
                print(f"FAILURE: Missing columns. Found: {found}, Missing: {required - found}")
                
        except Exception as e:
            print(f"Error checking schema: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
