"""Scheduled job execution using cron-like scheduling."""

import asyncio
import logging
from typing import Optional, Dict, List, Callable, Awaitable, Any
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass, field
from enum import Enum
import re

from .job_queue import job_queue, JobPriority

logger = logging.getLogger(__name__)


class ScheduleType(str, Enum):
    """Schedule type."""
    INTERVAL = "interval"
    CRON = "cron"
    ONCE = "once"


@dataclass
class ScheduledTask:
    """Scheduled task definition."""
    name: str
    job_name: str
    schedule_type: ScheduleType
    args: Dict[str, Any] = field(default_factory=dict)
    priority: JobPriority = JobPriority.NORMAL
    enabled: bool = True
    
    # For interval scheduling
    interval_seconds: Optional[int] = None
    
    # For cron scheduling
    cron_expression: Optional[str] = None
    
    # For one-time scheduling
    run_at: Optional[datetime] = None
    
    # Runtime state
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    
    def calculate_next_run(self, from_time: datetime = None) -> Optional[datetime]:
        """Calculate next run time based on schedule."""
        base_time = from_time or datetime.utcnow()
        
        if self.schedule_type == ScheduleType.INTERVAL:
            if self.interval_seconds:
                if self.last_run:
                    return self.last_run + timedelta(seconds=self.interval_seconds)
                return base_time
            return None
            
        elif self.schedule_type == ScheduleType.CRON:
            if self.cron_expression:
                return self._parse_cron_next_run(base_time)
            return None
            
        elif self.schedule_type == ScheduleType.ONCE:
            if self.run_at and not self.last_run:
                return self.run_at
            return None
            
        return None
    
    def _parse_cron_next_run(self, from_time: datetime) -> Optional[datetime]:
        """Parse cron expression and calculate next run.
        
        Simplified cron format: minute hour day month weekday
        Supports: *, specific values, ranges (1-5), steps (*/5)
        """
        try:
            parts = self.cron_expression.split()
            if len(parts) != 5:
                logger.error(f"Invalid cron expression: {self.cron_expression}")
                return None
            
            minute, hour, day, month, weekday = parts
            
            # Start from next minute
            next_time = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
            
            # Try to find next matching time within 1 year
            max_iterations = 525600  # Minutes in a year
            for _ in range(max_iterations):
                if (self._matches_cron_field(minute, next_time.minute, 0, 59) and
                    self._matches_cron_field(hour, next_time.hour, 0, 23) and
                    self._matches_cron_field(day, next_time.day, 1, 31) and
                    self._matches_cron_field(month, next_time.month, 1, 12) and
                    self._matches_cron_field(weekday, next_time.weekday(), 0, 6)):
                    return next_time
                
                next_time += timedelta(minutes=1)
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing cron expression {self.cron_expression}: {e}")
            return None
    
    def _matches_cron_field(self, pattern: str, value: int, min_val: int, max_val: int) -> bool:
        """Check if value matches cron field pattern."""
        if pattern == "*":
            return True
        
        # Handle step values (*/5)
        if pattern.startswith("*/"):
            try:
                step = int(pattern[2:])
                return value % step == 0
            except ValueError:
                return False
        
        # Handle ranges (1-5)
        if "-" in pattern:
            try:
                start, end = pattern.split("-")
                return int(start) <= value <= int(end)
            except ValueError:
                return False
        
        # Handle comma-separated values (1,3,5)
        if "," in pattern:
            try:
                values = [int(v.strip()) for v in pattern.split(",")]
                return value in values
            except ValueError:
                return False
        
        # Handle single value
        try:
            return int(pattern) == value
        except ValueError:
            return False


