"""
战术决策模块 (Tactical Decision Engine)

功能:
- 入口发现与评估
- 策略匹配与选择
- 风险评估与陷阱检测
- 动态调整与参数优化
- 执行监控与自动切换

错误码: E_TACTICS_001 ~ E_TACTICS_004
"""

import asyncio
import hashlib
import random
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 错误码定义
# ============================================================================

class TacticsError(Exception):
    """战术决策错误基类"""
    def __init__(self, code: str, message: str, details: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


# 错误码
E_TACTICS_001 = "E_TACTICS_001"  # 入口发现失败
E_TACTICS_002 = "E_TACTICS_002"  # 策略选择失败
E_TACTICS_003 = "E_TACTICS_003"  # 风险评估失败
E_TACTICS_004 = "E_TACTICS_004"  # 动态调整失败


# ============================================================================
# 枚举
# ============================================================================

class EntryType(Enum):
    """入口类型"""
    OFFICIAL_API = "official_api"      # 官方API
    MOBILE_API = "mobile_api"          # 移动端API
    H5_API = "h5_api"                  # H5接口
    LEGACY_API = "legacy_api"          # 旧版接口
    THIRD_PARTY = "third_party"        # 第三方
    PC_WEB = "pc_web"                  # PC网页


class StrategyType(Enum):
    """策略类型"""
    DIRECT_API = "direct_api"              # 直接API调用
    MOBILE_REVERSE = "mobile_reverse"       # 移动端逆向
    WEB_SCRAPE = "web_scrape"              # 网页抓取
    BROWSER_AUTOMATION = "browser_auto"     # 浏览器自动化
    HYBRID = "hybrid"                       # 混合策略


class TrapType(Enum):
    """陷阱类型"""
    HONEYPOT_URL = "honeypot_url"          # 蜜罐URL
    FAKE_ALGORITHM = "fake_algorithm"       # 假签名算法
    TRACKING_PIXEL = "tracking_pixel"       # 追踪像素
    DELAYED_BAN = "delayed_ban"            # 延迟封禁
    DATA_POISON = "data_poison"            # 数据投毒


# ============================================================================
# 数据类
# ============================================================================

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

    def __str__(self) -> str:
        return (
            f"{self.type.value} | {self.url} | "
            f"难度:{self.difficulty} | 验证码风险:{self.captcha_risk:.0%}"
        )


@dataclass
class TargetAnalysis:
    """目标分析结果"""
    domain: str
    entries: List[EntryPoint] = field(default_factory=list)
    recommended: Optional[EntryPoint] = None
    risk_level: str = "unknown"  # low/medium/high/extreme

    def __str__(self) -> str:
        return (
            f"域名: {self.domain} | "
            f"发现入口: {len(self.entries)}个 | "
            f"风险等级: {self.risk_level}"
        )


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


@dataclass
class TrapIndicator:
    """陷阱指标"""
    trap_type: TrapType
    confidence: float      # 置信度 0-1
    evidence: str          # 证据
    recommendation: str    # 建议


@dataclass
class TacticsDecision:
    """战术决策"""
    recommended_tactics: StrategyType
    confidence: float
    reasoning: str
    alternative_tactics: List[StrategyType]
    required_skills: List[str]
    estimated_difficulty: str
    success_rate: float


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


# ============================================================================
# 入口发现器
# ============================================================================

class EntryDiscovery:
    """
    入口发现器

    通过真实HTTP请求探测目标域名的可用入口，分析响应特征判断入口类型和难度。

    使用示例:
        discovery = EntryDiscovery()
        # 同步版本
        analysis = discovery.discover("jd.com")
        # 异步版本 (推荐，更快)
        analysis = await discovery.discover_async("jd.com")
    """

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

    # 已知反爬严格的域名
    KNOWN_STRICT_DOMAINS = {
        "taobao.com": 4,
        "tmall.com": 4,
        "jd.com": 3,
        "pinduoduo.com": 4,
        "douyin.com": 4,
        "xiaohongshu.com": 4,
        "zhihu.com": 3,
        "weibo.com": 3,
    }

    # API响应特征
    API_CONTENT_TYPES = [
        "application/json",
        "application/xml",
        "text/json",
        "text/xml",
    ]

    # 签名参数特征
    SIGNATURE_INDICATORS = [
        "sign", "signature", "token", "timestamp", "nonce",
        "h5st", "x-sign", "wbi", "x-bogus", "a_bogus",
    ]

    def __init__(self, timeout: float = 10.0, max_concurrent: int = 10):
        """
        初始化入口发现器

        Args:
            timeout: 请求超时时间(秒)
            max_concurrent: 最大并发数
        """
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self._probe_results: Dict[str, Dict] = {}

    def discover(self, domain: str, quick_mode: bool = False) -> TargetAnalysis:
        """
        发现目标的所有可能入口 (同步版本)

        Args:
            domain: 目标域名
            quick_mode: 快速模式，只探测主要入口

        Returns:
            目标分析结果
        """
        try:
            # 尝试使用异步版本
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在已有事件循环中，使用同步方式
                return self._discover_sync(domain, quick_mode)
            else:
                return loop.run_until_complete(self.discover_async(domain, quick_mode))
        except RuntimeError:
            # 没有事件循环，创建新的
            return asyncio.run(self.discover_async(domain, quick_mode))

    def _discover_sync(self, domain: str, quick_mode: bool = False) -> TargetAnalysis:
        """同步探测入口"""
        logger.info(f"[ENTRY] 开始同步探测域名: {domain}")

        analysis = TargetAnalysis(domain=domain)

        try:
            import httpx

            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                # 首先探测主站
                main_entry = self._probe_url_sync(
                    client, f"https://{domain}/", EntryType.PC_WEB
                )
                if main_entry:
                    analysis.entries.append(main_entry)

                # 探测常见API路径
                patterns_to_check = []
                for entry_type, patterns in self.PROBE_PATTERNS.items():
                    for pattern in (patterns[:2] if quick_mode else patterns):
                        patterns_to_check.append((f"https://{domain}{pattern}", entry_type))

                for url, entry_type in patterns_to_check:
                    entry = self._probe_url_sync(client, url, entry_type)
                    if entry:
                        analysis.entries.append(entry)

                # 探测移动端域名
                for prefix in (self.MOBILE_DOMAINS[:2] if quick_mode else self.MOBILE_DOMAINS):
                    mobile_domain = f"{prefix}{domain}"
                    url = f"https://{mobile_domain}/"
                    entry = self._probe_url_sync(client, url, EntryType.MOBILE_API)
                    if entry:
                        analysis.entries.append(entry)

        except ImportError:
            logger.warning("[ENTRY] httpx 未安装，使用模拟数据")
            return self._fallback_discovery(domain)
        except Exception as e:
            logger.error(f"[ENTRY] 同步探测异常: {e}")

        # 确保至少有PC Web入口
        if not any(e.type == EntryType.PC_WEB for e in analysis.entries):
            analysis.entries.append(self._create_fallback_entry(domain))

        # 后处理
        analysis.recommended = self._select_best_entry(analysis.entries)
        analysis.risk_level = self._assess_target_risk(analysis)

        logger.info(f"[ENTRY] 发现 {len(analysis.entries)} 个入口")
        return analysis

    async def discover_async(self, domain: str, quick_mode: bool = False) -> TargetAnalysis:
        """
        发现目标的所有可能入口 (异步版本，推荐)

        Args:
            domain: 目标域名
            quick_mode: 快速模式

        Returns:
            目标分析结果
        """
        logger.info(f"[ENTRY] 开始异步探测域名: {domain}")

        analysis = TargetAnalysis(domain=domain)

        try:
            import httpx

            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=self.max_concurrent)
            ) as client:
                # 构建所有待探测URL
                probe_tasks = []

                # 主站
                probe_tasks.append(
                    self._probe_url_async(client, f"https://{domain}/", EntryType.PC_WEB)
                )

                # API路径
                for entry_type, patterns in self.PROBE_PATTERNS.items():
                    for pattern in (patterns[:2] if quick_mode else patterns):
                        url = f"https://{domain}{pattern}"
                        probe_tasks.append(
                            self._probe_url_async(client, url, entry_type)
                        )

                # 移动端域名
                for prefix in (self.MOBILE_DOMAINS[:3] if quick_mode else self.MOBILE_DOMAINS):
                    mobile_domain = f"{prefix}{domain}"
                    url = f"https://{mobile_domain}/"
                    probe_tasks.append(
                        self._probe_url_async(client, url, EntryType.MOBILE_API)
                    )

                # 并发执行所有探测
                results = await asyncio.gather(*probe_tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, EntryPoint):
                        analysis.entries.append(result)
                    elif isinstance(result, Exception):
                        logger.debug(f"[ENTRY] 探测异常: {result}")

        except ImportError:
            logger.warning("[ENTRY] httpx 未安装，使用模拟数据")
            return self._fallback_discovery(domain)
        except Exception as e:
            logger.error(f"[ENTRY] 异步探测异常: {e}")

        # 确保至少有PC Web入口
        if not any(e.type == EntryType.PC_WEB for e in analysis.entries):
            analysis.entries.append(self._create_fallback_entry(domain))

        # 后处理
        analysis.recommended = self._select_best_entry(analysis.entries)
        analysis.risk_level = self._assess_target_risk(analysis)

        logger.info(f"[ENTRY] 发现 {len(analysis.entries)} 个入口")
        logger.info(f"[ENTRY] 推荐入口: {analysis.recommended}")

        return analysis

    def _probe_url_sync(self, client, url: str, entry_type: EntryType) -> Optional[EntryPoint]:
        """同步探测单个URL"""
        try:
            resp = client.head(url, timeout=5)
            return self._analyze_response(resp, url, entry_type)
        except Exception as e:
            logger.debug(f"[ENTRY] HEAD 请求失败，尝试 GET: {url}")
            try:
                resp = client.get(url, timeout=5)
                return self._analyze_response(resp, url, entry_type)
            except Exception as e2:
                logger.debug(f"[ENTRY] 探测失败: {url} - {e2}")
                return None

    async def _probe_url_async(
        self,
        client,
        url: str,
        entry_type: EntryType
    ) -> Optional[EntryPoint]:
        """异步探测单个URL"""
        try:
            # 先尝试 HEAD 请求（更快）
            resp = await client.head(url, timeout=5)
            return self._analyze_response(resp, url, entry_type)
        except Exception:
            try:
                # HEAD 失败，尝试 GET
                resp = await client.get(url, timeout=5)
                return self._analyze_response(resp, url, entry_type)
            except Exception as e:
                logger.debug(f"[ENTRY] 异步探测失败: {url} - {e}")
                return None

    def _analyze_response(self, resp, url: str, entry_type: EntryType) -> Optional[EntryPoint]:
        """
        分析HTTP响应，判断入口特征

        Args:
            resp: httpx.Response 对象
            url: 请求URL
            entry_type: 预期的入口类型

        Returns:
            入口点信息，如果不是有效入口则返回None
        """
        # 状态码判断
        if resp.status_code >= 500:
            return None  # 服务器错误，跳过

        if resp.status_code == 404:
            return None  # 不存在

        # 分析响应特征
        content_type = resp.headers.get("content-type", "").lower()
        server = resp.headers.get("server", "").lower()

        # 判断是否为API入口
        is_api = any(ct in content_type for ct in self.API_CONTENT_TYPES)

        # 如果Content-Type是JSON但状态码是4xx，可能是有签名要求
        auth_required = resp.status_code in [401, 403]
        signature_required = False

        # 检查响应体中的签名提示
        try:
            if resp.status_code in [400, 401, 403] and is_api:
                body = resp.text[:1000] if hasattr(resp, 'text') else ""
                for indicator in self.SIGNATURE_INDICATORS:
                    if indicator in body.lower():
                        signature_required = True
                        break
        except:
            pass

        # 计算难度
        difficulty = self._calculate_difficulty(
            url, resp.status_code, is_api, auth_required, signature_required, server
        )

        # 计算验证码风险
        captcha_risk = self._estimate_captcha_risk(url, server, resp.headers)

        # 确定实际入口类型
        actual_type = entry_type
        if is_api and entry_type == EntryType.PC_WEB:
            actual_type = EntryType.OFFICIAL_API

        # 构造入口信息
        notes = []
        if is_api:
            notes.append("API接口")
        if auth_required:
            notes.append("需要认证")
        if signature_required:
            notes.append("需要签名")
        if resp.status_code == 200:
            notes.append("可直接访问")

        return EntryPoint(
            type=actual_type,
            url=url,
            method="GET",
            auth_required=auth_required,
            signature_required=signature_required,
            captcha_risk=captcha_risk,
            rate_limit=self._detect_rate_limit(resp.headers),
            difficulty=difficulty,
            notes="; ".join(notes) if notes else "正常响应"
        )

    def _calculate_difficulty(
        self,
        url: str,
        status_code: int,
        is_api: bool,
        auth_required: bool,
        signature_required: bool,
        server: str
    ) -> int:
        """计算入口难度 (1-5)"""
        difficulty = 1

        # 基础难度：根据已知严格域名
        for domain, base_diff in self.KNOWN_STRICT_DOMAINS.items():
            if domain in url:
                difficulty = max(difficulty, base_diff - 1)
                break

        # 需要认证 +1
        if auth_required:
            difficulty += 1

        # 需要签名 +1
        if signature_required:
            difficulty += 1

        # 反爬服务器特征
        anti_scraping_servers = ["cloudflare", "akamai", "incapsula", "imperva"]
        if any(s in server for s in anti_scraping_servers):
            difficulty += 1

        # 非200状态码
        if status_code in [403, 401]:
            difficulty += 1

        return min(5, difficulty)

    def _estimate_captcha_risk(self, url: str, server: str, headers: Dict) -> float:
        """估计验证码出现概率"""
        risk = 0.1  # 基础风险

        # 已知严格域名
        for domain in self.KNOWN_STRICT_DOMAINS:
            if domain in url:
                risk += 0.3
                break

        # Cloudflare等CDN
        if "cloudflare" in server or "cf-ray" in str(headers):
            risk += 0.2

        # 限流头
        if "x-ratelimit" in str(headers).lower():
            risk += 0.1

        return min(0.9, risk)

    def _detect_rate_limit(self, headers: Dict) -> Optional[int]:
        """检测响应中的速率限制信息"""
        for key in headers:
            key_lower = key.lower()
            if "ratelimit" in key_lower or "rate-limit" in key_lower:
                try:
                    value = headers[key]
                    if "remaining" in key_lower:
                        return int(value)
                    elif "limit" in key_lower:
                        return int(value)
                except:
                    pass
        return None

    def _create_fallback_entry(self, domain: str) -> EntryPoint:
        """创建后备PC Web入口"""
        difficulty = 3
        for d, diff in self.KNOWN_STRICT_DOMAINS.items():
            if d in domain:
                difficulty = diff
                break

        return EntryPoint(
            type=EntryType.PC_WEB,
            url=f"https://{domain}/",
            difficulty=difficulty,
            captcha_risk=0.5,
            notes="PC Web后备方案"
        )

    def _fallback_discovery(self, domain: str) -> TargetAnalysis:
        """后备发现方法 (当HTTP请求不可用时)"""
        analysis = TargetAnalysis(domain=domain)

        # 基于已知域名信息创建入口
        difficulty = 3
        for d, diff in self.KNOWN_STRICT_DOMAINS.items():
            if d in domain:
                difficulty = diff
                break

        # 添加预设入口
        analysis.entries.append(EntryPoint(
            type=EntryType.PC_WEB,
            url=f"https://{domain}/",
            difficulty=difficulty,
            captcha_risk=0.5,
            notes="后备模式"
        ))

        analysis.entries.append(EntryPoint(
            type=EntryType.MOBILE_API,
            url=f"https://m.{domain}/",
            difficulty=max(1, difficulty - 1),
            captcha_risk=0.3,
            notes="移动端后备"
        ))

        analysis.recommended = self._select_best_entry(analysis.entries)
        analysis.risk_level = self._assess_target_risk(analysis)

        return analysis

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

        # 综合评分：优先级 + 难度 + 签名需求
        def score(e: EntryPoint) -> float:
            base = priority.get(e.type, 10) * 10 + e.difficulty
            if e.signature_required:
                base += 5
            if e.auth_required:
                base += 3
            return base

        return min(entries, key=score)

    def _assess_target_risk(self, analysis: TargetAnalysis) -> str:
        """评估目标风险等级"""
        if not analysis.entries:
            return "unknown"

        min_difficulty = min(e.difficulty for e in analysis.entries)
        avg_captcha_risk = sum(e.captcha_risk for e in analysis.entries) / len(analysis.entries)

        if min_difficulty <= 2 and avg_captcha_risk < 0.3:
            return "low"
        elif min_difficulty <= 3 and avg_captcha_risk < 0.5:
            return "medium"
        elif min_difficulty <= 4:
            return "high"
        return "extreme"


