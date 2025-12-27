"""Task queue system for radio ingestion pipeline"""

import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timezone
from collections import deque
import structlog

logger = structlog.get_logger(__name__)


class TaskState(Enum):
    """Task processing states"""
    DISCOVERED = "discovered"
    CAPTURED = "captured"
    PREFILTERED = "prefiltered"
    LID_DONE = "lid_done"
    QUEUED_ASR = "queued_asr"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class ShardTask:
    """Represents a shard processing task"""
    shard_id: int
    source_id: int
    local_path: str
    state: TaskState = TaskState.DISCOVERED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Processing metadata
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # State transition callbacks
    on_state_change: Optional[Callable[['ShardTask'], None]] = None
    
    def transition_to(self, new_state: TaskState, error: Optional[str] = None):
        """Transition task to new state"""
        old_state = self.state
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
        
        if error:
            self.error = error
        
        logger.debug(
            "Task state transition",
            shard_id=self.shard_id,
            old_state=old_state.value,
            new_state=new_state.value,
            error=error
        )
        
        if self.on_state_change:
            try:
                self.on_state_change(self)
            except Exception as e:
                logger.error(
                    "State change callback failed",
                    shard_id=self.shard_id,
                    error=str(e)
                )


class TaskQueue:
    """Async task queue for shard processing pipeline"""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize task queue.
        
        Args:
            max_size: Maximum queue size (blocks when full)
        """
        self.queue = asyncio.Queue(maxsize=max_size)
        self.tasks: Dict[int, ShardTask] = {}  # shard_id -> task
        self.max_size = max_size
        
        logger.info("Task queue initialized", max_size=max_size)
    
    async def enqueue(self, task: ShardTask) -> bool:
        """
        Enqueue a task.
        
        Args:
            task: ShardTask to enqueue
        
        Returns:
            True if enqueued, False if queue is full
        """
        if task.shard_id in self.tasks:
            logger.warning(
                "Task already in queue",
                shard_id=task.shard_id,
                state=task.state.value
            )
            return False
        
        try:
            await asyncio.wait_for(self.queue.put(task), timeout=1.0)
            self.tasks[task.shard_id] = task
            
            logger.info(
                "Task enqueued",
                shard_id=task.shard_id,
                state=task.state.value,
                queue_size=self.queue.qsize()
            )
            
            return True
            
        except asyncio.TimeoutError:
            logger.error(
                "Queue full, failed to enqueue",
                shard_id=task.shard_id,
                queue_size=self.queue.qsize()
            )
            return False
    
    async def dequeue(self, timeout: Optional[float] = None) -> Optional[ShardTask]:
        """
        Dequeue a task.
        
        Args:
            timeout: Timeout in seconds (None for no timeout)
        
        Returns:
            ShardTask or None if timeout
        """
        try:
            if timeout is not None:
                task = await asyncio.wait_for(self.queue.get(), timeout=timeout)
            else:
                task = await self.queue.get()
            
            logger.debug(
                "Task dequeued",
                shard_id=task.shard_id,
                state=task.state.value
            )
            
            return task
            
        except asyncio.TimeoutError:
            return None
    
    def get_task(self, shard_id: int) -> Optional[ShardTask]:
        """Get task by shard ID"""
        return self.tasks.get(shard_id)
    
    def update_task_state(
        self,
        shard_id: int,
        new_state: TaskState,
        error: Optional[str] = None
    ) -> bool:
        """Update task state"""
        task = self.tasks.get(shard_id)
        if not task:
            logger.warning("Task not found for state update", shard_id=shard_id)
            return False
        
        task.transition_to(new_state, error)
        return True
    
    def get_tasks_by_state(self, state: TaskState) -> List[ShardTask]:
        """Get all tasks in a specific state"""
        return [task for task in self.tasks.values() if task.state == state]
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            "queue_size": self.queue.qsize(),
            "total_tasks": len(self.tasks),
            "by_state": {
                state.value: len(self.get_tasks_by_state(state))
                for state in TaskState
            }
        }
    
    def clear_completed(self, max_age_hours: int = 24):
        """Clear completed/failed tasks older than max_age_hours"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        
        to_remove = []
        for task in self.tasks.values():
            if task.state in [TaskState.COMPLETED, TaskState.FAILED]:
                if task.updated_at.timestamp() < cutoff_time:
                    to_remove.append(task.shard_id)
        
        for shard_id in to_remove:
            del self.tasks[shard_id]
        
        if to_remove:
            logger.info(
                "Cleared old tasks",
                count=len(to_remove),
                max_age_hours=max_age_hours
            )
        
        return len(to_remove)


