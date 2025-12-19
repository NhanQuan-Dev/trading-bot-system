# Domain-Driven Design (DDD) Overview

## 📚 What is DDD?

Domain-Driven Design is an approach to software development that:
- **Focuses on core business logic** (the "domain")
- **Uses ubiquitous language** (same terms as business)
- **Isolates complex logic** in well-defined boundaries
- **Models real-world processes** with code

## 🧱 Core Building Blocks

### 1. Entity
**Object with identity that persists over time**

```python
from src.trading.shared.kernel.entity import Entity

class Order(Entity):
    """Order with unique ID"""
    
    def __init__(self, order_id: str, symbol: str, quantity: Decimal):
        super().__init__(order_id)
        self._symbol = symbol
        self._quantity = quantity
    
    def __eq__(self, other):
        # Identity comparison (by ID)
        return isinstance(other, Order) and self.id == other.id

# Two orders with same data but different IDs are NOT equal
order1 = Order("123", "BTCUSDT", Decimal("0.1"))
order2 = Order("456", "BTCUSDT", Decimal("0.1"))
assert order1 != order2  # Different entities
```

**When to use:**
- Object has unique identifier
- Lifecycle matters (created → modified → deleted)
- Need to track changes over time

**Examples:** Order, Account, Position

---

### 2. Value Object
**Immutable object defined by its attributes**

```python
from src.trading.shared.kernel.value_object import ValueObject
from decimal import Decimal

class Price(ValueObject):
    """Price value object"""
    
    def __init__(self, amount: Decimal, currency: str = "USDT"):
        if amount < 0:
            raise ValueError("Price cannot be negative")
        self._amount = amount
        self._currency = currency
    
    def __eq__(self, other):
        # Value comparison (by attributes)
        return (isinstance(other, Price) and 
                self._amount == other._amount and
                self._currency == other._currency)

# Two prices with same values ARE equal
price1 = Price(Decimal("50000"), "USDT")
price2 = Price(Decimal("50000"), "USDT")
assert price1 == price2  # Same value
```

**When to use:**
- No unique identity needed
- Immutable (never changes after creation)
- Equality by value, not reference
- Contains validation logic

**Examples:** Money, Symbol, Timeframe, Price

---

### 3. Aggregate Root
**Cluster of entities with consistency boundary**

```python
from src.trading.shared.kernel.aggregate_root import AggregateRoot

class PortfolioAggregate(AggregateRoot):
    """Root entity managing account state"""
    
    def __init__(self, account_id: str):
        super().__init__()
        self._account_id = account_id
        self._balances: Dict[str, AssetBalance] = {}
        self._positions: Dict[str, Position] = {}
    
    def open_position(self, symbol: str, quantity: Decimal, 
                      entry_price: Decimal, leverage: int):
        """Business rule: Check sufficient margin"""
        required_margin = (quantity * entry_price) / leverage
        available = self._balances["USDT"].free
        
        # Invariant enforcement
        if required_margin > available:
            raise InsufficientBalanceError()
        
        # Create position
        position = Position(symbol, quantity, entry_price)
        self._positions[symbol] = position
        
        # Lock margin
        self._balances["USDT"].lock(required_margin)
        
        # Emit domain event
        self._add_domain_event(
            PositionOpenedEvent(self._account_id, symbol, quantity)
        )

# ALWAYS access positions through aggregate
portfolio = PortfolioAggregate("my_account")
portfolio.open_position("BTCUSDT", Decimal("0.1"), Decimal("50000"), 10)
# ❌ NEVER: position.quantity = Decimal("0.2")  # Bypass business rules!
```

**Responsibilities:**
1. **Enforce invariants** (business rules that must always be true)
2. **Control access** to entities inside
3. **Emit domain events** on state changes
4. **Transaction boundary** (save as unit)

**When to use:**
- Complex business logic with multiple entities
- Need to maintain consistency between entities
- Clear transactional boundary

**Examples:** PortfolioAggregate, OrderExecutionAggregate, StrategyAggregate

---

### 4. Domain Event
**Something important that happened**

