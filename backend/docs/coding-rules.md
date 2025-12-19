# Coding Rules & Standards

## 🎯 General Principles

### 1. Domain-Driven Design First
- ✅ Business logic in domain layer
- ✅ Domain has NO infrastructure dependencies
- ✅ Use ubiquitous language (business terms)
- ❌ Never put business rules in application/infrastructure

### 2. Explicit Over Implicit
- ✅ Clear method names: `calculate_unrealized_pnl()`
- ✅ Explicit types: `Decimal` not `float`
- ❌ Magic numbers: Use named constants

### 3. Fail Fast
- ✅ Validate inputs immediately
- ✅ Raise specific exceptions
- ❌ Silent failures or None returns

---

## 📁 File Structure

### Naming Conventions

```python
# Files: snake_case
portfolio_aggregate.py
asset_balance.py
sync_portfolio_use_case.py

# Classes: PascalCase
class PortfolioAggregate:
class AssetBalance:
class SyncPortfolioUseCase:

# Functions/methods: snake_case
def calculate_total_equity(self):
def open_position(self, symbol: str):

# Constants: UPPER_SNAKE_CASE
MAX_POSITION_SIZE = Decimal("100")
DEFAULT_LEVERAGE = 10

# Private: Leading underscore
self._balances: Dict[str, AssetBalance]
def _validate_margin(self, required: Decimal):
```

### Directory Organization

```
src/trading/domain/portfolio/
├── aggregates/           # Root entities
│   └── portfolio_aggregate.py
├── entities/            # Part of aggregates
│   └── asset_position.py
├── value_objects/       # Immutable values
│   └── asset_balance.py
├── services/            # Domain services
│   └── pnl_calculator.py
├── policies/            # Business rules
│   └── risk_policy.py
├── events/              # Domain events
│   └── balance_updated_event.py
└── repositories/        # Repository interfaces
    └── portfolio_repository.py
```

---

## 🏗️ Domain Layer Rules

### Entities & Aggregates

```python
from src.trading.shared.kernel.aggregate_root import AggregateRoot
from decimal import Decimal

class PortfolioAggregate(AggregateRoot):
    """
    RULES:
    1. Private attributes (leading _)
    2. No setters - use methods with business meaning
    3. Validate in __init__ and methods
    4. Emit domain events on state changes
    """
    
    def __init__(self, account_id: str):
        super().__init__()
        
        # Validate immediately
        if not account_id or not account_id.strip():
            raise ValueError("account_id cannot be empty")
        
        # Private attributes
        self._account_id = account_id
        self._balances: Dict[str, AssetBalance] = {}
        self._positions: Dict[str, Position] = {}
    
    # ✅ Good: Business method name
    def open_position(self, symbol: str, quantity: Decimal, 
                      entry_price: Decimal, leverage: int):
        """Open new position with validation"""
        
        # Guard clauses
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if leverage < 1 or leverage > 125:
            raise ValueError("Leverage must be 1-125")
        
        # Business rule enforcement
        required_margin = self._calculate_required_margin(
            quantity, entry_price, leverage
        )
        if not self._has_sufficient_balance(required_margin):
            raise InsufficientBalanceError(
                f"Need {required_margin} USDT, have {self._get_available_balance()}"
            )
        
        # State change
        position = Position(symbol, quantity, entry_price, leverage)
        self._positions[symbol] = position
        
        # Domain event
        self._add_domain_event(
            PositionOpenedEvent(
                account_id=self._account_id,
                symbol=symbol,
                quantity=quantity,
                entry_price=entry_price,
                leverage=leverage
            )
        )
    
    # ❌ Bad: Setter
    def set_balance(self, asset: str, amount: Decimal):
        self._balances[asset] = amount  # No validation, no events!
    
    # Private helper methods
    def _calculate_required_margin(self, quantity: Decimal, 
                                   price: Decimal, leverage: int) -> Decimal:
        return (quantity * price) / leverage
    
    def _has_sufficient_balance(self, required: Decimal) -> bool:
        return self._get_available_balance() >= required
    
    def _get_available_balance(self) -> Decimal:
        usdt = self._balances.get("USDT")
        return usdt.free if usdt else Decimal(0)
    
    # ✅ Good: Read-only properties
    @property
    def account_id(self) -> str:
        """Immutable identifier"""
        return self._account_id
    
    @property
    def positions(self) -> Dict[str, Position]:
        """Return copy to prevent external modification"""
        return self._positions.copy()
```

