# 00 - 快速开始与资源规划 (Quick Start & Resource Planning)

---
name: quick-start
version: 1.0.0
description: 新手引导、资源需求评估、配置建议
triggers:
  - "开始"
  - "怎么用"
  - "需要什么"
  - "代理"
  - "账号"
  - "配置"
priority: highest
---

## 模块目标

**核心原则：给出需求，必须完成。**

| 目标 | 达成标准 |
|------|---------|
| **资源自评估** | 根据目标网站自动判断代理/账号/频率需求 |
| **配置可执行** | 生成的配置代码可直接复制使用 |
| **成本可预估** | 给出明确的费用预估和推荐供应商 |
| **上手即可用** | 新用户 3 分钟内完成首次配置 |

## 模块概述

本模块帮助用户：
1. 快速上手爬虫系统
2. 根据目标网站自动评估所需资源
3. 获得代理、账号、配置的具体建议

```
┌─────────────────────────────────────────────────────────────────┐
│                      资源规划流程                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐│
│   │ 目标URL  │───▶│ 智能侦查  │───▶│ 资源评估  │───▶│ 配置建议 ││
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘│
│                         │                              │        │
│                         ▼                              ▼        │
│                   ┌──────────┐                  ┌──────────┐   │
│                   │反爬等级   │                  │ 告诉用户  │   │
│                   │登录需求   │                  │ 需要准备  │   │
│                   │请求频率   │                  │ 什么资源  │   │
│                   └──────────┘                  └──────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三分钟快速开始

### Step 1: 运行侦查

```python
from unified_agent import Brain

brain = Brain()

# 输入你的目标网站
analysis = brain.smart_investigate("https://你的目标网站.com")

# 查看完整报告（包含资源建议）
print(analysis.to_ai_report())
```

### Step 2: 查看资源建议

报告会自动包含：
- 是否需要代理
- 是否需要登录/多账号
- 推荐的请求频率
- 预估难度和成本

### Step 3: 按建议配置

根据报告提示，配置相应资源后开始抓取。

---

## 资源需求评估规则

### 核心决策表

根据 `smart_investigate()` 返回的 `anti_scrape_level` 自动判断：

| 反爬等级 | 代理需求 | 账号需求 | 请求频率 | 预估成本 |
|---------|---------|---------|---------|---------|
| 🟢 **low** | ❌ 不需要 | ❌ 不需要 | 2-5次/秒 | 免费 |
| 🟡 **medium** | ⚠️ 建议有 | ⚠️ 可能需要 | 1-2次/秒 | 0-100元/月 |
| 🔴 **high** | ✅ 需要 | ✅ 需要登录 | 0.5-1次/秒 | 100-500元/月 |
| ⚫ **extreme** | ✅ 必须 | ✅ 多账号 | 0.2-0.5次/秒 | 500+元/月 |

---

## 代理需求判断

### 什么时候需要代理？

```python
def need_proxy(analysis: SiteAnalysis, plan: ScrapePlan) -> ProxyAdvice:
    """
    根据分析结果判断是否需要代理

    Returns:
        ProxyAdvice: 代理建议
    """

    # 规则1: 反爬等级
    if analysis.anti_scrape_level == "extreme":
        return ProxyAdvice(
            required=True,
            reason="目标网站反爬等级极高，必须使用代理",
            type="residential",  # 住宅代理
            recommendation="推荐使用住宅代理，数据中心代理容易被识别"
        )

    if analysis.anti_scrape_level == "high":
        return ProxyAdvice(
            required=True,
            reason="目标网站有IP频率限制",
            type="datacenter",  # 数据中心代理即可
            recommendation="可使用数据中心代理，性价比更高"
        )

    # 规则2: 请求规模
    if plan.total_requests > 1000:
        return ProxyAdvice(
            required=True,
            reason=f"计划请求量({plan.total_requests})较大，建议使用代理分散请求",
            type="datacenter"
        )

    # 规则3: 检测到IP限制
    if "ip_blocking" in analysis.detection_risks:
        return ProxyAdvice(
            required=True,
            reason="检测到网站有IP封禁机制"
        )

    # 规则4: 小规模+低反爬
    if analysis.anti_scrape_level in ["low", "medium"] and plan.total_requests < 500:
        return ProxyAdvice(
            required=False,
            reason="小规模抓取 + 反爬等级不高，可以不用代理",
            recommendation="控制好请求频率（每秒1-2次）即可"
        )

    return ProxyAdvice(required=False)
