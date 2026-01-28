"""
诊断模块 - 错误分类器

负责根据错误信息进行分类。
"""

import re
import logging
from typing import Any, Dict, Optional, Tuple

from .types import ErrorCategory, Severity

logger = logging.getLogger(__name__)


class ErrorClassifier:
    """错误分类器"""

    # HTTP状态码映射
    HTTP_STATUS_MAP = {
        400: ("bad_request", Severity.MEDIUM),
        401: ("unauthorized", Severity.HIGH),
        403: ("forbidden", Severity.HIGH),
        404: ("not_found", Severity.MEDIUM),
        429: ("rate_limited", Severity.HIGH),
        500: ("server_error", Severity.MEDIUM),
        502: ("bad_gateway", Severity.MEDIUM),
        503: ("service_unavailable", Severity.MEDIUM),
        504: ("gateway_timeout", Severity.MEDIUM),
    }

    # 错误模式映射
    ERROR_PATTERNS = [
        # 网络错误
        (r"timeout|timed out", ErrorCategory.TIMEOUT, Severity.MEDIUM),
        (r"connection refused|connection reset", ErrorCategory.NETWORK, Severity.HIGH),
        (r"dns|name resolution", ErrorCategory.NETWORK, Severity.HIGH),
        (r"ssl|certificate", ErrorCategory.NETWORK, Severity.MEDIUM),

        # 代理错误
        (r"proxy.*error|proxy.*failed", ErrorCategory.PROXY, Severity.MEDIUM),
        (r"proxy.*timeout", ErrorCategory.PROXY, Severity.MEDIUM),

        # 反爬错误
        (r"blocked|banned|forbidden", ErrorCategory.ANTI_SCRAPING, Severity.HIGH),
        (r"captcha|verify|验证码", ErrorCategory.CAPTCHA, Severity.HIGH),
        (r"rate.?limit|too many requests", ErrorCategory.ANTI_SCRAPING, Severity.HIGH),

        # 签名错误
        (r"sign.*invalid|signature.*error|签名.*错误", ErrorCategory.SIGNATURE, Severity.HIGH),

        # 认证错误
        (r"auth.*failed|login.*required|unauthorized", ErrorCategory.AUTHENTICATION, Severity.HIGH),
        (r"token.*expired|session.*invalid", ErrorCategory.AUTHENTICATION, Severity.HIGH),

        # 解析错误
        (r"parse.*error|json.*decode|xml.*error", ErrorCategory.PARSING, Severity.MEDIUM),
        (r"element not found|selector.*failed", ErrorCategory.PARSING, Severity.MEDIUM),

        # 数据错误
        (r"empty.*data|no.*data|数据为空", ErrorCategory.DATA, Severity.MEDIUM),
        (r"invalid.*format|format.*error", ErrorCategory.DATA, Severity.MEDIUM),

        # 浏览器错误
        (r"browser.*crash|page.*crash", ErrorCategory.BROWSER, Severity.CRITICAL),
        (r"memory.*overflow|out of memory", ErrorCategory.BROWSER, Severity.CRITICAL),
    ]

    def classify(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ErrorCategory, Severity, str]:
        """
        分类错误

        Args:
            error: 异常对象
            context: 上下文信息

        Returns:
            (分类, 严重程度, 错误类型标识)
        """
        context = context or {}
        error_str = str(error).lower()
        error_type = type(error).__name__

        # 1. 检查HTTP状态码
        status_code = context.get("status_code")
        if status_code and status_code in self.HTTP_STATUS_MAP:
            error_name, severity = self.HTTP_STATUS_MAP[status_code]
            return ErrorCategory.HTTP_STATUS, severity, f"http_{status_code}"

        # 2. 检查5xx状态码
        if status_code and 500 <= status_code < 600:
            return ErrorCategory.HTTP_STATUS, Severity.MEDIUM, "http_5xx"

        # 3. 检查4xx状态码
        if status_code and 400 <= status_code < 500:
            return ErrorCategory.HTTP_STATUS, Severity.MEDIUM, f"http_{status_code}"

        # 4. 模式匹配
        for pattern, category, severity in self.ERROR_PATTERNS:
            if re.search(pattern, error_str, re.IGNORECASE):
                # 生成错误类型标识
                error_id = re.sub(r"[^a-z0-9]", "_", pattern.split("|")[0])
                return category, severity, error_id

        # 5. 未知错误
        logger.warning(f"[Classifier] Unknown error: {error_type} - {error_str[:100]}")
        return ErrorCategory.UNKNOWN, Severity.MEDIUM, "unknown"

    def get_severity_from_status(self, status_code: int) -> Severity:
        """根据HTTP状态码获取严重程度"""
        if status_code < 400:
            return Severity.LOW
        elif status_code in (401, 403, 429):
            return Severity.HIGH
        elif status_code >= 500:
            return Severity.MEDIUM
        else:
            return Severity.MEDIUM
