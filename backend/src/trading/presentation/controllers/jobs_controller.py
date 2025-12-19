"""Jobs API controller."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict

from ...infrastructure.jobs import (
    job_service,
    JobPriority,
    JobStatus,
    ScheduleType,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# ============================================================================
# Request/Response Models
# ============================================================================

class EnqueueJobRequest(BaseModel):
    """Request to enqueue a new job."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "sync_portfolio",
            "args": {"user_id": "user-123", "exchange": "binance"},
            "priority": "high",
            "max_retries": 3,
            "timeout": 300
        }
    })
    
    name: str = Field(..., description="Job name (must match a registered handler)")
    args: Dict[str, Any] = Field(default_factory=dict, description="Job arguments")
    priority: str = Field(default="normal", description="Job priority")
    scheduled_at: Optional[datetime] = Field(None, description="Schedule job for later execution")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    timeout: int = Field(default=300, ge=10, le=3600, description="Job timeout in seconds")


class JobResponse(BaseModel):
    """Job information response."""
    id: str
    name: str
    args: Dict[str, Any]
    status: str
    priority: str
    created_at: str
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    retry_count: int
    max_retries: int


class RegisterScheduledTaskRequest(BaseModel):
    """Request to register a scheduled task."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "my_portfolio_sync",
            "job_name": "sync_portfolio",
            "schedule_type": "interval",
            "interval_seconds": 300,
            "args": {"user_id": "user-123"},
            "priority": "normal",
    }})
    
    name: str = Field(..., description="Unique task name")
    job_name: str = Field(..., description="Job handler name to execute")
    schedule_type: str = Field(default="interval", description="Schedule type: interval, cron, once")
    args: Dict[str, Any] = Field(default_factory=dict, description="Job arguments")
    priority: str = Field(default="normal", description="Job priority")
    interval_seconds: Optional[int] = Field(None, ge=10, description="Interval in seconds (for interval type)")
    cron_expression: Optional[str] = Field(None, description="Cron expression (for cron type)")
    run_at: Optional[datetime] = Field(None, description="Execution time (for once type)")
    enabled: bool = Field(default=True, description="Whether task is enabled")


# ============================================================================
# Health & Stats Endpoints
# ============================================================================

@router.get("/health")
async def jobs_health():
    """Get job service health status."""
    return await job_service.health_check()


@router.get("/stats")
async def get_job_stats():
    """Get comprehensive job service statistics."""
    return await job_service.get_full_stats()


@router.get("/queue/stats")
async def get_queue_stats():
    """Get queue statistics."""
    return await job_service.get_queue_stats()


@router.get("/workers/stats")
async def get_worker_stats():
    """Get worker statistics."""
    return job_service.get_worker_stats()


@router.get("/scheduler/stats")
async def get_scheduler_stats():
    """Get scheduler statistics."""
    return job_service.get_scheduler_stats()


@router.get("/handlers")
async def get_registered_handlers():
    """Get list of registered job handlers."""
    return {
        "handlers": job_service.get_registered_job_handlers()
    }


# ============================================================================
# Job Queue Endpoints
# ============================================================================

@router.post("/enqueue", response_model=Dict[str, str])
async def enqueue_job(request: EnqueueJobRequest):
    """Enqueue a new job for execution."""
    try:
        priority_map = {
            "low": JobPriority.LOW,
            "normal": JobPriority.NORMAL,
            "high": JobPriority.HIGH,
            "critical": JobPriority.CRITICAL,
        }
        priority = priority_map.get(request.priority.lower(), JobPriority.NORMAL)
        
        job_id = await job_service.enqueue(
            name=request.name,
            args=request.args,
            priority=priority,
            scheduled_at=request.scheduled_at,
            max_retries=request.max_retries,
            timeout=request.timeout,
        )
        
        return {"job_id": job_id, "status": "enqueued"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}")
async def get_job(job_id: str):
    """Get job details by ID."""
    job = await job_service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job.to_dict()


@router.get("/job/{job_id}/result")
async def get_job_result(job_id: str):
    """Get job result by ID."""
    job = await job_service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = await job_service.get_job_result(job_id)
    
    return {
        "job_id": job_id,
        "status": job.status.value,
        "result": result,
        "error": job.error,
    }


@router.post("/job/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a pending job."""
    success = await job_service.cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="Job cannot be cancelled (may already be running or completed)"
        )
    
    return {"job_id": job_id, "status": "cancelled"}


