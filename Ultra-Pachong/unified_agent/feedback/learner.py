"""知识学习器 - 从任务执行中学习"""
from typing import Optional, List, Dict
from urllib.parse import urlparse
from datetime import datetime

from ..knowledge import KnowledgeStore, SiteKnowledge, ErrorKnowledge
from ..core.task import TaskResult
from .logger import DecisionLogger, Decision, DecisionOutcome


class KnowledgeLearner:
    """从任务执行中学习知识"""

    def __init__(self, store: Optional[KnowledgeStore] = None):
        self.store = store or KnowledgeStore()

    def learn_from_task(self, url: str, result: TaskResult,
                        decisions: List[Decision]):
        """从完成的任务中学习"""
        domain = urlparse(url).netloc

        # 学习网站知识
        self._learn_site(domain, result, decisions)

        # 学习错误知识
        if result.error_code:
            self._learn_error(result)

    def _learn_site(self, domain: str, result: TaskResult,
                    decisions: List[Decision]):
        """学习网站知识"""
        # 加载或创建
        site = self.store.load(f"site:{domain}")
        if not site:
            site = SiteKnowledge(domain=domain)

        # 更新策略成功率
        for strategy in result.strategies_tried:
            self._update_strategy(site, strategy, result.status.value == "success")

        # 从知识增益中提取信息
        if result.knowledge_gained:
            if "anti_crawl" in result.knowledge_gained:
                site.anti_crawl.update(result.knowledge_gained["anti_crawl"])
            if "selectors" in result.knowledge_gained:
                site.selectors.update(result.knowledge_gained["selectors"])

        # 更新置信度
        site.use_count += 1
        site.confidence = min(0.95, site.confidence + 0.05)

        self.store.save(site)

    def _update_strategy(self, site: SiteKnowledge, strategy_name: str,
                         success: bool):
        """更新策略成功率"""
        # 查找现有策略
        existing = None
        for s in site.strategies:
            if s.get("name") == strategy_name:
                existing = s
                break

        if existing:
            # 滑动平均更新成功率
            old_rate = existing.get("success_rate", 0.5)
            new_rate = old_rate * 0.8 + (1.0 if success else 0.0) * 0.2
            existing["success_rate"] = round(new_rate, 2)
            existing["last_used"] = datetime.now().isoformat()
        else:
            # 添加新策略
            site.strategies.append({
                "name": strategy_name,
                "success_rate": 1.0 if success else 0.0,
                "first_used": datetime.now().isoformat()
            })

    def _learn_error(self, result: TaskResult):
        """学习错误知识"""
        error_id = f"error:{result.error_code}"
        error = self.store.load(error_id)

        if not error:
            error = ErrorKnowledge(
                error_code=result.error_code,
                error_pattern=result.error_message or "",
            )

        error.use_count += 1
        self.store.save(error)

    def summarize_learning(self, task_id: str) -> Dict:
        """总结本次学习内容（用于日志）"""
        return {
            "task_id": task_id,
            "learned_at": datetime.now().isoformat(),
            "summary": "Learning complete"
            # TODO: 添加详细统计
        }
