import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:postgres123@localhost:5432/trading_platform"

async def fetch_code():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT code_content FROM strategies WHERE name = 'Martingale Smart Always-In (Fixed SL)'"))
        code = result.scalar()
        if code:
            with open("martingale_fixed_sl_base.py", "w") as f:
                f.write(code)
            print("Code saved to martingale_fixed_sl_base.py")
        else:
            print("Strategy not found")

if __name__ == "__main__":
    asyncio.run(fetch_code())
