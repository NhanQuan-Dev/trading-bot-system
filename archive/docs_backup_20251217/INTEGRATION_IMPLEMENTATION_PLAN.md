# KẾ HOẠCH TRIỂN KHAI TÍCH HỢP FRONTEND-BACKEND
## Option B: Full Implementation (6-7 Tuần)

**Ngày tạo:** 17/12/2025  
**Trạng thái hiện tại:** 45% Integration Ready (40+ endpoints đã có)  
**Mục tiêu:** 100% Integration Ready với 38 endpoints mới

---

## 📊 TỔNG QUAN

### Hiện trạng Backend
- ✅ **452 unit tests** (100% passing)
- ✅ **15+ database models** (User, Exchange, Bot, Strategy, Order, Position, Trade, etc.)
- ✅ **40+ existing endpoints** (Bots, Strategies, Backtest, Orders, MarketData, Cache, WebSocket)
- ✅ **Infrastructure đầy đủ:** Redis, WebSocket, Background Jobs, Cache Layer
- ⚠️ **Thiếu 38 endpoints** cho full frontend integration

### Mục tiêu Triển khai
- **38 endpoints mới** cho 11 frontend pages
- **8 controllers/services mới**: Portfolio, Connection, Performance, Risk, Alert, User, Enhanced Backtest, Enhanced Bot
- **Integration tests** cho tất cả endpoints mới
- **API documentation** đầy đủ (OpenAPI/Swagger)
- **Performance optimization** và caching strategy

---

## 🎯 PHASE 1: CRITICAL APIS (P0) - Tuần 1-2
**Thời gian:** 60-85 giờ (1.5-2 tuần)  
**Mục tiêu:** Enable Dashboard + Bot Management + Exchange Connections

### 1.1 Portfolio APIs (11 endpoints) - 40-50 giờ

#### Day 1-2: Setup & Summary Endpoint
**Files to create:**
- `backend/src/application/services/portfolio_service.py`
- `backend/src/presentation/api/v1/portfolio_controller.py`
- `backend/tests/unit/application/services/test_portfolio_service.py`
- `backend/tests/integration/test_portfolio_api.py`

**Tasks:**
1. Create PortfolioService class
   ```python
   class PortfolioService:
       def __init__(self, bot_repository, position_repository, trade_repository):
           self.bot_repo = bot_repository
           self.position_repo = position_repository
           self.trade_repo = trade_repository
       
       async def get_portfolio_summary(self, user_id: int) -> Dict:
           # Aggregate from all active bots
           # Calculate total balance, equity, P&L
           pass
   ```

2. Implement endpoints:
   - `GET /api/portfolio/summary` - Overall portfolio summary
     - Response: { total_balance, total_equity, unrealized_pnl, realized_pnl, roi }
     - Aggregates from all user's active bots
     - Cache: 60 seconds (Redis)

#### Day 3-4: Balance & P&L Endpoints
**Endpoints to implement:**
- `GET /api/portfolio/balance` - Current balance across all exchanges
  - Response: [{ exchange, asset, free, locked, total }]
  - Real-time data from positions
  
- `GET /api/portfolio/pnl/daily` - Daily P&L chart data (30 days)
  - Response: [{ date, pnl, cumulative_pnl }]
  - Calculate from Trade history
  - Cache: 300 seconds

- `GET /api/portfolio/pnl/monthly` - Monthly P&L summary
  - Response: [{ month, total_pnl, win_trades, loss_trades }]
  - Aggregate monthly statistics

#### Day 5-6: Performance Metrics
**Endpoints to implement:**
- `GET /api/portfolio/exposure` - Current market exposure by asset
  - Response: [{ asset, value, percentage, positions_count }]
  - Calculate from open positions
  
- `GET /api/portfolio/equity-curve` - Historical equity curve
  - Response: [{ timestamp, equity, drawdown }]
  - Time-series data from trades/positions
  - Cache: 300 seconds

