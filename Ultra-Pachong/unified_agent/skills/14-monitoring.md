# 14 - 监控告警模块 (Monitoring & Alerting)

---
name: monitoring-alerting
version: 1.0.0
description: 爬虫运行监控、性能分析与异常告警
triggers:
  - "监控"
  - "告警"
  - "monitoring"
  - "alerting"
  - "metrics"
  - "日志"
difficulty: ⭐⭐⭐
---

## 模块目标

**核心原则：给出需求，必须完成。**

| 目标 | 达成标准 |
|------|---------|
| **指标全采集** | 请求量/错误率/延迟/队列长度等核心指标实时可见 |
| **告警及时** | 异常发生后 1 分钟内触发告警，通知到相关人员 |
| **日志可查** | 结构化日志支持快速检索和问题定位 |
| **链路可追踪** | 分布式场景下请求全链路可追溯 |
| **仪表盘直观** | Grafana 仪表盘一目了然，关键指标可视化 |

---

## 模块概述

监控告警模块负责实时监控爬虫运行状态、收集性能指标、分析日志、及时发现问题并告警。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           监控告警架构                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         数据采集层                                   │  │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │  │
│   │  │ 指标采集  │ │ 日志采集  │ │ 链路追踪  │ │ 健康检查  │              │  │
│   │  │Prometheus│ │  Loki    │ │  Jaeger  │ │HealthChk │              │  │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         存储层                                       │  │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐                           │  │
│   │  │ 时序数据库 │ │ 日志存储  │ │ 追踪存储  │                           │  │
│   │  │   TSDB   │ │   ES    │ │  Jaeger  │                           │  │
│   │  └──────────┘ └──────────┘ └──────────┘                           │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         展示与告警层                                  │  │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │  │
│   │  │ Grafana  │ │AlertMgr │ │ 钉钉/飞书 │ │  邮件    │              │  │
│   │  │  仪表盘   │ │ 告警规则  │ │  Webhook │ │  SMTP   │              │  │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 指标采集

### Prometheus 指标

```python
"""
Prometheus 指标采集
"""

from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
    start_http_server
)
from functools import wraps
import time
from typing import Callable
from dataclasses import dataclass


# 创建指标
class CrawlerMetrics:
    """爬虫指标"""

    def __init__(self, registry: CollectorRegistry = None):
        self.registry = registry or CollectorRegistry()

        # 请求计数器
        self.requests_total = Counter(
            'crawler_requests_total',
            'Total number of HTTP requests',
            ['method', 'domain', 'status_code'],
            registry=self.registry
        )

        # 请求延迟直方图
        self.request_duration = Histogram(
            'crawler_request_duration_seconds',
            'HTTP request duration in seconds',
            ['domain'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )

        # 活跃任务数
        self.active_tasks = Gauge(
            'crawler_active_tasks',
            'Number of active crawl tasks',
            ['worker_id'],
            registry=self.registry
        )

        # 队列长度
        self.queue_size = Gauge(
            'crawler_queue_size',
            'Number of URLs in queue',
            ['queue_name'],
            registry=self.registry
        )

        # 错误计数器
        self.errors_total = Counter(
            'crawler_errors_total',
            'Total number of errors',
            ['error_type', 'domain'],
            registry=self.registry
        )

        # 数据采集量
        self.items_scraped = Counter(
            'crawler_items_scraped_total',
            'Total number of items scraped',
            ['spider', 'item_type'],
            registry=self.registry
        )

        # 代理使用情况
        self.proxy_requests = Counter(
            'crawler_proxy_requests_total',
            'Total proxy requests',
            ['proxy', 'status'],
            registry=self.registry
        )

        # 验证码遇到次数
        self.captcha_encountered = Counter(
            'crawler_captcha_total',
            'Total captchas encountered',
            ['domain', 'captcha_type'],
            registry=self.registry
        )

        # 内存使用
        self.memory_usage = Gauge(
            'crawler_memory_bytes',
            'Memory usage in bytes',
            ['type'],
            registry=self.registry
        )

        # 响应大小
        self.response_size = Summary(
            'crawler_response_size_bytes',
            'Response size in bytes',
            ['domain'],
            registry=self.registry
        )

    def record_request(
        self,
        domain: str,
        method: str,
        status_code: int,
        duration: float,
        response_size: int
    ):
        """记录请求"""
        self.requests_total.labels(
            method=method,
            domain=domain,
            status_code=str(status_code)
        ).inc()

        self.request_duration.labels(domain=domain).observe(duration)
        self.response_size.labels(domain=domain).observe(response_size)

    def record_error(self, error_type: str, domain: str):
        """记录错误"""
        self.errors_total.labels(error_type=error_type, domain=domain).inc()

    def record_item(self, spider: str, item_type: str, count: int = 1):
        """记录采集项"""
        self.items_scraped.labels(spider=spider, item_type=item_type).inc(count)


# 装饰器方式使用
def track_request(metrics: CrawlerMetrics, domain: str):
    """请求追踪装饰器"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                response = await func(*args, **kwargs)
                duration = time.time() - start_time

                metrics.record_request(
                    domain=domain,
                    method=getattr(response, 'request', {}).get('method', 'GET'),
                    status_code=response.status_code,
                    duration=duration,
                    response_size=len(response.content)
                )

                return response

            except Exception as e:
                metrics.record_error(type(e).__name__, domain)
                raise

        return wrapper
    return decorator


# 指标服务器
class MetricsServer:
    """指标暴露服务"""

    def __init__(self, metrics: CrawlerMetrics, port: int = 9090):
        self.metrics = metrics
        self.port = port

    def start(self):
        """启动指标服务器"""
        start_http_server(self.port, registry=self.metrics.registry)
        print(f"Metrics server started on port {self.port}")

    def get_metrics(self) -> bytes:
        """获取指标数据"""
        return generate_latest(self.metrics.registry)


# 使用示例
metrics = CrawlerMetrics()
metrics_server = MetricsServer(metrics)
metrics_server.start()

# 爬取时记录
@track_request(metrics, "example.com")
async def fetch_page(url: str):
    import httpx
    async with httpx.AsyncClient() as client:
        return await client.get(url)
```

