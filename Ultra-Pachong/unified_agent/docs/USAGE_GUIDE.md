# Unified Agent 使用指南 (v2.0 升级版)

## 概述

这是一个 **AI 驱动的智能采集系统**。设计目标是让 Claude AI 能够：
1. 智能分析目标网站特征和反爬策略
2. 自动收集所有关键信息
3. 给出操作建议和最优方案
4. 执行数据抓取

## 新功能 (v2.0)

- **智能分析**: 自动识别网站类型、反爬等级、加密参数
- **预设配置**: 内置 12+ 主流网站配置 (京东、淘宝、天猫等)
- **智能重试**: 自动处理失败，指数退避
- **AI 友好报告**: 所有输出都优化为 AI 易读格式

## 工作流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    智能采集工作流程 (v2.0)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   用户输入目标 URL                                               │
│          ↓                                                      │
│   Claude 调用 brain.smart_investigate(url)  ← 推荐使用           │
│          ↓                                                      │
│   Agent 自动执行:                                                │
│   ├── 检查预设配置                                              │
│   ├── 打开网站并收集信息                                        │
│   ├── 智能分析网站特征                                          │
│   ├── 评估反爬等级                                              │
│   ├── 分析加密参数                                              │
│   └── 生成操作建议                                              │
│          ↓                                                      │
│   返回 SiteAnalysis (包含完整分析报告)                          │
│          ↓                                                      │
│   Claude 根据 recommended_approach 决策:                        │
│   ├── "direct_api" → brain.call_api()                          │
│   ├── "browser_scrape" → brain.scrape_page()                   │
│   ├── "hybrid" → 先 interact() 获取签名，再 call_api()         │
│   └── "need_reverse" → 需要逆向分析                            │
│          ↓                                                      │
│   返回数据给用户                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 方式1: 一行代码 (最简单)

```python
from unified_agent import quick_smart_investigate

# 一行代码获取完整分析报告
report = quick_smart_investigate("https://jd.com")
print(report)
```

### 方式2: 使用 Brain 类 (推荐)

```python
from unified_agent import Brain

# 创建 Brain 实例
brain = Brain()

# 智能调查 (推荐)
analysis = brain.smart_investigate("https://item.jd.com/12345.html")

# 打印 AI 友好的完整报告
print(analysis.to_ai_report())

# 查看关键信息
print(f"反爬等级: {analysis.anti_scrape_level}")
print(f"推荐方案: {analysis.recommended_approach}")
print(f"下一步: {analysis.next_steps}")
```

### 方式3: 查看预设信息

```python
from unified_agent import get_site_info, list_presets

# 查看支持的网站
print(list_presets())
# ['京东', '淘宝', '天猫', '拼多多', '1688', '小红书', '微博', '知乎', '哔哩哔哩', '抖音', '当当', '苏宁']

# 获取某网站的预设信息
info = get_site_info("jd.com")
print(info)
# {'found': True, 'name': '京东', 'requires_signature': True, ...}
```

## 详细用法

### 1. 智能调查 (推荐)

```python
from unified_agent import Brain, AgentConfig, RetryConfig

# 配置
config = AgentConfig(
    proxy_enabled=False,  # 是否使用快代理
    headless=True,        # 无头模式
)

# 重试配置 (可选)
retry_config = RetryConfig(
    max_retries=3,        # 最大重试次数
    base_delay=1.0,       # 基础延迟
)

brain = Brain(config, retry_config)

# 智能调查
analysis = brain.smart_investigate("https://example.com")

# 获取完整报告
print(analysis.to_ai_report())
```

### 2. 分析结果说明

```python
# SiteAnalysis 对象包含:
analysis.site_type           # 网站类型: ecommerce, social, video, etc.
analysis.site_name           # 识别的网站名称
analysis.anti_scrape_level   # 反爬等级: low, medium, high, extreme
analysis.anti_scrape_features # 检测到的反爬特征
analysis.login_required      # 是否需要登录
analysis.login_detected      # 是否已登录
analysis.api_endpoints       # API 端点列表
analysis.main_data_api       # 主要数据 API
analysis.signature_params    # 加密参数分析
analysis.encryption_complexity # 加密复杂度
analysis.recommended_approach # 推荐方案
analysis.next_steps          # 下一步操作建议
analysis.warnings            # 警告信息
analysis.matched_preset      # 匹配的预设
```

### 3. 调用 API (带智能重试)

```python
# 当分析结果推荐 direct_api 时
result = brain.call_api(
    url="https://api.example.com/products",
    method="GET",
    params={"page": 1, "size": 20},
    use_collected_cookies=True,
    retry=True,  # 启用智能重试
)

# 查看结果
print(result.to_ai_summary())
# [OK] 请求成功 | 状态码: 200 | 返回 JSON 数组，包含 20 条数据 | 耗时: 150ms

if result.success:
    print(result.body)
```

### 4. 批量 API 调用

