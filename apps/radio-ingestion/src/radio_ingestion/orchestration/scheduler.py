"""Scheduler for periodic tasks (station refresh, captures)"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class ScheduledTask:
    """Represents a scheduled task"""

    def __init__(
        self, name: str, interval_seconds: float, callback: Callable, enabled: bool = True
    ):
        """
        Initialize scheduled task.

        Args:
            name: Task name for logging
            interval_seconds: Interval between executions
            callback: Async callback function
            enabled: Whether task is enabled
        """
        self.name = name
        self.interval_seconds = interval_seconds
        self.callback = callback
        self.enabled = enabled
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
        self.error_count = 0

    def update_next_run(self):
        """Update next run time"""
        if self.last_run:
            self.next_run = self.last_run + timedelta(seconds=self.interval_seconds)
        else:
            self.next_run = datetime.now(timezone.utc)

    async def execute(self) -> bool:
        """Execute the task"""
        if not self.enabled:
            return False

        try:
            logger.info("Executing scheduled task", task_name=self.name)
            await self.callback()

            self.last_run = datetime.now(timezone.utc)
            self.run_count += 1
            self.update_next_run()

            logger.info("Scheduled task completed", task_name=self.name, run_count=self.run_count)

            return True

        except Exception as e:
            self.error_count += 1
            logger.error(
                "Scheduled task failed",
                task_name=self.name,
                error=str(e),
                error_count=self.error_count,
            )
            return False


class TaskScheduler:
    """Scheduler for periodic tasks"""

    def __init__(self):
        """Initialize scheduler"""
        self.tasks: List[ScheduledTask] = []
        self.running = False
        self.scheduler_task: Optional[asyncio.Task] = None

        logger.info("Task scheduler initialized")

    def register_task(
        self, name: str, interval_seconds: float, callback: Callable, enabled: bool = True
    ) -> ScheduledTask:
        """
        Register a scheduled task.

        Args:
            name: Task name
            interval_seconds: Interval in seconds
            callback: Async callback function
            enabled: Whether enabled

        Returns:
            ScheduledTask instance
        """
        task = ScheduledTask(name, interval_seconds, callback, enabled)
        task.update_next_run()

        self.tasks.append(task)

        logger.info(
            "Task registered", task_name=name, interval_seconds=interval_seconds, enabled=enabled
        )

        return task

    def register_daily_task(
        self, name: str, callback: Callable, hour: int = 0, minute: int = 0, enabled: bool = True
    ) -> ScheduledTask:
        """
        Register a daily task at specific time.

        Args:
            name: Task name
            callback: Async callback function
            hour: Hour of day (0-23)
            minute: Minute (0-59)
            enabled: Whether enabled
        """
        # Calculate seconds until next run
        now = datetime.now(timezone.utc)
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if next_run <= now:
            # Already passed today, schedule for tomorrow
            next_run += timedelta(days=1)

        seconds_until_run = (next_run - now).total_seconds()

        # For daily tasks, we calculate interval after first run
        # Use a wrapper to reschedule for daily
        async def daily_wrapper():
            await callback()
            # Reschedule for next day
            task = self.get_task(name)
            if task:
                task.next_run = datetime.now(timezone.utc).replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                ) + timedelta(days=1)

        task = ScheduledTask(name, seconds_until_run, daily_wrapper, enabled)  # Initial delay
        task.next_run = next_run

        self.tasks.append(task)

        logger.info(
            "Daily task registered",
            task_name=name,
            hour=hour,
            minute=minute,
            next_run=next_run.isoformat(),
        )

        return task

    def get_task(self, name: str) -> Optional[ScheduledTask]:
        """Get task by name"""
        return next((t for t in self.tasks if t.name == name), None)

    async def scheduler_loop(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started", task_count=len(self.tasks))

        while self.running:
            try:
                now = datetime.now(timezone.utc)

                # Check each task
                for task in self.tasks:
                    if not task.enabled:
                        continue

                    # Initialize next_run if not set
                    if task.next_run is None:
                        task.update_next_run()

                    # Check if it's time to run
                    if now >= task.next_run:
                        asyncio.create_task(task.execute())

                # Sleep for a short interval before checking again
                await asyncio.sleep(60.0)  # Check every minute

            except Exception as e:
                logger.error("Scheduler loop error", error=str(e))
                await asyncio.sleep(60.0)

    async def start(self):
        """Start scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        self.scheduler_task = asyncio.create_task(self.scheduler_loop())

        logger.info("Scheduler started")

    async def stop(self, timeout: float = 10.0):
        """Stop scheduler"""
        if not self.running:
            return

        self.running = False

        if self.scheduler_task:
            await asyncio.wait_for(self.scheduler_task, timeout=timeout)

        logger.info("Scheduler stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        return {
            "running": self.running,
            "task_count": len(self.tasks),
            "tasks": [
                {
                    "name": task.name,
                    "enabled": task.enabled,
                    "interval_seconds": task.interval_seconds,
                    "run_count": task.run_count,
                    "error_count": task.error_count,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                }
                for task in self.tasks
            ],
        }


