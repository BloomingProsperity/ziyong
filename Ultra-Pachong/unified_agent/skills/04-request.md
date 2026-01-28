---
skill_id: "04-request"
name: "请求模块"
version: "1.1.0"
status: "stable"                    # draft | beta | stable | deprecated
implementation_status: "complete"   # none | partial | complete
difficulty: 2
category: "core"

description: "HTTP请求发送、重试策略与代理管理"

triggers:
  - condition: "action == 'http_request'"
  - pattern: "(请求|调用).*(api|url|接口)"

dependencies:
  required:
    - skill: "02-anti-detection"
      reason: "指纹伪装"
  optional:
    - skill: "24-credential-pool"
      reason: "会话管理"

external_dependencies:
  required:
    - name: "httpx"
      version: ">=0.24.0"
      type: "python_package"
      install: "pip install httpx"
  optional:
    - name: "curl_cffi"
      version: ">=0.6.0"
      condition: "TLS指纹模拟"
      type: "python_package"
      install: "pip install curl_cffi"

inputs:
  - name: "url"
    type: "string"
    required: true
  - name: "method"
    type: "string"
    default: "GET"
  - name: "params"
    type: "dict"
    required: false

outputs:
  - name: "Response"
    fields: [status_code, headers, body, elapsed_ms]
---

# 04 - 请求模块 (Request)

## 模块目标

| 目标 | SLO | 适用范围 | 降级策略 |
|------|-----|----------|----------|
| 请求成功 | 成功率 ≥ 95% | 正常网络 | 重试3次+换代理 |
| 代理可用 | 可用率 ≥ 90% | 代理池模式 | 直连回退 |
| 限流规避 | 429率 < 5% | 有限流站点 | 自动降速 |
| 会话保持 | 有效率 ≥ 95% | 需登录站点 | 自动刷新 |

## 模块概述

请求模块负责发送 HTTP 请求，包括智能重试、代理轮换、Cookie 管理等功能。

```
┌─────────────────────────────────────────────────────────────────┐
│                        请求模块架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐│
│   │ 构建请求  │───▶│ 代理选择  │───▶│ 发送请求  │───▶│ 处理响应 ││
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘│
│        │                               │                        │
│        │                               ▼                        │
│        │                        ┌──────────┐                    │
│        │                        │ 失败判断  │                    │
│        │                        └────┬─────┘                    │
│        │                             │                          │
│        │              ┌──────────────┼──────────────┐          │
│        │              ▼              ▼              ▼          │
│        │        ┌─────────┐    ┌─────────┐    ┌─────────┐      │
│        │        │ 成功返回 │    │ 重试    │    │ 失败返回 │      │
│        │        └─────────┘    └────┬────┘    └─────────┘      │
│        │                            │                          │
│        └────────────────────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心接口

### call_api() - 单次请求

```python
def call_api(
    url: str,
    method: Literal["GET", "POST", "PUT", "DELETE"] = "GET",
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    form_body: dict[str, Any] | None = None,
    use_collected_cookies: bool = True,
    timeout: float = 30.0,
    retry: bool = True,
) -> ApiCallResult
```

**使用示例**:
```python
from unified_agent import Brain

brain = Brain()

# GET 请求
result = brain.call_api("https://api.example.com/data")

# POST JSON
result = brain.call_api(
    url="https://api.example.com/data",
    method="POST",
    headers={"Content-Type": "application/json"},
    json_body={"page": 1, "size": 20}
)

# POST 表单
result = brain.call_api(
    url="https://api.example.com/login",
    method="POST",
    form_body={"username": "user", "password": "pass"}
)

# 带签名参数
result = brain.call_api(
    url="https://api.example.com/data",
    params={"id": "123", "sign": "abc123", "ts": "1234567890"}
)
```

---

### batch_call_api() - 批量请求

```python
def batch_call_api(
    requests: list[dict[str, Any]],
    delay_between: float = 1.0,
    stop_on_error: bool = False,
) -> list[ApiCallResult]
```

**使用示例**:
```python
# 批量抓取多页数据
results = brain.batch_call_api(
    requests=[
        {"url": f"https://api.example.com/list?page={i}"}
        for i in range(1, 11)
    ],
    delay_between=0.5,    # 每次请求间隔0.5秒
    stop_on_error=False   # 遇错不停止
)

# 检查结果
for i, result in enumerate(results):
    if result.success:
        print(f"Page {i+1}: {len(result.body['data'])} items")
    else:
        print(f"Page {i+1}: Failed - {result.error}")
