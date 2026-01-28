"""
抓取模块 - 核心抓取能力

包含:
- ScraperAgent: 数据抓取器
- InfoCollector: 信息收集器
- SmartAnalyzer: 智能分析器
- SitePreset: 网站预设配置
- StealthBrowser: 隐身浏览器
- JDCommentScraper: 京东评论爬虫
"""

from .agent import ScraperAgent, FieldConfig, PageAnalysis, ScrapeResult
from .collector import InfoCollector, SiteReport
from .smart_analyzer import SmartAnalyzer, SiteAnalysis, SignatureAnalysis
from .presets import SitePreset, get_preset, get_preset_info, list_presets
from .stealth import apply_stealth

# 京东评论爬虫 (延迟导入，因为依赖 playwright)
def __getattr__(name):
    if name == "JDCommentScraper":
        from .jd_comments import JDCommentScraper
        return JDCommentScraper
    if name == "Comment":
        from .jd_comments import Comment
        return Comment
    if name == "CommentCleaner":
        from .jd_comments import CommentCleaner
        return CommentCleaner
    if name == "BRAND_CONFIGS":
        from .jd_comments import BRAND_CONFIGS
        return BRAND_CONFIGS
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # 抓取器
    "ScraperAgent",
    "FieldConfig",
    "PageAnalysis",
    "ScrapeResult",
    # 收集器
    "InfoCollector",
    "SiteReport",
    # 分析器
    "SmartAnalyzer",
    "SiteAnalysis",
    "SignatureAnalysis",
    # 预设
    "SitePreset",
    "get_preset",
    "get_preset_info",
    "list_presets",
    # 隐身
    "apply_stealth",
    # 京东评论爬虫
    "JDCommentScraper",
    "Comment",
    "CommentCleaner",
    "BRAND_CONFIGS",
]
