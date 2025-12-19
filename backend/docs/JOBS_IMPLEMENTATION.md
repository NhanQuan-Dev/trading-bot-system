# Background Job Processing Implementation

## Overview

This document describes the background job processing infrastructure for the trading platform. The system provides reliable, scalable job execution with features including:

- **Redis-based job queue** with priority support
- **Scheduled tasks** with interval and cron-like scheduling
- **Worker pool** for parallel job processing
- **Dead letter queue** for failed job handling
- **Comprehensive monitoring** and statistics

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Job Service                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Job Queue     │  │  Job Scheduler  │  │   Job Worker    │ │
│  │                 │  │                 │  │                 │ │
│  │ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │ │
│  │ │  Critical   │ │  │ │  Interval   │ │  │ │   Handler   │ │ │
│  │ ├─────────────┤ │  │ │   Tasks     │ │  │ │  Registry   │ │ │
│  │ │    High     │ │  │ ├─────────────┤ │  │ ├─────────────┤ │ │
│  │ ├─────────────┤ │  │ │    Cron     │ │  │ │   Process   │ │ │
│  │ │   Normal    │ │  │ │   Tasks     │ │  │ │    Jobs     │ │ │
│  │ ├─────────────┤ │  │ ├─────────────┤ │  │ ├─────────────┤ │ │
│  │ │    Low      │ │  │ │  One-time   │ │  │ │   Stats     │ │ │
│  │ └─────────────┘ │  │ │   Tasks     │ │  │ │  Tracking   │ │ │
│  │                 │  │ └─────────────┘ │  │ └─────────────┘ │ │
│  │ ┌─────────────┐ │  │                 │  │                 │ │
│  │ │   DLQ       │ │  │                 │  │                 │ │
│  │ └─────────────┘ │  │                 │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │      Redis      │
                    └─────────────────┘
```

## Components

### 1. Job Queue (`job_queue.py`)

Redis-based job queue with priority levels and scheduling support.

#### Job Structure

```python
@dataclass
class Job:
    id: str                    # UUID
    name: str                  # Handler name
    args: Dict[str, Any]       # Arguments
    status: JobStatus          # pending/running/completed/failed/cancelled/retrying
    priority: JobPriority      # low/normal/high/critical
    created_at: str
    scheduled_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]
    result: Optional[Any]
    retry_count: int
    max_retries: int
    timeout: int
    user_id: Optional[str]
```

#### Priority Queues

Jobs are processed in priority order:
1. **Critical** - Immediate execution required
2. **High** - Important operations
3. **Normal** - Standard operations
4. **Low** - Background/batch operations

#### Usage

```python
from trading.infrastructure.jobs import job_queue, JobPriority

# Enqueue immediate job
job_id = await job_queue.enqueue(
    name="sync_portfolio",
    args={"user_id": "user-123"},
    priority=JobPriority.HIGH,
)

# Enqueue scheduled job
from datetime import datetime, timedelta
job_id = await job_queue.enqueue(
    name="send_report",
    scheduled_at=datetime.utcnow() + timedelta(hours=1),
)

# Get job status
job = await job_queue.get_job(job_id)
print(f"Status: {job.status}")

# Cancel pending job
await job_queue.cancel_job(job_id)
```

### 2. Job Scheduler (`job_scheduler.py`)

Scheduler for periodic and scheduled job execution.

#### Schedule Types

- **Interval**: Run every N seconds
- **Cron**: Cron-like expression (minute hour day month weekday)
- **Once**: Run at specific time

#### Registration

```python
from trading.infrastructure.jobs import job_scheduler, ScheduleType, JobPriority

# Interval-based task
job_scheduler.register(
    name="portfolio_sync",
    job_name="sync_all_portfolios",
    schedule_type=ScheduleType.INTERVAL,
    interval_seconds=300,  # Every 5 minutes
    priority=JobPriority.NORMAL,
)

# Cron-based task
job_scheduler.register(
    name="daily_report",
    job_name="send_daily_summary_emails",
    schedule_type=ScheduleType.CRON,
    cron_expression="0 8 * * *",  # 8 AM daily
    priority=JobPriority.NORMAL,
)

# Decorator syntax
from trading.infrastructure.jobs import every_minutes, daily_at

@every_minutes(5)
async def sync_data(args):
    pass

@daily_at(8, 0)
async def morning_report(args):
    pass
```

#### Cron Expression Format

```
* * * * *
│ │ │ │ │
│ │ │ │ └── Day of week (0-6, 0=Sunday)
│ │ │ └──── Month (1-12)
│ │ └────── Day of month (1-31)
│ └──────── Hour (0-23)
└────────── Minute (0-59)

Supported patterns:
- * : Any value
- N : Specific value
- N-M : Range
- */N : Every N
- N,M,O : List
```

### 3. Job Worker (`job_worker.py`)

Background worker that processes jobs from the queue.

#### Handler Registration

```python
from trading.infrastructure.jobs import job_handler

@job_handler("sync_portfolio")
async def sync_portfolio_task(args: Dict[str, Any]) -> Dict[str, Any]:
    user_id = args.get("user_id")
    # Do work...
    return {"status": "completed", "user_id": user_id}
```

#### Worker Configuration

```python
from trading.infrastructure.jobs import JobWorker, WorkerPool

# Single worker
worker = JobWorker(
    worker_id="worker-1",
    poll_interval=1.0,
    max_concurrent_jobs=1,
)
await worker.start()

# Worker pool
pool = WorkerPool(
    num_workers=3,
    max_concurrent_per_worker=1,
)
await pool.start()
```

### 4. Job Service (`job_service.py`)

Centralized service managing all job components.

```python
from trading.infrastructure.jobs import job_service

