# Migration Guide - Futures Monitor → Trading Bot Platform (DDD)

## 📋 Overview

This guide helps migrate from the old `src/` structure to the new DDD architecture in `src/trading/`.

**Old Structure:**
```
src/
├── domain/entities/       # Anemic entities
├── application/services/  # Fat services
├── infrastructure/        # Binance specific
└── presentation/          # Terminal UI (to be removed)
```

**New Structure:**
```
src/trading/
├── shared/kernel/         # DDD base classes
├── domain/               # 7 bounded contexts
├── application/          # Use cases
├── infrastructure/       # Adapters
└── interfaces/           # API/CLI
```

## 🎯 Migration Strategy

### Phase 1: Setup (Current)
✅ Create new directory structure  
✅ Create DDD kernel (Entity, AggregateRoot, etc.)  
✅ Migrate performance module  
✅ Create shared types & errors  

### Phase 2: Domain Migration (Next)
🔄 Migrate entities to aggregates  
🔄 Extract value objects  
🔄 Define domain events  

### Phase 3: Application Layer
⏳ Convert services to use cases  
⏳ Create DTOs  
⏳ Implement event handlers  

### Phase 4: Infrastructure
⏳ Create exchange adapters  
⏳ Implement repositories  
⏳ Setup persistence  

### Phase 5: Interfaces
⏳ Create REST API  
⏳ Remove terminal UI  
⏳ Add background workers  

## 📦 Code Mapping

### Entities → Aggregates

**Old: `src/domain/entities/account.py`**
```python
class Account:
    def __init__(self, balances: Dict[str, Balance]):
        self.balances = balances
```

**New: `src/trading/domain/portfolio/aggregates/portfolio_aggregate.py`**
```python
from src.trading.shared.kernel.aggregate_root import AggregateRoot
from src.trading.domain.portfolio.events import BalanceUpdatedEvent

class PortfolioAggregate(AggregateRoot):
    def __init__(self, account_id: str):
        super().__init__()
        self._account_id = account_id
        self._balances: Dict[str, AssetBalance] = {}
    
    def update_balance(self, asset: str, free: Decimal, locked: Decimal):
        """Update balance and emit domain event"""
        self._balances[asset] = AssetBalance(asset, free, locked)
        self._add_domain_event(
            BalanceUpdatedEvent(self._account_id, asset, free, locked)
        )
```

**Migration Steps:**
1. Extract business logic from old entity
2. Identify state transitions (these become methods)
3. Add domain events for state changes
4. Move validation logic into value objects
5. Convert to AggregateRoot

---

### Services → Use Cases

**Old: `src/application/services/account_service.py`**
```python
class AccountService:
    def __init__(self, repo, rest_client, ws_client):
        self.repo = repo
        self.rest_client = rest_client
        self.ws_client = ws_client
    
    async def fetch_account(self) -> Account:
        # Mixes: API call + domain logic + persistence
        data = await self.rest_client.fetch_account()
        account = Account(...)
        await self.repo.save(account)
        return account
```

**New: `src/trading/application/use_cases/fetch_account_snapshot.py`**
```python
from src.trading.application.dto.account_dto import AccountSnapshotDTO
from src.trading.infrastructure.exchange.exchange_gateway import ExchangeGateway

class FetchAccountSnapshotUseCase:
    def __init__(self, 
                 exchange_gateway: ExchangeGateway,
                 portfolio_repository: PortfolioRepository):
        self._gateway = exchange_gateway
        self._repository = portfolio_repository
    
    async def execute(self, account_id: str) -> AccountSnapshotDTO:
        # Single responsibility: orchestrate
        raw_data = await self._gateway.get_account_info()
        
        portfolio = self._repository.get_by_account(account_id)
        portfolio.sync_from_exchange(raw_data)
        
        await self._repository.save(portfolio)
        
        return AccountSnapshotDTO.from_aggregate(portfolio)
```

**Migration Steps:**
1. Identify business operation (use case name)
2. Extract API logic → Infrastructure adapter
3. Extract domain logic → Aggregate method
4. Use case only orchestrates
5. Return DTO, not domain entity

---

### Infrastructure → Adapters

**Old: `src/infrastructure/binance/rest_client.py`**
```python
class BinanceRestClient:
    async def fetch_account(self) -> Dict:
        response = await self._session.get("/fapi/v2/account")
        return response.json()
```

**New: `src/trading/infrastructure/exchange/binance_adapter.py`**
```python
from src.trading.infrastructure.exchange.exchange_gateway import ExchangeGateway

class BinanceAdapter(ExchangeGateway):
    """Adapter pattern: Binance API → Domain interface"""
    
    async def get_account_info(self) -> AccountInfoData:
        """Convert Binance response to domain data structure"""
        response = await self._http_client.get("/fapi/v2/account")
        
        return AccountInfoData(
            account_id=response["accountAlias"],
            balances=[
                BalanceData(asset=b["asset"], 
                           free=Decimal(b["availableBalance"]),
                           locked=Decimal(b["balance"]) - Decimal(b["availableBalance"]))
                for b in response["assets"]
            ]
        )
```

