import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

env_path = os.path.join(os.getcwd(), 'backend', '.env')
print(f"Loading .env from: {env_path}")
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found")
    sys.exit(1)

# Ensure async driver
if "postgresql://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

async def main():
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.connect() as conn:
        print("\n=== Fixing Database Schema ===")
        print("Attempting to add 'entry_reason' column to 'backtest_trades' table...")
        
        try:
            # Check if column exists
            result = await conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='backtest_trades' AND column_name='entry_reason'"
            ))
            if result.scalar():
                print("Column 'entry_reason' already exists. skipping.")
            else:
                # Add column
                # Note: using JSONB for Postgres. If SQLite (unlikely given previous logs), use JSON.
                # The user logs confirm asyncpg/Postgres.
                await conn.execute(text("ALTER TABLE backtest_trades ADD COLUMN entry_reason JSONB"))
                await conn.commit()
                print("SUCCESS: Added 'entry_reason' column.")
        except Exception as e:
            print(f"ERROR: Failed to modify table: {e}")
            # Try plain JSON if JSONB fails?
            if "type \"jsonb\" does not exist" in str(e).lower():
                 print("Retrying with JSON type...")
                 try:
                    await conn.execute(text("ALTER TABLE backtest_trades ADD COLUMN entry_reason JSON"))
                    await conn.commit()
                    print("SUCCESS: Added 'entry_reason' column (JSON).") 
                 except Exception as ex:
                     print(f"ERROR: Retry failed: {ex}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
