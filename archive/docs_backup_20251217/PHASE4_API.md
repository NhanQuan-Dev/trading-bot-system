# Phase 4 API Documentation

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000`  
**Phase 4 Endpoints:** Risk Management, WebSocket, Cache, Background Jobs

---

## Risk Management API

### Create Risk Limit

#### POST /api/v1/risk/limits
Create a new risk limit for user.

**Authentication:** Required

**Request Body:**
```json
{
  "symbol": "BTCUSDT",
  "limit_type": "position_size",
  "threshold_value": 10000.00,
  "warning_value": 8000.00,
  "enabled": true
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "symbol": "BTCUSDT",
  "limit_type": "position_size",
  "threshold_value": "10000.00",
  "warning_value": "8000.00",
  "enabled": true,
  "created_at": "2025-12-16T10:00:00Z"
}
```

---

### List Risk Limits

#### GET /api/v1/risk/limits
Get all risk limits for current user.

**Authentication:** Required

**Query Parameters:**
- `symbol` (optional): Filter by symbol
- `limit_type` (optional): Filter by limit type
- `enabled` (optional): Filter by enabled status

**Response (200 OK):**
```json
{
  "limits": [
    {
      "id": "uuid",
      "symbol": "BTCUSDT",
      "limit_type": "position_size",
      "threshold_value": "10000.00",
      "warning_value": "8000.00",
      "enabled": true
    }
  ]
}
```

---

### Evaluate Risk

#### POST /api/v1/risk/evaluate
Evaluate current risk metrics.

**Authentication:** Required

**Request Body:**
```json
{
  "symbol": "BTCUSDT"
}
```

**Response (200 OK):**
```json
{
  "risk_level": "moderate",
  "metrics": {
    "position_size": "5000.00",
    "daily_pnl": "-150.50",
    "total_exposure": "15000.00",
    "margin_ratio": "0.35"
  },
  "violations": [],
  "warnings": []
}
```

---

### Get Risk Alerts

#### GET /api/v1/risk/alerts
Get risk alerts for current user.

**Authentication:** Required

**Query Parameters:**
- `status` (optional): Filter by alert status (triggered, acknowledged, resolved)
- `severity` (optional): Filter by severity (low, medium, high, critical)
- `limit` (optional): Number of results (default: 50)

**Response (200 OK):**
```json
{
  "alerts": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "alert_type": "position_size_exceeded",
      "severity": "high",
      "message": "Position size exceeded threshold",
      "triggered_at": "2025-12-16T10:30:00Z",
      "status": "triggered",
      "metadata": {
        "symbol": "BTCUSDT",
        "current_value": "11000.00",
        "threshold": "10000.00"
      }
    }
  ]
}
```

---

## WebSocket API

### Connect to WebSocket

#### WS /api/v1/ws
Connect to WebSocket for real-time data.

**Authentication:** Required (via query parameter `token`)

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws?token=YOUR_ACCESS_TOKEN');
```

**Subscribe to Market Data:**
```json
{
  "action": "subscribe",
  "channel": "ticker",
  "symbols": ["BTCUSDT", "ETHUSDT"]
}
```

**Receive Price Updates:**
```json
{
  "channel": "ticker",
  "symbol": "BTCUSDT",
  "price": "43250.50",
  "change_24h": "2.45",
  "volume_24h": "125000.00",
  "timestamp": "2025-12-16T10:00:00Z"
}
```

**Subscribe to Trades:**
```json
{
  "action": "subscribe",
  "channel": "trades",
  "symbols": ["BTCUSDT"]
}
```

**Unsubscribe:**
```json
{
  "action": "unsubscribe",
  "channel": "ticker",
  "symbols": ["BTCUSDT"]
}
```

---

### WebSocket Management

#### GET /api/v1/websocket/connections
Get active WebSocket connections.

**Authentication:** Required

