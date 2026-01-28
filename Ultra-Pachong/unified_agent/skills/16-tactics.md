---
skill_id: "16-tactics"
name: "战术决策"
version: "1.1.0"
status: "stable"                    # draft | beta | stable | deprecated
implementation_status: "partial"    # none | partial | complete
difficulty: 5
category: "advanced"

description: "入口发现、策略匹配、动态调整的战术决策引擎"

triggers:
  - condition: "task.type == 'new_site'"
  - condition: "strategy.failed == true"
  - condition: "detection.risk >= MEDIUM"

dependencies:
  required:
    - skill: "01-reconnaissance"
      reason: "目标分析"
  optional:
    - skill: "08-diagnosis"
      reason: "故障诊断"
    - skill: "17-feedback-loop"
      reason: "经验反馈"

external_dependencies:
  required:
    - name: "httpx"
      version: ">=0.24.0"
      type: "python_package"
      install: "pip install httpx"
  optional: []
---

# 16 - 战术决策模块 (Tactical Decision Engine)

## 模块目标

| 目标 | SLO | 适用范围 | 降级策略 |
|------|-----|----------|----------|
| 入口发现 | 发现率 ≥ 90% | 有公开接口的站点 | 使用默认PC入口 |
| 策略匹配 | 匹配准确率 ≥ 85% | 已知站点类型 | 尝试全部策略 |
| 失败切换 | 切换时间 < 5s | 可恢复失败 | 立即切换下一策略 |
| 陷阱检测 | 检测率 ≥ 70% | 常见陷阱模式 | 保守模式运行 |
| 风险评估 | 实时评估 | 所有操作 | 默认中等风险 |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           战术决策引擎                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐   │
│   │  入口发现   │ →  │  策略匹配   │ →  │  执行监控   │ →  │ 动态调整 │   │
│   │             │    │             │    │             │    │          │   │
│   │ 找薄弱点   │    │ 选最优解   │    │ 检测异常   │    │ 快速切换 │   │
│   └─────────────┘    └─────────────┘    └─────────────┘    └──────────┘   │
│          │                  │                  │                 │         │
│          ▼                  ▼                  ▼                 ▼         │
│   ┌─────────────────────────────────────────────────────────────────────┐ │
│   │                        风险评估 (贯穿全程)                           │ │
│   │   蜜罐检测 | 假算法识别 | 封禁预警 | 资源消耗 | 暴露程度            │ │
│   └─────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 一、入口发现

### 入口优先级矩阵

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          入口优先级 (从高到低)                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  1. 官方 API        成本最低，稳定性最高，优先尝试                         │
│     └─ 检查: /api, /v1, /graphql, 开发者文档                              │
│                                                                            │
│  2. 移动端 API      通常防护比 Web 弱，签名相对简单                        │
│     └─ 检查: APP抓包, m.xxx.com, /api/app/                                │
│                                                                            │
│  3. H5/小程序       介于移动端和PC之间，可能有独立接口                     │
│     └─ 检查: h5.xxx.com, 微信小程序抓包                                   │
│                                                                            │
│  4. 旧版接口        老接口可能还在运行，防护较弱                           │
│     └─ 检查: /api/v1 vs /api/v3, legacy endpoints                         │
│                                                                            │
│  5. 第三方聚合      其他平台可能已抓取并提供数据                           │
│     └─ 检查: 数据聚合站, 比价网站, 搜索引擎缓存                           │
│                                                                            │
│  6. PC Web          防护最强，作为最后手段                                 │
│     └─ 需要: 完整指纹 + 签名破解 + 验证码处理                             │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### 入口探测器

