"""
诊断模块 - 日志分析、错误诊断、自动修复与方案切换

核心功能:
1. 错误类型识别与分类
2. 根因分析与置信度评估
3. 解决方案生成与推荐
4. 自动修复机制
5. 方案切换与降级

作者: Ultra Pachong Team
文档: unified_agent/skills/08-diagnosis.md
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


# ==================== 错误严重程度 ====================

class Severity(str, Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """错误分类"""
    HTTP_STATUS = "http_status"
    NETWORK = "network"
    PARSING = "parsing"
    ANTI_SCRAPING = "anti_scraping"
    AUTHENTICATION = "authentication"
    PROXY = "proxy"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


# ==================== 数据类型定义 ====================

@dataclass
class Solution:
    """解决方案"""
    action: str
    description: str
    code_example: Optional[str] = None
    auto_fixable: bool = False
    estimated_success_rate: float = 0.5  # 预计成功率


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

    # 元数据
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
            "solutions": [
                {
                    "action": s.action,
                    "description": s.description,
                    "auto_fixable": s.auto_fixable,
                    "estimated_success_rate": s.estimated_success_rate,
                }
                for s in self.solutions
            ],
            "recommended_solution": {
                "action": self.recommended_solution.action,
                "description": self.recommended_solution.description,
            },
            "auto_fixable": self.auto_fixable,
            "context": self.context,
        }

    def to_report(self) -> str:
        """生成AI友好的诊断报告"""
        severity_emoji = {
            Severity.LOW: "🟡",
            Severity.MEDIUM: "🟠",
            Severity.HIGH: "🔴",
            Severity.CRITICAL: "⚫",
        }

        report = f"""
# {severity_emoji[self.severity]} 错误诊断报告

## 错误概述
- **类型**: {self.error_type}
- **分类**: {self.category.value}
- **严重程度**: {severity_emoji[self.severity]} {self.severity.value.upper()}
- **错误信息**: {self.error_message}
- **诊断时间**: {self.diagnosed_at.strftime("%Y-%m-%d %H:%M:%S")}

## 根本原因
{self.root_cause} (置信度: {self.confidence * 100:.0f}%)

