# Architecture Documentation - Trading Bot Platform

## 🎯 System Overview

Professional trading bot platform designed with:
- **Domain-Driven Design (DDD)** - Complex business logic encapsulation
- **Clean Architecture** - Dependency inversion & layer isolation  
- **CQRS Pattern** - Command/Query separation
- **Event-Driven** - Async communication between bounded contexts

## 📐 Architecture Layers

```
┌──────────────────────────────────────────────────────┐
│              Interfaces Layer (API/CLI)              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ REST API │  │   CLI    │  │ Workers  │           │
│  └──────────┘  └──────────┘  └──────────┘           │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│            Application Layer (Use Cases)             │
│  ┌──────────────┐  ┌───────────────┐                │
│  │   Use Cases  │  │  DTOs/Events  │                │
│  └──────────────┘  └───────────────┘                │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│           Domain Layer (Business Logic)              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐     │
│  │ Portfolio  │  │ MarketData │  │ Execution  │ ... │
│  │    BC      │  │     BC     │  │     BC     │     │
│  └────────────┘  └────────────┘  └────────────┘     │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│        Infrastructure Layer (Technical)              │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────┐    │
│  │ Repositories │  │  Exchanges  │  │ Messaging│    │
│  └──────────────┘  └─────────────┘  └──────────┘    │
└──────────────────────────────────────────────────────┘
```

### Dependency Flow
- **Interfaces** → Application → Domain ← Infrastructure
- **Rule**: Dependencies point inward (toward domain)
- **Domain** has NO dependencies on outer layers

## 🏗️ Bounded Contexts

### 1. Portfolio Context
**Responsibility**: Account management, balances, positions

**Key Aggregates:**
- `PortfolioAggregate`: Root managing all assets
  - Account state
  - Asset balances (free/locked)
  - Open positions
  - Equity calculation

**Domain Events:**
- `BalanceUpdatedEvent`
- `PositionOpenedEvent`
- `PositionClosedEvent`
- `EquityChangedEvent`

**Use Cases:**
- Sync portfolio from exchange
- Calculate total equity
- Get position details
- Track P&L

**External Dependencies:**
- Exchange API (via ExchangeGateway)
- Risk Context (position limits)

---

### 2. MarketData Context
**Responsibility**: Market information (ticks, candles, orderbook)

**Key Entities:**
- `Tick`: Real-time price update
- `Candle`: OHLCV bar
- `DepthSnapshot`: Order book snapshot

**Value Objects:**
- `Symbol`: Base/quote pair
- `Timeframe`: Candle interval
- `Price`: Decimal-based price

**Domain Events:**
- `TickReceivedEvent`
- `CandleClosedEvent`
- `DepthUpdatedEvent`

**Use Cases:**
- Subscribe to market stream
- Get historical candles
- Monitor orderbook depth

**External Dependencies:**
- Exchange WebSocket streams
- Strategy Context (consumes data)

---

### 3. Execution Context
**Responsibility**: Order lifecycle management

**Key Aggregates:**
- `OrderExecutionAggregate`: Order + fills
  - Order state machine (NEW → FILLED/CANCELED)
  - Fill tracking
  - Average price calculation

**Domain Events:**
- `OrderPlacedEvent`
- `OrderFilledEvent`
- `OrderCanceledEvent`
- `OrderRejectedEvent`

**Use Cases:**
- Place market/limit order
- Cancel order
- Track order status
- Calculate realized P&L

**External Dependencies:**
- Exchange API
- Risk Context (pre-trade checks)
- Portfolio Context (update positions)

---

### 4. Risk Context
**Responsibility**: Risk management & limits

**Key Aggregates:**
- `RiskAggregate`: Risk parameters
  - Max position size
  - Max daily loss
  - Exposure limits

**Value Objects:**
- `RiskLimit`: Type + value
- `DrawdownMetrics`: Current/max drawdown

**Domain Events:**
- `RiskLimitExceededEvent`
- `DrawdownThresholdReachedEvent`

**Use Cases:**
- Pre-trade risk check
- Monitor exposure
- Calculate drawdown
- Enforce limits

**External Dependencies:**
- Portfolio Context (equity, positions)
- Execution Context (block orders)

---

### 5. Strategy Context
**Responsibility**: Trading logic & signal generation

**Key Aggregates:**
- `StrategyAggregate`: Strategy instance
  - Parameters
  - State (active/paused)
  - Performance metrics