```python
"""
入口发现与评估
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import httpx
import asyncio


class EntryType(Enum):
    """入口类型"""
    OFFICIAL_API = "official_api"      # 官方API
    MOBILE_API = "mobile_api"          # 移动端API
    H5_API = "h5_api"                  # H5接口
    LEGACY_API = "legacy_api"          # 旧版接口
    THIRD_PARTY = "third_party"        # 第三方
    PC_WEB = "pc_web"                  # PC网页


@dataclass
class EntryPoint:
    """入口点"""
    type: EntryType
    url: str
    method: str = "GET"
    auth_required: bool = False
    signature_required: bool = False
    captcha_risk: float = 0.0          # 验证码风险 0-1
    rate_limit: Optional[int] = None   # 请求限制
    difficulty: int = 1                 # 难度 1-5
    notes: str = ""


@dataclass
class TargetAnalysis:
    """目标分析结果"""
    domain: str
    entries: List[EntryPoint] = field(default_factory=list)
    recommended: Optional[EntryPoint] = None
    risk_level: str = "unknown"  # low/medium/high/extreme


class EntryDiscovery:
    """入口发现器"""

    # 常见入口路径模式
    PROBE_PATTERNS = {
        EntryType.OFFICIAL_API: [
            "/api/", "/v1/", "/v2/", "/v3/",
            "/graphql", "/rest/", "/openapi/",
        ],
        EntryType.MOBILE_API: [
            "/api/app/", "/mapi/", "/client/api/",
            "/mobile/", "/app/api/",
        ],
        EntryType.H5_API: [
            "/h5/api/", "/wap/", "/m/api/",
            "/miniapp/", "/weapp/",
        ],
        EntryType.LEGACY_API: [
            "/api/v1/", "/old/", "/legacy/",
            "/api_old/", "/_api/",
        ],
    }

    # 移动端域名模式
    MOBILE_DOMAINS = ["m.", "api.", "app.", "mobile.", "client."]

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10, follow_redirects=True)

    async def discover(self, domain: str) -> TargetAnalysis:
        """
        发现目标的所有可能入口

        策略:
        1. 检查常见API路径
        2. 检查移动端子域名
        3. 分析响应判断入口类型
        4. 评估每个入口的难度
        """
        analysis = TargetAnalysis(domain=domain)

        # 并行探测所有可能入口
        tasks = []

        # 探测API路径
        for entry_type, patterns in self.PROBE_PATTERNS.items():
            for pattern in patterns:
                url = f"https://{domain}{pattern}"
                tasks.append(self._probe_endpoint(url, entry_type))

        # 探测移动端域名
        for prefix in self.MOBILE_DOMAINS:
            mobile_domain = f"{prefix}{domain}"
            tasks.append(self._probe_domain(mobile_domain, EntryType.MOBILE_API))

        # 执行探测
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, EntryPoint):
                analysis.entries.append(result)

        # 选择推荐入口
        analysis.recommended = self._select_best_entry(analysis.entries)
        analysis.risk_level = self._assess_target_risk(analysis)

        return analysis

    async def _probe_endpoint(self, url: str, entry_type: EntryType) -> Optional[EntryPoint]:
        """探测单个端点"""
        try:
            response = await self.client.get(url)

            # 判断是否是有效入口
            if response.status_code in [200, 401, 403]:
                return EntryPoint(
                    type=entry_type,
                    url=url,
                    auth_required=(response.status_code == 401),
                    difficulty=self._estimate_difficulty(response),
                    notes=self._extract_notes(response),
                )
        except Exception:
            pass
        return None

    async def _probe_domain(self, domain: str, entry_type: EntryType) -> Optional[EntryPoint]:
        """探测域名"""
        try:
            url = f"https://{domain}/"
            response = await self.client.get(url)

            if response.status_code < 500:
                return EntryPoint(
                    type=entry_type,
                    url=url,
                    difficulty=self._estimate_difficulty(response),
                )
        except Exception:
            pass
        return None

    def _estimate_difficulty(self, response: httpx.Response) -> int:
        """估算入口难度"""
        difficulty = 1

        headers = response.headers
        content = response.text[:5000] if response.text else ""

        # 检查安全头
        if "x-request-id" in headers:
            difficulty += 1
        if any(h in headers for h in ["x-sign", "x-signature", "x-token"]):
            difficulty += 2

        # 检查内容特征
        if "captcha" in content.lower():
            difficulty += 1
        if "encrypted" in content.lower() or "sign" in content.lower():
            difficulty += 1

        return min(difficulty, 5)

    def _extract_notes(self, response: httpx.Response) -> str:
        """提取关键信息"""
        notes = []

        # API 版本
        if "api-version" in response.headers:
            notes.append(f"API版本: {response.headers['api-version']}")

        # 限流信息
        if "x-ratelimit-limit" in response.headers:
            notes.append(f"限流: {response.headers['x-ratelimit-limit']}/min")

        return "; ".join(notes)

    def _select_best_entry(self, entries: List[EntryPoint]) -> Optional[EntryPoint]:
        """选择最优入口"""
        if not entries:
            return None

        # 按优先级和难度排序
        priority = {
            EntryType.OFFICIAL_API: 1,
            EntryType.MOBILE_API: 2,
            EntryType.H5_API: 3,
            EntryType.LEGACY_API: 4,
            EntryType.THIRD_PARTY: 5,
            EntryType.PC_WEB: 6,
        }

        return min(entries, key=lambda e: (priority.get(e.type, 10), e.difficulty))

    def _assess_target_risk(self, analysis: TargetAnalysis) -> str:
        """评估目标风险等级"""
        if not analysis.entries:
            return "unknown"

        min_difficulty = min(e.difficulty for e in analysis.entries)

        if min_difficulty <= 2:
            return "low"
        elif min_difficulty <= 3:
            return "medium"
        elif min_difficulty <= 4:
            return "high"
        return "extreme"
```