# ============================================================================
# 策略选择器
# ============================================================================

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

        Args:
            context: 策略上下文
            entry: 入口点

        Returns:
            推荐策略
        """
        logger.info(f"[TACTICS] 选择策略: 入口类型={entry.type.value}, 难度={entry.difficulty}")

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


# ============================================================================
# 陷阱检测器
# ============================================================================

class TrapDetector:
    """陷阱检测器"""

    # 蜜罐URL特征
    HONEYPOT_PATTERNS = [
        r'/trap/', r'/honeypot/', r'/hidden/',
        r'display:\s*none', r'visibility:\s*hidden',
        r'position:\s*absolute.*left:\s*-\d+',
    ]

    def detect_honeypot_url(self, url: str, html: str) -> Optional[TrapIndicator]:
        """
        检测蜜罐URL

        Args:
            url: URL
            html: HTML内容

        Returns:
            陷阱指标
        """
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
            idx = html.find(url)
            context = html[max(0, idx - 200):idx + 200]
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
        sign_func: Callable,
        test_cases: List[Tuple[dict, str]]
    ) -> Optional[TrapIndicator]:
        """
        验证签名算法是否真实

        Args:
            sign_func: 签名函数
            test_cases: 测试用例 [(params, expected), ...]

        Returns:
            陷阱指标
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