class PipelineProcessor:
    """
    Process shard tasks through the pipeline.
    
    States: DISCOVERED → CAPTURED → PREFILTERED → LID_DONE → QUEUED_ASR → COMPLETED
    """
    
    def __init__(
        self,
        task_queue: TaskQueue,
        capture_callback: Optional[Callable[[ShardTask], Any]] = None,
        prefilter_callback: Optional[Callable[[ShardTask], Any]] = None,
        lid_callback: Optional[Callable[[ShardTask], Any]] = None,
        asr_callback: Optional[Callable[[ShardTask], Any]] = None
    ):
        """
        Initialize pipeline processor.
        
        Args:
            task_queue: Task queue instance
            capture_callback: Callback for capture stage
            prefilter_callback: Callback for prefilter stage
            lid_callback: Callback for LID stage
            asr_callback: Callback for ASR queueing stage
        """
        self.task_queue = task_queue
        self.capture_callback = capture_callback
        self.prefilter_callback = prefilter_callback
        self.lid_callback = lid_callback
        self.asr_callback = asr_callback
        
        self.running = False
        self.workers: List[asyncio.Task] = []
        
        logger.info("Pipeline processor initialized")
    
    async def process_task(self, task: ShardTask):
        """Process a single task through the pipeline"""
        try:
            # Process based on current state
            # DISCOVERED means shard was created but not yet processed
            # We start processing from CAPTURED state (assuming capture already done)
            
            if task.state == TaskState.CAPTURED:
                if self.prefilter_callback:
                    await self._run_callback(self.prefilter_callback, task)
                task.transition_to(TaskState.PREFILTERED)
            
            if task.state == TaskState.PREFILTERED:
                if self.lid_callback:
                    await self._run_callback(self.lid_callback, task)
                task.transition_to(TaskState.LID_DONE)
            
            if task.state == TaskState.LID_DONE:
                if self.asr_callback:
                    await self._run_callback(self.asr_callback, task)
                task.transition_to(TaskState.QUEUED_ASR)
            
            if task.state == TaskState.QUEUED_ASR:
                task.transition_to(TaskState.COMPLETED)
                
        except Exception as e:
            logger.error(
                "Task processing failed",
                shard_id=task.shard_id,
                state=task.state.value,
                error=str(e)
            )
            task.transition_to(TaskState.FAILED, error=str(e))
    
    async def _run_callback(
        self,
        callback: Callable,
        task: ShardTask
    ):
        """Run a callback and handle errors"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(task)
            else:
                callback(task)
        except Exception as e:
            logger.error(
                "Pipeline callback failed",
                shard_id=task.shard_id,
                callback=callback.__name__ if hasattr(callback, '__name__') else str(callback),
                error=str(e)
            )
            raise
    
    async def worker(self, worker_id: int):
        """Worker coroutine that processes tasks from queue"""
        logger.info("Pipeline worker started", worker_id=worker_id)
        
        while self.running:
            try:
                task = await self.task_queue.dequeue(timeout=1.0)
                
                if task:
                    await self.process_task(task)
                    
            except Exception as e:
                logger.error(
                    "Worker error",
                    worker_id=worker_id,
                    error=str(e)
                )
                await asyncio.sleep(1.0)
    
    async def start(self, num_workers: int = 2):
        """Start processing workers"""
        if self.running:
            logger.warning("Processor already running")
            return
        
        self.running = True
        self.workers = [
            asyncio.create_task(self.worker(i))
            for i in range(num_workers)
        ]
        
        logger.info("Pipeline processor started", num_workers=num_workers)
    
    async def stop(self, timeout: float = 10.0):
        """Stop processing workers"""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for workers to finish current tasks
        await asyncio.wait(self.workers, timeout=timeout)
        
        logger.info("Pipeline processor stopped")