**Entities:**
- `Signal`: Entry/exit signal
- `StrategyConfig`: User configuration

**Domain Events:**
- `SignalGeneratedEvent`
- `StrategyStartedEvent`
- `StrategyStoppedEvent`

**Use Cases:**
- Start/stop strategy
- Process market data → signals
- Track strategy performance

**External Dependencies:**
- MarketData Context (consumes)
- Execution Context (places orders)

---

### 6. Exchange Context
**Responsibility**: Exchange abstraction & connectivity

**Key Entities:**
- `ExchangeState`: Connection status
- `ExchangeCapability`: Supported features

**Value Objects:**
- `ExchangeName`: Binance, OKX, etc.
- `APICredential`: Key/secret pair

**Use Cases:**
- Connect to exchange
- Validate credentials
- Query capabilities

**External Dependencies:**
- All contexts use ExchangeGateway interface

---

### 7. Backtest Context
**Responsibility**: Strategy simulation & optimization

**Key Aggregates:**
- `BacktestRunAggregate`: Simulation run
  - Historical data
  - Simulated trades
  - Performance metrics

**Domain Events:**
- `BacktestStartedEvent`
- `BacktestCompletedEvent`

**Use Cases:**
- Run backtest
- Optimize parameters
- Generate report

---

## 🔄 Communication Patterns

### Synchronous (Use Cases)
```
API Request → Use Case → Repository → Database
                ↓
            Domain Logic
```

### Asynchronous (Events)
```
Aggregate → Domain Event → Event Bus → Event Handler → Use Case
```

**Example Flow:**
1. `OrderExecutionAggregate` emits `OrderFilledEvent`
2. Event bus publishes to subscribers
3. Portfolio event handler receives event
4. Updates position via `UpdatePositionUseCase`

## 🧩 Component Interactions

### Example: Place Order Flow

```
┌─────────┐     ┌──────────────┐     ┌─────────────┐
│REST API │────▶│PlaceOrderUse │────▶│RiskAggregate│
│         │     │    Case      │     │             │
└─────────┘     └──────┬───────┘     └─────────────┘
                       │
                       ▼
              ┌────────────────┐
              │OrderExecution  │
              │  Aggregate     │
              └────────┬───────┘
                       │ emits OrderPlacedEvent
                       ▼
              ┌────────────────┐
              │BinanceAdapter  │───────▶ Binance API
              └────────────────┘
```

**Steps:**
1. REST API receives request
2. Use case validates via Risk aggregate
3. Creates Order aggregate
4. Aggregate emits domain event
5. Adapter sends to exchange
6. Event handler updates Portfolio

## 🗃️ Data Flow

### Write Path (Command)
```
API → DTO → Use Case → Aggregate → Repository → Database
                                ↓
                          Domain Events
```

### Read Path (Query)
```
API → Query Service → Read Model (DB/Cache) → DTO
```

**CQRS Benefits:**
- Optimized reads (denormalized views)
- Separate scaling
- Event sourcing ready

## 🔌 Infrastructure Details

### Exchange Integration
```python
# Domain interface (in domain layer)
class ExchangeGateway(ABC):
    @abstractmethod
    async def get_account_info(self) -> AccountInfoData:
        pass

# Implementation (in infrastructure)
class BinanceAdapter(ExchangeGateway):
    async def get_account_info(self) -> AccountInfoData:
        # Binance-specific implementation
        response = await self._http.get("/fapi/v2/account")
        return self._convert_to_domain_data(response)
```

### Repository Pattern
```python
# Domain interface
class PortfolioRepository(ABC):
    @abstractmethod
    async def get_by_account(self, account_id: str) -> PortfolioAggregate:
        pass

# Infrastructure implementation
class SqlPortfolioRepository(PortfolioRepository):
    async def get_by_account(self, account_id: str) -> PortfolioAggregate:
        row = await self._db.fetchone(
            "SELECT * FROM portfolios WHERE account_id = ?", 
            (account_id,)
        )
        return self._map_to_aggregate(row)
```

### Event Bus
```python
# Publish domain events
class PortfolioAggregate(AggregateRoot):
    def update_balance(self, asset: str, free: Decimal, locked: Decimal):
        # Business logic
        self._balances[asset] = AssetBalance(asset, free, locked)
        
        # Emit event
        self._add_domain_event(
            BalanceUpdatedEvent(self._account_id, asset, free, locked)
        )

# Subscribe to events
class UpdatePortfolioOnOrderFilled:
    async def handle(self, event: OrderFilledEvent):
        # Update portfolio when order is filled
        portfolio = await self._repo.get_by_account(event.account_id)
        portfolio.apply_fill(event.symbol, event.quantity, event.price)
        await self._repo.save(portfolio)
```

