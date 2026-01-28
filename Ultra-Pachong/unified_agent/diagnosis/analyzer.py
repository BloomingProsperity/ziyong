"""
诊断模块 - 错误分析器

负责分析错误原因并生成解决方案。
"""

import logging
from typing import Any, Dict, List, Optional

from .types import ErrorCategory, Severity, Solution

logger = logging.getLogger(__name__)


class ErrorAnalyzer:
    """错误分析器"""

    # 解决方案库
    SOLUTION_DATABASE: Dict[ErrorCategory, List[Solution]] = {
        ErrorCategory.HTTP_STATUS: [
            Solution(
                action="retry",
                description="等待后重试请求",
                auto_fixable=True,
                estimated_success_rate=0.6,
                priority=3,
            ),
            Solution(
                action="change_proxy",
                description="切换代理IP",
                auto_fixable=True,
                estimated_success_rate=0.7,
                priority=5,
            ),
            Solution(
                action="rotate_ua",
                description="更换User-Agent",
                auto_fixable=True,
                estimated_success_rate=0.5,
                priority=4,
            ),
        ],
        ErrorCategory.TIMEOUT: [
            Solution(
                action="increase_timeout",
                description="增加超时时间",
                auto_fixable=True,
                estimated_success_rate=0.7,
                priority=5,
            ),
            Solution(
                action="retry",
                description="重试请求",
                auto_fixable=True,
                estimated_success_rate=0.5,
                priority=3,
            ),
            Solution(
                action="change_proxy",
                description="切换代理",
                auto_fixable=True,
                estimated_success_rate=0.6,
                priority=4,
            ),
        ],
        ErrorCategory.ANTI_SCRAPING: [
            Solution(
                action="change_proxy",
                description="切换代理IP绕过封禁",
                auto_fixable=True,
                estimated_success_rate=0.8,
                priority=8,
            ),
            Solution(
                action="reduce_speed",
                description="降低请求频率",
                auto_fixable=True,
                estimated_success_rate=0.6,
                priority=6,
            ),
            Solution(
                action="rotate_ua",
                description="更换User-Agent和指纹",
                auto_fixable=True,
                estimated_success_rate=0.5,
                priority=5,
            ),
            Solution(
                action="add_delay",
                description="增加随机延迟",
                auto_fixable=True,
                estimated_success_rate=0.5,
                priority=4,
            ),
        ],
        ErrorCategory.CAPTCHA: [
            Solution(
                action="solve_captcha",
                description="调用验证码识别服务",
                auto_fixable=False,
                estimated_success_rate=0.8,
                priority=8,
            ),
            Solution(
                action="change_proxy",
                description="切换IP尝试绕过验证码",
                auto_fixable=True,
                estimated_success_rate=0.4,
                priority=5,
            ),
        ],
        ErrorCategory.SIGNATURE: [
            Solution(
                action="regenerate_sign",
                description="重新生成签名",
                auto_fixable=True,
                estimated_success_rate=0.7,
                priority=7,
            ),
            Solution(
                action="update_algorithm",
                description="更新签名算法",
                auto_fixable=False,
                estimated_success_rate=0.9,
                priority=9,
            ),
        ],
        ErrorCategory.AUTHENTICATION: [
            Solution(
                action="refresh_cookie",
                description="刷新Cookie/登录态",
                auto_fixable=True,
                estimated_success_rate=0.8,
                priority=8,
            ),
            Solution(
                action="relogin",
                description="重新登录",
                auto_fixable=False,
                estimated_success_rate=0.9,
                priority=9,
            ),
        ],
        ErrorCategory.PROXY: [
            Solution(
                action="change_proxy",
                description="切换到可用代理",
                auto_fixable=True,
                estimated_success_rate=0.9,
                priority=9,
            ),
            Solution(
                action="use_direct",
                description="尝试直连",
                auto_fixable=True,
                estimated_success_rate=0.5,
                priority=4,
            ),
        ],
        ErrorCategory.PARSING: [
            Solution(
                action="update_selector",
                description="更新选择器",
                auto_fixable=False,
                estimated_success_rate=0.8,
                priority=7,
            ),
            Solution(
                action="use_backup_selector",
                description="使用备用选择器",
                auto_fixable=True,
                estimated_success_rate=0.6,
                priority=5,
            ),
            Solution(
                action="increase_wait",
                description="增加页面加载等待时间",
                auto_fixable=True,
                estimated_success_rate=0.5,
                priority=4,
            ),
        ],
        ErrorCategory.BROWSER: [
            Solution(
                action="restart_browser",
                description="重启浏览器",
                auto_fixable=True,
                estimated_success_rate=0.9,
                priority=9,
            ),
            Solution(
                action="clear_cache",
                description="清理浏览器缓存",
                auto_fixable=True,
                estimated_success_rate=0.6,
                priority=5,
            ),
        ],
        ErrorCategory.DATA: [
            Solution(
                action="retry",
                description="重试获取数据",
                auto_fixable=True,
                estimated_success_rate=0.5,
                priority=4,
            ),
            Solution(
                action="report_empty",
                description="上报数据异常",
                auto_fixable=False,
                estimated_success_rate=1.0,
                priority=3,
            ),
        ],
    }

    # 根因分析模板
    ROOT_CAUSE_TEMPLATES = {
        ErrorCategory.HTTP_STATUS: "服务器返回 {status_code} 状态码，{reason}",
        ErrorCategory.TIMEOUT: "请求超时，可能是网络延迟或服务器响应慢",
        ErrorCategory.ANTI_SCRAPING: "触发了反爬机制，IP或指纹可能被标记",
        ErrorCategory.CAPTCHA: "出现验证码，需要人机验证",
        ErrorCategory.SIGNATURE: "请求签名无效，算法可能已更新",
        ErrorCategory.AUTHENTICATION: "认证失败，登录态可能已过期",
        ErrorCategory.PROXY: "代理服务器异常或不可用",
        ErrorCategory.PARSING: "页面结构变化或选择器失效",
        ErrorCategory.BROWSER: "浏览器进程异常",
        ErrorCategory.DATA: "数据格式异常或为空",
        ErrorCategory.UNKNOWN: "未知错误，需要人工分析",
    }

    def analyze(
        self,
        category: ErrorCategory,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分析错误

        Args:
            category: 错误分类
            error: 异常对象
            context: 上下文信息

        Returns:
            分析结果字典
        """
        context = context or {}
        error_str = str(error)

        # 获取根因
        root_cause = self._get_root_cause(category, context)

        # 获取可能原因
        probable_causes = self._get_probable_causes(category, error_str, context)

        # 获取解决方案
        solutions = self._get_solutions(category)

        # 选择推荐方案
        recommended = self._select_recommended(solutions)

        # 计算置信度
        confidence = self._calculate_confidence(category, error_str, context)

        return {
            "root_cause": root_cause,
            "probable_causes": probable_causes,
            "solutions": solutions,
            "recommended_solution": recommended,
            "confidence": confidence,
            "auto_fixable": recommended.auto_fixable if recommended else False,
        }

    def _get_root_cause(self, category: ErrorCategory, context: Dict) -> str:
        """获取根因描述"""
        template = self.ROOT_CAUSE_TEMPLATES.get(
            category,
            self.ROOT_CAUSE_TEMPLATES[ErrorCategory.UNKNOWN]
        )

        # 填充模板变量
        status_code = context.get("status_code", "N/A")
        reason = self._get_status_reason(status_code)

        return template.format(status_code=status_code, reason=reason)

    def _get_status_reason(self, status_code: int) -> str:
        """获取状态码原因"""
        reasons = {
            400: "请求参数错误",
            401: "未授权",
            403: "访问被拒绝",
            404: "资源不存在",
            429: "请求频率过高",
            500: "服务器内部错误",
            502: "网关错误",
            503: "服务不可用",
            504: "网关超时",
        }
        return reasons.get(status_code, "未知原因")

    def _get_probable_causes(
        self,
        category: ErrorCategory,
        error_str: str,
        context: Dict
    ) -> List[str]:
        """获取可能原因列表"""
        causes_map = {
            ErrorCategory.HTTP_STATUS: [
                "IP被目标网站封禁",
                "请求头不完整或格式错误",
                "Cookie/Session失效",
                "请求参数缺失或错误",
            ],
            ErrorCategory.TIMEOUT: [
                "网络连接不稳定",
                "代理服务器响应慢",
                "目标服务器负载过高",
                "超时时间设置过短",
            ],
            ErrorCategory.ANTI_SCRAPING: [
                "IP被封禁或进入黑名单",
                "请求频率过高触发限制",
                "浏览器指纹被识别为机器人",
                "User-Agent不合法",
            ],
            ErrorCategory.CAPTCHA: [
                "触发了人机验证机制",
                "请求行为异常被标记",
                "IP风险评分过高",
            ],
            ErrorCategory.SIGNATURE: [
                "签名算法已更新",
                "时间戳过期",
                "参数顺序错误",
                "密钥失效",
            ],
            ErrorCategory.AUTHENTICATION: [
                "Cookie已过期",
                "Token失效",
                "账号被限制",
                "需要重新登录",
            ],
        }

        return causes_map.get(category, ["未知原因，需要人工分析"])

    def _get_solutions(self, category: ErrorCategory) -> List[Solution]:
        """获取解决方案列表"""
        solutions = self.SOLUTION_DATABASE.get(category, [])

        if not solutions:
            # 默认解决方案
            solutions = [
                Solution(
                    action="retry",
                    description="重试请求",
                    auto_fixable=True,
                    estimated_success_rate=0.3,
                    priority=3,
                ),
                Solution(
                    action="escalate",
                    description="上报人工处理",
                    auto_fixable=False,
                    estimated_success_rate=1.0,
                    priority=1,
                ),
            ]

        return sorted(solutions, key=lambda s: s.priority, reverse=True)

    def _select_recommended(self, solutions: List[Solution]) -> Optional[Solution]:
        """选择推荐方案"""
        if not solutions:
            return None

        # 优先选择可自动修复且成功率高的方案
        auto_fixable = [s for s in solutions if s.auto_fixable]
        if auto_fixable:
            return max(auto_fixable, key=lambda s: s.estimated_success_rate)

        return solutions[0]

    def _calculate_confidence(
        self,
        category: ErrorCategory,
        error_str: str,
        context: Dict
    ) -> float:
        """计算诊断置信度"""
        base_confidence = 0.7

        # 有状态码提高置信度
        if context.get("status_code"):
            base_confidence += 0.1

        # 已知分类提高置信度
        if category != ErrorCategory.UNKNOWN:
            base_confidence += 0.1

        return min(base_confidence, 1.0)