**Response (200 OK):**
```json
{
  "connections": [
    {
      "connection_id": "uuid",
      "client_id": "client-123",
      "connected_at": "2025-12-16T10:00:00Z",
      "subscriptions": ["ticker:BTCUSDT", "trades:ETHUSDT"]
    }
  ]
}
```

---

## Cache Management API

### Get Cache Health

#### GET /api/v1/cache/health
Check cache service health.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "redis_connected": true,
  "uptime_seconds": 3600,
  "cache_hit_rate": 0.85
}
```

---

### Get Cache Statistics

#### GET /api/v1/cache/stats
Get cache statistics.

**Response (200 OK):**
```json
{
  "market_data_cache": {
    "keys": 150,
    "hit_rate": 0.92,
    "avg_ttl_seconds": 300
  },
  "user_session_cache": {
    "keys": 45,
    "hit_rate": 0.88,
    "avg_ttl_seconds": 1800
  },
  "price_cache": {
    "keys": 200,
    "hit_rate": 0.95,
    "avg_ttl_seconds": 60
  }
}
```

---

### Get Cached Market Data

#### GET /api/v1/cache/market-data/{symbol}
Get cached market data for a symbol.

**Response (200 OK):**
```json
{
  "symbol": "BTCUSDT",
  "price": "43250.50",
  "order_book": {
    "bids": [[43250.00, 1.5], [43249.50, 2.3]],
    "asks": [[43251.00, 1.2], [43251.50, 1.8]]
  },
  "recent_trades": [
    {
      "price": "43250.50",
      "quantity": "0.5",
      "time": "2025-12-16T10:00:00Z"
    }
  ],
  "cached_at": "2025-12-16T10:00:05Z"
}
```

---

### Clear Cache

#### DELETE /api/v1/cache/{cache_type}
Clear specific cache type.

**Authentication:** Required (Admin)

**Path Parameters:**
- `cache_type`: market_data, user_session, price, or all

**Response (200 OK):**
```json
{
  "cleared": 150,
  "cache_type": "market_data"
}
```

---

## Background Jobs API

### Get Job Service Health

#### GET /api/v1/jobs/health
Check job service health.

**Response (200 OK):**
```json
{
  "running": true,
  "timestamp": "2025-12-16T10:00:00Z",
  "scheduler": {
    "enabled": true,
    "running": true
  },
  "workers": {
    "mode": "single",
    "running": true
  },
  "queue": {
    "pending": {
      "critical": 0,
      "high": 2,
      "normal": 5,
      "low": 10
    },
    "scheduled": 3,
    "processing": 1,
    "dead_letter": 0
  }
}
```

---

### Enqueue Job

#### POST /api/v1/jobs/enqueue
Enqueue a new background job.

**Authentication:** Required

**Request Body:**
```json
{
  "name": "sync_portfolio",
  "args": {
    "user_id": "user-123",
    "exchange": "binance"
  },
  "priority": "high",
  "max_retries": 3,
  "timeout": 300
}
```

**Response (200 OK):**
```json
{
  "job_id": "uuid",
  "status": "enqueued"
}
```

---

### Get Job Status

#### GET /api/v1/jobs/job/{job_id}
Get job details and status.

**Response (200 OK):**
```json
{
  "id": "uuid",
  "name": "sync_portfolio",
  "args": {
    "user_id": "user-123"
  },
  "status": "completed",
  "priority": "high",
  "created_at": "2025-12-16T09:50:00Z",
  "started_at": "2025-12-16T09:50:05Z",
  "completed_at": "2025-12-16T09:50:10Z",
  "result": {
    "synced": true,
    "positions_updated": 5
  },
  "retry_count": 0,
  "max_retries": 3
}
```

---

### Get Job Result

#### GET /api/v1/jobs/job/{job_id}/result
Get job execution result.

**Response (200 OK):**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "result": {
    "user_id": "user-123",
    "synced_at": "2025-12-16T09:50:10Z",
    "positions_updated": 5,
    "balances_updated": 3
  },
  "error": null
}
```

---

### Cancel Job

