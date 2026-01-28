---
skill_id: "01-reconnaissance"
name: "侦查模块"
version: "1.1.0"
status: "stable"                    # draft | beta | stable | deprecated
implementation_status: "complete"   # none | partial | complete
difficulty: 2
category: "core"

description: "目标网站信息收集与智能分析"

triggers:
  - pattern: "(分析|调查|侦查).*(网站|站点|url)"
  - condition: "site.known == false"

dependencies:
  required: []
  optional:
    - skill: "11-fingerprint"
      reason: "指纹伪装"

external_dependencies:
  required:
    - name: "httpx"
      version: ">=0.24.0"
      type: "python_package"
      install: "pip install httpx"
  optional:
    - name: "playwright"
      version: ">=1.40.0"
      condition: "浏览器模式"
      type: "python_package"
      install: "pip install playwright"

outputs:
  - name: "SiteAnalysis"
    fields: [anti_crawl_level, signatures, entry_points, recommendations]
---

# 01 - 侦查模块 (Reconnaissance)

## 模块目标

| 目标 | SLO | 适用范围 | 降级策略 |
|------|-----|----------|----------|
| 请求捕获 | 捕获率 ≥ 95% | XHR/Fetch/WS | 仅捕获主请求 |
| 特征识别 | 准确率 ≥ 90% | 已知反爬模式 | 标记为UNKNOWN |
| 建议输出 | 可执行率 ≥ 85% | 标准场景 | 输出多个备选 |
| 入口发现 | 发现率 ≥ 80% | 有公开接口 | 默认PC入口 |

## 模块概述

侦查模块是爬虫流程的**第一步**，为 [16-战术模块](16-tactics.md) 提供目标情报：
1. 访问目标页面
2. 捕获所有网络请求
3. 收集 Cookie/Header/Console
4. 智能分析网站特征
5. 生成操作建议
6. **输出入口优先级评估**

```
┌─────────────────────────────────────────────────────────────┐
│                      侦查模块架构                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐         ┌─────────────┐                  │
│   │ InfoCollector│────────▶│ SiteReport  │                  │
│   │  信息收集器   │         │   原始报告   │                  │
│   └─────────────┘         └──────┬──────┘                  │
│                                  │                          │
│                                  ▼                          │
│                          ┌─────────────┐                    │
│                          │SmartAnalyzer│                    │
│                          │  智能分析器  │                    │
│                          └──────┬──────┘                    │
│                                  │                          │
│                                  ▼                          │
│                          ┌─────────────┐                    │
│                          │SiteAnalysis │                    │
│                          │  分析结果    │                    │
│                          └─────────────┘                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心接口

### investigate() - 基础侦查

```python
def investigate(
    url: str,
    wait_seconds: float = 5.0,    # 等待AJAX加载
    scroll: bool = True,           # 触发懒加载
    take_screenshot: bool = True,  # 保存截图
) -> SiteReport
```

**使用场景**: 需要原始数据自行分析时

```python
from unified_agent import Brain

brain = Brain()
report = brain.investigate("https://jd.com/item/123")

# 查看捕获的API请求
for req in report.api_requests:
    print(f"{req.method} {req.url}")
    print(f"Headers: {req.headers}")
    print(f"Params: {req.params}")

# 查看收集的Cookie
for cookie in report.cookies:
    print(f"{cookie['name']}={cookie['value']}")
```

---

### smart_investigate() - 智能侦查 (推荐)

```python
def smart_investigate(
    url: str,
    wait_seconds: float = 5.0,
    scroll: bool = True,
    take_screenshot: bool = True,
) -> SiteAnalysis
```

**使用场景**: 希望自动分析并获取建议时

```python
analysis = brain.smart_investigate("https://jd.com/item/123")
print(analysis.to_ai_report())
```

---

### interact() - 交互式侦查

```python
def interact(
    url: str,
    actions: list[dict],          # 动作列表
    wait_between: float = 1.0,    # 动作间隔
) -> SiteReport
```

**使用场景**: 需要触发特定操作才能捕获API时

```python
report = brain.interact(
    url="https://jd.com",
    actions=[
        {"type": "fill", "selector": "#key", "value": "手机"},
        {"type": "click", "selector": ".search-btn"},
        {"type": "wait", "seconds": 3},
    ]
)
```

---

## 数据结构

### SiteReport - 原始报告

```python
@dataclass
class SiteReport:
    url: str                           # 目标URL
    timestamp: datetime                # 采集时间

    # 网络数据
    cookies: list[dict]                # 所有Cookie
    headers: dict[str, str]            # 响应头
    api_requests: list[ApiRequest]     # 捕获的API请求

    # 页面数据
    html: str                          # 页面HTML
    interactive_elements: list[dict]   # 可交互元素

    # 调试数据
    console_logs: list[str]            # Console日志
    js_errors: list[str]               # JS错误

    # 截图
    screenshot_b64: str | None         # Base64截图

    # 检测结果
    detected_params: list[str]         # 检测到的加密参数

    def summary_for_ai(self) -> str:
        """生成AI友好的摘要"""

    def to_json(self) -> str:
        """导出为JSON"""
