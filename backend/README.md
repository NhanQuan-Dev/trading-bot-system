# Trading Bot Platform - Backend

Python-based backend API và trading engine sử dụng Domain-Driven Design (DDD) và Clean Architecture.

## 🚀 Quick Start

```bash
# Install dependencies
poetry install  # or: pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Add your Binance API keys

# Run development server
./scripts/run_dev.sh

# Run tests
pytest tests/unit/ -v
```

## 📁 Structure

```
backend/
├── src/trading/              # Main application
│   ├── shared/              # Shared kernel (DDD base classes, types)
│   ├── domain/              # Business logic (7 bounded contexts)
│   │   └── portfolio/       # ✅ Portfolio BC (Complete)
│   ├── application/         # Use cases & DTOs
│   ├── infrastructure/      # External integrations (Binance, DB)
│   └── presentation/        # API controllers (FastAPI)
├── tests/                   # All tests
├── config/                  # Configuration files
├── docs/                    # Architecture documentation
└── scripts/                 # Dev/deployment scripts
```

## 📚 Documentation

- `docs/architecture.md` - System design overview
- `docs/ddd-overview.md` - DDD patterns explained
- `docs/coding-rules.md` - Code standards
- `../PROJECT_STATUS.md` - Current progress (85%)
- `../NEXT_STEPS.md` - Development roadmap

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# With coverage
pytest tests/unit/ --cov=src.trading
```

## 🔧 Tech Stack

- **Framework**: FastAPI
- **Architecture**: DDD + Clean Architecture
- **Exchange**: Binance Futures API
- **Testing**: pytest
- **Python**: 3.12+