```python
# 批量调用多个 API
results = brain.batch_call_api([
    {"url": "https://api.example.com/page/1"},
    {"url": "https://api.example.com/page/2"},
    {"url": "https://api.example.com/page/3"},
], delay_between=1.0)  # 每个请求间隔 1 秒

for i, result in enumerate(results):
    print(f"Page {i+1}: {result.to_ai_summary()}")
```

### 5. 带交互的调查

```python
# 当需要点击按钮、填写表单来触发 API 时
report = brain.interact("https://example.com", [
    {"type": "click", "selector": "#search-btn"},
    {"type": "fill", "selector": "#keyword", "value": "手机"},
    {"type": "click", "selector": "#submit"},
    {"type": "wait", "seconds": 3},
])

# 然后可以再次进行智能分析
analysis = brain.analyzer.analyze(report)
```

### 6. 数据抓取

```python
# 智能抓取
result = brain.scrape_page("https://example.com/products", max_pages=3)

# 自定义选择器抓取
result = brain.scrape_with_selector(
    url="https://example.com/products",
    item_selector=".product-card",
    fields=[
        {"name": "title", "selector": ".title", "attr": "text"},
        {"name": "price", "selector": ".price", "attr": "text"},
    ],
    max_pages=3,
)

# 导出数据
brain.export_data(result.data, "products", format="csv")
```

## 预设网站配置

系统内置了以下网站的配置:

| 网站 | 反爬等级 | 需要签名 | 签名参数 |
|------|---------|---------|---------|
| 京东 | EXTREME | 是 | h5st, x-api-eid-token |
| 淘宝 | EXTREME | 是 | sign, _m_h5_tk |
| 天猫 | EXTREME | 是 | sign, _m_h5_tk |
| 拼多多 | HIGH | 是 | anti-content |
| 抖音 | EXTREME | 是 | X-Bogus, a_bogus |
| 小红书 | HIGH | 是 | x-s, x-t |
| B站 | MEDIUM | 是 | wts, w_rid |
| 知乎 | MEDIUM | 否 | - |
| 微博 | MEDIUM | 否 | - |
| 当当 | LOW | 否 | - |
| 苏宁 | MEDIUM | 否 | - |
| 1688 | HIGH | 否 | - |

### 使用预设

```python
from unified_agent import get_preset

# 获取预设配置
preset = get_preset("jd.com")

if preset:
    print(f"登录页: {preset.login_url}")
    print(f"列表选择器: {preset.list_item_selector}")
    print(f"API 配置: {preset.main_apis}")
    print(f"建议操作: {preset.suggested_actions}")
```

## 状态监控

```python
# 获取统计信息
stats = brain.get_stats()
print(stats)
# {'request_count': 10, 'error_count': 1, 'success_rate': 90.0, ...}

# 获取状态报告
print(brain.get_status_report())

# 重置状态
brain.reset()
```

## 配置快代理

```python
from unified_agent import Brain, AgentConfig

# 方式1: 直接配置
config = AgentConfig.for_kuaidaili(
    username="your_username",
    password="your_password",
)

# 方式2: 环境变量
# 设置: KUAIDAILI_USERNAME, KUAIDAILI_PASSWORD
config = AgentConfig.from_env()

brain = Brain(config)
```

## 完整示例: 智能抓取京东商品

```python
from unified_agent import Brain, AgentConfig

brain = Brain(AgentConfig(proxy_enabled=False, headless=True))

# 第一步: 智能调查
print("=== 智能分析 ===")
analysis = brain.smart_investigate("https://item.jd.com/12345.html")
print(analysis.to_ai_report())

# 第二步: 根据建议决策
print(f"\n推荐方案: {analysis.recommended_approach}")
print(f"下一步操作:")
for step in analysis.next_steps:
    print(f"  - {step}")

# 第三步: 如果是 "need_reverse"，可能需要特殊处理
if analysis.recommended_approach == "need_reverse":
    print("\n此网站加密复杂，建议:")
    print("1. 使用 RPC 模式获取签名")
    print("2. 或使用浏览器抓取模式")

    # 使用浏览器抓取
    result = brain.scrape_page("https://item.jd.com/12345.html")
    if result.success:
        print(f"抓取到 {len(result.data)} 条数据")

# 第四步: 导出数据
if result.success:
    brain.export_data(result.data, "jd_products", format="json")
```

## 错误处理

```python
# API 调用失败时
result = brain.call_api("https://api.example.com/data")

if not result.success:
    print(f"请求失败: {result.error}")
    print(f"状态码: {result.status_code}")
    print(f"重试次数: {result.retries}")
```

## 注意事项

1. **反爬检测**: Agent 内置反检测措施，但 EXTREME 级别网站可能仍需额外处理
2. **代理**: 对于高反爬网站，强烈建议使用快代理
3. **登录态**: 如需登录，先手动登录后设置 Cookie:
   ```python
   brain.set_cookies({"pt_key": "xxx", "pt_pin": "yyy"})
   ```
4. **速率限制**: 使用 `batch_call_api` 的 `delay_between` 控制请求频率
5. **智能重试**: 默认启用，会自动处理 429、5xx 等临时错误