### 自定义指标收集器

```python
"""
自定义 Prometheus 收集器
"""

from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
from prometheus_client import CollectorRegistry, REGISTRY
import redis


class CrawlerStatsCollector:
    """爬虫状态收集器"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def collect(self):
        """收集指标"""

        # 队列指标
        queue_gauge = GaugeMetricFamily(
            'crawler_queue_length',
            'Length of crawler queues',
            labels=['queue']
        )

        queues = ['pending', 'processing', 'completed', 'failed']
        for queue in queues:
            length = self.redis.llen(f"crawler:{queue}")
            queue_gauge.add_metric([queue], length)

        yield queue_gauge

        # Worker 状态
        worker_gauge = GaugeMetricFamily(
            'crawler_workers',
            'Number of workers by status',
            labels=['status']
        )

        workers = self.redis.hgetall("crawler:workers")
        status_counts = {'idle': 0, 'busy': 0, 'error': 0}

        for worker_id, data in workers.items():
            import json
            info = json.loads(data)
            status = info.get('status', 'unknown')
            if status in status_counts:
                status_counts[status] += 1

        for status, count in status_counts.items():
            worker_gauge.add_metric([status], count)

        yield worker_gauge

        # 今日统计
        today_counter = CounterMetricFamily(
            'crawler_today_total',
            'Today statistics',
            labels=['metric']
        )

        today_stats = {
            'requests': self.redis.get("stats:today:requests") or 0,
            'success': self.redis.get("stats:today:success") or 0,
            'failed': self.redis.get("stats:today:failed") or 0,
            'items': self.redis.get("stats:today:items") or 0,
        }

        for metric, value in today_stats.items():
            today_counter.add_metric([metric], int(value))

        yield today_counter


# 注册收集器
redis_client = redis.Redis()
REGISTRY.register(CrawlerStatsCollector(redis_client))
```

---

## 日志系统

### 结构化日志

