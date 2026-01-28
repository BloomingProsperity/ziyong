"""
Unified Agent - AI 驱动的智能采集系统 (升级版)

核心组件:
- Brain: AI 协作接口，Claude 控制 Agent 的统一入口
- SmartAnalyzer: 智能分析器，自动识别网站特征
- InfoCollector: 信息收集器，捕获网站所有信息
- ScraperAgent: 数据抓取器

新增独立模块包（可单独导入）:
- diagnosis/: 诊断模块 - 错误分析、自动修复
- recovery/: 恢复模块 - 故障决策树、自动恢复
- signature/: 签名模块 - 标准算法、平台签名
- credential/: 凭据模块 - 凭据池管理

目录结构:
- api/: 主接口 (brain, orchestrator)
- scraper/: 抓取模块 (agent, collector, analyzer, presets, stealth)
- infra/: 基础设施 (proxy, cookie_pool, sign_server, dispatcher)
- core/: 核心基础 (config, task, types, deps)
- diagnosis/: 诊断模块（独立）
- recovery/: 恢复模块（独立）
- signature/: 签名模块（独立）
- credential/: 凭据模块（独立）
- knowledge/: 知识库
- mcp/: MCP服务
- feedback/: 反馈学习

使用方式:

    # 方式1: 完整导入（需要playwright）
    from unified_agent import Brain
    brain = Brain()

    # 方式2: 单独导入模块（无需playwright）
    from unified_agent.diagnosis import Diagnoser
    from unified_agent.recovery import FaultDecisionTree
    from unified_agent.signature import SignatureGenerator
    from unified_agent.credential import CredentialPool
"""

# 延迟导入：只有实际使用时才加载依赖playwright的模块
# 这样新模块可以独立使用

def __getattr__(name):
    """延迟导入，支持模块按需加载"""
    
    # 配置 (core/) - 无外部依赖
    if name == "AgentConfig":
        from .core.config import AgentConfig
        return AgentConfig
    
    # 以下模块依赖 playwright，按需加载
    _scraper_exports = {
        "ScraperAgent", "FieldConfig", "PageAnalysis", "ScrapeResult",
        "InfoCollector", "SiteReport",
        "SmartAnalyzer", "SiteAnalysis", "SignatureAnalysis",
        "SitePreset", "get_preset", "get_preset_info", "list_presets",
    }
    
    _infra_exports = {
        "ProxyManager", "ProxyInfo", "ProxyPool", "ProxyType", "create_residential_proxy",
        "CookiePool", "CookiePoolManager", "InfrastructureAdvisor", "CookieSession",
        "SignatureGenerator", "SignClient", "SignRequest", "SignResponse",
        "MassiveDispatcher", "DispatchResult", "batch_fetch",
    }
    
    _api_exports = {
        "Brain", "ApiCallResult", "RetryConfig",
        "quick_investigate", "quick_smart_investigate", "quick_scrape", "get_site_info",
        "AgentOrchestrator",
    }
    
    if name in _scraper_exports:
        if name in ("ScraperAgent", "FieldConfig", "PageAnalysis", "ScrapeResult"):
            from .scraper.agent import ScraperAgent, FieldConfig, PageAnalysis, ScrapeResult
            return locals()[name]
        elif name in ("InfoCollector", "SiteReport"):
            from .scraper.collector import InfoCollector, SiteReport
            return locals()[name]
        elif name in ("SmartAnalyzer", "SiteAnalysis", "SignatureAnalysis"):
            from .scraper.smart_analyzer import SmartAnalyzer, SiteAnalysis, SignatureAnalysis
            return locals()[name]
        elif name in ("SitePreset", "get_preset", "get_preset_info", "list_presets"):
            from .scraper.presets import SitePreset, get_preset, get_preset_info, list_presets
            return locals()[name]
    
    if name in _infra_exports:
        if name in ("ProxyManager", "ProxyInfo", "ProxyPool", "ProxyType", "create_residential_proxy"):
            from .infra.proxy import ProxyManager, ProxyInfo, ProxyPool, ProxyType, create_residential_proxy
            return locals()[name]
        elif name in ("CookiePool", "CookiePoolManager", "InfrastructureAdvisor", "CookieSession"):
            from .infra.cookie_pool import CookiePool, CookiePoolManager, InfrastructureAdvisor, CookieSession
            return locals()[name]
        elif name in ("SignatureGenerator", "SignClient", "SignRequest", "SignResponse"):
            from .infra.sign_server import SignatureGenerator as SG, SignClient, SignRequest, SignResponse
            if name == "SignatureGenerator":
                return SG
            return locals()[name]
        elif name in ("MassiveDispatcher", "DispatchResult", "batch_fetch"):
            from .infra.dispatcher import MassiveDispatcher, DispatchResult, batch_fetch
            return locals()[name]
    
    if name in _api_exports:
        if name == "AgentOrchestrator":
            from .api.orchestrator import AgentOrchestrator
            return AgentOrchestrator
        else:
            from .api.brain import (
                Brain, ApiCallResult, RetryConfig,
                quick_investigate, quick_smart_investigate, quick_scrape, get_site_info,
            )
            return locals()[name]
    
    raise AttributeError(f"module 'unified_agent' has no attribute '{name}'")

__all__ = [
    # 核心接口
    "Brain",
    "AgentOrchestrator",
    "SmartAnalyzer",
    "InfoCollector",
    "ScraperAgent",
    # 配置
    "AgentConfig",
    "RetryConfig",
    # 数据类
    "SiteReport",
    "SiteAnalysis",
    "SignatureAnalysis",
    "ScrapeResult",
    "PageAnalysis",
    "FieldConfig",
    "ApiCallResult",
    # 预设
    "SitePreset",
    "get_preset",
    "get_preset_info",
    "list_presets",
    # 代理
    "ProxyManager",
    "ProxyInfo",
    "ProxyPool",
    "ProxyType",
    "create_residential_proxy",
    # Cookie池
    "CookiePool",
    "CookiePoolManager",
    "CookieSession",
    "InfrastructureAdvisor",
    # 签名服务
    "SignatureGenerator",
    "SignClient",
    "SignRequest",
    "SignResponse",
    # 高并发调度
    "MassiveDispatcher",
    "DispatchResult",
    "batch_fetch",
    # 便捷函数
    "quick_investigate",
    "quick_smart_investigate",
    "quick_scrape",
    "get_site_info",
]
