# 13 - 分布式架构模块 (Distributed Architecture)

---
name: distributed-architecture
version: 1.0.0
description: 分布式爬虫架构设计、任务调度与数据同步
triggers:
  - "分布式"
  - "distributed"
  - "集群"
  - "cluster"
  - "横向扩展"
  - "Celery"
  - "Redis"
difficulty: ⭐⭐⭐⭐
---

## 模块目标

**核心原则：给出需求，必须完成。**

| 目标 | 达成标准 |
|------|---------|
| **任务全分发** | 提交的 URL 100% 被 Worker 领取执行 |
| **去重全覆盖** | 相同 URL 不重复爬取，Bloom Filter 误判率 < 0.01% |
| **故障可恢复** | Worker 崩溃后任务自动重新分配，无数据丢失 |
| **横向可扩展** | 新增 Worker 即可线性提升吞吐量 |

## 模块概述

分布式模块负责将爬虫从单机扩展到集群，实现高并发、高可用的数据采集能力。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         分布式爬虫架构                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         调度层 (Scheduler)                          │  │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │  │
│   │  │ 任务分发  │ │ 优先级队列│ │ 去重过滤  │ │ 限流控制  │              │  │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                    ┌───────────────┼───────────────┐                        │
│                    ▼               ▼               ▼                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         Worker 层                                    │  │
│   │   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐  │  │
│   │   │Worker 1│   │Worker 2│   │Worker 3│   │Worker 4│   │Worker N│  │  │
│   │   └────────┘   └────────┘   └────────┘   └────────┘   └────────┘  │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         存储层 (Storage)                            │  │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │  │
│   │  │  Redis   │ │ MongoDB  │ │  MySQL   │ │ 文件存储  │              │  │
│   │  │ (队列/缓存)│ │ (文档)   │ │ (关系)   │ │ (S3/OSS) │              │  │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 架构模式

### 1. 主从架构 (Master-Worker)

```python
"""
主从架构：一个 Master 节点分发任务，多个 Worker 节点执行
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import redis
import json
import uuid
import threading
import time


@dataclass
class Task:
    """任务定义"""
    task_id: str
    url: str
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, data: str) -> "Task":
        return cls(**json.loads(data))


class MasterNode:
    """主节点 - 负责任务分发和协调"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        self.task_queue = "crawler:tasks"
        self.result_queue = "crawler:results"
        self.worker_registry = "crawler:workers"
        self.dedup_set = "crawler:seen"

    def submit_task(self, url: str, priority: int = 0, **metadata) -> str:
        """提交任务"""

        # URL 去重
        url_hash = self._hash_url(url)
        if self.redis.sismember(self.dedup_set, url_hash):
            return None  # 已存在

        # 创建任务
        task = Task(
            task_id=str(uuid.uuid4()),
            url=url,
            priority=priority,
            metadata=metadata
        )

        # 标记已见
        self.redis.sadd(self.dedup_set, url_hash)

        # 加入队列（按优先级排序）
        self.redis.zadd(self.task_queue, {task.to_json(): -priority})

        return task.task_id

    def submit_batch(self, urls: List[str], priority: int = 0) -> List[str]:
        """批量提交任务"""

        task_ids = []
        pipeline = self.redis.pipeline()

        for url in urls:
            url_hash = self._hash_url(url)
            if not self.redis.sismember(self.dedup_set, url_hash):
                task = Task(
                    task_id=str(uuid.uuid4()),
                    url=url,
                    priority=priority
                )
                pipeline.sadd(self.dedup_set, url_hash)
                pipeline.zadd(self.task_queue, {task.to_json(): -priority})
                task_ids.append(task.task_id)

        pipeline.execute()
        return task_ids

    def get_stats(self) -> Dict:
        """获取统计信息"""

        return {
            "pending_tasks": self.redis.zcard(self.task_queue),
            "completed_results": self.redis.llen(self.result_queue),
            "unique_urls": self.redis.scard(self.dedup_set),
            "active_workers": self.redis.hlen(self.worker_registry),
        }

    def get_workers(self) -> List[Dict]:
        """获取 Worker 状态"""

        workers = []
        for worker_id, data in self.redis.hgetall(self.worker_registry).items():
            worker = json.loads(data)
            worker["worker_id"] = worker_id.decode()
            workers.append(worker)

        return workers

    def _hash_url(self, url: str) -> str:
        """URL 哈希"""
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()


class WorkerNode:
    """Worker 节点 - 负责执行爬取任务"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        worker_id: Optional[str] = None
    ):
        self.redis = redis.from_url(redis_url)
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.task_queue = "crawler:tasks"
        self.result_queue = "crawler:results"
        self.worker_registry = "crawler:workers"
        self.retry_queue = "crawler:retry"
        self.running = False

    def start(self, scraper_func):
        """启动 Worker"""

        self.running = True
        self._register()

        # 心跳线程
        heartbeat_thread = threading.Thread(target=self._heartbeat)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

        print(f"[{self.worker_id}] Worker started")

        while self.running:
            # 从队列获取任务（阻塞）
            result = self.redis.bzpopmin(self.task_queue, timeout=5)

            if result is None:
                continue

            _, task_json, _ = result
            task = Task.from_json(task_json)

            self._update_status("processing", task.url)

            try:
                # 执行爬取
                data = scraper_func(task.url, task.metadata)

                # 提交结果
                self._submit_result(task, data, success=True)
                self._update_status("idle")

            except Exception as e:
                print(f"[{self.worker_id}] Error: {e}")
                self._handle_failure(task, str(e))
                self._update_status("idle")

    def stop(self):
        """停止 Worker"""
        self.running = False
        self._unregister()

    def _register(self):
        """注册 Worker"""
        self.redis.hset(self.worker_registry, self.worker_id, json.dumps({
            "status": "idle",
            "started_at": datetime.now().isoformat(),
            "last_heartbeat": datetime.now().isoformat(),
            "current_url": None,
        }))

    def _unregister(self):
        """注销 Worker"""
        self.redis.hdel(self.worker_registry, self.worker_id)

    def _update_status(self, status: str, current_url: str = None):
        """更新状态"""
        self.redis.hset(self.worker_registry, self.worker_id, json.dumps({
            "status": status,
            "last_heartbeat": datetime.now().isoformat(),
            "current_url": current_url,
        }))

    def _heartbeat(self):
        """心跳"""
        while self.running:
            self._update_status("heartbeat")
            time.sleep(10)

    def _submit_result(self, task: Task, data: Dict, success: bool):
        """提交结果"""
        result = {
            "task_id": task.task_id,
            "url": task.url,
            "success": success,
            "data": data,
            "worker_id": self.worker_id,
            "completed_at": datetime.now().isoformat(),
        }
        self.redis.lpush(self.result_queue, json.dumps(result))

    def _handle_failure(self, task: Task, error: str):
        """处理失败"""
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            # 放回队列（降低优先级）
            self.redis.zadd(
                self.task_queue,
                {task.to_json(): -(task.priority - task.retry_count)}
            )
        else:
            # 记录失败
            self._submit_result(task, {"error": error}, success=False)


# 使用示例
def scrape_page(url: str, metadata: Dict) -> Dict:
    """爬取函数"""
    import httpx
    response = httpx.get(url)
    return {
        "status_code": response.status_code,
        "content_length": len(response.content),
        "title": "...",  # 解析标题
    }


# Master 端
master = MasterNode()
master.submit_batch([
    "https://example.com/page/1",
    "https://example.com/page/2",
    "https://example.com/page/3",
])

# Worker 端 (多个节点运行)
worker = WorkerNode()
worker.start(scrape_page)
```

