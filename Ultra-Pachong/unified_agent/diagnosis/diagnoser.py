"""
诊断模块 - 主诊断器

组合分类器和分析器，提供完整的诊断功能。
"""

import logging
from typing import Any, Dict, Optional

from .types import DiagnosisResult, ErrorCategory, Severity, Solution
from .classifier import ErrorClassifier
from .analyzer import ErrorAnalyzer

logger = logging.getLogger(__name__)


class Diagnoser:
    """
    主诊断器

    使用示例:
        diagnoser = Diagnoser()
        result = diagnoser.diagnose(error, context={"status_code": 403})
        print(result.to_report())
    """

    def __init__(self):
        """初始化诊断器"""
        self.classifier = ErrorClassifier()
        self.analyzer = ErrorAnalyzer()
        self.diagnosis_count = 0

        logger.info("[Diagnoser] 初始化完成")

    def diagnose(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> DiagnosisResult:
        """
        诊断错误

        Args:
            error: 异常对象
            context: 上下文信息 (可包含 status_code, url 等)

        Returns:
            诊断结果
        """
        context = context or {}
        error_str = str(error)
        error_type = type(error).__name__

        logger.info(f"[Diagnoser] 开始诊断: {error_type}")

        # 1. 分类错误
        category, severity, error_id = self.classifier.classify(error, context)

        logger.debug(f"[Diagnoser] 分类: {category.value}, 严重程度: {severity.value}")

        # 2. 分析错误
        analysis = self.analyzer.analyze(category, error, context)

        # 3. 构建诊断结果
        result = DiagnosisResult(
            error_type=error_id,
            error_code=str(context.get("status_code")) if context.get("status_code") else None,
            error_message=error_str,
            category=category,
            severity=severity,
            root_cause=analysis["root_cause"],
            probable_causes=analysis["probable_causes"],
            confidence=analysis["confidence"],
            solutions=analysis["solutions"],
            recommended_solution=analysis["recommended_solution"],
            auto_fixable=analysis["auto_fixable"],
            context=context,
        )

        self.diagnosis_count += 1
        logger.info(f"[Diagnoser] 诊断完成: {result.error_type} -> {result.recommended_solution.action}")

        return result

    def quick_diagnose(
        self,
        error_message: str,
        status_code: Optional[int] = None
    ) -> DiagnosisResult:
        """
        快速诊断 (简化接口)

        Args:
            error_message: 错误信息字符串
            status_code: HTTP状态码 (可选)

        Returns:
            诊断结果
        """
        error = Exception(error_message)
        context = {}
        if status_code:
            context["status_code"] = status_code

        return self.diagnose(error, context)

    def diagnose_http_error(
        self,
        status_code: int,
        response_body: Optional[str] = None,
        url: Optional[str] = None
    ) -> DiagnosisResult:
        """
        诊断HTTP错误

        Args:
            status_code: HTTP状态码
            response_body: 响应体 (可选)
            url: 请求URL (可选)

        Returns:
            诊断结果
        """
        error_message = f"HTTP {status_code}"
        if response_body:
            error_message += f": {response_body[:200]}"

        error = Exception(error_message)
        context = {
            "status_code": status_code,
            "response_body": response_body,
            "url": url,
        }

        return self.diagnose(error, context)

    def get_stats(self) -> Dict[str, Any]:
        """获取诊断统计"""
        return {
            "diagnosis_count": self.diagnosis_count,
        }


# ==================== 便捷函数 ====================

def diagnose_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> DiagnosisResult:
    """
    便捷函数：诊断错误

    Args:
        error: 异常对象
        context: 上下文信息

    Returns:
        诊断结果
    """
    diagnoser = Diagnoser()
    return diagnoser.diagnose(error, context)


def diagnose_http(status_code: int, url: Optional[str] = None) -> DiagnosisResult:
    """
    便捷函数：诊断HTTP错误

    Args:
        status_code: HTTP状态码
        url: 请求URL

    Returns:
        诊断结果
    """
    diagnoser = Diagnoser()
    return diagnoser.diagnose_http_error(status_code, url=url)
