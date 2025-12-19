"""Background worker for processing jobs from queue."""

import asyncio
import logging
import signal
import sys
from typing import Optional, Dict, Callable, Awaitable, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from .job_queue import job_queue, Job, JobStatus

logger = logging.getLogger(__name__)


class WorkerStatus(str, Enum):
    """Worker status."""
    IDLE = "idle"
    PROCESSING = "processing"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class WorkerStats:
    """Worker statistics."""
    worker_id: str
    status: WorkerStatus
    started_at: Optional[datetime] = None
    jobs_processed: int = 0
    jobs_succeeded: int = 0
    jobs_failed: int = 0
    current_job: Optional[str] = None
    last_job_at: Optional[datetime] = None
    total_processing_time: float = 0.0
    
    @property
    def average_processing_time(self) -> float:
        """Average job processing time in seconds."""
        if self.jobs_processed == 0:
            return 0.0
        return self.total_processing_time / self.jobs_processed
    
    @property
    def success_rate(self) -> float:
        """Job success rate as percentage."""
        if self.jobs_processed == 0:
            return 100.0
        return (self.jobs_succeeded / self.jobs_processed) * 100


# Type alias for task handlers
TaskHandler = Callable[[Dict[str, Any]], Awaitable[Any]]


class JobWorker:
    """Background worker that processes jobs from the queue."""
    
    # Registry of task handlers
    _handlers: Dict[str, TaskHandler] = {}
    
    def __init__(
        self,
        worker_id: str = None,
        poll_interval: float = 1.0,
        max_concurrent_jobs: int = 1,
    ):
        self.worker_id = worker_id or f"worker-{id(self)}"
        self.poll_interval = poll_interval
        self.max_concurrent_jobs = max_concurrent_jobs
        
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._current_jobs: Dict[str, asyncio.Task] = {}
        
        self.stats = WorkerStats(
            worker_id=self.worker_id,
            status=WorkerStatus.STOPPED,
        )
    
    @classmethod
    def register_handler(cls, job_name: str, handler: TaskHandler):
        """Register a handler for a job type."""
        cls._handlers[job_name] = handler
        logger.info(f"Registered handler for job: {job_name}")
    
    @classmethod
    def get_handler(cls, job_name: str) -> Optional[TaskHandler]:
        """Get handler for a job type."""
        return cls._handlers.get(job_name)
    
    @classmethod
    def get_registered_jobs(cls) -> List[str]:
        """Get list of registered job names."""
        return list(cls._handlers.keys())
    
    async def start(self):
        """Start the worker."""
        if self._running:
            return
        
        self._running = True
        self.stats.status = WorkerStatus.IDLE
        self.stats.started_at = datetime.utcnow()
        
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info(f"Worker {self.worker_id} started")
    
    async def stop(self, wait_for_jobs: bool = True):
        """Stop the worker."""
        self._running = False
        self.stats.status = WorkerStatus.STOPPING
        
        # Wait for current jobs to finish
        if wait_for_jobs and self._current_jobs:
            logger.info(f"Worker {self.worker_id} waiting for {len(self._current_jobs)} jobs to finish")
            try:
                await asyncio.wait(
                    list(self._current_jobs.values()),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Worker {self.worker_id} timeout waiting for jobs")
        
        # Cancel remaining tasks
        for job_id, task in self._current_jobs.items():
            if not task.done():
                task.cancel()
                logger.warning(f"Cancelled job {job_id}")
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        
        self.stats.status = WorkerStatus.STOPPED
        logger.info(f"Worker {self.worker_id} stopped")
    
    async def _worker_loop(self):
        """Main worker loop."""
        while self._running:
            try:
                # Check if we can process more jobs
                if len(self._current_jobs) >= self.max_concurrent_jobs:
                    await asyncio.sleep(self.poll_interval)
                    continue
                
                # Try to get a job
                job = await job_queue.dequeue()
                
                if job:
                    self.stats.status = WorkerStatus.PROCESSING
                    task = asyncio.create_task(self._process_job(job))
                    self._current_jobs[job.id] = task
                    task.add_done_callback(
                        lambda t, job_id=job.id: self._job_done_callback(job_id)
                    )
                else:
                    self.stats.status = WorkerStatus.IDLE
                    await asyncio.sleep(self.poll_interval)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(self.poll_interval)
    
    def _job_done_callback(self, job_id: str):
        """Callback when a job task is done."""
        if job_id in self._current_jobs:
            del self._current_jobs[job_id]
        
        if not self._current_jobs:
            self.stats.status = WorkerStatus.IDLE
    
    async def _process_job(self, job: Job):
        """Process a single job."""
        start_time = datetime.utcnow()
        self.stats.current_job = job.id
        self.stats.last_job_at = start_time
        
        logger.info(f"Worker {self.worker_id} processing job {job.id} ({job.name})")
        
        try:
            # Get handler
            handler = self._handlers.get(job.name)
            
            if not handler:
                raise ValueError(f"No handler registered for job: {job.name}")
            
            # Execute with timeout
            result = await asyncio.wait_for(
                handler(job.args),
                timeout=job.timeout
            )
            
            # Mark as completed
            await job_queue.complete_job(job, result)
            
            self.stats.jobs_succeeded += 1
            
        except asyncio.TimeoutError:
            error_msg = f"Job timed out after {job.timeout}s"
            logger.error(f"Job {job.id} ({job.name}): {error_msg}")
            await job_queue.fail_job(job, error_msg)
            self.stats.jobs_failed += 1
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Job {job.id} ({job.name}) failed: {error_msg}")
            await job_queue.fail_job(job, error_msg)
            self.stats.jobs_failed += 1
        
        finally:
            self.stats.jobs_processed += 1
            self.stats.current_job = None
            
            # Update processing time
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            self.stats.total_processing_time += elapsed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        return {
            "worker_id": self.worker_id,
            "status": self.stats.status.value,
            "started_at": self.stats.started_at.isoformat() if self.stats.started_at else None,
            "jobs_processed": self.stats.jobs_processed,
            "jobs_succeeded": self.stats.jobs_succeeded,
            "jobs_failed": self.stats.jobs_failed,
            "success_rate": self.stats.success_rate,
            "current_job": self.stats.current_job,
            "current_jobs_count": len(self._current_jobs),
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "last_job_at": self.stats.last_job_at.isoformat() if self.stats.last_job_at else None,
            "average_processing_time": self.stats.average_processing_time,
            "total_processing_time": self.stats.total_processing_time,
        }


# Decorator to register job handlers
def job_handler(job_name: str = None):
    """Decorator to register a function as a job handler."""
    def decorator(func: TaskHandler):
        name = job_name or func.__name__
        JobWorker.register_handler(name, func)
        return func
    return decorator


# Global worker instance
job_worker = JobWorker(worker_id="main-worker")


class WorkerPool:
    """Pool of workers for parallel job processing."""
    
    def __init__(self, num_workers: int = 3, max_concurrent_per_worker: int = 1):
        self.num_workers = num_workers
        self.max_concurrent_per_worker = max_concurrent_per_worker
        self.workers: List[JobWorker] = []
        self._running = False
    
    async def start(self):
        """Start all workers in the pool."""
        if self._running:
            return
        
        self._running = True
        
        for i in range(self.num_workers):
            worker = JobWorker(
                worker_id=f"pool-worker-{i}",
                max_concurrent_jobs=self.max_concurrent_per_worker,
            )
            self.workers.append(worker)
            await worker.start()
        
        logger.info(f"Worker pool started with {self.num_workers} workers")
    
    async def stop(self, wait_for_jobs: bool = True):
        """Stop all workers in the pool."""
        self._running = False
        
        stop_tasks = [
            worker.stop(wait_for_jobs=wait_for_jobs)
            for worker in self.workers
        ]
        await asyncio.gather(*stop_tasks)
        
        self.workers.clear()
        logger.info("Worker pool stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        worker_stats = [w.get_stats() for w in self.workers]
        
        total_processed = sum(s["jobs_processed"] for s in worker_stats)
        total_succeeded = sum(s["jobs_succeeded"] for s in worker_stats)
        total_failed = sum(s["jobs_failed"] for s in worker_stats)
        
        return {
            "running": self._running,
            "num_workers": self.num_workers,
            "total_jobs_processed": total_processed,
            "total_jobs_succeeded": total_succeeded,
            "total_jobs_failed": total_failed,
            "overall_success_rate": (total_succeeded / total_processed * 100) if total_processed > 0 else 100.0,
            "workers": worker_stats,
        }


# Global worker pool
worker_pool = WorkerPool()