### 2. Celery 任务队列

```python
"""
使用 Celery 实现分布式任务队列
"""

from celery import Celery
from celery.result import AsyncResult
from typing import List, Dict
import httpx


# 配置 Celery
app = Celery(
    'crawler',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
)

app.conf.update(
    # 任务序列化
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # 任务超时
    task_time_limit=300,
    task_soft_time_limit=240,

    # 重试设置
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # 并发设置
    worker_prefetch_multiplier=1,
    worker_concurrency=10,

    # 结果过期
    result_expires=3600,

    # 任务路由
    task_routes={
        'crawler.tasks.scrape_page': {'queue': 'scrape'},
        'crawler.tasks.parse_data': {'queue': 'parse'},
        'crawler.tasks.save_data': {'queue': 'save'},
    },
)


@app.task(bind=True, max_retries=3)
def scrape_page(self, url: str, headers: Dict = None) -> Dict:
    """爬取页面任务"""

    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=headers or {})
            response.raise_for_status()

            return {
                "url": url,
                "status_code": response.status_code,
                "content": response.text,
                "headers": dict(response.headers),
            }

    except Exception as e:
        # 重试
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


@app.task
def parse_data(html: str, url: str) -> Dict:
    """解析数据任务"""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, 'html.parser')

    return {
        "url": url,
        "title": soup.title.string if soup.title else None,
        "links": [a.get('href') for a in soup.find_all('a', href=True)],
    }


@app.task
def save_data(data: Dict, collection: str = "default") -> bool:
    """保存数据任务"""

    from pymongo import MongoClient

    client = MongoClient("mongodb://localhost:27017")
    db = client.crawler
    db[collection].insert_one(data)

    return True


# 任务编排
@app.task
def crawl_and_save(url: str) -> str:
    """编排任务链"""

    from celery import chain

    # 创建任务链: 爬取 -> 解析 -> 保存
    workflow = chain(
        scrape_page.s(url),
        parse_data.s(url),
        save_data.s("pages")
    )

    result = workflow.apply_async()
    return result.id


# 批量处理
@app.task
def batch_crawl(urls: List[str]) -> List[str]:
    """批量爬取"""

    from celery import group

    # 创建任务组（并行执行）
    job = group(scrape_page.s(url) for url in urls)
    result = job.apply_async()

    return result.id


# 客户端调用
def submit_crawl_job(urls: List[str]):
    """提交爬取任务"""

    task_ids = []

    for url in urls:
        result = crawl_and_save.delay(url)
        task_ids.append(result.id)

    return task_ids


def get_task_status(task_id: str) -> Dict:
    """获取任务状态"""

    result = AsyncResult(task_id, app=app)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


# 启动 Worker:
# celery -A crawler.tasks worker -Q scrape,parse,save --loglevel=info -c 10
```