### Value Objects

```python
from src.trading.shared.kernel.value_object import ValueObject
from decimal import Decimal

class Money(ValueObject):
    """
    RULES:
    1. Immutable (no setters)
    2. Validation in __init__
    3. Equality by value
    4. Business operations as methods
    """
    
    def __init__(self, amount: Decimal, currency: str = "USDT"):
        # Validate
        if not isinstance(amount, Decimal):
            raise TypeError("Amount must be Decimal")
        if currency not in ["USDT", "BTC", "ETH"]:
            raise ValueError(f"Unsupported currency: {currency}")
        
        # Private, immutable
        self._amount = amount
        self._currency = currency
    
    # ✅ Good: New instance, not mutation
    def add(self, other: 'Money') -> 'Money':
        """Add money (must be same currency)"""
        if self._currency != other._currency:
            raise ValueError("Cannot add different currencies")
        
        return Money(self._amount + other._amount, self._currency)
    
    def __add__(self, other: 'Money') -> 'Money':
        """Support + operator"""
        return self.add(other)
    
    # ✅ Good: Read-only properties
    @property
    def amount(self) -> Decimal:
        return self._amount
    
    @property
    def currency(self) -> str:
        return self._currency
    
    # Value equality
    def __eq__(self, other) -> bool:
        if not isinstance(other, Money):
            return False
        return (self._amount == other._amount and 
                self._currency == other._currency)
    
    def __hash__(self) -> int:
        return hash((self._amount, self._currency))
    
    def __repr__(self) -> str:
        return f"Money({self._amount}, {self._currency})"
```

### Domain Events

```python
from src.trading.shared.kernel.domain_event import DomainEvent
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass(frozen=True)  # Immutable!
class BalanceUpdatedEvent(DomainEvent):
    """
    RULES:
    1. Past tense name (something happened)
    2. Immutable (frozen=True)
    3. Include all relevant data
    4. Add timestamp in base class
    """
    
    account_id: str
    asset: str
    free: Decimal
    locked: Decimal
    old_free: Decimal  # For auditing
    
    # Don't add methods (just data)
```

### Repository Interfaces

```python
from abc import ABC, abstractmethod
from typing import Optional

class PortfolioRepository(ABC):
    """
    RULES:
    1. Interface in domain layer
    2. Implementation in infrastructure
    3. Methods use domain language
    4. One repository per aggregate root
    """
    
    @abstractmethod
    async def get_by_account(self, account_id: str) -> Optional[PortfolioAggregate]:
        """Get portfolio by account ID, or None if not found"""
        pass
    
    @abstractmethod
    async def save(self, portfolio: PortfolioAggregate) -> None:
        """Save portfolio and publish domain events"""
        pass
    
    # ❌ Bad: Technical names
    # def select_where_id(self, id: str): pass
    # def insert(self, data: dict): pass
```

---

## 📦 Application Layer Rules

### Use Cases

```python
from src.trading.application.dto.portfolio_dto import PortfolioSnapshotDTO

class SyncPortfolioUseCase:
    """
    RULES:
    1. One use case = one business operation
    2. Orchestration only (no business logic)
    3. Return DTOs, not domain entities
    4. Handle infrastructure errors
    """
    
    def __init__(self,
                 exchange_gateway: ExchangeGateway,
                 portfolio_repository: PortfolioRepository,
                 event_bus: DomainEventBus):
        # Dependency injection
        self._gateway = exchange_gateway
        self._repository = portfolio_repository
        self._event_bus = event_bus
    
    async def execute(self, account_id: str) -> PortfolioSnapshotDTO:
        """Execute use case and return DTO"""
        
        try:
            # 1. Get data from infrastructure
            account_data = await self._gateway.get_account_info()
            
            # 2. Load aggregate
            portfolio = (await self._repository.get_by_account(account_id)
                        or PortfolioAggregate(account_id))
            
            # 3. Call domain logic (aggregate methods)
            for balance in account_data.balances:
                portfolio.update_balance(
                    balance.asset, 
                    balance.free, 
                    balance.locked
                )
            
            # 4. Persist
            await self._repository.save(portfolio)
            
            # 5. Return DTO
            return PortfolioSnapshotDTO.from_aggregate(portfolio)
            
        except ExchangeAPIError as e:
            # Convert infrastructure errors to application errors
            raise ApplicationError(f"Failed to sync portfolio: {e}")
```