**Migration Steps:**
1. Create domain interface (Gateway)
2. Implement adapter for specific exchange
3. Convert API responses to domain data structures
4. Handle errors with domain exceptions

---

### Value Objects

**Old: Primitives everywhere**
```python
symbol = "BTCUSDT"  # Just a string
price = 50000.0     # Just a float
```

**New: `src/trading/shared/types/symbol.py`**
```python
from src.trading.shared.kernel.value_object import ValueObject

class Symbol(ValueObject):
    def __init__(self, base: str, quote: str, exchange: str = "binance"):
        self._base = base.upper()
        self._quote = quote.upper()
        self._exchange = exchange.lower()
    
    def to_exchange_format(self) -> str:
        return f"{self._base}{self._quote}"
    
    def __eq__(self, other):
        if not isinstance(other, Symbol):
            return False
        return (self._base == other._base and 
                self._quote == other._quote)
```

**Migration Steps:**
1. Find repeated validation logic
2. Create value object class
3. Move validation to __init__
4. Add domain behavior methods
5. Replace primitives with value objects

---

## 🗂️ File-by-File Migration

### ✅ Completed

| Old File | New Location | Status |
|----------|--------------|--------|
| `src/shared/performance/` | `src/trading/performance/` | ✅ Migrated |
| - | `src/trading/shared/kernel/` | ✅ Created |
| - | `src/trading/shared/types/` | ✅ Created |

### 🔄 In Progress

| Old File | New Location | Action |
|----------|--------------|--------|
| `src/domain/entities/account.py` | `src/trading/domain/portfolio/aggregates/portfolio_aggregate.py` | Convert to aggregate |
| `src/domain/entities/position.py` | `src/trading/domain/portfolio/entities/asset_position.py` | Extract from aggregate |
| `src/domain/entities/balance.py` | `src/trading/domain/portfolio/value_objects/asset_balance.py` | Convert to value object |
| `src/domain/entities/orderbook.py` | `src/trading/domain/marketdata/entities/depth_snapshot.py` | Move to MarketData BC |

### ⏳ Pending

| Old File | New Location | Action |
|----------|--------------|--------|
| `src/application/services/account_service.py` | Multiple use cases | Split into: `FetchAccountSnapshot`, `StreamAccountUpdates` |
| `src/application/services/market_data_service.py` | `src/trading/infrastructure/marketdata/` | Convert to adapter |
| `src/infrastructure/binance/rest_client.py` | `src/trading/infrastructure/exchange/binance_adapter.py` | Implement ExchangeGateway |
| `src/infrastructure/binance/websocket_client.py` | `src/trading/infrastructure/messaging/binance_stream.py` | Convert to event stream |

### 🗑️ To Remove

| Old File | Reason |
|----------|--------|
| `src/presentation/` | Remove terminal UI (focus on API) |
| `src/main.py` | Replace with new entry point |

---

## 🔧 Implementation Examples

### Example 1: Portfolio Aggregate

Create `src/trading/domain/portfolio/aggregates/portfolio_aggregate.py`:

```python
from decimal import Decimal
from typing import Dict, Optional
from src.trading.shared.kernel.aggregate_root import AggregateRoot
from src.trading.domain.portfolio.entities.asset_position import AssetPosition
from src.trading.domain.portfolio.value_objects.asset_balance import AssetBalance
from src.trading.domain.portfolio.events import (
    BalanceUpdatedEvent, PositionOpenedEvent, PositionClosedEvent
)

class PortfolioAggregate(AggregateRoot):
    """
    Aggregate managing all assets and positions for an account.
    
    Invariants:
    - Total balance = free + locked
    - Position margin <= available balance
    - Can't open position without sufficient balance
    """
    
    def __init__(self, account_id: str):
        super().__init__()
        self._account_id = account_id
        self._balances: Dict[str, AssetBalance] = {}
        self._positions: Dict[str, AssetPosition] = {}
    
    def update_balance(self, asset: str, free: Decimal, locked: Decimal):
        """Update asset balance from exchange"""
        old_balance = self._balances.get(asset)
        new_balance = AssetBalance(asset, free, locked)
        
        self._balances[asset] = new_balance
        
        self._add_domain_event(
            BalanceUpdatedEvent(
                account_id=self._account_id,
                asset=asset,
                free=free,
                locked=locked,
                old_free=old_balance.free if old_balance else Decimal(0)
            )
        )
    
    def open_position(self, symbol: str, quantity: Decimal, 
                      entry_price: Decimal, leverage: int):
        """Open new position with validation"""
        # Business rule: check sufficient balance
        required_margin = (quantity * entry_price) / leverage
        available = self._balances.get("USDT", AssetBalance("USDT", Decimal(0), Decimal(0))).free
        
        if required_margin > available:
            raise InsufficientBalanceError(
                f"Need {required_margin} USDT, have {available}"
            )
        
        position = AssetPosition(symbol, quantity, entry_price, leverage)
        self._positions[symbol] = position
        
        self._add_domain_event(
            PositionOpenedEvent(
                account_id=self._account_id,
                symbol=symbol,
                quantity=quantity,
                entry_price=entry_price,
                leverage=leverage
            )
        )
    
    def get_total_equity(self) -> Decimal:
        """Calculate total equity (balance + unrealized PnL)"""
        balance = sum(b.total for b in self._balances.values())
        unrealized_pnl = sum(p.unrealized_pnl for p in self._positions.values())
        return balance + unrealized_pnl
```

