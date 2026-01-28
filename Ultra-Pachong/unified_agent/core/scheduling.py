"""
调度模块 - 任务编排、并发控制与流量管理

核心功能:
1. 任务队列管理 (优先级队列、FIFO/LIFO、延迟任务)
2. 速率限制器 (令牌桶、滑动窗口)
3. 并发控制器 (Semaphore、动态调整)
4. 失败重试队列 (指数退避、智能重试)
5. 批量任务调度器 (批量处理、进度追踪)

作者: Ultra Pachong Team
文档: unified_agent/skills/07-scheduling.md
"""

from __future__ import annotations

import asyncio
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, List, Dict, Awaitable, TypeVar, Generic
from enum import Enum
from collections import deque
import heapq

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ==================== 任务状态定义 ====================

class TaskPriority(int, Enum):
    """任务优先级"""
    CRITICAL = 0   # 最高优先级
    HIGH = 1
    NORMAL = 2
    LOW = 3
    IDLE = 4       # 空闲时执行


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"


# ==================== 任务数据类型 ====================

@dataclass
class Task(Generic[T]):
    """调度任务"""
    id: str
    func: Callable[..., Awaitable[T]]
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[T] = None
    error: Optional[Exception] = None
    retries: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    delay: float = 0  # 延迟执行(秒)
    timeout: Optional[float] = None

    def __lt__(self, other):
        """优先级比较（用于堆排序）"""
        return self.priority.value < other.priority.value

    @property
    def duration_ms(self) -> Optional[float]:
        """执行时长（毫秒）"""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds() * 1000
        return None


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    retries: int = 0


# ==================== 速率限制器 ====================

class RateLimiter(ABC):
    """速率限制器基类"""

    @abstractmethod
    async def acquire(self, tokens: int = 1) -> bool:
        """获取令牌"""
        raise NotImplementedError

    @abstractmethod
    def reset(self):
        """重置限流器"""
        raise NotImplementedError


class TokenBucketLimiter(RateLimiter):
    """令牌桶限流器

    算法:
    - 以固定速率生成令牌
    - 桶有最大容量
    - 请求消耗令牌，无令牌则等待
    """

    def __init__(self, rate: float, capacity: int):
        """
        初始化令牌桶

        Args:
            rate: 每秒生成的令牌数
            capacity: 桶的最大容量（允许突发）
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

        logger.info(f"[TokenBucket] Initialized: rate={rate}/s, capacity={capacity}")

    async def acquire(self, tokens: int = 1) -> bool:
        """
        获取令牌

        Args:
            tokens: 需要的令牌数

        Returns:
            是否成功获取
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update

            # 补充令牌
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            # 需要等待
            wait_time = (tokens - self.tokens) / self.rate
            logger.debug(f"[TokenBucket] Waiting {wait_time:.3f}s for {tokens} tokens")
            await asyncio.sleep(wait_time)

            self.tokens = max(0, self.tokens - tokens)
            self.last_update = time.monotonic()

            return True

    def reset(self):
        """重置令牌桶"""
        self.tokens = float(self.capacity)
        self.last_update = time.monotonic()
        logger.info("[TokenBucket] Reset")


