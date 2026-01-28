"""
MCP服务器 - 对外接口

提供 MCP 协议兼容的服务器，支持工具调用和管理。
"""

import time
import logging
from typing import Dict, Any, List, Optional
from collections import deque

from .types import ToolCall, ToolResult, ToolResultStatus
from .tools import ToolRegistry, create_default_registry

logger = logging.getLogger(__name__)


class RateLimiter:
    """滑动窗口速率限制器"""

    def __init__(self, max_calls: int = 100, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls: deque = deque()

    def check(self) -> bool:
        """检查是否允许调用"""
        now = time.time()

        # 清理过期记录
        while self.calls and self.calls[0] < now - self.window_seconds:
            self.calls.popleft()

        if len(self.calls) >= self.max_calls:
            return False

        self.calls.append(now)
        return True

    def get_remaining(self) -> int:
        """获取剩余可用次数"""
        now = time.time()
        while self.calls and self.calls[0] < now - self.window_seconds:
            self.calls.popleft()
        return max(0, self.max_calls - len(self.calls))


class MCPServer:
    """
    MCP服务器 - 处理工具调用请求

    使用示例:
        server = MCPServer()

        # 列出工具
        tools = server.list_tools()

        # 调用工具
        result = server.call("scrape_page", url="https://example.com")

        # 处理请求
        response = server.handle_request({
            "method": "call_tool",
            "tool": "analyze_site",
            "arguments": {"url": "https://jd.com"}
        })
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        rate_limit: int = 100,
        rate_window: int = 60
    ):
        """
        初始化 MCP 服务器

        Args:
            registry: 工具注册表（默认使用内置注册表）
            rate_limit: 每分钟最大调用次数
            rate_window: 速率限制时间窗口（秒）
        """
        self.registry = registry or create_default_registry()
        self.rate_limiter = RateLimiter(rate_limit, rate_window)

        # 安全配置
        self.url_blacklist = [
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "internal",
            "169.254.",  # Link-local
            "10.",       # Private
            "192.168.",  # Private
        ]

        # 统计
        self._total_calls = 0
        self._success_calls = 0
        self._error_calls = 0

        logger.info(f"[MCPServer] 初始化完成，工具数: {len(self.registry.list_names())}")

    # ==================== 请求处理 ====================

    def handle_request(self, request: Dict) -> Dict:
        """
        处理请求 - 主入口

        Args:
            request: 请求字典，包含 method 和相关参数

        Returns:
            响应字典
        """
        method = request.get("method")

        handlers = {
            "list_tools": self._handle_list_tools,
            "call_tool": lambda: self._handle_call_tool(request),
            "get_tool": lambda: self._handle_get_tool(request),
            "server_info": self._handle_server_info,
        }

        handler = handlers.get(method)
        if handler:
            return handler()
        else:
            return {
                "error": f"Unknown method: {method}",
                "error_code": "INVALID_METHOD",
                "available_methods": list(handlers.keys())
            }

    def _handle_list_tools(self) -> Dict:
        """返回工具列表"""
        return {
            "tools": self.registry.list_tools(),
            "count": len(self.registry.list_names())
        }

    def _handle_get_tool(self, request: Dict) -> Dict:
        """获取单个工具信息"""
        tool_name = request.get("tool")
        tool = self.registry.get(tool_name)

        if tool:
            return {"tool": tool.to_schema()}
        else:
            return {
                "error": f"Tool not found: {tool_name}",
                "error_code": "TOOL_NOT_FOUND"
            }

    def _handle_call_tool(self, request: Dict) -> Dict:
        """处理工具调用"""
        tool_name = request.get("tool")
        arguments = request.get("arguments", {})

        self._total_calls += 1

        # 安全检查
        security_result = self._security_check(tool_name, arguments)
        if not security_result["passed"]:
            self._error_calls += 1
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=security_result["reason"],
                error_code="SECURITY_BLOCKED"
            ).to_dict()

        # 速率限制
        if not self.rate_limiter.check():
            self._error_calls += 1
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Rate limit exceeded. Remaining: {self.rate_limiter.get_remaining()}",
                error_code="RATE_LIMITED"
            ).to_dict()

        # 执行
        result = self.registry.execute(tool_name, arguments)

        if result.status == ToolResultStatus.SUCCESS:
            self._success_calls += 1
        else:
            self._error_calls += 1

        return result.to_dict()

    def _handle_server_info(self) -> Dict:
        """返回服务器信息"""
        return {
            "name": "Unified Agent MCP Server",
            "version": "1.0.0",
            "tools_count": len(self.registry.list_names()),
            "rate_limit": {
                "limit": self.rate_limiter.max_calls,
                "window_seconds": self.rate_limiter.window_seconds,
                "remaining": self.rate_limiter.get_remaining(),
            },
            "stats": {
                "total_calls": self._total_calls,
                "success_calls": self._success_calls,
                "error_calls": self._error_calls,
                "success_rate": self._success_calls / self._total_calls if self._total_calls > 0 else 1.0,
            }
        }

    # ==================== 安全检查 ====================

    def _security_check(self, tool_name: str, arguments: Dict) -> Dict:
        """
        安全检查

        Returns:
            {"passed": bool, "reason": str}
        """
        # 检查工具是否存在
        if not self.registry.get(tool_name):
            return {"passed": False, "reason": f"Tool not found: {tool_name}"}

        # 检查URL黑名单
        url = arguments.get("url", "")
        for blocked in self.url_blacklist:
            if blocked in url.lower():
                return {"passed": False, "reason": f"URL blocked: contains '{blocked}'"}

        # 检查敏感参数
        sensitive_keys = ["password", "secret", "token", "key"]
        for key in arguments:
            if any(s in key.lower() for s in sensitive_keys):
                logger.warning(f"[MCPServer] 敏感参数检测: {key}")

        return {"passed": True, "reason": ""}

    # ==================== 便捷方法 ====================

    def list_tools(self) -> List[Dict]:
        """列出所有工具"""
        return self.registry.list_tools()

    def call(self, tool_name: str, **kwargs) -> ToolResult:
        """
        直接调用工具

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            ToolResult
        """
        result_dict = self._handle_call_tool({
            "tool": tool_name,
            "arguments": kwargs
        })

        return ToolResult(
            status=ToolResultStatus(result_dict["status"]),
            data=result_dict.get("data"),
            error=result_dict.get("error"),
            error_code=result_dict.get("error_code"),
            duration_ms=result_dict.get("duration_ms", 0),
            metadata=result_dict.get("metadata", {})
        )

    def scrape(self, url: str, **kwargs) -> ToolResult:
        """抓取页面 - 快捷方法"""
        return self.call("scrape_page", url=url, **kwargs)

    def analyze(self, url: str) -> ToolResult:
        """分析网站 - 快捷方法"""
        return self.call("analyze_site", url=url)

    def sign(self, params: Dict, sign_type: str = "md5", secret: str = "") -> ToolResult:
        """生成签名 - 快捷方法"""
        return self.call("generate_signature", params=params, sign_type=sign_type, secret=secret)

    def diagnose(self, error_message: str, status_code: Optional[int] = None) -> ToolResult:
        """诊断错误 - 快捷方法"""
        args = {"error_message": error_message}
        if status_code:
            args["status_code"] = status_code
        return self.call("diagnose_error", **args)

    # ==================== 统计 ====================

    def get_stats(self) -> Dict:
        """获取服务器统计"""
        return self._handle_server_info()["stats"]

    def reset_stats(self):
        """重置统计"""
        self._total_calls = 0
        self._success_calls = 0
        self._error_calls = 0