---

## 二、策略匹配

### 策略决策树

```
                          ┌─────────────────┐
                          │   目标分析完成   │
                          └────────┬────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                              ▼
            有官方 API?                      无官方 API
                    │                              │
              ┌─────┴─────┐                 ┌──────┴──────┐
              ▼           ▼                 ▼             ▼
           有文档      无文档          有移动端API    无移动端
              │           │                 │             │
              ▼           ▼                 ▼             ▼
         直接调用    逆向分析           APP抓包      PC Web
                                            │         突破
                                            ▼
                                     有签名? ──────────┐
                                       │              │
                                  ┌────┴────┐        │
                                  ▼         ▼        ▼
                               简单签名  复杂签名  无签名
                                  │         │        │
                                  ▼         ▼        ▼
                              直接还原  深度逆向  直接请求
```

### 策略选择器

```python
"""
策略匹配与选择
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum


class StrategyType(Enum):
    """策略类型"""
    DIRECT_API = "direct_api"              # 直接API调用
    MOBILE_REVERSE = "mobile_reverse"       # 移动端逆向
    WEB_SCRAPE = "web_scrape"              # 网页抓取
    BROWSER_AUTOMATION = "browser_auto"     # 浏览器自动化
    HYBRID = "hybrid"                       # 混合策略


@dataclass
class Strategy:
    """策略"""
    type: StrategyType
    name: str
    description: str

    # 资源需求
    needs_proxy: bool = False
    needs_fingerprint: bool = False
    needs_captcha_solver: bool = False
    needs_js_reverse: bool = False

    # 预估指标
    success_rate: float = 0.8          # 预估成功率
    speed: str = "fast"                # fast/medium/slow
    cost: str = "low"                  # low/medium/high

    # 实现步骤
    steps: List[str] = field(default_factory=list)

    # 备选策略
    fallback: Optional[str] = None


@dataclass
class StrategyContext:
    """策略上下文 - 当前状态"""
    target_domain: str
    entry_point: Optional[EntryPoint] = None
    current_strategy: Optional[Strategy] = None

    # 资源状态
    has_proxy: bool = False
    has_fingerprints: bool = False
    has_captcha_solver: bool = False

    # 执行状态
    attempts: int = 0
    failures: int = 0
    last_error: Optional[str] = None
    is_blocked: bool = False


class StrategySelector:
    """策略选择器"""

    # 预定义策略库
    STRATEGIES = {
        "api_direct": Strategy(
            type=StrategyType.DIRECT_API,
            name="直接API调用",
            description="官方或公开API直接调用",
            success_rate=0.95,
            speed="fast",
            cost="low",
            steps=[
                "获取API文档或抓包分析",
                "构造请求参数",
                "处理认证(如需要)",
                "发起请求",
            ],
            fallback="mobile_simple",
        ),

        "mobile_simple": Strategy(
            type=StrategyType.MOBILE_REVERSE,
            name="移动端简单签名",
            description="移动端API + 简单签名还原",
            needs_proxy=True,
            needs_js_reverse=True,
            success_rate=0.85,
            speed="medium",
            cost="medium",
            steps=[
                "APP抓包获取请求",
                "分析签名参数",
                "还原签名算法",
                "构造请求",
            ],
            fallback="mobile_advanced",
        ),

        "mobile_advanced": Strategy(
            type=StrategyType.MOBILE_REVERSE,
            name="移动端深度逆向",
            description="APK逆向 + Frida Hook",
            needs_proxy=True,
            needs_js_reverse=True,
            success_rate=0.75,
            speed="slow",
            cost="high",
            steps=[
                "APK反编译",
                "定位签名函数",
                "Frida Hook获取参数",
                "还原或RPC调用",
            ],
            fallback="web_browser",
        ),

        "web_browser": Strategy(
            type=StrategyType.BROWSER_AUTOMATION,
            name="浏览器自动化",
            description="Playwright/Selenium 模拟真实浏览器",
            needs_proxy=True,
            needs_fingerprint=True,
            needs_captcha_solver=True,
            success_rate=0.70,
            speed="slow",
            cost="high",
            steps=[
                "配置浏览器指纹",
                "启动浏览器",
                "模拟用户行为",
                "处理验证码",
                "提取数据",
            ],
            fallback=None,
        ),

        "hybrid_stealth": Strategy(
            type=StrategyType.HYBRID,
            name="混合隐身策略",
            description="API + 浏览器混合，最大限度规避检测",
            needs_proxy=True,
            needs_fingerprint=True,
            needs_js_reverse=True,
            success_rate=0.80,
            speed="medium",
            cost="high",
            steps=[
                "浏览器获取Cookie/Token",
                "API获取数据",
                "定期刷新会话",
                "异常时回退浏览器",
            ],
            fallback="web_browser",
        ),
    }

    def select(self, context: StrategyContext, entry: EntryPoint) -> Strategy:
        """
        根据上下文选择最优策略

        决策因素:
        1. 入口类型和难度
        2. 可用资源
        3. 历史成功率
        4. 当前被封状态
        """
        # 如果已被封，需要更高级策略
        if context.is_blocked:
            return self._select_recovery_strategy(context)

        # 根据入口类型选择
        if entry.type == EntryType.OFFICIAL_API:
            return self.STRATEGIES["api_direct"]

        elif entry.type == EntryType.MOBILE_API:
            if entry.difficulty <= 2:
                return self.STRATEGIES["mobile_simple"]
            else:
                return self.STRATEGIES["mobile_advanced"]

        elif entry.type == EntryType.PC_WEB:
            if entry.difficulty >= 4:
                return self.STRATEGIES["hybrid_stealth"]
            else:
                return self.STRATEGIES["web_browser"]

        # 默认
        return self.STRATEGIES["mobile_simple"]

    def _select_recovery_strategy(self, context: StrategyContext) -> Strategy:
        """选择恢复策略"""
        # 被封后需要更高级的策略
        if context.failures < 3:
            return self.STRATEGIES["hybrid_stealth"]
        return self.STRATEGIES["web_browser"]

    def get_fallback(self, current: Strategy) -> Optional[Strategy]:
        """获取备选策略"""
        if current.fallback:
            return self.STRATEGIES.get(current.fallback)
        return None
```

