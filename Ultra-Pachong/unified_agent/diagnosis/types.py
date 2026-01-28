"""
诊断模块 - 类型定义

定义诊断相关的枚举和数据类。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    """错误严重程度"""
    LOW = "low"          # 低 - 不影响主流程
    MEDIUM = "medium"    # 中 - 部分功能受影响
    HIGH = "high"        # 高 - 严重影响任务
    CRITICAL = "critical"  # 致命 - 任务无法继续


class ErrorCategory(str, Enum):
    """错误分类"""
    HTTP_STATUS = "http_status"      # HTTP状态码错误
    NETWORK = "network"              # 网络错误
    PARSING = "parsing"              # 解析错误
    ANTI_SCRAPING = "anti_scraping"  # 反爬错误
    AUTHENTICATION = "authentication"  # 认证错误
    PROXY = "proxy"                  # 代理错误
    TIMEOUT = "timeout"              # 超时错误
    SIGNATURE = "signature"          # 签名错误
    CAPTCHA = "captcha"              # 验证码错误
    DATA = "data"                    # 数据错误
    BROWSER = "browser"              # 浏览器错误
    UNKNOWN = "unknown"              # 未知错误


@dataclass
class Solution:
    """解决方案"""
    action: str                      # 动作标识
    description: str                 # 描述
    code_example: Optional[str] = None  # 代码示例
    auto_fixable: bool = False       # 是否可自动修复
    estimated_success_rate: float = 0.5  # 预计成功率
    priority: int = 5                # 优先级 1-10

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "description": self.description,
            "auto_fixable": self.auto_fixable,
            "estimated_success_rate": self.estimated_success_rate,
            "priority": self.priority,
        }


@dataclass
class DiagnosisResult:
    """诊断结果"""
    # 错误信息
    error_type: str
    error_code: Optional[str]
    error_message: str
    category: ErrorCategory
    severity: Severity

    # 分析结果
    root_cause: str
    probable_causes: List[str]
    confidence: float  # 0-1

    # 解决方案
    solutions: List[Solution]
    recommended_solution: Solution
    auto_fixable: bool

    # 上下文
    context: Dict[str, Any] = field(default_factory=dict)
    diagnosed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "error_type": self.error_type,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "root_cause": self.root_cause,
            "probable_causes": self.probable_causes,
            "confidence": self.confidence,
            "solutions": [s.to_dict() for s in self.solutions],
            "recommended_solution": self.recommended_solution.to_dict(),
            "auto_fixable": self.auto_fixable,
            "diagnosed_at": self.diagnosed_at.isoformat(),
        }

    def to_report(self) -> str:
        """生成AI友好的诊断报告"""
        lines = [
            "=" * 60,
            f"诊断报告 | {self.diagnosed_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            f"错误类型: {self.error_type}",
            f"错误码: {self.error_code or 'N/A'}",
            f"分类: {self.category.value}",
            f"严重程度: {self.severity.value}",
            "",
            f"根因: {self.root_cause}",
            f"置信度: {self.confidence:.0%}",
            "",
            "可能原因:",
        ]
        for i, cause in enumerate(self.probable_causes, 1):
            lines.append(f"  {i}. {cause}")

        lines.extend([
            "",
            f"推荐方案: {self.recommended_solution.action}",
            f"  描述: {self.recommended_solution.description}",
            f"  可自动修复: {'是' if self.auto_fixable else '否'}",
            "",
            "=" * 60,
        ])

        return "\n".join(lines)
