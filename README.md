# Trading Bot Platform

Full-stack cryptocurrency trading bot platform với Clean Architecture + DDD.

## 📁 Monorepo Structure

```
trading-bot-platform/
├── backend/                 # Python Backend (FastAPI + DDD)
│   ├── src/trading/        # Main application code
│   ├── tests/              # Backend tests  
│   ├── docs/               # Architecture docs
│   └── config/             # Configuration
│
├── frontend/                # React Frontend (Feature-Based)
│   ├── src/
│   │   ├── features/       # Feature modules (portfolio, trading, etc)
│   │   ├── shared/         # Shared code
│   │   └── app/            # App setup
│   └── tests/              # Frontend tests
│
├── docker-compose.yml       # Orchestrate services
└── docs/                    # Shared documentation  
```

## 🚀 Quick Start

### Backend (Currently Running)

```bash
cd backend/src
# Server is running on http://localhost:8001
# API Docs: http://localhost:8001/api/docs

# Test health
curl http://localhost:8001/health

# Test API endpoints
curl http://localhost:8001/api/v1/orders/
```

### Development Setup

```bash
cd backend
poetry install
cp .env.example .env
# Edit .env with your Binance API keys

# Run server
cd src
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## 🏗️ Architecture

### Backend: Clean Architecture + DDD
- **Domain Layer**: Business logic với 7 bounded contexts
  - ✅ **Order Context (90%)** - Complete order management with exchange integration
  - ✅ **Exchange Context (80%)** - Binance API integration with encryption
  - ✅ **Portfolio Context (30%)** - Basic portfolio management
  - ⏳ **Bot Context (0%)** - Trading bot management (next priority)
  - ⏳ MarketData, Risk, Strategy contexts
- **Application Layer**: Use cases & business orchestration
- **Infrastructure Layer**: PostgreSQL, Binance API, WebSocket
- **Interface Layer**: REST API (FastAPI) với OpenAPI docs

### Frontend: Feature-Based Architecture (Planned)
- **Features**: portfolio, trading, market-data, risk, auth
- **Shared**: Reusable components, hooks, utils
- **Infrastructure**: API clients, WebSocket, storage

## 📊 Current Status - December 16, 2025

| Component | Status | Progress | Features |
|-----------|--------|----------|----------|
| **Order Management** | ✅ Complete | 100% | CRUD, Exchange integration, 6 REST endpoints |
| **Exchange Integration** | ✅ Complete | 100% | Binance API, Encryption, 5 REST endpoints |  
| **User Authentication** | ✅ Complete | 100% | JWT, Registration, Login |
| **Database Layer** | ✅ Complete | 100% | PostgreSQL, 18+ tables, Migrations |
| **Bot Management** | ⏳ Next | 0% | Strategy execution, Lifecycle |
| **Market Data** | ⏳ Planned | 0% | Real-time streaming, Historical data |
| **Frontend** | 📁 Skeleton | 0% | Structure only |

**Overall**: ~75% Complete (Backend), 0% Frontend

## 🎯 Key Features Implemented

### ✅ Order Management
- Create orders (Market, Limit, Stop) with exchange submission
- Cancel orders on exchange
- Advanced filtering and pagination
- Real-time status tracking
- Commission and execution tracking

### ✅ Exchange Integration  
- Binance Futures API integration
- API key encryption with Fernet
- Testnet/Mainnet support
- Connection testing and validation

### ✅ Authentication System
- JWT access/refresh tokens
- User registration and login
- Protected endpoints with role-based access

### ✅ Database Infrastructure
- PostgreSQL with async SQLAlchemy 2.0
- 18+ tables with proper relationships
- Alembic migrations
- Connection pooling

## 🔗 Live Endpoints

**Server:** http://localhost:8001
**API Docs:** http://localhost:8001/api/docs

### Order Endpoints
- `POST /api/v1/orders/` - Create new order
- `GET /api/v1/orders/` - List orders with filters
- `GET /api/v1/orders/{id}` - Get order by ID  
- `DELETE /api/v1/orders/{id}` - Cancel order
- `GET /api/v1/orders/active` - List active orders
- `GET /api/v1/orders/stats` - Order statistics

### Exchange Endpoints
- `POST /api/v1/exchanges/connections` - Add exchange connection
- `GET /api/v1/exchanges/connections` - List connections
- `POST /api/v1/exchanges/connections/test` - Test connection
- `DELETE /api/v1/exchanges/connections/{id}` - Remove connection

### Authentication Endpoints  
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh token

## 📚 Documentation

- [PROJECT_STATUS.md](./PROJECT_STATUS.md) - Detailed progress tracking
- [NEXT_STEPS.md](./NEXT_STEPS.md) - Development roadmap  
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Quick reference guide
- [docs/architecture.md](./docs/architecture.md) - System architecture
- [docs/ddd-overview.md](./docs/ddd-overview.md) - DDD implementation
- **Live API Docs:** http://localhost:8001/api/docs

## 🛠️ Technology Stack

### Backend
- **Framework:** FastAPI (Python 3.12+)
- **Database:** PostgreSQL 15 with SQLAlchemy 2.0  
- **Authentication:** JWT with bcrypt
- **API Integration:** Binance Futures API
- **Architecture:** Clean Architecture + DDD
- **Security:** Fernet encryption, API key protection

### Infrastructure
- **Package Management:** Poetry
- **Database Migrations:** Alembic
- **Configuration:** Pydantic Settings
- **Development:** Hot reload, auto-formatting
- **Documentation:** Auto-generated OpenAPI specs

## 🎯 Next Steps

1. **Phase 2.2:** Bot Management - Strategy execution and lifecycle
2. **Phase 3:** Market Data - Real-time WebSocket streaming  
3. **Testing:** Unit and integration test coverage
4. **Frontend:** React application with real-time updates
5. **DevOps:** Docker deployment and CI/CD

---

**Last Updated:** December 16, 2025  
**Server Status:** 🟢 Running on http://localhost:8001

## 🔧 Tech Stack

### Backend
- Python 3.12+
- FastAPI (REST API)
- pytest (Testing)
- Binance Futures API
- PostgreSQL (planned)

### Frontend (Planned)
- React 18 + TypeScript
- Vite (Build tool)
- Zustand (State management)
- TanStack Query (Data fetching)
- TailwindCSS (Styling)

## 📝 Next Steps

1. **Backend REST API**: Create FastAPI endpoints cho Portfolio BC
2. **Frontend Implementation**: Implement portfolio dashboard
3. **MarketData BC**: Implement market data streaming
4. **Integration**: Connect FE ↔ BE via REST + WebSocket

---

**Last Updated**: 2025-12-10
