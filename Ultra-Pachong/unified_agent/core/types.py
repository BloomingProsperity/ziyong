"""基础类型定义 - 全局共享的枚举和类型"""
from enum import Enum
from typing import TypedDict, Optional, Any


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """任务类型 (来自 18-brain-controller)"""
    EXPLICIT = "explicit"      # 明确任务: 有具体URL和目标
    FUZZY = "fuzzy"            # 模糊任务: 需要探索
    CONSULT = "consult"        # 咨询任务: 问问题
    HELP = "help"              # 求助任务: 遇到困难


class Difficulty(str, Enum):
    """难度等级"""
    EASY = "easy"              # 静态页面、公开API
    MEDIUM = "medium"          # Cookie、简单签名
    HARD = "hard"              # 复杂签名、验证码
    EXTREME = "extreme"        # 京东h5st、淘宝mtop


class ErrorCode(str, Enum):
    """错误码 (来自 19-fault-decision-tree)"""
    # 网络层
    TIMEOUT = "TIMEOUT"
    DNS_FAILED = "DNS_FAILED"
    SSL_ERROR = "SSL_ERROR"
    # HTTP层
    HTTP_403 = "HTTP_403"
    HTTP_404 = "HTTP_404"
    HTTP_429 = "HTTP_429"
    HTTP_5XX = "HTTP_5XX"
    # 反爬层
    CAPTCHA = "CAPTCHA"
    IP_BANNED = "IP_BANNED"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    # 数据层
    SELECTOR_FAILED = "SELECTOR_FAILED"
    EMPTY_DATA = "EMPTY_DATA"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"


class ToolResultStatus(str, Enum):
    """MCP工具返回状态"""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