```python
from src.trading.shared.kernel.domain_event import DomainEvent
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class BalanceUpdatedEvent(DomainEvent):
    """Event: Balance changed"""
    account_id: str
    asset: str
    free: Decimal
    locked: Decimal
    old_free: Decimal

# Emit from aggregate
class PortfolioAggregate(AggregateRoot):
    def update_balance(self, asset: str, free: Decimal, locked: Decimal):
        old_free = self._balances[asset].free if asset in self._balances else Decimal(0)
        
        self._balances[asset] = AssetBalance(asset, free, locked)
        
        # Record event
        self._add_domain_event(
            BalanceUpdatedEvent(
                account_id=self._account_id,
                asset=asset,
                free=free,
                locked=locked,
                old_free=old_free
            )
        )

# Handle event (in another bounded context)
class UpdateRiskOnBalanceChange:
    async def handle(self, event: BalanceUpdatedEvent):
        # React to balance change
        risk_aggregate = await self._repo.get(event.account_id)
        risk_aggregate.recalculate_exposure()
        await self._repo.save(risk_aggregate)
```

**Naming Convention:**
- Past tense (something happened)
- Specific: `BalanceUpdatedEvent`, not `BalanceChangedEvent`
- Immutable (frozen dataclass)

**When to use:**
- Trigger behavior in other contexts
- Audit log / event sourcing
- Async processing
- Decouple bounded contexts

**Examples:** OrderFilledEvent, PositionClosedEvent, RiskLimitExceededEvent

---

### 5. Repository
**Persistence abstraction for aggregates**

```python
from abc import ABC, abstractmethod

# Domain interface (in domain layer)
class PortfolioRepository(ABC):
    """Repository for PortfolioAggregate"""
    
    @abstractmethod
    async def get_by_account(self, account_id: str) -> Optional[PortfolioAggregate]:
        """Get portfolio or None"""
        pass
    
    @abstractmethod
    async def save(self, portfolio: PortfolioAggregate) -> None:
        """Save portfolio and publish events"""
        pass

# Implementation (in infrastructure layer)
class SqlPortfolioRepository(PortfolioRepository):
    async def get_by_account(self, account_id: str) -> Optional[PortfolioAggregate]:
        # Query database
        row = await self._db.fetchone(
            "SELECT * FROM portfolios WHERE account_id = ?",
            (account_id,)
        )
        
        if not row:
            return None
        
        # Reconstitute aggregate
        portfolio = PortfolioAggregate(account_id)
        # ... load state from row
        return portfolio
    
    async def save(self, portfolio: PortfolioAggregate) -> None:
        # Save to database
        await self._db.execute(
            "UPDATE portfolios SET ... WHERE account_id = ?",
            (...)
        )
        
        # Publish domain events
        for event in portfolio.domain_events:
            await self._event_bus.publish(event)
        
        portfolio.clear_domain_events()
```

**Rules:**
- One repository per aggregate root
- Methods use domain language (get_by_account, not select)
- Hides persistence details from domain

---

### 6. Domain Service
**Business logic that doesn't fit in entity/aggregate**

```python
class PositionValueCalculator:
    """Service: Calculate position value at market price"""
    
    def calculate_position_value(
        self, 
        position: Position, 
        market_price: Price
    ) -> Money:
        """Calculate current position value"""
        if position.side == PositionSide.LONG:
            value = position.quantity * market_price.amount
        else:  # SHORT
            value = position.quantity * (2 * position.entry_price.amount - market_price.amount)
        
        return Money(value, market_price.currency)

# Use in aggregate
class PortfolioAggregate(AggregateRoot):
    def __init__(self, calculator: PositionValueCalculator):
        self._calculator = calculator
    
    def calculate_total_value(self, market_prices: Dict[str, Price]) -> Money:
        total = Money(Decimal(0), "USDT")
        for symbol, position in self._positions.items():
            position_value = self._calculator.calculate_position_value(
                position, market_prices[symbol]
            )
            total += position_value
        return total
```

