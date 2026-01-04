
import asyncio
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend/src"))
sys.path.append(os.path.join(os.getcwd(), "backend"))

from trading.infrastructure.persistence.database import get_db_context
from trading.infrastructure.persistence.repositories.bot_repository import BotRepository
from application.services.connection_service import ConnectionService
from trading.infrastructure.exchange.binance_adapter import BinanceAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_leverage():
    bot_id = "c95bae7f-a940-41fa-ac2f-892fad7ec836" # From previous logs
    
    print(f"Checking leverage for Bot {bot_id}...")
    
    async with get_db_context() as session:
        bot_repo = BotRepository(session)
        conn_service = ConnectionService(session)
        
        bot = await bot_repo.find_by_id(bot_id)
        if not bot:
            print("Bot not found!")
            return

        print(f"Bot found: {bot.name}, Symbol: {bot.configuration.symbol}")
        
        creds = await conn_service.get_connection_credentials(str(bot.exchange_connection_id), bot.user_id)
        
        base_url = "https://demo-fapi.binance.com" if creds["is_testnet"] else "https://fapi.binance.com"
        print(f"Using URL: {base_url}")
        
        adapter = BinanceAdapter(
            api_key=creds["api_key"],
            api_secret=creds["api_secret"],
            base_url=base_url,
            testnet=creds["is_testnet"]
        )
        
        try:
            risk_data = await adapter.get_position_risk(symbol=bot.configuration.symbol)
            print("\n--- Position Risk Data ---")
            for item in risk_data:
                print(f"Symbol: {item['symbol']}")
                print(f"Leverage: {item['leverage']}")
                print(f"Margin Type: {item['marginType']}")
                print(f"Liquidation Price: {item['liquidationPrice']}")
                print(f"Entry Price: {item['entryPrice']}")
                print(f"Unrealized PnL: {item['unRealizedProfit']}")
                print("--------------------------")
                
        except Exception as e:
            print(f"Error fetching position risk: {e}")
        finally:
            await adapter.close()

if __name__ == "__main__":
    asyncio.run(check_leverage())
