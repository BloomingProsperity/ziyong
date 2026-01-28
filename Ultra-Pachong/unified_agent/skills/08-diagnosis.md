# 08 - 诊断模块 (Diagnosis & Troubleshooting)

---
name: diagnosis
version: 1.0.0
description: 日志分析、错误诊断、自动修复与方案切换
triggers:
  - "错误"
  - "失败"
  - "报错"
  - "不工作"
  - "error"
  - "failed"
  - "日志"
priority: high
---

## 模块目标

**核心原则：给出需求，必须完成。**

| 目标 | 达成标准 |
|------|---------|
| **错误全识别** | 常见错误类型 100% 识别并给出原因 |
| **方案可执行** | 每个错误都有明确的解决步骤 |
| **自动可修复** | 可自动修复的问题自动处理，无需人工 |
| **方案可切换** | 失败时自动切换到备选方案继续执行 |

## 模块概述

诊断模块帮助 AI 自动分析运行日志，识别问题并给出解决方案。

```
┌─────────────────────────────────────────────────────────────────┐
│                      诊断修复流程                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐│
│   │ 运行爬虫  │───▶│ 收集日志  │───▶│ 分析问题  │───▶│ 给出方案 ││
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘│
│        │               │               │               │       │
│        │               ▼               ▼               ▼       │
│        │         ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│        │         │ 错误日志  │   │ 匹配规则  │   │ 自动修复  │   │
│        │         │ 状态码   │   │ 识别原因  │   │ 或建议   │   │
│        │         │ 异常信息  │   │ 评估严重  │   │ 换方案   │   │
│        │         └──────────┘   └──────────┘   └──────────┘   │
│        │                                             │         │
│        └─────────────────────────────────────────────┘         │
│                         重试/换方案                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 日志系统

### 日志级别

| 级别 | 说明 | 示例 |
|------|------|------|
| `DEBUG` | 详细调试信息 | 请求参数、响应头 |
| `INFO` | 正常运行信息 | 开始抓取、完成抓取 |
| `WARNING` | 警告信息 | 重试中、速度变慢 |
| `ERROR` | 错误信息 | 请求失败、解析失败 |
| `CRITICAL` | 严重错误 | 被封禁、账号异常 |

### 日志配置

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)

logger = logging.getLogger('unified_agent')
```

### 日志输出示例

```
2024-01-27 12:00:00 | INFO | unified_agent | 开始侦查: https://jd.com
2024-01-27 12:00:05 | INFO | unified_agent | 侦查完成，发现 15 个API请求
2024-01-27 12:00:06 | INFO | unified_agent | 反爬等级: extreme
2024-01-27 12:00:10 | WARNING | unified_agent | 请求失败，状态码: 403，重试中 (1/3)
2024-01-27 12:00:15 | WARNING | unified_agent | 请求失败，状态码: 403，重试中 (2/3)
2024-01-27 12:00:20 | ERROR | unified_agent | 请求失败，状态码: 403，已达最大重试次数
2024-01-27 12:00:20 | ERROR | unified_agent | 错误详情: IP被封禁，需要更换代理
```

---

## 错误诊断规则

### 错误类型识别