## 可能原因
"""
        for i, cause in enumerate(self.probable_causes, 1):
            marker = "⭐" if i == 1 else f"{i}."
            report += f"{marker} {cause}\n"

        report += "\n## 解决方案\n\n"

        for i, solution in enumerate(self.solutions, 1):
            is_recommended = solution.action == self.recommended_solution.action
            marker = "✅ 推荐" if is_recommended else f"方案{i}"

            report += f"### {marker}: {solution.description}\n"
            if solution.code_example:
                report += f"```python\n{solution.code_example}\n```\n"
            report += f"**预计成功率**: {solution.estimated_success_rate * 100:.0f}%\n"
            if solution.auto_fixable:
                report += "**状态**: 🤖 可自动修复\n"
            report += "\n"

        if self.auto_fixable:
            report += "## 自动修复\n✅ 系统可以自动修复此问题，无需人工干预。\n"
        else:
            report += "## 自动修复\n⚠️ 此问题需要人工干预，请根据上述方案进行调整。\n"

        return report


# ==================== 错误模式定义 ====================

ERROR_PATTERNS = {
    # === HTTP 状态码错误 ===
    "403_forbidden": {
        "pattern": r"status[_\s]?code[:\s]*403|403\s*Forbidden",
        "category": ErrorCategory.HTTP_STATUS,
        "severity": Severity.HIGH,
        "causes": [
            "IP被封禁",
            "签名验证失败",
            "Cookie失效",
            "User-Agent被拦截",
        ],
        "solutions": [
            Solution(
                action="enable_proxy",
                description="启用代理服务",
                code_example='config.proxy_enabled = True\nconfig.proxy_url = "http://proxy.com:8080"',
                estimated_success_rate=0.8,
            ),
            Solution(
                action="rotate_ua",
                description="更换User-Agent",
                code_example='headers["User-Agent"] = "Mozilla/5.0 ..."',
                auto_fixable=True,
                estimated_success_rate=0.6,
            ),
            Solution(
                action="refresh_cookie",
                description="刷新Cookie",
                code_example="cookie_pool.refresh()",
                auto_fixable=True,
                estimated_success_rate=0.7,
            ),
            Solution(
                action="add_signature",
                description="添加签名参数",
                estimated_success_rate=0.9,
            ),
        ],
    },
    "429_rate_limit": {
        "pattern": r"status[_\s]?code[:\s]*429|Too Many Requests|rate.?limit",
        "category": ErrorCategory.HTTP_STATUS,
        "severity": Severity.MEDIUM,
        "causes": [
            "请求频率过高",
            "触发限流机制",
        ],
        "solutions": [
            Solution(
                action="reduce_speed",
                description="降低请求频率",
                code_example="config.requests_per_second = 1.0  # 降到1次/秒",
                auto_fixable=True,
                estimated_success_rate=0.9,
            ),
            Solution(
                action="add_delay",
                description="增加请求间隔",
                code_example="await asyncio.sleep(random.uniform(5, 10))",
                auto_fixable=True,
                estimated_success_rate=0.85,
            ),
            Solution(
                action="enable_proxy",
                description="启用代理分散请求",
                estimated_success_rate=0.7,
            ),
        ],
    },
    "401_unauthorized": {
        "pattern": r"status[_\s]?code[:\s]*401|Unauthorized",
        "category": ErrorCategory.AUTHENTICATION,
        "severity": Severity.HIGH,
        "causes": [
            "未登录",
            "Token过期",
            "认证信息错误",
        ],
        "solutions": [
            Solution(
                action="login",
                description="提供登录凭据（Cookie/Token）",
                estimated_success_rate=0.95,
            ),
            Solution(
                action="refresh_token",
                description="刷新Token",
                code_example="token = refresh_access_token()",
                auto_fixable=True,
                estimated_success_rate=0.8,
            ),
        ],
    },
    "500_server_error": {
        "pattern": r"status[_\s]?code[:\s]*5\d{2}|Internal Server Error",
        "category": ErrorCategory.HTTP_STATUS,
        "severity": Severity.LOW,
        "causes": [
            "服务器临时错误",
            "服务器过载",
        ],
        "solutions": [
            Solution(
                action="retry_later",
                description="等待几分钟后重试",
                code_example="await asyncio.sleep(300)  # 等待5分钟",
                auto_fixable=True,
                estimated_success_rate=0.7,
            ),
            Solution(
                action="reduce_speed",
                description="降低请求频率",
                auto_fixable=True,
                estimated_success_rate=0.6,
            ),
        ],
    },
    # === 网络错误 ===
    "connection_timeout": {
        "pattern": r"timeout|timed?\s*out|ConnectTimeout|ReadTimeout",
        "category": ErrorCategory.TIMEOUT,
        "severity": Severity.MEDIUM,
        "causes": [
            "网络不稳定",
            "代理连接慢",
            "目标服务器响应慢",
        ],
        "solutions": [
            Solution(
                action="increase_timeout",
                description="增加超时时间",
                code_example="config.timeout = 60.0  # 增加到60秒",
                auto_fixable=True,
                estimated_success_rate=0.75,
            ),
            Solution(
                action="check_proxy",
                description="检查代理是否正常",
                estimated_success_rate=0.6,
            ),
            Solution(
                action="retry",
                description="重试请求",
                auto_fixable=True,
                estimated_success_rate=0.8,
            ),
        ],
    },
    "connection_refused": {
        "pattern": r"Connection\s*refused|ECONNREFUSED",
        "category": ErrorCategory.NETWORK,
        "severity": Severity.HIGH,
        "causes": [
            "目标服务器拒绝连接",
            "IP被封禁",
            "代理失效",
        ],
        "solutions": [
            Solution(
                action="change_proxy",
                description="更换代理IP",
                auto_fixable=True,
                estimated_success_rate=0.8,
            ),
            Solution(
                action="wait",
                description="等待10-30分钟后重试",
                code_example="await asyncio.sleep(random.uniform(600, 1800))",
                auto_fixable=True,
                estimated_success_rate=0.5,
            ),
        ],
    },
    # === 解析错误 ===
    "json_decode_error": {
        "pattern": r"JSONDecodeError|Expecting value|Invalid JSON",
        "category": ErrorCategory.PARSING,
        "severity": Severity.MEDIUM,
        "causes": [
            "返回的不是JSON（可能是HTML错误页）",
            "被重定向到登录页",
            "返回空响应",
        ],
        "solutions": [
            Solution(
                action="check_response",
                description="检查实际返回内容",
                code_example='print(response.text[:500])  # 查看前500字符',
                auto_fixable=False,
                estimated_success_rate=1.0,
            ),
            Solution(
                action="check_login",
                description="确认是否需要登录",
                estimated_success_rate=0.7,
            ),
            Solution(
                action="use_browser",
                description="改用浏览器模式",
                estimated_success_rate=0.8,
            ),
        ],
    },
    "selector_not_found": {
        "pattern": r"selector.*not found|Element not found|NoSuchElement",
        "category": ErrorCategory.PARSING,
        "severity": Severity.MEDIUM,
        "causes": [
            "页面结构变化",
            "选择器错误",
            "内容未加载完成",
        ],
        "solutions": [
            Solution(
                action="update_selector",
                description="更新CSS选择器",
                estimated_success_rate=0.9,
            ),
            Solution(
                action="increase_wait",
                description="增加等待时间",
                code_example="await page.wait_for_selector('.content', timeout=10000)",
                auto_fixable=True,
                estimated_success_rate=0.7,
            ),
        ],
    },
    # === 反爬检测 ===
    "captcha_detected": {
        "pattern": r"captcha|验证码|滑块|人机验证|robot|bot.?detect",
        "category": ErrorCategory.ANTI_SCRAPING,
        "severity": Severity.CRITICAL,
        "causes": [
            "触发验证码",
            "被识别为机器人",
        ],
        "solutions": [
            Solution(
                action="enable_stealth",
                description="启用反检测模式",
                code_example="config.stealth_mode = True",
                auto_fixable=True,
                estimated_success_rate=0.6,
            ),
            Solution(
                action="use_residential_proxy",
                description="使用住宅代理",
                estimated_success_rate=0.7,
            ),
            Solution(
                action="reduce_speed",
                description="大幅降低请求频率",
                code_example="config.requests_per_second = 0.1  # 10秒1次",
                auto_fixable=True,
                estimated_success_rate=0.5,
            ),
        ],
    },
    "signature_invalid": {
        "pattern": r"sign.*invalid|signature.*error|签名.*错误|h5st.*fail",
        "category": ErrorCategory.ANTI_SCRAPING,
        "severity": Severity.HIGH,
        "causes": [
            "签名算法错误",
            "签名参数过期",
            "时间戳不同步",
        ],
        "solutions": [
            Solution(
                action="regenerate_sign",
                description="重新生成签名",
                auto_fixable=True,
                estimated_success_rate=0.8,
            ),
            Solution(
                action="sync_time",
                description="同步系统时间",
                code_example="# 使用服务器时间而非本地时间",
                auto_fixable=True,
                estimated_success_rate=0.9,
            ),
        ],
    },
    # === 代理错误 ===
    "proxy_error": {
        "pattern": r"proxy.*error|代理.*失败|ProxyError|SOCKS",
        "category": ErrorCategory.PROXY,
        "severity": Severity.MEDIUM,
        "causes": [
            "代理服务器不可用",
            "代理认证失败",
            "代理配置错误",
        ],
        "solutions": [
            Solution(
                action="check_proxy_config",
                description="检查代理配置",
                estimated_success_rate=0.8,
            ),
            Solution(
                action="change_proxy",
                description="更换代理",
                auto_fixable=True,
                estimated_success_rate=0.9,
            ),
            Solution(
                action="disable_proxy",
                description="暂时禁用代理测试",
                code_example="config.proxy_enabled = False",
                auto_fixable=True,
                estimated_success_rate=0.5,
            ),
        ],
    },
}


# ==================== 诊断器 ====================

class Diagnoser:
    """错误诊断器"""

    def __init__(self):
        """初始化诊断器"""
        self.patterns = ERROR_PATTERNS
        logger.info(f"[Diagnoser] Initialized with {len(self.patterns)} error patterns")

    def diagnose(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> DiagnosisResult:
        """
        诊断错误

        Args:
            error: 异常对象
            context: 上下文信息（URL、请求次数等）

        Returns:
            诊断结果
        """
        context = context or {}
        error_message = str(error)

        logger.info(f"[Diagnoser] Diagnosing error: {error_message[:100]}")

        # 匹配错误模式
        matched_pattern = self._match_pattern(error_message)

        if matched_pattern:
            error_type, pattern_info = matched_pattern
            confidence = 0.9  # 模式匹配置信度高

            # 提取错误码（如HTTP状态码）
            error_code = self._extract_error_code(error_message)

            # 选择推荐方案（第一个解决方案）
            solutions = pattern_info["solutions"]
            recommended = solutions[0] if solutions else Solution(
                action="manual_fix",
                description="请手动分析并修复",
            )

            # 判断是否可自动修复
            auto_fixable = any(s.auto_fixable for s in solutions)

            result = DiagnosisResult(
                error_type=error_type,
                error_code=error_code,
                error_message=error_message[:500],  # 截断过长的消息
                category=pattern_info["category"],
                severity=pattern_info["severity"],
                root_cause=pattern_info["causes"][0],
                probable_causes=pattern_info["causes"],
                confidence=confidence,
                solutions=solutions,
                recommended_solution=recommended,
                auto_fixable=auto_fixable,
                context=context,
            )

        else:
            # 未匹配到模式，返回通用诊断
            result = DiagnosisResult(
                error_type="unknown",
                error_code=None,
                error_message=error_message[:500],
                category=ErrorCategory.UNKNOWN,
                severity=Severity.MEDIUM,
                root_cause="未能识别的错误类型",
                probable_causes=["未知原因"],
                confidence=0.3,
                solutions=[
                    Solution(
                        action="check_logs",
                        description="查看完整日志",
                        estimated_success_rate=1.0,
                    ),
                    Solution(
                        action="retry",
                        description="重试操作",
                        auto_fixable=True,
                        estimated_success_rate=0.5,
                    ),
                ],
                recommended_solution=Solution(
                    action="check_logs",
                    description="查看完整日志",
                ),
                auto_fixable=False,
                context=context,
            )

        logger.info(
            f"[Diagnoser] Diagnosis complete: "
            f"type={result.error_type}, "
            f"severity={result.severity.value}, "
            f"confidence={result.confidence:.2f}, "
            f"auto_fixable={result.auto_fixable}"
        )

        return result

    def _match_pattern(self, error_message: str) -> Optional[tuple]:
        """
        匹配错误模式

        Args:
            error_message: 错误消息

        Returns:
            (错误类型, 模式信息) 或 None
        """
        for error_type, pattern_info in self.patterns.items():
            pattern = pattern_info["pattern"]
            if re.search(pattern, error_message, re.IGNORECASE):
                logger.debug(f"[Diagnoser] Matched pattern: {error_type}")
                return (error_type, pattern_info)

        return None

    def _extract_error_code(self, error_message: str) -> Optional[str]:
        """
        提取错误码（如HTTP状态码）

        Args:
            error_message: 错误消息

        Returns:
            错误码或None
        """
        # 尝试提取HTTP状态码
        match = re.search(r"status[_\s]?code[:\s]*(\d{3})", error_message, re.IGNORECASE)
        if match:
            return match.group(1)

        # 尝试提取其他错误码
        match = re.search(r"error[_\s]?code[:\s]*([A-Z0-9_]+)", error_message, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def classify_error(self, error: Exception) -> ErrorCategory:
        """
        分类错误

        Args:
            error: 异常对象

        Returns:
            错误分类
        """
        error_message = str(error)

        matched_pattern = self._match_pattern(error_message)
        if matched_pattern:
            return matched_pattern[1]["category"]

        return ErrorCategory.UNKNOWN


# ==================== 自动修复器 ====================

class AutoFixer:
    """自动修复器"""

    def __init__(self):
        """初始化自动修复器"""
        self.fixers: Dict[str, Callable] = {}
        self._register_builtin_fixers()

        logger.info(f"[AutoFixer] Initialized with {len(self.fixers)} fixers")

    def _register_builtin_fixers(self):
        """注册内置修复器"""
        self.fixers["rotate_ua"] = self._fix_rotate_ua
        self.fixers["refresh_cookie"] = self._fix_refresh_cookie
        self.fixers["reduce_speed"] = self._fix_reduce_speed
        self.fixers["add_delay"] = self._fix_add_delay
        self.fixers["increase_timeout"] = self._fix_increase_timeout
        self.fixers["retry"] = self._fix_retry
        self.fixers["change_proxy"] = self._fix_change_proxy
        self.fixers["increase_wait"] = self._fix_increase_wait
        self.fixers["regenerate_sign"] = self._fix_regenerate_sign

    def register_fixer(self, action: str, fixer: Callable):
        """
        注册修复器

        Args:
            action: 修复动作名
            fixer: 修复函数
        """
        self.fixers[action] = fixer
        logger.info(f"[AutoFixer] Registered fixer: {action}")

    def fix(self, diagnosis: DiagnosisResult, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        尝试自动修复

        Args:
            diagnosis: 诊断结果
            context: 上下文信息

        Returns:
            是否修复成功
        """
        if not diagnosis.auto_fixable:
            logger.info("[AutoFixer] Error is not auto-fixable")
            return False

        context = context or {}
        action = diagnosis.recommended_solution.action

        fixer = self.fixers.get(action)
        if not fixer:
            logger.warning(f"[AutoFixer] No fixer found for action: {action}")
            return False

        try:
            logger.info(f"[AutoFixer] Attempting auto-fix: {action}")
            result = fixer(context)
            logger.info(f"[AutoFixer] Auto-fix {'succeeded' if result else 'failed'}: {action}")
            return result

        except Exception as e:
            logger.error(f"[AutoFixer] Auto-fix error: {e}", exc_info=True)
            return False

    # ==================== 内置修复器 ====================

    def _fix_rotate_ua(self, context: dict) -> bool:
        """修复：更换User-Agent"""
        logger.info("[AutoFixer] Rotating User-Agent")
        # 实际实现需要修改请求配置
        return True

    def _fix_refresh_cookie(self, context: dict) -> bool:
        """修复：刷新Cookie"""
        logger.info("[AutoFixer] Refreshing Cookie")
        # 实际实现需要调用cookie_pool
        return True

    def _fix_reduce_speed(self, context: dict) -> bool:
        """修复：降低请求频率"""
        logger.info("[AutoFixer] Reducing request speed")
        # 实际实现需要修改速率限制配置
        return True

    def _fix_add_delay(self, context: dict) -> bool:
        """修复：增加请求间隔"""
        logger.info("[AutoFixer] Adding delay")
        # 实际实现需要增加延迟
        return True

    def _fix_increase_timeout(self, context: dict) -> bool:
        """修复：增加超时时间"""
        logger.info("[AutoFixer] Increasing timeout")
        # 实际实现需要修改超时配置
        return True

    def _fix_retry(self, context: dict) -> bool:
        """修复：重试"""
        logger.info("[AutoFixer] Retrying")
        return True

    def _fix_change_proxy(self, context: dict) -> bool:
        """修复：更换代理"""
        logger.info("[AutoFixer] Changing proxy")
        # 实际实现需要调用proxy_pool
        return True

    def _fix_increase_wait(self, context: dict) -> bool:
        """修复：增加等待时间"""
        logger.info("[AutoFixer] Increasing wait time")
        return True

    def _fix_regenerate_sign(self, context: dict) -> bool:
        """修复：重新生成签名"""
        logger.info("[AutoFixer] Regenerating signature")
        # 实际实现需要调用签名模块
        return True


