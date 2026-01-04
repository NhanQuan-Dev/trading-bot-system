"""Simple status check endpoint for repair jobs."""

from fastapi import APIRouter, HTTPException
from uuid import UUID
from ...infrastructure.jobs.job_queue import job_queue

router = APIRouter()


@router.get("/repair-jobs/{job_id}/status")  
async def get_repair_job_status(job_id: UUID):
    """Check status of a background data repair job."""
    try:
        job = await job_queue.get_job(str(job_id))
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": str(job_id),
            "status": job.status,  # QUEUED, RUNNING, COMPLETED, FAILED
            "created_at": job.created_at.isoformat() if hasattr(job, 'created_at') else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching job status: {str(e)}")