---

## 三、风险评估与陷阱检测

### 蜜罐与假算法检测

```python
"""
蜜罐检测与假算法识别
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from enum import Enum
import hashlib
import time


class TrapType(Enum):
    """陷阱类型"""
    HONEYPOT_URL = "honeypot_url"          # 蜜罐URL
    FAKE_ALGORITHM = "fake_algorithm"       # 假签名算法
    TRACKING_PIXEL = "tracking_pixel"       # 追踪像素
    DELAYED_BAN = "delayed_ban"            # 延迟封禁
    DATA_POISON = "data_poison"            # 数据投毒


@dataclass
class TrapIndicator:
    """陷阱指标"""
    trap_type: TrapType
    confidence: float      # 置信度 0-1
    evidence: str          # 证据
    recommendation: str    # 建议


class TrapDetector:
    """陷阱检测器"""

    # 蜜罐URL特征
    HONEYPOT_PATTERNS = [
        r'/trap/', r'/honeypot/', r'/hidden/',
        r'display:\s*none', r'visibility:\s*hidden',
        r'position:\s*absolute.*left:\s*-\d+',
    ]

    # 假算法特征
    FAKE_ALGORITHM_SIGNS = [
        "算法返回值与预期不符",
        "相同输入产生不同输出",
        "算法过于简单（可能是诱饵）",
        "请求成功但数据明显错误",
    ]

    def detect_honeypot_url(self, url: str, html: str) -> Optional[TrapIndicator]:
        """
        检测蜜罐URL

        蜜罐特征:
        - 隐藏链接（CSS display:none）
        - 诱导路径（/admin, /secret）
        - robots.txt 禁止但故意暴露
        """
        import re

        for pattern in self.HONEYPOT_PATTERNS:
            if re.search(pattern, html, re.IGNORECASE):
                return TrapIndicator(
                    trap_type=TrapType.HONEYPOT_URL,
                    confidence=0.8,
                    evidence=f"匹配模式: {pattern}",
                    recommendation="跳过此URL，可能是蜜罐"
                )

        # 检查链接是否在隐藏元素中
        if url in html:
            # 简化检测：链接周围是否有隐藏样式
            idx = html.find(url)
            context = html[max(0, idx-200):idx+200]
            if any(h in context.lower() for h in ['display:none', 'visibility:hidden']):
                return TrapIndicator(
                    trap_type=TrapType.HONEYPOT_URL,
                    confidence=0.9,
                    evidence="链接在隐藏元素中",
                    recommendation="这是蜜罐链接，正常用户看不到"
                )

        return None

    def verify_algorithm(
        self,
        sign_func: callable,
        test_cases: List[Tuple[dict, str]]
    ) -> Optional[TrapIndicator]:
        """
        验证签名算法是否真实

        检测方法:
        1. 多次调用同一输入，结果应一致
        2. 结果应与抓包数据匹配
        3. 算法复杂度应合理
        """
        # 测试1: 一致性检验
        if test_cases:
            params, expected = test_cases[0]
            results = set()
            for _ in range(3):
                result = sign_func(params)
                results.add(result)

            if len(results) > 1:
                return TrapIndicator(
                    trap_type=TrapType.FAKE_ALGORITHM,
                    confidence=0.95,
                    evidence="相同输入产生不同输出",
                    recommendation="算法可能包含随机因素或是假算法"
                )

        # 测试2: 与预期匹配
        for params, expected in test_cases:
            actual = sign_func(params)
            if actual != expected:
                return TrapIndicator(
                    trap_type=TrapType.FAKE_ALGORITHM,
                    confidence=0.8,
                    evidence=f"预期 {expected[:20]}...，实际 {actual[:20]}...",
                    recommendation="算法结果与抓包不符，可能找错了函数"
                )

        return None

    def detect_data_poison(self, data: List[dict], field: str) -> Optional[TrapIndicator]:
        """
        检测数据投毒

        投毒特征:
        - 价格异常（过高或过低）
        - 电话号码格式正确但无法拨通
        - 地址真实但门牌号不存在
        """
        if not data:
            return None

        # 示例：检测价格异常
        if field == "price":
            prices = [d.get(field, 0) for d in data if d.get(field)]
            if prices:
                avg = sum(prices) / len(prices)
                outliers = [p for p in prices if p < avg * 0.1 or p > avg * 10]
                if len(outliers) / len(prices) > 0.3:
                    return TrapIndicator(
                        trap_type=TrapType.DATA_POISON,
                        confidence=0.7,
                        evidence=f"30%以上价格异常: {outliers[:5]}",
                        recommendation="数据可能被投毒，建议交叉验证"
                    )

        return None


class RiskAssessor:
    """风险评估器"""

    def assess_block_risk(
        self,
        success_rate: float,
        request_count: int,
        error_pattern: List[str]
    ) -> Dict:
        """
        评估被封风险

        Returns:
            {
                "risk_level": "low/medium/high/critical",
                "indicators": [...],
                "recommendations": [...]
            }
        """
        indicators = []
        recommendations = []
        risk_score = 0

        # 成功率下降
        if success_rate < 0.5:
            risk_score += 40
            indicators.append(f"成功率低: {success_rate:.1%}")
            recommendations.append("降低请求频率")

        # 请求量
        if request_count > 1000:
            risk_score += 20
            indicators.append(f"请求量大: {request_count}")
            recommendations.append("考虑切换IP或策略")

        # 错误模式
        block_keywords = ["blocked", "banned", "captcha", "verify", "forbidden"]
        for error in error_pattern:
            if any(kw in error.lower() for kw in block_keywords):
                risk_score += 30
                indicators.append(f"封禁信号: {error[:50]}")
                recommendations.append("立即暂停，更换策略")

        # 确定风险等级
        if risk_score >= 70:
            level = "critical"
        elif risk_score >= 50:
            level = "high"
        elif risk_score >= 30:
            level = "medium"
        else:
            level = "low"

        return {
            "risk_level": level,
            "risk_score": risk_score,
            "indicators": indicators,
            "recommendations": recommendations,
        }
```

