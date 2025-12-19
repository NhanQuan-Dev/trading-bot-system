"""Test cases for Job and JobQueue."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import json

from src.trading.infrastructure.jobs.job_queue import (
    Job,
    JobQueue,
    JobStatus,
    JobPriority
)


class TestJobStatus:
    """Test JobStatus enum."""
    
    def test_job_status_values(self):
        """Test JobStatus enum values."""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"
        assert JobStatus.RETRYING == "retrying"


class TestJobPriority:
    """Test JobPriority enum."""
    
    def test_job_priority_values(self):
        """Test JobPriority enum values."""
        assert JobPriority.LOW == "low"
        assert JobPriority.NORMAL == "normal"
        assert JobPriority.HIGH == "high"
        assert JobPriority.CRITICAL == "critical"


class TestJob:
    """Test Job dataclass."""
    
    def test_create_job_minimal(self):
        """Test creating job with minimal data."""
        job = Job(
            id="job-123",
            name="test_task",
            args={},
            status=JobStatus.PENDING,
            priority=JobPriority.NORMAL,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        assert job.id == "job-123"
        assert job.name == "test_task"
        assert job.status == JobStatus.PENDING
        assert job.priority == JobPriority.NORMAL
        assert job.max_retries == 3
        assert job.timeout == 300
    
    def test_create_job_full(self):
        """Test creating job with all fields."""
        now = datetime.now(timezone.utc)
        
        job = Job(
            id="job-456",
            name="complex_task",
            args={"param1": "value1", "param2": 42},
            status=JobStatus.RUNNING,
            priority=JobPriority.HIGH,
            created_at=now.isoformat(),
            scheduled_at=(now + timedelta(hours=1)).isoformat(),
            started_at=now.isoformat(),
            max_retries=5,
            timeout=600,
            user_id="user-123"
        )
        
        assert job.id == "job-456"
        assert job.args == {"param1": "value1", "param2": 42}
        assert job.max_retries == 5
        assert job.timeout == 600
        assert job.user_id == "user-123"
    
    def test_job_to_dict(self):
        """Test job serialization to dict."""
        job = Job(
            id="job-789",
            name="test_task",
            args={"key": "value"},
            status=JobStatus.PENDING,
            priority=JobPriority.NORMAL,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        job_dict = job.to_dict()
        
        assert isinstance(job_dict, dict)
        assert job_dict["id"] == "job-789"
        assert job_dict["name"] == "test_task"
        assert job_dict["args"] == {"key": "value"}
        assert job_dict["status"] == JobStatus.PENDING
        assert job_dict["priority"] == JobPriority.NORMAL
    
    def test_job_from_dict(self):
        """Test job deserialization from dict."""
        job_dict = {
            "id": "job-abc",
            "name": "test_task",
            "args": {"test": True},
            "status": "pending",
            "priority": "high",
            "created_at": "2024-01-15T12:00:00",
            "scheduled_at": None,
            "started_at": None,
            "completed_at": None,
            "error": None,
            "result": None,
            "retry_count": 0,
            "max_retries": 3,
            "timeout": 300,
            "user_id": None
        }
        
        job = Job.from_dict(job_dict)
        
        assert job.id == "job-abc"
        assert job.name == "test_task"
        assert job.status == JobStatus.PENDING
        assert job.priority == JobPriority.HIGH
        assert job.args == {"test": True}
    
    def test_job_to_json(self):
        """Test job JSON serialization."""
        job = Job(
            id="job-def",
            name="json_task",
            args={"data": [1, 2, 3]},
            status=JobStatus.COMPLETED,
            priority=JobPriority.NORMAL,
            created_at=datetime.now(timezone.utc).isoformat(),
            result={"success": True}
        )
        
        json_str = job.to_json()
        
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["id"] == "job-def"
        assert parsed["result"] == {"success": True}
    
    def test_job_from_json(self):
        """Test job JSON deserialization."""
        json_str = json.dumps({
            "id": "job-ghi",
            "name": "from_json_task",
            "args": {},
            "status": "failed",
            "priority": "low",
            "created_at": "2024-01-15T12:00:00",
            "scheduled_at": None,
            "started_at": None,
            "completed_at": "2024-01-15T12:05:00",
            "error": "Test error",
            "result": None,
            "retry_count": 3,
            "max_retries": 3,
            "timeout": 300,
            "user_id": None
        })
        
        job = Job.from_json(json_str)
        
        assert job.id == "job-ghi"
        assert job.status == JobStatus.FAILED
        assert job.error == "Test error"
        assert job.retry_count == 3


class TestJobQueue:
    """Test JobQueue implementation."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_mock = AsyncMock()
        redis_mock.set = AsyncMock(return_value=True)
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.rpush = AsyncMock(return_value=1)
        redis_mock.lpop = AsyncMock(return_value=None)
        redis_mock.zadd = AsyncMock(return_value=1)
        redis_mock.zrangebyscore = AsyncMock(return_value=[])
        redis_mock.zrem = AsyncMock(return_value=1)
        redis_mock.sadd = AsyncMock(return_value=1)
        redis_mock.srem = AsyncMock(return_value=1)
        return redis_mock
    
    @pytest.fixture
    def job_queue(self, mock_redis):
        """Create JobQueue instance with mocked Redis."""
        queue = JobQueue(prefix="test_jobs")
        queue.redis = mock_redis
        return queue
    
    def test_init(self, job_queue):
        """Test JobQueue initialization."""
        assert job_queue.prefix == "test_jobs"
        assert "test_jobs:queue:critical" in job_queue.queues.values()
        assert job_queue.scheduled_set == "test_jobs:scheduled"
        assert job_queue.processing_set == "test_jobs:processing"
    
    @pytest.mark.asyncio
    async def test_enqueue_immediate(self, job_queue, mock_redis):
        """Test enqueueing immediate job."""
        job_id = await job_queue.enqueue(
            name="test_task",
            args={"param": "value"},
            priority=JobPriority.HIGH
        )
        
        assert job_id is not None
        # Verify job data was saved
        mock_redis.set.assert_called_once()
        # Verify job was added to queue
        mock_redis.rpush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_enqueue_scheduled(self, job_queue, mock_redis):
        """Test enqueueing scheduled job."""
        with patch('src.trading.infrastructure.jobs.job_queue.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 15, 12, 0, 0)
            future_time = datetime(2024, 1, 15, 13, 0, 0)  # 1 hour later, naive
            
            job_id = await job_queue.enqueue(
                name="scheduled_task",
                args={},
                priority=JobPriority.NORMAL,
                scheduled_at=future_time
            )
        
            assert job_id is not None
            # Verify job was added to scheduled set
            mock_redis.zadd.assert_called_once()
            # Verify job was NOT added to immediate queue
            mock_redis.rpush.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_enqueue_with_options(self, job_queue, mock_redis):
        """Test enqueueing with custom options."""
        job_id = await job_queue.enqueue(
            name="custom_task",
            args={"data": [1, 2, 3]},
            priority=JobPriority.CRITICAL,
            max_retries=5,
            timeout=600,
            user_id="user-123"
        )
        
        assert job_id is not None
        # Verify options were saved
        call_args = mock_redis.set.call_args
        job_json = call_args[0][1]
        job_data = json.loads(job_json)
        assert job_data["max_retries"] == 5
        assert job_data["timeout"] == 600
        assert job_data["user_id"] == "user-123"
    
    @pytest.mark.asyncio
    async def test_dequeue_from_priority_queue(self, job_queue, mock_redis):
        """Test dequeuing job from priority queue."""
        # Mock lpop to return job ID
        mock_redis.lpop.return_value = "job-123"
        
        # Mock get_job to return job data
        job_data = Job(
            id="job-123",
            name="test_task",
            args={},
            status=JobStatus.PENDING,
            priority=JobPriority.HIGH,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        mock_redis.get.return_value = job_data.to_json()
        
        job = await job_queue.dequeue()
        
        assert job is not None
        assert job.id == "job-123"
        assert job.status == JobStatus.RUNNING
        # Verify job was marked as processing
        mock_redis.sadd.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dequeue_empty_queue(self, job_queue, mock_redis):
        """Test dequeuing from empty queue."""
        mock_redis.lpop.return_value = None
        
        job = await job_queue.dequeue()
        assert job is None
    
    @pytest.mark.asyncio
    async def test_get_job_exists(self, job_queue, mock_redis):
        """Test getting existing job."""
        job_data = Job(
            id="job-456",
            name="test_task",
            args={"key": "value"},
            status=JobStatus.RUNNING,
            priority=JobPriority.NORMAL,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        mock_redis.get.return_value = job_data.to_json()
        
        job = await job_queue.get_job("job-456")
        
        assert job is not None
        assert job.id == "job-456"
        assert job.args == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_get_job_not_found(self, job_queue, mock_redis):
        """Test getting non-existent job."""
        mock_redis.get.return_value = None
        
        job = await job_queue.get_job("nonexistent")
        assert job is None
    
    @pytest.mark.asyncio
    async def test_complete_job(self, job_queue, mock_redis):
        """Test completing a job."""
        job = Job(
            id="job-789",
            name="test_task",
            args={},
            status=JobStatus.RUNNING,
            priority=JobPriority.NORMAL,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        await job_queue.complete_job(job, result={"output": "success"})
        
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.result == {"output": "success"}
        # Verify job was saved
        mock_redis.set.assert_called()
        # Verify removed from processing set
        mock_redis.srem.assert_called()
    
    @pytest.mark.asyncio
    async def test_fail_job_with_retry(self, job_queue, mock_redis):
        """Test failing job with retry."""
        job = Job(
            id="job-abc",
            name="test_task",
            args={},
            status=JobStatus.RUNNING,
            priority=JobPriority.NORMAL,
            created_at=datetime.now(timezone.utc).isoformat(),
            retry_count=0,
            max_retries=3
        )
        
        await job_queue.fail_job(job, error="Test error", retry=True)
        
        assert job.status == JobStatus.RETRYING
        assert job.retry_count == 1
        assert job.error == "Test error"
        # Verify job was rescheduled
        mock_redis.zadd.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fail_job_permanently(self, job_queue, mock_redis):
        """Test failing job permanently."""
        job = Job(
            id="job-def",
            name="test_task",
            args={},
            status=JobStatus.RUNNING,
            priority=JobPriority.NORMAL,
            created_at=datetime.now(timezone.utc).isoformat(),
            retry_count=3,
            max_retries=3
        )
        
        await job_queue.fail_job(job, error="Final error", retry=True)
        
        assert job.status == JobStatus.FAILED
        assert job.completed_at is not None
        # Verify job was moved to dead letter queue
        assert mock_redis.rpush.call_count >= 1