```python
"""
结构化日志系统
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict
import sys
from dataclasses import dataclass, asdict
import traceback


class JsonFormatter(logging.Formatter):
    """JSON 格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加额外字段
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        return json.dumps(log_data, ensure_ascii=False)


class CrawlerLogger:
    """爬虫日志器"""

    def __init__(
        self,
        name: str = "crawler",
        level: int = logging.INFO,
        json_output: bool = True
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # 移除已有处理器
        self.logger.handlers = []

        # 控制台处理器
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        if json_output:
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))

        self.logger.addHandler(handler)

    def _log(self, level: int, msg: str, **kwargs):
        """内部日志方法"""
        extra = {'extra_data': kwargs} if kwargs else {}
        self.logger.log(level, msg, extra=extra)

    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self._log(logging.ERROR, msg, **kwargs)

    def exception(self, msg: str, **kwargs):
        self.logger.exception(msg, extra={'extra_data': kwargs})

    # 爬虫专用方法
    def request(
        self,
        url: str,
        method: str,
        status_code: int,
        duration: float,
        **kwargs
    ):
        """记录请求日志"""
        self.info(
            f"HTTP {method} {url}",
            event="http_request",
            url=url,
            method=method,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )

    def item_scraped(self, item_type: str, item_id: str, **kwargs):
        """记录采集日志"""
        self.info(
            f"Scraped {item_type}: {item_id}",
            event="item_scraped",
            item_type=item_type,
            item_id=item_id,
            **kwargs
        )

    def captcha(self, domain: str, captcha_type: str, success: bool, **kwargs):
        """记录验证码日志"""
        self.info(
            f"Captcha {captcha_type} on {domain}: {'success' if success else 'failed'}",
            event="captcha",
            domain=domain,
            captcha_type=captcha_type,
            success=success,
            **kwargs
        )

    def proxy_error(self, proxy: str, error: str, **kwargs):
        """记录代理错误"""
        self.warning(
            f"Proxy error: {proxy}",
            event="proxy_error",
            proxy=proxy,
            error=error,
            **kwargs
        )


# 使用示例
logger = CrawlerLogger("my_spider")

logger.request(
    url="https://example.com/api/products",
    method="GET",
    status_code=200,
    duration=0.235,
    proxy="http://proxy:8080"
)

logger.item_scraped(
    item_type="product",
    item_id="12345",
    title="Example Product",
    price=99.99
)
```

### 日志聚合 (Loki)

```python
"""
Loki 日志推送
"""

import httpx
import time
from typing import List, Dict
from dataclasses import dataclass
import json


@dataclass
class LokiConfig:
    url: str = "http://localhost:3100"
    batch_size: int = 100
    flush_interval: float = 5.0


class LokiHandler:
    """Loki 日志处理器"""

    def __init__(self, config: LokiConfig, labels: Dict[str, str]):
        self.config = config
        self.labels = labels
        self.buffer: List[tuple] = []
        self.last_flush = time.time()

    def push(self, message: str, level: str = "info", **extra_labels):
        """推送日志"""

        timestamp = str(int(time.time() * 1e9))  # 纳秒时间戳
        all_labels = {**self.labels, "level": level, **extra_labels}

        self.buffer.append((timestamp, message, all_labels))

        # 检查是否需要刷新
        if len(self.buffer) >= self.config.batch_size:
            self.flush()
        elif time.time() - self.last_flush > self.config.flush_interval:
            self.flush()

    def flush(self):
        """刷新缓冲区到 Loki"""

        if not self.buffer:
            return

        # 按标签分组
        streams = {}
        for timestamp, message, labels in self.buffer:
            label_key = json.dumps(labels, sort_keys=True)
            if label_key not in streams:
                streams[label_key] = {
                    "stream": labels,
                    "values": []
                }
            streams[label_key]["values"].append([timestamp, message])

        # 构建请求体
        payload = {"streams": list(streams.values())}

        # 发送到 Loki
        try:
            httpx.post(
                f"{self.config.url}/loki/api/v1/push",
                json=payload,
                timeout=10
            )
        except Exception as e:
            print(f"Failed to push logs to Loki: {e}")

        self.buffer = []
        self.last_flush = time.time()


# 集成到 Python logging
import logging


class LokiLoggingHandler(logging.Handler):
    """Python logging 的 Loki 处理器"""

    def __init__(self, loki_handler: LokiHandler):
        super().__init__()
        self.loki = loki_handler

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            extra = {}

            # 提取额外字段
            if hasattr(record, 'extra_data'):
                for k, v in record.extra_data.items():
                    if isinstance(v, (str, int, float, bool)):
                        extra[k] = str(v)

            self.loki.push(msg, record.levelname.lower(), **extra)

        except Exception:
            self.handleError(record)


# 使用示例
loki_handler = LokiHandler(
    LokiConfig(url="http://localhost:3100"),
    labels={"job": "crawler", "env": "production"}
)

logger = logging.getLogger("crawler")
logger.addHandler(LokiLoggingHandler(loki_handler))
```