class SlidingWindowLimiter(RateLimiter):
    """滑动窗口限流器

    算法:
    - 固定时间窗口内限制请求数
    - 窗口滑动，自动清理过期请求
    """

    def __init__(self, max_requests: int, window_seconds: float):
        """
        初始化滑动窗口

        Args:
            max_requests: 窗口内最大请求数
            window_seconds: 窗口时长(秒)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self._lock = asyncio.Lock()

        logger.info(
            f"[SlidingWindow] Initialized: "
            f"max={max_requests} requests/{window_seconds}s"
        )

    async def acquire(self, tokens: int = 1) -> bool:
        """获取请求许可"""
        async with self._lock:
            now = time.monotonic()

            # 清理过期请求
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()

            if len(self.requests) + tokens <= self.max_requests:
                for _ in range(tokens):
                    self.requests.append(now)
                return True

            # 计算需要等待的时间
            if self.requests:
                oldest = self.requests[0]
                wait_time = (oldest + self.window_seconds) - now
                if wait_time > 0:
                    logger.debug(f"[SlidingWindow] Waiting {wait_time:.3f}s")
                    await asyncio.sleep(wait_time)

            # 重新清理并添加
            now = time.monotonic()
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()

            for _ in range(tokens):
                self.requests.append(now)

            return True

    def reset(self):
        """重置滑动窗口"""
        self.requests.clear()
        logger.info("[SlidingWindow] Reset")


# ==================== 并发控制器 ====================

class ConcurrencyLimiter:
    """并发控制器 - 基于Semaphore"""

    def __init__(self, max_concurrent: int):
        """
        初始化并发控制器

        Args:
            max_concurrent: 最大并发数
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_count = 0
        self._lock = asyncio.Lock()

        logger.info(f"[ConcurrencyLimiter] Initialized: max={max_concurrent}")

    async def __aenter__(self):
        """获取并发槽位"""
        await self.semaphore.acquire()
        async with self._lock:
            self.active_count += 1
        return self

    async def __aexit__(self, *args):
        """释放并发槽位"""
        async with self._lock:
            self.active_count -= 1
        self.semaphore.release()

    async def run(self, coro: Awaitable[T]) -> T:
        """在并发限制下执行协程"""
        async with self:
            return await coro

    def get_active_count(self) -> int:
        """获取当前活跃任务数"""
        return self.active_count


# ==================== 任务队列 ====================

class TaskQueue(ABC):
    """任务队列基类"""

    @abstractmethod
    async def put(self, task: Task):
        """添加任务"""
        raise NotImplementedError

    @abstractmethod
    async def get(self) -> Task:
        """获取任务"""
        raise NotImplementedError

    @abstractmethod
    def empty(self) -> bool:
        """是否为空"""
        raise NotImplementedError

    @abstractmethod
    def qsize(self) -> int:
        """队列大小"""
        raise NotImplementedError


class FIFOQueue(TaskQueue):
    """先进先出队列"""

    def __init__(self):
        self.queue = asyncio.Queue()

    async def put(self, task: Task):
        await self.queue.put(task)

    async def get(self) -> Task:
        return await self.queue.get()

    def empty(self) -> bool:
        return self.queue.empty()

    def qsize(self) -> int:
        return self.queue.qsize()


class PriorityQueue(TaskQueue):
    """优先级队列（基于堆）"""

    def __init__(self):
        self.queue = asyncio.PriorityQueue()

    async def put(self, task: Task):
        # PriorityQueue使用元组 (priority, task)
        await self.queue.put((task.priority.value, task))

    async def get(self) -> Task:
        _, task = await self.queue.get()
        return task

    def empty(self) -> bool:
        return self.queue.empty()

    def qsize(self) -> int:
        return self.queue.qsize()


class DelayedQueue(TaskQueue):
    """延迟队列 - 支持延迟执行的任务"""

    def __init__(self):
        self._heap: List[tuple] = []  # (execute_time, task)
        self._lock = asyncio.Lock()

    async def put(self, task: Task):
        """添加任务"""
        execute_time = time.monotonic() + task.delay
        async with self._lock:
            heapq.heappush(self._heap, (execute_time, task))

    async def get(self) -> Task:
        """获取任务（等待到执行时间）"""
        while True:
            async with self._lock:
                if not self._heap:
                    await asyncio.sleep(0.1)
                    continue

                execute_time, task = self._heap[0]
                now = time.monotonic()

                if now >= execute_time:
                    heapq.heappop(self._heap)
                    return task

            # 等待到执行时间
            wait_time = execute_time - time.monotonic()
            if wait_time > 0:
                await asyncio.sleep(min(wait_time, 0.1))

    def empty(self) -> bool:
        return len(self._heap) == 0

    def qsize(self) -> int:
        return len(self._heap)


# ==================== 重试策略 ====================

class RetryStrategy(ABC):
    """重试策略基类"""

    @abstractmethod
    def should_retry(self, task: Task) -> bool:
        """是否应该重试"""
        raise NotImplementedError

    @abstractmethod
    def get_delay(self, task: Task) -> float:
        """获取重试延迟"""
        raise NotImplementedError