# ============================================================================
# 风险评估器
# ============================================================================

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

        Args:
            success_rate: 成功率
            request_count: 请求数量
            error_pattern: 错误模式列表

        Returns:
            风险评估结果
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


# ============================================================================
# 战术决策器
# ============================================================================

class TacticsDecider:
    """战术决策器"""

    def __init__(self):
        self.entry_discovery = EntryDiscovery()
        self.strategy_selector = StrategySelector()
        self.trap_detector = TrapDetector()
        self.risk_assessor = RiskAssessor()

    def decide(
        self,
        domain: str,
        context: Optional[Dict] = None
    ) -> TacticsDecision:
        """
        决定最优战术

        Args:
            domain: 目标域名
            context: 上下文信息

        Returns:
            战术决策
        """
        logger.info(f"[TACTICS] 开始战术决策: {domain}")

        # 1. 入口发现
        analysis = self.entry_discovery.discover(domain)

        if not analysis.recommended:
            raise TacticsError(
                E_TACTICS_001,
                f"未发现可用入口: {domain}",
                {"domain": domain}
            )

        # 2. 策略选择
        strategy_context = StrategyContext(
            target_domain=domain,
            entry_point=analysis.recommended
        )
        strategy = self.strategy_selector.select(strategy_context, analysis.recommended)

        # 3. 构建决策
        decision = TacticsDecision(
            recommended_tactics=strategy.type,
            confidence=0.8,
            reasoning=f"入口类型={analysis.recommended.type.value}, 难度={analysis.recommended.difficulty}",
            alternative_tactics=[
                s.type for s in self.strategy_selector.STRATEGIES.values()
                if s.type != strategy.type
            ][:2],
            required_skills=self._get_required_skills(strategy),
            estimated_difficulty=self._estimate_difficulty(analysis.recommended.difficulty),
            success_rate=strategy.success_rate
        )

        logger.info(f"[TACTICS] 决策完成: {decision.recommended_tactics.value}")

        return decision

    def _get_required_skills(self, strategy: Strategy) -> List[str]:
        """获取所需技能"""
        skills = []
        if strategy.needs_proxy:
            skills.append("proxy")
        if strategy.needs_fingerprint:
            skills.append("fingerprint")
        if strategy.needs_captcha_solver:
            skills.append("captcha")
        if strategy.needs_js_reverse:
            skills.append("js_reverse")
        return skills

    def _estimate_difficulty(self, entry_difficulty: int) -> str:
        """估算难度"""
        if entry_difficulty <= 2:
            return "easy"
        elif entry_difficulty <= 3:
            return "medium"
        elif entry_difficulty <= 4:
            return "hard"
        else:
            return "expert"