```python
ERROR_PATTERNS = {
    # === HTTP 状态码错误 ===
    "403_forbidden": {
        "pattern": r"status[_\s]?code[:\s]*403|403\s*Forbidden",
        "severity": "high",
        "causes": [
            "IP被封禁",
            "签名验证失败",
            "Cookie失效",
            "User-Agent被拦截"
        ],
        "solutions": [
            {"action": "enable_proxy", "description": "启用代理"},
            {"action": "rotate_ua", "description": "更换User-Agent"},
            {"action": "refresh_cookie", "description": "刷新Cookie"},
            {"action": "add_signature", "description": "添加签名参数"}
        ]
    },

    "429_rate_limit": {
        "pattern": r"status[_\s]?code[:\s]*429|Too Many Requests|rate.?limit",
        "severity": "medium",
        "causes": [
            "请求频率过高",
            "触发限流机制"
        ],
        "solutions": [
            {"action": "reduce_speed", "description": "降低请求频率"},
            {"action": "add_delay", "description": "增加请求间隔到 5-10 秒"},
            {"action": "enable_proxy", "description": "启用代理分散请求"}
        ]
    },

    "401_unauthorized": {
        "pattern": r"status[_\s]?code[:\s]*401|Unauthorized",
        "severity": "high",
        "causes": [
            "未登录",
            "Token过期",
            "认证信息错误"
        ],
        "solutions": [
            {"action": "login", "description": "需要登录，请提供Cookie"},
            {"action": "refresh_token", "description": "刷新Token"}
        ]
    },

    "500_server_error": {
        "pattern": r"status[_\s]?code[:\s]*5\d{2}|Internal Server Error",
        "severity": "low",
        "causes": [
            "服务器临时错误",
            "服务器过载"
        ],
        "solutions": [
            {"action": "retry_later", "description": "等待几分钟后重试"},
            {"action": "reduce_speed", "description": "降低请求频率"}
        ]
    },

    # === 网络错误 ===
    "connection_timeout": {
        "pattern": r"timeout|timed?\s*out|ConnectTimeout",
        "severity": "medium",
        "causes": [
            "网络不稳定",
            "代理连接慢",
            "目标服务器响应慢"
        ],
        "solutions": [
            {"action": "increase_timeout", "description": "增加超时时间到 60 秒"},
            {"action": "check_proxy", "description": "检查代理是否正常"},
            {"action": "retry", "description": "重试请求"}
        ]
    },

    "connection_refused": {
        "pattern": r"Connection\s*refused|ECONNREFUSED",
        "severity": "high",
        "causes": [
            "目标服务器拒绝连接",
            "IP被封禁",
            "代理失效"
        ],
        "solutions": [
            {"action": "change_proxy", "description": "更换代理IP"},
            {"action": "wait", "description": "等待 10-30 分钟后重试"}
        ]
    },

    # === 解析错误 ===
    "json_decode_error": {
        "pattern": r"JSONDecodeError|Expecting value|Invalid JSON",
        "severity": "medium",
        "causes": [
            "返回的不是JSON（可能是HTML错误页）",
            "被重定向到登录页",
            "返回空响应"
        ],
        "solutions": [
            {"action": "check_response", "description": "检查实际返回内容"},
            {"action": "check_login", "description": "确认是否需要登录"},
            {"action": "use_browser", "description": "改用浏览器模式"}
        ]
    },

    "selector_not_found": {
        "pattern": r"selector.*not found|Element not found|NoSuchElement",
        "severity": "medium",
        "causes": [
            "页面结构变化",
            "选择器错误",
            "内容未加载完成"
        ],
        "solutions": [
            {"action": "update_selector", "description": "更新CSS选择器"},
            {"action": "increase_wait", "description": "增加等待时间"},
            {"action": "check_page", "description": "检查页面是否正常加载"}
        ]
    },

    # === 反爬检测 ===
    "captcha_detected": {
        "pattern": r"captcha|验证码|滑块|人机验证|robot|bot.?detect",
        "severity": "critical",
        "causes": [
            "触发验证码",
            "被识别为机器人"
        ],
        "solutions": [
            {"action": "enable_stealth", "description": "启用反检测模式"},
            {"action": "use_residential_proxy", "description": "使用住宅代理"},
            {"action": "reduce_speed", "description": "大幅降低请求频率"},
            {"action": "manual_solve", "description": "手动解决验证码后继续"}
        ]
    },

    "signature_invalid": {
        "pattern": r"sign.*invalid|signature.*error|签名.*错误|h5st.*fail",
        "severity": "high",
        "causes": [
            "签名算法错误",
            "签名参数过期",
            "时间戳不同步"
        ],
        "solutions": [
            {"action": "regenerate_sign", "description": "重新生成签名"},
            {"action": "sync_time", "description": "同步系统时间"},
            {"action": "use_browser", "description": "改用浏览器执行获取签名"}
        ]
    },

    # === 代理错误 ===
    "proxy_error": {
        "pattern": r"proxy.*error|代理.*失败|ProxyError|SOCKS",
        "severity": "medium",
        "causes": [
            "代理服务器不可用",
            "代理认证失败",
            "代理配置错误"
        ],
        "solutions": [
            {"action": "check_proxy_config", "description": "检查代理配置"},
            {"action": "change_proxy", "description": "更换代理"},
            {"action": "disable_proxy", "description": "暂时禁用代理测试"}
        ]
    }
}
```

---

## 诊断报告

### DiagnosisReport 结构

```python
@dataclass
class DiagnosisReport:
    """诊断报告"""

    # 错误信息
    error_type: str                    # 错误类型
    error_message: str                 # 错误消息
    severity: str                      # 严重程度: low/medium/high/critical

    # 分析结果
    probable_causes: list[str]         # 可能的原因
    confidence: float                  # 诊断置信度 0-1

    # 解决方案
    solutions: list[dict]              # 解决方案列表
    recommended_solution: dict         # 推荐方案
    auto_fixable: bool                 # 是否可自动修复

    # 上下文
    request_url: str                   # 出错的URL
    request_count: int                 # 已请求次数
    error_count: int                   # 错误次数
    last_success_time: datetime        # 上次成功时间

    def to_user_report(self) -> str:
        """生成用户友好的报告"""
```

