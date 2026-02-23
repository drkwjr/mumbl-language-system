"""Scheduler for managing concurrent stream captures"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog
from radio_ingestion.capture.stream_recorder import StreamRecorder

logger = structlog.get_logger(__name__)


class CaptureTaskStatus(Enum):
    """Status of a capture task"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CaptureTask:
    """Represents a capture task"""

    source_id: int
    stream_url: str
    station_name: str
    duration: int
    status: CaptureTaskStatus = CaptureTaskStatus.PENDING
    output_path: Optional[str] = None
    file_size: int = 0
    error: Optional[str] = None
    error_code: Optional[int] = None
    error_kind: Optional[str] = None
    error_detail: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3


class CaptureScheduler:
    """Manages concurrent stream captures with rate limiting"""

    def __init__(
        self,
        recorder: StreamRecorder,
        max_concurrent: int = 5,
        completion_callback: Optional[Callable[[CaptureTask], None]] = None,
    ):
        """
        Initialize capture scheduler.

        Args:
            recorder: StreamRecorder instance
            max_concurrent: Maximum concurrent captures
            completion_callback: Optional callback when task completes
        """
        self.recorder = recorder
        self.max_concurrent = max_concurrent
        self.completion_callback = completion_callback

        self.tasks: Dict[int, CaptureTask] = {}
        self.running_tasks: Dict[int, asyncio.Task] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def schedule_capture(
        self,
        source_id: int,
        stream_url: str,
        station_name: str,
        duration: int,
        max_retries: int = 3,
    ) -> CaptureTask:
        """
        Schedule a capture task.

        Args:
            source_id: Source ID from database
            stream_url: Stream URL to capture
            station_name: Station name for logging
            duration: Capture duration in seconds
            max_retries: Maximum retry attempts

        Returns:
            CaptureTask object
        """
        task = CaptureTask(
            source_id=source_id,
            stream_url=stream_url,
            station_name=station_name,
            duration=duration,
            max_retries=max_retries,
        )

        self.tasks[source_id] = task

        # Start capture asynchronously
        asyncio.create_task(self._execute_capture(task))

        return task

    async def _execute_capture(self, task: CaptureTask):
        """Execute a capture task with concurrency control"""
        async with self.semaphore:
            task.status = CaptureTaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)

            logger.info(
                "Starting capture task",
                source_id=task.source_id,
                station_name=task.station_name,
                duration=task.duration,
            )

            try:
                # Run ffmpeg in executor (blocking I/O)
                loop = asyncio.get_event_loop()
                output_name = f"source_{task.source_id}_{int(time.time())}.wav"
                result = await loop.run_in_executor(
                    None,
                    self.recorder.record_stream,
                    task.stream_url,
                    task.duration,
                    output_name,
                    True,  # reconnect
                    task.max_retries,
                    2.0,  # retry_delay
                )

                if result["success"]:
                    task.status = CaptureTaskStatus.COMPLETED
                    task.output_path = result["path"]
                    task.file_size = result["file_size"]

                    logger.info(
                        "Capture task completed",
                        source_id=task.source_id,
                        output_path=task.output_path,
                        file_size=task.file_size,
                    )
                else:
                    task.status = CaptureTaskStatus.FAILED
                    task.error = result["error"]
                    task.error_code = result.get("error_code")
                    task.error_kind = result.get("error_kind")
                    task.error_detail = result.get("error_detail")
                    task.retry_count += 1

                    logger.warning(
                        "Capture task failed",
                        source_id=task.source_id,
                        error=task.error,
                        error_kind=task.error_kind,
                        error_code=task.error_code,
                        retry_count=task.retry_count,
                    )

            except Exception as e:
                task.status = CaptureTaskStatus.FAILED
                task.error = str(e)

                logger.error("Capture task exception", source_id=task.source_id, error=str(e))

            finally:
                task.completed_at = datetime.now(timezone.utc)

                # Call completion callback if provided
                if self.completion_callback:
                    try:
                        self.completion_callback(task)
                    except Exception as e:
                        logger.error(
                            "Completion callback failed", source_id=task.source_id, error=str(e)
                        )

                # Clean up running task
                if task.source_id in self.running_tasks:
                    del self.running_tasks[task.source_id]

    def get_task_status(self, source_id: int) -> Optional[CaptureTask]:
        """Get status of a capture task"""
        return self.tasks.get(source_id)

    def get_active_tasks(self) -> List[CaptureTask]:
        """Get list of active (pending or running) tasks"""
        return [
            task
            for task in self.tasks.values()
            if task.status in [CaptureTaskStatus.PENDING, CaptureTaskStatus.RUNNING]
        ]

    def get_completed_tasks(self) -> List[CaptureTask]:
        """Get list of completed tasks"""
        return [task for task in self.tasks.values() if task.status == CaptureTaskStatus.COMPLETED]

    def get_failed_tasks(self) -> List[CaptureTask]:
        """Get list of failed tasks"""
        return [task for task in self.tasks.values() if task.status == CaptureTaskStatus.FAILED]

    async def wait_for_completion(self, timeout: Optional[float] = None):
        """Wait for all active tasks to complete"""
        active_tasks = self.get_active_tasks()

        if not active_tasks:
            return

        start_time = time.time()

        while active_tasks:
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(
                    "Wait for completion timed out",
                    timeout=timeout,
                    remaining_tasks=len(active_tasks),
                )
                break

            # Wait a bit before checking again
            await asyncio.sleep(1.0)

            active_tasks = self.get_active_tasks()

        logger.info(
            "All tasks completed or timed out",
            completed=len(self.get_completed_tasks()),
            failed=len(self.get_failed_tasks()),
        )