### 3. Scrapy 分布式

```python
"""
使用 Scrapy-Redis 实现分布式爬虫
"""

# settings.py
SCHEDULER = "scrapy_redis.scheduler.Scheduler"
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
SCHEDULER_PERSIST = True

REDIS_URL = 'redis://localhost:6379'

# 不清除指纹
SCHEDULER_FLUSH_ON_START = False

# 队列类型
SCHEDULER_QUEUE_CLASS = 'scrapy_redis.queue.PriorityQueue'


# spider.py
import scrapy
from scrapy_redis.spiders import RedisSpider


class DistributedSpider(RedisSpider):
    """分布式 Spider"""

    name = "distributed"
    redis_key = "distributed:start_urls"

    # 自定义设置
    custom_settings = {
        'CONCURRENT_REQUESTS': 16,
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
    }

    def parse(self, response):
        """解析响应"""

        # 提取数据
        for item in response.css('.product-item'):
            yield {
                'title': item.css('.title::text').get(),
                'price': item.css('.price::text').get(),
                'url': response.urljoin(item.css('a::attr(href)').get()),
            }

        # 提取下一页
        next_page = response.css('.pagination .next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)


# 推送 URL 到 Redis
import redis

r = redis.Redis()
urls = [
    "https://example.com/products?page=1",
    "https://example.com/products?page=2",
    "https://example.com/products?page=3",
]

for url in urls:
    r.lpush("distributed:start_urls", url)


# 启动多个 Spider 实例
# scrapy crawl distributed
```

---

## 消息队列

### RabbitMQ 集成

```python
"""
RabbitMQ 消息队列集成
"""

import pika
import json
from typing import Callable, Dict
from dataclasses import dataclass
import threading


@dataclass
class RabbitMQConfig:
    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtual_host: str = "/"


class RabbitMQPublisher:
    """消息发布者"""

    def __init__(self, config: RabbitMQConfig):
        credentials = pika.PlainCredentials(config.username, config.password)
        parameters = pika.ConnectionParameters(
            host=config.host,
            port=config.port,
            virtual_host=config.virtual_host,
            credentials=credentials,
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

    def declare_queue(self, queue_name: str, durable: bool = True):
        """声明队列"""
        self.channel.queue_declare(queue=queue_name, durable=durable)

    def publish(
        self,
        queue_name: str,
        message: Dict,
        priority: int = 0
    ):
        """发布消息"""

        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # 持久化
                priority=priority,
            )
        )

    def publish_batch(self, queue_name: str, messages: list):
        """批量发布"""
        for msg in messages:
            self.publish(queue_name, msg)

    def close(self):
        self.connection.close()


class RabbitMQConsumer:
    """消息消费者"""

    def __init__(self, config: RabbitMQConfig):
        credentials = pika.PlainCredentials(config.username, config.password)
        parameters = pika.ConnectionParameters(
            host=config.host,
            port=config.port,
            virtual_host=config.virtual_host,
            credentials=credentials,
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

    def consume(
        self,
        queue_name: str,
        callback: Callable[[Dict], bool],
        prefetch_count: int = 1
    ):
        """消费消息"""

        self.channel.basic_qos(prefetch_count=prefetch_count)
        self.channel.queue_declare(queue=queue_name, durable=True)

        def on_message(ch, method, properties, body):
            message = json.loads(body)
            try:
                success = callback(message)
                if success:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                else:
                    # 拒绝并重新排队
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            except Exception as e:
                print(f"Error processing message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=on_message
        )

        print(f"Waiting for messages on {queue_name}")
        self.channel.start_consuming()

    def stop(self):
        self.channel.stop_consuming()
        self.connection.close()


# 使用示例
def process_task(message: Dict) -> bool:
    """处理任务"""
    url = message.get("url")
    print(f"Processing: {url}")
    # 爬取逻辑...
    return True


# 发布端
publisher = RabbitMQPublisher(RabbitMQConfig())
publisher.declare_queue("crawl_tasks")
publisher.publish("crawl_tasks", {"url": "https://example.com/page/1"})
publisher.close()

# 消费端
consumer = RabbitMQConsumer(RabbitMQConfig())
consumer.consume("crawl_tasks", process_task)
```

### Kafka 集成