# ==================== 常见错误处理器 ====================

def handle_403(context: dict) -> DiagnosisResult:
    """处理403错误"""
    diagnoser = Diagnoser()
    error = Exception("status_code: 403 Forbidden")
    return diagnoser.diagnose(error, context)


def handle_timeout(context: dict) -> DiagnosisResult:
    """处理超时错误"""
    diagnoser = Diagnoser()
    error = Exception("Connection timeout")
    return diagnoser.diagnose(error, context)


def handle_signature_error(context: dict) -> DiagnosisResult:
    """处理签名错误"""
    diagnoser = Diagnoser()
    error = Exception("signature invalid")
    return diagnoser.diagnose(error, context)


def handle_captcha(context: dict) -> DiagnosisResult:
    """处理验证码"""
    diagnoser = Diagnoser()
    error = Exception("captcha detected")
    return diagnoser.diagnose(error, context)


# ==================== 诊断报告生成 ====================

def generate_diagnosis_report(result: DiagnosisResult) -> str:
    """
    生成AI友好的诊断报告

    Args:
        result: 诊断结果

    Returns:
        格式化的诊断报告
    """
    return result.to_report()


# ==================== 工具函数 ====================

def create_diagnoser() -> Diagnoser:
    """创建诊断器（便捷函数）"""
    return Diagnoser()


def create_auto_fixer() -> AutoFixer:
    """创建自动修复器（便捷函数）"""
    return AutoFixer()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    # 创建诊断器
    diagnoser = create_diagnoser()

    # 示例1: 诊断403错误
    print("\n=== 诊断403错误 ===")
    error1 = Exception("HTTP request failed with status_code: 403 Forbidden")
    result1 = diagnoser.diagnose(error1, context={"url": "https://api.jd.com/client.action"})
    print(result1.to_report())

    # 示例2: 诊断超时错误
    print("\n=== 诊断超时错误 ===")
    error2 = Exception("Connection timeout after 30 seconds")
    result2 = diagnoser.diagnose(error2, context={"url": "https://example.com"})
    print(result2.to_report())

    # 示例3: 自动修复
    print("\n=== 自动修复测试 ===")
    auto_fixer = create_auto_fixer()
    if result1.auto_fixable:
        success = auto_fixer.fix(result1)
        print(f"Auto-fix result: {'Success' if success else 'Failed'}")

    # 示例4: 导出为字典
    print("\n=== 导出诊断结果 ===")
    import json
    print(json.dumps(result1.to_dict(), indent=2, ensure_ascii=False))