class ExponentialBackoff(RetryStrategy):
    """指数退避重试策略"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        """
        初始化指数退避

        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟（秒）
            max_delay: 最大延迟（秒）
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def should_retry(self, task: Task) -> bool:
        """是否应该重试"""
        return task.retries < self.max_retries

    def get_delay(self, task: Task) -> float:
        """获取重试延迟（指数增长）"""
        delay = self.base_delay * (2 ** task.retries)
        return min(delay, self.max_delay)


# ==================== 批量任务调度器 ====================

@dataclass
class ScheduleConfig:
    """调度配置"""
    concurrency: int = 5
    rate_limit: Optional[float] = None  # 每秒请求数
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: Optional[float] = None
    queue_type: str = "fifo"  # fifo / priority / delayed


@dataclass
class ScheduleResult:
    """调度结果"""
    total: int
    success: int
    failed: int
    cancelled: int
    duration_seconds: float
    results: List[TaskResult]

    @property
    def success_rate(self) -> float:
        """成功率"""
        return (self.success / self.total * 100) if self.total > 0 else 0

    def summary(self) -> str:
        """生成摘要"""
        return (
            f"[Schedule Result] "
            f"Total: {self.total} | "
            f"Success: {self.success} ({self.success_rate:.1f}%) | "
            f"Failed: {self.failed} | "
            f"Duration: {self.duration_seconds:.1f}s"
        )


class BatchScheduler:
    """批量任务调度器"""

    def __init__(self, config: ScheduleConfig):
        """
        初始化调度器

        Args:
            config: 调度配置
        """
        self.config = config

        # 并发控制
        self.concurrency_limiter = ConcurrencyLimiter(config.concurrency)

        # 速率限制
        self.rate_limiter: Optional[RateLimiter] = None
        if config.rate_limit:
            self.rate_limiter = TokenBucketLimiter(
                rate=config.rate_limit,
                capacity=config.concurrency,
            )

        # 重试策略
        self.retry_strategy = ExponentialBackoff(
            max_retries=config.max_retries,
            base_delay=config.retry_delay,
        )

        # 任务队列
        self.queue = self._create_queue(config.queue_type)

        # 统计
        self._total = 0
        self._success = 0
        self._failed = 0
        self._cancelled = 0
        self._results: List[TaskResult] = []

        logger.info(
            f"[BatchScheduler] Initialized: "
            f"concurrency={config.concurrency}, "
            f"rate_limit={config.rate_limit}, "
            f"queue_type={config.queue_type}"
        )

    def _create_queue(self, queue_type: str) -> TaskQueue:
        """创建任务队列"""
        if queue_type == "fifo":
            return FIFOQueue()
        elif queue_type == "priority":
            return PriorityQueue()
        elif queue_type == "delayed":
            return DelayedQueue()
        else:
            raise ValueError(f"Unknown queue type: {queue_type}")

    async def schedule(
        self,
        tasks: List[Task],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> ScheduleResult:
        """
        调度执行批量任务

        Args:
            tasks: 任务列表
            progress_callback: 进度回调函数

        Returns:
            调度结果
        """
        start_time = time.time()
        self._total = len(tasks)
        self._success = 0
        self._failed = 0
        self._cancelled = 0
        self._results = []

        # 入队
        for task in tasks:
            task.status = TaskStatus.QUEUED
            await self.queue.put(task)

        logger.info(f"[BatchScheduler] Scheduled {len(tasks)} tasks")

        # 完成计数
        completed = 0
        completed_lock = asyncio.Lock()

        async def worker():
            """Worker协程"""
            nonlocal completed

            while not self.queue.empty():
                try:
                    task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # 执行任务
                result = await self._execute_task(task)
                self._results.append(result)

                # 处理结果
                if result.status == TaskStatus.SUCCESS:
                    self._success += 1
                elif result.status == TaskStatus.FAILED:
                    # 检查是否需要重试
                    if self.retry_strategy.should_retry(task):
                        task.retries += 1
                        delay = self.retry_strategy.get_delay(task)
                        task.delay = delay
                        task.status = TaskStatus.RETRY
                        await self.queue.put(task)
                        logger.info(
                            f"[BatchScheduler] Retrying task {task.id} "
                            f"(attempt {task.retries + 1}/{self.config.max_retries + 1}) "
                            f"after {delay:.1f}s"
                        )
                        continue
                    else:
                        self._failed += 1
                elif result.status == TaskStatus.CANCELLED:
                    self._cancelled += 1

                # 更新进度
                async with completed_lock:
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, self._total)

        # 启动Workers
        workers = [
            asyncio.create_task(worker())
            for _ in range(self.config.concurrency)
        ]

        # 等待所有Worker完成
        await asyncio.gather(*workers, return_exceptions=True)

        duration = time.time() - start_time

        result = ScheduleResult(
            total=self._total,
            success=self._success,
            failed=self._failed,
            cancelled=self._cancelled,
            duration_seconds=duration,
            results=self._results,
        )

        logger.info(result.summary())

        return result

    async def _execute_task(self, task: Task) -> TaskResult:
        """执行单个任务"""
        # 速率限制
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # 并发控制
        async with self.concurrency_limiter:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()

            try:
                # 执行任务（带超时）
                timeout = task.timeout or self.config.timeout
                if timeout:
                    task.result = await asyncio.wait_for(
                        task.func(*task.args, **task.kwargs),
                        timeout=timeout,
                    )
                else:
                    task.result = await task.func(*task.args, **task.kwargs)

                task.status = TaskStatus.SUCCESS
                task.finished_at = datetime.now()

                logger.debug(
                    f"[BatchScheduler] Task {task.id} succeeded "
                    f"in {task.duration_ms:.0f}ms"
                )

                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.SUCCESS,
                    result=task.result,
                    duration_ms=task.duration_ms,
                    retries=task.retries,
                )

            except asyncio.TimeoutError:
                task.status = TaskStatus.FAILED
                task.error = Exception("Task timeout")
                task.finished_at = datetime.now()

                logger.warning(f"[BatchScheduler] Task {task.id} timed out")

                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error="Timeout",
                    duration_ms=task.duration_ms,
                    retries=task.retries,
                )

            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED
                task.finished_at = datetime.now()

                logger.warning(f"[BatchScheduler] Task {task.id} cancelled")

                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.CANCELLED,
                    error="Cancelled",
                    duration_ms=task.duration_ms,
                    retries=task.retries,
                )

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = e
                task.finished_at = datetime.now()

                logger.error(
                    f"[BatchScheduler] Task {task.id} failed: {e}",
                    exc_info=True,
                )

                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error=str(e),
                    duration_ms=task.duration_ms,
                    retries=task.retries,
                )


