
import asyncio
import uuid
import json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, select
from sqlalchemy.orm import sessionmaker

# Use the correct DB URL
DATABASE_URL = "postgresql+asyncpg://postgres:postgres123@localhost:5432/trading_platform"

async def insert_strategy():
    engine = create_async_engine(DATABASE_URL)
    
    # Read the code content
    with open("martingale_mtf_fixed_sl.py", "r") as f:
        code_content = f.read()

    async with engine.connect() as conn:
        # Check if exists
        check_sql = text("SELECT id FROM strategies WHERE name = :name")
        result = await conn.execute(check_sql, {"name": "Martingale Smart MTF (Fixed SL)"})
        existing = result.scalar()

        if existing:
            print(f"Strategy already exists with ID: {existing}")
            # Update code
            update_sql = text("""
                UPDATE strategies 
                SET code_content = :code, 
                    updated_at = NOW(),
                    strategy_type = 'CUSTOM',
                    description = :desc
                WHERE id = :id
            """)
            await conn.execute(update_sql, {
                "code": code_content, 
                "id": existing,
                "desc": "Martingale with HTF Trend Filter and Corrected Step-Up (SL = Old TP - 50%)"
            })
            print("Updated existing strategy.")
        else:
            new_id = uuid.uuid4()
            user_id = uuid.UUID("00000000-0000-0000-0000-000000000001") # Default User
            
            insert_sql = text("""
                INSERT INTO strategies (
                    id, user_id, name, strategy_type, description, parameters, is_active, code_content, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :name, 'CUSTOM', :description, :parameters, true, :code_content, NOW(), NOW()
                )
            """)
            
            await conn.execute(insert_sql, {
                "id": new_id,
                "user_id": user_id,
                "name": "Martingale Smart MTF (Fixed SL)",
                "description": "Martingale with HTF Trend Filter and Corrected Step-Up (SL = Old TP - 50%)",
                "parameters": json.dumps({
                    "htf_timeframe": "1h",
                    "htf_ma_period": 20
                }),
                "code_content": code_content
            })
            print(f"Inserted new strategy with ID: {new_id}")
            
        await conn.commit()

if __name__ == "__main__":
    asyncio.run(insert_strategy())
