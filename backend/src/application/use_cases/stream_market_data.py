from src.infrastructure.binance.websocket_client import WebSocketClient
from src.application.services.market_data_service import MarketDataService

class StreamMarketData:
    def __init__(self, market_data_service: MarketDataService, websocket_client: WebSocketClient):
        self.market_data_service = market_data_service
        self.websocket_client = websocket_client

    async def stream(self):
        await self.websocket_client.connect()
        try:
            async for message in self.websocket_client.receive():
                await self.market_data_service.process_market_data(message)
        except Exception as e:
            print(f"Error while streaming market data: {e}")
        finally:
            await self.websocket_client.disconnect()