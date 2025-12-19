"""Test cases for JobScheduler."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from src.trading.infrastructure.jobs.job_scheduler import (
    JobScheduler,
    ScheduledTask,
    ScheduleType
)
from src.trading.infrastructure.jobs.job_queue import JobPriority


class TestScheduleType:
    """Test ScheduleType enum."""
    
    def test_schedule_type_values(self):
        """Test ScheduleType enum values."""
        assert ScheduleType.INTERVAL == "interval"
        assert ScheduleType.CRON == "cron"
        assert ScheduleType.ONCE == "once"


class TestScheduledTask:
    """Test ScheduledTask dataclass."""
    
    def test_create_interval_task(self):
        """Test creating interval-based task."""
        task = ScheduledTask(
            name="hourly_task",
            job_name="sync_data",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=3600
        )
        
        assert task.name == "hourly_task"
        assert task.job_name == "sync_data"
        assert task.schedule_type == ScheduleType.INTERVAL
        assert task.interval_seconds == 3600
        assert task.enabled is True
    
    def test_create_cron_task(self):
        """Test creating cron-based task."""
        task = ScheduledTask(
            name="daily_task",
            job_name="cleanup",
            schedule_type=ScheduleType.CRON,
            cron_expression="0 2 * * *"
        )
        
        assert task.schedule_type == ScheduleType.CRON
        assert task.cron_expression == "0 2 * * *"
    
    def test_create_once_task(self):
        """Test creating one-time task."""
        run_at = datetime(2024, 12, 25, 10, 0, 0, tzinfo=timezone.utc)
        
        task = ScheduledTask(
            name="one_time_task",
            job_name="special_event",
            schedule_type=ScheduleType.ONCE,
            run_at=run_at
        )
        
        assert task.schedule_type == ScheduleType.ONCE
        assert task.run_at == run_at
    
    def test_calculate_next_run_interval_first_time(self):
        """Test calculating next run for interval task (first time)."""
        with patch('src.trading.infrastructure.jobs.job_scheduler.datetime') as mock_datetime:
            base_time = datetime(2024, 1, 15, 12, 0, 0)
            mock_datetime.utcnow.return_value = base_time
            
            task = ScheduledTask(
                name="test_task",
                job_name="test_job",
                schedule_type=ScheduleType.INTERVAL,
                interval_seconds=300
            )
            
            next_run = task.calculate_next_run()
            
            assert next_run is not None
            # First run should be immediate (base_time)
            assert next_run == base_time
    
    def test_calculate_next_run_interval_after_run(self):
        """Test calculating next run for interval task after first run."""
        last_run = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        task = ScheduledTask(
            name="test_task",
            job_name="test_job",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=3600,
            last_run=last_run
        )
        
        next_run = task.calculate_next_run()
        
        assert next_run is not None
        assert next_run == last_run + timedelta(seconds=3600)
    
    def test_calculate_next_run_once_not_run(self):
        """Test calculating next run for once task (not run yet)."""
        run_at = datetime(2024, 12, 25, 10, 0, 0, tzinfo=timezone.utc)
        
        task = ScheduledTask(
            name="test_task",
            job_name="test_job",
            schedule_type=ScheduleType.ONCE,
            run_at=run_at
        )
        
        next_run = task.calculate_next_run()
        assert next_run == run_at
    
    def test_calculate_next_run_once_already_run(self):
        """Test calculating next run for once task (already run)."""
        run_at = datetime(2024, 12, 25, 10, 0, 0, tzinfo=timezone.utc)
        last_run = datetime(2024, 12, 25, 10, 5, 0, tzinfo=timezone.utc)
        
        task = ScheduledTask(
            name="test_task",
            job_name="test_job",
            schedule_type=ScheduleType.ONCE,
            run_at=run_at,
            last_run=last_run
        )
        
        next_run = task.calculate_next_run()
        assert next_run is None  # Should not run again
    
    def test_matches_cron_field_wildcard(self):
        """Test cron field matching with wildcard."""
        task = ScheduledTask(
            name="test",
            job_name="test_job",
            schedule_type=ScheduleType.CRON
        )
        
        assert task._matches_cron_field("*", 5, 0, 59) is True
        assert task._matches_cron_field("*", 0, 0, 23) is True
    
    def test_matches_cron_field_specific_value(self):
        """Test cron field matching with specific value."""
        task = ScheduledTask(
            name="test",
            job_name="test_job",
            schedule_type=ScheduleType.CRON
        )
        
        assert task._matches_cron_field("5", 5, 0, 59) is True
        assert task._matches_cron_field("5", 6, 0, 59) is False
    
    def test_matches_cron_field_range(self):
        """Test cron field matching with range."""
        task = ScheduledTask(
            name="test",
            job_name="test_job",
            schedule_type=ScheduleType.CRON
        )
        
        assert task._matches_cron_field("1-5", 3, 0, 59) is True
        assert task._matches_cron_field("1-5", 1, 0, 59) is True
        assert task._matches_cron_field("1-5", 5, 0, 59) is True
        assert task._matches_cron_field("1-5", 6, 0, 59) is False
    
    def test_matches_cron_field_step(self):
        """Test cron field matching with step."""
        task = ScheduledTask(
            name="test",
            job_name="test_job",
            schedule_type=ScheduleType.CRON
        )
        
        assert task._matches_cron_field("*/5", 0, 0, 59) is True
        assert task._matches_cron_field("*/5", 5, 0, 59) is True
        assert task._matches_cron_field("*/5", 10, 0, 59) is True
        assert task._matches_cron_field("*/5", 3, 0, 59) is False
    
    def test_matches_cron_field_list(self):
        """Test cron field matching with comma-separated list."""
        task = ScheduledTask(
            name="test",
            job_name="test_job",
            schedule_type=ScheduleType.CRON
        )
        
        assert task._matches_cron_field("1,3,5", 1, 0, 59) is True
        assert task._matches_cron_field("1,3,5", 3, 0, 59) is True
        assert task._matches_cron_field("1,3,5", 5, 0, 59) is True
        assert task._matches_cron_field("1,3,5", 2, 0, 59) is False


class TestJobScheduler:
    """Test JobScheduler implementation."""
    
    @pytest.fixture
    def scheduler(self):
        """Create JobScheduler instance."""
        return JobScheduler()
    
    def test_init(self, scheduler):
        """Test JobScheduler initialization."""
        assert scheduler.tasks == {}
        assert scheduler._running is False
        assert scheduler._check_interval == 30
    
    def test_register_interval_task(self, scheduler):
        """Test registering interval task."""
        task = scheduler.register(
            name="hourly_sync",
            job_name="sync_data",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=3600,
            priority=JobPriority.HIGH
        )
        
        assert task.name == "hourly_sync"
        assert task.job_name == "sync_data"
        assert task.interval_seconds == 3600
        assert "hourly_sync" in scheduler.tasks
    
    def test_register_cron_task(self, scheduler):
        """Test registering cron task."""
        task = scheduler.register(
            name="daily_cleanup",
            job_name="cleanup",
            schedule_type=ScheduleType.CRON,
            cron_expression="0 2 * * *",
            args={"deep": True}
        )
        
        assert task.cron_expression == "0 2 * * *"
        assert task.args == {"deep": True}
        assert "daily_cleanup" in scheduler.tasks
    
    def test_register_once_task(self, scheduler):
        """Test registering one-time task."""
        run_at = datetime(2024, 12, 25, 10, 0, 0, tzinfo=timezone.utc)
        
        task = scheduler.register(
            name="special_event",
            job_name="event_handler",
            schedule_type=ScheduleType.ONCE,
            run_at=run_at
        )
        
        assert task.run_at == run_at
        assert task.next_run == run_at
        assert "special_event" in scheduler.tasks
    
    def test_unregister_task(self, scheduler):
        """Test unregistering task."""
        scheduler.register(
            name="temp_task",
            job_name="temp_job",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=60
        )
        
        assert "temp_task" in scheduler.tasks
        
        result = scheduler.unregister("temp_task")
        assert result is True
        assert "temp_task" not in scheduler.tasks
    
    def test_unregister_nonexistent_task(self, scheduler):
        """Test unregistering non-existent task."""
        result = scheduler.unregister("nonexistent")
        assert result is False
    
    def test_enable_task(self, scheduler):
        """Test enabling disabled task."""
        task = scheduler.register(
            name="toggle_task",
            job_name="toggle_job",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=60,
            enabled=False
        )
        
        assert task.enabled is False
        
        result = scheduler.enable("toggle_task")
        assert result is True
        assert scheduler.tasks["toggle_task"].enabled is True
        assert scheduler.tasks["toggle_task"].next_run is not None
    
    def test_disable_task(self, scheduler):
        """Test disabling enabled task."""
        scheduler.register(
            name="toggle_task",
            job_name="toggle_job",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=60,
            enabled=True
        )
        
        result = scheduler.disable("toggle_task")
        assert result is True
        assert scheduler.tasks["toggle_task"].enabled is False
    
    def test_get_task(self, scheduler):
        """Test getting task by name."""
        scheduler.register(
            name="test_task",
            job_name="test_job",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=300
        )
        
        task = scheduler.get_task("test_task")
        assert task is not None
        assert task.name == "test_task"
    
    def test_get_nonexistent_task(self, scheduler):
        """Test getting non-existent task."""
        task = scheduler.get_task("nonexistent")
        assert task is None
    
    def test_get_all_tasks(self, scheduler):
        """Test getting all tasks."""
        scheduler.register(
            name="task1",
            job_name="job1",
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=60
        )
        scheduler.register(
            name="task2",
            job_name="job2",
            schedule_type=ScheduleType.CRON,
            cron_expression="0 * * * *"
        )
        
        tasks = scheduler.get_all_tasks()
        assert len(tasks) == 2
        assert any(t.name == "task1" for t in tasks)
        assert any(t.name == "task2" for t in tasks)
    
    @pytest.mark.asyncio
    async def test_start_scheduler(self, scheduler):
        """Test starting scheduler."""
        await scheduler.start()
        
        assert scheduler._running is True
        assert scheduler._scheduler_task is not None
        
        # Cleanup
        await scheduler.stop()
    
    @pytest.mark.asyncio
    async def test_stop_scheduler(self, scheduler):
        """Test stopping scheduler."""
        await scheduler.start()
        assert scheduler._running is True
        
        await scheduler.stop()
        
        assert scheduler._running is False
        assert scheduler._scheduler_task is None
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, scheduler):
        """Test starting already running scheduler."""
        await scheduler.start()
        task_before = scheduler._scheduler_task
        
        await scheduler.start()  # Should not create new task
        task_after = scheduler._scheduler_task
        
        assert task_before == task_after
        
        # Cleanup
        await scheduler.stop()
