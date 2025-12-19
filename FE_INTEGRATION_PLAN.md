# Frontend Integration Plan

**Project**: Trading Bot Platform  
**Created**: December 17, 2025  
**Last Updated**: December 17, 2025

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Frontend Pages Analysis](#frontend-pages-analysis)
3. [Required Backend APIs](#required-backend-apis)
4. [Integration Phases](#integration-phases)
5. [API Client Setup](#api-client-setup)
6. [Data Flow Architecture](#data-flow-architecture)
7. [State Management Strategy](#state-management-strategy)
8. [WebSocket Integration](#websocket-integration)
9. [Error Handling & Loading States](#error-handling--loading-states)
10. [Testing Strategy](#testing-strategy)

---

## 📊 Overview

### Current State
- **Frontend**: React + TypeScript + Vite with shadcn/ui components
- **Backend**: FastAPI with RESTful API + WebSocket support
- **State Management**: Zustand store (currently mock data)
- **Pages**: 12 pages (Dashboard, Bots, Backtest, etc.)

### Integration Goal
Replace all mock data in frontend with real API calls to backend, implement authentication flow, and establish real-time updates via WebSocket.

---

## 🎨 Frontend Pages Analysis

### Page Inventory

| # | Page | Path | Backend APIs Needed | Priority |
|---|------|------|---------------------|----------|
| 1 | **Index (Dashboard)** | `/` | Account info, Portfolio summary, Bot list, Market data | 🔴 Critical |
| 2 | **Bots** | `/bots` | Bot CRUD, Bot control (start/stop) | 🔴 Critical |
| 3 | **BotDetail** | `/bots/:id` | Bot details, Bot performance, Orders, Config update | 🔴 Critical |
| 4 | **Backtest** | `/backtest` | Backtest CRUD, Backtest execution | 🟡 High |
| 5 | **BacktestDetail** | `/backtest/:id` | Backtest results, Equity curve, Metrics | 🟡 High |
| 6 | **Strategies** | `/strategies` | Strategy CRUD, Strategy execution | 🟡 High |
| 7 | **Connections** | `/connections` | Exchange connection CRUD, Connection testing | 🔴 Critical |
| 8 | **Performance** | `/performance` | Performance metrics, Returns, Risk metrics | 🟢 Medium |
| 9 | **Risk** | `/risk` | Risk limits, Exposure, Alerts | 🟢 Medium |
| 10 | **Alerts** | `/alerts` | Alert list, Alert settings | 🟢 Medium |
| 11 | **Settings** | `/settings` | User profile, Preferences, API keys | 🟢 Medium |
| 12 | **NotFound** | `/404` | N/A | ⚪ Low |

---

## 🔌 Required Backend APIs

### Phase 1: Authentication & Core Setup (CRITICAL)

#### 1.1 Authentication APIs
```typescript
// Required for: Login, Registration, Token refresh
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
GET    /api/v1/users/me
PATCH  /api/v1/users/me
```

**Frontend Components:**
- Login page (NEW - needs to be created)
- Registration page (NEW)
- Protected route wrapper
- Auth context/hook

**Status**: ⚠️ **MISSING** - No auth pages in frontend yet

---

#### 1.2 Exchange Connection APIs
```typescript
// Required for: Connections page
GET    /api/v1/exchanges/connections
POST   /api/v1/exchanges/connections
PUT    /api/v1/exchanges/connections/{id}
DELETE /api/v1/exchanges/connections/{id}
POST   /api/v1/exchanges/connections/test
GET    /api/v1/exchanges/connections/{id}/account
```

**Frontend Usage:**
- `Connections.tsx` - Full CRUD for exchange connections
- `WelcomeSetup.tsx` - Initial connection setup

**Status**: ✅ **READY** - Backend APIs exist

---

### Phase 2: Bot Management (CRITICAL)

#### 2.1 Bot APIs
```typescript
// Required for: Bots page, BotDetail page, Dashboard
POST   /api/v1/bots
GET    /api/v1/bots                    // List with filters
GET    /api/v1/bots/{bot_id}
PATCH  /api/v1/bots/{bot_id}
DELETE /api/v1/bots/{bot_id}
POST   /api/v1/bots/{bot_id}/start
POST   /api/v1/bots/{bot_id}/stop
POST   /api/v1/bots/{bot_id}/pause     // ⚠️ Check if exists
```

**Frontend Usage:**
- `Bots.tsx` - Bot list, create, delete
- `BotDetail.tsx` - Bot details, start/stop, config
- `Index.tsx` - Active bots summary

**Status**: ✅ **READY** - Backend APIs exist

---

#### 2.2 Bot Configuration APIs
```typescript
// Required for: Bot config in BotDetail
GET    /api/v1/bots/{bot_id}/config
PATCH  /api/v1/bots/{bot_id}/config
```

**Status**: ⚠️ **PARTIAL** - Config via PATCH /bots/{id}, no dedicated endpoint

---

### Phase 3: Strategy Management (HIGH)

#### 3.1 Strategy APIs
```typescript
// Required for: Strategies page
POST   /api/v1/strategies
GET    /api/v1/strategies
GET    /api/v1/strategies/{strategy_id}
PATCH  /api/v1/strategies/{strategy_id}
DELETE /api/v1/strategies/{strategy_id}
POST   /api/v1/strategies/{strategy_id}/validate
```

**Frontend Usage:**
- `Strategies.tsx` - Strategy CRUD, code editor

**Status**: ⚠️ **CHECK NEEDED** - Not documented in API_REFERENCE.md

---

### Phase 4: Order Management (CRITICAL)

#### 4.1 Order APIs
```typescript
// Required for: BotDetail page orders section
POST   /api/v1/orders
GET    /api/v1/orders                  // List with filters
GET    /api/v1/orders/active
GET    /api/v1/orders/stats
GET    /api/v1/orders/{order_id}
DELETE /api/v1/orders/{order_id}       // Cancel order
```

**Frontend Usage:**
- `BotDetail.tsx` - Order history, active orders

**Status**: ✅ **READY** - Backend APIs exist

---

### Phase 5: Backtesting (HIGH)

#### 5.1 Backtest APIs
```typescript
// Required for: Backtest page, BacktestDetail page
POST   /api/v1/backtests
GET    /api/v1/backtests                // List with filters
GET    /api/v1/backtests/{backtest_id}
DELETE /api/v1/backtests/{backtest_id}
POST   /api/v1/backtests/{backtest_id}/cancel  // ⚠️ Check if exists
```

**Frontend Usage:**
- `Backtest.tsx` - Create backtest, list history
- `BacktestDetail.tsx` - Results, equity curve, metrics

**Status**: ✅ **READY** - Backend APIs exist (Phase 5)

---

### Phase 6: Market Data (CRITICAL)

#### 6.1 Market Data APIs
```typescript
// Required for: Dashboard, BotDetail charts
GET    /api/v1/market/ticker/{symbol}
GET    /api/v1/market/klines/{symbol}
GET    /api/v1/market/orderbook/{symbol}  // ⚠️ Check if exists
```

**Frontend Usage:**
- `Index.tsx` - Market overview
- `BotDetail.tsx` - Price charts

**Status**: ✅ **READY** - Backend APIs exist

---

### Phase 7: Performance Analytics (MEDIUM)

#### 7.1 Performance APIs
```typescript
// Required for: Performance page
GET    /api/v1/performance/overview
GET    /api/v1/performance/returns/daily
GET    /api/v1/performance/returns/monthly
GET    /api/v1/performance/metrics/by-bot
GET    /api/v1/performance/metrics/by-strategy
GET    /api/v1/performance/risk-metrics
```

**Frontend Usage:**
- `Performance.tsx` - Analytics dashboard

**Status**: ⚠️ **CHECK NEEDED** - Not in v1 routes, may be in presentation layer

---

### Phase 8: Risk Management (MEDIUM)

#### 8.1 Risk APIs
```typescript
// Required for: Risk page
GET    /api/v1/risk/overview
GET    /api/v1/risk/exposure
GET    /api/v1/risk/limits
POST   /api/v1/risk/limits
PATCH  /api/v1/risk/limits/{limit_id}
DELETE /api/v1/risk/limits/{limit_id}
GET    /api/v1/risk/alerts
```

**Frontend Usage:**
- `Risk.tsx` - Risk monitoring, limits management

**Status**: ✅ **READY** - Backend APIs exist (Phase 4)

---

### Phase 9: WebSocket Real-time Updates

#### 9.1 WebSocket Endpoints
```typescript
// Required for: Real-time updates
WS     /api/v1/ws/market/{symbol}       // Market data stream
WS     /api/v1/ws/orders                // Order updates
WS     /api/v1/ws/bots/{bot_id}         // Bot status updates ⚠️
WS     /api/v1/ws/portfolio             // Portfolio updates ⚠️
```

**Frontend Usage:**
- All pages - Real-time data updates
- Dashboard - Live portfolio value
- BotDetail - Live bot metrics

**Status**: ⚠️ **PARTIAL** - Market & orders WS exist, need bot/portfolio WS

---

## 🔄 Integration Phases

### Phase 1: Foundation (Week 1) 🔴 CRITICAL

**Goal**: Setup authentication and basic infrastructure

**Tasks**:
1. Create authentication pages (Login, Register)
2. Setup API client with axios/fetch
3. Implement auth token management
4. Create protected route wrapper
5. Setup error handling & toast notifications
6. Test connection with backend health endpoint

**APIs to Integrate**:
- `/api/v1/auth/*`
- `/api/v1/users/me`

**Deliverables**:
- ✅ Login/Register pages
- ✅ Auth context/hook
- ✅ API client with interceptors
- ✅ Token storage (localStorage/cookies)

---

### Phase 2: Exchange Connections (Week 1) 🔴 CRITICAL

**Goal**: Users can connect exchange accounts

**Tasks**:
1. Integrate Connections page with APIs
2. Add connection testing functionality
3. Update WelcomeSetup flow
4. Add connection status indicators

**APIs to Integrate**:
- `/api/v1/exchanges/connections/*`

**Deliverables**:
- ✅ Working Connections CRUD
- ✅ Connection test validation
- ✅ Initial setup wizard

---

### Phase 3: Bot Management (Week 2) 🔴 CRITICAL

**Goal**: Users can create and manage bots

**Tasks**:
1. Integrate Bots page with APIs
2. Integrate BotDetail page with APIs
3. Add bot control (start/stop/pause)
4. Update Dashboard with real bot data
5. Add bot performance charts

**APIs to Integrate**:
- `/api/v1/bots/*`
- `/api/v1/orders/*`

**Deliverables**:
- ✅ Bot CRUD operations
- ✅ Bot control panel
- ✅ Bot detail view with orders
- ✅ Live bot metrics

---

### Phase 4: Market Data & Charts (Week 2)

**Goal**: Display real market data

**Tasks**:
1. Integrate market data APIs
2. Add price charts (using recharts/lightweight-charts)
3. Update MarketOverview component
4. Add ticker price updates

**APIs to Integrate**:
- `/api/v1/market/*`

**Deliverables**:
- ✅ Live price data
- ✅ Candlestick charts
- ✅ Market overview dashboard

---

### Phase 5: Backtesting (Week 3) 🟡 HIGH

**Goal**: Users can run and analyze backtests

**Tasks**:
1. Integrate Backtest page with APIs
2. Integrate BacktestDetail page with APIs
3. Add backtest execution progress
4. Add equity curve visualization
5. Add metrics comparison

**APIs to Integrate**:
- `/api/v1/backtests/*`

**Deliverables**:
- ✅ Backtest creation and execution
- ✅ Results visualization
- ✅ Historical backtest list

---

### Phase 6: WebSocket Real-time Updates (Week 3)

**Goal**: Real-time data updates without polling

**Tasks**:
1. Setup WebSocket client
2. Integrate market data stream
3. Integrate order updates stream
4. Add reconnection logic
5. Update UI with real-time data

**APIs to Integrate**:
- `WS /api/v1/ws/*`

**Deliverables**:
- ✅ WebSocket connection manager
- ✅ Real-time market prices
- ✅ Live order updates
- ✅ Auto-reconnect on disconnect

---

### Phase 7: Performance & Risk (Week 4) 🟢 MEDIUM

**Goal**: Analytics and risk management

**Tasks**:
1. Integrate Performance page
2. Integrate Risk page
3. Add performance charts
4. Add risk metrics and alerts

**APIs to Integrate**:
- `/api/v1/performance/*`
- `/api/v1/risk/*`

**Deliverables**:
- ✅ Performance analytics dashboard
- ✅ Risk monitoring
- ✅ Alert management

---

### Phase 8: Strategy Management (Week 4)

**Goal**: Users can create and edit strategies

**Tasks**:
1. Integrate Strategies page
2. Add code editor (Monaco/CodeMirror)
3. Add strategy validation
4. Add strategy testing

**APIs to Integrate**:
- `/api/v1/strategies/*`

**Deliverables**:
- ✅ Strategy CRUD
- ✅ Code editor with Python syntax
- ✅ Strategy validation

---

### Phase 9: Settings & Preferences (Week 5)

**Goal**: User profile and settings

**Tasks**:
1. Integrate Settings page
2. Add profile update
3. Add theme settings
4. Add notification preferences

**APIs to Integrate**:
- `/api/v1/users/me`

**Deliverables**:
- ✅ User profile management
- ✅ Settings persistence

---

## 🛠️ API Client Setup

### Recommended Structure

```typescript
// src/lib/api/client.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - Add auth token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - Handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Handle token refresh or redirect to login
    }
    return Promise.reject(error);
  }
);
```

### API Service Structure

```
src/lib/api/
├── client.ts           # Axios client with interceptors
├── auth.ts             # Auth API calls
├── bots.ts             # Bot API calls
├── orders.ts           # Order API calls
├── backtests.ts        # Backtest API calls
├── market.ts           # Market data API calls
├── performance.ts      # Performance API calls
├── risk.ts             # Risk API calls
├── strategies.ts       # Strategy API calls
├── connections.ts      # Exchange connection API calls
└── websocket.ts        # WebSocket client
```

---

## 🔀 Data Flow Architecture

### Request Flow
```
Frontend Component
    ↓
API Service (src/lib/api/*.ts)
    ↓
Axios Client (with interceptors)
    ↓
Backend API
    ↓
Response
    ↓
Zustand Store (state update)
    ↓
UI Update
```

### WebSocket Flow
```
Frontend Component (useEffect)
    ↓
WebSocket Client
    ↓
Backend WebSocket
    ↓
Real-time Message
    ↓
Zustand Store (state update)
    ↓
UI Update (no re-render needed)
```

---

## 📦 State Management Strategy

### Zustand Store Structure

```typescript
// src/lib/store.ts
interface AppStore {
  // Auth state
  user: User | null;
  isAuthenticated: boolean;
  login: (credentials) => Promise<void>;
  logout: () => void;
  
  // Bot state
  bots: Bot[];
  fetchBots: () => Promise<void>;
  createBot: (data) => Promise<void>;
  updateBot: (id, data) => Promise<void>;
  deleteBot: (id) => Promise<void>;
  
  // Orders state
  orders: Order[];
  fetchOrders: (filters) => Promise<void>;
  
  // Market data
  tickers: Record<string, Ticker>;
  updateTicker: (symbol, data) => void;
  
  // WebSocket
  wsConnected: boolean;
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
}
```

**Strategy**:
- Keep API calls in store actions
- Use optimistic updates where appropriate
- Handle loading/error states in store
- Use selectors for derived state

---

## 🌐 WebSocket Integration

### Connection Manager

```typescript
// src/lib/api/websocket.ts
class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  
  connect(token: string) {
    const wsUrl = `ws://localhost:8000/api/v1/ws?token=${token}`;
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
    
    this.ws.onerror = () => {
      this.reconnect();
    };
  }
  
  subscribe(channel: string, callback: Function) {
    // Subscribe to specific channels
  }
  
  private reconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => this.connect(), 5000);
      this.reconnectAttempts++;
    }
  }
}
```

---

## ⚠️ Error Handling & Loading States

### Loading States

```typescript
interface LoadingState {
  isLoading: boolean;
  error: string | null;
}

// In components
const [state, setState] = useState<LoadingState>({
  isLoading: false,
  error: null,
});

// Usage
setState({ isLoading: true, error: null });
try {
  await apiCall();
} catch (error) {
  setState({ isLoading: false, error: error.message });
}
```

### Error Handling Strategy

1. **Network Errors**: Show toast notification
2. **Validation Errors**: Display inline form errors
3. **Auth Errors**: Redirect to login
4. **Server Errors**: Show error page with retry option
5. **Rate Limiting**: Show cooldown message

---

## 🧪 Testing Strategy

### Testing Layers

1. **Unit Tests**: API service functions
2. **Integration Tests**: API client with MSW (Mock Service Worker)
3. **E2E Tests**: Full user flows with Playwright/Cypress
4. **WebSocket Tests**: Mock WebSocket connections

### Example Test

```typescript
// src/lib/api/bots.test.ts
import { describe, it, expect, vi } from 'vitest';
import { fetchBots } from './bots';
import { apiClient } from './client';

vi.mock('./client');

describe('Bot API', () => {
  it('fetches bots successfully', async () => {
    apiClient.get.mockResolvedValue({
      data: { items: [], total: 0 }
    });
    
    const result = await fetchBots();
    expect(result.items).toEqual([]);
  });
});
```

---

## 📝 Implementation Checklist

### Pre-Integration
- [ ] Review all backend API endpoints
- [ ] Identify missing APIs
- [ ] Setup environment variables
- [ ] Install required packages (axios, react-query, etc.)

### Phase 1: Auth
- [ ] Create Login page
- [ ] Create Register page
- [ ] Setup API client
- [ ] Implement token management
- [ ] Add protected routes
- [ ] Test auth flow

### Phase 2: Connections
- [ ] Integrate Connections CRUD
- [ ] Add connection testing
- [ ] Update WelcomeSetup

### Phase 3: Bots
- [ ] Integrate Bot CRUD
- [ ] Add bot controls
- [ ] Update Dashboard with real data
- [ ] Add bot performance metrics

### Phase 4: Orders
- [ ] Integrate order APIs
- [ ] Add order history in BotDetail
- [ ] Add active orders view

### Phase 5: Backtesting
- [ ] Integrate backtest creation
- [ ] Add progress tracking
- [ ] Visualize results
- [ ] Add equity curve charts

### Phase 6: WebSocket
- [ ] Setup WebSocket client
- [ ] Connect to market stream
- [ ] Connect to order stream
- [ ] Add reconnection logic

### Phase 7: Performance & Risk
- [ ] Integrate performance APIs
- [ ] Integrate risk APIs
- [ ] Add analytics charts

### Phase 8: Strategies
- [ ] Integrate strategy CRUD
- [ ] Add code editor
- [ ] Add validation

### Phase 9: Settings
- [ ] Integrate user profile
- [ ] Add settings management

---

## 🚀 Quick Start Commands

```bash
# Install dependencies
cd frontend
npm install axios react-query zustand

# Setup environment
cp .env.example .env
# Edit VITE_API_URL=http://localhost:8000

# Start frontend
npm run dev

# Start backend (in another terminal)
cd ../backend
./run.sh
```

---

**Next Steps**: See [FE_INTEGRATION_STATUS.md](FE_INTEGRATION_STATUS.md) for current implementation status.
