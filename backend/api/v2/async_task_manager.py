"""
异步任务管理器，用于处理长时间运行的AI推理任务
支持任务创建、状态查询和结果获取
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel
import logging
import threading
import concurrent.futures
import time

logger = logging.getLogger(__name__)

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: int = 0  # 0-100

class AsyncTaskManager:
    """异步任务管理器，管理长时间运行的后台任务"""

    def __init__(self, max_workers: int = 5, cleanup_interval: int = 3600):
        self.tasks: Dict[str, TaskResult] = {}
        self.max_workers = max_workers
        self.cleanup_interval = cleanup_interval
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._cleanup_task = None
        self._lock = threading.Lock()

    async def start_cleanup_task(self):
        """启动定期清理任务"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def _periodic_cleanup(self):
        """定期清理过期任务"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_old_tasks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理任务失败: {e}")

    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理超过指定时间的已完成任务"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        with self._lock:
            to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and
                    task.completed_at and task.completed_at < cutoff_time):
                    to_remove.append(task_id)

            for task_id in to_remove:
                del self.tasks[task_id]
                logger.info(f"清理过期任务: {task_id}")

    def submit_task(self, func: Callable, *args, **kwargs) -> str:
        """提交一个同步函数作为异步任务执行"""
        task_id = f"task_{uuid.uuid4()}"

        # 创建任务记录
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )

        with self._lock:
            self.tasks[task_id] = task_result

        # 提交任务到线程池
        future = self.executor.submit(self._execute_task, task_id, func, *args, **kwargs)

        logger.info(f"任务已提交: {task_id}")
        return task_id

    def _execute_task(self, task_id: str, func: Callable, *args, **kwargs):
        """在线程池中执行任务"""
        task_start_time = time.time()
        try:
            with self._lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = TaskStatus.RUNNING
                    self.tasks[task_id].started_at = datetime.now()

            logger.info(f"开始执行任务: {task_id}")

            # 执行实际的任务函数
            func_start_time = time.time()
            result = func(*args, **kwargs)
            func_duration = time.time() - func_start_time

            task_total_duration = time.time() - task_start_time

            with self._lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = TaskStatus.COMPLETED
                    self.tasks[task_id].result = result
                    self.tasks[task_id].completed_at = datetime.now()
                    self.tasks[task_id].progress = 100

            logger.info(f"任务执行成功: {task_id}, 总耗时: {task_total_duration:.2f}秒 (函数执行: {func_duration:.2f}秒)")

        except Exception as e:
            task_total_duration = time.time() - task_start_time
            error_msg = str(e)
            logger.error(f"任务执行失败 {task_id}: {error_msg}, 耗时: {task_total_duration:.2f}秒")

            with self._lock:
                if task_id in self.tasks:
                    self.tasks[task_id].status = TaskStatus.FAILED
                    self.tasks[task_id].error = error_msg
                    self.tasks[task_id].completed_at = datetime.now()

    def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """获取任务状态"""
        with self._lock:
            return self.tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, TaskResult]:
        """获取所有任务状态"""
        with self._lock:
            return self.tasks.copy()

    def cancel_task(self, task_id: str) -> bool:
        """取消任务（只能取消还未开始的任务）"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.FAILED
                task.error = "任务已取消"
                task.completed_at = datetime.now()
                return True
            return False

    async def wait_for_task(self, task_id: str, timeout: float = 300) -> Optional[TaskResult]:
        """等待任务完成（带超时）"""
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < timeout:
            task = self.get_task_status(task_id)
            if task and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                return task
            await asyncio.sleep(1)  # 每秒检查一次

        return None  # 超时

    def shutdown(self):
        """关闭任务管理器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        self.executor.shutdown(wait=True)

# 全局任务管理器实例
task_manager = AsyncTaskManager()