---

## 四、动态调整

### 执行监控与自动切换

```python
"""
执行监控与动态调整
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
import asyncio


@dataclass
class ExecutionMetrics:
    """执行指标"""
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    blocked: int = 0

    # 时间窗口指标
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=100))
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful / self.total_requests

    @property
    def avg_response_time(self) -> float:
        if not self.response_times:
            return 0
        return sum(self.response_times) / len(self.response_times)

    @property
    def recent_error_rate(self) -> float:
        if len(self.recent_errors) < 10:
            return 0
        errors = sum(1 for e in self.recent_errors if e)
        return errors / len(self.recent_errors)


class AdaptiveExecutor:
    """自适应执行器"""

    def __init__(
        self,
        strategy_selector: StrategySelector,
        trap_detector: TrapDetector,
        risk_assessor: RiskAssessor,
    ):
        self.strategy_selector = strategy_selector
        self.trap_detector = trap_detector
        self.risk_assessor = risk_assessor

        self.metrics = ExecutionMetrics()
        self.current_strategy: Optional[Strategy] = None
        self.context: Optional[StrategyContext] = None

        # 调整参数
        self.base_delay = 1.0
        self.current_delay = 1.0
        self.max_delay = 30.0

    async def execute_with_adaptation(
        self,
        task_func: Callable,
        context: StrategyContext,
    ) -> Dict:
        """
        带自适应的执行

        流程:
        1. 执行任务
        2. 记录结果
        3. 评估风险
        4. 必要时调整策略
        """
        self.context = context

        while True:
            # 风险检查
            risk = self.risk_assessor.assess_block_risk(
                self.metrics.success_rate,
                self.metrics.total_requests,
                list(self.metrics.recent_errors)
            )

            if risk["risk_level"] == "critical":
                # 紧急情况：切换策略
                await self._switch_strategy("risk_critical")

            # 执行
            start_time = datetime.now()
            try:
                result = await task_func()
                self._record_success(start_time)

                # 成功后逐步恢复速度
                self._decrease_delay()

                return {"success": True, "data": result}

            except Exception as e:
                self._record_failure(start_time, str(e))

                # 判断是否需要切换策略
                if await self._should_switch_strategy(e):
                    await self._switch_strategy(str(e))
                else:
                    # 增加延迟
                    self._increase_delay()

                # 等待后重试
                await asyncio.sleep(self.current_delay)

    def _record_success(self, start_time: datetime):
        """记录成功"""
        self.metrics.total_requests += 1
        self.metrics.successful += 1
        self.metrics.recent_errors.append(False)

        elapsed = (datetime.now() - start_time).total_seconds()
        self.metrics.response_times.append(elapsed)

    def _record_failure(self, start_time: datetime, error: str):
        """记录失败"""
        self.metrics.total_requests += 1
        self.metrics.failed += 1
        self.metrics.recent_errors.append(True)

        if any(kw in error.lower() for kw in ["block", "ban", "captcha"]):
            self.metrics.blocked += 1

    async def _should_switch_strategy(self, error: Exception) -> bool:
        """判断是否需要切换策略"""
        error_str = str(error).lower()

        # 致命错误，必须切换
        fatal_keywords = ["banned", "blocked", "suspended", "terminated"]
        if any(kw in error_str for kw in fatal_keywords):
            return True

        # 连续失败次数过多
        recent_failures = sum(1 for e in list(self.metrics.recent_errors)[-10:] if e)
        if recent_failures >= 8:
            return True

        return False

    async def _switch_strategy(self, reason: str):
        """切换策略"""
        print(f"[TACTICS] 策略切换触发: {reason}")

        if self.current_strategy:
            fallback = self.strategy_selector.get_fallback(self.current_strategy)
            if fallback:
                print(f"[TACTICS] 切换到备选策略: {fallback.name}")
                self.current_strategy = fallback

                # 重置指标
                self.metrics = ExecutionMetrics()
                self.current_delay = self.base_delay
            else:
                print("[TACTICS] 无可用备选策略，任务终止")
                raise RuntimeError("所有策略已耗尽")

    def _increase_delay(self):
        """增加延迟（指数退避）"""
        self.current_delay = min(self.current_delay * 1.5, self.max_delay)
        print(f"[TACTICS] 延迟增加到 {self.current_delay:.1f}s")

    def _decrease_delay(self):
        """减少延迟"""
        self.current_delay = max(self.current_delay * 0.9, self.base_delay)


class ParameterTuner:
    """参数微调器"""

    def __init__(self):
        self.history: List[Dict] = []

    def tune_request_params(
        self,
        base_params: Dict,
        success_rate: float,
        error_pattern: str
    ) -> Dict:
        """
        根据执行情况微调请求参数

        调整项:
        - 请求头顺序
        - Cookie属性
        - 时间戳精度
        - 随机因子
        """
        params = base_params.copy()

        # 成功率低时增加随机性
        if success_rate < 0.7:
            params["add_noise"] = True
            params["randomize_headers"] = True

        # 根据错误类型调整
        if "fingerprint" in error_pattern.lower():
            params["rotate_fingerprint"] = True
        if "rate" in error_pattern.lower():
            params["decrease_speed"] = True

        return params
```