- `GET /api/portfolio/positions` - All open positions summary
  - Response: [{ bot_id, symbol, side, size, entry_price, current_price, pnl }]
  - Aggregated positions view

#### Day 7-8: Advanced Analytics
**Endpoints to implement:**
- `GET /api/portfolio/performance` - Performance metrics
  - Response: { sharpe_ratio, sortino_ratio, max_drawdown, win_rate, profit_factor }
  - Calculate from trade history
  - Cache: 600 seconds

- `GET /api/portfolio/metrics` - Key trading metrics
  - Response: { total_trades, avg_profit, avg_loss, largest_win, largest_loss }
  
- `GET /api/portfolio/trade-distribution` - Win/loss distribution chart
  - Response: { bins: [], frequencies: [] }
  - Histogram data for P&L distribution

- `GET /api/portfolio/drawdown-curve` - Drawdown over time
  - Response: [{ date, drawdown_pct, underwater_days }]

**Technical Requirements:**
- Use PostgreSQL aggregation queries for performance
- Implement Redis caching (TTL: 60-600s based on data type)
- Add database indexes: trades(user_id, created_at), positions(user_id, status)
- Pagination support: 50 items default
- Error handling for missing data
- Unit tests: ~30 tests for PortfolioService
- Integration tests: ~11 tests for all endpoints

---

### 1.2 Connection Management APIs (6 endpoints) - 15-25 giờ

#### Day 9-10: Connection CRUD
**Files to create:**
- `backend/src/application/services/connection_service.py`
- `backend/src/presentation/api/v1/connection_controller.py`
- `backend/tests/unit/application/services/test_connection_service.py`

**Endpoints to implement:**
1. `GET /api/connections` - List all user's exchange connections
   - Response: [{ id, exchange_id, name, status, is_testnet, created_at }]
   - Status: active, inactive, error
   
2. `POST /api/connections` - Add new exchange connection
   - Request: { exchange_id, api_key, api_secret, api_passphrase?, is_testnet }
   - Validate API keys format
   - Create ExchangeAPIKey record
   
3. `PUT /api/connections/{id}` - Update connection
   - Request: { name?, api_key?, api_secret?, status? }
   - Re-validate if keys changed
   
4. `DELETE /api/connections/{id}` - Remove connection
   - Soft delete if has active bots
   - Hard delete if no dependencies

#### Day 11: Connection Testing
**Endpoints to implement:**
5. `POST /api/connections/test` - Test API credentials
   - Request: { exchange_id, api_key, api_secret, is_testnet }
   - Call exchange API to verify
   - Return: { success, balance?, error? }
   - Timeout: 10 seconds
   
6. `POST /api/connections/{id}/refresh` - Refresh connection status
   - Test existing connection
   - Update status in database

**Technical Requirements:**
- API key encryption at rest (use existing encryption service)
- Rate limiting: 10 requests/minute for test endpoint
- Async validation with timeout
- Security: mask API keys in responses (show last 4 chars only)
- Unit tests: ~15 tests
- Integration tests: ~6 tests

---

### 1.3 Bot Resource APIs (3 endpoints) - 5-10 giờ

#### Day 12: Bot Detail Resources
**Files to modify:**
- `backend/src/presentation/api/v1/bot_controller.py` (extend existing)
- `backend/tests/integration/test_bot_api.py` (add tests)

**Endpoints to implement:**
1. `GET /api/bots/{id}/positions` - Bot's open positions
   - Response: [{ id, symbol, side, size, entry_price, current_price, pnl, created_at }]
   - Pagination: 50 positions per page
   - Sort: by created_at desc
   
2. `GET /api/bots/{id}/orders` - Bot's recent orders
   - Response: [{ id, symbol, side, type, quantity, price, status, created_at }]
   - Pagination: 50 orders per page
   - Filter: by status (open, filled, cancelled)
   
3. `GET /api/bots/{id}/trades` - Bot's trade history
   - Response: [{ id, symbol, side, quantity, price, fee, pnl, created_at }]
   - Pagination: 50 trades per page
   - Date range filter support