class JobScheduler:
    """Scheduler for periodic and scheduled job execution."""
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._check_interval = 30  # Check every 30 seconds
    
    def register(
        self,
        name: str,
        job_name: str,
        schedule_type: ScheduleType = ScheduleType.INTERVAL,
        args: Dict[str, Any] = None,
        priority: JobPriority = JobPriority.NORMAL,
        interval_seconds: int = None,
        cron_expression: str = None,
        run_at: datetime = None,
        enabled: bool = True,
    ) -> ScheduledTask:
        """Register a scheduled task."""
        task = ScheduledTask(
            name=name,
            job_name=job_name,
            schedule_type=schedule_type,
            args=args or {},
            priority=priority,
            interval_seconds=interval_seconds,
            cron_expression=cron_expression,
            run_at=run_at,
            enabled=enabled,
        )
        
        # Calculate initial next run
        task.next_run = task.calculate_next_run()
        
        self.tasks[name] = task
        logger.info(f"Registered scheduled task: {name} (next run: {task.next_run})")
        
        return task
    
    def unregister(self, name: str) -> bool:
        """Unregister a scheduled task."""
        if name in self.tasks:
            del self.tasks[name]
            logger.info(f"Unregistered scheduled task: {name}")
            return True
        return False
    
    def enable(self, name: str) -> bool:
        """Enable a scheduled task."""
        if name in self.tasks:
            self.tasks[name].enabled = True
            self.tasks[name].next_run = self.tasks[name].calculate_next_run()
            logger.info(f"Enabled scheduled task: {name}")
            return True
        return False
    
    def disable(self, name: str) -> bool:
        """Disable a scheduled task."""
        if name in self.tasks:
            self.tasks[name].enabled = False
            logger.info(f"Disabled scheduled task: {name}")
            return True
        return False
    
    def get_task(self, name: str) -> Optional[ScheduledTask]:
        """Get scheduled task by name."""
        return self.tasks.get(name)
    
    def get_all_tasks(self) -> List[ScheduledTask]:
        """Get all scheduled tasks."""
        return list(self.tasks.values())
    
    async def start(self):
        """Start the scheduler."""
        if self._running:
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Job scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None
        
        logger.info("Job scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_and_enqueue_tasks()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self._check_interval)
    
    async def _check_and_enqueue_tasks(self):
        """Check scheduled tasks and enqueue if ready."""
        now = datetime.utcnow()
        
        for task in self.tasks.values():
            if not task.enabled:
                continue
            
            if task.next_run and task.next_run <= now:
                try:
                    # Enqueue the job
                    job_id = await job_queue.enqueue(
                        name=task.job_name,
                        args=task.args,
                        priority=task.priority,
                    )
                    
                    # Update task state
                    task.last_run = now
                    task.run_count += 1
                    task.next_run = task.calculate_next_run(now)
                    
                    logger.info(
                        f"Scheduled task {task.name} enqueued as job {job_id} "
                        f"(run #{task.run_count}, next: {task.next_run})"
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to enqueue scheduled task {task.name}: {e}")
    
    async def run_task_now(self, name: str) -> Optional[str]:
        """Manually trigger a scheduled task to run now."""
        task = self.tasks.get(name)
        if not task:
            return None
        
        try:
            job_id = await job_queue.enqueue(
                name=task.job_name,
                args=task.args,
                priority=task.priority,
            )
            
            logger.info(f"Manually triggered scheduled task {name} as job {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to manually trigger task {name}: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        now = datetime.now(UTC)
        
        enabled_tasks = [t for t in self.tasks.values() if t.enabled]
        due_tasks = [t for t in enabled_tasks if t.next_run and t.next_run <= now]
        
        return {
            "running": self._running,
            "check_interval": self._check_interval,
            "total_tasks": len(self.tasks),
            "enabled_tasks": len(enabled_tasks),
            "disabled_tasks": len(self.tasks) - len(enabled_tasks),
            "due_tasks": len(due_tasks),
            "tasks": [
                {
                    "name": t.name,
                    "job_name": t.job_name,
                    "schedule_type": t.schedule_type.value,
                    "enabled": t.enabled,
                    "last_run": t.last_run.isoformat() if t.last_run else None,
                    "next_run": t.next_run.isoformat() if t.next_run else None,
                    "run_count": t.run_count,
                }
                for t in self.tasks.values()
            ],
        }


# Global scheduler instance
job_scheduler = JobScheduler()


# Decorator for registering scheduled tasks
def scheduled(
    name: str = None,
    schedule_type: ScheduleType = ScheduleType.INTERVAL,
    interval_seconds: int = None,
    cron_expression: str = None,
    priority: JobPriority = JobPriority.NORMAL,
    enabled: bool = True,
):
    """Decorator to register a function as a scheduled task."""
    def decorator(func: Callable[..., Awaitable[Any]]):
        task_name = name or func.__name__
        job_name = func.__name__
        
        job_scheduler.register(
            name=task_name,
            job_name=job_name,
            schedule_type=schedule_type,
            interval_seconds=interval_seconds,
            cron_expression=cron_expression,
            priority=priority,
            enabled=enabled,
        )
        
        return func
    return decorator


# Convenience functions for common schedules
def every_seconds(seconds: int, name: str = None, priority: JobPriority = JobPriority.NORMAL):
    """Register task to run every N seconds."""
    return scheduled(
        name=name,
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=seconds,
        priority=priority,
    )


def every_minutes(minutes: int, name: str = None, priority: JobPriority = JobPriority.NORMAL):
    """Register task to run every N minutes."""
    return scheduled(
        name=name,
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=minutes * 60,
        priority=priority,
    )


def every_hours(hours: int, name: str = None, priority: JobPriority = JobPriority.NORMAL):
    """Register task to run every N hours."""
    return scheduled(
        name=name,
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=hours * 3600,
        priority=priority,
    )


def daily_at(hour: int, minute: int = 0, name: str = None, priority: JobPriority = JobPriority.NORMAL):
    """Register task to run daily at specific time."""
    return scheduled(
        name=name,
        schedule_type=ScheduleType.CRON,
        cron_expression=f"{minute} {hour} * * *",
        priority=priority,
    )


def cron(expression: str, name: str = None, priority: JobPriority = JobPriority.NORMAL):
    """Register task with cron expression."""
    return scheduled(
        name=name,
        schedule_type=ScheduleType.CRON,
        cron_expression=expression,
        priority=priority,
    )
