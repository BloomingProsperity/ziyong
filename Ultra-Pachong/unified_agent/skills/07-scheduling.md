# 07 - 调度模块 (Scheduling)

---
name: scheduling
version: 1.0.0
description: 任务编排、并发控制与流量管理
triggers:
  - "调度"
  - "并发"
  - "限流"
  - "批量"
  - "队列"
dependencies:
  - asyncio
  - aiohttp
---

## 模块目标

**核心原则：给出需求，必须完成。**

| 目标 | 达成标准 |
|------|---------|
| **任务全执行** | 提交的任务 100% 执行，失败自动重试 |
| **限流不触发** | 请求速率自动控制，429 错误率 < 1% |
| **并发可控** | 并发数精确控制，资源占用可预测 |
| **进度可恢复** | 中断后可从断点继续，无需重新开始 |

## 模块概述

调度模块负责任务编排和流量控制，确保爬虫高效且不触发反爬。

```
┌─────────────────────────────────────────────────────────────────┐
│                        调度模块架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                      任务队列                            │  │
│   │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐              │  │
│   │  │Task1│ │Task2│ │Task3│ │Task4│ │Task5│ ...          │  │
│   │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘              │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                     调度器                               │  │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │  │
│   │  │ 并发控制  │  │  限流器   │  │ 优先级   │              │  │
│   │  │Semaphore │  │RateLimiter│  │ Priority │              │  │
│   │  └──────────┘  └──────────┘  └──────────┘              │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│        ┌─────────┐     ┌─────────┐     ┌─────────┐             │
│        │Worker 1 │     │Worker 2 │     │Worker 3 │             │
│        └─────────┘     └─────────┘     └─────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 并发控制

### 信号量限制

```python
import asyncio
from asyncio import Semaphore

class ConcurrencyController:
    """并发控制器"""

    def __init__(self, max_concurrent: int = 5):
        self.semaphore = Semaphore(max_concurrent)
        self.active_count = 0

    async def acquire(self):
        await self.semaphore.acquire()
        self.active_count += 1

    def release(self):
        self.semaphore.release()
        self.active_count -= 1

    async def run(self, coro):
        """在并发限制下执行协程"""
        await self.acquire()
        try:
            return await coro
        finally:
            self.release()
