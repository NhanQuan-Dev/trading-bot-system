"""Redis-based job queue implementation."""

import asyncio
import json
import logging
import uuid
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from ..cache import redis_client

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(str, Enum):
    """Job priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Job:
    """Job definition."""
    id: str
    name: str
    args: Dict[str, Any]
    status: JobStatus
    priority: JobPriority
    created_at: str
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 300  # 5 minutes default
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Create job from dictionary."""
        data["status"] = JobStatus(data["status"])
        data["priority"] = JobPriority(data["priority"])
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert job to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Job":
        """Create job from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class JobQueue:
    """Redis-based job queue for background task processing."""
    
    def __init__(self, prefix: str = "jobs"):
        self.prefix = prefix
        self.redis = redis_client
        
        # Queue names for different priorities
        self.queues = {
            JobPriority.CRITICAL: f"{prefix}:queue:critical",
            JobPriority.HIGH: f"{prefix}:queue:high",
            JobPriority.NORMAL: f"{prefix}:queue:normal",
            JobPriority.LOW: f"{prefix}:queue:low",
        }
        
        # Other key prefixes
        self.job_data_prefix = f"{prefix}:job"
        self.scheduled_set = f"{prefix}:scheduled"
        self.processing_set = f"{prefix}:processing"
        self.dead_letter_queue = f"{prefix}:dlq"
        self.results_prefix = f"{prefix}:results"
    
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
        """Add a job to the queue."""
        job_id = str(uuid.uuid4())
        
        job = Job(
            id=job_id,
            name=name,
            args=args or {},
            status=JobStatus.PENDING,
            priority=priority,
            created_at=datetime.utcnow().isoformat(),
            scheduled_at=scheduled_at.isoformat() if scheduled_at else None,
            max_retries=max_retries,
            timeout=timeout,
            user_id=user_id,
        )
        
        try:
            # Store job data
            job_key = f"{self.job_data_prefix}:{job_id}"
            await self.redis.set(job_key, job.to_json(), ex=86400 * 7)  # 7 days TTL
            
            if scheduled_at and scheduled_at > datetime.utcnow():
                # Add to scheduled set with score as timestamp
                await self.redis.zadd(
                    self.scheduled_set,
                    {job_id: scheduled_at.timestamp()}
                )
            else:
                # Add to immediate queue
                queue_key = self.queues[priority]
                await self.redis.rpush(queue_key, job_id)
            
            logger.info(f"Job {job_id} ({name}) enqueued with priority {priority.value}")
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to enqueue job {name}: {e}")
            raise
    
    async def dequeue(self, timeout: int = 5) -> Optional[Job]:
        """Get next job from queue (priority ordered)."""
        try:
            # First, move scheduled jobs that are ready
            await self._move_scheduled_jobs()
            
            # Try queues in priority order
            for priority in [JobPriority.CRITICAL, JobPriority.HIGH, 
                           JobPriority.NORMAL, JobPriority.LOW]:
                queue_key = self.queues[priority]
                
                # Pop job ID from queue
                job_id = await self.redis.lpop(queue_key)
                
                if job_id:
                    job = await self.get_job(job_id)
                    if job:
                        # Mark as processing
                        await self.redis.sadd(self.processing_set, job_id)
                        job.status = JobStatus.RUNNING
                        job.started_at = datetime.utcnow().isoformat()
                        await self._save_job(job)
                        
                        return job
            
            return None
            
        except Exception as e:
            logger.error(f"Error dequeuing job: {e}")
            return None
    
    async def _move_scheduled_jobs(self):
        """Move scheduled jobs that are ready to the main queue."""
        try:
            now = datetime.utcnow().timestamp()
            
            # Get jobs that are ready (score <= now)
            ready_jobs = await self.redis.zrangebyscore(
                self.scheduled_set, 0, now, withscores=False
            )
            
            for job_id in ready_jobs:
                job = await self.get_job(job_id)
                if job:
                    # Add to appropriate queue
                    queue_key = self.queues[job.priority]
                    await self.redis.rpush(queue_key, job_id)
                    
                    # Remove from scheduled set
                    await self.redis.zrem(self.scheduled_set, job_id)
                    
                    logger.debug(f"Moved scheduled job {job_id} to queue")
                    
        except Exception as e:
            logger.error(f"Error moving scheduled jobs: {e}")
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        try:
            job_key = f"{self.job_data_prefix}:{job_id}"
            job_data = await self.redis.get(job_key)
            
            if job_data:
                return Job.from_json(job_data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {e}")
            return None
    
    async def _save_job(self, job: Job):
        """Save job data."""
        job_key = f"{self.job_data_prefix}:{job.id}"
        await self.redis.set(job_key, job.to_json(), ex=86400 * 7)
    
    async def complete_job(self, job: Job, result: Any = None):
        """Mark job as completed."""
        try:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow().isoformat()
            job.result = result
            
            await self._save_job(job)
            
            # Remove from processing set
            await self.redis.srem(self.processing_set, job.id)
            
            # Store result separately if provided
            if result:
                result_key = f"{self.results_prefix}:{job.id}"
                await self.redis.set(result_key, json.dumps(result, default=str), ex=86400)
            
            logger.info(f"Job {job.id} ({job.name}) completed successfully")
            
        except Exception as e:
            logger.error(f"Error completing job {job.id}: {e}")
    
    async def fail_job(self, job: Job, error: str, retry: bool = True):
        """Mark job as failed."""
        try:
            if retry and job.retry_count < job.max_retries:
                # Retry the job
                job.status = JobStatus.RETRYING
                job.retry_count += 1
                job.error = error
                
                await self._save_job(job)
                
                # Re-queue with exponential backoff
                delay = min(60 * (2 ** job.retry_count), 3600)  # Max 1 hour
                scheduled_at = datetime.utcnow() + timedelta(seconds=delay)
                
                await self.redis.zadd(
                    self.scheduled_set,
                    {job.id: scheduled_at.timestamp()}
                )
                
                # Remove from processing set
                await self.redis.srem(self.processing_set, job.id)
                
                logger.warning(
                    f"Job {job.id} ({job.name}) failed, retry {job.retry_count}/{job.max_retries} "
                    f"scheduled in {delay}s: {error}"
                )
            else:
                # Move to dead letter queue
                job.status = JobStatus.FAILED
                job.completed_at = datetime.utcnow().isoformat()
                job.error = error
                
                await self._save_job(job)
                
                # Remove from processing set
                await self.redis.srem(self.processing_set, job.id)
                
                # Add to dead letter queue
                await self.redis.rpush(self.dead_letter_queue, job.id)
                
                logger.error(f"Job {job.id} ({job.name}) failed permanently: {error}")
                
        except Exception as e:
            logger.error(f"Error failing job {job.id}: {e}")
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        try:
            job = await self.get_job(job_id)
            if not job:
                return False
            
            if job.status not in [JobStatus.PENDING, JobStatus.RETRYING]:
                return False
            
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow().isoformat()
            
            await self._save_job(job)
            
            # Remove from scheduled set if present
            await self.redis.zrem(self.scheduled_set, job_id)
            
            logger.info(f"Job {job_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False
    
    async def get_job_result(self, job_id: str) -> Optional[Any]:
        """Get job result."""
        try:
            result_key = f"{self.results_prefix}:{job_id}"
            result_data = await self.redis.get(result_key)
            
            if result_data:
                return json.loads(result_data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting job result {job_id}: {e}")
            return None
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        try:
            stats = {
                "pending": {},
                "scheduled": 0,
                "processing": 0,
                "dead_letter": 0,
            }
            
            # Count jobs in each priority queue
            for priority, queue_key in self.queues.items():
                count = await self.redis.llen(queue_key)
                stats["pending"][priority.value] = count
            
            # Count scheduled jobs
            stats["scheduled"] = await self.redis.zcard(self.scheduled_set)
            
            # Count processing jobs
            stats["processing"] = await self.redis.scard(self.processing_set)
            
            # Count dead letter queue
            stats["dead_letter"] = await self.redis.llen(self.dead_letter_queue)
            
            # Calculate totals
            stats["total_pending"] = sum(stats["pending"].values())
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {"error": str(e)}
    
    async def get_pending_jobs(
        self, 
        priority: JobPriority = None, 
        limit: int = 100
    ) -> List[Job]:
        """Get list of pending jobs."""
        try:
            jobs = []
            queues_to_check = [self.queues[priority]] if priority else list(self.queues.values())
            
            for queue_key in queues_to_check:
                job_ids = await self.redis.lrange(queue_key, 0, limit - 1 - len(jobs))
                
                for job_id in job_ids:
                    job = await self.get_job(job_id)
                    if job:
                        jobs.append(job)
                    
                    if len(jobs) >= limit:
                        break
                
                if len(jobs) >= limit:
                    break
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting pending jobs: {e}")
            return []
    
    async def get_dead_letter_jobs(self, limit: int = 100) -> List[Job]:
        """Get jobs from dead letter queue."""
        try:
            job_ids = await self.redis.lrange(self.dead_letter_queue, 0, limit - 1)
            jobs = []
            
            for job_id in job_ids:
                job = await self.get_job(job_id)
                if job:
                    jobs.append(job)
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error getting dead letter jobs: {e}")
            return []
    
    async def retry_dead_letter_job(self, job_id: str) -> bool:
        """Retry a job from dead letter queue."""
        try:
            job = await self.get_job(job_id)
            if not job or job.status != JobStatus.FAILED:
                return False
            
            # Reset job for retry
            job.status = JobStatus.PENDING
            job.retry_count = 0
            job.error = None
            job.started_at = None
            job.completed_at = None
            
            await self._save_job(job)
            
            # Remove from dead letter queue
            await self.redis.lrem(self.dead_letter_queue, 1, job_id)
            
            # Add back to queue
            queue_key = self.queues[job.priority]
            await self.redis.rpush(queue_key, job_id)
            
            logger.info(f"Job {job_id} moved from DLQ to queue for retry")
            return True
            
        except Exception as e:
            logger.error(f"Error retrying dead letter job {job_id}: {e}")
            return False
    
    async def clear_dead_letter_queue(self) -> int:
        """Clear all jobs from dead letter queue."""
        try:
            count = await self.redis.llen(self.dead_letter_queue)
            await self.redis.delete(self.dead_letter_queue)
            logger.warning(f"Cleared {count} jobs from dead letter queue")
            return count
        except Exception as e:
            logger.error(f"Error clearing dead letter queue: {e}")
            return 0


# Global job queue instance
job_queue = JobQueue()
