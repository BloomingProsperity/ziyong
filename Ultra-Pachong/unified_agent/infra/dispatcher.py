"""
高并发调度器 - 支持日采10万+数据

核心能力：
1. 并发控制 - 控制同时发起的请求数
2. 速率限制 - 每秒最大请求数
3. 自动重试 - 失败自动重试
4. Cookie轮换 - 自动切换Cookie池中的Cookie
5. 代理轮换 - 自动切换代理

架构：
```
┌─────────────────────────────────────────────────────────────────┐
│                     MassiveDispatcher                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   URLs ──▶ [TaskQueue] ──▶ [Workers] ──▶ [Results]             │
│                 │              │                                │
│                 ▼              ▼                                │
│           [RateLimiter]   [CookiePool]                         │
│                            [ProxyPool]                          │
│                            [SignServer]                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

使用示例：
    dispatcher = MassiveDispatcher(
        concurrency=50,
        requests_per_second=10,
    )

    results = await dispatcher.dispatch(
        urls=["https://example.com/1", "https://example.com/2", ...],
        fetch_func=my_fetch_function,
    )
"""

from __future__ import annotations

import asyncio
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, List, Dict, Awaitable
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class DispatchTask:
    """调度任务"""
    id: int
    url: str
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    retries: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    cookie_session_id: Optional[str] = None
    proxy: Optional[str] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds() * 1000
        return None


@dataclass
class DispatchResult:
    """调度结果"""
    total: int
    success: int
    failed: int
    retried: int
    duration_seconds: float
    results: List[Any]
    errors: List[Dict]

    @property
    def success_rate(self) -> float:
        return self.success / self.total * 100 if self.total > 0 else 0

    def summary(self) -> str:
        return (
            f"[Dispatch Result] Total: {self.total} | "
            f"Success: {self.success} ({self.success_rate:.1f}%) | "
            f"Failed: {self.failed} | "
            f"Duration: {self.duration_seconds:.1f}s"
        )


