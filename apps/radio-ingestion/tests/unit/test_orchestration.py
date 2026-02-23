"""Unit tests for orchestration module"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from radio_ingestion.orchestration.scheduler import (
    BackpressureController,
    ScheduledTask,
    TaskScheduler,
)
from radio_ingestion.orchestration.task_queue import (
    PipelineProcessor,
    ShardTask,
    TaskQueue,
    TaskState,
)


class TestTaskQueue:
    """Test TaskQueue"""

    @pytest.fixture
    def queue(self):
        """Create task queue"""
        return TaskQueue(max_size=10)

    def test_init(self, queue):
        """Test queue initialization"""
        assert queue.max_size == 10
        assert len(queue.tasks) == 0

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self, queue):
        """Test enqueue and dequeue"""
        task = ShardTask(shard_id=1, source_id=1, local_path="/test/path.wav")

        success = await queue.enqueue(task)
        assert success is True

        dequeued = await queue.dequeue(timeout=1.0)
        assert dequeued is not None
        assert dequeued.shard_id == 1

    @pytest.mark.asyncio
    async def test_enqueue_duplicate(self, queue):
        """Test enqueueing duplicate task"""
        task = ShardTask(shard_id=1, source_id=1, local_path="/test.wav")

        await queue.enqueue(task)
        success = await queue.enqueue(task)  # Try again

        assert success is False

    def test_get_task(self, queue):
        """Test getting task by ID"""
        task = ShardTask(shard_id=1, source_id=1, local_path="/test.wav")
        queue.tasks[1] = task

        retrieved = queue.get_task(1)
        assert retrieved is not None
        assert retrieved.shard_id == 1

    def test_update_task_state(self, queue):
        """Test updating task state"""
        task = ShardTask(shard_id=1, source_id=1, local_path="/test.wav")
        queue.tasks[1] = task

        success = queue.update_task_state(1, TaskState.PREFILTERED)

        assert success is True
        assert task.state == TaskState.PREFILTERED

    def test_get_tasks_by_state(self, queue):
        """Test getting tasks by state"""
        task1 = ShardTask(
            shard_id=1, source_id=1, local_path="/test1.wav", state=TaskState.CAPTURED
        )
        task2 = ShardTask(
            shard_id=2, source_id=1, local_path="/test2.wav", state=TaskState.PREFILTERED
        )
        task3 = ShardTask(
            shard_id=3, source_id=1, local_path="/test3.wav", state=TaskState.CAPTURED
        )

        queue.tasks = {1: task1, 2: task2, 3: task3}

        captured = queue.get_tasks_by_state(TaskState.CAPTURED)
        assert len(captured) == 2
        assert all(t.state == TaskState.CAPTURED for t in captured)

    def test_get_queue_stats(self, queue):
        """Test queue statistics"""
        task = ShardTask(shard_id=1, source_id=1, local_path="/test.wav", state=TaskState.CAPTURED)
        queue.tasks[1] = task

        stats = queue.get_queue_stats()

        assert "queue_size" in stats
        assert "total_tasks" in stats
        assert "by_state" in stats
        assert stats["total_tasks"] == 1


class TestShardTask:
    """Test ShardTask"""

    def test_transition_to(self):
        """Test state transition"""
        task = ShardTask(shard_id=1, source_id=1, local_path="/test.wav")

        task.transition_to(TaskState.PREFILTERED)

        assert task.state == TaskState.PREFILTERED
        assert task.updated_at is not None

    def test_transition_with_error(self):
        """Test state transition with error"""
        task = ShardTask(shard_id=1, source_id=1, local_path="/test.wav")

        task.transition_to(TaskState.FAILED, error="Test error")

        assert task.state == TaskState.FAILED
        assert task.error == "Test error"


class TestPipelineProcessor:
    """Test PipelineProcessor"""

    @pytest.fixture
    def queue(self):
        """Create task queue"""
        return TaskQueue(max_size=10)

    @pytest.fixture
    def processor(self, queue):
        """Create processor"""
        return PipelineProcessor(task_queue=queue)

    @pytest.mark.asyncio
    async def test_process_task_state_machine(self, processor):
        """Test task processing through states"""
        task = ShardTask(shard_id=1, source_id=1, local_path="/test.wav", state=TaskState.CAPTURED)

        # Mock callbacks
        prefilter_called = []

        async def mock_prefilter(t):
            prefilter_called.append(t.shard_id)

        processor.prefilter_callback = mock_prefilter

        await processor.process_task(task)

        assert task.state in [TaskState.PREFILTERED, TaskState.LID_DONE, TaskState.QUEUED_ASR]
        assert len(prefilter_called) > 0

    @pytest.mark.asyncio
    async def test_start_stop(self, processor):
        """Test starting and stopping processor"""
        await processor.start(num_workers=2)
        assert processor.running is True
        assert len(processor.workers) == 2

        await processor.stop()
        assert processor.running is False


class TestTaskScheduler:
    """Test TaskScheduler"""

    def test_init(self):
        """Test scheduler initialization"""
        scheduler = TaskScheduler()
        assert len(scheduler.tasks) == 0
        assert scheduler.running is False

    def test_register_task(self):
        """Test registering a task"""
        scheduler = TaskScheduler()

        async def mock_callback():
            pass

        task = scheduler.register_task(
            name="test_task", interval_seconds=3600.0, callback=mock_callback
        )

        assert task.name == "test_task"
        assert task.interval_seconds == 3600.0
        assert task in scheduler.tasks

    def test_register_daily_task(self):
        """Test registering a daily task"""
        scheduler = TaskScheduler()

        async def mock_callback():
            pass

        task = scheduler.register_daily_task(
            name="daily_refresh", callback=mock_callback, hour=2, minute=0
        )

        assert task.name == "daily_refresh"
        assert task in scheduler.tasks

    def test_get_task(self):
        """Test getting task by name"""
        scheduler = TaskScheduler()

        async def mock_callback():
            pass

        scheduler.register_task("test", 3600.0, mock_callback)

        task = scheduler.get_task("test")
        assert task is not None
        assert task.name == "test"

    def test_get_stats(self):
        """Test getting scheduler statistics"""
        scheduler = TaskScheduler()

        async def mock_callback():
            pass

        scheduler.register_task("test", 3600.0, mock_callback)

        stats = scheduler.get_stats()

        assert stats["running"] is False
        assert stats["task_count"] == 1
        assert len(stats["tasks"]) == 1


class TestBackpressureController:
    """Test BackpressureController"""

    def test_init(self):
        """Test controller initialization"""
        controller = BackpressureController()
        assert controller.current_capture_duration == 180  # max_capture_duration
        assert controller.asr_backlog_size == 0

    def test_update_asr_backlog_below_threshold(self):
        """Test backlog update below threshold"""
        controller = BackpressureController(asr_backlog_threshold=100, max_capture_duration=180)

        controller.update_asr_backlog(50)

        assert controller.get_capture_duration() == 180  # No reduction

    def test_update_asr_backlog_above_threshold(self):
        """Test backlog update above threshold"""
        controller = BackpressureController(
            asr_backlog_threshold=100,
            max_capture_duration=180,
            min_capture_duration=60,
            reduction_factor=0.5,
        )

        controller.update_asr_backlog(150)

        # Should reduce by 50%: 180 * 0.5 = 90
        assert controller.get_capture_duration() == 90

    def test_update_asr_backlog_recovery(self):
        """Test backlog recovery"""
        controller = BackpressureController(asr_backlog_threshold=100, max_capture_duration=180)

        # Trigger backpressure
        controller.update_asr_backlog(150)
        assert controller.get_capture_duration() < 180

        # Recover
        controller.update_asr_backlog(30)
        assert controller.get_capture_duration() == 180  # Restored

    def test_get_status(self):
        """Test getting status"""
        controller = BackpressureController()
        controller.update_asr_backlog(150)

        status = controller.get_status()

        assert "asr_backlog_size" in status
        assert "current_capture_duration" in status
        assert "backpressure_active" in status