**Technical Requirements:**
- Reuse existing Position/Order/Trade repositories
- Add bot_id indexes for performance
- Cache: None (real-time data)
- Unit tests: ~8 tests
- Integration tests: ~3 tests

---

### Phase 1 Deliverables
✅ **20 endpoints** triển khai xong  
✅ **3 controllers mới:** Portfolio, Connection, Bot (extended)  
✅ **3 services mới:** PortfolioService, ConnectionService  
✅ **60+ unit tests**  
✅ **20+ integration tests**  
✅ **Dashboard page** hoàn toàn functional  
✅ **Bot management** đầy đủ chi tiết  
✅ **Exchange connections** management hoàn chỉnh  

---

## 🎯 PHASE 2: HIGH PRIORITY APIS (P1) - Tuần 3-4
**Thời gian:** 60-80 giờ (1.5-2 tuần)  
**Mục tiêu:** Enable Performance Analytics + Risk Management

### 2.1 Performance Analytics APIs (6 endpoints) - 35-45 giờ

#### Week 3 Day 1-2: Setup Performance Service
**Files to create:**
- `backend/src/application/services/performance_analytics_service.py`
- `backend/src/presentation/api/v1/performance_controller.py`
- `backend/tests/unit/application/services/test_performance_service.py`

**Endpoints to implement:**
1. `GET /api/performance/overview` - Performance overview dashboard
   - Response: { 
       total_return_pct, 
       sharpe_ratio, 
       sortino_ratio, 
       max_drawdown, 
       calmar_ratio,
       win_rate,
       profit_factor
     }
   - Calculate from all user's trades
   - Cache: 300 seconds

#### Week 3 Day 3-4: Time Series Analytics
**Endpoints to implement:**
2. `GET /api/performance/returns/daily` - Daily returns chart
   - Response: [{ date, return_pct, cumulative_return_pct }]
   - 90 days default, configurable via query param
   
3. `GET /api/performance/returns/monthly` - Monthly performance
   - Response: [{ month, return_pct, trades_count, win_rate }]
   - 12 months default

4. `GET /api/performance/metrics/by-bot` - Bot-level performance comparison
   - Response: [{ bot_id, bot_name, total_pnl, win_rate, sharpe_ratio }]
   - Compare all user's bots

#### Week 3 Day 5: Advanced Metrics
**Endpoints to implement:**
5. `GET /api/performance/metrics/by-strategy` - Strategy performance comparison
   - Response: [{ strategy_id, strategy_name, total_pnl, trades_count, avg_profit }]
   - Aggregate by strategy

6. `GET /api/performance/risk-metrics` - Risk analysis
   - Response: { 
       var_95: float,  # Value at Risk
       cvar_95: float,  # Conditional VaR
       volatility: float,
       beta: float,
       correlation_btc: float
     }
   - Statistical risk measures

**Technical Implementation:**
- Financial calculations module:
  ```python
  class PerformanceMetrics:
      @staticmethod
      def calculate_sharpe_ratio(returns: List[float], risk_free_rate=0.02) -> float:
          # (mean_return - risk_free) / std_dev
          pass
      
      @staticmethod
      def calculate_sortino_ratio(returns: List[float]) -> float:
          # Downside deviation only
          pass
      
      @staticmethod
      def calculate_calmar_ratio(returns: List[float], max_drawdown: float) -> float:
          # Annual return / max drawdown
          pass
  ```

- Use numpy/pandas for efficient calculations
- Cache complex calculations (300-600s)
- Add database indexes: trades(user_id, created_at, pnl)
- Unit tests: ~20 tests for metrics calculations
- Integration tests: ~6 tests for endpoints

---

### 2.2 Risk Management APIs (6 endpoints) - 25-35 giờ

#### Week 4 Day 1-2: Risk Service Setup
**Files to create:**
- `backend/src/application/services/risk_monitoring_service.py`
- `backend/src/presentation/api/v1/risk_controller.py`
- `backend/tests/unit/application/services/test_risk_service.py`

