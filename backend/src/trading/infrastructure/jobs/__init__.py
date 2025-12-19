"""Background job processing infrastructure."""

from .job_queue import (
    JobQueue,
    job_queue,
    Job,
    JobStatus,
    JobPriority,
)
from .job_scheduler import (
    JobScheduler,
    job_scheduler,
    ScheduledTask,
    ScheduleType,
    scheduled,
    every_seconds,
    every_minutes,
    every_hours,
    daily_at,
    cron,
)
from .job_worker import (
    JobWorker,
    job_worker,
    WorkerPool,
    worker_pool,
    WorkerStatus,
    job_handler,
)
from .job_service import JobService, job_service
from .tasks import (
    sync_portfolio_task,
    sync_all_portfolios_task,
    monitor_risk_task,
    evaluate_risk_limits_task,
    cleanup_data_task,
    vacuum_database_task,
    check_price_alerts_task,
    send_price_notification_task,
    bot_health_check_task,
    restart_unhealthy_bots_task,
    fetch_market_data_task,
    update_24h_stats_task,
    generate_daily_report_task,
    send_daily_summary_emails_task,
    register_default_scheduled_tasks,
)

__all__ = [
    # Job Queue
    "JobQueue",
    "job_queue",
    "Job",
    "JobStatus",
    "JobPriority",
    # Scheduler
    "JobScheduler",
    "job_scheduler",
    "ScheduledTask",
    "ScheduleType",
    "scheduled",
    "every_seconds",
    "every_minutes",
    "every_hours",
    "daily_at",
    "cron",
    # Worker
    "JobWorker",
    "job_worker",
    "WorkerPool",
    "worker_pool",
    "WorkerStatus",
    "job_handler",
    # Service
    "JobService",
    "job_service",
    # Tasks
    "sync_portfolio_task",
    "sync_all_portfolios_task",
    "monitor_risk_task",
    "evaluate_risk_limits_task",
    "cleanup_data_task",
    "vacuum_database_task",
    "check_price_alerts_task",
    "send_price_notification_task",
    "bot_health_check_task",
    "restart_unhealthy_bots_task",
    "fetch_market_data_task",
    "update_24h_stats_task",
    "generate_daily_report_task",
    "send_daily_summary_emails_task",
    "register_default_scheduled_tasks",
]