---

## 五、诊断日志

```
# 入口发现
[ENTRY] 探测目标: example.com
[ENTRY] 发现入口: 4 个
[ENTRY] - API /api/v2/ (难度:2)
[ENTRY] - Mobile m.example.com (难度:3)
[ENTRY] - H5 /h5/api/ (难度:3)
[ENTRY] - Web / (难度:5)
[ENTRY] 推荐入口: /api/v2/ (难度最低)

# 策略选择
[TACTICS] 选择策略: 直接API调用
[TACTICS] 资源需求: proxy=否, fingerprint=否

# 风险评估
[RISK] 当前风险: medium (score=45)
[RISK] 指标: 成功率 65%, 请求量 500
[RISK] 建议: 降低请求频率

# 陷阱检测
[TRAP] 检测到蜜罐URL: /admin/secret (置信度:0.9)
[TRAP] 跳过此URL

# 动态调整
[TACTICS] 连续失败 5 次
[TACTICS] 策略切换: 直接API → 移动端简单签名
[TACTICS] 延迟调整: 1s → 3s

# 算法验证
[VERIFY] 签名算法验证: 3 组测试用例
[VERIFY] 结果: 全部通过
[VERIFY] 算法可信
```

---

## 相关模块

- **输入**: [01-侦查模块](01-reconnaissance.md) - 目标信息
- **配合**: [02-反检测模块](02-anti-detection.md) - 指纹伪装
- **配合**: [03-签名模块](03-signature.md) - 算法逆向
- **配合**: [09-JS逆向模块](09-js-reverse.md) - 深度逆向
- **配合**: [10-验证码模块](10-captcha.md) - 验证码处理
- **输出**: [08-诊断模块](08-diagnosis.md) - 错误分析
- **输出**: [17-反馈闭环模块](17-feedback-loop.md) - 经验学习与反馈调节