**Endpoints to implement:**
1. `GET /api/risk/overview` - Risk dashboard overview
   - Response: {
       current_exposure: float,
       leverage_used: float,
       margin_level: float,
       risk_score: int,  # 1-100
       active_alerts: int
     }
   - Real-time risk metrics

2. `GET /api/risk/exposure` - Detailed exposure breakdown
   - Response: [{ 
       asset: str,
       exposure_value: float,
       exposure_pct: float,
       limit: float,
       status: "safe" | "warning" | "danger"
     }]
   - Per-asset risk analysis

#### Week 4 Day 3-4: Risk Limits & Alerts
**Endpoints to implement:**
3. `GET /api/risk/limits` - User's risk limits configuration
   - Response: [{ 
       type: "position_size" | "daily_loss" | "exposure",
       value: float,
       current: float,
       status: str
     }]
   - From RiskLimit model

4. `POST /api/risk/limits` - Update risk limits
   - Request: { position_size_limit?, daily_loss_limit?, exposure_limit? }
   - Validate and save to RiskLimit table

5. `GET /api/risk/alerts` - Risk alerts history
   - Response: [{ 
       id, type, severity, message, triggered_at, resolved_at
     }]
   - From RiskAlert model
   - Pagination: 50 alerts

#### Week 4 Day 5: Emergency Controls
**Endpoints to implement:**
6. `POST /api/risk/emergency-stop` - Emergency stop all bots
   - Request: { reason: str }
   - Stop all user's active bots
   - Close all open positions (market orders)
   - Send alert notifications
   - Audit log

**Technical Requirements:**
- Real-time exposure calculation from positions
- WebSocket integration for live risk updates
- Background job for continuous risk monitoring
- Risk score algorithm:
  ```python
  def calculate_risk_score(exposure_pct, leverage, volatility, drawdown) -> int:
      # Weighted formula returning 1-100
      # 1-30: Low risk (green)
      # 31-60: Medium risk (yellow)
      # 61-100: High risk (red)
      pass
  ```
- Unit tests: ~15 tests
- Integration tests: ~6 tests

---

### Phase 2 Deliverables
✅ **12 endpoints** triển khai xong  
✅ **2 controllers mới:** Performance, Risk  
✅ **2 services mới:** PerformanceAnalyticsService, RiskMonitoringService  
✅ **35+ unit tests**  
✅ **12+ integration tests**  
✅ **Performance page** hoàn toàn functional  
✅ **Risk management** real-time monitoring  
✅ **Financial metrics** calculations library  

---

## 🎯 PHASE 3: MEDIUM PRIORITY APIS (P2) - Tuần 5
**Thời gian:** 30-40 giờ (1 tuần)  
**Mục tiêu:** Enhanced Backtest Analysis + Strategy Performance

### 3.1 Backtest Detail APIs (4 endpoints) - 20-25 giờ

#### Week 5 Day 1-2: Backtest Enhancement
**Files to modify:**
- `backend/src/presentation/api/v1/backtest_controller.py` (extend existing)
- `backend/tests/integration/test_backtest_api.py`

**Endpoints to implement:**
1. `GET /api/backtests/{id}/trades` - Backtest trade history
   - Response: [{ 
       id, symbol, side, entry_price, exit_price, 
       quantity, pnl, pnl_pct, duration, created_at 
     }]
   - Pagination: 100 trades per page
   - Filter: by symbol, side, pnl range
   - From BacktestTrade model

2. `GET /api/backtests/{id}/equity-curve` - Backtest equity curve
   - Response: [{ timestamp, equity, drawdown }]
   - Time-series data
   - Calculate from BacktestTrade

3. `GET /api/backtests/{id}/positions` - Position timeline
   - Response: [{ 
       timestamp, open_positions, total_exposure, margin_used 
     }]
   - Historical position data