```

### ApiRequest - API请求

```python
@dataclass
class ApiRequest:
    method: str                    # GET/POST/...
    url: str                       # 完整URL
    headers: dict[str, str]        # 请求头
    params: dict[str, Any]         # URL参数
    body: str | dict | None        # 请求体
    response_status: int           # 响应状态码
    response_body: Any             # 响应内容
```

### SiteAnalysis - 智能分析结果

```python
@dataclass
class SiteAnalysis:
    # === 网站识别 ===
    site_name: str                 # "京东", "淘宝", "未知"
    site_id: str                   # "jd", "taobao", "unknown"
    site_type: str                 # "ecommerce", "social", "video", "news"

    # === 反爬评估 ===
    anti_scrape_level: str         # "low" | "medium" | "high" | "extreme"
    detection_risks: list[str]     # ["TLS指纹检测", "Canvas检测", ...]

    # === 登录状态 ===
    login_required: bool           # 是否需要登录
    is_logged_in: bool             # 当前是否已登录
    login_check_cookie: str        # 用于判断登录的Cookie

    # === API分析 ===
    main_data_api: dict | None     # 主数据接口
    api_endpoints: list[dict]      # 所有发现的接口

    # === 签名分析 ===
    signature_required: bool       # 是否需要签名
    signature_params: list[str]    # 签名参数名 ["h5st", "sign"]
    signature_analysis: SignatureAnalysis | None

    # === 决策建议 ===
    recommended_approach: str      # 推荐方案
    next_steps: list[str]          # 下一步操作
    warnings: list[str]            # 注意事项

    def to_ai_report(self) -> str:
        """生成Markdown格式的AI报告"""
```

---

## 信息收集清单

### 网络层收集

| 项目 | 来源 | 用途 |
|------|------|------|
| XHR/Fetch 请求 | Network监听 | 发现API端点 |
| WebSocket消息 | WS监听 | 实时数据接口 |
| 请求头 | Request Headers | 伪装请求 |
| 响应头 | Response Headers | 分析服务器 |
| Cookie | Document.cookie + Network | 会话管理 |
| Set-Cookie | Response Headers | Cookie来源 |

### 页面层收集

| 项目 | 来源 | 用途 |
|------|------|------|
| HTML结构 | page.content() | 选择器定位 |
| 表单元素 | form, input, select | 交互分析 |
| 按钮/链接 | button, a | 操作触发点 |
| 数据属性 | data-* | 隐藏数据 |
| Script标签 | script[src] | JS分析 |
| Meta信息 | meta | 页面元数据 |

### 调试层收集

| 项目 | 来源 | 用途 |
|------|------|------|
| Console.log | CDP Console | 调试信息 |
| Console.error | CDP Console | 错误追踪 |
| JS异常 | page.on('pageerror') | 问题定位 |
| 网络错误 | page.on('requestfailed') | 请求问题 |

---

## 智能分析规则

### 网站类型识别

```python
SITE_TYPE_RULES = {
    "ecommerce": {
        "keywords": ["商品", "价格", "购物车", "cart", "product", "price"],
        "domains": ["jd.com", "taobao.com", "tmall.com", "pdd.com"],
        "patterns": ["/item/", "/product/", "/goods/"]
    },
    "social": {
        "keywords": ["关注", "粉丝", "点赞", "评论", "follow", "like"],
        "domains": ["weibo.com", "xiaohongshu.com", "zhihu.com"],
        "patterns": ["/user/", "/profile/", "/status/"]
    },
    "video": {
        "keywords": ["播放", "视频", "play", "video"],
        "domains": ["bilibili.com", "douyin.com", "youtube.com"],
        "patterns": ["/video/", "/watch/", "/v/"]
    }
}
```

### 反爬等级评估

```python
ANTI_SCRAPE_SCORING = {
    # 低危检测 (各1分)
    "basic_ua_check": 1,
    "referer_check": 1,
    "cookie_required": 1,

    # 中危检测 (各2分)
    "rate_limiting": 2,
    "ip_blocking": 2,
    "session_validation": 2,

    # 高危检测 (各3分)
    "signature_required": 3,
    "token_refresh": 3,
    "fingerprint_check": 3,

    # 极高危检测 (各5分)
    "tls_fingerprint": 5,
    "behavior_analysis": 5,
    "captcha": 5,
    "device_fingerprint": 5,
}

