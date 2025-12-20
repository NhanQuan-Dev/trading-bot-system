# Creating New Trading Strategies

This guide explains how to add new trading strategies to the backtesting system.

## Quick Start

To add a new strategy, you only need to create **one file**:

```
backend/src/trading/strategies/implementations/your_strategy.py
```

The system will **auto-discover** your strategy - no registration required!

---

## Step 1: Create Strategy File

Create a new file in `backend/src/trading/strategies/implementations/`:

```python
# implementations/my_awesome_strategy.py
from decimal import Decimal
from typing import Any, Dict
from ..base import StrategyBase

class MyAwesomeStrategy(StrategyBase):
    # Required: Strategy name (used in registry)
    name = "My Awesome Strategy"
    
    # Required: Description shown in UI
    description = "A custom strategy that does amazing things."
    
    def __init__(self, exchange, config: Dict[str, Any]):
        super().__init__(exchange, config)
        # Initialize your parameters from config
        self.my_param = config.get("my_param", 10)
    
    async def on_tick(self, market_data: Any):
        """
        Called on every price update (for live trading).
        
        Args:
            market_data: {"symbol": "BTC/USDT", "price": 50000.0, ...}
        """
        symbol = market_data.get("symbol")
        price = float(market_data.get("price"))
        
        # Your trading logic here
        if should_buy:
            await self.buy(symbol, Decimal("0.001"))
        elif should_sell:
            await self.sell(symbol, Decimal("0.001"))
```

---

## Step 2: Add Backtest Support

For backtesting, update `backend/src/trading/strategies/backtest_adapter.py`:

### 2.1 Add Strategy ID Mapping

```python
STRATEGY_ID_TO_NAME = {
    # ... existing strategies ...
    "00000000-0000-0000-0000-000000000006": "My Awesome Strategy",  # Add your UUID
}
```

### 2.2 Add Signal Logic

In `BacktestStrategyAdapter._setup_strategy()`:

```python
elif self.strategy_name == "My Awesome Strategy":
    self.my_param = int(self.config.get("my_param", 10))
    self.min_history = 20
```

In `BacktestStrategyAdapter.generate_signal()`:

```python
elif self.strategy_name == "My Awesome Strategy":
    return self._my_awesome_signal(position)
```

Add your signal method:

```python
def _my_awesome_signal(self, position: Optional[Dict]) -> Optional[Dict]:
    """Your strategy logic for backtesting."""
    closes = [c["close"] for c in self.history]
    
    # Your signal logic
    if buy_condition and not position:
        return {"type": "buy"}
    elif sell_condition and position:
        return {"type": "close"}
    
    return None
```

---

## Step 3: Register in Database (Optional)

Add to `backend/src/trading/infrastructure/persistence/seed_strategies.py`:

```python
STRATEGIES = [
    # ... existing ...
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000006"),
        "name": "My Awesome Strategy",
        "strategy_type": "CUSTOM",
        "description": "A custom strategy that does amazing things.",
        "parameters": {"my_param": 10}
    }
]
```

---

## Step 4: Update Frontend (Optional)

Add to `frontend/src/pages/BacktestDetail.tsx` → `strategyMap`:

```typescript
const strategyMap: Record<string, string> = {
    // ... existing ...
    '00000000-0000-0000-0000-000000000006': 'My Awesome Strategy',
};
```

---

## Architecture Overview

```
├── strategies/
│   ├── base.py                 # StrategyBase - inherit from this
│   ├── registry.py             # Auto-discovers strategies (live trading)
│   ├── backtest_adapter.py     # Converts strategies for backtesting
│   └── implementations/
│       ├── scalping.py         # Scalping (EMA crossover)
│       ├── grid_trading.py     # Grid Trading (price levels)
│       ├── mean_reversion.py   # Mean Reversion (Bollinger Bands)
│       ├── trend_following.py  # Trend Following (RSI)
│       ├── arbitrage.py        # Arbitrage (volatility)
│       └── your_strategy.py    # Your new strategy
```

---

## Signal Types

Your strategy should return one of these signal types:

| Signal | Description |
|--------|-------------|
| `{"type": "buy"}` | Open a LONG position |
| `{"type": "sell"}` | Open a SHORT position |
| `{"type": "close"}` | Close current position |
| `None` | No action |

---

## Available Helper Methods

In `backtest_adapter.py`:

```python
# EMA (Exponential Moving Average)
ema_values = self._ema(closes, period=14)

# RSI (Relative Strength Index)
rsi_value = self._rsi(closes, period=14)
```

---

## Example: Dual MA Crossover Strategy

```python
# In backtest_adapter.py

def _dual_ma_signal(self, position: Optional[Dict]) -> Optional[Dict]:
    """Dual Moving Average Crossover."""
    closes = [c["close"] for c in self.history]
    
    ma_fast = sum(closes[-10:]) / 10  # 10-period SMA
    ma_slow = sum(closes[-20:]) / 20  # 20-period SMA
    
    prev_closes = closes[:-1]
    prev_fast = sum(prev_closes[-10:]) / 10
    prev_slow = sum(prev_closes[-20:]) / 20
    
    # Golden cross
    if prev_fast <= prev_slow and ma_fast > ma_slow:
        if not position:
            return {"type": "buy"}
    
    # Death cross
    elif prev_fast >= prev_slow and ma_fast < ma_slow:
        if position:
            return {"type": "close"}
    
    return None
```

---

## Checklist for New Strategies

- [ ] Create file in `implementations/`
- [ ] Set `name` and `description` class attributes
- [ ] Implement `async on_tick()` for live trading
- [ ] Add UUID to `STRATEGY_ID_TO_NAME` in `backtest_adapter.py`
- [ ] Add `_setup_strategy()` config in `backtest_adapter.py`
- [ ] Add `_your_strategy_signal()` method in `backtest_adapter.py`
- [ ] Add to `seed_strategies.py` (if needed in database)
- [ ] Update frontend `strategyMap` (if needed)
- [ ] Test with backtest

---

**Last Updated:** 2025-12-20