#### POST /api/v1/jobs/job/{job_id}/cancel
Cancel a pending job.

**Response (200 OK):**
```json
{
  "job_id": "uuid",
  "status": "cancelled"
}
```

---

### List Pending Jobs

#### GET /api/v1/jobs/pending
Get list of pending jobs.

**Query Parameters:**
- `priority` (optional): Filter by priority (low, normal, high, critical)
- `limit` (optional): Number of results (default: 100)

**Response (200 OK):**
```json
{
  "count": 17,
  "jobs": [
    {
      "id": "uuid",
      "name": "sync_portfolio",
      "status": "pending",
      "priority": "high",
      "created_at": "2025-12-16T10:00:00Z"
    }
  ]
}
```

---

### Get Job Statistics

#### GET /api/v1/jobs/stats
Get comprehensive job statistics.

**Response (200 OK):**
```json
{
  "running": true,
  "timestamp": "2025-12-16T10:00:00Z",
  "queue": {
    "total_pending": 17,
    "pending": {
      "critical": 0,
      "high": 2,
      "normal": 5,
      "low": 10
    },
    "scheduled": 3,
    "processing": 1,
    "dead_letter": 0
  },
  "scheduler": {
    "total_tasks": 6,
    "enabled_tasks": 5,
    "disabled_tasks": 1,
    "due_tasks": 0
  },
  "workers": {
    "worker_id": "main-worker",
    "status": "processing",
    "jobs_processed": 150,
    "jobs_succeeded": 145,
    "jobs_failed": 5,
    "success_rate": 96.67,
    "average_processing_time": 2.5
  }
}
```

---

### Scheduled Tasks Management

#### GET /api/v1/jobs/scheduled
List all scheduled tasks.

**Response (200 OK):**
```json
{
  "tasks": [
    {
      "name": "scheduled_portfolio_sync",
      "job_name": "sync_all_portfolios",
      "schedule_type": "interval",
      "enabled": true,
      "last_run": "2025-12-16T09:55:00Z",
      "next_run": "2025-12-16T10:00:00Z",
      "run_count": 120
    }
  ]
}
```

---

#### POST /api/v1/jobs/scheduled/register
Register a new scheduled task.

**Request Body:**
```json
{
  "name": "my_custom_task",
  "job_name": "sync_portfolio",
  "schedule_type": "interval",
  "interval_seconds": 300,
  "args": {
    "user_id": "user-123"
  },
  "priority": "normal",
  "enabled": true
}
```

**Response (200 OK):**
```json
{
  "name": "my_custom_task",
  "job_name": "sync_portfolio",
  "schedule_type": "interval",
  "next_run": "2025-12-16T10:05:00Z",
  "enabled": true
}
```

---

#### POST /api/v1/jobs/scheduled/{task_name}/run
Manually trigger a scheduled task.

**Response (200 OK):**
```json
{
  "task_name": "scheduled_portfolio_sync",
  "job_id": "uuid",
  "status": "triggered"
}
```

---

#### POST /api/v1/jobs/scheduled/{task_name}/enable
Enable a scheduled task.

#### POST /api/v1/jobs/scheduled/{task_name}/disable
Disable a scheduled task.

#### DELETE /api/v1/jobs/scheduled/{task_name}
Unregister a scheduled task.

---

### Dead Letter Queue Management

#### GET /api/v1/jobs/dlq
Get jobs from dead letter queue.

**Query Parameters:**
- `limit` (optional): Number of results (default: 100)

**Response (200 OK):**
```json
{
  "count": 5,
  "jobs": [
    {
      "id": "uuid",
      "name": "failed_job",
      "status": "failed",
      "error": "Connection timeout",
      "retry_count": 3,
      "max_retries": 3,
      "created_at": "2025-12-16T09:00:00Z",
      "completed_at": "2025-12-16T09:15:00Z"
    }
  ]
}
```

---

#### POST /api/v1/jobs/dlq/{job_id}/retry
Retry a job from dead letter queue.