### 诊断报告示例

```markdown
# 🔴 错误诊断报告

## 错误概述
- **类型**: 403 Forbidden (IP被封禁)
- **严重程度**: 🔴 高
- **发生时间**: 2024-01-27 12:00:20
- **出错URL**: https://api.jd.com/client.action

## 可能原因
1. ⭐ IP被目标网站封禁 (置信度: 90%)
2. 签名验证失败
3. Cookie失效

## 解决方案

### 方案1: 启用代理 ✅ 推荐
```python
config = AgentConfig(
    proxy_enabled=True,
    proxy_host="your-proxy.com",
    proxy_port=15818,
)
```
**预计效果**: 更换IP后可恢复正常

### 方案2: 降低请求频率
```python
time.sleep(random.uniform(5, 10))  # 增加到5-10秒
```
**预计效果**: 避免触发限流

### 方案3: 刷新Cookie
重新登录获取新的Cookie

## 自动修复
⚠️ 当前错误无法自动修复，需要您：
1. [ ] 配置代理服务
2. [ ] 填入代理信息
3. [ ] 重新运行

## 运行统计
- 总请求: 150 次
- 成功: 120 次 (80%)
- 失败: 30 次 (20%)
- 上次成功: 5 分钟前
```

---

## 自动修复策略

### 可自动修复的问题

| 问题 | 自动修复动作 |
|------|-------------|
| 429 限流 | 自动降速，增加延迟 |
| 超时 | 自动增加超时时间并重试 |
| 5xx 服务器错误 | 等待后自动重试 |
| Cookie 过期 (有备份) | 自动切换备用Cookie |
| 代理失效 (有代理池) | 自动切换到下一个代理 |

### 需要人工处理的问题

| 问题 | 需要用户做什么 |
|------|---------------|
| 403 IP封禁 | 配置代理 |
| 验证码 | 手动解决或配置打码服务 |
| 401 未登录 | 提供登录Cookie |
| 签名失败 | 更新签名算法 |

### 自动修复代码

```python
class AutoFixer:
    """自动修复器"""

    def __init__(self, brain: Brain):
        self.brain = brain
        self.fix_history = []

    def try_fix(self, error: Exception, context: dict) -> FixResult:
        """尝试自动修复"""

        diagnosis = self.diagnose(error, context)

        if not diagnosis.auto_fixable:
            return FixResult(
                success=False,
                message="需要人工处理",
                report=diagnosis.to_user_report()
            )

        # 尝试自动修复
        for solution in diagnosis.solutions:
            if solution.get("auto"):
                result = self.apply_fix(solution)
                if result.success:
                    return result

        return FixResult(success=False, message="自动修复失败")

    def apply_fix(self, solution: dict) -> FixResult:
        """应用修复方案"""

        action = solution["action"]

        if action == "reduce_speed":
            self.brain.config.min_delay *= 2
            self.brain.config.max_delay *= 2
            return FixResult(True, f"已降低请求频率，间隔改为 {self.brain.config.min_delay}-{self.brain.config.max_delay} 秒")

        elif action == "increase_timeout":
            self.brain.config.timeout *= 2
            return FixResult(True, f"已增加超时时间到 {self.brain.config.timeout} 秒")

        elif action == "retry":
            return FixResult(True, "将进行重试", should_retry=True)

        elif action == "change_proxy":
            if self.brain.proxy_pool:
                new_proxy = self.brain.proxy_pool.get_next()
                self.brain.set_proxy(new_proxy)
                return FixResult(True, f"已切换到新代理: {new_proxy}")

        return FixResult(False, f"无法自动执行: {action}")
```

---

## 方案切换策略

### 策略优先级

```python
APPROACH_PRIORITY = [
    {
        "approach": "direct_api",
        "description": "直接API调用",
        "conditions": ["低反爬", "已知API", "无签名"],
        "fallback": "api_with_signature"
    },
    {
        "approach": "api_with_signature",
        "description": "带签名API调用",
        "conditions": ["中等反爬", "已知签名算法"],
        "fallback": "browser_scrape"
    },
    {
        "approach": "browser_scrape",
        "description": "浏览器渲染抓取",
        "conditions": ["高反爬", "需要JS执行"],
        "fallback": "browser_with_stealth"
    },
    {
        "approach": "browser_with_stealth",
        "description": "隐身浏览器模式",
        "conditions": ["极高反爬", "反检测"],
        "fallback": "manual"
    },
    {
        "approach": "manual",
        "description": "需要人工介入",
        "conditions": ["验证码", "账号问题"],
        "fallback": None
    }
]
```