```

### 代理类型说明

| 类型 | 说明 | 价格 | 适用场景 |
|------|------|------|---------|
| **数据中心代理** | 机房IP | 便宜 (几十元/月) | medium等级网站 |
| **住宅代理** | 真实家庭IP | 较贵 (几百元/月) | high/extreme等级 |
| **移动代理** | 手机4G IP | 最贵 | 极端反爬场景 |

### 代理配置示例

```python
# 情况1: 不需要代理
config = AgentConfig(proxy_enabled=False)

# 情况2: 需要代理
config = AgentConfig(
    proxy_enabled=True,
    proxy_host="代理服务商给你的地址",
    proxy_port=15818,
    proxy_username="你的用户名",  # 如果需要认证
    proxy_password="你的密码",
)

brain = Brain(config)
```

---

## 账号需求判断

### 什么时候需要登录？

```python
def need_account(analysis: SiteAnalysis) -> AccountAdvice:
    """
    根据分析结果判断是否需要账号

    Returns:
        AccountAdvice: 账号建议
    """

    # 规则1: 明确需要登录
    if analysis.login_required:
        return AccountAdvice(
            required=True,
            reason="目标页面需要登录才能访问",
            count=1,
            how_to="使用浏览器登录后，导出Cookie"
        )

    # 规则2: 登录后数据更完整
    if analysis.login_benefits:
        return AccountAdvice(
            required=False,
            recommended=True,
            reason="登录后可获取更完整的数据",
            benefits=analysis.login_benefits
        )

    # 规则3: 不需要登录
    return AccountAdvice(
        required=False,
        reason="目标数据无需登录即可访问"
    )
```

### 什么时候需要多账号？

```python
def need_multiple_accounts(analysis: SiteAnalysis, plan: ScrapePlan) -> MultiAccountAdvice:
    """判断是否需要多账号"""

    # 规则1: 极高反爬 + 大规模
    if analysis.anti_scrape_level == "extreme" and plan.total_requests > 5000:
        return MultiAccountAdvice(
            required=True,
            reason="极高反爬网站 + 大规模抓取，单账号容易被限制",
            recommended_count=3-5,
            warning="注意：多账号有封号风险，需要控制每个账号的使用频率"
        )

    # 规则2: 账号有请求限额
    if analysis.account_rate_limit:
        accounts_needed = math.ceil(plan.total_requests / analysis.account_rate_limit)
        return MultiAccountAdvice(
            required=accounts_needed > 1,
            reason=f"每个账号每日限额{analysis.account_rate_limit}次，需要{accounts_needed}个账号",
            recommended_count=accounts_needed
        )

    # 规则3: 一般情况不需要多账号
    return MultiAccountAdvice(
        required=False,
        reason="当前规模使用1个账号即可"
    )
```

### 账号配置示例

```python
# 情况1: 不需要账号（公开数据）
brain = Brain()
result = brain.scrape_page("https://example.com/products")

# 情况2: 需要登录（使用Cookie）
brain = Brain()
brain.set_cookies({
    "session_id": "你的session",
    "token": "你的token",
    # 从浏览器开发者工具复制
})
result = brain.scrape_page("https://example.com/my-orders")

# 情况3: 多账号轮换
accounts = [
    {"user": "account1", "cookies": {...}},
    {"user": "account2", "cookies": {...}},
    {"user": "account3", "cookies": {...}},
]

for i, url in enumerate(urls):
    account = accounts[i % len(accounts)]  # 轮换使用
    brain.set_cookies(account["cookies"])
    result = brain.call_api(url)
    time.sleep(2)  # 控制频率
```

---

## 如何获取 Cookie？

### 方法1: 浏览器开发者工具

```
1. 用浏览器正常登录网站
2. 按 F12 打开开发者工具
3. 切换到 "Network"（网络）标签
4. 刷新页面
5. 点击任意请求
6. 在 "Headers" 中找到 "Cookie"
7. 复制整个 Cookie 值
```

### 方法2: 使用插件导出

推荐插件：
- **EditThisCookie** (Chrome)
- **Cookie-Editor** (Firefox)

导出为 JSON 格式，然后：

```python
import json

