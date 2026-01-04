import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from sqlalchemy import text
from trading.infrastructure.persistence.database import get_db_context

async def fix_constraint():
    print("Starting database constraint fix...")
    async with get_db_context() as session:
        # 1. Drop old constraint
        print("Dropping old constraint ck_orders_side...")
        try:
            await session.execute(text("ALTER TABLE orders DROP CONSTRAINT ck_orders_side"))
            print("Dropped successfully.")
        except Exception as e:
            print(f"Warning dropping constraint (might have been dropped partially): {e}")

        # 2. Migrate Data
        print("Migrating existing data (LONG->BUY, SHORT->SELL)...")
        await session.execute(text("UPDATE orders SET side='BUY' WHERE side='LONG'"))
        await session.execute(text("UPDATE orders SET side='SELL' WHERE side='SHORT'"))
        
        # 3. Add new constraint
        print("Adding new constraint ck_orders_side (BUY, SELL)...")
        try:
            await session.execute(text("ALTER TABLE orders ADD CONSTRAINT ck_orders_side CHECK (side IN ('BUY', 'SELL'))"))
            print("Added successfully.")
        except Exception as e:
            print(f"Error adding constraint: {e}")
            raise
            
        await session.commit()
    print("Database fix completed.")

if __name__ == "__main__":
    asyncio.run(fix_constraint())