---

## 告警系统

### 告警规则

```python
"""
告警规则引擎
"""

from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any, Optional
from enum import Enum
from datetime import datetime, timedelta
import asyncio


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    description: str
    severity: AlertSeverity
    condition: Callable[[Dict], bool]
    cooldown: int = 300  # 冷却时间（秒）
    labels: Dict[str, str] = field(default_factory=dict)

    # 运行时状态
    last_triggered: Optional[datetime] = None
    is_firing: bool = False


@dataclass
class Alert:
    """告警实例"""
    rule_name: str
    severity: AlertSeverity
    description: str
    labels: Dict[str, str]
    annotations: Dict[str, Any]
    starts_at: datetime
    ends_at: Optional[datetime] = None


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self.rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.handlers: List[Callable[[Alert], None]] = []

    def add_rule(self, rule: AlertRule):
        """添加规则"""
        self.rules.append(rule)

    def add_handler(self, handler: Callable[[Alert], None]):
        """添加告警处理器"""
        self.handlers.append(handler)

    def evaluate(self, metrics: Dict):
        """评估所有规则"""

        now = datetime.now()

        for rule in self.rules:
            try:
                is_triggered = rule.condition(metrics)
            except Exception as e:
                print(f"Rule {rule.name} evaluation failed: {e}")
                continue

            alert_key = f"{rule.name}:{hash(frozenset(rule.labels.items()))}"

            if is_triggered:
                # 检查冷却时间
                if rule.last_triggered:
                    if (now - rule.last_triggered).seconds < rule.cooldown:
                        continue

                if not rule.is_firing:
                    # 新告警
                    alert = Alert(
                        rule_name=rule.name,
                        severity=rule.severity,
                        description=rule.description,
                        labels=rule.labels,
                        annotations={"metrics": metrics},
                        starts_at=now,
                    )
                    self.active_alerts[alert_key] = alert
                    rule.is_firing = True
                    rule.last_triggered = now

                    # 触发处理器
                    self._fire_alert(alert)

            else:
                if rule.is_firing:
                    # 告警恢复
                    if alert_key in self.active_alerts:
                        alert = self.active_alerts[alert_key]
                        alert.ends_at = now
                        self._resolve_alert(alert)
                        del self.active_alerts[alert_key]

                    rule.is_firing = False

    def _fire_alert(self, alert: Alert):
        """触发告警"""
        for handler in self.handlers:
            try:
                handler(alert)
            except Exception as e:
                print(f"Alert handler failed: {e}")

    def _resolve_alert(self, alert: Alert):
        """告警恢复"""
        # 可以发送恢复通知
        pass


# 预定义规则
def create_default_rules() -> List[AlertRule]:
    """创建默认告警规则"""

    return [
        AlertRule(
            name="high_error_rate",
            description="错误率超过 10%",
            severity=AlertSeverity.CRITICAL,
            condition=lambda m: m.get("error_rate", 0) > 0.1,
            cooldown=300,
        ),
        AlertRule(
            name="queue_backlog",
            description="队列积压超过 10000",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("queue_size", 0) > 10000,
            cooldown=600,
        ),
        AlertRule(
            name="slow_response",
            description="平均响应时间超过 5 秒",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("avg_response_time", 0) > 5.0,
            cooldown=300,
        ),
        AlertRule(
            name="proxy_exhausted",
            description="可用代理少于 5 个",
            severity=AlertSeverity.CRITICAL,
            condition=lambda m: m.get("available_proxies", 100) < 5,
            cooldown=300,
        ),
        AlertRule(
            name="worker_down",
            description="活跃 Worker 数量为 0",
            severity=AlertSeverity.CRITICAL,
            condition=lambda m: m.get("active_workers", 1) == 0,
            cooldown=60,
        ),
        AlertRule(
            name="captcha_spike",
            description="验证码出现率超过 50%",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("captcha_rate", 0) > 0.5,
            cooldown=300,
        ),
    ]
```