# 评级标准
# 0-3分: low
# 4-8分: medium
# 9-15分: high
# 16+分: extreme
```

### 签名参数检测

```python
SIGNATURE_KEYWORDS = [
    # 通用签名
    "sign", "signature", "sig", "hash",

    # Token类
    "token", "access_token", "auth", "ticket",

    # 时间戳
    "timestamp", "ts", "t", "time",

    # 随机数
    "nonce", "random", "r",

    # 平台特定
    "h5st",           # 京东
    "x-sign",         # 阿里
    "x-mini-wua",     # 阿里
    "anti-content",   # 拼多多
    "x-bogus",        # 抖音
    "a_bogus",        # 抖音
    "x-s", "x-t",     # 小红书
    "wbi", "w_rid",   # B站
    "x-zse-96",       # 知乎
]
```

---

## 最佳实践

### 1. 等待时间设置

```python
# 简单静态页面
analysis = brain.smart_investigate(url, wait_seconds=2)

# AJAX加载页面
analysis = brain.smart_investigate(url, wait_seconds=5)

# 复杂SPA应用
analysis = brain.smart_investigate(url, wait_seconds=10)

# 需要滚动加载
analysis = brain.smart_investigate(url, wait_seconds=5, scroll=True)
```

### 2. 交互触发API

```python
# 搜索场景
report = brain.interact(url, [
    {"type": "fill", "selector": "#search", "value": "关键词"},
    {"type": "click", "selector": ".search-btn"},
    {"type": "wait", "seconds": 3},
])

# 翻页场景
report = brain.interact(url, [
    {"type": "click", "selector": ".next-page"},
    {"type": "wait", "seconds": 2},
])

# 滚动加载
report = brain.interact(url, [
    {"type": "scroll", "direction": "down", "distance": 1000},
    {"type": "wait", "seconds": 2},
    {"type": "scroll", "direction": "down", "distance": 1000},
])
```

### 3. 结果缓存复用

```python
# 保存报告供后续分析
report = brain.investigate(url)
brain.save_report(report, "jd_report")

# 后续可直接加载分析
# report = load_report("jd_report")
```

---

## 输出示例

### to_ai_report() 输出

```markdown
# 网站分析报告

## 基础信息
- **网站**: 京东 (jd)
- **类型**: 电商平台
- **URL**: https://item.jd.com/123456.html

## 反爬评估
- **等级**: extreme (极高)
- **评分**: 18/25

### 检测到的风险
1. TLS/JA3 指纹检测
2. Canvas 指纹检测
3. H5ST 签名验证
4. 设备指纹采集
5. 行为轨迹分析

## 登录状态
- **需要登录**: 否 (商品页面)
- **当前状态**: 未登录

## API端点
### 主数据接口
- **URL**: `https://api.m.jd.com/client.action`
- **方法**: POST
- **需签名**: 是 (h5st)

### 其他接口
1. `https://api.m.jd.com/api?functionId=pc_club_getProductPageFitting`
2. `https://api.m.jd.com/api?functionId=pc_club_productCouponInfo`

## 签名分析
- **参数名**: h5st
- **长度**: 128字符
- **字符集**: hex + 下划线
- **复杂度**: extreme
- **预估算法**: HMAC-SHA256 + 时间戳 + 设备指纹

## 推荐方案
**need_reverse** - 需要逆向签名

## 下一步操作
1. 分析页面JS找到h5st生成位置
2. 使用AST工具反混淆代码
3. 定位签名函数并分析参数
4. 选择方案: 纯算法复现 或 JS引擎执行

## 注意事项
- 京东反爬强度极高，建议使用代理池
- h5st版本可能更新，需要持续维护
- 建议配合登录态提高成功率
```

---

## 诊断日志

```
# 侦查启动
[RECON] 开始侦查: https://example.com/api/list
[RECON] 浏览器启动: chromium headless=True

# 请求捕获
[RECON] 捕获请求: GET /api/list?page=1 (XHR)
[RECON] 捕获请求: POST /api/sign (Fetch)
[RECON] 发现签名参数: h5st, sign, timestamp

# 特征识别
[RECON] 检测到反爬: TLS指纹检测, Canvas指纹
[RECON] 检测到签名: h5st (京东风格, 复杂度:extreme)
[RECON] 检测到验证码风险: 高 (页面包含captcha元素)

# 分析完成
[RECON] 分析完成: 耗时 8.5s
[RECON] 推荐方案: need_reverse
[RECON] 推荐入口: /api/app/list (移动端API, 难度较低)

# 错误情况
[RECON] ERROR: 页面加载超时 (30s)
[RECON] ERROR: 浏览器崩溃，正在重启
[RECON] WARN: 部分请求被 CORS 阻止
```

---

## 相关模块

- **战术决策**: [16-战术模块](16-tactics.md) - 接收侦查结果，选择突破策略
- **下一步**: [02-反检测模块](02-anti-detection.md) - 应用伪装策略
- **依赖**: [03-签名模块](03-signature.md) - 深度签名分析
- **配合**: [04-请求模块](04-request.md) - 发送实际请求