### Example 2: Use Case

Create `src/trading/application/use_cases/portfolio/sync_portfolio.py`:

```python
from src.trading.domain.portfolio.aggregates.portfolio_aggregate import PortfolioAggregate
from src.trading.domain.portfolio.repositories.portfolio_repository import PortfolioRepository
from src.trading.infrastructure.exchange.exchange_gateway import ExchangeGateway

class SyncPortfolioUseCase:
    """Sync portfolio state from exchange"""
    
    def __init__(self,
                 exchange_gateway: ExchangeGateway,
                 portfolio_repository: PortfolioRepository):
        self._gateway = exchange_gateway
        self._repository = portfolio_repository
    
    async def execute(self, account_id: str) -> None:
        # Fetch from exchange
        account_data = await self._gateway.get_account_info()
        
        # Get or create aggregate
        portfolio = (await self._repository.get_by_account(account_id) 
                     or PortfolioAggregate(account_id))
        
        # Update domain model
        for balance_data in account_data.balances:
            portfolio.update_balance(
                balance_data.asset,
                balance_data.free,
                balance_data.locked
            )
        
        for position_data in account_data.positions:
            if position_data.quantity > 0:
                portfolio.open_position(
                    position_data.symbol,
                    position_data.quantity,
                    position_data.entry_price,
                    position_data.leverage
                )
        
        # Persist
        await self._repository.save(portfolio)
        
        # Domain events will be published by repository
```

### Example 3: Infrastructure Adapter

Create `src/trading/infrastructure/exchange/binance_adapter.py`:

```python
from decimal import Decimal
from src.trading.infrastructure.exchange.exchange_gateway import ExchangeGateway
from src.trading.infrastructure.exchange.dto import AccountInfoData, BalanceData
from src.trading.infrastructure.http.http_client import HTTPClient

class BinanceAdapter(ExchangeGateway):
    """Binance Futures API adapter"""
    
    def __init__(self, http_client: HTTPClient):
        self._http = http_client
    
    async def get_account_info(self) -> AccountInfoData:
        """Get account balances and positions"""
        response = await self._http.get("/fapi/v2/account")
        
        return AccountInfoData(
            account_id=response.get("accountAlias", "main"),
            balances=[
                BalanceData(
                    asset=asset["asset"],
                    free=Decimal(asset["availableBalance"]),
                    locked=Decimal(asset["balance"]) - Decimal(asset["availableBalance"])
                )
                for asset in response["assets"]
                if Decimal(asset["balance"]) > 0
            ],
            positions=[
                PositionData(
                    symbol=pos["symbol"],
                    quantity=abs(Decimal(pos["positionAmt"])),
                    side="LONG" if Decimal(pos["positionAmt"]) > 0 else "SHORT",
                    entry_price=Decimal(pos["entryPrice"]),
                    leverage=int(pos["leverage"]),
                    unrealized_pnl=Decimal(pos["unrealizedProfit"])
                )
                for pos in response["positions"]
                if Decimal(pos["positionAmt"]) != 0
            ]
        )
```

---

## ✅ Checklist

### Phase 1: Foundation
- [x] Create directory structure
- [x] Create DDD kernel
- [x] Migrate performance module
- [x] Create shared types
- [ ] Create __init__.py files

### Phase 2: Domain
- [ ] Create PortfolioAggregate
- [ ] Create MarketData entities
- [ ] Create ExecutionAggregate
- [ ] Define domain events
- [ ] Create repositories interfaces

### Phase 3: Application
- [ ] Create use cases
- [ ] Create DTOs
- [ ] Implement event handlers

### Phase 4: Infrastructure
- [ ] Create BinanceAdapter
- [ ] Implement repositories
- [ ] Setup event bus
- [ ] Add caching layer

### Phase 5: Interfaces
- [ ] Create REST API
- [ ] Add CLI commands
- [ ] Remove terminal UI

---

## 🚀 Next Steps

1. **Review this guide** and understand mappings
2. **Start with PortfolioAggregate** (most critical)
3. **Create use cases** one by one
4. **Test each layer** independently
5. **Wire everything** in DI container

## 📚 References

- [DDD Overview](./ddd-overview.md)
- [Architecture](./architecture.md)
- [Performance Guide](./PERFORMANCE_MODULE.md)