### 通知渠道

```python
"""
告警通知渠道
"""

import httpx
from abc import ABC, abstractmethod
from typing import Dict
from dataclasses import dataclass
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class NotificationChannel(ABC):
    """通知渠道基类"""

    @abstractmethod
    def send(self, alert: Alert) -> bool:
        pass


class DingTalkChannel(NotificationChannel):
    """钉钉通知"""

    def __init__(self, webhook_url: str, secret: str = None):
        self.webhook_url = webhook_url
        self.secret = secret

    def send(self, alert: Alert) -> bool:
        # 颜色映射
        colors = {
            AlertSeverity.INFO: "#1890ff",
            AlertSeverity.WARNING: "#faad14",
            AlertSeverity.CRITICAL: "#ff4d4f",
        }

        # 构建消息
        message = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"[{alert.severity.value.upper()}] {alert.rule_name}",
                "text": f"""## 🚨 爬虫告警

**规则**: {alert.rule_name}

**级别**: {alert.severity.value}

**描述**: {alert.description}

**时间**: {alert.starts_at.strftime('%Y-%m-%d %H:%M:%S')}

**标签**: {', '.join(f'{k}={v}' for k, v in alert.labels.items())}
"""
            }
        }

        try:
            response = httpx.post(self.webhook_url, json=message, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"DingTalk notification failed: {e}")
            return False


class FeishuChannel(NotificationChannel):
    """飞书通知"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, alert: Alert) -> bool:
        message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"[{alert.severity.value.upper()}] 爬虫告警"
                    },
                    "template": "red" if alert.severity == AlertSeverity.CRITICAL else "orange"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"""**规则**: {alert.rule_name}
**描述**: {alert.description}
**时间**: {alert.starts_at.strftime('%Y-%m-%d %H:%M:%S')}"""
                        }
                    }
                ]
            }
        }

        try:
            response = httpx.post(self.webhook_url, json=message, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Feishu notification failed: {e}")
            return False


class EmailChannel(NotificationChannel):
    """邮件通知"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str]
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs

    def send(self, alert: Alert) -> bool:
        subject = f"[{alert.severity.value.upper()}] 爬虫告警: {alert.rule_name}"

        body = f"""
        <html>
        <body>
        <h2>🚨 爬虫告警</h2>
        <table border="1" cellpadding="10">
            <tr><td><b>规则</b></td><td>{alert.rule_name}</td></tr>
            <tr><td><b>级别</b></td><td>{alert.severity.value}</td></tr>
            <tr><td><b>描述</b></td><td>{alert.description}</td></tr>
            <tr><td><b>时间</b></td><td>{alert.starts_at.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
        </table>
        </body>
        </html>
        """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.from_addr
        msg['To'] = ', '.join(self.to_addrs)
        msg.attach(MIMEText(body, 'html'))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            return True
        except Exception as e:
            print(f"Email notification failed: {e}")
            return False


class TelegramChannel(NotificationChannel):
    """Telegram 通知"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, alert: Alert) -> bool:
        message = f"""🚨 *爬虫告警*

*规则*: {alert.rule_name}
*级别*: {alert.severity.value}
*描述*: {alert.description}
*时间*: {alert.starts_at.strftime('%Y-%m-%d %H:%M:%S')}
"""

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        try:
            response = httpx.post(url, data={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram notification failed: {e}")
            return False


# 使用示例
alert_manager = AlertManager()

# 添加规则
for rule in create_default_rules():
    alert_manager.add_rule(rule)

# 添加通知渠道
dingtalk = DingTalkChannel("https://oapi.dingtalk.com/robot/send?access_token=xxx")
alert_manager.add_handler(dingtalk.send)

# 评估（通常在定时任务中调用）
metrics = {
    "error_rate": 0.15,
    "queue_size": 5000,
    "avg_response_time": 2.3,
    "available_proxies": 20,
    "active_workers": 5,
}
alert_manager.evaluate(metrics)
```