# 读取导出的 Cookie 文件
with open("cookies.json", "r") as f:
    cookies_list = json.load(f)

# 转换为字典格式
cookies = {c["name"]: c["value"] for c in cookies_list}

# 使用
brain.set_cookies(cookies)
```

### 方法3: 代码自动获取（高级）

```python
# 使用 Playwright 自动登录
async def auto_login(username, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 显示浏览器
        page = await browser.new_page()

        await page.goto("https://example.com/login")
        await page.fill("#username", username)
        await page.fill("#password", password)
        await page.click("#login-btn")

        # 等待登录成功
        await page.wait_for_url("**/home**")

        # 获取 Cookie
        cookies = await page.context.cookies()

        await browser.close()
        return {c["name"]: c["value"] for c in cookies}
```

---

## 完整资源评估报告

### ResourceAssessment 结构

```python
@dataclass
class ResourceAssessment:
    """资源评估报告"""

    # 目标信息
    target_url: str
    site_name: str
    anti_scrape_level: str

    # 代理评估
    proxy_required: bool
    proxy_reason: str
    proxy_type: str | None          # datacenter/residential/mobile
    proxy_provider: list[str]       # 推荐供应商

    # 账号评估
    login_required: bool
    login_reason: str
    multi_account: bool
    account_count: int

    # 频率建议
    recommended_rps: float          # 每秒请求数
    recommended_delay: float        # 请求间隔(秒)

    # 成本预估
    estimated_cost: str             # "免费" / "100-500元/月" / ...
    cost_breakdown: dict            # 成本明细

    # 配置代码
    config_code: str                # 生成的配置代码

    def to_user_report(self) -> str:
        """生成用户友好的报告"""
```

### 报告输出示例

```markdown
# 资源评估报告

## 目标网站
- **网站**: 京东 (jd.com)
- **反爬等级**: ⚫ extreme (极高)

---

## 📡 代理配置

**状态**: ✅ 需要代理

**原因**: 京东反爬等级极高，有以下检测:
- TLS/JA3 指纹检测
- IP 频率限制
- 设备指纹检测

**建议**:
- 类型: 住宅代理 (Residential Proxy)
- 推荐服务商: 快代理、芝麻代理、Luminati
- 预估费用: 200-500元/月

**配置方法**:
```python
config = AgentConfig(
    proxy_enabled=True,
    proxy_host="your-proxy.com",
    proxy_port=15818,
    proxy_username="your_username",
    proxy_password="your_password",
)
```

---

## 👤 账号配置

**状态**: ⚠️ 建议登录

**原因**:
- 商品页面可直接访问
- 登录后可获取更多信息（库存、优惠券等）

**建议**:
- 账号数量: 1个（小规模）/ 3-5个（大规模）
- 获取方式: 手动登录后导出Cookie

**配置方法**:
```python
# 从浏览器复制 Cookie
brain.set_cookies({
    "pt_key": "AAJxxxx...",
    "pt_pin": "your_username",
})
```

---

## ⏱️ 频率控制

**建议配置**:
- 请求间隔: 2-5 秒
- 每秒请求: 0.2-0.5 次
- 每日上限: 建议 < 1000 次/账号

```python
import time
import random

for url in urls:
    result = brain.call_api(url)
    time.sleep(random.uniform(2, 5))  # 随机延迟
```

---

## 💰 成本预估

| 项目 | 费用 | 说明 |
|------|------|------|
| 代理 | 200-500元/月 | 住宅代理 |
| 账号 | 0元 | 自己注册 |
| 服务器 | 0-100元/月 | 可选 |
| **总计** | **200-600元/月** | |

---

## 🚀 下一步

1. [ ] 准备代理服务 → 联系服务商开通
2. [ ] 准备账号 → 注册并登录获取Cookie
3. [ ] 配置参数 → 复制上面的代码
4. [ ] 开始测试 → 先小规模测试
```

---

## 自动生成配置代码

```python
def generate_config_code(assessment: ResourceAssessment) -> str:
    """根据评估结果生成配置代码"""

    lines = [
        "from unified_agent import Brain, AgentConfig",
        "",
        "# 自动生成的配置",
        "config = AgentConfig(",
    ]

    # 代理配置
    if assessment.proxy_required:
        lines.extend([
            "    # 代理配置 (请填入你的代理信息)",
            "    proxy_enabled=True,",
            '    proxy_host="your-proxy.com",  # TODO: 填入代理地址',
            "    proxy_port=15818,              # TODO: 填入代理端口",
            '    proxy_username="",             # TODO: 填入用户名',
            '    proxy_password="",             # TODO: 填入密码',
        ])
    else:
        lines.append("    proxy_enabled=False,")

    lines.extend([
        "    headless=True,",
        ")",
        "",
        "brain = Brain(config)",
        "",
    ])

    # Cookie 配置
    if assessment.login_required:
        lines.extend([
            "# Cookie 配置 (请填入你的登录Cookie)",
            "brain.set_cookies({",
            '    # TODO: 从浏览器复制你的Cookie',
            '    # "cookie_name": "cookie_value",',
            "})",
            "",
        ])

    # 频率控制
    lines.extend([
        "# 频率控制",
        "import time",
        "import random",
        "",
        f"MIN_DELAY = {assessment.recommended_delay}  # 最小延迟(秒)",
        f"MAX_DELAY = {assessment.recommended_delay * 2}  # 最大延迟(秒)",
        "",
        "# 使用示例",
        "for url in your_urls:",
        "    result = brain.call_api(url)",
        "    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))",
    ])

    return "\n".join(lines)
```

---

## 常见问题

### Q: 我怎么知道需不需要代理？

**A**: 运行 `smart_investigate()` 后查看报告中的建议。或者：
- 先不用代理尝试
- 如果出现 `403`、`429` 错误，说明需要代理
- 如果请求变慢或被重定向到验证页，说明需要代理

### Q: 代理从哪里买？

**A**: 推荐服务商:

| 服务商 | 类型 | 价格参考 | 适合场景 |
|--------|------|---------|---------|
| [快代理](https://www.kuaidaili.com/) | 数据中心 | 50-200元/月 | medium等级 |
| [芝麻代理](http://www.zhimaruanjian.com/) | 混合 | 100-300元/月 | high等级 |
| [Luminati](https://brightdata.com/) | 住宅 | $500+/月 | extreme等级 |

### Q: Cookie 会过期吗？

**A**: 会的。不同网站过期时间不同：
- 短期 Cookie: 几小时到1天
- 长期 Cookie: 7天到30天
- 解决方案: 定期重新登录获取

### Q: 账号会被封吗？

**A**: 可能会，降低风险的方法：
1. 控制请求频率
2. 使用代理
3. 模拟真实用户行为
4. 不要24小时连续运行

---

## 诊断日志

```
# 资源评估
[RESOURCE] 开始评估: https://jd.com
[RESOURCE] 反爬等级: extreme
[RESOURCE] 代理需求: 必须 (住宅代理)
[RESOURCE] 账号需求: 建议登录
[RESOURCE] 推荐频率: 0.2-0.5/s

# 配置生成
[CONFIG] 生成代理配置: proxy_enabled=True
[CONFIG] 生成延迟配置: delay=2-5s
[CONFIG] 输出配置代码: 42行

# 成本预估
[COST] 代理: 200-500元/月
[COST] 账号: 0元
[COST] 总计: 200-600元/月

# 检查项
[CHECK] 代理连接: OK
[CHECK] Cookie 有效: OK
[CHECK] 测试请求: 200 OK

# 错误情况
[RESOURCE] WARN: 未配置代理，但目标需要代理
[RESOURCE] WARN: Cookie 即将过期 (剩余 2h)
[CONFIG] ERROR: 代理连接失败，请检查配置
```

---

## 相关模块

- **下一步**: [01-侦查模块](01-reconnaissance.md) - 详细分析网站
- **配置**: [02-反检测模块](02-anti-detection.md) - 伪装设置
- **请求**: [04-请求模块](04-request.md) - 代理和重试配置
- **决策**: [16-战术模块](16-tactics.md) - 策略选择与切换
