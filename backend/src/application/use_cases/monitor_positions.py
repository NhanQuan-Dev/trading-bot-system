from src.domain.repositories.account_repository import AccountRepository
from src.domain.entities.position import Position
from src.application.services.market_data_service import MarketDataService
from src.application.services.account_service import AccountService

class MonitorPositions:
    def __init__(self, account_repository: AccountRepository, market_data_service: MarketDataService, account_service: AccountService):
        self.account_repository = account_repository
        self.market_data_service = market_data_service
        self.account_service = account_service

    async def execute(self):
        positions = await self.account_service.get_open_positions()
        for position in positions:
            await self.monitor_position(position)

    async def monitor_position(self, position: Position):
        mark_price = await self.market_data_service.get_mark_price(position.symbol)
        # Logic to monitor the position based on mark price and other criteria
        # This could include checking for stop-loss, take-profit, etc.
        print(f"Monitoring position: {position.symbol} | Current Mark Price: {mark_price}")