### 自动切换逻辑

```python
class ApproachSwitcher:
    """方案切换器"""

    def __init__(self):
        self.current_approach = "direct_api"
        self.failed_approaches = set()

    def on_failure(self, error: Exception) -> str:
        """失败时切换方案"""

        diagnosis = diagnose(error)

        # 当前方案标记为失败
        self.failed_approaches.add(self.current_approach)

        # 找到下一个可用方案
        for strategy in APPROACH_PRIORITY:
            if strategy["approach"] not in self.failed_approaches:
                self.current_approach = strategy["approach"]
                return self.explain_switch(strategy)

        return "所有方案都已尝试，需要人工介入"

    def explain_switch(self, strategy: dict) -> str:
        """解释为什么切换方案"""
        return f"""
## 方案切换通知

**原方案失败**: {self.previous_approach}
**切换到**: {strategy['approach']} - {strategy['description']}

**原因**: {self.failure_reason}

**下一步**: AI 将使用新方案重试
"""
```

---

## 使用示例

### 基础用法

```python
from unified_agent import Brain
from unified_agent.diagnosis import Diagnoser, AutoFixer

brain = Brain()
diagnoser = Diagnoser()
fixer = AutoFixer(brain)

try:
    result = brain.call_api("https://example.com/api")
except Exception as e:
    # 诊断问题
    report = diagnoser.diagnose(e)
    print(report.to_user_report())

    # 尝试自动修复
    fix_result = fixer.try_fix(e, context={})
    if fix_result.success:
        print(f"自动修复成功: {fix_result.message}")
        # 重试
        result = brain.call_api("https://example.com/api")
    else:
        print(f"需要人工处理: {fix_result.report}")
```

### 完整工作流

```python
async def robust_scrape(brain: Brain, urls: list[str]):
    """带诊断的健壮爬取"""

    results = []
    errors = []

    for url in urls:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = brain.call_api(url)
                if result.success:
                    results.append(result)
                    break
                else:
                    # 分析失败原因
                    diagnosis = diagnose_response(result)
                    fix = apply_auto_fix(diagnosis)

                    if not fix.success:
                        errors.append({
                            "url": url,
                            "diagnosis": diagnosis,
                            "needs_manual": True
                        })
                        break

            except Exception as e:
                diagnosis = diagnose_exception(e)

                if diagnosis.auto_fixable:
                    apply_auto_fix(diagnosis)
                    continue  # 重试
                else:
                    errors.append({
                        "url": url,
                        "error": str(e),
                        "diagnosis": diagnosis.to_user_report()
                    })
                    break

    # 生成总结报告
    return ScrapeReport(
        total=len(urls),
        success=len(results),
        failed=len(errors),
        results=results,
        errors=errors
    )
```

---

## 常见问题速查

### 快速诊断表

| 现象 | 可能原因 | 快速解决 |
|------|---------|---------|
| 403 错误 | IP被封 | 启用代理 |
| 429 错误 | 请求太快 | 增加延迟到 5-10秒 |
| 返回空数据 | 需要登录 | 设置Cookie |
| 乱码/解析失败 | 返回了HTML错误页 | 检查是否被重定向 |
| 超时 | 网络慢/代理慢 | 增加超时/换代理 |
| 验证码 | 触发反爬 | 降速+换IP+加反检测 |
| 签名错误 | 算法过期 | 更新签名逻辑 |

### 紧急恢复步骤

```
遇到问题时按此顺序尝试:

1. 先停止运行，等待 5 分钟
2. 检查日志，确认错误类型
3. 如果是 403/429:
   - 启用代理
   - 降低频率
4. 如果是 401/需要登录:
   - 重新获取 Cookie
5. 如果是验证码:
   - 降速到每 10 秒一个请求
   - 启用反检测模式
6. 如果还是不行:
   - 换方案（改用浏览器模式）
```

---

## 相关模块

- **数据来源**: [04-请求模块](04-request.md) - 请求错误
- **配合**: [00-快速开始](00-quick-start.md) - 资源配置
- **配合**: [02-反检测模块](02-anti-detection.md) - 反爬问题
- **配合**: [16-战术模块](16-tactics.md) - 策略切换与风险评估
- **输出**: [17-反馈闭环模块](17-feedback-loop.md) - 错误经验积累
