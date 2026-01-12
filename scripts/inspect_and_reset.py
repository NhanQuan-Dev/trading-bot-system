import asyncio
import os
import sys
from sqlalchemy import text, inspect
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
        # 1. Inspect Tables
        print("\n=== Existing Tables ===")
        # Async inspection is tricky, retrieving via text query for simplicity
        result = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ))
        tables = [row[0] for row in result.fetchall()]
        for t in tables:
            print(f"- {t}")
        
        # Check for candidates
        candidates = [t for t in tables if 'file' in t.lower() or 'code' in t.lower()]
        if candidates:
            print(f"\nPotential 'Strategy Files' tables found: {candidates}")
        else:
            print("\nNo obvious 'Strategy Files' table found.")

        # 2. Truncate Strategies
        print("\n=== Truncating 'strategies' table (CASCADE) ===")
        # This will delete ALL data in strategies and dependent bots/trades/backtests
        try:
            await conn.execute(text("TRUNCATE TABLE strategies CASCADE"))
            await conn.commit()
            print("SUCCESS: Strategies table truncated.")
        except Exception as e:
            print(f"ERROR: Failed to truncate strategies: {e}")
            
        # 3. Drop 'strategy_files' if strictly named that and requested
        if 'strategy_files' in tables:
            print("\n=== Dropping 'strategy_files' table ===")
            try:
                await conn.execute(text("DROP TABLE strategy_files CASCADE"))
                await conn.commit()
                print("SUCCESS: strategy_files table dropped.")
            except Exception as e:
                print(f"ERROR: Failed to drop strategy_files: {e}")
        else:
             print("\n'strategy_files' table not found, skipping drop.")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
