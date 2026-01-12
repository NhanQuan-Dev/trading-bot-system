import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from trading.infrastructure.persistence.database import get_db_context
from sqlalchemy import text

async def main():
    async with get_db_context() as session:
        result = await session.execute(text(
            "SELECT id, status, error_message FROM backtest_runs ORDER BY created_at DESC LIMIT 1"
        ))
        row = result.mappings().fetchone()
        if row:
            print(f"ID: {row['id']}")
            print(f"Status: {row['status']}")
            print(f"Error Message: {row['error_message']}")
        else:
            print("No backtests found.")

if __name__ == "__main__":
    asyncio.run(main())