### DTOs (Data Transfer Objects)

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import List

@dataclass(frozen=True)
class PortfolioSnapshotDTO:
    """
    RULES:
    1. Immutable (frozen=True)
    2. Primitive types only (Decimal, str, int)
    3. No business logic
    4. Factory methods for conversion
    """
    
    account_id: str
    total_equity: Decimal
    available_balance: Decimal
    positions_count: int
    unrealized_pnl: Decimal
    
    @classmethod
    def from_aggregate(cls, portfolio: PortfolioAggregate) -> 'PortfolioSnapshotDTO':
        """Convert aggregate to DTO"""
        return cls(
            account_id=portfolio.account_id,
            total_equity=portfolio.get_total_equity().amount,
            available_balance=portfolio.get_available_balance().amount,
            positions_count=len(portfolio.positions),
            unrealized_pnl=portfolio.calculate_unrealized_pnl().amount
        )
```

---

## 🔌 Infrastructure Layer Rules

### Adapters

```python
from src.trading.infrastructure.exchange.exchange_gateway import ExchangeGateway
from src.trading.infrastructure.http.http_client import HTTPClient

class BinanceAdapter(ExchangeGateway):
    """
    RULES:
    1. Implement domain interface
    2. Convert API responses to domain data structures
    3. Handle API-specific errors
    4. No domain logic (just translation)
    """
    
    def __init__(self, http_client: HTTPClient, api_key: str, api_secret: str):
        self._http = http_client
        self._api_key = api_key
        self._api_secret = api_secret
    
    async def get_account_info(self) -> AccountInfoData:
        """Convert Binance response to domain data structure"""
        
        try:
            # Call external API
            response = await self._http.get(
                "/fapi/v2/account",
                headers=self._auth_headers()
            )
            
            # Convert to domain data structure (not domain entity!)
            return AccountInfoData(
                account_id=response.get("accountAlias", "main"),
                balances=[
                    BalanceData(
                        asset=b["asset"],
                        free=Decimal(b["availableBalance"]),
                        locked=Decimal(b["balance"]) - Decimal(b["availableBalance"])
                    )
                    for b in response["assets"]
                    if Decimal(b["balance"]) > 0
                ]
            )
            
        except HTTPError as e:
            # Convert to domain exception
            raise ExchangeAPIError(f"Binance API error: {e}")
    
    def _auth_headers(self) -> dict:
        """Binance-specific authentication"""
        timestamp = int(time.time() * 1000)
        signature = self._generate_signature(timestamp)
        return {
            "X-MBX-APIKEY": self._api_key,
            "timestamp": timestamp,
            "signature": signature
        }
```

### Repository Implementation

```python
from src.trading.domain.portfolio.repositories.portfolio_repository import PortfolioRepository
from src.trading.infrastructure.persistence.database import Database

