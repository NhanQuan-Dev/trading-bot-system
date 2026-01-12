# Strategy Template Guide

Tài liệu này mô tả cách viết Strategy chuẩn cho hệ thống Trading Bot.

## Các Module Có Sẵn (Không Cần Import)

Khi bạn viết code strategy trong UI, các biến sau **ĐÃ CÓ SẴN**:

| Biến | Mô tả |
|------|-------|
| `StrategyBase` | Class cha (PHẢI inherit) |
| `Decimal` | Decimal từ module `decimal` |
| `pd` | Pandas (`import pandas as pd`) |
| `ta` | Pandas TA (`import pandas_ta as ta`) |
| `np` | Numpy (`import numpy as np`) |
| `logger` | Logger (`logging.getLogger(...)`) |
| `Optional`, `Dict`, `Any`, `List` | Typing hints |

---

## Template Chuẩn

```python
class MyCustomStrategy(StrategyBase):
    # BẮT BUỘC: Tên hiển thị (dùng cho logging và UI)
    name = "My Custom Strategy"
    
    # TÙY CHỌN: Mô tả ngắn
    description = "Mô tả chiến lược của bạn ở đây."

    def __init__(self, exchange, config):
        """Khởi tạo strategy với config từ UI."""
        super().__init__(exchange, config)
        
        # Đọc parameters từ config (do user nhập trong UI)
        self.my_param = int(config.get("my_param", "10"))
        self.quantity = Decimal(str(config.get("quantity", "0.001")))
        
        # State tracking
        self.history = []

    async def on_tick(self, market_data):
        """
        Được gọi khi có dữ liệu thị trường mới (Live Trading).
        
        Args:
            market_data: Dict với keys như 'symbol', 'price', 'volume'
        """
        symbol = market_data.get("symbol")
        price = float(market_data.get("price"))
        
        # Logic trading của bạn ở đây
        # Ví dụ: Mua khi giá tăng
        if some_condition:
            await self.buy(symbol, self.quantity)
        elif other_condition:
            await self.sell(symbol, self.quantity)

    def calculate_signal(self, candle, idx, position):
        """
        Được gọi bởi Backtest Engine (BẮT BUỘC cho Backtesting).
        
        Args:
            candle: Dict với keys 'open', 'high', 'low', 'close', 'volume', 'timestamp'
            idx: Index của candle hiện tại trong dataset
            idx: Index của candle hiện tại trong dataset
            position: Object position hiện tại (None nếu không có).
                      Attributes quan trọng:
                      - `position.avg_entry_price` (Decimal): Giá vốn trung bình (LƯU Ý: Không dùng `entry_price`).
                      - `position.quantity` (Decimal): Khối lượng.
                      - `position.unrealized_pnl` (Decimal): Lãi/Lỗ chưa chốt.
        
        Returns:
            None: Không làm gì
            {"type": "open_long"}: Mở Long
            {"type": "open_short"}: Mở Short
            {"type": "close_position"}: Đóng vị thế
            Có thể thêm "quantity" và "metadata" trong dict
        """
        close_price = float(candle['close'])
        
        # Logic của bạn
        if should_buy and not position:
            return {
                "type": "open_long",
                "quantity": float(self.quantity),
                "metadata": {
                    "reason": "Giá tăng mạnh",
                    "indicator": "RSI > 70"
                }
            }
        elif should_sell and position:
            return {"type": "close_position"}
        
        return None
```

---

## Ví Dụ: Simple Moving Average Crossover

```python
class SMACrossStrategy(StrategyBase):
    name = "SMA Crossover"
    description = "Mua khi SMA ngắn cắt lên SMA dài"

    def __init__(self, exchange, config):
        super().__init__(exchange, config)
        self.fast_period = int(config.get("fast_period", "10"))
        self.slow_period = int(config.get("slow_period", "30"))
        self.quantity = Decimal(str(config.get("quantity", "0.01")))
        self.history = []

    async def on_tick(self, market_data):
        # Live trading logic (optional if only backtesting)
        pass

    def calculate_signal(self, candle, idx, position):
        self.history.append(float(candle['close']))
        
        if len(self.history) < self.slow_period:
            return None
        
        # Tính SMA
        fast_sma = sum(self.history[-self.fast_period:]) / self.fast_period
        slow_sma = sum(self.history[-self.slow_period:]) / self.slow_period
        
        # Crossover logic
        if fast_sma > slow_sma and not position:
            return {"type": "open_long", "metadata": {"fast": fast_sma, "slow": slow_sma}}
        elif fast_sma < slow_sma and position:
            return {"type": "close_position"}
        
        return None
```

---

## Lưu Ý Quan Trọng

1. **KHÔNG import gì cả** - Tất cả các thư viện data science (pandas, numpy, ta-lib) đã có sẵn.
   - Tuy nhiên, các thư viện chuẩn như `datetime`, `math`, `random` vẫn **CẦN import** nếu sử dụng.
2. **PHẢI inherit từ `StrategyBase`**
3. **PHẢI có `name` attribute**
4. **PHẢI có `calculate_signal()` method để chạy Backtest**
   - **LƯU Ý**: Sử dụng `position.avg_entry_price` thay vì `entry_price`.
5. **PHẢI có `on_tick()` method** (kể cả dummy `pass`) để tương thích với hệ thống.
6. **Sử dụng `Decimal` cho tiền/số lượng** để tránh lỗi floating point.
7. **Metadata trong signal** sẽ hiển thị khi xem chi tiết trade trong UI.
