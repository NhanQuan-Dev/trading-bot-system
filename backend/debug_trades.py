
import asyncio
import uuid
from sqlalchemy import select, func, and_
from src.trading.infrastructure.persistence.database import get_db_context
from src.trading.infrastructure.persistence.models.trading_models import TradeModel
from src.trading.infrastructure.persistence.models.bot_models import BotModel
from decimal import Decimal

BOT_ID = "c95bae7f-a940-41fa-ac2f-892fad7ec836"

async def main():
    print(f"Checking trades for Bot: {BOT_ID}")
    
    async with get_db_context() as session:
        # 1. Query Bot Stats
        stmt = select(BotModel).where(BotModel.id == uuid.UUID(BOT_ID))
        result = await session.execute(stmt)
        bot = result.scalar_one_or_none()
        
        if not bot:
            print("Bot not found!")
            return

        print(f"\n[Bot Stats in DB]")
        print(f"Total Trades: {bot.total_trades}")
        print(f"Total PnL: {bot.total_pnl}")
        print(f"Win Rate: {bot.winning_trades}/{bot.total_trades}")
        
        # 2. Query Trade Count
        stmt = select(func.count(TradeModel.id)).where(TradeModel.bot_id == uuid.UUID(BOT_ID))
        result = await session.execute(stmt)
        count = result.scalar()
        print(f"\n[Actual Trade Count in DB]")
        print(f"Count: {count}")
        
        # 3. List Trades
        stmt = select(TradeModel).where(TradeModel.bot_id == uuid.UUID(BOT_ID)).order_by(TradeModel.executed_at)
        result = await session.execute(stmt)
        trades = result.scalars().all()
        
        print(f"\n[Trade List ({len(trades)})]")
        for i, t in enumerate(trades):
            print(f"{i+1}. ID: {t.id} | Side: {t.side} | Qty: {t.quantity} | PnL: {t.pnl} | Time: {t.executed_at}")

        # 4. Check for mismatches
        if count != bot.total_trades:
             print("\n!!! MISMATCH DETECTED !!!")
             print(f"Bot says {bot.total_trades}, DB has {count}")
        else:
             print("\nStats are consistent.")

if __name__ == "__main__":
    asyncio.run(main())
