"""
故障决策树模块 (Fault Decision Tree Module)

功能:
- 故障分类与识别
- 决策路径推荐
- 自动恢复执行
- 故障上报与追溯
- 经验学习与优化

错误码: E_FAULT_001 ~ E_FAULT_005
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 错误码定义
# ============================================================================

class FaultTreeError(Exception):
    """故障决策树错误基类"""
    def __init__(self, code: str, message: str, details: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


# 错误码
E_FAULT_001 = "E_FAULT_001"  # 未知故障类型
E_FAULT_002 = "E_FAULT_002"  # 决策失败
E_FAULT_003 = "E_FAULT_003"  # 恢复执行失败
E_FAULT_004 = "E_FAULT_004"  # 配置错误
E_FAULT_005 = "E_FAULT_005"  # 故障升级


# ============================================================================
# 故障分类
# ============================================================================

class FaultCategory(Enum):
    """故障分类"""
    # 网络层
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_DNS = "network_dns"
    NETWORK_SSL = "network_ssl"
    NETWORK_CONNECTION = "network_connection"

    # HTTP层
    HTTP_400 = "http_400"
    HTTP_401 = "http_401"
    HTTP_403 = "http_403"
    HTTP_404 = "http_404"
    HTTP_429 = "http_429"
    HTTP_500 = "http_500"
    HTTP_502 = "http_502"
    HTTP_503 = "http_503"
    HTTP_504 = "http_504"
    HTTP_5XX = "http_5xx"

    # 反爬层
    ANTI_IP_BLOCKED = "anti_ip_blocked"
    ANTI_CAPTCHA = "anti_captcha"
    ANTI_SIGNATURE = "anti_signature"
    ANTI_FINGERPRINT = "anti_fingerprint"
    ANTI_BEHAVIOR = "anti_behavior"
    ANTI_RATE_LIMIT = "anti_rate_limit"

    # 数据层
    DATA_EMPTY = "data_empty"
    DATA_INVALID = "data_invalid"
    DATA_FORMAT_CHANGED = "data_format_changed"
    DATA_ELEMENT_NOT_FOUND = "data_element_not_found"

    # 浏览器层
    BROWSER_CRASH = "browser_crash"
    BROWSER_TIMEOUT = "browser_timeout"
    BROWSER_MEMORY = "browser_memory"
    BROWSER_SCRIPT_ERROR = "browser_script_error"

    # 逻辑层
    LOGIC_INFINITE_LOOP = "logic_infinite_loop"
    LOGIC_STATE_LOST = "logic_state_lost"
    LOGIC_UNEXPECTED = "logic_unexpected"

    # 未知
    UNKNOWN = "unknown"


class FaultSeverity(Enum):
    """故障严重程度"""
    LOW = "low"          # 低 - 不影响任务
    MEDIUM = "medium"    # 中 - 部分影响
    HIGH = "high"        # 高 - 严重影响
    CRITICAL = "critical"  # 致命 - 完全无法执行


# ============================================================================
# 恢复动作
# ============================================================================

class RecoveryAction(Enum):
    """恢复动作"""
    # 网络层动作
    RETRY = "retry"
    SWITCH_PROXY = "switch_proxy"
    CHANGE_DNS = "change_dns"
    INCREASE_TIMEOUT = "increase_timeout"
    USE_DIRECT_CONNECTION = "use_direct_connection"

    # HTTP层动作
    USE_STEALTH = "use_stealth"
    REDUCE_RATE = "reduce_rate"
    ROTATE_COOKIE = "rotate_cookie"
    CHANGE_USER_AGENT = "change_user_agent"
    ADD_REFERER = "add_referer"
    WAIT_COOLDOWN = "wait_cooldown"

    # 反爬层动作
    SOLVE_CAPTCHA = "solve_captcha"
    FIX_SIGNATURE = "fix_signature"
    UPDATE_FINGERPRINT = "update_fingerprint"
    SWITCH_STRATEGY = "switch_strategy"
    ENABLE_BROWSER = "enable_browser"

    # 数据层动作
    UPDATE_SELECTOR = "update_selector"
    USE_BACKUP_SELECTOR = "use_backup_selector"
    REPORT_FORMAT_CHANGE = "report_format_change"
    WAIT_PAGE_LOAD = "wait_page_load"

    # 浏览器层动作
    RESTART_BROWSER = "restart_browser"
    CLEAR_CACHE = "clear_cache"
    DISABLE_EXTENSIONS = "disable_extensions"

    # 升级动作
    ESCALATE_TO_USER = "escalate_to_user"
    ABORT_TASK = "abort_task"
    USE_FALLBACK = "use_fallback"


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class FaultDecision:
    """故障决策"""
    fault_category: FaultCategory
    severity: FaultSeverity
    recovery_actions: List[RecoveryAction]
    priority: int  # 执行优先级 1-10
    auto_recoverable: bool  # 是否可自动恢复
    estimated_recovery_time: str  # 预估恢复时间
    fallback_plan: Optional[str] = None
    reasoning: str = ""  # 决策理由

    def __str__(self) -> str:
        return (
            f"[{self.fault_category.value}] {self.severity.value} | "
            f"可自动恢复: {self.auto_recoverable} | "
            f"动作: {[a.value for a in self.recovery_actions]}"
        )


@dataclass
class FaultReport:
    """故障上报"""
    fault_id: str
    timestamp: datetime
    task_id: str
    fault_category: FaultCategory
    fault_type: str
    severity: FaultSeverity

    # 上下文
    context: Dict[str, Any] = field(default_factory=dict)

    # 诊断
    diagnosis: Dict[str, Any] = field(default_factory=dict)

    # 解决方案
    resolution: Dict[str, Any] = field(default_factory=dict)

    # 预防措施
    prevention: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    actions_taken: List[RecoveryAction]
    outcome: str
    cost_time_ms: float
    errors: List[str] = field(default_factory=list)


# ============================================================================
# 故障决策树
# ============================================================================

class FaultDecisionTree:
    """故障决策树"""

    def __init__(self):
        self.rules: Dict[FaultCategory, FaultDecision] = {}
        self._init_rules()

    def _init_rules(self):
        """初始化决策规则"""

        # 网络层规则
        self.rules[FaultCategory.NETWORK_TIMEOUT] = FaultDecision(
            fault_category=FaultCategory.NETWORK_TIMEOUT,
            severity=FaultSeverity.MEDIUM,
            recovery_actions=[
                RecoveryAction.INCREASE_TIMEOUT,
                RecoveryAction.RETRY,
                RecoveryAction.SWITCH_PROXY,
            ],
            priority=5,
            auto_recoverable=True,
            estimated_recovery_time="30-60s",
            reasoning="网络超时通常是暂时性问题，增加超时时间后重试"
        )

        self.rules[FaultCategory.NETWORK_DNS] = FaultDecision(
            fault_category=FaultCategory.NETWORK_DNS,
            severity=FaultSeverity.HIGH,
            recovery_actions=[
                RecoveryAction.CHANGE_DNS,
                RecoveryAction.USE_DIRECT_CONNECTION,
                RecoveryAction.ESCALATE_TO_USER,
            ],
            priority=8,
            auto_recoverable=False,
            estimated_recovery_time="5-10min",
            reasoning="DNS失败可能是域名错误，需要人工确认"
        )

        self.rules[FaultCategory.NETWORK_SSL] = FaultDecision(
            fault_category=FaultCategory.NETWORK_SSL,
            severity=FaultSeverity.MEDIUM,
            recovery_actions=[
                RecoveryAction.USE_DIRECT_CONNECTION,
                RecoveryAction.ESCALATE_TO_USER,
            ],
            priority=7,
            auto_recoverable=False,
            estimated_recovery_time="manual",
            reasoning="SSL证书错误需要人工判断是否信任"
        )

        # HTTP层规则
        self.rules[FaultCategory.HTTP_403] = FaultDecision(
            fault_category=FaultCategory.HTTP_403,
            severity=FaultSeverity.HIGH,
            recovery_actions=[
                RecoveryAction.SWITCH_PROXY,
                RecoveryAction.CHANGE_USER_AGENT,
                RecoveryAction.ADD_REFERER,
                RecoveryAction.USE_STEALTH,
            ],
            priority=8,
            auto_recoverable=True,
            estimated_recovery_time="60-120s",
            reasoning="403通常是反爬检测，需要更换IP和指纹"
        )

        self.rules[FaultCategory.HTTP_429] = FaultDecision(
            fault_category=FaultCategory.HTTP_429,
            severity=FaultSeverity.MEDIUM,
            recovery_actions=[
                RecoveryAction.WAIT_COOLDOWN,
                RecoveryAction.REDUCE_RATE,
                RecoveryAction.SWITCH_PROXY,
            ],
            priority=6,
            auto_recoverable=True,
            estimated_recovery_time="30-300s",
            reasoning="429是频率限制，需要降速和等待"
        )

        self.rules[FaultCategory.HTTP_404] = FaultDecision(
            fault_category=FaultCategory.HTTP_404,
            severity=FaultSeverity.MEDIUM,
            recovery_actions=[
                RecoveryAction.USE_FALLBACK,
                RecoveryAction.ESCALATE_TO_USER,
            ],
            priority=5,
            auto_recoverable=False,
            estimated_recovery_time="manual",
            reasoning="404说明资源不存在，需要确认URL正确性"
        )

        self.rules[FaultCategory.HTTP_5XX] = FaultDecision(
            fault_category=FaultCategory.HTTP_5XX,
            severity=FaultSeverity.LOW,
            recovery_actions=[
                RecoveryAction.WAIT_COOLDOWN,
                RecoveryAction.RETRY,
            ],
            priority=3,
            auto_recoverable=True,
            estimated_recovery_time="60-300s",
            reasoning="5xx是服务端问题，等待后重试"
        )

        # 反爬层规则
        self.rules[FaultCategory.ANTI_IP_BLOCKED] = FaultDecision(
            fault_category=FaultCategory.ANTI_IP_BLOCKED,
            severity=FaultSeverity.CRITICAL,
            recovery_actions=[
                RecoveryAction.SWITCH_PROXY,
                RecoveryAction.REDUCE_RATE,
                RecoveryAction.USE_STEALTH,
            ],
            priority=10,
            auto_recoverable=True,
            estimated_recovery_time="immediate",
            reasoning="IP被封必须立即切换"
        )

        self.rules[FaultCategory.ANTI_CAPTCHA] = FaultDecision(
            fault_category=FaultCategory.ANTI_CAPTCHA,
            severity=FaultSeverity.HIGH,
            recovery_actions=[
                RecoveryAction.SOLVE_CAPTCHA,
                RecoveryAction.SWITCH_PROXY,
                RecoveryAction.ESCALATE_TO_USER,
            ],
            priority=8,
            auto_recoverable=False,
            estimated_recovery_time="manual",
            reasoning="验证码需要人工或第三方服务处理"
        )

        self.rules[FaultCategory.ANTI_SIGNATURE] = FaultDecision(
            fault_category=FaultCategory.ANTI_SIGNATURE,
            severity=FaultSeverity.HIGH,
            recovery_actions=[
                RecoveryAction.FIX_SIGNATURE,
                RecoveryAction.SWITCH_STRATEGY,
                RecoveryAction.ESCALATE_TO_USER,
            ],
            priority=9,
            auto_recoverable=False,
            estimated_recovery_time="manual",
            reasoning="签名错误需要重新分析算法"
        )

        # 数据层规则
        self.rules[FaultCategory.DATA_EMPTY] = FaultDecision(
            fault_category=FaultCategory.DATA_EMPTY,
            severity=FaultSeverity.MEDIUM,
            recovery_actions=[
                RecoveryAction.WAIT_PAGE_LOAD,
                RecoveryAction.UPDATE_SELECTOR,
                RecoveryAction.USE_BACKUP_SELECTOR,
            ],
            priority=6,
            auto_recoverable=True,
            estimated_recovery_time="10-30s",
            reasoning="数据为空可能是页面未加载完成"
        )

        self.rules[FaultCategory.DATA_ELEMENT_NOT_FOUND] = FaultDecision(
            fault_category=FaultCategory.DATA_ELEMENT_NOT_FOUND,
            severity=FaultSeverity.HIGH,
            recovery_actions=[
                RecoveryAction.UPDATE_SELECTOR,
                RecoveryAction.USE_BACKUP_SELECTOR,
                RecoveryAction.REPORT_FORMAT_CHANGE,
            ],
            priority=7,
            auto_recoverable=False,
            estimated_recovery_time="manual",
            reasoning="元素定位失败可能是页面改版"
        )

        # 浏览器层规则
        self.rules[FaultCategory.BROWSER_CRASH] = FaultDecision(
            fault_category=FaultCategory.BROWSER_CRASH,
            severity=FaultSeverity.CRITICAL,
            recovery_actions=[
                RecoveryAction.RESTART_BROWSER,
                RecoveryAction.CLEAR_CACHE,
            ],
            priority=10,
            auto_recoverable=True,
            estimated_recovery_time="30-60s",
            reasoning="浏览器崩溃需要重启"
        )

        # 未知故障
        self.rules[FaultCategory.UNKNOWN] = FaultDecision(
            fault_category=FaultCategory.UNKNOWN,
            severity=FaultSeverity.MEDIUM,
            recovery_actions=[
                RecoveryAction.RETRY,
                RecoveryAction.ESCALATE_TO_USER,
            ],
            priority=5,
            auto_recoverable=False,
            estimated_recovery_time="manual",
            reasoning="未知故障需要人工分析"
        )

    def diagnose(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> FaultDecision:
        """
        诊断故障并给出决策

        Args:
            error: 异常对象
            context: 上下文信息

        Returns:
            故障决策
        """
        # 1. 分类故障
        fault_category = self.classify_fault(error, context)

        # 2. 获取决策
        decision = self.rules.get(fault_category)

        if decision is None:
            # 未知故障，使用默认决策
            logger.warning(f"[FAULT] 未知故障类型: {fault_category}")
            decision = self.rules[FaultCategory.UNKNOWN]

        logger.info(f"[FAULT] 故障诊断: {decision}")

        return decision

    def classify_fault(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> FaultCategory:
        """
        分类故障

        Args:
            error: 异常对象
            context: 上下文信息

        Returns:
            故障分类
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # HTTP状态码检查
        status_code = context.get("status_code")
        if status_code:
            if status_code == 403:
                return FaultCategory.HTTP_403
            elif status_code == 404:
                return FaultCategory.HTTP_404
            elif status_code == 429:
                return FaultCategory.HTTP_429
            elif status_code == 500:
                return FaultCategory.HTTP_500
            elif status_code == 502:
                return FaultCategory.HTTP_502
            elif status_code == 503:
                return FaultCategory.HTTP_503
            elif status_code == 504:
                return FaultCategory.HTTP_504
            elif 500 <= status_code < 600:
                return FaultCategory.HTTP_5XX

        # 网络层错误
        if "timeout" in error_str or "timed out" in error_str:
            return FaultCategory.NETWORK_TIMEOUT
        if "dns" in error_str or "name resolution" in error_str:
            return FaultCategory.NETWORK_DNS
        if "ssl" in error_str or "certificate" in error_str:
            return FaultCategory.NETWORK_SSL
        if "connection" in error_str and "refused" in error_str:
            return FaultCategory.NETWORK_CONNECTION

        # 反爬层错误
        if "blocked" in error_str or "banned" in error_str:
            return FaultCategory.ANTI_IP_BLOCKED
        if "captcha" in error_str or "verify" in error_str:
            return FaultCategory.ANTI_CAPTCHA
        if "signature" in error_str or "sign" in error_str:
            return FaultCategory.ANTI_SIGNATURE
        if "fingerprint" in error_str:
            return FaultCategory.ANTI_FINGERPRINT
        if "rate limit" in error_str:
            return FaultCategory.ANTI_RATE_LIMIT

        # 数据层错误
        if "element not found" in error_str or "no such element" in error_str:
            return FaultCategory.DATA_ELEMENT_NOT_FOUND
        if "empty" in error_str and "data" in error_str:
            return FaultCategory.DATA_EMPTY

        # 浏览器层错误
        if "crash" in error_str or "browser" in error_str:
            return FaultCategory.BROWSER_CRASH

        # 默认未知
        logger.warning(f"[FAULT] 无法分类故障: {error_type} - {error_str[:100]}")
        return FaultCategory.UNKNOWN


