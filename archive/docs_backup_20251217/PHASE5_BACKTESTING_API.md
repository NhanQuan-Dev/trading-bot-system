"""
# Phase 5: Backtesting & Performance Analytics API

Complete API documentation for backtesting functionality.

## Table of Contents
1. [Overview](#overview)
2. [Backtesting Endpoints](#backtesting-endpoints)
3. [Request/Response Schemas](#requestresponse-schemas)
4. [Usage Examples](#usage-examples)
5. [Performance Metrics](#performance-metrics)

---

## Overview

The backtesting system allows users to test trading strategies against historical data with realistic market simulation including:
- Event-driven candle-by-candle processing
- Slippage and commission modeling
- Comprehensive performance metrics
- Real-time progress tracking
- Detailed trade-by-trade analysis

**Base URL**: `/api/v1/backtests`

---

## Backtesting Endpoints

### 1. Run Backtest

Start a new backtest execution.

**Endpoint**: `POST /api/v1/backtests`  
**Status**: `202 Accepted`

**Request Body**:
```json
{
  "strategy_id": "uuid",
  "config": {
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_capital": 10000.0,
    "position_sizing": "FIXED_PERCENT",
    "position_size_percent": 100.0,
    "max_position_size": null,
    "slippage_model": "PERCENTAGE",
    "slippage_percent": 0.1,
    "commission_model": "PERCENTAGE",
    "commission_rate": 0.1,
    "mode": "NORMAL"
  },
  "strategy_code": null
}
```

**Response**:
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "strategy_id": "uuid",
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 10000.0,
  "status": "PENDING",
  "progress_percent": 0,
  "start_time": null,
  "end_time": null,
  "error_message": null,
  "final_equity": null,
  "total_trades": null,
  "win_rate": null,
  "total_return": null,
  "created_at": "2024-12-16T10:30:00Z"
}
```

---

### 2. Get Backtest Details

Retrieve backtest run information.

**Endpoint**: `GET /api/v1/backtests/{backtest_id}`  
**Status**: `200 OK`

**Response**:
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "strategy_id": "uuid",
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 10000.0,
  "status": "COMPLETED",
  "progress_percent": 100,
  "start_time": "2024-12-16T10:30:00Z",
  "end_time": "2024-12-16T10:35:00Z",
  "error_message": null,
  "final_equity": 12450.50,
  "total_trades": 45,
  "win_rate": 62.5,
  "total_return": 24.51,
  "created_at": "2024-12-16T10:30:00Z"
}
```

---

### 3. List Backtests

List backtests with optional filters.

**Endpoint**: `GET /api/v1/backtests`  
**Query Parameters**:
- `strategy_id` (optional): Filter by strategy UUID
- `symbol` (optional): Filter by trading symbol
- `limit` (optional, default=50): Maximum results (1-100)
- `offset` (optional, default=0): Pagination offset

**Status**: `200 OK`

**Response**:
```json
{
  "backtests": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "strategy_id": "uuid",
      "symbol": "BTCUSDT",
      "timeframe": "1h",
      "status": "COMPLETED",
      "total_return": 24.51,
      "created_at": "2024-12-16T10:30:00Z"
    }
  ],
  "total": 15,
  "limit": 50,
  "offset": 0
}
```

---

### 4. Get Backtest Results

Retrieve detailed backtest results with full performance metrics.

**Endpoint**: `GET /api/v1/backtests/{backtest_id}/results`  
**Status**: `200 OK`

**Response**:
```json
{
  "backtest_run": { /* BacktestRunResponse */ },
  "initial_capital": 10000.0,
  "final_equity": 12450.50,
  "peak_equity": 13200.00,
  "total_trades": 45,
  "performance_metrics": {
    "total_return": 24.51,
    "annual_return": 25.32,
    "compound_annual_growth_rate": 24.89,
    "sharpe_ratio": 1.85,
    "sortino_ratio": 2.34,
    "calmar_ratio": 1.45,
    "max_drawdown": -15.23,
    "max_drawdown_duration_days": 45,
    "volatility": 12.45,
    "downside_deviation": 8.34,
    "win_rate": 62.5,
    "profit_factor": 2.15,
    "payoff_ratio": 1.85,
    "expected_value": 54.50,
    "total_trades": 45,
    "winning_trades": 28,
    "losing_trades": 17,
    "break_even_trades": 0,
    "average_trade_pnl": 54.50,
    "average_winning_trade": 125.30,
    "average_losing_trade": -67.80,
    "largest_winning_trade": 450.00,
    "largest_losing_trade": -230.00,
    "max_consecutive_wins": 8,
    "max_consecutive_losses": 4,
    "average_exposure_percent": 85.5,
    "max_simultaneous_positions": 1,
    "risk_of_ruin": 2.5
  },
  "equity_curve": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "equity": 10000.0,
      "drawdown_percent": 0.0,
      "return_percent": 0.0
    },
    {
      "timestamp": "2024-01-01T01:00:00Z",
      "equity": 10125.50,
      "drawdown_percent": 0.0,
      "return_percent": 1.26
    }
  ],
  "trades": [
    {
      "symbol": "BTCUSDT",
      "direction": "LONG",
      "entry_price": 42500.00,
      "exit_price": 43200.00,
      "quantity": 0.25,
      "entry_time": "2024-01-01T10:00:00Z",
      "exit_time": "2024-01-01T14:00:00Z",
      "duration_seconds": 14400,
      "gross_pnl": 175.00,
      "commission": 21.35,
      "slippage": 4.25,
      "net_pnl": 149.40,
      "pnl_percent": 1.65,
      "mae": -25.50,
      "mfe": 210.00,
      "is_winner": true
    }
  ]
}
```

---

### 5. Get Backtest Status

Check execution status and progress.

**Endpoint**: `GET /api/v1/backtests/{backtest_id}/status`  
**Status**: `200 OK`

**Response**:
```json
{
  "id": "uuid",
  "status": "RUNNING",
  "progress_percent": 65,
  "message": null
}
```

**Status Values**:
- `PENDING`: Queued for execution
- `RUNNING`: Currently executing
- `COMPLETED`: Successfully finished
- `FAILED`: Execution failed
- `CANCELLED`: User cancelled

---

### 6. Cancel Backtest

Cancel a running backtest.

**Endpoint**: `POST /api/v1/backtests/{backtest_id}/cancel`  
**Status**: `200 OK`

**Response**:
```json
{
  "id": "uuid",
  "status": "CANCELLED",
  "progress_percent": 45,
  "message": "Backtest cancelled"
}
```

---

### 7. Delete Backtest

Delete a backtest and its results.

**Endpoint**: `DELETE /api/v1/backtests/{backtest_id}`  
**Status**: `204 No Content`

**Note**: Cannot delete running backtests. Cancel first, then delete.

---

## Request/Response Schemas

### Backtest Configuration

```python
{
  "symbol": str,                      # Trading pair
  "timeframe": str,                   # "1m", "5m", "15m", "1h", "4h", "1d"
  "start_date": date,                 # YYYY-MM-DD
  "end_date": date,                   # YYYY-MM-DD
  "initial_capital": Decimal,         # > 0
  
  # Position Sizing
  "position_sizing": str,             # "FIXED_PERCENT", "FIXED_AMOUNT", "RISK_BASED", "KELLY"
  "position_size_percent": Decimal,   # Percent of capital to use (0-100)
  "max_position_size": Decimal,       # Optional maximum position size
  
  # Cost Models
  "slippage_model": str,              # "NONE", "FIXED", "PERCENTAGE", "VOLUME_BASED", "RANDOM"
  "slippage_percent": Decimal,        # Slippage percentage
  "commission_model": str,            # "NONE", "FIXED", "PERCENTAGE", "TIERED"
  "commission_rate": Decimal,         # Commission rate
  
  # Execution Mode
  "mode": str                         # "NORMAL", "FAST", "MONTE_CARLO"
}
```

### Performance Metrics

All performance metrics include:
- **Returns**: Total, Annual, CAGR
- **Risk Ratios**: Sharpe, Sortino, Calmar
- **Drawdown**: Maximum drawdown amount and duration
- **Volatility**: Standard deviation and downside deviation
- **Trade Statistics**: Win rate, profit factor, payoff ratio
- **Trade Distribution**: Average, largest, consecutive wins/losses
- **Exposure**: Time in market percentage
- **Risk**: Risk of ruin calculation

---

## Usage Examples

### Example 1: Simple Backtest

```python
import httpx

# Start backtest
response = httpx.post(
    "http://localhost:8000/api/v1/backtests",
    json={
        "strategy_id": "550e8400-e29b-41d4-a716-446655440000",
        "config": {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 10000.0,
            "position_size_percent": 100.0,
            "slippage_percent": 0.1,
            "commission_rate": 0.1
        }
    }
)
backtest = response.json()
backtest_id = backtest["id"]

# Poll for completion
while True:
    status = httpx.get(f"http://localhost:8000/api/v1/backtests/{backtest_id}/status").json()
    print(f"Progress: {status['progress_percent']}%")
    
    if status["status"] == "COMPLETED":
        break
    elif status["status"] == "FAILED":
        print(f"Failed: {status['message']}")
        break
    
    time.sleep(2)

# Get results
results = httpx.get(f"http://localhost:8000/api/v1/backtests/{backtest_id}/results").json()
print(f"Total Return: {results['performance_metrics']['total_return']}%")
print(f"Sharpe Ratio: {results['performance_metrics']['sharpe_ratio']}")
print(f"Win Rate: {results['performance_metrics']['win_rate']}%")
```

### Example 2: List and Compare Backtests

```python
# Get all backtests for a strategy
response = httpx.get(
    "http://localhost:8000/api/v1/backtests",
    params={"strategy_id": "550e8400-e29b-41d4-a716-446655440000"}
)
backtests = response.json()["backtests"]

# Compare performance
for backtest in backtests:
    print(f"{backtest['symbol']}: {backtest['total_return']}% return")
```

### Example 3: Advanced Configuration

```python
# Backtest with custom slippage and commission models
response = httpx.post(
    "http://localhost:8000/api/v1/backtests",
    json={
        "strategy_id": "550e8400-e29b-41d4-a716-446655440000",
        "config": {
            "symbol": "ETHUSDT",
            "timeframe": "4h",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 50000.0,
            "position_sizing": "RISK_BASED",
            "position_size_percent": 2.0,  # Risk 2% per trade
            "slippage_model": "VOLUME_BASED",
            "slippage_percent": 0.15,
            "commission_model": "TIERED",
            "commission_rate": 0.1,
            "mode": "NORMAL"
        }
    }
)
```

---

## Performance Metrics

### Risk-Adjusted Returns

**Sharpe Ratio**: Measures risk-adjusted return using total volatility
- Formula: `(Annual Return - Risk Free Rate) / Volatility`
- Good: > 1.0, Excellent: > 2.0

**Sortino Ratio**: Measures risk-adjusted return using downside volatility
- Formula: `(Annual Return - Risk Free Rate) / Downside Deviation`
- Better than Sharpe for asymmetric returns

**Calmar Ratio**: Return relative to maximum drawdown
- Formula: `Annual Return / Max Drawdown`
- Good: > 1.0

### Drawdown Analysis

**Maximum Drawdown**: Largest peak-to-trough decline
**Drawdown Duration**: Days from peak to recovery
**Current Drawdown**: Current distance from peak equity

### Trade Statistics

**Win Rate**: Percentage of winning trades
**Profit Factor**: Gross profit / Gross loss
**Payoff Ratio**: Average win / Average loss
**Expected Value**: Expected P&L per trade

### Additional Metrics

**MAE (Maximum Adverse Excursion)**: Largest unrealized loss during trade
**MFE (Maximum Favorable Excursion)**: Largest unrealized profit during trade
**Risk of Ruin**: Probability of losing all capital

---

## Error Handling

All endpoints return standard error responses:

```json
{
  "detail": "Error description",
  "request_id": "uuid"
}
```

**Common HTTP Status Codes**:
- `200`: Success
- `202`: Accepted (background task started)
- `204`: No Content (successful deletion)
- `400`: Bad Request (invalid parameters)
- `403`: Forbidden (not authorized)
- `404`: Not Found (backtest doesn't exist)
- `500`: Internal Server Error

---

## Database Schema

### backtest_runs Table

Tracks backtest execution state and progress.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Owner user ID |
| strategy_id | UUID | Strategy being tested |
| symbol | VARCHAR(20) | Trading symbol |
| timeframe | VARCHAR(10) | Candlestick timeframe |
| start_date | DATE | Test start date |
| end_date | DATE | Test end date |
| initial_capital | DECIMAL(20,8) | Starting capital |
| config | JSONB | Full configuration |
| status | VARCHAR(20) | Execution status |
| progress_percent | INTEGER | Progress (0-100) |
| start_time | TIMESTAMP | Execution start |
| end_time | TIMESTAMP | Execution end |
| error_message | TEXT | Error details |
| final_equity | DECIMAL(20,8) | Final balance |
| total_trades | INTEGER | Trade count |
| win_rate | DECIMAL(5,2) | Win percentage |
| total_return | DECIMAL(10,4) | Return percentage |

### backtest_results Table

Detailed performance metrics and analysis.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| backtest_run_id | UUID | Link to run |
| initial_capital | DECIMAL(20,8) | Starting capital |
| final_equity | DECIMAL(20,8) | Ending equity |
| peak_equity | DECIMAL(20,8) | Highest equity |
| total_trades | INTEGER | Total trades |
| winning_trades | INTEGER | Winning count |
| losing_trades | INTEGER | Losing count |
| sharpe_ratio | DECIMAL(10,4) | Risk-adjusted return |
| sortino_ratio | DECIMAL(10,4) | Downside risk metric |
| max_drawdown | DECIMAL(10,4) | Maximum drawdown |
| win_rate | DECIMAL(5,2) | Win percentage |
| profit_factor | DECIMAL(10,4) | Profit/loss ratio |
| equity_curve | JSONB | Time series data |
| trades | JSONB | Trade details |

### backtest_trades Table

Individual trade records.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| result_id | UUID | Link to result |
| symbol | VARCHAR(20) | Trading symbol |
| direction | VARCHAR(10) | LONG/SHORT |
| entry_price | DECIMAL(20,8) | Entry price |
| exit_price | DECIMAL(20,8) | Exit price |
| quantity | DECIMAL(20,8) | Position size |
| entry_time | TIMESTAMP | Trade open time |
| exit_time | TIMESTAMP | Trade close time |
| gross_pnl | DECIMAL(20,8) | Gross P&L |
| commission | DECIMAL(20,8) | Total commission |
| slippage | DECIMAL(20,8) | Slippage cost |
| net_pnl | DECIMAL(20,8) | Net P&L |
| pnl_percent | DECIMAL(10,4) | Return percentage |
| mae | DECIMAL(20,8) | Max adverse excursion |
| mfe | DECIMAL(20,8) | Max favorable excursion |

---

## Implementation Notes

### Background Execution

Backtests run in background tasks using FastAPI's BackgroundTasks. The endpoint returns immediately with a 202 status, and clients can poll the status endpoint for updates.

### Progress Tracking

Progress is updated every 100 candles processed. The engine calls a progress callback that updates the database.

### Strategy Functions

Strategy functions receive:
- `candle`: Current OHLCV data
- `idx`: Candle index
- `position`: Current open position (or None)

And return signals:
- `{"type": "buy", "stop_loss": 42000, "take_profit": 45000}`
- `{"type": "sell", "stop_loss": 43000, "take_profit": 41000}`
- `{"type": "close"}`
- `None` (no action)

### Performance Optimization

- Equity curve is sampled (not every candle stored)
- Metrics calculated once at completion
- Background job processing prevents blocking
- Database indexes on frequently queried fields

---

**Last Updated**: December 16, 2024  
**API Version**: 1.0.0  
**Phase**: 5 - Backtesting & Performance Analytics
"""