---

## 健康检查

### 健康检查服务

```python
"""
健康检查服务
"""

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any
from enum import Enum
from datetime import datetime
import asyncio
from fastapi import FastAPI
import httpx


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """健康检查项"""
    name: str
    check_func: Callable[[], bool]
    timeout: float = 5.0
    critical: bool = True  # 是否影响整体健康状态


@dataclass
class HealthResult:
    """健康检查结果"""
    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.now)


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        self.checks: List[HealthCheck] = []

    def add_check(self, check: HealthCheck):
        """添加检查项"""
        self.checks.append(check)

    async def run_check(self, check: HealthCheck) -> HealthResult:
        """运行单个检查"""
        start_time = datetime.now()

        try:
            # 带超时运行
            result = await asyncio.wait_for(
                asyncio.to_thread(check.check_func),
                timeout=check.timeout
            )

            duration = (datetime.now() - start_time).total_seconds() * 1000

            if result:
                return HealthResult(
                    name=check.name,
                    status=HealthStatus.HEALTHY,
                    duration_ms=duration
                )
            else:
                return HealthResult(
                    name=check.name,
                    status=HealthStatus.UNHEALTHY,
                    message="Check returned False",
                    duration_ms=duration
                )

        except asyncio.TimeoutError:
            return HealthResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Timeout after {check.timeout}s"
            )
        except Exception as e:
            return HealthResult(
                name=check.name,
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )

    async def run_all(self) -> Dict:
        """运行所有检查"""
        results = await asyncio.gather(
            *[self.run_check(c) for c in self.checks]
        )

        # 计算整体状态
        critical_unhealthy = any(
            r.status == HealthStatus.UNHEALTHY
            for r, c in zip(results, self.checks)
            if c.critical
        )

        any_unhealthy = any(r.status == HealthStatus.UNHEALTHY for r in results)

        if critical_unhealthy:
            overall = HealthStatus.UNHEALTHY
        elif any_unhealthy:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return {
            "status": overall.value,
            "timestamp": datetime.now().isoformat(),
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                }
                for r in results
            ]
        }


# 预定义检查
def create_default_checks(redis_url: str, mongo_url: str = None) -> List[HealthCheck]:
    """创建默认检查"""

    checks = []

    # Redis 检查
    def check_redis():
        import redis
        r = redis.from_url(redis_url)
        return r.ping()

    checks.append(HealthCheck(
        name="redis",
        check_func=check_redis,
        timeout=5.0,
        critical=True
    ))

    # MongoDB 检查
    if mongo_url:
        def check_mongo():
            from pymongo import MongoClient
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            return client.admin.command('ping')['ok'] == 1

        checks.append(HealthCheck(
            name="mongodb",
            check_func=check_mongo,
            timeout=5.0,
            critical=True
        ))

    # 代理池检查
    def check_proxy_pool():
        import redis
        r = redis.from_url(redis_url)
        count = r.scard("proxy:available")
        return count > 0

    checks.append(HealthCheck(
        name="proxy_pool",
        check_func=check_proxy_pool,
        timeout=5.0,
        critical=False
    ))

    return checks


# FastAPI 健康检查端点
app = FastAPI()
checker = HealthChecker()

for check in create_default_checks("redis://localhost:6379"):
    checker.add_check(check)


@app.get("/health")
async def health():
    """健康检查端点"""
    result = await checker.run_all()
    status_code = 200 if result["status"] != "unhealthy" else 503
    return result


@app.get("/health/live")
async def liveness():
    """存活探针（K8s）"""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    """就绪探针（K8s）"""
    result = await checker.run_all()
    if result["status"] == "unhealthy":
        return {"status": "not ready"}, 503
    return {"status": "ready"}
```

---

## Grafana 仪表盘

### 仪表盘配置

