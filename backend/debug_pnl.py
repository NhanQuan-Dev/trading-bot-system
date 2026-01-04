
import asyncio
import uuid
import sys
import os
from sqlalchemy import select

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from trading.infrastructure.persistence.database import get_db_context
from trading.infrastructure.persistence.models.bot_models import BotModel

async def check_bot_pnl():
    bot_id = "c95bae7f-a940-41fa-ac2f-892fad7ec836" # From previous logs/screenshot
    async with get_db_context() as session:
        stmt = select(BotModel).where(BotModel.id == uuid.UUID(bot_id))
        result = await session.execute(stmt)
        bot = result.scalar_one_or_none()
        if bot:
            print(f"Bot ID: {bot.id}")
            print(f"Total PnL (Column): {bot.total_pnl}")
            print(f"Total Trades: {bot.total_trades}")
            print(f"Winning Trades: {bot.winning_trades}")
            print(f"Losing Trades: {bot.losing_trades}")
            print(f"Current Win Streak: {bot.current_win_streak}")
            print(f"Current Loss Streak: {bot.current_loss_streak}")
            print(f"Max Win Streak: {bot.max_win_streak}")
            print(f"Max Loss Streak: {bot.max_loss_streak}")
            print(f"Performance JSON: {bot.performance}")
        else:
            print("Bot not found")

if __name__ == "__main__":
    asyncio.run(check_bot_pnl())