#### Week 5 Day 3: Export & Comparison
**Endpoints to implement:**
4. `GET /api/backtests/{id}/export/csv` - Export backtest results
   - Format: CSV file download
   - Headers: Date, Symbol, Side, Entry, Exit, P&L, P&L%
   - Stream large files

**Technical Requirements:**
- Efficient pagination for large backtest results
- CSV streaming for memory efficiency
- Cache backtest summary (3600s - backtest immutable)
- Unit tests: ~10 tests
- Integration tests: ~4 tests

---

### 3.2 Strategy Performance APIs (2 endpoints) - 10-15 giờ

#### Week 5 Day 4-5: Strategy Analytics
**Files to modify:**
- `backend/src/presentation/api/v1/strategy_controller.py` (extend existing)

**Endpoints to implement:**
1. `GET /api/strategies/{id}/performance` - Strategy performance metrics
   - Response: {
       total_pnl: float,
       total_trades: int,
       win_rate: float,
       avg_profit: float,
       sharpe_ratio: float,
       active_bots: int,
       best_symbol: str
     }
   - Aggregate from all bots using this strategy

2. `GET /api/strategies/{id}/performance-history` - Historical performance
   - Response: [{ month, pnl, trades_count, win_rate }]
   - Monthly breakdown
   - 12 months default

**Technical Requirements:**
- Complex aggregation queries across Bot, Trade tables
- Cache: 300 seconds
- Unit tests: ~5 tests
- Integration tests: ~2 tests

---

### Phase 3 Deliverables
✅ **6 endpoints** triển khai xong  
✅ **Backtest detail page** với trade history & analytics  
✅ **Strategy performance** tracking  
✅ **CSV export** functionality  
✅ **15+ unit tests**  
✅ **6+ integration tests**  

---

## 🎯 PHASE 4: LOW PRIORITY APIS (P3) - Tuần 6
**Thời gian:** 40-50 giờ (1 tuần)  
**Mục tiêu:** Alerts System + User Settings + Polish

### 4.1 Alerts APIs (7 endpoints) - 25-30 giờ

#### Week 6 Day 1-2: Alert Management
**Files to create:**
- `backend/src/application/services/alert_service.py`
- `backend/src/presentation/api/v1/alert_controller.py`
- `backend/tests/unit/application/services/test_alert_service.py`

**Endpoints to implement:**
1. `GET /api/alerts` - List user's alerts
   - Response: [{ id, type, message, severity, status, created_at }]
   - Pagination: 50 alerts
   - Filter: by type, severity, status

2. `POST /api/alerts` - Create new alert rule
   - Request: { 
       type: "price" | "pnl" | "position" | "risk",
       condition: { ... },
       notification_channels: ["email", "webhook", "ui"]
     }
   - Validate condition logic

3. `GET /api/alerts/{id}` - Alert details
   - Response: { id, type, condition, status, history: [] }

4. `PUT /api/alerts/{id}` - Update alert rule
   - Request: { condition?, enabled?, notification_channels? }

5. `DELETE /api/alerts/{id}` - Delete alert
   - Soft delete, keep history

#### Week 6 Day 3: Alert Actions & History
**Endpoints to implement:**
6. `POST /api/alerts/{id}/acknowledge` - Acknowledge alert
   - Mark as read/acknowledged
   - Update status

7. `GET /api/alerts/history` - Alert trigger history
   - Response: [{ alert_id, triggered_at, message, resolved_at }]
   - Last 30 days

**Technical Requirements:**
- Background job for alert monitoring (runs every 1 minute)
- WebSocket push for real-time alerts
- Email/webhook integration (use existing notification service)
- Alert conditions parser:
  ```python
  class AlertCondition:
      def evaluate(self, current_value: float) -> bool:
          # Parse condition: "price > 50000", "pnl < -1000"
          pass
  ```
- Unit tests: ~15 tests
- Integration tests: ~7 tests

---

### 4.2 User & Settings APIs (8 endpoints) - 15-20 giờ

#### Week 6 Day 4-5: User Management
**Files to create:**
- `backend/src/presentation/api/v1/user_controller.py`
- `backend/src/domain/entities/user_preferences.py`
- `backend/tests/integration/test_user_api.py`