```python
"""
Kafka 消息队列集成（高吞吐场景）
"""

from kafka import KafkaProducer, KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic
import json
from typing import Dict, Callable, List
from dataclasses import dataclass


@dataclass
class KafkaConfig:
    bootstrap_servers: List[str] = None
    client_id: str = "crawler"

    def __post_init__(self):
        if self.bootstrap_servers is None:
            self.bootstrap_servers = ["localhost:9092"]


class KafkaCrawlerProducer:
    """Kafka 生产者"""

    def __init__(self, config: KafkaConfig):
        self.producer = KafkaProducer(
            bootstrap_servers=config.bootstrap_servers,
            client_id=config.client_id,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            batch_size=16384,
            linger_ms=10,
            compression_type='gzip',
        )

    def create_topic(self, topic: str, partitions: int = 3, replication: int = 1):
        """创建 Topic"""
        admin = KafkaAdminClient(bootstrap_servers=self.producer.config['bootstrap_servers'])
        try:
            admin.create_topics([
                NewTopic(name=topic, num_partitions=partitions, replication_factor=replication)
            ])
        except Exception as e:
            print(f"Topic may already exist: {e}")

    def send(self, topic: str, message: Dict, key: str = None):
        """发送消息"""
        future = self.producer.send(topic, value=message, key=key)
        return future

    def send_batch(self, topic: str, messages: List[Dict]):
        """批量发送"""
        futures = []
        for msg in messages:
            key = msg.get('url', None)
            future = self.producer.send(topic, value=msg, key=key)
            futures.append(future)

        self.producer.flush()
        return futures

    def close(self):
        self.producer.close()


class KafkaCrawlerConsumer:
    """Kafka 消费者"""

    def __init__(
        self,
        config: KafkaConfig,
        group_id: str,
        topics: List[str]
    ):
        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=config.bootstrap_servers,
            group_id=group_id,
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            max_poll_records=100,
            session_timeout_ms=30000,
        )
        self.running = False

    def consume(self, callback: Callable[[Dict], bool]):
        """消费消息"""

        self.running = True

        while self.running:
            messages = self.consumer.poll(timeout_ms=1000)

            for topic_partition, records in messages.items():
                for record in records:
                    try:
                        success = callback(record.value)
                        if success:
                            self.consumer.commit()
                    except Exception as e:
                        print(f"Error: {e}")

    def stop(self):
        self.running = False
        self.consumer.close()


# 使用示例
config = KafkaConfig()

# 生产者
producer = KafkaCrawlerProducer(config)
producer.create_topic("crawl_tasks", partitions=6)
producer.send_batch("crawl_tasks", [
    {"url": "https://example.com/1", "priority": 1},
    {"url": "https://example.com/2", "priority": 2},
])
producer.close()

# 消费者（多实例运行实现并行）
consumer = KafkaCrawlerConsumer(config, group_id="crawler_group", topics=["crawl_tasks"])
consumer.consume(lambda msg: print(f"Processing: {msg['url']}") or True)
```

---

## 任务调度

### APScheduler 定时调度

```python
"""
使用 APScheduler 实现定时任务调度
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import pytz


class CrawlScheduler:
    """爬虫定时调度器"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        jobstores = {
            'default': RedisJobStore(host='localhost', port=6379, db=2),
        }

        executors = {
            'default': ThreadPoolExecutor(20),
            'processpool': ProcessPoolExecutor(5),
        }

        job_defaults = {
            'coalesce': True,  # 错过的任务只执行一次
            'max_instances': 3,
            'misfire_grace_time': 60,
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.timezone('Asia/Shanghai'),
        )

    def start(self):
        """启动调度器"""
        self.scheduler.start()

    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()

    def add_cron_job(
        self,
        func,
        job_id: str,
        cron_expression: str,
        **kwargs
    ):
        """
        添加 Cron 任务

        Args:
            func: 任务函数
            job_id: 任务ID
            cron_expression: Cron 表达式 "分 时 日 月 周"
        """

        parts = cron_expression.split()
        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
        )

        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **kwargs
        )

    def add_interval_job(
        self,
        func,
        job_id: str,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        **kwargs
    ):
        """添加间隔任务"""

        trigger = IntervalTrigger(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
        )

        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **kwargs
        )

    def remove_job(self, job_id: str):
        """移除任务"""
        self.scheduler.remove_job(job_id)

    def pause_job(self, job_id: str):
        """暂停任务"""
        self.scheduler.pause_job(job_id)

    def resume_job(self, job_id: str):
        """恢复任务"""
        self.scheduler.resume_job(job_id)

    def get_jobs(self):
        """获取所有任务"""
        return self.scheduler.get_jobs()


# 定义爬取任务
def crawl_daily_data():
    """每日数据采集"""
    print(f"[{datetime.now()}] Running daily crawl...")
    # 爬取逻辑


def crawl_hourly_updates():
    """每小时增量更新"""
    print(f"[{datetime.now()}] Running hourly update...")
    # 爬取逻辑


# 使用
scheduler = CrawlScheduler()

# 每天凌晨 2 点执行
scheduler.add_cron_job(crawl_daily_data, "daily_crawl", "0 2 * * *")

# 每小时执行
scheduler.add_interval_job(crawl_hourly_updates, "hourly_update", hours=1)

scheduler.start()

# 保持运行
try:
    while True:
        pass
except KeyboardInterrupt:
    scheduler.shutdown()
```

---

## URL 去重

### Bloom Filter 去重

