"""Integration tests for orchestration"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from mumbl_storage.db import DatabaseConfig, get_connection
from radio_ingestion.config import RadioIngestionConfig
from radio_ingestion.orchestration.scheduler import BackpressureController, TaskScheduler
from radio_ingestion.orchestration.task_queue import ShardTask, TaskQueue, TaskState
from radio_ingestion.service import RadioIngestionService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_task_queue_integration():
    """Test task queue with multiple tasks"""
    queue = TaskQueue(max_size=10)

    # Enqueue multiple tasks
    for i in range(5):
        task = ShardTask(shard_id=i + 1, source_id=1, local_path=f"/test/path{i}.wav")
        await queue.enqueue(task)

    # Dequeue and verify
    dequeued_count = 0
    while True:
        task = await queue.dequeue(timeout=0.1)
        if task is None:
            break
        dequeued_count += 1

    assert dequeued_count == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scheduler_task_execution():
    """Test scheduler executes tasks"""
    scheduler = TaskScheduler()

    execution_count = 0

    async def test_callback():
        nonlocal execution_count
        execution_count += 1

    scheduler.register_task(
        name="test_task", interval_seconds=1.0, callback=test_callback  # Run every second for test
    )

    # Start scheduler
    await scheduler.start()

    # Wait for task to execute
    await asyncio.sleep(2.0)

    # Stop scheduler
    await scheduler.stop()

    # Task should have executed at least once
    assert execution_count > 0


@pytest.mark.integration
def test_backpressure_controller():
    """Test backpressure controller logic"""
    controller = BackpressureController(
        asr_backlog_threshold=50,
        max_capture_duration=180,
        min_capture_duration=60,
        reduction_factor=0.5,
    )

    # No backpressure initially
    assert controller.get_capture_duration() == 180

    # Trigger backpressure
    controller.update_asr_backlog(100)
    assert controller.get_capture_duration() < 180

    # Reduce further
    controller.update_asr_backlog(200)
    assert controller.get_capture_duration() >= 60  # Min duration

    # Recover
    controller.update_asr_backlog(20)
    assert controller.get_capture_duration() == 180


@pytest.mark.integration
@pytest.mark.asyncio
async def test_service_health_check():
    """Test service health check"""
    try:
        config = DatabaseConfig.from_env()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")

    service = RadioIngestionService()

    # Health check should work even if service not fully started
    health = await service.health_check()

    assert "status" in health
    assert "timestamp" in health
    assert "components" in health
    assert "database" in health["components"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_task_state_transitions():
    """Test task state machine transitions"""
    queue = TaskQueue()

    task = ShardTask(shard_id=1, source_id=1, local_path="/test.wav", state=TaskState.CAPTURED)

    await queue.enqueue(task)

    # Transition through states
    queue.update_task_state(1, TaskState.PREFILTERED)
    assert task.state == TaskState.PREFILTERED

    queue.update_task_state(1, TaskState.LID_DONE)
    assert task.state == TaskState.LID_DONE

    queue.update_task_state(1, TaskState.QUEUED_ASR)
    assert task.state == TaskState.QUEUED_ASR

    queue.update_task_state(1, TaskState.COMPLETED)
    assert task.state == TaskState.COMPLETED
