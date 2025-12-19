# Next Phase Implementation Plan

**Project**: Trading Bot Platform  
**Current Status**: Phase 1 Authentication ✅ Complete  
**Next Phase**: Phase 2 - Core Bot Management  
**Updated**: December 18, 2025

---

## ✅ Phase 1 Complete - Authentication

### What Was Done
- ✅ Login page with email field (backend uses email, not username)
- ✅ Register page without username field
- ✅ Auth API client with axios interceptors
- ✅ Token refresh queue for concurrent 401s
- ✅ Protected routes with loading state
- ✅ Public routes guard (redirect authenticated users)
- ✅ Logout button in Sidebar
- ✅ CORS fixed for port 8081
- ✅ Complete flow tested with Playwright

### Key Learnings
1. **Backend schema mismatch**: Backend uses `email` for login, not `username`
2. **CORS config**: Need to update `.env` file, not just `settings.py`
3. **User model**: Backend doesn't have `username` field, only `email` and `full_name`
4. **Auth initialization**: Need `authInitialized` flag to prevent flicker on page load

---

## 🎯 Phase 2: Core Bot Management (NEXT)

**Goal**: Enable users to manage bots and exchange connections  
**Estimated Time**: 10-12 hours  
**Priority**: 🔴 HIGH (Core feature)

### Why This Phase?
Before users can create bots, they need:
1. Exchange API connections configured
2. Ability to create/manage bots
3. View bot status and orders

This is the **critical path** to MVP functionality.

---

## 📋 Phase 2 Tasks Breakdown

### Task 1: Exchange Connections Integration ✅ COMPLETE (3-4 hours)

**Backend Status**: ✅ All APIs ready  
**Frontend Status**: 🟡 Page exists but uses mock data

#### Sub-tasks:
1. **Create Connections API Service** (1h)
   ```typescript
   // frontend/src/lib/api/connections.ts
   export const connectionsApi = {
     list: () => apiClient.get('/api/v1/exchanges/connections'),
     create: (data) => apiClient.post('/api/v1/exchanges/connections', data),
     update: (id, data) => apiClient.put(`/api/v1/exchanges/connections/${id}`, data),
     delete: (id) => apiClient.delete(`/api/v1/exchanges/connections/${id}`),
     test: (data) => apiClient.post('/api/v1/exchanges/connections/test', data),
     getAccount: (id) => apiClient.get(`/api/v1/exchanges/connections/${id}/account`),
   };
   ```

2. **Update Zustand Store** (1h)
   - Replace mock `connections` state with API integration
   - Add `fetchConnections()` action
   - Add `addConnection()` action
   - Add `updateConnection()` action
   - Add `deleteConnection()` action
   - Add `testConnection()` action

3. **Update Connections Page** (1-2h)
   - Replace `mockConnections` with `useAppStore`
   - Add loading states
   - Add error handling
   - Implement connection test feature
   - Handle form validation
   - Show API key status

#### Testing Checklist:
- [x] List connections from backend
- [x] Create new connection (Binance testnet)
- [x] Test connection (verify API keys)
- [x] Update connection credentials
- [x] Delete connection
- [x] Show connection status (connected/disconnected)
- [x] Handle API errors gracefully

#### Implementation Summary:
**Files Created:**
- ✅ `frontend/src/lib/types/connection.ts` - TypeScript interfaces
- ✅ `frontend/src/lib/api/connections.ts` - API service with 6 methods

**Files Updated:**
- ✅ `frontend/src/lib/store.ts` - Real API integration, async actions
- ✅ `frontend/src/pages/Connections.tsx` - Full UI with loading states, Test button, proper error handling

**Features Implemented:**
- ✅ Fetch connections on mount
- ✅ Create connection with testnet toggle
- ✅ Test connection button (validates API keys before saving)
- ✅ Delete connection with confirmation
- ✅ Refresh connections
- ✅ Loading spinner during operations
- ✅ Empty state when no connections
- ✅ Display connection status (active/inactive)
- ✅ Show API key preview with toggle
- ✅ Format dates properly (ISO → locale)

---

### Task 2: Bot Management API Integration (3-4 hours)

**Backend Status**: ✅ All APIs ready  
**Frontend Status**: 🟡 Pages exist but use mock data

#### Sub-tasks:
1. **Create Bots API Service** (1h)
   ```typescript
   // frontend/src/lib/api/bots.ts
   export const botsApi = {
     list: (params?) => apiClient.get('/api/v1/bots', { params }),
     create: (data) => apiClient.post('/api/v1/bots', data),
     get: (id) => apiClient.get(`/api/v1/bots/${id}`),
     update: (id, data) => apiClient.patch(`/api/v1/bots/${id}`, data),
     delete: (id) => apiClient.delete(`/api/v1/bots/${id}`),
     start: (id) => apiClient.post(`/api/v1/bots/${id}/start`),
     stop: (id) => apiClient.post(`/api/v1/bots/${id}/stop`),
     // Note: Need to verify if pause endpoint exists
   };
   ```