@router.get("/pending")
async def get_pending_jobs(
    priority: Optional[str] = Query(None, description="Filter by priority"),
    limit: int = Query(100, ge=1, le=1000),
):
    """Get list of pending jobs."""
    priority_filter = None
    if priority:
        priority_map = {
            "low": JobPriority.LOW,
            "normal": JobPriority.NORMAL,
            "high": JobPriority.HIGH,
            "critical": JobPriority.CRITICAL,
        }
        priority_filter = priority_map.get(priority.lower())
    
    jobs = await job_service.get_pending_jobs(priority=priority_filter, limit=limit)
    
    return {
        "count": len(jobs),
        "jobs": [j.to_dict() for j in jobs]
    }


# ============================================================================
# Dead Letter Queue Endpoints
# ============================================================================

@router.get("/dlq")
async def get_dead_letter_jobs(
    limit: int = Query(100, ge=1, le=1000),
):
    """Get jobs from dead letter queue."""
    jobs = await job_service.get_dead_letter_jobs(limit=limit)
    
    return {
        "count": len(jobs),
        "jobs": [j.to_dict() for j in jobs]
    }


@router.post("/dlq/{job_id}/retry")
async def retry_dead_letter_job(job_id: str):
    """Retry a job from dead letter queue."""
    success = await job_service.retry_dead_letter_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Job cannot be retried (may not be in DLQ)"
        )
    
    return {"job_id": job_id, "status": "requeued"}


@router.delete("/dlq")
async def clear_dead_letter_queue():
    """Clear all jobs from dead letter queue."""
    count = await job_service.clear_dead_letter_queue()
    return {"cleared": count}


# ============================================================================
# Scheduled Tasks Endpoints
# ============================================================================

@router.get("/scheduled")
async def get_scheduled_tasks():
    """Get all scheduled tasks."""
    return {
        "tasks": job_service.get_scheduled_tasks()
    }


@router.post("/scheduled/register")
async def register_scheduled_task(request: RegisterScheduledTaskRequest):
    """Register a new scheduled task."""
    try:
        schedule_type_map = {
            "interval": ScheduleType.INTERVAL,
            "cron": ScheduleType.CRON,
            "once": ScheduleType.ONCE,
        }
        schedule_type = schedule_type_map.get(
            request.schedule_type.lower(), 
            ScheduleType.INTERVAL
        )
        
        priority_map = {
            "low": JobPriority.LOW,
            "normal": JobPriority.NORMAL,
            "high": JobPriority.HIGH,
            "critical": JobPriority.CRITICAL,
        }
        priority = priority_map.get(request.priority.lower(), JobPriority.NORMAL)
        
        task = job_service.register_scheduled_task(
            name=request.name,
            job_name=request.job_name,
            schedule_type=schedule_type,
            args=request.args,
            priority=priority,
            interval_seconds=request.interval_seconds,
            cron_expression=request.cron_expression,
            run_at=request.run_at,
            enabled=request.enabled,
        )
        
        return {
            "name": task.name,
            "job_name": task.job_name,
            "schedule_type": task.schedule_type.value,
            "next_run": task.next_run.isoformat() if task.next_run else None,
            "enabled": task.enabled,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scheduled/{task_name}")
async def unregister_scheduled_task(task_name: str):
    """Unregister a scheduled task."""
    success = job_service.unregister_scheduled_task(task_name)
    
    if not success:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    
    return {"task_name": task_name, "status": "unregistered"}


@router.post("/scheduled/{task_name}/enable")
async def enable_scheduled_task(task_name: str):
    """Enable a scheduled task."""
    success = job_service.enable_scheduled_task(task_name)
    
    if not success:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    
    return {"task_name": task_name, "status": "enabled"}


@router.post("/scheduled/{task_name}/disable")
async def disable_scheduled_task(task_name: str):
    """Disable a scheduled task."""
    success = job_service.disable_scheduled_task(task_name)
    
    if not success:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    
    return {"task_name": task_name, "status": "disabled"}


@router.post("/scheduled/{task_name}/run")
async def run_scheduled_task_now(task_name: str):
    """Manually trigger a scheduled task to run now."""
    job_id = await job_service.run_scheduled_task_now(task_name)
    
    if not job_id:
        raise HTTPException(status_code=404, detail="Scheduled task not found")
    
    return {
        "task_name": task_name,
        "job_id": job_id,
        "status": "triggered"
    }
