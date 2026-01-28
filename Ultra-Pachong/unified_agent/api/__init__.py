"""
API 模块 - 主要接口

包含:
- Brain: AI 协作接口，Claude 控制 Agent 的统一入口
- AgentOrchestrator: 编排器，串联所有模块
"""

from .brain import (
    Brain,
    ApiCallResult,
    RetryConfig,
    quick_investigate,
    quick_smart_investigate,
    quick_scrape,
    get_site_info,
)
from .orchestrator import AgentOrchestrator

__all__ = [
    "Brain",
    "ApiCallResult",
    "RetryConfig",
    "AgentOrchestrator",
    "quick_investigate",
    "quick_smart_investigate",
    "quick_scrape",
    "get_site_info",
]