**When to use:**
- Logic involves multiple aggregates
- Stateless operations
- Complex calculations
- NOT data transformation (that's application service)

---

## 🎯 Bounded Context

**Self-contained domain model with clear boundaries**

### Portfolio Context

```
Portfolio/
├── aggregates/
│   └── portfolio_aggregate.py    # Root
├── entities/
│   └── asset_position.py         # Part of aggregate
├── value_objects/
│   └── asset_balance.py          # Immutable
├── services/
│   └── pnl_calculator.py         # Domain logic
├── events/
│   └── balance_updated_event.py  # What happened
└── repositories/
    └── portfolio_repository.py   # Interface
```

**Rules:**
1. **Ubiquitous language** - Use business terms (Portfolio, not AccountData)
2. **Boundaries** - Don't reach into other contexts' aggregates
3. **Communication** - Via domain events or services
4. **Independence** - Can change without affecting others

### Context Mapping

```
┌─────────────┐            ┌──────────────┐
│  Portfolio  │─ Events ──▶│  Execution   │
│   Context   │            │   Context    │
└─────────────┘            └──────────────┘
      │                            │
      │ Uses                  Uses │
      ▼                            ▼
┌─────────────┐            ┌──────────────┐
│  Exchange   │            │     Risk     │
│   Context   │            │   Context    │
└─────────────┘            └──────────────┘
```

---

## 🏛️ Layered Architecture

### Domain Layer (Core)
**Pure business logic, no dependencies**

```python
# domain/portfolio/aggregates/portfolio_aggregate.py
class PortfolioAggregate(AggregateRoot):
    """Domain model - NO infrastructure dependencies"""
    
    def open_position(self, symbol: str, ...):
        # Pure business logic
        if self._violates_risk_limits(...):
            raise RiskLimitExceeded()
        
        position = Position(symbol, ...)
        self._positions[symbol] = position
        
        self._add_domain_event(PositionOpenedEvent(...))
```

### Application Layer (Orchestration)
**Coordinates domain objects and infrastructure**

```python
# application/use_cases/portfolio/sync_portfolio.py
class SyncPortfolioUseCase:
    """Orchestrates domain + infrastructure"""
    
    def __init__(self, 
                 gateway: ExchangeGateway,  # Infrastructure
                 repo: PortfolioRepository):  # Infrastructure
        self._gateway = gateway
        self._repo = repo
    
    async def execute(self, account_id: str) -> None:
        # Get data from infrastructure
        account_data = await self._gateway.get_account_info()
        
        # Load aggregate
        portfolio = await self._repo.get_by_account(account_id)
        
        # Call domain logic
        for balance in account_data.balances:
            portfolio.update_balance(balance.asset, balance.free, balance.locked)
        
        # Save via repository
        await self._repo.save(portfolio)
```

### Infrastructure Layer (Technical)
**Database, APIs, external services**

```python
# infrastructure/exchange/binance_adapter.py
class BinanceAdapter(ExchangeGateway):
    """Implements domain interface"""
    
    async def get_account_info(self) -> AccountInfoData:
        # Technical details (HTTP, JSON, etc.)
        response = await self._http.get("/fapi/v2/account")
        
        # Map to domain data structure
        return AccountInfoData(
            balances=[
                BalanceData(asset=b["asset"], free=Decimal(b["availableBalance"]), ...)
                for b in response["assets"]
            ]
        )
```

### Interfaces Layer (API/CLI)
**External communication**

```python
# interfaces/api/routes/portfolio_routes.py
@router.get("/portfolio/{account_id}")
async def get_portfolio(
    account_id: str,
    use_case: SyncPortfolioUseCase = Depends()
):
    """REST endpoint"""
    await use_case.execute(account_id)
    return {"status": "synced"}
```

---

## 🔄 CQRS Pattern

**Command Query Responsibility Segregation**

### Command (Write)
```python
# Command: Changes state
class PlaceOrderCommand:
    account_id: str
    symbol: str
    side: str
    quantity: Decimal

# Handler
class PlaceOrderHandler:
    async def handle(self, cmd: PlaceOrderCommand):
        # Load aggregate
        execution = OrderExecutionAggregate(cmd.account_id)
        
        # Execute business logic
        order = execution.place_order(
            symbol=cmd.symbol,
            side=cmd.side,
            quantity=cmd.quantity
        )
        
        # Save
        await self._repo.save(execution)
        
        return order.id
```

### Query (Read)
```python
# Query: Read-only, optimized
class GetPortfolioQuery:
    account_id: str

# Handler (reads from optimized view)
class GetPortfolioHandler:
    async def handle(self, query: GetPortfolioQuery):
        # Query read model (denormalized)
        return await self._db.fetchone(
            """
            SELECT 
                account_id,
                total_equity,
                unrealized_pnl,
                (SELECT COUNT(*) FROM positions WHERE account_id = ?) as position_count
            FROM portfolio_summary
            WHERE account_id = ?
            """,
            (query.account_id, query.account_id)
        )
```

**Benefits:**
- Optimized writes (normalized)
- Optimized reads (denormalized)
- Scale independently

---

## 🎨 Ubiquitous Language

**Use business terms consistently**

| ✅ Good (Domain) | ❌ Bad (Technical) |
|-----------------|-------------------|
| Portfolio | AccountData |
| Position | PositionDict |
| Place Order | InsertOrder |
| Calculate P&L | ComputeProfitLoss |
| Risk Limit | MaxLossValue |

**Example:**
```python
# ✅ Good: Domain language
class PortfolioAggregate:
    def calculate_unrealized_pnl(self) -> Money:
        """Calculate unrealized profit and loss"""
        pass

# ❌ Bad: Technical jargon
class AccountData:
    def compute_diff_between_current_and_entry(self) -> float:
        pass
```

---

## 🚫 Anti-Patterns to Avoid

### 1. Anemic Domain Model
```python
# ❌ Bad: No business logic in entity
class Order:
    def __init__(self):
        self.status = "NEW"

# Business logic in service
class OrderService:
    def fill_order(self, order: Order):
        order.status = "FILLED"  # Just setting data
```

**Fix:** Move logic to entity
```python
# ✅ Good: Logic in domain
class Order(Entity):
    def fill(self, quantity: Decimal, price: Decimal):
        if self._status == OrderStatus.CANCELED:
            raise CannotFillCanceledOrder()
        
        self._filled_quantity += quantity
        self._fills.append(Fill(quantity, price))
        
        if self._filled_quantity == self._quantity:
            self._status = OrderStatus.FILLED
```

### 2. Domain Logic in Application Layer
```python
# ❌ Bad: Business rule in use case
class PlaceOrderUseCase:
    async def execute(self, symbol: str, quantity: Decimal):
        portfolio = await self._repo.get(...)
        
        # Business logic here (should be in domain!)
        if portfolio.balance < quantity * price:
            raise InsufficientBalance()
```

**Fix:** Move to aggregate
```python
# ✅ Good: Rule in aggregate
class PortfolioAggregate:
    def open_position(self, quantity: Decimal, price: Decimal):
        # Business rule inside domain
        if not self._has_sufficient_balance(quantity * price):
            raise InsufficientBalance()
```

### 3. Breaking Aggregate Boundaries
```python
# ❌ Bad: Accessing entity outside aggregate
portfolio = await portfolio_repo.get(...)
position = portfolio.positions["BTCUSDT"]  # Direct access
position.quantity = Decimal("0.5")  # Bypass business rules!
```

**Fix:** Use aggregate methods
```python
# ✅ Good: Through aggregate
portfolio.update_position_quantity("BTCUSDT", Decimal("0.5"))
```

---

## 📖 Summary

**Key Concepts:**
1. **Entity** - Object with identity
2. **Value Object** - Immutable, equality by value
3. **Aggregate Root** - Consistency boundary
4. **Domain Event** - Something happened
5. **Repository** - Persistence abstraction
6. **Bounded Context** - Self-contained model

**Design Principles:**
- Domain at the center (no dependencies)
- Ubiquitous language
- Rich domain model (not anemic)
- Event-driven communication

**Benefits:**
- Maintainable (logic in one place)
- Testable (domain isolated)
- Scalable (clear boundaries)
- Understandable (business language)

---

## 🎓 Learning Resources

- **Book**: Domain-Driven Design (Eric Evans)
- **Book**: Implementing Domain-Driven Design (Vaughn Vernon)
- **Online**: [DDD Community](https://github.com/ddd-crew)
- **Examples**: This codebase!

## 🔗 Related Docs

- [Architecture](./architecture.md)
- [Migration Guide](./MIGRATION_GUIDE.md)
- [Coding Rules](./coding-rules.md)
