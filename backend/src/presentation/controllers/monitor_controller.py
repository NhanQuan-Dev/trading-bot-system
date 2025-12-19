import asyncio
from application.services.market_data_service import MarketDataService
from application.services.account_service import AccountService
from application.services.orderbook_service import OrderBookService
from presentation.ui.renderer import Renderer
from infrastructure.config.settings import Settings

class MonitorController:
    def __init__(self, account_service: AccountService, market_data_service: MarketDataService, 
                 orderbook_service: OrderBookService, renderer: Renderer, settings: Settings):
        self.account_service = account_service
        self.market_data_service = market_data_service
        self.orderbook_service = orderbook_service
        self.renderer = renderer
        self.settings = settings
        
        # State
        self.state = {
            "total_wallet_balance": None,
            "available_balance": None,
            "balances": [],
            "positions": {},
            "mark_prices": {},
            "orderbook": {"bids": [], "asks": []},
        }
        self.state_lock = asyncio.Lock()

    async def start_monitoring(self):
        """Start all monitoring tasks"""
        print("Starting Futures Monitor...")
        
        # Fetch initial snapshot
        await self.fetch_initial_snapshot()
        
        # Start all async tasks
        await asyncio.gather(
            self.render_loop(),
            self.market_data_service.stream_mark_prices(self.state, self.state_lock),
            self.orderbook_service.stream_orderbook(self.state, self.state_lock),
            self.account_service.stream_account_updates(self.state, self.state_lock),
        )
    
    async def fetch_initial_snapshot(self):
        """Fetch initial account snapshot"""
        account = await self.account_service.fetch_account_snapshot()
        async with self.state_lock:
            self.state["total_wallet_balance"] = account.total_wallet_balance
            self.state["available_balance"] = account.available_balance
            self.state["balances"] = [
                {"a": b.asset, "wb": b.wallet_balance, "cw": b.cross_wallet_balance}
                for b in account.balances
            ]
        print(f"Initial snapshot loaded: Total={account.total_wallet_balance}, Available={account.available_balance}")
    
    async def render_loop(self):
        """Main render loop"""
        await asyncio.sleep(2)  # Wait for data to populate
        
        while True:
            async with self.state_lock:
                total_wallet = self.state["total_wallet_balance"]
                available = self.state["available_balance"]
                balances = list(self.state["balances"])
                positions = dict(self.state["positions"])
                mark_prices = dict(self.state["mark_prices"])
                orderbook = dict(self.state["orderbook"])
            
            self.renderer.clear_screen()
            self.renderer.render_mark_prices(mark_prices)
            self.renderer.render_balances(total_wallet, available, balances)
            self.renderer.render_positions(positions)
            self.renderer.render_orderbook(orderbook)
            
            await asyncio.sleep(self.settings.RENDER_INTERVAL)