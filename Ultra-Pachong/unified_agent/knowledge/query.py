"""知识查询 - 检索接口"""
from typing import Optional, List, Dict
from urllib.parse import urlparse

from .schema import SiteKnowledge, ErrorKnowledge, KnowledgeEntry
from .store import KnowledgeStore


class KnowledgeQuery:
    """知识查询接口"""

    def __init__(self, store: Optional[KnowledgeStore] = None):
        self.store = store or KnowledgeStore()

    def get_site_knowledge(self, url: str) -> Optional[SiteKnowledge]:
        """根据URL获取网站知识"""
        domain = urlparse(url).netloc
        # 尝试精确匹配
        entry = self.store.load(f"site:{domain}")
        if entry:
            return entry

        # 尝试主域名匹配 (www.jd.com -> jd.com)
        parts = domain.split(".")
        if len(parts) > 2:
            main_domain = ".".join(parts[-2:])
            entry = self.store.load(f"site:{main_domain}")
            if entry:
                return entry

        return None

    def get_error_solution(self, error_code: str) -> Optional[ErrorKnowledge]:
        """根据错误码获取解决方案"""
        return self.store.load(f"error:{error_code}")

    def find_similar_sites(self, anti_crawl_features: List[str]) -> List[SiteKnowledge]:
        """查找有相似反爬特征的网站"""
        results = []
        for site_name in self.store.list_sites():
            entry = self.store.load(f"site:{site_name}")
            if entry and isinstance(entry, SiteKnowledge):
                site_features = list(entry.anti_crawl.keys())
                if any(f in site_features for f in anti_crawl_features):
                    results.append(entry)
        return results

    def get_best_strategy(self, url: str) -> Optional[Dict]:
        """获取URL的最佳策略"""
        site = self.get_site_knowledge(url)
        if not site or not site.strategies:
            return None

        # 按成功率排序
        sorted_strategies = sorted(
            site.strategies,
            key=lambda s: s.get("success_rate", 0),
            reverse=True
        )
        return sorted_strategies[0] if sorted_strategies else None

    def record_usage(self, entry_id: str):
        """记录知识使用次数"""
        entry = self.store.load(entry_id)
        if entry:
            entry.use_count += 1
            self.store.save(entry)