```json
{
  "dashboard": {
    "title": "爬虫监控仪表盘",
    "tags": ["crawler", "monitoring"],
    "timezone": "browser",
    "panels": [
      {
        "title": "请求速率",
        "type": "graph",
        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "rate(crawler_requests_total[5m])",
            "legendFormat": "{{domain}} - {{status_code}}"
          }
        ]
      },
      {
        "title": "错误率",
        "type": "gauge",
        "gridPos": {"x": 12, "y": 0, "w": 6, "h": 8},
        "targets": [
          {
            "expr": "sum(rate(crawler_errors_total[5m])) / sum(rate(crawler_requests_total[5m])) * 100"
          }
        ],
        "options": {
          "thresholds": [
            {"value": 0, "color": "green"},
            {"value": 5, "color": "yellow"},
            {"value": 10, "color": "red"}
          ]
        }
      },
      {
        "title": "队列长度",
        "type": "stat",
        "gridPos": {"x": 18, "y": 0, "w": 6, "h": 8},
        "targets": [
          {
            "expr": "crawler_queue_size"
          }
        ]
      },
      {
        "title": "响应时间分布",
        "type": "heatmap",
        "gridPos": {"x": 0, "y": 8, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "rate(crawler_request_duration_seconds_bucket[5m])",
            "format": "heatmap"
          }
        ]
      },
      {
        "title": "活跃 Worker",
        "type": "stat",
        "gridPos": {"x": 12, "y": 8, "w": 6, "h": 8},
        "targets": [
          {
            "expr": "sum(crawler_active_tasks)"
          }
        ]
      },
      {
        "title": "采集数据量",
        "type": "graph",
        "gridPos": {"x": 18, "y": 8, "w": 6, "h": 8},
        "targets": [
          {
            "expr": "increase(crawler_items_scraped_total[1h])",
            "legendFormat": "{{item_type}}"
          }
        ]
      },
      {
        "title": "代理健康状况",
        "type": "table",
        "gridPos": {"x": 0, "y": 16, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "crawler_proxy_requests_total",
            "format": "table"
          }
        ]
      },
      {
        "title": "验证码统计",
        "type": "piechart",
        "gridPos": {"x": 12, "y": 16, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "sum by (captcha_type) (crawler_captcha_total)"
          }
        ]
      }
    ],
    "refresh": "10s"
  }
}
```

### Prometheus 告警规则

```yaml
# prometheus_rules.yml
groups:
  - name: crawler_alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(crawler_errors_total[5m]))
          / sum(rate(crawler_requests_total[5m])) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "爬虫错误率过高"
          description: "错误率已超过 10%，当前值: {{ $value | humanizePercentage }}"

      - alert: QueueBacklog
        expr: crawler_queue_size > 10000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "任务队列积压"
          description: "队列中有 {{ $value }} 个待处理任务"

      - alert: SlowResponse
        expr: |
          histogram_quantile(0.95, rate(crawler_request_duration_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "响应时间过长"
          description: "P95 响应时间: {{ $value | humanizeDuration }}"

      - alert: NoActiveWorkers
        expr: sum(crawler_active_tasks) == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "没有活跃的 Worker"
          description: "所有 Worker 都已停止工作"

      - alert: ProxyPoolEmpty
        expr: count(crawler_proxy_requests_total{status="success"}) < 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "代理池即将耗尽"
          description: "可用代理少于 5 个"

      - alert: HighCaptchaRate
        expr: |
          sum(rate(crawler_captcha_total[5m]))
          / sum(rate(crawler_requests_total[5m])) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "验证码出现率过高"
          description: "超过 50% 的请求触发了验证码"
```

---

## 链路追踪

### OpenTelemetry 集成