2. **Update Zustand Store** (1h)
   - Replace mock `bots` state
   - Add `fetchBots()` action with filters
   - Add `createBot()` action
   - Add `updateBot()` action
   - Add `deleteBot()` action
   - Add `startBot()`, `stopBot()` actions

3. **Update Bots Page** (1-2h)
   - Replace mock data with API calls
   - Add bot creation form
   - Add filters (status, exchange, strategy)
   - Add pagination
   - Implement bot controls (start/stop)
   - Show bot status and metrics
   - Handle loading and error states

#### Testing Checklist:
- [ ] List all bots
- [ ] Filter bots by status/exchange
- [ ] Create new bot
- [ ] Start/stop bot
- [ ] Update bot configuration
- [ ] Delete bot
- [ ] Navigate to bot detail page
- [ ] Show bot metrics (P&L, trades, etc.)

---

### Task 3: Bot Detail Page Integration (2-3 hours)

**Backend Status**: ✅ Bot + Order APIs ready  
**Frontend Status**: 🟡 Page exists but uses mock data

#### Sub-tasks:
1. **Create Orders API Service** (0.5h)
   ```typescript
   // frontend/src/lib/api/orders.ts
   export const ordersApi = {
     list: (params?) => apiClient.get('/api/v1/orders', { params }),
     getActive: () => apiClient.get('/api/v1/orders/active'),
     getStats: (params?) => apiClient.get('/api/v1/orders/stats', { params }),
     get: (id) => apiClient.get(`/api/v1/orders/${id}`),
     cancel: (id) => apiClient.delete(`/api/v1/orders/${id}`),
   };
   ```

2. **Update BotDetail Page** (1.5-2h)
   - Fetch bot data by ID from route params
   - Fetch bot orders with filters
   - Display order history
   - Add order status filters
   - Show performance metrics
   - Add bot control buttons
   - Handle loading and error states

3. **Add Performance Metrics** (0.5-1h)
   - Calculate P&L from orders
   - Show win rate
   - Display trade count
   - Show drawdown (if available)

#### Testing Checklist:
- [ ] Load bot detail by ID
- [ ] Show bot configuration
- [ ] Display order history
- [ ] Filter orders by status
- [ ] Show performance metrics
- [ ] Control bot from detail page
- [ ] Handle bot not found error
- [ ] Navigate back to bots list

---

### Task 4: Update Dashboard (1-2 hours)

**Backend Status**: ✅ Can aggregate from Bot + Order APIs  
**Frontend Status**: 🟡 Page exists but needs real data

#### Sub-tasks:
1. **Aggregate Dashboard Metrics** (1h)
   - Fetch all bots
   - Count active bots
   - Calculate total P&L from orders
   - Show recent trades
   - Display system status

2. **Update Index Page** (0.5-1h)
   - Replace mock stats
   - Add loading states
   - Show real market data
   - Add refresh button

#### Testing Checklist:
- [ ] Show total bot count
- [ ] Show active bot count
- [ ] Display total P&L
- [ ] Show recent trades
- [ ] Display market overview
- [ ] Handle empty state (no bots)

---

## 🔧 Technical Considerations

### 1. TypeScript Types
All backend response types need to be defined:
```typescript
// frontend/src/lib/types/bot.ts
export interface Bot {
  id: string;
  user_id: string;
  exchange_id: string;
  strategy_id: string | null;
  symbol: string;
  status: 'stopped' | 'running' | 'paused' | 'error';
  configuration: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// frontend/src/lib/types/connection.ts
export interface ExchangeConnection {
  id: string;
  user_id: string;
  exchange: string;
  name: string;
  api_key: string;
  is_active: boolean;
  is_testnet: boolean;
  created_at: string;
}

// frontend/src/lib/types/order.ts
export interface Order {
  id: string;
  bot_id: string;
  symbol: string;
  side: 'buy' | 'sell';
  order_type: 'market' | 'limit' | 'stop_loss' | 'take_profit';
  price: number | null;
  quantity: number;
  status: 'pending' | 'open' | 'filled' | 'cancelled' | 'rejected';
  filled_quantity: number;
  average_price: number | null;
  created_at: string;
  updated_at: string;
}
```

### 2. Error Handling Pattern
```typescript
try {
  const response = await botsApi.list();
  set({ bots: response.data, isLoading: false });
} catch (error) {
  if (axios.isAxiosError(error)) {
    const message = error.response?.data?.detail || 'Failed to fetch bots';
    toast({ title: 'Error', description: message, variant: 'destructive' });
  }
  set({ isLoading: false });
}
```