```

---

## 响应数据结构

### ApiCallResult

```python
@dataclass
class ApiCallResult:
    success: bool                  # 请求是否成功 (status_code < 400)
    status_code: int | None        # HTTP状态码
    headers: dict[str, str]        # 响应头
    body: str | dict | list | None # 响应体 (自动解析JSON)
    error: str | None              # 错误信息
    retries: int                   # 实际重试次数
    response_time_ms: float        # 响应耗时(毫秒)

    def to_ai_summary(self) -> str:
        """生成AI友好摘要"""
        if self.success:
            if isinstance(self.body, dict):
                return f"[OK] 状态码:{self.status_code} | JSON对象({len(self.body)}字段) | {self.response_time_ms:.0f}ms"
            elif isinstance(self.body, list):
                return f"[OK] 状态码:{self.status_code} | JSON数组({len(self.body)}条) | {self.response_time_ms:.0f}ms"
            else:
                return f"[OK] 状态码:{self.status_code} | 文本({len(self.body)}字符) | {self.response_time_ms:.0f}ms"
        else:
            return f"[FAIL] 状态码:{self.status_code} | 错误:{self.error} | 重试:{self.retries}次"
```

---

## 智能重试机制

### 重试配置

```python
@dataclass
class RetryConfig:
    max_retries: int = 3              # 最大重试次数
    base_delay: float = 1.0           # 基础延迟(秒)
    max_delay: float = 30.0           # 最大延迟
    exponential_base: float = 2.0     # 指数基数
    jitter: bool = True               # 随机抖动

    # 触发重试的状态码
    retry_on_status: tuple[int, ...] = (
        429,  # Too Many Requests (限流)
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    )
```

### 指数退避算法

```
延迟计算公式:
delay = base_delay × (exponential_base ^ attempt)
delay = min(delay, max_delay)
if jitter:
    delay = delay × random(0.5, 1.5)

示例 (base=1.0, exp=2.0):
- 第1次重试: 1.0 × 2^0 = 1秒 (+ 抖动)
- 第2次重试: 1.0 × 2^1 = 2秒 (+ 抖动)
- 第3次重试: 1.0 × 2^2 = 4秒 (+ 抖动)
```

### 重试流程

```
请求 ──▶ 响应
          │
          ▼
    ┌───────────┐
    │ 状态码判断 │
    └─────┬─────┘
          │
    ┌─────┼─────┬─────────────┐
    │     │     │             │
    ▼     ▼     ▼             ▼
  2xx   4xx   5xx/429      超时/网络错误
  成功  失败   重试?         重试?
                │             │
                ▼             ▼
          ┌─────────┐   ┌─────────┐
          │剩余次数>0│   │剩余次数>0│
          └────┬────┘   └────┬────┘
               │             │
          ┌────┴────┐   ┌────┴────┐
          │等待delay │   │等待delay │
          └────┬────┘   └────┬────┘
               │             │
               └──────┬──────┘
                      │
                      ▼
                    重试
```

---

## 代理管理

### 代理配置

```python
from unified_agent import AgentConfig

config = AgentConfig(
    proxy_enabled=True,
    proxy_host="proxy.example.com",
    proxy_port=8080,
    proxy_username="user",       # 可选
    proxy_password="password",   # 可选
)

brain = Brain(config)
```

### ProxyManager

```python
class ProxyManager:
    """代理池管理器"""

    def get_playwright_proxy(self) -> dict | None:
        """获取 Playwright 格式代理"""
        if not self.config.proxy_enabled:
            return None

        proxy = {
            "server": f"http://{self.config.proxy_host}:{self.config.proxy_port}"
        }

        if self.config.proxy_username:
            proxy["username"] = self.config.proxy_username
            proxy["password"] = self.config.proxy_password

        return proxy

    def get_httpx_proxy(self) -> str | None:
        """获取 httpx 格式代理"""
        if not self.config.proxy_enabled:
            return None

        if self.config.proxy_username:
            return f"http://{self.config.proxy_username}:{self.config.proxy_password}@{self.config.proxy_host}:{self.config.proxy_port}"
        else:
            return f"http://{self.config.proxy_host}:{self.config.proxy_port}"

    def health_check(self) -> bool:
        """代理健康检查"""
        try:
            with httpx.Client(proxy=self.get_httpx_proxy(), timeout=10) as client:
                response = client.get("https://httpbin.org/ip")
                return response.status_code == 200
        except:
            return False
```

### 代理轮换策略

```python
class ProxyPool:
    """代理池 (扩展实现)"""

    def __init__(self, proxies: list[str]):
        self.proxies = proxies
        self.current_index = 0
        self.failed_proxies = set()

    def get_next(self) -> str:
        """轮询获取下一个代理"""
        available = [p for p in self.proxies if p not in self.failed_proxies]
        if not available:
            self.failed_proxies.clear()  # 重置
            available = self.proxies

        proxy = available[self.current_index % len(available)]
        self.current_index += 1
        return proxy

    def mark_failed(self, proxy: str):
        """标记失败的代理"""
        self.failed_proxies.add(proxy)

    def get_random(self) -> str:
        """随机获取代理"""
        import random
        available = [p for p in self.proxies if p not in self.failed_proxies]
        return random.choice(available) if available else random.choice(self.proxies)
```

---

## Cookie 管理

### 自动Cookie

```python
# 侦查时自动收集 Cookie
analysis = brain.smart_investigate("https://example.com")