**Response (200 OK):**
```json
{
  "job_id": "uuid",
  "status": "requeued"
}
```

---

#### DELETE /api/v1/jobs/dlq
Clear all jobs from dead letter queue.

**Response (200 OK):**
```json
{
  "cleared": 5
}
```

---

## Error Responses

All endpoints return standard error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters",
  "request_id": "uuid"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or missing authentication token",
  "request_id": "uuid"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found",
  "request_id": "uuid"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error",
  "request_id": "uuid"
}
```

---

## Rate Limiting

Phase 4 endpoints respect the following rate limits:

- **Risk Management:** 60 requests/minute
- **WebSocket:** Unlimited connections (per user)
- **Cache Management:** 120 requests/minute
- **Job Management:** 60 requests/minute

---

## Complete Endpoint Summary

### Phase 4 Endpoints (48 total)

**Risk Management (8 endpoints)**
- POST /api/v1/risk/limits
- GET /api/v1/risk/limits
- GET /api/v1/risk/limits/{id}
- PUT /api/v1/risk/limits/{id}
- DELETE /api/v1/risk/limits/{id}
- POST /api/v1/risk/evaluate
- GET /api/v1/risk/alerts
- POST /api/v1/risk/alerts/{id}/acknowledge

**WebSocket (5 endpoints)**
- WS /api/v1/ws
- GET /api/v1/websocket/connections
- GET /api/v1/websocket/stats
- POST /api/v1/websocket/broadcast
- DELETE /api/v1/websocket/connections/{id}

**Cache (8 endpoints)**
- GET /api/v1/cache/health
- GET /api/v1/cache/stats
- GET /api/v1/cache/market-data/{symbol}
- GET /api/v1/cache/price/{symbol}
- POST /api/v1/cache/price-alert
- GET /api/v1/cache/price-alerts
- DELETE /api/v1/cache/{type}
- POST /api/v1/cache/invalidate

**Jobs (27 endpoints)**
- GET /api/v1/jobs/health
- GET /api/v1/jobs/stats
- GET /api/v1/jobs/handlers
- POST /api/v1/jobs/enqueue
- GET /api/v1/jobs/job/{id}
- GET /api/v1/jobs/job/{id}/result
- POST /api/v1/jobs/job/{id}/cancel
- GET /api/v1/jobs/pending
- GET /api/v1/jobs/queue/stats
- GET /api/v1/jobs/workers/stats
- GET /api/v1/jobs/scheduler/stats
- GET /api/v1/jobs/scheduled
- POST /api/v1/jobs/scheduled/register
- DELETE /api/v1/jobs/scheduled/{name}
- POST /api/v1/jobs/scheduled/{name}/enable
- POST /api/v1/jobs/scheduled/{name}/disable
- POST /api/v1/jobs/scheduled/{name}/run
- GET /api/v1/jobs/dlq
- POST /api/v1/jobs/dlq/{id}/retry
- DELETE /api/v1/jobs/dlq

---

## Testing Examples

### Complete Phase 4 Workflow

```bash
# 1. Create risk limit
curl -X POST http://localhost:8000/api/v1/risk/limits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "limit_type": "position_size",
    "threshold_value": 10000.00
  }'

# 2. Connect to WebSocket
wscat -c "ws://localhost:8000/api/v1/ws?token=$TOKEN"

# 3. Subscribe to prices
{"action": "subscribe", "channel": "ticker", "symbols": ["BTCUSDT"]}

# 4. Check cache health
curl http://localhost:8000/api/v1/cache/health \
  -H "Authorization: Bearer $TOKEN"

# 5. Enqueue background job
curl -X POST http://localhost:8000/api/v1/jobs/enqueue \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sync_portfolio",
    "args": {"user_id": "user-123"},
    "priority": "high"
  }'

# 6. Check job status
curl http://localhost:8000/api/v1/jobs/job/{job_id} \
  -H "Authorization: Bearer $TOKEN"
```