```python
"""
OpenTelemetry 链路追踪
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from functools import wraps
from typing import Callable
import httpx


def setup_tracing(service_name: str, jaeger_host: str = "localhost"):
    """设置链路追踪"""

    resource = Resource(attributes={
        ResourceAttributes.SERVICE_NAME: service_name,
    })

    provider = TracerProvider(resource=resource)

    exporter = JaegerExporter(
        agent_host_name=jaeger_host,
        agent_port=6831,
    )

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # 自动 instrument httpx
    HTTPXClientInstrumentor().instrument()

    return trace.get_tracer(service_name)


# 使用装饰器追踪
def traced(name: str = None):
    """追踪装饰器"""

    def decorator(func: Callable):
        tracer = trace.get_tracer(__name__)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            span_name = name or func.__name__
            with tracer.start_as_current_span(span_name) as span:
                # 添加属性
                span.set_attribute("function", func.__name__)

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("success", True)
                    return result
                except Exception as e:
                    span.set_attribute("success", False)
                    span.set_attribute("error", str(e))
                    span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            span_name = name or func.__name__
            with tracer.start_as_current_span(span_name) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("success", True)
                    return result
                except Exception as e:
                    span.set_attribute("success", False)
                    span.record_exception(e)
                    raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# 使用示例
tracer = setup_tracing("crawler-service", "localhost")


@traced("crawl_page")
async def crawl_page(url: str):
    """带追踪的爬取"""
    current_span = trace.get_current_span()
    current_span.set_attribute("url", url)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        current_span.set_attribute("status_code", response.status_code)
        return response


@traced("parse_data")
def parse_data(html: str):
    """带追踪的解析"""
    current_span = trace.get_current_span()
    # 解析逻辑...
    current_span.set_attribute("items_found", 10)
    return []
```

---

## 诊断日志

```
# 指标采集
[METRICS] 采集周期: {interval}s
[METRICS] 请求总量: {requests_total}, 错误: {errors_total}
[METRICS] 平均延迟: {avg_latency}ms, P99: {p99_latency}ms
[METRICS] 队列长度: {queue_size}
[METRICS] 活跃Worker: {active_workers}

# 告警触发
[ALERT] 规则触发: {rule_name}
[ALERT] 级别: {severity}, 描述: {description}
[ALERT] 当前值: {current_value}, 阈值: {threshold}
[ALERT] 通知渠道: {channels}

# 告警恢复
[ALERT] 规则恢复: {rule_name}
[ALERT] 持续时间: {duration}

# 日志聚合
[LOG] 推送到Loki: {batch_size}条
[LOG] 日志级别分布: INFO={info}, WARN={warn}, ERROR={error}

# 健康检查
[HEALTH] 检查项: {check_name}
[HEALTH] 状态: {status}, 耗时: {duration}ms
[HEALTH] 整体状态: {overall_status}

# 链路追踪
[TRACE] TraceID: {trace_id}
[TRACE] Span: {span_name}, 耗时: {duration}ms
[TRACE] 调用链深度: {depth}

# 通知发送
[NOTIFY] 渠道: {channel} (钉钉/飞书/邮件)
[NOTIFY] 发送结果: {success}

# 错误情况
[METRICS] ERROR: 指标采集失败: {error}
[ALERT] ERROR: 通知发送失败: {channel}, {error}
[HEALTH] ERROR: 健康检查超时: {check_name}
```

---

## 策略协调

监控告警配合 [16-战术决策模块](16-tactics.md) 实现自动响应：
- **错误率告警** → 自动切换代理/降低并发
- **队列积压告警** → 自动扩容 Worker
- **代理耗尽告警** → 自动触发代理补充

---

## 相关模块

- **上游**: [08-诊断模块](08-diagnosis.md) - 错误诊断
- **配合**: [13-分布式模块](13-distributed.md) - 集群监控
- **配合**: [07-调度模块](07-scheduling.md) - 任务监控
- **输出**: [17-反馈闭环模块](17-feedback-loop.md) - 指标反馈与自动调节

---

## 常见问题

### Q: 如何选择监控方案？

| 规模 | 推荐方案 |
|-----|---------|
| 小型（单机） | 日志文件 + 简单脚本 |
| 中型（集群） | Prometheus + Grafana |
| 大型（分布式） | Prometheus + Loki + Jaeger |

### Q: 告警疲劳如何处理？

1. 设置合理的阈值和冷却时间
2. 使用告警分级，只对 CRITICAL 发送即时通知
3. 实现告警聚合，相似告警合并
4. 定期回顾和调整告警规则

### Q: 日志量太大如何处理？

1. 设置日志级别，生产环境用 WARNING 及以上
2. 采样日志，只记录部分请求
3. 使用日志轮转，自动清理旧日志
4. 结构化日志，便于过滤和分析