# ============================================================================
# 使用示例
# ============================================================================

def example_usage():
    """使用示例"""
    print("=" * 80)
    print("战术决策模块 - 使用示例")
    print("=" * 80)

    # 1. 创建决策器
    decider = TacticsDecider()

    # 2. 测试不同域名
    test_domains = [
        "jd.com",
        "taobao.com",
        "example.com",
    ]

    for domain in test_domains:
        print(f"\n{'=' * 80}")
        print(f"测试域名: {domain}")
        print("-" * 80)

        # 入口发现
        analysis = decider.entry_discovery.discover(domain)
        print(f"\n入口分析: {analysis}")
        print(f"发现入口数量: {len(analysis.entries)}")
        for i, entry in enumerate(analysis.entries, 1):
            print(f"  {i}. {entry}")
        print(f"\n推荐入口: {analysis.recommended}")
        print(f"风险等级: {analysis.risk_level}")

        # 战术决策
        decision = decider.decide(domain)
        print(f"\n战术决策:")
        print(f"  推荐策略: {decision.recommended_tactics.value}")
        print(f"  置信度: {decision.confidence:.1%}")
        print(f"  理由: {decision.reasoning}")
        print(f"  备选策略: {[t.value for t in decision.alternative_tactics]}")
        print(f"  所需技能: {decision.required_skills}")
        print(f"  预估难度: {decision.estimated_difficulty}")
        print(f"  预估成功率: {decision.success_rate:.1%}")

    # 3. 风险评估
    print(f"\n{'=' * 80}")
    print("风险评估示例")
    print("-" * 80)
    risk_assessor = RiskAssessor()
    risk = risk_assessor.assess_block_risk(
        success_rate=0.4,
        request_count=500,
        error_pattern=["403 Forbidden", "IP blocked"]
    )
    print(f"风险等级: {risk['risk_level']}")
    print(f"风险分数: {risk['risk_score']}")
    print(f"指标: {risk['indicators']}")
    print(f"建议: {risk['recommendations']}")


if __name__ == "__main__":
    example_usage()