```python
"""
使用 Bloom Filter 实现高效 URL 去重
"""

import mmh3
from bitarray import bitarray
import math
from typing import Optional
import redis


class BloomFilter:
    """内存 Bloom Filter"""

    def __init__(
        self,
        expected_items: int = 1000000,
        false_positive_rate: float = 0.01
    ):
        # 计算最佳参数
        self.size = self._get_size(expected_items, false_positive_rate)
        self.hash_count = self._get_hash_count(self.size, expected_items)

        self.bit_array = bitarray(self.size)
        self.bit_array.setall(0)

    def add(self, item: str):
        """添加元素"""
        for seed in range(self.hash_count):
            index = mmh3.hash(item, seed) % self.size
            self.bit_array[index] = 1

    def contains(self, item: str) -> bool:
        """检查元素是否存在"""
        for seed in range(self.hash_count):
            index = mmh3.hash(item, seed) % self.size
            if not self.bit_array[index]:
                return False
        return True

    def add_if_not_exists(self, item: str) -> bool:
        """添加元素，返回是否为新元素"""
        if self.contains(item):
            return False
        self.add(item)
        return True

    def _get_size(self, n: int, p: float) -> int:
        """计算 bit 数组大小"""
        return int(-(n * math.log(p)) / (math.log(2) ** 2))

    def _get_hash_count(self, m: int, n: int) -> int:
        """计算哈希函数数量"""
        return int((m / n) * math.log(2))


class RedisBloomFilter:
    """Redis Bloom Filter（支持分布式）"""

    def __init__(
        self,
        redis_client: redis.Redis,
        key: str = "crawler:bloom",
        expected_items: int = 10000000,
        false_positive_rate: float = 0.001
    ):
        self.redis = redis_client
        self.key = key
        self.size = self._get_size(expected_items, false_positive_rate)
        self.hash_count = self._get_hash_count(self.size, expected_items)

    def add(self, item: str):
        """添加元素"""
        pipeline = self.redis.pipeline()
        for seed in range(self.hash_count):
            index = mmh3.hash(item, seed) % self.size
            pipeline.setbit(self.key, index, 1)
        pipeline.execute()

    def contains(self, item: str) -> bool:
        """检查元素"""
        pipeline = self.redis.pipeline()
        for seed in range(self.hash_count):
            index = mmh3.hash(item, seed) % self.size
            pipeline.getbit(self.key, index)

        results = pipeline.execute()
        return all(results)

    def add_if_not_exists(self, item: str) -> bool:
        """添加并返回是否新增"""
        # 使用 Lua 脚本保证原子性
        script = """
        local key = KEYS[1]
        local hash_count = tonumber(ARGV[1])
        local size = tonumber(ARGV[2])

        -- 检查是否存在
        local exists = true
        for i = 3, 3 + hash_count - 1 do
            local index = tonumber(ARGV[i])
            if redis.call('GETBIT', key, index) == 0 then
                exists = false
                break
            end
        end

        if exists then
            return 0
        end

        -- 添加
        for i = 3, 3 + hash_count - 1 do
            local index = tonumber(ARGV[i])
            redis.call('SETBIT', key, index, 1)
        end

        return 1
        """

        indices = [mmh3.hash(item, seed) % self.size for seed in range(self.hash_count)]
        args = [self.hash_count, self.size] + indices

        result = self.redis.eval(script, 1, self.key, *args)
        return result == 1

    def _get_size(self, n: int, p: float) -> int:
        return int(-(n * math.log(p)) / (math.log(2) ** 2))

    def _get_hash_count(self, m: int, n: int) -> int:
        return int((m / n) * math.log(2))


# 使用示例
class DeduplicatedCrawler:
    """带去重的爬虫"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
        self.bloom = RedisBloomFilter(
            self.redis,
            expected_items=10000000,
            false_positive_rate=0.0001
        )

    def should_crawl(self, url: str) -> bool:
        """判断是否应该爬取"""
        # 规范化 URL
        normalized_url = self._normalize_url(url)
        return self.bloom.add_if_not_exists(normalized_url)

    def _normalize_url(self, url: str) -> str:
        """URL 规范化"""
        from urllib.parse import urlparse, urlencode, parse_qs

        parsed = urlparse(url)

        # 排序查询参数
        query = parse_qs(parsed.query)
        sorted_query = urlencode(sorted(query.items()), doseq=True)

        # 重建 URL
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{sorted_query}"
```

---

## 分布式锁

### Redis 分布式锁

```python
"""
Redis 分布式锁实现
"""

import redis
import time
import uuid
from contextlib import contextmanager
from typing import Optional


class DistributedLock:
    """分布式锁"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def acquire(
        self,
        lock_name: str,
        timeout: int = 10,
        retry_interval: float = 0.1,
        max_retries: int = 100
    ) -> Optional[str]:
        """
        获取锁

        Args:
            lock_name: 锁名称
            timeout: 锁超时时间（秒）
            retry_interval: 重试间隔（秒）
            max_retries: 最大重试次数

        Returns:
            str: 锁标识符，获取失败返回 None
        """

        lock_key = f"lock:{lock_name}"
        lock_id = str(uuid.uuid4())

        for _ in range(max_retries):
            # 尝试设置锁
            if self.redis.set(lock_key, lock_id, nx=True, ex=timeout):
                return lock_id

            time.sleep(retry_interval)

        return None

    def release(self, lock_name: str, lock_id: str) -> bool:
        """
        释放锁

        Args:
            lock_name: 锁名称
            lock_id: 锁标识符

        Returns:
            bool: 是否成功释放
        """

        lock_key = f"lock:{lock_name}"

        # 使用 Lua 脚本保证原子性
        script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        else
            return 0
        end
        """

        result = self.redis.eval(script, 1, lock_key, lock_id)
        return result == 1

    def extend(self, lock_name: str, lock_id: str, timeout: int) -> bool:
        """
        延长锁时间

        Args:
            lock_name: 锁名称
            lock_id: 锁标识符
            timeout: 新的超时时间

        Returns:
            bool: 是否成功延长
        """

        lock_key = f"lock:{lock_name}"

        script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('EXPIRE', KEYS[1], ARGV[2])
        else
            return 0
        end
        """

        result = self.redis.eval(script, 1, lock_key, lock_id, timeout)
        return result == 1

    @contextmanager
    def lock(
        self,
        lock_name: str,
        timeout: int = 10,
        retry_interval: float = 0.1,
        max_retries: int = 100
    ):
        """
        上下文管理器方式使用锁

        with lock.lock("my_resource"):
            # 临界区代码
        """

        lock_id = self.acquire(lock_name, timeout, retry_interval, max_retries)

        if lock_id is None:
            raise Exception(f"Failed to acquire lock: {lock_name}")

        try:
            yield lock_id
        finally:
            self.release(lock_name, lock_id)


# 使用示例
class DistributedCrawler:
    """使用分布式锁的爬虫"""

    def __init__(self):
        self.redis = redis.Redis()
        self.lock = DistributedLock(self.redis)

    def crawl_with_lock(self, resource_id: str):
        """带锁的爬取（确保同一资源不会并发访问）"""

        with self.lock.lock(f"resource:{resource_id}", timeout=60):
            # 只有一个 Worker 能执行这里
            self._do_crawl(resource_id)

    def _do_crawl(self, resource_id: str):
        """实际爬取逻辑"""
        pass
```