class BackpressureController:
    """Manages backpressure based on queue sizes and processing rates"""

    def __init__(
        self,
        asr_backlog_threshold: int = 100,
        asr_backlog_warning: int = 50,
        min_capture_duration: int = 60,
        max_capture_duration: int = 180,
        reduction_factor: float = 0.5,
    ):
        """
        Initialize backpressure controller.

        Args:
            asr_backlog_threshold: Reduce capture when ASR backlog exceeds this
            asr_backlog_warning: Log warning when ASR backlog exceeds this
            min_capture_duration: Minimum capture duration (seconds)
            max_capture_duration: Maximum capture duration (seconds)
            reduction_factor: Factor to reduce capture duration (0.0-1.0)
        """
        self.asr_backlog_threshold = asr_backlog_threshold
        self.asr_backlog_warning = asr_backlog_warning
        self.min_capture_duration = min_capture_duration
        self.max_capture_duration = max_capture_duration
        self.reduction_factor = reduction_factor

        self.current_capture_duration = max_capture_duration
        self.asr_backlog_size = 0

        logger.info(
            "Backpressure controller initialized",
            asr_backlog_threshold=asr_backlog_threshold,
            min_duration=min_capture_duration,
            max_duration=max_capture_duration,
        )

    def update_asr_backlog(self, backlog_size: int):
        """Update ASR backlog size"""
        self.asr_backlog_size = backlog_size

        if backlog_size >= self.asr_backlog_threshold:
            # Reduce capture duration
            new_duration = max(
                self.min_capture_duration,
                int(self.current_capture_duration * self.reduction_factor),
            )

            if new_duration < self.current_capture_duration:
                logger.warning(
                    "Reducing capture duration due to ASR backlog",
                    backlog_size=backlog_size,
                    old_duration=self.current_capture_duration,
                    new_duration=new_duration,
                )
                self.current_capture_duration = new_duration

        elif backlog_size >= self.asr_backlog_warning:
            logger.warning(
                "ASR backlog warning",
                backlog_size=backlog_size,
                threshold=self.asr_backlog_threshold,
            )

        elif backlog_size < self.asr_backlog_warning:
            # Backlog reduced, restore capture duration
            if self.current_capture_duration < self.max_capture_duration:
                self.current_capture_duration = self.max_capture_duration
                logger.info("Restored capture duration", duration=self.current_capture_duration)

    def get_capture_duration(self) -> int:
        """Get current capture duration (adjusted for backpressure)"""
        return self.current_capture_duration

    def get_status(self) -> Dict[str, Any]:
        """Get backpressure status"""
        return {
            "asr_backlog_size": self.asr_backlog_size,
            "current_capture_duration": self.current_capture_duration,
            "backpressure_active": self.current_capture_duration < self.max_capture_duration,
        }