**Endpoints to implement:**
1. `GET /api/user/profile` - User profile
   - Response: { id, email, username, created_at, preferences }

2. `PUT /api/user/profile` - Update profile
   - Request: { username?, email?, password? }
   - Validate and hash password

3. `GET /api/user/preferences` - User preferences
   - Response: { 
       theme: "light" | "dark",
       language: "en" | "vi",
       timezone: str,
       notifications_enabled: bool,
       default_exchange: str
     }

4. `PUT /api/user/preferences` - Update preferences
   - Request: { theme?, language?, timezone?, ... }

#### Week 6 Day 5: Activity & Settings
**Endpoints to implement:**
5. `GET /api/user/activity-log` - User activity history
   - Response: [{ action, details, ip_address, created_at }]
   - Pagination: 100 items
   - Security audit trail

6. `GET /api/user/api-keys` - API keys management
   - Response: [{ id, name, key_preview, permissions, created_at }]
   - For future API access

7. `POST /api/user/api-keys` - Generate new API key
   - Response: { key, secret }
   - One-time display of secret

8. `DELETE /api/user/api-keys/{id}` - Revoke API key

**Technical Requirements:**
- Create UserPreferences model (JSON field or separate table)
- Activity logging middleware
- API key generation (secure random + hash)
- Unit tests: ~10 tests
- Integration tests: ~8 tests

---

### Phase 4 Deliverables
✅ **15 endpoints** triển khai xong  
✅ **2 controllers mới:** Alert, User  
✅ **1 service mới:** AlertService  
✅ **Alerts system** với real-time notifications  
✅ **User settings** management  
✅ **Activity logging** & audit trail  
✅ **25+ unit tests**  
✅ **15+ integration tests**  

---

## 🎯 PHASE 5: TESTING & OPTIMIZATION - Tuần 7
**Thời gian:** 30-40 giờ (1 tuần)  
**Mục tiêu:** Integration Testing + Performance Optimization + Documentation

### 5.1 Integration Testing (15-20 giờ)

#### Week 7 Day 1-2: End-to-End Tests
**Files to create:**
- `backend/tests/e2e/test_dashboard_flow.py`
- `backend/tests/e2e/test_bot_lifecycle.py`
- `backend/tests/e2e/test_trading_flow.py`

**Test Scenarios:**
1. **Complete Dashboard Flow**
   - User login → Portfolio summary → Daily P&L chart → Exposure view
   - Verify data consistency across endpoints

2. **Bot Lifecycle Flow**
   - Create connection → Create bot → Start bot → Monitor positions/orders → Stop bot
   - Verify state transitions

3. **Trading Flow**
   - Bot receives signal → Creates order → Order filled → Position created → Trade recorded
   - End-to-end validation

4. **Risk Management Flow**
   - Set risk limits → Trigger alert → Emergency stop → Verify all bots stopped

**Tools:**
- pytest-asyncio for async testing
- httpx for HTTP client
- Factory pattern for test data
- 20+ end-to-end test scenarios

---

### 5.2 Performance Optimization (10-15 giờ)

#### Week 7 Day 3-4: Load Testing & Optimization

**Tasks:**
1. **Load Testing**
   - Use locust or k6 for load testing
   - Test scenarios:
     - 100 concurrent users on dashboard
     - 1000 requests/second on portfolio summary
     - WebSocket connections (100 simultaneous)
   - Target: < 200ms p95 latency

2. **Database Optimization**
   - Review slow queries (enable query logging)
   - Add missing indexes:
     ```sql
     CREATE INDEX idx_trades_user_created ON trades(user_id, created_at DESC);
     CREATE INDEX idx_positions_user_status ON positions(user_id, status);
     CREATE INDEX idx_orders_bot_created ON orders(bot_id, created_at DESC);
     ```
   - Optimize aggregation queries (use CTEs, window functions)

