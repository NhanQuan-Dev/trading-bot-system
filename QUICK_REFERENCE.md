# Quick Reference - Trading Bot Platform

## 🚀 Quick Start

```bash
# Install dependencies
poetry install  # or: pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Add your API keys

# Run tests
pytest tests/unit/

# Format code
./scripts/format.sh

# Lint code
./scripts/lint.sh
```

## 📁 Project Structure

```
src/trading/
├── shared/              # Shared kernel & utilities
│   ├── kernel/          # DDD base classes
│   ├── types/           # Value objects (Money, Symbol, Timeframe)
│   └── errors/          # Exception hierarchy
├── performance/         # Performance optimizations
├── domain/             # Business logic (7 bounded contexts)
│   └── portfolio/      # ✅ COMPLETE
│       ├── aggregates/  # PortfolioAggregate
│       ├── entities/    # AssetPosition
│       ├── value_objects/  # AssetBalance
│       ├── events/      # Domain events
│       └── repositories/  # Repository interface
├── application/        # Use cases & DTOs
│   ├── use_cases/
│   │   └── portfolio/  # ✅ SyncPortfolioUseCase
│   └── dto/           # ✅ PortfolioSnapshotDTO
└── infrastructure/    # Technical implementations
    ├── exchange/      # ✅ BinanceAdapter
    └── persistence/   # ✅ InMemoryPortfolioRepository
```

## 🧪 Testing

All 34 unit tests pass! ✅

```bash
# Run all tests
pytest tests/unit/domain/portfolio/ -v

# Run specific test
pytest tests/unit/domain/portfolio/test_asset_balance.py -v

# With coverage
pytest tests/unit/ --cov=src.trading
```

## 🔑 Key Concepts

### DDD Layers
```
Interfaces → Application → Domain ← Infrastructure
```

### Example Usage

```python
# Domain (Business Logic)
from src.trading.domain.portfolio.aggregates.portfolio_aggregate import PortfolioAggregate
from src.trading.shared.types.symbol import Symbol

portfolio = PortfolioAggregate("account_123")
portfolio.update_balance("USDT", Decimal("1000"), Decimal("0"))

symbol = Symbol("BTC", "USDT")
position_id = portfolio.open_position(
    symbol=symbol,
    quantity=Decimal("0.1"),
    side="LONG",
    entry_price=Decimal("50000"),
    leverage=10
)
```

## 📚 Documentation

| File | Purpose |
|------|---------|
| `docs/architecture.md` | System design |
| `docs/ddd-overview.md` | DDD patterns explained |
| `docs/coding-rules.md` | Code standards |
| `docs/MIGRATION_GUIDE.md` | Migration examples |
| `NEXT_STEPS.md` | Development roadmap |
| `PROJECT_STATUS.md` | Detailed progress |

---

**Status:** Portfolio BC complete with 34 passing tests ✅
