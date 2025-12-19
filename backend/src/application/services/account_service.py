"""
Account Service - Quản lý dữ liệu tài khoản và cập nhật real-time.

Mục đích:
- Fetch snapshot tài khoản ban đầu từ Binance.
- Stream cập nhật tài khoản qua WebSocket (balances, positions).

Liên quan đến file nào:
- Sử dụng AccountRepository từ domain/repositories/account_repository.py để lấy dữ liệu.
- Sử dụng Account entity từ domain/entities/account.py để định nghĩa dữ liệu.
- Khi gặp bug: Kiểm tra log WebSocket, verify API key/secret trong infrastructure/binance/, hoặc test với mock data từ in_memory_account_repository.py.
"""

import asyncio
import json
import websockets
from domain.repositories.account_repository import AccountRepository
from domain.entities.account import Account
from shared.exceptions.api_exception import APIException

class AccountService:
    def __init__(self, account_repository: AccountRepository):
        # Khởi tạo service với repository để truy cập dữ liệu tài khoản
        self.account_repository = account_repository

    async def fetch_account_snapshot(self) -> Account:
        """Fetch initial account snapshot - Lấy dữ liệu tài khoản ban đầu"""
        try:
            # Gọi repository để lấy dữ liệu từ API hoặc storage
            account = await self.account_repository.fetch_account_data()
            return account
        except Exception as e:
            # Nếu lỗi, raise exception với thông tin chi tiết
            raise APIException(f"Failed to fetch account snapshot: {e}") from e

    async def stream_account_updates(self, state: dict, state_lock: asyncio.Lock):
        """Stream account updates via WebSocket User Data Stream - Stream cập nhật tài khoản real-time qua WebSocket"""
        # Lấy listen key để kết nối WebSocket
        listen_key = self.account_repository.get_listen_key()
        url = f"wss://fstream.binancefuture.com/ws/{listen_key}"
        print(f"[WS userData] Connecting to: {url}")
        
        while True:
            try:
                # Kết nối WebSocket với ping để giữ alive
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    print("[WS userData] Connected")
                    async for msg in ws:
                        # Nhận message từ WebSocket
                        data = json.loads(msg)
                        etype = data.get("e")
                        
                        if etype == "ACCOUNT_UPDATE":
                            # Xử lý cập nhật tài khoản (balances, positions)
                            await self._handle_account_update(data, state, state_lock)
                        elif etype == "ORDER_TRADE_UPDATE":
                            # Log cập nhật order (không xử lý sâu ở đây)
                            print(f"[WS ORDER] Order update received: {data.get('o', {}).get('X')}")
                            
            except Exception as e:
                # Nếu lỗi, log và reconnect sau 3s
                print(f"[WS userData] Error: {e}, reconnecting in 3s...")
                await asyncio.sleep(3)
    
    async def _handle_account_update(self, data: dict, state: dict, state_lock: asyncio.Lock):
        """Handle ACCOUNT_UPDATE event - Xử lý sự kiện cập nhật tài khoản"""
        acc = data.get("a", {})
        balances_data = acc.get("B", [])
        positions_data = acc.get("P", [])
        
        async with state_lock:
            # Cập nhật balances (số dư tài sản)
            if balances_data:
                balances = []
                for b in balances_data:
                    balances.append({
                        "a": b["a"],  # Asset symbol
                        "wb": b["wb"],  # Wallet balance
                        "cw": b.get("cw"),  # Cross wallet
                    })
                state["balances"] = balances
                print(f"[WS] Balance updated: {len(balances)} assets")
            
            # Cập nhật positions (vị thế giao dịch)
            if positions_data:
                positions = state["positions"]
                for p in positions_data:
                    sym = p["s"]  # Symbol
                    pos_amt = float(p["pa"])  # Position amount
                    position_side = p.get("ps", "BOTH")  # Position side
                    key = (sym, position_side)
                    
                    if abs(pos_amt) > 1e-8:  # Nếu có vị thế (không zero)
                        positions[key] = {
                            "positionAmt": p["pa"],
                            "entryPrice": p["ep"],
                            "leverage": p.get("l", "0"),
                            "unrealizedPnL": p.get("up", "0"),
                            "marginType": p.get("mt", "cross"),
                            "positionSide": position_side,
                        }
                        print(f"[WS] Position updated: {sym} {position_side}")
                    else:
                        # Nếu vị thế đóng, xóa khỏi state
                        if key in positions:
                            del positions[key]
                            print(f"[WS] Position closed: {sym} {position_side}")
                state["positions"] = positions