## ⚡ Performance Optimizations

### 1. Connection Pooling
- HTTP: Reuse connections (via `HTTPPoolManager`)
- WebSocket: Single connection per stream
- Database: Connection pool (20-50 connections)

### 2. Caching Strategy
- **L1 (In-Memory)**: Recent aggregates (TTL: 5s)
- **L2 (Redis)**: Market data, orderbook (TTL: 1s)
- **CDN**: Historical candles (TTL: 1h)

### 3. Async Processing
- Non-blocking I/O everywhere
- Event handlers run async
- WebSocket streams (aiohttp)

### 4. Data Structures
- `RingBuffer`: Fixed-size price history
- `FastOrderBook`: Sorted dict for depth
- `LockFreeQueue`: Thread-safe queues

### 5. JSON Optimization
- `orjson`: 3x faster than stdlib
- `simdjson`: 4x faster (read-only)

## 🏛️ Design Principles

### Single Responsibility
- Each aggregate manages ONE concept
- Each use case does ONE operation
- Each repository handles ONE aggregate

### Dependency Inversion
- Domain defines interfaces
- Infrastructure implements them
- Use cases depend on abstractions

### Tell, Don't Ask
```python
# ❌ Bad (asking)
if portfolio.get_balance("USDT") > required_margin:
    portfolio.set_position(...)

# ✅ Good (telling)
portfolio.open_position(symbol, quantity, price, leverage)
# Aggregate checks balance internally
```

### Ubiquitous Language
- Use business terms: Portfolio, Position, Signal
- NOT technical: Dict, List, Data
- Consistent naming across layers

## 🧪 Testing Strategy

### Unit Tests (Domain)
```python
def test_portfolio_opens_position():
    portfolio = PortfolioAggregate("test_account")
    portfolio.update_balance("USDT", Decimal(1000), Decimal(0))
    
    portfolio.open_position("BTCUSDT", Decimal(0.1), Decimal(50000), 10)
    
    assert "BTCUSDT" in portfolio.positions
    assert len(portfolio.domain_events) == 2  # Balance + Position events
```

### Integration Tests (Use Cases)
```python
async def test_sync_portfolio_use_case():
    # Mock gateway
    gateway = MockExchangeGateway()
    gateway.set_account_data(...)
    
    # Execute
    use_case = SyncPortfolioUseCase(gateway, repository)
    await use_case.execute("test_account")
    
    # Verify
    portfolio = await repository.get_by_account("test_account")
    assert portfolio.balances["USDT"].free == Decimal(1000)
```

### E2E Tests (Full Flow)
```python
async def test_place_order_flow():
    # Real API request
    response = await client.post("/api/orders", json={
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.001",
        "type": "MARKET"
    })
    
    assert response.status_code == 200
    
    # Verify in database
    order = await db.fetchone("SELECT * FROM orders WHERE id = ?", ...)
    assert order["status"] == "FILLED"
```

## 📦 Deployment

### Local Development
```bash
docker-compose up  # App + Redis
```

### Production (Kubernetes)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trading-bot
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: app
        image: trading-bot:latest
        env:
        - name: BINANCE_API_KEY
          valueFrom:
            secretKeyRef:
              name: binance-secret
              key: api-key
```

## 🔒 Security

- API keys in environment variables
- Request signing (HMAC-SHA256)
- Rate limiting (exchange + application)
- Input validation (Pydantic)

## 📊 Monitoring

- **Metrics**: Prometheus (order latency, fill rate)
- **Logs**: Structured JSON (ELK stack)
- **Tracing**: OpenTelemetry (distributed tracing)
- **Alerts**: PagerDuty (risk limits exceeded)

## 🚀 Scalability

- **Horizontal**: Multiple workers (order processing)
- **Vertical**: High-performance modules (orjson, uvloop)
- **Sharding**: By account_id (database)
- **Caching**: Redis cluster

## 📚 Further Reading

- [Migration Guide](./MIGRATION_GUIDE.md)
- [DDD Overview](./ddd-overview.md)
- [Performance Module](./PERFORMANCE_MODULE.md)
- [Coding Rules](./coding-rules.md)
