import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from sqlalchemy import text
from trading.infrastructure.persistence.database import get_db_context

async def fix_constraint():
    print("Starting database constraint fix for STATUS...")
    async with get_db_context() as session:
        # 1. Drop old constraint
        print("Dropping old constraint ck_orders_status...")
        try:
            await session.execute(text("ALTER TABLE orders DROP CONSTRAINT ck_orders_status"))
            print("Dropped successfully.")
        except Exception as e:
            print(f"Warning dropping constraint: {e}")

        # 2. Add new constraint
        print("Adding new constraint ck_orders_status (including NEW)...")
        try:
            await session.execute(text("ALTER TABLE orders ADD CONSTRAINT ck_orders_status CHECK (status IN ('PENDING', 'NEW', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'REJECTED', 'EXPIRED'))"))
            print("Added successfully.")
        except Exception as e:
            print(f"Error adding constraint: {e}")
            raise
            
        await session.commit()
    print("Database fix completed.")

if __name__ == "__main__":
    asyncio.run(fix_constraint())
