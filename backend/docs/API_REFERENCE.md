# API Reference - Trading Bot Platform

**Version**: 1.0.0  
**Base URL**: `http://localhost:8000`  
**Last Updated**: December 17, 2025

---

## Table of Contents

1. [Authentication](#authentication)
2. [Core APIs (Phase 1-3)](#core-apis-phase-1-3)
   - Health & System
   - User Management
   - Bot Management
   - Strategy Management
   - Order Management
   - Market Data
3. [Advanced APIs (Phase 4)](#advanced-apis-phase-4)
   - Risk Management
   - WebSocket Streaming
   - Cache Management
   - Background Jobs
4. [Backtesting APIs (Phase 5)](#backtesting-apis-phase-5)
5. [Error Responses](#error-responses)

---

## Authentication

All authenticated endpoints require a Bearer token:

```
Authorization: Bearer <access_token>
```

### Token Format
- **Access Token**: JWT with 30-minute expiration
- **Refresh Token**: JWT with 7-day expiration

---

## Core APIs (Phase 1-3)

### Health & System

#### GET /health
System health check (no authentication required).

**Response 200**:
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "1.0.0"
}
```

#### GET /api/v1/health
API health check (no authentication required).

**Response 200**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-17T10:00:00Z"
}
```

---

### Authentication Endpoints

#### POST /api/v1/auth/register
Register new user account.

**Request**:
```json
{
  "username": "trader123",
  "email": "trader@example.com",
  "password": "SecurePass123!",
  "full_name": "John Trader"
}
```

**Response 201**:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "username": "trader123",
    "email": "trader@example.com",
    "full_name": "John Trader",
    "is_active": true
  }
}
```

#### POST /api/v1/auth/login
Login user.

**Request**:
```json
{
  "username": "trader123",
  "password": "SecurePass123!"
}
```

**Response 200**: Same as register response.

#### POST /api/v1/auth/refresh
Refresh access token.

**Request**:
```json
{
  "refresh_token": "eyJ..."
}
```

**Response 200**:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

---

### User Management

#### GET /api/v1/users/me
Get current user profile (authenticated).

**Response 200**:
```json
{
  "id": "uuid",
  "username": "trader123",
  "email": "trader@example.com",
  "full_name": "John Trader",
  "is_active": true,
  "preferences": {
    "theme": "dark",
    "language": "en"
  },
  "created_at": "2025-12-01T10:00:00Z"
}
```

#### PATCH /api/v1/users/me
Update current user profile.

**Request**:
```json
{
  "full_name": "John Updated",
  "preferences": {
    "theme": "light"
  }
}
```

**Response 200**: Updated user object.

---

### Bot Management

#### POST /api/v1/bots
Create new trading bot (authenticated).

**Request**:
```json
{
  "name": "BTC Scalper",
  "strategy_id": "uuid",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "config": {
    "leverage": 10,
    "position_size": 0.1
  }
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "name": "BTC Scalper",
  "status": "inactive",
  "strategy_id": "uuid",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "created_at": "2025-12-17T10:00:00Z"
}
```

#### GET /api/v1/bots
List user's bots (authenticated).

**Query Parameters**:
- `status` (optional): Filter by status (active, inactive, paused)
- `exchange` (optional): Filter by exchange
- `limit` (optional): Results per page (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Response 200**:
```json
{
  "items": [/* bot objects */],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

#### GET /api/v1/bots/{bot_id}
Get bot details (authenticated).

**Response 200**: Bot object with full details.

#### PATCH /api/v1/bots/{bot_id}
Update bot configuration (authenticated).

**Request**:
```json
{
  "name": "Updated Name",
  "config": {
    "leverage": 5
  }
}
```

**Response 200**: Updated bot object.

#### POST /api/v1/bots/{bot_id}/start
Start bot trading (authenticated).

**Response 200**:
```json
{
  "message": "Bot started successfully",
  "bot_id": "uuid",
  "status": "active"
}
```

#### POST /api/v1/bots/{bot_id}/stop
Stop bot trading (authenticated).

**Response 200**: Similar to start response.

#### DELETE /api/v1/bots/{bot_id}
Delete bot (authenticated).

**Response 204**: No content.

---

### Order Management

#### POST /api/v1/orders
Place new order (authenticated).

**Request**:
```json
{
  "bot_id": "uuid",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "order_type": "LIMIT",
  "quantity": 0.001,
  "price": 45000.00
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "bot_id": "uuid",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "order_type": "LIMIT",
  "quantity": "0.001",
  "price": "45000.00",
  "status": "pending",
  "created_at": "2025-12-17T10:00:00Z"
}
```

#### GET /api/v1/orders
List orders (authenticated).

**Query Parameters**:
- `bot_id` (optional): Filter by bot
- `symbol` (optional): Filter by symbol
- `status` (optional): Filter by status
- `limit`, `offset`: Pagination

**Response 200**: Paginated list of orders.

#### GET /api/v1/orders/{order_id}
Get order details (authenticated).

**Response 200**: Order object with full details.

#### DELETE /api/v1/orders/{order_id}
Cancel order (authenticated).

**Response 200**:
```json
{
  "message": "Order cancelled successfully",
  "order_id": "uuid",
  "status": "cancelled"
}
```

---

### Market Data

#### GET /api/v1/market/ticker/{symbol}
Get current ticker price (authenticated).

**Response 200**:
```json
{
  "symbol": "BTCUSDT",
  "price": "45000.00",
  "timestamp": "2025-12-17T10:00:00Z"
}
```

#### GET /api/v1/market/klines/{symbol}
Get candlestick data (authenticated).

**Query Parameters**:
- `interval`: 1m, 5m, 15m, 1h, 4h, 1d
- `limit`: Number of candles (default: 500, max: 1000)

**Response 200**:
```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "data": [
    {
      "timestamp": "2025-12-17T10:00:00Z",
      "open": "45000.00",
      "high": "45500.00",
      "low": "44800.00",
      "close": "45200.00",
      "volume": "1234.56"
    }
  ]
}
```

---

## Advanced APIs (Phase 4)

### Risk Management

#### POST /api/v1/risk/limits
Create risk limit (authenticated).

**Request**:
```json
{
  "limit_type": "POSITION_SIZE",
  "limit_value": 10000.00,
  "symbol": "BTCUSDT",
  "warning_threshold": 80.0,
  "critical_threshold": 95.0
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "limit_type": "POSITION_SIZE",
  "limit_value": "10000.00",
  "enabled": true,
  "created_at": "2025-12-17T10:00:00Z"
}
```

#### GET /api/v1/risk/limits
List user's risk limits (authenticated).

**Response 200**: Array of risk limit objects.

#### GET /api/v1/risk/alerts
Get active risk alerts (authenticated).

**Response 200**:
```json
{
  "alerts": [
    {
      "id": "uuid",
      "alert_type": "POSITION_SIZE_WARNING",
      "severity": "warning",
      "message": "Position size approaching limit",
      "current_value": "8500.00",
      "limit_value": "10000.00",
      "triggered_at": "2025-12-17T10:00:00Z"
    }
  ]
}
```

---

### Cache Management

#### GET /api/v1/cache/health
Get cache system health (authenticated).

**Response 200**:
```json
{
  "status": "healthy",
  "connected": true,
  "redis_version": "7.0.0"
}
```

#### GET /api/v1/cache/stats
Get cache statistics (authenticated).

**Response 200**:
```json
{
  "total_keys": 1250,
  "memory_used": "15.2MB",
  "hit_rate": 0.85,
  "miss_rate": 0.15
}
```

#### DELETE /api/v1/cache/keys/{pattern}
Clear cache keys by pattern (authenticated, admin only).

**Response 200**:
```json
{
  "deleted_count": 45,
  "pattern": "market:*"
}
```

---

### Background Jobs

#### GET /api/v1/jobs/health
Get job system health (authenticated).

**Response 200**:
```json
{
  "running": true,
  "timestamp": "2025-12-17T10:00:00Z",
  "scheduler": {
    "enabled": true,
    "running": true
  },
  "workers": {
    "total": 5,
    "active": 3,
    "idle": 2
  }
}
```

#### GET /api/v1/jobs/stats
Get job statistics (authenticated).

**Response 200**:
```json
{
  "queue": {
    "pending": 12,
    "running": 5,
    "completed": 1024,
    "failed": 3
  },
  "workers": {
    "total": 5,
    "active": 3
  }
}
```

#### POST /api/v1/jobs
Enqueue new job (authenticated).

**Request**:
```json
{
  "name": "sync_portfolio",
  "args": {
    "user_id": "uuid",
    "exchange": "binance"
  },
  "priority": "high",
  "max_retries": 3
}
```

**Response 201**:
```json
{
  "job_id": "uuid",
  "status": "pending",
  "created_at": "2025-12-17T10:00:00Z"
}
```

---

### WebSocket Streaming

#### WS /api/v1/ws/market/{symbol}
Real-time market data stream (authenticated via query param token).

**Connection**: `ws://localhost:8000/api/v1/ws/market/BTCUSDT?token=<access_token>`

**Messages Received**:
```json
{
  "type": "ticker",
  "symbol": "BTCUSDT",
  "price": "45000.00",
  "timestamp": "2025-12-17T10:00:00.123Z"
}
```

#### WS /api/v1/ws/orders
Real-time order updates (authenticated).

**Messages Received**:
```json
{
  "type": "order_update",
  "order_id": "uuid",
  "status": "filled",
  "filled_quantity": "0.001",
  "timestamp": "2025-12-17T10:00:00.123Z"
}
```

---

## Backtesting APIs (Phase 5)

#### POST /api/v1/backtests
Create and run backtest (authenticated).

**Request**:
```json
{
  "strategy_id": "uuid",
  "symbol": "BTCUSDT",
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-12-01T00:00:00Z",
  "config": {
    "initial_capital": 10000.00,
    "mode": "PERCENT_EQUITY",
    "commission_rate": 0.001,
    "slippage_model": "FIXED"
  }
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "strategy_id": "uuid",
  "status": "running",
  "progress_percent": 0,
  "created_at": "2025-12-17T10:00:00Z"
}
```

#### GET /api/v1/backtests
List user's backtests (authenticated).

**Query Parameters**:
- `status`: Filter by status
- `strategy_id`: Filter by strategy
- `limit`, `offset`: Pagination

**Response 200**: Paginated list of backtests.

#### GET /api/v1/backtests/{backtest_id}
Get backtest details and results (authenticated).

**Response 200**:
```json
{
  "id": "uuid",
  "status": "completed",
  "progress_percent": 100,
  "results": {
    "total_return": "25.4",
    "sharpe_ratio": "1.82",
    "sortino_ratio": "2.15",
    "max_drawdown": "8.5",
    "win_rate": "62.5",
    "profit_factor": "1.85",
    "total_trades": 247
  },
  "equity_curve": [/* array of equity points */],
  "completed_at": "2025-12-17T10:05:00Z"
}
```

#### DELETE /api/v1/backtests/{backtest_id}
Cancel or delete backtest (authenticated).

**Response 204**: No content.

---

## Error Responses

### Standard Error Format

```json
{
  "detail": "Error message",
  "code": "ERROR_CODE",
  "timestamp": "2025-12-17T10:00:00Z"
}
```

### Common HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Successful GET, PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | No permission |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

### Example Error Responses

**400 Bad Request**:
```json
{
  "detail": "Invalid order quantity",
  "code": "INVALID_QUANTITY",
  "timestamp": "2025-12-17T10:00:00Z"
}
```

**401 Unauthorized**:
```json
{
  "detail": "Invalid or expired token",
  "code": "INVALID_TOKEN",
  "timestamp": "2025-12-17T10:00:00Z"
}
```

**422 Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "price"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Rate Limiting

- **Default**: 100 requests per minute per user
- **Burst**: 10 requests per second
- **Headers**:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

---

## Pagination

All list endpoints support pagination:

**Query Parameters**:
- `limit`: Items per page (default: 50, max: 100)
- `offset`: Starting position (default: 0)

**Response Format**:
```json
{
  "items": [/* array of items */],
  "total": 1250,
  "limit": 50,
  "offset": 0
}
```

---

## Interactive Documentation

Visit **http://localhost:8000/docs** for interactive Swagger UI documentation.

---

**Last Updated**: December 17, 2025  
**API Version**: 1.0.0
