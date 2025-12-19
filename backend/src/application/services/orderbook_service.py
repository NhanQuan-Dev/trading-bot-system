"""
OrderBook Service - Quản lý dữ liệu orderbook (sổ lệnh) real-time.

Mục đích:
- Stream orderbook depth (bids/asks) của symbol được theo dõi qua WebSocket từ Binance.

Liên quan đến file nào:
- Sử dụng RestClient từ infrastructure/binance/rest_client.py nếu cần fetch ban đầu.
- Sử dụng Settings từ infrastructure/config/settings.py cho ORDERBOOK_SYMBOL.
- Khi gặp bug: Kiểm tra WebSocket, verify symbol trong settings, hoặc log trong shared/exceptions/.
"""

import asyncio
import json
import websockets
from infrastructure.binance.rest_client import RestClient
from infrastructure.config.settings import Settings

class OrderBookService:
    def __init__(self, rest_client: RestClient, settings: Settings):
        # Khởi tạo với RestClient và Settings
        self.rest_client = rest_client
        self.settings = settings

    async def stream_orderbook(self, state: dict, state_lock: asyncio.Lock):
        """Stream orderbook depth for the tracked symbol - Stream sổ lệnh của symbol"""
        # Tạo stream name cho orderbook depth 5 levels, update 100ms
        stream_name = f"{self.settings.ORDERBOOK_SYMBOL.lower()}@depth5@100ms"
        url = f"{self.settings.WS_BASE}/ws/{stream_name}"
        print(f"[WS orderbook] Connecting to: {url}")
        
        while True:
            try:
                # Kết nối WebSocket
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    print("[WS orderbook] Connected")
                    async for msg in ws:
                        # Nhận data orderbook
                        data = json.loads(msg)
                        # Parse bids (mua) và asks (bán): list of [price, quantity]
                        bids = [(b[0], b[1]) for b in data.get("b", [])]
                        asks = [(a[0], a[1]) for a in data.get("a", [])]
                        
                        # Cập nhật state
                        async with state_lock:
                            state["orderbook"]["bids"] = bids
                            state["orderbook"]["asks"] = asks
                            
            except Exception as e:
                # Log lỗi và reconnect
                print(f"[WS orderbook] Error: {e}, reconnecting in 3s...")
                await asyncio.sleep(3)