class SqlPortfolioRepository(PortfolioRepository):
    """
    RULES:
    1. Implement domain interface
    2. Handle persistence details
    3. Publish domain events after save
    4. Map between domain and storage
    """
    
    def __init__(self, db: Database, event_bus: DomainEventBus):
        self._db = db
        self._event_bus = event_bus
    
    async def get_by_account(self, account_id: str) -> Optional[PortfolioAggregate]:
        """Reconstitute aggregate from database"""
        
        # Query
        row = await self._db.fetchone(
            "SELECT * FROM portfolios WHERE account_id = ?",
            (account_id,)
        )
        
        if not row:
            return None
        
        # Reconstitute aggregate
        portfolio = PortfolioAggregate(account_id)
        
        # Load balances
        balances = await self._db.fetchall(
            "SELECT * FROM balances WHERE account_id = ?",
            (account_id,)
        )
        for b in balances:
            portfolio._balances[b["asset"]] = AssetBalance(
                b["asset"], 
                Decimal(b["free"]), 
                Decimal(b["locked"])
            )
        
        # Load positions
        positions = await self._db.fetchall(
            "SELECT * FROM positions WHERE account_id = ?",
            (account_id,)
        )
        for p in positions:
            portfolio._positions[p["symbol"]] = Position(...)
        
        return portfolio
    
    async def save(self, portfolio: PortfolioAggregate) -> None:
        """Save aggregate and publish events"""
        
        async with self._db.transaction():
            # Save aggregate
            await self._db.execute(
                "UPDATE portfolios SET updated_at = ? WHERE account_id = ?",
                (datetime.utcnow(), portfolio.account_id)
            )
            
            # Save balances
            for asset, balance in portfolio._balances.items():
                await self._db.execute(
                    """
                    INSERT INTO balances (account_id, asset, free, locked)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (account_id, asset) DO UPDATE SET
                        free = excluded.free,
                        locked = excluded.locked
                    """,
                    (portfolio.account_id, asset, balance.free, balance.locked)
                )
            
            # Publish domain events
            for event in portfolio.domain_events:
                await self._event_bus.publish(event)
            
            portfolio.clear_domain_events()
```

---

## 🎨 Code Style

### Type Hints

```python
# ✅ Good: Always use type hints
from typing import Dict, List, Optional
from decimal import Decimal

def calculate_pnl(
    entry_price: Decimal,
    exit_price: Decimal,
    quantity: Decimal
) -> Decimal:
    return (exit_price - entry_price) * quantity

# ❌ Bad: No type hints
def calculate_pnl(entry_price, exit_price, quantity):
    return (exit_price - entry_price) * quantity
```

### Decimal vs Float

```python
from decimal import Decimal

# ✅ Good: Decimal for money/prices
price = Decimal("50000.50")
quantity = Decimal("0.001")
total = price * quantity  # Exact

# ❌ Bad: Float (rounding errors!)
price = 50000.50
quantity = 0.001
total = price * quantity  # 50.0005000000000006
```

### Error Handling

```python
# ✅ Good: Specific exceptions
class InsufficientBalanceError(DomainError):
    """Raised when balance is insufficient for operation"""
    pass

def open_position(self, ...):
    if not self._has_sufficient_balance(required):
        raise InsufficientBalanceError(
            f"Need {required} USDT, have {available}"
        )

# ❌ Bad: Generic exceptions
def open_position(self, ...):
    if not self._has_sufficient_balance(required):
        raise Exception("Not enough balance")  # Too generic!
```

### Guard Clauses

```python
# ✅ Good: Guard clauses at top
def open_position(self, symbol: str, quantity: Decimal, ...):
    # Validate first
    if not symbol:
        raise ValueError("Symbol cannot be empty")
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    if symbol in self._positions:
        raise PositionAlreadyExistsError(symbol)
    
    # Main logic
    position = Position(symbol, quantity, ...)
    self._positions[symbol] = position

# ❌ Bad: Nested ifs
def open_position(self, symbol: str, quantity: Decimal, ...):
    if symbol:
        if quantity > 0:
            if symbol not in self._positions:
                position = Position(...)  # Deeply nested!
```

### Docstrings

```python
def calculate_unrealized_pnl(self, market_prices: Dict[str, Decimal]) -> Money:
    """
    Calculate unrealized profit/loss for all positions.
    
    Args:
        market_prices: Current market prices by symbol
    
    Returns:
        Total unrealized P&L in USDT
    
    Raises:
        ValueError: If market_prices missing required symbols
    
    Example:
        >>> portfolio.calculate_unrealized_pnl({"BTCUSDT": Decimal("50000")})
        Money(Decimal("150.50"), "USDT")
    """
    pass
```

---

## ✅ Testing Rules

### Unit Tests (Domain)

```python
import pytest
from decimal import Decimal