# ============================================================================
# 自动恢复执行器
# ============================================================================

class AutoRecoveryExecutor:
    """
    自动恢复执行器

    支持依赖注入，可以连接到实际的系统组件：
    - ProxyManager: 代理管理器
    - config: AgentConfig 配置对象
    - browser_context: Playwright 浏览器上下文
    - rate_limiter: 速率限制器

    使用示例:
        from unified_agent.infra.proxy import ProxyManager
        from unified_agent.core.config import AgentConfig

        executor = AutoRecoveryExecutor(
            proxy_manager=ProxyManager(config),
            config=AgentConfig()
        )
        result = executor.execute(decision, context)
    """

    def __init__(
        self,
        max_attempts: int = 3,
        proxy_manager: Any = None,
        config: Any = None,
        browser_context: Any = None,
        rate_limiter: Any = None
    ):
        """
        初始化自动恢复执行器

        Args:
            max_attempts: 最大重试次数
            proxy_manager: 代理管理器实例 (ProxyManager)
            config: 配置对象 (AgentConfig)
            browser_context: 浏览器上下文 (Playwright BrowserContext)
            rate_limiter: 速率限制器实例
        """
        self.max_attempts = max_attempts
        self.execution_log: List[Dict] = []

        # 外部依赖
        self.proxy_manager = proxy_manager
        self.config = config
        self.browser_context = browser_context
        self.rate_limiter = rate_limiter

        # 内部状态
        self._current_rate_factor = 1.0  # 速率因子
        self._current_timeout_factor = 1.0  # 超时因子
        self._recovery_count = 0  # 恢复计数

    def set_proxy_manager(self, proxy_manager: Any):
        """设置代理管理器"""
        self.proxy_manager = proxy_manager

    def set_config(self, config: Any):
        """设置配置对象"""
        self.config = config

    def set_browser_context(self, browser_context: Any):
        """设置浏览器上下文"""
        self.browser_context = browser_context

    def set_rate_limiter(self, rate_limiter: Any):
        """设置速率限制器"""
        self.rate_limiter = rate_limiter

    def execute(
        self,
        decision: FaultDecision,
        context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        执行恢复动作

        Args:
            decision: 故障决策
            context: 上下文信息

        Returns:
            恢复结果
        """
        start_time = time.time()
        actions_taken = []
        errors = []

        logger.info(f"[RECOVERY] 开始执行恢复: {decision.fault_category.value}")
        logger.info(f"[RECOVERY] 计划动作: {[a.value for a in decision.recovery_actions]}")

        # 检查是否可自动恢复
        if not decision.auto_recoverable:
            logger.warning("[RECOVERY] 该故障不可自动恢复，需要人工介入")
            return RecoveryResult(
                success=False,
                actions_taken=[],
                outcome="需要人工介入",
                cost_time_ms=(time.time() - start_time) * 1000,
                errors=["故障不可自动恢复"]
            )

        # 依次执行恢复动作
        for action in decision.recovery_actions:
            try:
                success = self.apply_action(action, context)
                actions_taken.append(action)

                if success:
                    logger.info(f"[RECOVERY] 动作成功: {action.value}")
                    self._recovery_count += 1
                    # 记录执行日志
                    self.execution_log.append({
                        "timestamp": time.time(),
                        "fault_category": decision.fault_category.value,
                        "action": action.value,
                        "success": True
                    })
                    # 成功后停止
                    break
                else:
                    logger.warning(f"[RECOVERY] 动作失败: {action.value}")
                    errors.append(f"{action.value} 失败")

            except Exception as e:
                logger.error(f"[RECOVERY] 动作异常: {action.value} - {e}")
                errors.append(f"{action.value} 异常: {str(e)}")

        cost_time = (time.time() - start_time) * 1000
        success = len(errors) == 0 or (len(actions_taken) > 0 and len(errors) < len(actions_taken))

        result = RecoveryResult(
            success=success,
            actions_taken=actions_taken,
            outcome="成功恢复" if success else "恢复失败",
            cost_time_ms=cost_time,
            errors=errors
        )

        logger.info(f"[RECOVERY] 恢复结果: {result.outcome} (耗时: {cost_time:.1f}ms)")

        return result

    def apply_action(
        self,
        action: RecoveryAction,
        context: Dict[str, Any]
    ) -> bool:
        """
        应用单个恢复动作

        Args:
            action: 恢复动作
            context: 上下文信息

        Returns:
            是否成功
        """
        logger.info(f"[RECOVERY] 执行动作: {action.value}")

        # 动作路由
        action_map = {
            RecoveryAction.RETRY: self._action_retry,
            RecoveryAction.SWITCH_PROXY: self._action_switch_proxy,
            RecoveryAction.WAIT_COOLDOWN: self._action_wait_cooldown,
            RecoveryAction.REDUCE_RATE: self._action_reduce_rate,
            RecoveryAction.INCREASE_TIMEOUT: self._action_increase_timeout,
            RecoveryAction.RESTART_BROWSER: self._action_restart_browser,
            RecoveryAction.ESCALATE_TO_USER: self._action_escalate_to_user,
            RecoveryAction.CHANGE_USER_AGENT: self._action_change_user_agent,
            RecoveryAction.ROTATE_COOKIE: self._action_rotate_cookie,
            RecoveryAction.CLEAR_CACHE: self._action_clear_cache,
        }

        handler = action_map.get(action)
        if handler:
            return handler(context)
        else:
            logger.warning(f"[RECOVERY] 未实现的动作: {action.value}")
            return False

    def _action_retry(self, context: Dict) -> bool:
        """重试 - 简单延迟后重试"""
        delay = context.get("retry_delay", 3)
        logger.info(f"[RECOVERY] 等待 {delay} 秒后重试...")
        time.sleep(delay)
        return True

    def _action_switch_proxy(self, context: Dict) -> bool:
        """
        切换代理

        实现逻辑:
        1. 如果有 ProxyManager，调用其切换方法
        2. 如果有配置对象，更新代理配置
        3. 返回切换结果
        """
        logger.info("[RECOVERY] 正在切换代理...")

        # 方式1: 使用 ProxyManager
        if self.proxy_manager is not None:
            try:
                # 尝试调用 ProxyManager 的方法
                if hasattr(self.proxy_manager, 'rotate'):
                    new_proxy = self.proxy_manager.rotate()
                    logger.info(f"[RECOVERY] 代理已轮换: {new_proxy}")
                    return True
                elif hasattr(self.proxy_manager, 'get_next'):
                    new_proxy = self.proxy_manager.get_next()
                    logger.info(f"[RECOVERY] 代理已切换: {new_proxy}")
                    return True
                elif hasattr(self.proxy_manager, 'switch'):
                    success = self.proxy_manager.switch()
                    logger.info(f"[RECOVERY] 代理切换: {'成功' if success else '失败'}")
                    return success
            except Exception as e:
                logger.error(f"[RECOVERY] 代理切换异常: {e}")
                return False

        # 方式2: 使用配置对象
        if self.config is not None:
            try:
                # 如果配置有代理列表，切换到下一个
                if hasattr(self.config, 'proxy_list') and self.config.proxy_list:
                    current_idx = getattr(self.config, '_proxy_idx', 0)
                    next_idx = (current_idx + 1) % len(self.config.proxy_list)
                    self.config._proxy_idx = next_idx
                    new_proxy = self.config.proxy_list[next_idx]

                    if hasattr(self.config, 'proxy_url'):
                        self.config.proxy_url = new_proxy

                    logger.info(f"[RECOVERY] 代理已切换至: {new_proxy}")
                    return True
                elif hasattr(self.config, 'proxy_enabled'):
                    # 如果没有代理列表，尝试禁用代理
                    self.config.proxy_enabled = not self.config.proxy_enabled
                    logger.info(f"[RECOVERY] 代理状态切换为: {self.config.proxy_enabled}")
                    return True
            except Exception as e:
                logger.error(f"[RECOVERY] 配置更新异常: {e}")
                return False

        # 方式3: 通过context传入的回调
        switch_callback = context.get("switch_proxy_callback")
        if switch_callback and callable(switch_callback):
            try:
                result = switch_callback()
                logger.info(f"[RECOVERY] 代理切换回调执行: {'成功' if result else '失败'}")
                return bool(result)
            except Exception as e:
                logger.error(f"[RECOVERY] 代理切换回调异常: {e}")
                return False

        logger.warning("[RECOVERY] 无可用的代理切换方式")
        return False

    def _action_wait_cooldown(self, context: Dict) -> bool:
        """等待冷却"""
        cooldown = context.get("cooldown_seconds", 30)
        max_wait = context.get("max_cooldown", 60)
        actual_wait = min(cooldown, max_wait)

        logger.info(f"[RECOVERY] 等待冷却 {actual_wait} 秒...")
        time.sleep(actual_wait)
        return True

    def _action_reduce_rate(self, context: Dict) -> bool:
        """
        降低请求速率

        实现逻辑:
        1. 如果有速率限制器，调用其降速方法
        2. 如果有配置对象，降低 requests_per_second
        3. 记录当前降速因子
        """
        logger.info("[RECOVERY] 正在降低请求速率...")
        reduction_factor = context.get("rate_reduction_factor", 0.5)

        # 方式1: 使用速率限制器
        if self.rate_limiter is not None:
            try:
                if hasattr(self.rate_limiter, 'set_rate'):
                    current_rate = getattr(self.rate_limiter, 'rate', 1.0)
                    new_rate = max(0.1, current_rate * reduction_factor)
                    self.rate_limiter.set_rate(new_rate)
                    logger.info(f"[RECOVERY] 速率已降低: {current_rate} -> {new_rate}")
                    return True
                elif hasattr(self.rate_limiter, 'reduce'):
                    self.rate_limiter.reduce(reduction_factor)
                    logger.info(f"[RECOVERY] 速率已降低 {reduction_factor * 100}%")
                    return True
            except Exception as e:
                logger.error(f"[RECOVERY] 速率调整异常: {e}")

        # 方式2: 使用配置对象
        if self.config is not None:
            try:
                if hasattr(self.config, 'requests_per_second'):
                    old_rate = self.config.requests_per_second
                    new_rate = max(0.1, old_rate * reduction_factor)
                    self.config.requests_per_second = new_rate
                    self._current_rate_factor *= reduction_factor
                    logger.info(f"[RECOVERY] 配置速率已降低: {old_rate} -> {new_rate}")
                    return True
                elif hasattr(self.config, 'delay_between_requests'):
                    old_delay = self.config.delay_between_requests
                    new_delay = old_delay / reduction_factor  # 增加延迟
                    self.config.delay_between_requests = new_delay
                    logger.info(f"[RECOVERY] 请求延迟已增加: {old_delay} -> {new_delay}")
                    return True
            except Exception as e:
                logger.error(f"[RECOVERY] 配置更新异常: {e}")

        # 方式3: 记录降速因子供外部使用
        self._current_rate_factor *= reduction_factor
        context["rate_factor"] = self._current_rate_factor
        logger.info(f"[RECOVERY] 已记录降速因子: {self._current_rate_factor}")
        return True

    def _action_increase_timeout(self, context: Dict) -> bool:
        """
        增加超时时间

        实现逻辑:
        1. 如果有配置对象，增加 timeout 值
        2. 记录当前超时因子
        """
        logger.info("[RECOVERY] 正在增加超时时间...")
        increase_factor = context.get("timeout_increase_factor", 1.5)

        # 方式1: 使用配置对象
        if self.config is not None:
            try:
                if hasattr(self.config, 'timeout'):
                    old_timeout = self.config.timeout
                    new_timeout = min(old_timeout * increase_factor, 120)  # 最大120秒
                    self.config.timeout = new_timeout
                    self._current_timeout_factor *= increase_factor
                    logger.info(f"[RECOVERY] 超时时间已增加: {old_timeout} -> {new_timeout} 秒")
                    return True
                elif hasattr(self.config, 'request_timeout'):
                    old_timeout = self.config.request_timeout
                    new_timeout = min(old_timeout * increase_factor, 120)
                    self.config.request_timeout = new_timeout
                    logger.info(f"[RECOVERY] 请求超时已增加: {old_timeout} -> {new_timeout} 秒")
                    return True
            except Exception as e:
                logger.error(f"[RECOVERY] 配置更新异常: {e}")

        # 方式2: 记录超时因子供外部使用
        self._current_timeout_factor *= increase_factor
        context["timeout_factor"] = self._current_timeout_factor
        logger.info(f"[RECOVERY] 已记录超时因子: {self._current_timeout_factor}")
        return True

    def _action_restart_browser(self, context: Dict) -> bool:
        """
        重启浏览器

        实现逻辑:
        1. 如果有浏览器上下文，关闭并重新创建
        2. 清理浏览器缓存和Cookie
        """
        logger.info("[RECOVERY] 正在重启浏览器...")

        # 方式1: 使用 Playwright 浏览器上下文
        if self.browser_context is not None:
            try:
                # 获取浏览器引用
                browser = None
                if hasattr(self.browser_context, 'browser'):
                    browser = self.browser_context.browser

                # 关闭当前上下文
                if hasattr(self.browser_context, 'close'):
                    self.browser_context.close()
                    logger.info("[RECOVERY] 浏览器上下文已关闭")

                # 如果有浏览器引用，创建新上下文
                if browser is not None and hasattr(browser, 'new_context'):
                    self.browser_context = browser.new_context()
                    logger.info("[RECOVERY] 新的浏览器上下文已创建")
                    return True

            except Exception as e:
                logger.error(f"[RECOVERY] 浏览器重启异常: {e}")

        # 方式2: 通过context传入的回调
        restart_callback = context.get("restart_browser_callback")
        if restart_callback and callable(restart_callback):
            try:
                new_context = restart_callback()
                if new_context:
                    self.browser_context = new_context
                    logger.info("[RECOVERY] 浏览器已通过回调重启")
                    return True
            except Exception as e:
                logger.error(f"[RECOVERY] 浏览器重启回调异常: {e}")

        # 方式3: 使用 Playwright 同步API重新启动
        try:
            from playwright.sync_api import sync_playwright

            # 检查是否有浏览器类型配置
            browser_type = context.get("browser_type", "chromium")
            headless = context.get("headless", True)

            with sync_playwright() as p:
                browser_launcher = getattr(p, browser_type)
                browser = browser_launcher.launch(headless=headless)
                self.browser_context = browser.new_context()
                logger.info(f"[RECOVERY] 浏览器已重启 (type={browser_type}, headless={headless})")
                return True

        except ImportError:
            logger.warning("[RECOVERY] Playwright 未安装")
        except Exception as e:
            logger.error(f"[RECOVERY] Playwright 浏览器启动异常: {e}")

        logger.warning("[RECOVERY] 无可用的浏览器重启方式")
        return False

    def _action_escalate_to_user(self, context: Dict) -> bool:
        """升级到用户"""
        logger.warning("[RECOVERY] 需要用户介入")
        # 可以通过回调通知用户
        notify_callback = context.get("notify_user_callback")
        if notify_callback and callable(notify_callback):
            try:
                notify_callback(context.get("error_message", "需要人工处理"))
            except Exception as e:
                logger.error(f"[RECOVERY] 用户通知异常: {e}")
        return False

    def _action_change_user_agent(self, context: Dict) -> bool:
        """更换 User-Agent"""
        logger.info("[RECOVERY] 正在更换 User-Agent...")

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

        import random
        new_ua = random.choice(user_agents)

        if self.config is not None and hasattr(self.config, 'user_agent'):
            self.config.user_agent = new_ua
            logger.info(f"[RECOVERY] User-Agent 已更换: {new_ua[:50]}...")
            return True

        context["new_user_agent"] = new_ua
        logger.info(f"[RECOVERY] 新 User-Agent 已记录: {new_ua[:50]}...")
        return True

    def _action_rotate_cookie(self, context: Dict) -> bool:
        """轮换 Cookie"""
        logger.info("[RECOVERY] 正在轮换 Cookie...")

        # 通过回调获取新Cookie
        cookie_callback = context.get("get_cookie_callback")
        if cookie_callback and callable(cookie_callback):
            try:
                new_cookie = cookie_callback()
                if new_cookie:
                    context["new_cookie"] = new_cookie
                    logger.info("[RECOVERY] Cookie 已轮换")
                    return True
            except Exception as e:
                logger.error(f"[RECOVERY] Cookie 轮换异常: {e}")

        logger.warning("[RECOVERY] 无可用的 Cookie 轮换方式")
        return False

    def _action_clear_cache(self, context: Dict) -> bool:
        """清理缓存"""
        logger.info("[RECOVERY] 正在清理缓存...")

        if self.browser_context is not None:
            try:
                if hasattr(self.browser_context, 'clear_cookies'):
                    self.browser_context.clear_cookies()
                    logger.info("[RECOVERY] 浏览器 Cookie 已清理")
                    return True
            except Exception as e:
                logger.error(f"[RECOVERY] 缓存清理异常: {e}")

        return True  # 缓存清理通常不是关键操作

    def get_recovery_stats(self) -> Dict:
        """获取恢复统计"""
        return {
            "total_recoveries": self._recovery_count,
            "current_rate_factor": self._current_rate_factor,
            "current_timeout_factor": self._current_timeout_factor,
            "execution_log_count": len(self.execution_log)
        }

    def reset_factors(self):
        """重置速率和超时因子"""
        self._current_rate_factor = 1.0
        self._current_timeout_factor = 1.0
        logger.info("[RECOVERY] 速率和超时因子已重置")


# ============================================================================
# 使用示例
# ============================================================================

def example_usage():
    """使用示例"""
    print("=" * 80)
    print("故障决策树模块 - 使用示例")
    print("=" * 80)

    # 1. 创建决策树
    tree = FaultDecisionTree()

    # 2. 模拟各种故障
    test_cases = [
        (Exception("Connection timeout"), {"status_code": None}),
        (Exception("403 Forbidden"), {"status_code": 403}),
        (Exception("429 Too Many Requests"), {"status_code": 429}),
        (Exception("IP blocked by server"), {"status_code": 403}),
        (Exception("CAPTCHA required"), {"status_code": 200}),
        (Exception("Element not found"), {"status_code": 200}),
    ]

    executor = AutoRecoveryExecutor()

    for i, (error, context) in enumerate(test_cases, 1):
        print(f"\n测试案例 {i}: {error}")
        print("-" * 80)

        # 诊断
        decision = tree.diagnose(error, context)
        print(f"故障分类: {decision.fault_category.value}")
        print(f"严重程度: {decision.severity.value}")
        print(f"可自动恢复: {decision.auto_recoverable}")
        print(f"恢复动作: {[a.value for a in decision.recovery_actions]}")
        print(f"预估恢复时间: {decision.estimated_recovery_time}")
        print(f"决策理由: {decision.reasoning}")

        # 执行恢复 (仅演示可自动恢复的)
        if decision.auto_recoverable and i <= 2:  # 只演示前2个
            print("\n执行自动恢复:")
            result = executor.execute(decision, context)
            print(f"恢复结果: {result.outcome}")
            print(f"执行动作: {[a.value for a in result.actions_taken]}")
            if result.errors:
                print(f"错误信息: {result.errors}")


if __name__ == "__main__":
    example_usage()
