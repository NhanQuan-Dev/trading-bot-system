"""
Market Data Service - Quản lý dữ liệu thị trường real-time.

Mục đích:
- Stream giá mark price của các symbol được theo dõi qua WebSocket từ Binance.

Liên quan đến file nào:
- Sử dụng RestClient từ infrastructure/binance/rest_client.py để API calls nếu cần.
- Sử dụng Settings từ infrastructure/config/settings.py cho config.
- Khi gặp bug: Kiểm tra WebSocket connection, verify TRACKED_SYMBOLS trong settings, hoặc log errors trong shared/exceptions/.
"""

import asyncio
import json
import websockets
from typing import Dict
from infrastructure.binance.rest_client import RestClient
from infrastructure.config.settings import Settings

class MarketDataService:
    def __init__(self, rest_client: RestClient, settings: Settings):
        # Khởi tạo với RestClient để gọi API và Settings cho config
        self.rest_client = rest_client
        self.settings = settings

    async def stream_mark_prices(self, state: dict, state_lock: asyncio.Lock):
        """Stream mark prices for tracked symbols - Stream giá mark price của các symbol"""
        # Tạo streams cho các symbol được theo dõi (chuyển lowercase)
        streams = "/".join(f"{sym.lower()}@markPrice" for sym in self.settings.TRACKED_SYMBOLS)
        url = f"{self.settings.WS_BASE}/stream?streams={streams}"
        print(f"[WS markPrice] Connecting to: {url}")
        
        while True:
            try:
                # Kết nối WebSocket với ping để giữ alive
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    print("[WS markPrice] Connected")
                    async for msg in ws:
                        # Nhận message từ WebSocket
                        payload = json.loads(msg)
                        data = payload.get("data", {})
                        sym = data.get("s")  # Symbol
                        price = data.get("p")  # Price
                        
                        if sym and price:
                            # Cập nhật state với giá mới
                            async with state_lock:
                                state["mark_prices"][sym] = price
                                
            except Exception as e:
                # Nếu lỗi, log và reconnect sau 3s
                print(f"[WS markPrice] Error: {e}, reconnecting in 3s...")
                await asyncio.sleep(3)