"""知识Schema - 定义知识结构 (来自 22-knowledge-format)"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class KnowledgeType(str, Enum):
    """知识类型"""
    SITE = "site"              # 网站知识
    TECHNIQUE = "technique"    # 技术知识
    ERROR = "error"            # 错误知识
    DECISION = "decision"      # 决策知识


@dataclass
class KnowledgeEntry:
    """知识条目基类"""
    id: str
    type: KnowledgeType
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source_task_id: Optional[str] = None       # 来源任务
    confidence: float = 0.5                    # 置信度 0-1
    use_count: int = 0                         # 使用次数
    tags: List[str] = field(default_factory=list)


@dataclass
class SiteKnowledge(KnowledgeEntry):
    """网站知识 - 特定网站的爬取经验"""
    domain: str = ""

    # 反爬特征
    anti_crawl: Dict[str, Any] = field(default_factory=dict)
    # 例: {"signature": "h5st", "captcha": "slider", "rate_limit": "100/min"}

    # 有效策略
    strategies: List[Dict] = field(default_factory=list)
    # 例: [{"name": "api", "success_rate": 0.8, "note": "需要签名"}]

    # 选择器
    selectors: Dict[str, str] = field(default_factory=dict)
    # 例: {"title": ".product-name", "price": ".price-value"}

    def __post_init__(self):
        self.type = KnowledgeType.SITE
        self.id = f"site:{self.domain}"


@dataclass
class ErrorKnowledge(KnowledgeEntry):
    """错误知识 - 错误处理经验"""
    error_code: str = ""
    error_pattern: str = ""                    # 错误特征

    cause: str = ""                            # 原因
    fix: str = ""                              # 解决方法
    prevention: str = ""                       # 预防措施

    def __post_init__(self):
        self.type = KnowledgeType.ERROR
        self.id = f"error:{self.error_code}"


@dataclass
class TechniqueKnowledge(KnowledgeEntry):
    """技术知识 - 通用技术方案"""
    name: str = ""
    description: str = ""
    code_snippet: str = ""
    applicable_scenarios: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.type = KnowledgeType.TECHNIQUE
        self.id = f"tech:{self.name}"
