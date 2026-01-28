"""
恢复模块 - 类型定义

定义故障恢复相关的枚举和数据类。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


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
    CRITICAL = "critical"  # 致命 - 无法继续


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


@dataclass
class FaultDecision:
    """故障决策"""
    fault_category: FaultCategory
    severity: FaultSeverity
    recovery_actions: List[RecoveryAction]
    priority: int  # 执行优先级 1-10
    auto_recoverable: bool
    estimated_recovery_time: str
    fallback_plan: Optional[str] = None
    reasoning: str = ""

    def __str__(self) -> str:
        return (
            f"[{self.fault_category.value}] {self.severity.value} | "
            f"可自动恢复: {self.auto_recoverable} | "
            f"动作: {[a.value for a in self.recovery_actions]}"
        )


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    actions_taken: List[RecoveryAction]
    outcome: str
    cost_time_ms: float
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "actions_taken": [a.value for a in self.actions_taken],
            "outcome": self.outcome,
            "cost_time_ms": self.cost_time_ms,
            "errors": self.errors,
        }