3. **Cache Strategy Review**
   - Profile cache hit rates
   - Adjust TTL values based on access patterns
   - Implement cache warming for popular endpoints

4. **Query Optimization**
   - Use EXPLAIN ANALYZE for complex queries
   - Consider materialized views for expensive aggregations
   - Implement query result pagination everywhere

**Files to create:**
- `backend/tests/performance/test_load_dashboard.py`
- `backend/tests/performance/test_load_portfolio.py`
- `backend/docs/PERFORMANCE_OPTIMIZATION.md`

---

### 5.3 API Documentation (5-10 giờ)

#### Week 7 Day 5: Documentation & Polish

**Tasks:**
1. **OpenAPI/Swagger Documentation**
   - Complete all endpoint documentation
   - Add request/response examples
   - Document error codes
   - Update API_DOCUMENTATION.md

2. **Postman Collection**
   - Export complete API collection
   - Include example requests
   - Environment variables setup

3. **Developer Guide**
   - Update INTEGRATION_GUIDE.md
   - Add frontend integration examples
   - Document authentication flow
   - API rate limits documentation

4. **Deployment Guide**
   - Production checklist
   - Environment variables
   - Database migration guide
   - Monitoring setup

**Files to update/create:**
- `backend/docs/API_DOCUMENTATION.md` (complete update)
- `backend/docs/INTEGRATION_GUIDE.md` (new)
- `backend/docs/DEPLOYMENT_GUIDE.md` (new)
- `backend/postman/trading-bot-api.json` (new)

---

### Phase 5 Deliverables
✅ **20+ end-to-end tests**  
✅ **Load testing** complete with performance baselines  
✅ **Database optimization** với indexes và query tuning  
✅ **Complete API documentation** (OpenAPI + Postman)  
✅ **Integration guides** cho frontend team  
✅ **Deployment documentation** đầy đủ  

---

## 📋 TIMELINE SUMMARY

| Phase | Week | Endpoints | Hours | Status |
|-------|------|-----------|-------|--------|
| **Phase 1 (P0)** | 1-2 | 20 | 60-85 | ⏳ Pending |
| **Phase 2 (P1)** | 3-4 | 12 | 60-80 | ⏳ Pending |
| **Phase 3 (P2)** | 5 | 6 | 30-40 | ⏳ Pending |
| **Phase 4 (P3)** | 6 | 15 | 40-50 | ⏳ Pending |
| **Phase 5 (Testing)** | 7 | 0 | 30-40 | ⏳ Pending |
| **TOTAL** | **7 weeks** | **53** | **220-295** | **0%** |

---

## 🚀 IMMEDIATE NEXT STEPS

### Day 1 (Bắt đầu Phase 1)
1. ✅ Review plan này với team
2. ⏳ Setup branch: `feature/phase1-critical-apis`
3. ⏳ Create PortfolioService skeleton
4. ⏳ Create PortfolioController với routing
5. ⏳ Setup database indexes cho portfolio queries

### Day 2
1. Implement `GET /api/portfolio/summary`
2. Write unit tests cho summary calculation
3. Test với existing data
4. Implement caching logic

### Day 3-7
- Continue với remaining Phase 1 endpoints
- Daily commits và progress tracking
- Integration tests sau mỗi controller

---

## 📊 SUCCESS METRICS

### Code Quality
- ✅ 100% unit test coverage cho services mới
- ✅ 100% integration test coverage cho endpoints mới
- ✅ 0 critical security vulnerabilities
- ✅ Code review approval trước merge

### Performance
- ✅ API response time: p95 < 200ms
- ✅ Database query time: p95 < 100ms
- ✅ Cache hit rate: > 70%
- ✅ WebSocket latency: < 50ms

### Documentation
- ✅ 100% API endpoints documented
- ✅ OpenAPI spec complete
- ✅ Integration examples cho mỗi endpoint
- ✅ Deployment guide complete

---

## 🔒 RISK MANAGEMENT