# 后续请求自动携带
result = brain.call_api(
    url="https://api.example.com/data",
    use_collected_cookies=True  # 默认开启
)
```

### 手动设置Cookie

```python
# 设置单个Cookie
brain.set_cookies({"session_id": "abc123"})

# 设置多个Cookie
brain.set_cookies({
    "pt_key": "xxx",
    "pt_pin": "xxx",
    "user_token": "yyy"
})

# 获取已收集的Cookie
cookies = brain.get_collected_cookies()
```

---

## HTTP客户端选择

### httpx (默认)

```python
# 适用场景: 一般请求
import httpx

with httpx.Client(
    timeout=30.0,
    follow_redirects=True,
    proxy=proxy_url
) as client:
    response = client.get(url)
```

### curl_cffi (绕过TLS检测)

```python
# 适用场景: 有 TLS/JA3 指纹检测的网站
from curl_cffi import requests

response = requests.get(
    url,
    impersonate="chrome120",  # 模拟 Chrome TLS 指纹
    proxies={"https": proxy_url}
)
```

### 选择建议

| 场景 | 推荐客户端 | 原因 |
|------|-----------|------|
| 普通网站 | httpx | 简单高效 |
| Cloudflare | curl_cffi | TLS指纹绕过 |
| 强反爬网站 | Playwright | 完整浏览器环境 |
| 高并发 | httpx + asyncio | 异步支持好 |

---

## 错误处理

### 常见错误码

| 状态码 | 含义 | 处理方式 |
|--------|------|---------|
| 200 | 成功 | 正常处理 |
| 301/302 | 重定向 | 自动跟随 |
| 400 | 参数错误 | 检查请求参数 |
| 401 | 未认证 | 检查登录态/Token |
| 403 | 禁止访问 | 检查签名/IP |
| 404 | 不存在 | 检查URL |
| 429 | 限流 | 降速/重试 |
| 500 | 服务器错误 | 重试 |
| 502/503/504 | 网关错误 | 重试 |

### 错误恢复

```python
result = brain.call_api(url)

if not result.success:
    if result.status_code == 429:
        # 限流 - 等待更长时间
        time.sleep(60)
        result = brain.call_api(url)

    elif result.status_code == 403:
        # 被封 - 切换代理
        brain.config.proxy_host = get_new_proxy()
        result = brain.call_api(url)

    elif result.status_code == 401:
        # 登录态失效 - 重新登录
        brain.set_cookies(get_new_cookies())
        result = brain.call_api(url)
```

---

## 性能优化

### 连接复用

```python
# 使用 Client 上下文管理器复用连接
with httpx.Client() as client:
    for url in urls:
        response = client.get(url)
```

### 异步请求

```python
import asyncio
import httpx

async def fetch_all(urls: list[str]) -> list:
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return responses

# 使用
responses = asyncio.run(fetch_all(urls))
```

### 请求限速

```python
import asyncio
from asyncio import Semaphore

async def rate_limited_fetch(urls: list[str], max_concurrent: int = 5):
    """限速并发请求"""
    semaphore = Semaphore(max_concurrent)

    async def fetch_one(url):
        async with semaphore:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                await asyncio.sleep(0.5)  # 请求间隔
                return response

    return await asyncio.gather(*[fetch_one(url) for url in urls])
```

---

## 诊断日志

```
# 请求发送
[REQ] GET https://api.example.com/data (retry=0)
[REQ] Headers: UA=Chrome/120, Cookie=session_xxx
[REQ] Proxy: http://proxy1:8080

# 响应处理
[REQ] 响应: 200 OK (1.2s, 15KB)
[REQ] 响应: JSON对象 (12字段)

# 重试机制
[REQ] 响应: 429 Too Many Requests
[REQ] 重试: 等待 2.3s (指数退避 + 抖动)
[REQ] 重试: 第 2/3 次，切换代理 -> proxy2:8080
[REQ] 重试成功: 200 OK

# 代理管理
[PROXY] 选择: http://proxy1:8080 (成功率: 95%)
[PROXY] 健康检查: proxy1=OK, proxy2=OK, proxy3=FAIL
[PROXY] 标记失败: proxy3:8080 (连续失败 3 次)
[PROXY] 轮换: proxy1 -> proxy2

# Cookie 管理
[COOKIE] 收集: session_id, user_token (来自侦查)
[COOKIE] 设置: pt_key, pt_pin (手动)
[COOKIE] 过期警告: user_token 即将过期 (剩余 5 分钟)

# 错误情况
[REQ] ERROR: 超时 (>30s)
[REQ] ERROR: 403 Forbidden - 签名验证失败
[REQ] ERROR: 代理连接失败，切换中...
[REQ] WARN: 限流触发，降低请求频率
```

---

## 相关模块

- **上游**: [02-反检测模块](02-anti-detection.md) - 请求伪装
- **上游**: [03-签名模块](03-signature.md) - 签名参数
- **下游**: [05-解析模块](05-parsing.md) - 响应解析
- **配合**: [07-调度模块](07-scheduling.md) - 并发控制
- **配合**: [16-战术模块](16-tactics.md) - 请求失败时切换策略
