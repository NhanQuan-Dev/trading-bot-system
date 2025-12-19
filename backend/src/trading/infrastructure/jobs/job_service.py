"""Centralized job management service."""

import asyncio
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, UTC

from .job_queue import job_queue, JobPriority, JobStatus, Job
from .job_scheduler import job_scheduler, ScheduleType
from .job_worker import job_worker, worker_pool, JobWorker

logger = logging.getLogger(__name__)


class JobService:
    """Centralized service for job queue, scheduler, and workers."""
    
    def __init__(
        self,
        use_worker_pool: bool = False,
        num_workers: int = 3,
        enable_scheduler: bool = True,
    ):
        self.use_worker_pool = use_worker_pool
        self.num_workers = num_workers
        self.enable_scheduler = enable_scheduler
        self._running = False
    
    async def start(self):
        """Start all job processing components."""
        if self._running:
            logger.warning("Job service already running")
            return
        
        try:
            # Start scheduler
            if self.enable_scheduler:
                await job_scheduler.start()
                logger.info("Job scheduler started")
            
            # Start workers
            if self.use_worker_pool:
                await worker_pool.start()
                logger.info(f"Worker pool started with {self.num_workers} workers")
            else:
                await job_worker.start()
                logger.info("Single worker started")
            
            self._running = True
            logger.info("Job service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start job service: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop all job processing components."""
        try:
            # Stop scheduler
            if self.enable_scheduler:
                await job_scheduler.stop()
                logger.info("Job scheduler stopped")
            
            # Stop workers
            if self.use_worker_pool:
                await worker_pool.stop()
            else:
                await job_worker.stop()
            
            self._running = False
            logger.info("Job service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping job service: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all job service components."""
        return {
            "running": self._running,
            "timestamp": datetime.now(UTC).isoformat(),
            "scheduler": {
                "enabled": self.enable_scheduler,
                "running": job_scheduler._running if self.enable_scheduler else False,
            },
            "workers": {
                "mode": "pool" if self.use_worker_pool else "single",
                "running": worker_pool._running if self.use_worker_pool else job_worker._running,
            },
            "queue": await job_queue.get_queue_stats(),
        }
    
    # === Job Queue Operations ===
    
    async def enqueue(
        self,
        name: str,
        args: Dict[str, Any] = None,
        priority: JobPriority = JobPriority.NORMAL,
        scheduled_at: datetime = None,
        max_retries: int = 3,
        timeout: int = 300,
        user_id: str = None,
    ) -> str:
        """Enqueue a new job."""
        return await job_queue.enqueue(
            name=name,
            args=args,
            priority=priority,
            scheduled_at=scheduled_at,
            max_retries=max_retries,
            timeout=timeout,
            user_id=user_id,
        )
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return await job_queue.get_job(job_id)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        return await job_queue.cancel_job(job_id)
    
    async def get_job_result(self, job_id: str) -> Optional[Any]:
        """Get job result."""
        return await job_queue.get_job_result(job_id)
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return await job_queue.get_queue_stats()
    
    async def get_pending_jobs(
        self,
        priority: JobPriority = None,
        limit: int = 100,
    ) -> List[Job]:
        """Get pending jobs."""
        return await job_queue.get_pending_jobs(priority, limit)
    
    async def get_dead_letter_jobs(self, limit: int = 100) -> List[Job]:
        """Get jobs from dead letter queue."""
        return await job_queue.get_dead_letter_jobs(limit)
    
    async def retry_dead_letter_job(self, job_id: str) -> bool:
        """Retry a job from dead letter queue."""
        return await job_queue.retry_dead_letter_job(job_id)
    
    async def clear_dead_letter_queue(self) -> int:
        """Clear all jobs from dead letter queue."""
        return await job_queue.clear_dead_letter_queue()
    
    # === Scheduler Operations ===
    
    def register_scheduled_task(
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
    ):
        """Register a scheduled task."""
        return job_scheduler.register(
            name=name,
            job_name=job_name,
            schedule_type=schedule_type,
            args=args,
            priority=priority,
            interval_seconds=interval_seconds,
            cron_expression=cron_expression,
            run_at=run_at,
            enabled=enabled,
        )
    
    def unregister_scheduled_task(self, name: str) -> bool:
        """Unregister a scheduled task."""
        return job_scheduler.unregister(name)
    
    def enable_scheduled_task(self, name: str) -> bool:
        """Enable a scheduled task."""
        return job_scheduler.enable(name)
    
    def disable_scheduled_task(self, name: str) -> bool:
        """Disable a scheduled task."""
        return job_scheduler.disable(name)
    
    async def run_scheduled_task_now(self, name: str) -> Optional[str]:
        """Manually trigger a scheduled task."""
        return await job_scheduler.run_task_now(name)
    
    def get_scheduled_tasks(self) -> List[Dict[str, Any]]:
        """Get all scheduled tasks."""
        return job_scheduler.get_stats()["tasks"]
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return job_scheduler.get_stats()
    
    # === Worker Operations ===
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        if self.use_worker_pool:
            return worker_pool.get_stats()
        return job_worker.get_stats()
    
    def get_registered_job_handlers(self) -> List[str]:
        """Get list of registered job handlers."""
        return JobWorker.get_registered_jobs()
    
    # === Combined Stats ===
    
    async def get_full_stats(self) -> Dict[str, Any]:
        """Get comprehensive job service statistics."""
        return {
            "running": self._running,
            "timestamp": datetime.now(UTC).isoformat(),
            "queue": await self.get_queue_stats(),
            "scheduler": self.get_scheduler_stats() if self.enable_scheduler else None,
            "workers": self.get_worker_stats(),
            "registered_handlers": self.get_registered_job_handlers(),
        }


# Global job service instance
job_service = JobService(
    use_worker_pool=False,
    enable_scheduler=True,
)