### Technical Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Performance issues với aggregation queries | High | Medium | Implement caching, database indexes, load testing |
| Breaking changes trong existing APIs | High | Low | Comprehensive tests, API versioning |
| Security vulnerabilities | Critical | Low | Security audit, API key encryption, rate limiting |
| Database migration issues | Medium | Low | Backup strategy, rollback plan, staging testing |

### Timeline Risks
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Scope creep | High | Medium | Strict scope adherence, change control process |
| Integration complexity | Medium | Medium | Early integration testing, frequent communication |
| Testing bottleneck | Medium | Low | Parallel test development, automated testing |

---

## 🎯 PHASE GATES

Mỗi phase phải pass qua checkpoints sau trước khi proceed:

### Phase 1 Gate
- [ ] All 20 endpoints implemented
- [ ] 60+ unit tests passing
- [ ] 20+ integration tests passing
- [ ] Dashboard fully functional in frontend
- [ ] Performance: < 200ms response time
- [ ] Code review approved

### Phase 2 Gate
- [ ] All 12 endpoints implemented
- [ ] Performance metrics calculations validated
- [ ] Risk monitoring functional
- [ ] 35+ unit tests passing
- [ ] Integration tests passing
- [ ] Frontend integration successful

### Phase 3 Gate
- [ ] Backtest detail pages working
- [ ] CSV export tested with large datasets
- [ ] Strategy performance accurate
- [ ] All tests passing

### Phase 4 Gate
- [ ] Alert system functional
- [ ] User settings persisted
- [ ] All tests passing
- [ ] Documentation complete

### Phase 5 Gate
- [ ] Load testing passed (target: 100 concurrent users)
- [ ] Performance optimizations applied
- [ ] Complete documentation
- [ ] Production deployment ready

---

## 📚 APPENDIX

### A. Database Indexes Required
```sql
-- Portfolio queries
CREATE INDEX idx_trades_user_created ON trades(user_id, created_at DESC);
CREATE INDEX idx_trades_user_pnl ON trades(user_id, pnl);
CREATE INDEX idx_positions_user_status ON positions(user_id, status);
CREATE INDEX idx_positions_user_asset ON positions(user_id, asset);

-- Bot queries
CREATE INDEX idx_orders_bot_created ON orders(bot_id, created_at DESC);
CREATE INDEX idx_trades_bot_created ON trades(bot_id, created_at DESC);

-- Performance queries  
CREATE INDEX idx_trades_user_symbol_created ON trades(user_id, symbol, created_at);

-- Alert queries
CREATE INDEX idx_alerts_user_status ON alerts(user_id, status);
```

### B. Cache Strategy
| Endpoint | TTL | Reason |
|----------|-----|--------|
| /portfolio/summary | 60s | Balance changes frequently |
| /portfolio/pnl/daily | 300s | Historical data |
| /portfolio/equity-curve | 300s | Expensive calculation |
| /performance/overview | 300s | Complex aggregation |
| /backtest/{id}/* | 3600s | Immutable data |
| /strategies/{id}/performance | 300s | Aggregated data |

### C. API Rate Limits
| Endpoint Category | Rate Limit | Burst |
|------------------|------------|-------|
| Authentication | 5/min | 10 |
| Portfolio | 60/min | 100 |
| Trading (orders) | 30/min | 50 |
| Market Data | 120/min | 200 |
| WebSocket | 10 connections/user | - |

### D. Dependencies
```python
# requirements.txt additions
pandas>=2.0.0  # For performance calculations
numpy>=1.24.0  # For statistical metrics
openpyxl>=3.1.0  # For Excel export (future)
python-crontab>=3.0.0  # For cron parsing
```

---

**Document Version:** 1.0  
**Last Updated:** 17/12/2025  
**Author:** Development Team  
**Status:** Ready for Implementation  

---

## 🎬 BẮT ĐẦU PHASE 1

Khi sẵn sàng, run command:
```bash
git checkout -b feature/phase1-critical-apis
cd backend
```

Sau đó implement theo Day 1-2 plan ở trên! 🚀