---

## 负载均衡

### IP 代理负载均衡

```python
"""
代理 IP 负载均衡
"""

from typing import List, Dict, Optional
import random
import time
from dataclasses import dataclass, field
from collections import defaultdict
import threading


@dataclass
class ProxyStats:
    """代理统计"""
    success_count: int = 0
    fail_count: int = 0
    total_time: float = 0.0
    last_used: float = 0.0
    banned_until: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 0.5

    @property
    def avg_response_time(self) -> float:
        return self.total_time / self.success_count if self.success_count > 0 else 999

    @property
    def is_banned(self) -> bool:
        return time.time() < self.banned_until


class ProxyLoadBalancer:
    """代理负载均衡器"""

    def __init__(self, proxies: List[str]):
        self.proxies = proxies
        self.stats: Dict[str, ProxyStats] = {p: ProxyStats() for p in proxies}
        self.lock = threading.Lock()

        # 每个域名单独统计
        self.domain_stats: Dict[str, Dict[str, ProxyStats]] = defaultdict(
            lambda: {p: ProxyStats() for p in self.proxies}
        )

    def get_proxy(self, domain: str = None, strategy: str = "weighted") -> Optional[str]:
        """
        获取代理

        Args:
            domain: 目标域名（用于域名级负载均衡）
            strategy: 策略 - "random", "round_robin", "weighted", "least_connections"

        Returns:
            str: 代理地址
        """

        with self.lock:
            # 获取对应的统计数据
            stats = self.domain_stats[domain] if domain else self.stats

            # 过滤被封禁的代理
            available = [p for p, s in stats.items() if not s.is_banned]

            if not available:
                # 所有代理都被封，返回封禁时间最短的
                return min(stats.items(), key=lambda x: x[1].banned_until)[0]

            if strategy == "random":
                return random.choice(available)

            elif strategy == "weighted":
                # 基于成功率和响应时间的加权选择
                weights = []
                for proxy in available:
                    s = stats[proxy]
                    # 权重 = 成功率 / (平均响应时间 + 1)
                    weight = s.success_rate / (s.avg_response_time + 1)
                    weights.append(weight)

                total = sum(weights)
                if total == 0:
                    return random.choice(available)

                r = random.uniform(0, total)
                cumulative = 0
                for proxy, weight in zip(available, weights):
                    cumulative += weight
                    if r <= cumulative:
                        return proxy

                return available[-1]

            elif strategy == "least_connections":
                # 选择最近最少使用的
                return min(available, key=lambda p: stats[p].last_used)

            else:
                return random.choice(available)

    def report_success(self, proxy: str, response_time: float, domain: str = None):
        """报告成功"""
        with self.lock:
            stats = self.domain_stats[domain] if domain else self.stats

            if proxy in stats:
                stats[proxy].success_count += 1
                stats[proxy].total_time += response_time
                stats[proxy].last_used = time.time()

    def report_failure(self, proxy: str, domain: str = None, ban_seconds: int = 0):
        """报告失败"""
        with self.lock:
            stats = self.domain_stats[domain] if domain else self.stats

            if proxy in stats:
                stats[proxy].fail_count += 1
                stats[proxy].last_used = time.time()

                if ban_seconds > 0:
                    stats[proxy].banned_until = time.time() + ban_seconds

    def get_stats(self, domain: str = None) -> Dict[str, Dict]:
        """获取统计信息"""
        stats = self.domain_stats[domain] if domain else self.stats

        return {
            proxy: {
                "success_rate": s.success_rate,
                "avg_response_time": s.avg_response_time,
                "is_banned": s.is_banned,
                "total_requests": s.success_count + s.fail_count,
            }
            for proxy, s in stats.items()
        }


# 使用示例
proxies = [
    "http://proxy1:8080",
    "http://proxy2:8080",
    "http://proxy3:8080",
]

balancer = ProxyLoadBalancer(proxies)

# 爬取时使用
async def crawl(url: str):
    from urllib.parse import urlparse
    domain = urlparse(url).netloc

    proxy = balancer.get_proxy(domain, strategy="weighted")

    start_time = time.time()
    try:
        # 使用代理请求
        async with httpx.AsyncClient(proxy=proxy) as client:
            response = await client.get(url)

        response_time = time.time() - start_time
        balancer.report_success(proxy, response_time, domain)
        return response

    except Exception as e:
        # 根据错误类型决定封禁时间
        if "banned" in str(e).lower():
            balancer.report_failure(proxy, domain, ban_seconds=300)
        else:
            balancer.report_failure(proxy, domain)
        raise
```