class RateLimiter:
    """速率限制器 - 令牌桶算法"""

    def __init__(self, rate: float, burst: int = 1):
        """
        Args:
            rate: 每秒允许的请求数
            burst: 最大突发请求数
        """
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_time = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """获取一个令牌"""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_time
            self.last_time = now

            # 添加令牌
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)

            if self.tokens >= 1:
                self.tokens -= 1
                return

            # 等待令牌
            wait_time = (1 - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
            self.tokens = 0


class MassiveDispatcher:
    """
    高并发调度器

    支持：
    - 并发控制
    - 速率限制
    - 自动重试
    - Cookie轮换
    - 代理轮换
    - 进度追踪
    """

    def __init__(
        self,
        concurrency: int = 50,
        requests_per_second: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0,
        cookie_pool=None,
        proxy_pool=None,
    ):
        """
        Args:
            concurrency: 最大并发数
            requests_per_second: 每秒最大请求数
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            timeout: 请求超时（秒）
            cookie_pool: Cookie池实例
            proxy_pool: 代理池实例
        """
        self.concurrency = concurrency
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.cookie_pool = cookie_pool
        self.proxy_pool = proxy_pool

        self.rate_limiter = RateLimiter(rate=requests_per_second, burst=concurrency)

        # 统计
        self._total = 0
        self._success = 0
        self._failed = 0
        self._retried = 0
        self._start_time: Optional[float] = None

    async def dispatch(
        self,
        urls: List[str],
        fetch_func: Callable[[str, Optional[dict], Optional[str]], Awaitable[Any]],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> DispatchResult:
        """
        并发调度

        Args:
            urls: URL列表
            fetch_func: 抓取函数，签名为 async def fetch(url, cookies, proxy) -> result
            progress_callback: 进度回调，签名为 callback(completed, total)

        Returns:
            DispatchResult
        """
        self._start_time = time.time()
        self._total = len(urls)
        self._success = 0
        self._failed = 0
        self._retried = 0

        # 创建任务
        tasks = [DispatchTask(id=i, url=url) for i, url in enumerate(urls)]
        results: List[Any] = [None] * len(urls)
        errors: List[Dict] = []

        # 任务队列
        queue = asyncio.Queue()
        for task in tasks:
            await queue.put(task)

        # 完成计数
        completed = 0
        completed_lock = asyncio.Lock()

        async def worker():
            nonlocal completed

            while True:
                try:
                    task = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                # 执行任务
                await self._execute_task(task, fetch_func)

                # 处理结果
                if task.status == TaskStatus.SUCCESS:
                    results[task.id] = task.result
                    self._success += 1
                elif task.status == TaskStatus.RETRY and task.retries < self.max_retries:
                    # 重新入队
                    task.status = TaskStatus.PENDING
                    task.retries += 1
                    self._retried += 1
                    await asyncio.sleep(self.retry_delay * task.retries)
                    await queue.put(task)
                else:
                    errors.append({
                        "url": task.url,
                        "error": task.error,
                        "retries": task.retries,
                    })
                    self._failed += 1

                # 更新进度
                async with completed_lock:
                    if task.status in (TaskStatus.SUCCESS, TaskStatus.FAILED):
                        completed += 1
                        if progress_callback:
                            progress_callback(completed, self._total)

                queue.task_done()

        # 启动Worker
        workers = [asyncio.create_task(worker()) for _ in range(self.concurrency)]

        # 等待所有任务完成
        await queue.join()

        # 取消未完成的Worker
        for w in workers:
            w.cancel()

        duration = time.time() - self._start_time

        return DispatchResult(
            total=self._total,
            success=self._success,
            failed=self._failed,
            retried=self._retried,
            duration_seconds=duration,
            results=[r for r in results if r is not None],
            errors=errors,
        )

    async def _execute_task(
        self,
        task: DispatchTask,
        fetch_func: Callable,
    ):
        """执行单个任务"""
        # 速率限制
        await self.rate_limiter.acquire()

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        # 获取Cookie
        cookies = None
        if self.cookie_pool:
            session = self.cookie_pool.get()
            if session:
                cookies = session.cookies
                task.cookie_session_id = session.id

        # 获取代理
        proxy = None
        if self.proxy_pool:
            proxy = self.proxy_pool.get()
            task.proxy = proxy

        try:
            # 执行抓取
            result = await asyncio.wait_for(
                fetch_func(task.url, cookies, proxy),
                timeout=self.timeout,
            )
            task.result = result
            task.status = TaskStatus.SUCCESS

            # 报告Cookie成功
            if self.cookie_pool and task.cookie_session_id:
                self.cookie_pool.mark_success(task.cookie_session_id)

        except asyncio.TimeoutError:
            task.error = "Timeout"
            task.status = TaskStatus.RETRY
            logger.warning(f"[Dispatcher] Timeout: {task.url}")

        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.RETRY
            logger.warning(f"[Dispatcher] Error: {task.url} - {e}")

            # 报告Cookie失败
            if self.cookie_pool and task.cookie_session_id:
                self.cookie_pool.mark_failed(task.cookie_session_id)

        finally:
            task.finished_at = datetime.now()

    def get_progress(self) -> Dict:
        """获取当前进度"""
        elapsed = time.time() - self._start_time if self._start_time else 0
        completed = self._success + self._failed

        return {
            "total": self._total,
            "completed": completed,
            "success": self._success,
            "failed": self._failed,
            "retried": self._retried,
            "progress": completed / self._total * 100 if self._total > 0 else 0,
            "elapsed_seconds": elapsed,
            "rate": completed / elapsed if elapsed > 0 else 0,
        }


# ==================== 便捷函数 ====================

async def batch_fetch(
    urls: List[str],
    fetch_func: Callable,
    concurrency: int = 50,
    requests_per_second: float = 10.0,
    max_retries: int = 3,
    show_progress: bool = True,
) -> DispatchResult:
    """
    批量抓取便捷函数

    Args:
        urls: URL列表
        fetch_func: 抓取函数
        concurrency: 并发数
        requests_per_second: 每秒请求数
        max_retries: 最大重试
        show_progress: 是否显示进度

    Returns:
        DispatchResult

    示例：
        async def my_fetch(url, cookies, proxy):
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                return response.json()

        result = await batch_fetch(urls, my_fetch, concurrency=100)
        print(result.summary())
    """
    dispatcher = MassiveDispatcher(
        concurrency=concurrency,
        requests_per_second=requests_per_second,
        max_retries=max_retries,
    )

    def progress_callback(completed, total):
        if show_progress:
            percent = completed / total * 100
            print(f"\r[Progress] {completed}/{total} ({percent:.1f}%)", end="", flush=True)

    result = await dispatcher.dispatch(urls, fetch_func, progress_callback)

    if show_progress:
        print()  # 换行
        print(result.summary())

    return result


# ==================== 示例代码 ====================

async def example_usage():
    """使用示例"""
    import httpx

    # 定义抓取函数
    async def fetch(url: str, cookies: Optional[dict], proxy: Optional[str]):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            return {"url": url, "status": response.status_code}

    # 生成URL列表
    urls = [f"https://httpbin.org/get?page={i}" for i in range(100)]

    # 批量抓取
    result = await batch_fetch(
        urls=urls,
        fetch_func=fetch,
        concurrency=10,
        requests_per_second=5.0,
    )

    print(f"\n成功获取 {result.success} 条数据")
    if result.errors:
        print(f"失败 {len(result.errors)} 条:")
        for err in result.errors[:5]:
            print(f"  - {err['url']}: {err['error']}")


if __name__ == "__main__":
    asyncio.run(example_usage())