```

### 使用示例

```python
async def fetch_all(urls: list[str], max_concurrent: int = 5):
    """并发控制的批量请求"""

    controller = ConcurrencyController(max_concurrent)
    results = []

    async def fetch_one(url):
        async with httpx.AsyncClient() as client:
            return await controller.run(client.get(url))

    tasks = [fetch_one(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results

# 使用
urls = [f"https://api.example.com/item/{i}" for i in range(100)]
results = asyncio.run(fetch_all(urls, max_concurrent=10))
```

---

## 限流器

### 令牌桶算法

```python
import time
import asyncio

class TokenBucket:
    """令牌桶限流器"""

    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: 每秒生成的令牌数
            capacity: 桶的最大容量
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> float:
        """获取令牌，返回等待时间"""

        async with self.lock:
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
                return 0

            # 需要等待
            wait_time = (tokens - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
            self.tokens = 0
            self.last_update = time.monotonic()

            return wait_time
```

### 滑动窗口限流

```python
from collections import deque
import time

class SlidingWindowLimiter:
    """滑动窗口限流器"""

    def __init__(self, max_requests: int, window_seconds: float):
        """
        Args:
            max_requests: 窗口内最大请求数
            window_seconds: 窗口时长(秒)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()

    def acquire(self) -> bool:
        """尝试获取请求许可"""

        now = time.monotonic()

        # 清理过期请求
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()

        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True

        return False

    def wait_time(self) -> float:
        """计算需要等待的时间"""

        if len(self.requests) < self.max_requests:
            return 0

        oldest = self.requests[0]
        return max(0, oldest + self.window_seconds - time.monotonic())
```

### 限流使用

```python
# 每秒最多 2 个请求
limiter = TokenBucket(rate=2, capacity=5)

async def rate_limited_request(url: str):
    wait_time = await limiter.acquire()
    if wait_time > 0:
        print(f"限流等待: {wait_time:.2f}s")

    async with httpx.AsyncClient() as client:
        return await client.get(url)
```

---

## 任务队列

### 基础队列

```python
import asyncio
from dataclasses import dataclass
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    id: str
    url: str
    priority: int = 0
    status: TaskStatus = TaskStatus.PENDING
    retries: int = 0
    max_retries: int = 3
    result: Any = None
    error: str | None = None

class TaskQueue:
    """任务队列"""

    def __init__(self):
        self.pending = asyncio.PriorityQueue()
        self.running = {}
        self.completed = []
        self.failed = []

    async def put(self, task: Task):
        """添加任务"""
        await self.pending.put((task.priority, task.id, task))

    async def get(self) -> Task:
        """获取任务"""
        _, _, task = await self.pending.get()
        task.status = TaskStatus.RUNNING
        self.running[task.id] = task
        return task

    def complete(self, task: Task, result: Any):
        """完成任务"""
        task.status = TaskStatus.COMPLETED
        task.result = result
        del self.running[task.id]
        self.completed.append(task)

    def fail(self, task: Task, error: str):
        """失败任务"""
        task.error = error
        task.retries += 1

        if task.retries < task.max_retries:
            task.status = TaskStatus.PENDING
            asyncio.create_task(self.put(task))
        else:
            task.status = TaskStatus.FAILED
            del self.running[task.id]
            self.failed.append(task)
```

### 优先级队列

```python
# 优先级定义 (数字越小优先级越高)
PRIORITY = {
    "critical": 0,
    "high": 1,
    "normal": 2,
    "low": 3,
}

# 添加任务
await queue.put(Task(id="1", url="...", priority=PRIORITY["high"]))
await queue.put(Task(id="2", url="...", priority=PRIORITY["normal"]))
await queue.put(Task(id="3", url="...", priority=PRIORITY["critical"]))

# 获取顺序: 3 -> 1 -> 2
```

---

## 工作池

### Worker Pool

```python
class WorkerPool:
    """工作池"""

    def __init__(
        self,
        queue: TaskQueue,
        num_workers: int = 5,
        rate_limiter: TokenBucket | None = None
    ):
        self.queue = queue
        self.num_workers = num_workers
        self.rate_limiter = rate_limiter
        self.workers = []
        self.running = False

    async def worker(self, worker_id: int):
        """工作协程"""

        while self.running:
            try:
                task = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue

            try:
                # 限流
                if self.rate_limiter:
                    await self.rate_limiter.acquire()

                # 执行任务
                result = await self.execute(task)
                self.queue.complete(task, result)

            except Exception as e:
                self.queue.fail(task, str(e))

    async def execute(self, task: Task) -> Any:
        """执行任务 (子类实现)"""
        raise NotImplementedError

    async def start(self):
        """启动工作池"""
        self.running = True
        self.workers = [
            asyncio.create_task(self.worker(i))
            for i in range(self.num_workers)
        ]

    async def stop(self):
        """停止工作池"""
        self.running = False
        await asyncio.gather(*self.workers, return_exceptions=True)

    async def wait_all(self):
        """等待所有任务完成"""
        while self.queue.running or not self.queue.pending.empty():
            await asyncio.sleep(0.1)
```

---

## 批量请求

### batch_call_api 实现

```python
def batch_call_api(
    requests: list[dict[str, Any]],
    delay_between: float = 1.0,
    stop_on_error: bool = False,
) -> list[ApiCallResult]:
    """同步批量请求"""

    results = []

    for i, req in enumerate(requests):
        print(f"请求 {i+1}/{len(requests)}")

        result = call_api(**req)
        results.append(result)

        if not result.success and stop_on_error:
            print(f"遇到错误，停止: {result.error}")
            break

        if i < len(requests) - 1:
            time.sleep(delay_between)

    return results
```

### 异步批量请求

```python
async def async_batch_call(
    urls: list[str],
    max_concurrent: int = 5,
    delay: float = 0.1,
) -> list[dict]:
    """异步批量请求"""

    semaphore = asyncio.Semaphore(max_concurrent)
    results = []

    async def fetch_one(url: str, index: int):
        async with semaphore:
            await asyncio.sleep(delay * index % max_concurrent)

            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                return {
                    "url": url,
                    "status": response.status_code,
                    "data": response.json()
                }

    tasks = [fetch_one(url, i) for i, url in enumerate(urls)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results
```

---

## 失败重试队列

### 重试策略

```python
@dataclass
class RetryPolicy:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential: bool = True
    jitter: bool = True

    def get_delay(self, retry_count: int) -> float:
        if self.exponential:
            delay = self.base_delay * (2 ** retry_count)
        else:
            delay = self.base_delay

        delay = min(delay, self.max_delay)

        if self.jitter:
            delay *= random.uniform(0.5, 1.5)

        return delay
```

### 重试队列实现

```python
class RetryQueue:
    """失败重试队列"""

    def __init__(self, policy: RetryPolicy):
        self.policy = policy
        self.queue = []

    def add(self, task: Task):
        """添加到重试队列"""
        if task.retries < self.policy.max_retries:
            delay = self.policy.get_delay(task.retries)
            retry_at = time.monotonic() + delay
            heapq.heappush(self.queue, (retry_at, task))

    def get_ready(self) -> list[Task]:
        """获取可重试的任务"""
        now = time.monotonic()
        ready = []

        while self.queue and self.queue[0][0] <= now:
            _, task = heapq.heappop(self.queue)
            ready.append(task)

        return ready
```

---

## 调度配置

### SchedulerConfig

```python
@dataclass
class SchedulerConfig:
    # 并发控制
    max_concurrent: int = 5          # 最大并发数
    max_workers: int = 3             # 工作线程数

    # 限流配置
    requests_per_second: float = 2.0 # 每秒请求数
    burst_size: int = 10             # 突发容量

    # 延迟配置
    min_delay: float = 0.5           # 最小请求间隔
    max_delay: float = 3.0           # 最大请求间隔
    human_like: bool = True          # 人类化延迟

    # 重试配置
    max_retries: int = 3
    retry_delay: float = 5.0

    # 超时配置
    request_timeout: float = 30.0
    task_timeout: float = 300.0
```

---

## 监控统计

### 统计指标

```python
@dataclass
class SchedulerStats:
    """调度器统计"""

    # 任务统计
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    pending_tasks: int = 0

    # 时间统计
    start_time: float = 0
    total_runtime: float = 0
    avg_task_time: float = 0

    # 性能统计
    requests_per_second: float = 0
    success_rate: float = 0
    retry_rate: float = 0

    def to_report(self) -> str:
        return f"""
调度器统计报告
==============
任务统计:
  - 总任务: {self.total_tasks}
  - 完成: {self.completed_tasks}
  - 失败: {self.failed_tasks}
  - 待处理: {self.pending_tasks}

性能统计:
  - 运行时间: {self.total_runtime:.1f}s
  - 请求速率: {self.requests_per_second:.2f}/s
  - 成功率: {self.success_rate:.1%}
  - 重试率: {self.retry_rate:.1%}
"""
```

---

## 完整示例

### 批量抓取商品

```python
import asyncio
from unified_agent import Brain

async def batch_scrape_products(product_ids: list[str]):
    """批量抓取商品信息"""

    brain = Brain()

    # 配置
    max_concurrent = 5
    rate_limit = 2.0  # 每秒2个请求

    limiter = TokenBucket(rate=rate_limit, capacity=10)
    semaphore = asyncio.Semaphore(max_concurrent)

    results = []

    async def scrape_one(product_id: str):
        async with semaphore:
            await limiter.acquire()

            url = f"https://api.example.com/product/{product_id}"
            result = brain.call_api(url)

            if result.success:
                return result.body
            else:
                return {"id": product_id, "error": result.error}

    tasks = [scrape_one(pid) for pid in product_ids]
    results = await asyncio.gather(*tasks)

    return results

# 使用
product_ids = [f"P{i:06d}" for i in range(1, 101)]
results = asyncio.run(batch_scrape_products(product_ids))

# 保存结果
brain.export_data(results, "products", format="json")
```

---

## 最佳实践

### 1. 根据目标网站调整配置

```python
# 普通网站
config = SchedulerConfig(
    max_concurrent=10,
    requests_per_second=5.0,
)

# 严格反爬网站
config = SchedulerConfig(
    max_concurrent=2,
    requests_per_second=0.5,
    human_like=True,
)
```

### 2. 监控和调整

```python
# 运行时监控
while not queue.empty():
    stats = scheduler.get_stats()

    if stats.success_rate < 0.9:
        # 成功率下降，降低速率
        scheduler.decrease_rate()

    if stats.requests_per_second > target_rate:
        # 超速，增加延迟
        scheduler.increase_delay()

    await asyncio.sleep(10)
```

### 3. 优雅退出

```python
import signal

async def graceful_shutdown():
    """优雅退出"""
    print("收到退出信号，正在保存进度...")

    # 停止接收新任务
    scheduler.stop_accepting()

    # 等待当前任务完成
    await scheduler.wait_running()

    # 保存未完成任务
    scheduler.save_pending()

    print("退出完成")

# 注册信号处理
loop = asyncio.get_event_loop()
loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(graceful_shutdown()))
```

---

## 诊断日志

```
# 调度器启动
[SCHED] 启动调度器: workers=5, rate=2.0/s, concurrent=10
[SCHED] 任务队列初始化: capacity=10000

# 任务管理
[SCHED] 添加任务: 100 个 URL (优先级: normal)
[SCHED] 任务分发: task_001 -> worker_2
[SCHED] 任务完成: task_001 (1.2s)
[SCHED] 任务失败: task_002 (重试 1/3)

# 并发控制
[SCHED] 并发状态: active=5/10
[SCHED] 等待信号量: task_003 排队中
[SCHED] 获取信号量: task_003 开始执行

# 限流控制
[SCHED] 令牌桶: tokens=3/10, rate=2.0/s
[SCHED] 限流等待: 0.5s (令牌不足)
[SCHED] 限流触发: 当前 5.2/s > 目标 2.0/s

# 进度统计
[SCHED] 进度: 50/100 (50%), 成功率: 98%
[SCHED] 速率: 1.8/s, 预计剩余: 28s

# 重试队列
[RETRY] 加入重试队列: task_002 (延迟 2.0s)
[RETRY] 重试执行: task_002 (第 2/3 次)
[RETRY] 重试成功: task_002

# 错误情况
[SCHED] WARN: 成功率下降至 85%，降低速率
[SCHED] ERROR: Worker_3 异常退出，重启中
[SCHED] 优雅退出: 保存 30 个未完成任务
```

---

## 相关模块

- **配合**: [04-请求模块](04-request.md) - 请求执行
- **配合**: [06-存储模块](06-storage.md) - 进度保存
- **上游**: [01-侦查模块](01-reconnaissance.md) - 任务发现
- **配合**: [16-战术模块](16-tactics.md) - 根据成功率调整策略