# ==================== 工具函数 ====================

def create_scheduler(
    concurrency: int = 5,
    rate_limit: Optional[float] = None,
    max_retries: int = 3,
    **kwargs
) -> BatchScheduler:
    """
    创建批量调度器（便捷函数）

    Args:
        concurrency: 最大并发数
        rate_limit: 每秒请求数限制
        max_retries: 最大重试次数
        **kwargs: 其他配置参数

    Returns:
        批量调度器实例
    """
    config = ScheduleConfig(
        concurrency=concurrency,
        rate_limit=rate_limit,
        max_retries=max_retries,
        **kwargs
    )
    return BatchScheduler(config)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    async def example_fetch(url: str) -> dict:
        """示例抓取函数"""
        await asyncio.sleep(0.5)  # 模拟网络请求
        return {"url": url, "status": 200}

    async def main():
        print("\n=== 批量任务调度示例 ===")

        # 创建调度器
        scheduler = create_scheduler(
            concurrency=10,
            rate_limit=5.0,  # 每秒5个请求
            max_retries=2,
        )

        # 创建任务列表
        tasks = [
            Task(
                id=f"task_{i}",
                func=example_fetch,
                args=(f"https://example.com/page/{i}",),
                priority=TaskPriority.NORMAL,
            )
            for i in range(50)
        ]

        # 进度回调
        def progress(completed, total):
            print(f"\rProgress: {completed}/{total} ({completed/total*100:.1f}%)", end="")

        # 执行调度
        result = await scheduler.schedule(tasks, progress_callback=progress)

        # 打印结果
        print("\n\n" + result.summary())
        print(f"Success Rate: {result.success_rate:.2f}%")

    # 运行示例
    asyncio.run(main())