### 3. Loading States
```typescript
// In store
interface BotState {
  bots: Bot[];
  isLoading: boolean;
  error: string | null;
}

// In component
const { bots, isLoading } = useAppStore();

if (isLoading) return <LoadingSpinner />;
if (!bots.length) return <EmptyState />;
```

### 4. Pagination
Backend supports `skip` and `limit` parameters:
```typescript
// Store pagination state
interface PaginationState {
  currentPage: number;
  pageSize: number;
  totalCount: number;
}

// Fetch with pagination
fetchBots: async (page = 1, limit = 20) => {
  const skip = (page - 1) * limit;
  const response = await botsApi.list({ skip, limit });
  // Update state...
}
```

---

## 📊 Success Metrics for Phase 2

### Must Have (MVP)
- [ ] User can view all exchange connections
- [ ] User can add new connection (Binance testnet)
- [ ] User can test connection
- [ ] User can view all bots
- [ ] User can create a new bot
- [ ] User can start/stop a bot
- [ ] User can view bot details
- [ ] User can see order history
- [ ] Dashboard shows real bot count and P&L

### Nice to Have
- [ ] Edit connection credentials
- [ ] Delete connection with confirmation
- [ ] Edit bot configuration
- [ ] Pause bot (if backend supports)
- [ ] Real-time bot metrics
- [ ] Advanced order filters
- [ ] Export order history

---

## 🚀 Getting Started with Phase 2

### Step 1: Setup Types (15 minutes)
```bash
cd frontend/src/lib
mkdir -p types
touch types/bot.ts types/connection.ts types/order.ts types/common.ts
```

### Step 2: Create API Services (30 minutes)
```bash
mkdir -p lib/api
touch lib/api/connections.ts lib/api/bots.ts lib/api/orders.ts
```

### Step 3: Start with Connections (Most Independent)
Connections page is the best starting point because:
- No dependencies on other features
- Simple CRUD operations
- User needs this before creating bots
- Good warmup task

### Step 4: Test as You Go
After each API integration:
1. Check network tab for API calls
2. Verify data structure matches types
3. Test error cases (network failure, 401, etc.)
4. Verify loading states work

---

## 🎯 Phase 2 Timeline

### Day 1 (4 hours)
- ✅ Setup types (0.5h)
- ✅ Create API services (1h)
- ✅ Integrate Connections page (2.5h)
- ✅ Test connection flow

### Day 2 (4 hours)
- ✅ Integrate Bots list page (2h)
- ✅ Add bot creation form (1h)
- ✅ Test bot CRUD operations (1h)

### Day 3 (4 hours)
- ✅ Integrate BotDetail page (2h)
- ✅ Integrate Orders API (1h)
- ✅ Update Dashboard (1h)
- ✅ End-to-end testing

**Total**: ~12 hours (1.5 days @ 8h/day)

---

## 📝 Notes & Considerations

### Backend API Gaps
Based on FE_INTEGRATION_STATUS.md:

1. **Bot Pause Endpoint**: Not documented
   - Check if `POST /api/v1/bots/{id}/pause` exists
   - If not, can omit pause button for now

2. **Strategy Selection**: No Strategy API yet
   - Bot creation will need to handle `strategy_id` as optional
   - Can add dropdown later when Strategy API is built

3. **Performance Metrics**: Unclear API
   - For now, calculate from orders in frontend
   - Phase 3 will add dedicated performance endpoints

### Known Issues to Watch
1. Backend schema uses `email` not `username` (already fixed in auth)
2. CORS needs both settings.py AND .env updated
3. Token refresh needs queue to avoid concurrent calls
4. Protected routes need `authInitialized` check

---

## 🔄 After Phase 2

### Phase 3: Dashboard & Market Data (7 hours)
- Integrate market data API
- Add real-time price updates
- Show price charts
- Market overview widget

### Phase 4: Backtesting (7 hours)
- Integrate backtest API
- Run backtest
- View results
- Show equity curve

### Phase 5: Real-time Updates (8 hours)
- Implement WebSocket client
- Market price stream
- Order execution stream
- Bot metrics stream (if available)

---

## ✅ Ready to Start?

**Recommended First Task**: Exchange Connections Integration

**Why?**
- Independent feature (no dependencies)
- Simple CRUD operations
- Required before bot creation
- Good practice for the pattern

**Command to Start**:
```bash
cd frontend/src/lib
mkdir -p api types
touch api/connections.ts types/connection.ts
# Start coding!
```

**Need Help?**
- Review AUTH_PAGES_REQUIREMENTS.md for patterns
- Check existing pages (Login.tsx) for examples
- Backend API docs: http://localhost:8000/docs
- Test APIs with curl first to understand responses

---

**Status**: ✅ Ready to begin Phase 2  
**Next Review**: After Connections integration complete