def test_portfolio_opens_position_successfully():
    """Test: Portfolio can open position with sufficient balance"""
    # Arrange
    portfolio = PortfolioAggregate("test_account")
    portfolio.update_balance("USDT", Decimal("1000"), Decimal("0"))
    
    # Act
    portfolio.open_position(
        symbol="BTCUSDT",
        quantity=Decimal("0.1"),
        entry_price=Decimal("50000"),
        leverage=10
    )
    
    # Assert
    assert "BTCUSDT" in portfolio.positions
    assert portfolio.positions["BTCUSDT"].quantity == Decimal("0.1")
    assert len(portfolio.domain_events) == 2  # BalanceUpdated + PositionOpened

def test_portfolio_rejects_position_with_insufficient_balance():
    """Test: Portfolio raises error when balance insufficient"""
    # Arrange
    portfolio = PortfolioAggregate("test_account")
    portfolio.update_balance("USDT", Decimal("100"), Decimal("0"))
    
    # Act & Assert
    with pytest.raises(InsufficientBalanceError):
        portfolio.open_position(
            symbol="BTCUSDT",
            quantity=Decimal("1.0"),  # Needs 5000 USDT
            entry_price=Decimal("50000"),
            leverage=10
        )
```

### Integration Tests (Use Cases)

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_sync_portfolio_use_case():
    """Test: SyncPortfolioUseCase syncs from exchange"""
    # Arrange
    mock_gateway = AsyncMock()
    mock_gateway.get_account_info.return_value = AccountInfoData(
        account_id="test",
        balances=[BalanceData("USDT", Decimal("1000"), Decimal("0"))]
    )
    
    mock_repo = AsyncMock()
    mock_repo.get_by_account.return_value = None  # New portfolio
    
    use_case = SyncPortfolioUseCase(mock_gateway, mock_repo)
    
    # Act
    result = await use_case.execute("test")
    
    # Assert
    assert result.available_balance == Decimal("1000")
    mock_repo.save.assert_called_once()
```

---

## 🚫 Common Mistakes

### 1. Anemic Domain Model
```python
# ❌ Bad: Just data, no behavior
class Portfolio:
    def __init__(self):
        self.balances = {}

# Business logic in service
class PortfolioService:
    def add_balance(self, portfolio, asset, amount):
        portfolio.balances[asset] = amount

# ✅ Good: Behavior in domain
class Portfolio:
    def update_balance(self, asset: str, free: Decimal, locked: Decimal):
        # Validation, events, business rules here
        pass
```

### 2. Domain Depending on Infrastructure
```python
# ❌ Bad: Domain imports infrastructure
from src.trading.infrastructure.binance.rest_client import BinanceClient

class PortfolioAggregate:
    def __init__(self, binance_client: BinanceClient):  # NO!
        self._client = binance_client

# ✅ Good: Domain defines interface
class ExchangeGateway(ABC):  # In domain layer
    @abstractmethod
    async def get_account_info(self): pass

class PortfolioAggregate:
    # No infrastructure dependency!
```

### 3. Exposing Mutable State
```python
# ❌ Bad: Direct access to mutable collection
class Portfolio:
    def __init__(self):
        self.positions: Dict[str, Position] = {}

portfolio.positions["BTCUSDT"] = Position(...)  # Bypass business rules!

# ✅ Good: Read-only access
class Portfolio:
    @property
    def positions(self) -> Dict[str, Position]:
        return self._positions.copy()  # Return copy
```

---

## 📚 Checklist

### Before Committing
- [ ] All type hints added
- [ ] Docstrings for public methods
- [ ] Tests pass (`pytest`)
- [ ] Code formatted (`black`, `isort`)
- [ ] Linting passes (`ruff`, `mypy`)
- [ ] No hardcoded values
- [ ] Error messages clear
- [ ] Domain logic in domain layer

### Code Review
- [ ] Business logic in correct layer?
- [ ] Dependencies point inward?
- [ ] Aggregates maintain invariants?
- [ ] Domain events emitted on state changes?
- [ ] DTOs used at boundaries?
- [ ] Specific exception types?

---

## 🔗 Related Docs

- [DDD Overview](./ddd-overview.md)
- [Architecture](./architecture.md)
- [Migration Guide](./MIGRATION_GUIDE.md)
