"""
恢复模块 - 故障决策树

负责故障分类和决策匹配。
"""

import re
import logging
from typing import Any, Dict, Optional

from .types import (
    FaultCategory,
    FaultSeverity,
    RecoveryAction,
    FaultDecision,
)

logger = logging.getLogger(__name__)


class FaultDecisionTree:
    """
    故障决策树

    根据故障类型匹配恢复决策。

    使用示例:
        tree = FaultDecisionTree()
        decision = tree.diagnose(error, context)
        print(decision.recovery_actions)
    """

    def __init__(self):
        """初始化决策树"""
        self.rules: Dict[FaultCategory, FaultDecision] = {}
        self._init_rules()
        logger.info(f"[DecisionTree] 初始化完成，规则数: {len(self.rules)}")

    def _init_rules(self):
        """初始化决策规则"""
        # 网络层规则
        self._add_rule(
            FaultCategory.NETWORK_TIMEOUT,
            severity=FaultSeverity.MEDIUM,
            actions=[RecoveryAction.INCREASE_TIMEOUT, RecoveryAction.RETRY, RecoveryAction.SWITCH_PROXY],
            priority=5,
            auto_recoverable=True,
            recovery_time="30-60s",
            reasoning="网络超时通常是暂时性问题，增加超时时间后重试"
        )

        self._add_rule(
            FaultCategory.NETWORK_DNS,
            severity=FaultSeverity.HIGH,
            actions=[RecoveryAction.CHANGE_DNS, RecoveryAction.USE_DIRECT_CONNECTION, RecoveryAction.ESCALATE_TO_USER],
            priority=8,
            auto_recoverable=False,
            recovery_time="5-10min",
            reasoning="DNS失败可能是域名错误，需要人工确认"
        )

        self._add_rule(
            FaultCategory.NETWORK_SSL,
            severity=FaultSeverity.MEDIUM,
            actions=[RecoveryAction.USE_DIRECT_CONNECTION, RecoveryAction.ESCALATE_TO_USER],
            priority=7,
            auto_recoverable=False,
            recovery_time="manual",
            reasoning="SSL证书错误需要人工判断是否信任"
        )

        # HTTP层规则
        self._add_rule(
            FaultCategory.HTTP_403,
            severity=FaultSeverity.HIGH,
            actions=[RecoveryAction.SWITCH_PROXY, RecoveryAction.CHANGE_USER_AGENT, RecoveryAction.ADD_REFERER, RecoveryAction.USE_STEALTH],
            priority=8,
            auto_recoverable=True,
            recovery_time="60-120s",
            reasoning="403通常是反爬检测，需要更换IP和指纹"
        )

        self._add_rule(
            FaultCategory.HTTP_429,
            severity=FaultSeverity.MEDIUM,
            actions=[RecoveryAction.WAIT_COOLDOWN, RecoveryAction.REDUCE_RATE, RecoveryAction.SWITCH_PROXY],
            priority=6,
            auto_recoverable=True,
            recovery_time="30-300s",
            reasoning="429是频率限制，需要降速和等待"
        )

        self._add_rule(
            FaultCategory.HTTP_404,
            severity=FaultSeverity.MEDIUM,
            actions=[RecoveryAction.USE_FALLBACK, RecoveryAction.ESCALATE_TO_USER],
            priority=5,
            auto_recoverable=False,
            recovery_time="manual",
            reasoning="404说明资源不存在，需要确认URL正确性"
        )

        self._add_rule(
            FaultCategory.HTTP_5XX,
            severity=FaultSeverity.LOW,
            actions=[RecoveryAction.WAIT_COOLDOWN, RecoveryAction.RETRY],
            priority=3,
            auto_recoverable=True,
            recovery_time="60-300s",
            reasoning="5xx是服务端问题，等待后重试"
        )

        # 反爬层规则
        self._add_rule(
            FaultCategory.ANTI_IP_BLOCKED,
            severity=FaultSeverity.CRITICAL,
            actions=[RecoveryAction.SWITCH_PROXY, RecoveryAction.REDUCE_RATE, RecoveryAction.USE_STEALTH],
            priority=10,
            auto_recoverable=True,
            recovery_time="immediate",
            reasoning="IP被封必须立即切换"
        )

        self._add_rule(
            FaultCategory.ANTI_CAPTCHA,
            severity=FaultSeverity.HIGH,
            actions=[RecoveryAction.SOLVE_CAPTCHA, RecoveryAction.SWITCH_PROXY, RecoveryAction.ESCALATE_TO_USER],
            priority=8,
            auto_recoverable=False,
            recovery_time="manual",
            reasoning="验证码需要人工或第三方服务处理"
        )

        self._add_rule(
            FaultCategory.ANTI_SIGNATURE,
            severity=FaultSeverity.HIGH,
            actions=[RecoveryAction.FIX_SIGNATURE, RecoveryAction.SWITCH_STRATEGY, RecoveryAction.ESCALATE_TO_USER],
            priority=9,
            auto_recoverable=False,
            recovery_time="manual",
            reasoning="签名错误需要重新分析算法"
        )

        self._add_rule(
            FaultCategory.ANTI_RATE_LIMIT,
            severity=FaultSeverity.MEDIUM,
            actions=[RecoveryAction.WAIT_COOLDOWN, RecoveryAction.REDUCE_RATE, RecoveryAction.SWITCH_PROXY],
            priority=6,
            auto_recoverable=True,
            recovery_time="30-300s",
            reasoning="频率限制需要降速"
        )

        # 数据层规则
        self._add_rule(
            FaultCategory.DATA_EMPTY,
            severity=FaultSeverity.MEDIUM,
            actions=[RecoveryAction.WAIT_PAGE_LOAD, RecoveryAction.UPDATE_SELECTOR, RecoveryAction.USE_BACKUP_SELECTOR],
            priority=6,
            auto_recoverable=True,
            recovery_time="10-30s",
            reasoning="数据为空可能是页面未加载完成"
        )

        self._add_rule(
            FaultCategory.DATA_ELEMENT_NOT_FOUND,
            severity=FaultSeverity.HIGH,
            actions=[RecoveryAction.UPDATE_SELECTOR, RecoveryAction.USE_BACKUP_SELECTOR, RecoveryAction.REPORT_FORMAT_CHANGE],
            priority=7,
            auto_recoverable=False,
            recovery_time="manual",
            reasoning="元素定位失败可能是页面改版"
        )

        # 浏览器层规则
        self._add_rule(
            FaultCategory.BROWSER_CRASH,
            severity=FaultSeverity.CRITICAL,
            actions=[RecoveryAction.RESTART_BROWSER, RecoveryAction.CLEAR_CACHE],
            priority=10,
            auto_recoverable=True,
            recovery_time="30-60s",
            reasoning="浏览器崩溃需要重启"
        )

        # 未知故障
        self._add_rule(
            FaultCategory.UNKNOWN,
            severity=FaultSeverity.MEDIUM,
            actions=[RecoveryAction.RETRY, RecoveryAction.ESCALATE_TO_USER],
            priority=5,
            auto_recoverable=False,
            recovery_time="manual",
            reasoning="未知故障需要人工分析"
        )

    def _add_rule(
        self,
        category: FaultCategory,
        severity: FaultSeverity,
        actions: list,
        priority: int,
        auto_recoverable: bool,
        recovery_time: str,
        reasoning: str
    ):
        """添加决策规则"""
        self.rules[category] = FaultDecision(
            fault_category=category,
            severity=severity,
            recovery_actions=actions,
            priority=priority,
            auto_recoverable=auto_recoverable,
            estimated_recovery_time=recovery_time,
            reasoning=reasoning
        )

    def diagnose(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> FaultDecision:
        """
        诊断故障并给出决策

        Args:
            error: 异常对象
            context: 上下文信息

        Returns:
            故障决策
        """
        context = context or {}

        # 分类故障
        fault_category = self.classify_fault(error, context)

        # 获取决策
        decision = self.rules.get(fault_category)

        if decision is None:
            logger.warning(f"[DecisionTree] 未知故障类型: {fault_category}")
            decision = self.rules[FaultCategory.UNKNOWN]

        logger.info(f"[DecisionTree] 诊断: {decision}")

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

        # HTTP状态码检查
        status_code = context.get("status_code")
        if status_code:
            category = self._classify_by_status(status_code)
            if category:
                return category

        # 模式匹配
        patterns = [
            (r"timeout|timed out", FaultCategory.NETWORK_TIMEOUT),
            (r"dns|name resolution", FaultCategory.NETWORK_DNS),
            (r"ssl|certificate", FaultCategory.NETWORK_SSL),
            (r"connection.*refused", FaultCategory.NETWORK_CONNECTION),
            (r"blocked|banned", FaultCategory.ANTI_IP_BLOCKED),
            (r"captcha|verify|验证码", FaultCategory.ANTI_CAPTCHA),
            (r"sign.*invalid|signature", FaultCategory.ANTI_SIGNATURE),
            (r"rate.?limit", FaultCategory.ANTI_RATE_LIMIT),
            (r"element not found", FaultCategory.DATA_ELEMENT_NOT_FOUND),
            (r"empty.*data|no.*data", FaultCategory.DATA_EMPTY),
            (r"browser.*crash|page.*crash", FaultCategory.BROWSER_CRASH),
        ]

        for pattern, category in patterns:
            if re.search(pattern, error_str, re.IGNORECASE):
                return category

        logger.warning(f"[DecisionTree] 无法分类: {error_str[:100]}")
        return FaultCategory.UNKNOWN

    def _classify_by_status(self, status_code: int) -> Optional[FaultCategory]:
        """根据HTTP状态码分类"""
        status_map = {
            400: FaultCategory.HTTP_400,
            401: FaultCategory.HTTP_401,
            403: FaultCategory.HTTP_403,
            404: FaultCategory.HTTP_404,
            429: FaultCategory.HTTP_429,
            500: FaultCategory.HTTP_500,
            502: FaultCategory.HTTP_502,
            503: FaultCategory.HTTP_503,
            504: FaultCategory.HTTP_504,
        }

        if status_code in status_map:
            return status_map[status_code]

        if 500 <= status_code < 600:
            return FaultCategory.HTTP_5XX

        return None

    def get_decision(self, category: FaultCategory) -> Optional[FaultDecision]:
        """获取指定分类的决策"""
        return self.rules.get(category)