---

## 数据同步

### 数据分片存储

```python
"""
数据分片存储 - 支持水平扩展
"""

import hashlib
from typing import List, Dict, Any
from pymongo import MongoClient
import redis


class ShardedStorage:
    """分片存储"""

    def __init__(self, shards: List[str]):
        """
        Args:
            shards: MongoDB 连接字符串列表
        """
        self.shard_count = len(shards)
        self.clients = [MongoClient(s) for s in shards]

    def _get_shard(self, key: str) -> MongoClient:
        """根据 key 获取对应的分片"""
        # 一致性哈希
        hash_value = int(hashlib.md5(key.encode()).hexdigest(), 16)
        shard_index = hash_value % self.shard_count
        return self.clients[shard_index]

    def save(self, collection: str, key: str, data: Dict):
        """保存数据"""
        client = self._get_shard(key)
        db = client.crawler
        db[collection].update_one(
            {"_id": key},
            {"$set": data},
            upsert=True
        )

    def get(self, collection: str, key: str) -> Dict:
        """获取数据"""
        client = self._get_shard(key)
        db = client.crawler
        return db[collection].find_one({"_id": key})

    def query_all(self, collection: str, query: Dict) -> List[Dict]:
        """查询所有分片"""
        results = []
        for client in self.clients:
            db = client.crawler
            results.extend(db[collection].find(query))
        return results


class ConsistentHash:
    """一致性哈希"""

    def __init__(self, nodes: List[str], virtual_nodes: int = 150):
        self.ring = {}
        self.sorted_keys = []
        self.virtual_nodes = virtual_nodes

        for node in nodes:
            self.add_node(node)

    def add_node(self, node: str):
        """添加节点"""
        for i in range(self.virtual_nodes):
            key = self._hash(f"{node}:{i}")
            self.ring[key] = node

        self.sorted_keys = sorted(self.ring.keys())

    def remove_node(self, node: str):
        """移除节点"""
        for i in range(self.virtual_nodes):
            key = self._hash(f"{node}:{i}")
            if key in self.ring:
                del self.ring[key]

        self.sorted_keys = sorted(self.ring.keys())

    def get_node(self, key: str) -> str:
        """获取 key 对应的节点"""
        if not self.ring:
            return None

        hash_key = self._hash(key)

        # 二分查找
        import bisect
        idx = bisect.bisect(self.sorted_keys, hash_key)

        if idx == len(self.sorted_keys):
            idx = 0

        return self.ring[self.sorted_keys[idx]]

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)
```

---

## 容错与恢复

### 任务持久化与恢复