# Start all services
await job_service.start()

# Enqueue job
job_id = await job_service.enqueue(
    name="sync_portfolio",
    args={"user_id": "123"},
)

# Get stats
stats = await job_service.get_full_stats()

# Stop all services
await job_service.stop()
```

## Pre-defined Tasks

### Portfolio Tasks
- `sync_portfolio` - Sync portfolio for single user
- `sync_all_portfolios` - Batch sync for all users

### Risk Tasks
- `monitor_risk` - Monitor risk for user/all
- `evaluate_risk_limits` - Evaluate all risk limits

### Cleanup Tasks
- `cleanup_data` - Clean old data (trades, logs, cache)
- `vacuum_database` - Database optimization

### Price Alert Tasks
- `check_price_alerts` - Check and trigger price alerts
- `send_price_notification` - Send alert notification

### Bot Tasks
- `bot_health_check` - Check bot health
- `restart_unhealthy_bots` - Auto-restart unhealthy bots

### Market Data Tasks
- `fetch_market_data` - Fetch and cache market data
- `update_24h_stats` - Update 24h statistics

### Report Tasks
- `generate_daily_report` - Generate daily trading report
- `send_daily_summary_emails` - Send summary emails

## API Endpoints

### Health & Stats
```
GET  /api/v1/jobs/health          # Service health
GET  /api/v1/jobs/stats           # Full statistics
GET  /api/v1/jobs/queue/stats     # Queue stats
GET  /api/v1/jobs/workers/stats   # Worker stats
GET  /api/v1/jobs/scheduler/stats # Scheduler stats
GET  /api/v1/jobs/handlers        # Registered handlers
```

### Job Management
```
POST /api/v1/jobs/enqueue         # Enqueue new job
GET  /api/v1/jobs/job/{job_id}    # Get job details
GET  /api/v1/jobs/job/{job_id}/result  # Get job result
POST /api/v1/jobs/job/{job_id}/cancel  # Cancel job
GET  /api/v1/jobs/pending         # List pending jobs
```

### Dead Letter Queue
```
GET  /api/v1/jobs/dlq             # List DLQ jobs
POST /api/v1/jobs/dlq/{job_id}/retry  # Retry DLQ job
DELETE /api/v1/jobs/dlq           # Clear DLQ
```

### Scheduled Tasks
```
GET  /api/v1/jobs/scheduled       # List tasks
POST /api/v1/jobs/scheduled/register  # Register task
DELETE /api/v1/jobs/scheduled/{name}  # Unregister
POST /api/v1/jobs/scheduled/{name}/enable  # Enable
POST /api/v1/jobs/scheduled/{name}/disable # Disable
POST /api/v1/jobs/scheduled/{name}/run     # Run now
```

## Default Scheduled Tasks

| Task | Job | Schedule | Priority |
|------|-----|----------|----------|
| Portfolio Sync | sync_all_portfolios | Every 5 min | Normal |
| Risk Monitoring | evaluate_risk_limits | Every 1 min | High |
| Bot Health Check | bot_health_check | Every 2 min | High |
| Data Cleanup | cleanup_data | Daily 3 AM | Low |
| Database Vacuum | vacuum_database | Weekly Sun 4 AM | Low |
| Daily Summary | send_daily_summary_emails | Daily 8 AM | Normal |

## Error Handling

### Retry Logic

Jobs that fail are automatically retried with exponential backoff:
- Retry 1: 2 minutes
- Retry 2: 4 minutes
- Retry 3: 8 minutes
- Max delay: 1 hour

### Dead Letter Queue

Jobs that exceed max retries are moved to the Dead Letter Queue (DLQ) for manual review:

```python
# Get DLQ jobs
failed_jobs = await job_queue.get_dead_letter_jobs(limit=100)

# Retry a specific job
await job_queue.retry_dead_letter_job(job_id)

# Clear entire DLQ
await job_queue.clear_dead_letter_queue()
```

## Configuration

```python
# In job_service.py
job_service = JobService(
    use_worker_pool=False,    # Use single worker (True for pool)
    num_workers=3,            # Workers in pool
    enable_scheduler=True,    # Enable scheduled tasks
)
```

## Monitoring

### Queue Statistics
```json
{
  "pending": {
    "critical": 0,
    "high": 2,
    "normal": 5,
    "low": 10
  },
  "scheduled": 3,
  "processing": 1,
  "dead_letter": 0,
  "total_pending": 17
}
```

### Worker Statistics
```json
{
  "worker_id": "main-worker",
  "status": "processing",
  "jobs_processed": 150,
  "jobs_succeeded": 145,
  "jobs_failed": 5,
  "success_rate": 96.67,
  "average_processing_time": 2.5
}
```

### Scheduler Statistics
```json
{
  "running": true,
  "total_tasks": 6,
  "enabled_tasks": 5,
  "disabled_tasks": 1,
  "due_tasks": 0,
  "tasks": [...]
}
```

## Best Practices

1. **Job Handlers**: Keep handlers focused and idempotent
2. **Timeouts**: Set appropriate timeouts for each job type
3. **Retries**: Use sensible max_retries based on job criticality
4. **Priority**: Reserve HIGH/CRITICAL for truly urgent tasks
5. **Scheduling**: Stagger scheduled tasks to avoid spikes
6. **Monitoring**: Regular review of DLQ and failed jobs
7. **Cleanup**: Implement data retention policies

## File Structure

```
backend/src/trading/infrastructure/jobs/
├── __init__.py           # Module exports
├── job_queue.py          # Redis-based job queue
├── job_scheduler.py      # Scheduled task management
├── job_worker.py         # Background worker
├── job_service.py        # Centralized service
└── tasks.py              # Pre-defined task handlers
```