```python
"""
任务持久化与故障恢复
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import redis


@dataclass
class CrawlState:
    """爬取状态"""
    task_id: str
    total_urls: int
    crawled_count: int
    failed_count: int
    pending_urls: List[str]
    failed_urls: List[Dict]
    last_checkpoint: str
    status: str  # "running", "paused", "completed", "failed"


class CheckpointManager:
    """检查点管理器"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.checkpoint_key = "crawler:checkpoints"

    def save_checkpoint(self, state: CrawlState):
        """保存检查点"""
        state.last_checkpoint = datetime.now().isoformat()
        self.redis.hset(
            self.checkpoint_key,
            state.task_id,
            json.dumps(asdict(state))
        )

    def load_checkpoint(self, task_id: str) -> Optional[CrawlState]:
        """加载检查点"""
        data = self.redis.hget(self.checkpoint_key, task_id)
        if data:
            return CrawlState(**json.loads(data))
        return None

    def list_checkpoints(self) -> List[CrawlState]:
        """列出所有检查点"""
        checkpoints = []
        for task_id, data in self.redis.hgetall(self.checkpoint_key).items():
            checkpoints.append(CrawlState(**json.loads(data)))
        return checkpoints

    def delete_checkpoint(self, task_id: str):
        """删除检查点"""
        self.redis.hdel(self.checkpoint_key, task_id)


class ResumableCrawler:
    """可恢复的爬虫"""

    def __init__(self, task_id: str, redis_url: str = "redis://localhost:6379"):
        self.task_id = task_id
        self.redis = redis.from_url(redis_url)
        self.checkpoint_mgr = CheckpointManager(self.redis)
        self.state: Optional[CrawlState] = None

        # 检查点保存间隔
        self.checkpoint_interval = 100

    def start(self, urls: List[str], resume: bool = True):
        """
        开始爬取

        Args:
            urls: URL 列表
            resume: 是否从检查点恢复
        """

        if resume:
            self.state = self.checkpoint_mgr.load_checkpoint(self.task_id)

        if self.state is None:
            self.state = CrawlState(
                task_id=self.task_id,
                total_urls=len(urls),
                crawled_count=0,
                failed_count=0,
                pending_urls=urls,
                failed_urls=[],
                last_checkpoint=datetime.now().isoformat(),
                status="running"
            )

        print(f"Starting crawl: {self.state.crawled_count}/{self.state.total_urls}")

        try:
            self._run()
        except KeyboardInterrupt:
            print("\nPausing...")
            self.state.status = "paused"
            self.checkpoint_mgr.save_checkpoint(self.state)
            print(f"Checkpoint saved. Resume with task_id: {self.task_id}")

    def _run(self):
        """执行爬取"""
        count = 0

        while self.state.pending_urls:
            url = self.state.pending_urls.pop(0)

            try:
                self._crawl_url(url)
                self.state.crawled_count += 1
            except Exception as e:
                self.state.failed_count += 1
                self.state.failed_urls.append({
                    "url": url,
                    "error": str(e),
                    "time": datetime.now().isoformat()
                })

            count += 1
            if count % self.checkpoint_interval == 0:
                self.checkpoint_mgr.save_checkpoint(self.state)
                print(f"Checkpoint: {self.state.crawled_count}/{self.state.total_urls}")

        self.state.status = "completed"
        self.checkpoint_mgr.save_checkpoint(self.state)
        print(f"Completed: {self.state.crawled_count} success, {self.state.failed_count} failed")

    def _crawl_url(self, url: str):
        """爬取单个 URL"""
        import httpx
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        # 处理响应...

    def retry_failed(self):
        """重试失败的任务"""
        if self.state is None:
            self.state = self.checkpoint_mgr.load_checkpoint(self.task_id)

        if self.state and self.state.failed_urls:
            urls = [f["url"] for f in self.state.failed_urls]
            self.state.failed_urls = []
            self.state.pending_urls = urls
            self.state.status = "running"
            self._run()


# 使用示例
crawler = ResumableCrawler("job_001")
crawler.start([
    "https://example.com/page/1",
    "https://example.com/page/2",
    # ...
], resume=True)

# 重试失败的
crawler.retry_failed()
```

---

## 诊断日志

```
# Master 节点
[MASTER] 启动主节点: redis://localhost:6379
[MASTER] 任务提交: 1000 URLs (去重后: 987)
[MASTER] 当前状态: pending=987, workers=5, completed=0

# Worker 节点
[WORKER-a1b2] 启动: 连接 Master 成功
[WORKER-a1b2] 领取任务: https://example.com/page/1
[WORKER-a1b2] 任务完成: 200 OK (耗时 1.2s)
[WORKER-a1b2] 心跳: alive (已处理: 156)

# 任务调度
[SCHED] 任务分发: task_123 -> worker-a1b2
[SCHED] 优先级调整: high_priority +100 任务
[SCHED] 限流触发: worker-c3d4 暂停 30s (目标域名限速)

# 去重过滤
[DEDUP] URL 已存在: https://example.com/page/1 (跳过)
[DEDUP] 新增 URL: https://example.com/page/2 (加入队列)
[DEDUP] Bloom Filter 状态: 10M items, 0.001% FP rate

# 故障恢复
[RECOVER] Worker-c3d4 失联 (>30s)
[RECOVER] 回收任务: 5 个任务重新入队
[RECOVER] 检查点加载: job_001 (crawled=500, pending=487)

# 负载均衡
[LB] 代理分配: http://proxy1:8080 (成功率: 95%, 响应: 1.2s)
[LB] 代理封禁: http://proxy2:8080 (封禁 300s)
[LB] 策略调整: weighted -> least_connections

# 错误情况
[MASTER] ERROR: Redis 连接失败，重试中...
[WORKER] ERROR: 任务执行超时 (>60s)
[DEDUP] WARN: Bloom Filter 接近容量上限 (90%)
```

---

## 相关模块

- **上游**: [07-调度模块](07-scheduling.md) - 单机调度
- **配合**: [04-请求模块](04-request.md) - 代理管理
- **配合**: [14-监控模块](14-monitoring.md) - 集群监控
- **配合**: [16-战术模块](16-tactics.md) - 分布式环境下的策略协调
- **下游**: [06-存储模块](06-storage.md) - 数据持久化

---

## 常见问题

### Q: 如何选择消息队列？

| 场景 | 推荐 | 原因 |
|-----|-----|-----|
| 小规模/快速开发 | Redis | 简单，性能好 |
| 可靠性要求高 | RabbitMQ | 消息确认机制完善 |
| 高吞吐量 | Kafka | 专为大数据设计 |
| 已有 Redis | Redis + Celery | 复用基础设施 |

### Q: Worker 数量如何设置？

- CPU 密集型（解析）: Worker 数 = CPU 核心数
- IO 密集型（请求）: Worker 数 = CPU 核心数 × (1 + IO等待时间/CPU时间)
- 一般建议从 10 个 Worker 开始，根据监控调整

### Q: 如何处理分布式环境的 Cookie/Session？

1. 使用 Redis 共享 Session 存储
2. 每个 Worker 独立维护 Cookie，按域名分配任务
3. 使用 Token 认证代替 Cookie
