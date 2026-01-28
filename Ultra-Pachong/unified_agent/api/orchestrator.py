"""编排器 - 串联所有模块

AgentOrchestrator 是整个系统的统一调度入口，它会：
1. 自动评估任务需求（是否需要Cookie池、代理等）
2. 查询已有知识，复用成功经验
3. 选择最佳策略执行
4. 从执行结果中学习
"""
import asyncio
from typing import Optional, Dict, Any, List

from ..core import Task, TaskResult, TaskStatus, TaskType
from ..core import DependencyManager, ensure_deps
from ..knowledge import KnowledgeStore, KnowledgeQuery
from ..mcp import MCPServer
from ..feedback import DecisionLogger, KnowledgeLearner, DecisionType, DecisionOutcome
from ..infra.cookie_pool import CookiePoolManager, InfrastructureAdvisor


class AgentOrchestrator:
    """Agent编排器 - 统一调度入口"""

    def __init__(self, auto_install_deps: bool = True):
        # 检查依赖
        self.dep_manager = DependencyManager()
        if auto_install_deps:
            self._ensure_dependencies()

        # 初始化模块
        self.knowledge_store = KnowledgeStore()
        self.knowledge_query = KnowledgeQuery(self.knowledge_store)
        self.mcp = MCPServer()
        self.decision_logger = DecisionLogger()
        self.learner = KnowledgeLearner(self.knowledge_store)

        # 基础设施评估（自动建议Cookie池等）
        self.cookie_pool_manager = CookiePoolManager()
        self.infra_advisor = InfrastructureAdvisor(self.cookie_pool_manager)

    def _ensure_dependencies(self):
        """确保核心依赖已安装"""
        missing = self.dep_manager.get_missing("current")
        if missing:
            print(f"[Agent] 检测到缺失依赖: {', '.join(missing)}")
            results = self.dep_manager.install_missing("current", auto_confirm=True)
            for name, success in results.items():
                status = "✅" if success else "❌"
                print(f"[Agent] 安装 {name}: {status}")

    def install_feature_deps(self, features: List[str]) -> Dict[str, bool]:
        """按功能安装依赖"""
        feature_deps = {
            "browser": ["playwright"],
            "captcha": ["ddddocr"],
            "validation": ["pydantic"],
            "crypto": ["cryptography"],
        }
        results = {}
        for feature in features:
            deps = feature_deps.get(feature, [])
            for dep in deps:
                status, _ = self.dep_manager.check(dep)
                if status.value == "missing":
                    results[dep] = self.dep_manager.install(dep)
        return results

    async def execute_task(self, task: Task) -> TaskResult:
        """执行任务 - 主流程"""
        # 1. 开始记录
        self.decision_logger.start_task(task.id)

        try:
            # 2. 查询已有知识
            site_knowledge = None
            if task.target_url:
                site_knowledge = self.knowledge_query.get_site_knowledge(task.target_url)
                if site_knowledge:
                    self.decision_logger.log_decision(
                        type=DecisionType.MODULE_SELECT,
                        description=f"Found existing knowledge for {site_knowledge.domain}",
                        reason="Knowledge reuse"
                    )

            # 3. 分析并选择策略
            strategy = self._select_strategy(task, site_knowledge)

            # 4. 执行
            result = await self._execute(task, strategy)

            # 5. 学习
            decisions = self.decision_logger.end_task(save=True)
            if task.target_url:
                self.learner.learn_from_task(task.target_url, result, decisions)

            return result

        except Exception as e:
            self.decision_logger.log_decision(
                type=DecisionType.ERROR_HANDLE,
                description=f"Task failed: {str(e)}",
                reason="Exception"
            )
            self.decision_logger.end_task(save=True)
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error_message=str(e)
            )

    def _select_strategy(self, task: Task, site_knowledge) -> Dict:
        """选择策略"""
        # 优先使用已知最佳策略
        if site_knowledge:
            best = self.knowledge_query.get_best_strategy(task.target_url)
            if best:
                decision = self.decision_logger.log_decision(
                    type=DecisionType.STRATEGY_SELECT,
                    description=f"Selected strategy: {best['name']}",
                    reason=f"Success rate: {best.get('success_rate', 'unknown')}",
                    alternatives=["request", "browser", "api"]
                )
                return best

        # 默认策略
        decision = self.decision_logger.log_decision(
            type=DecisionType.STRATEGY_SELECT,
            description="Using default strategy: request",
            reason="No prior knowledge"
        )
        return {"name": "request", "success_rate": 0.5}

    async def _execute(self, task: Task, strategy: Dict) -> TaskResult:
        """执行任务"""
        strategies_tried = [strategy["name"]]

        # 调用MCP工具
        if task.target_url:
            result = self.mcp.scrape(task.target_url)

            if result.status.value == "success":
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.SUCCESS,
                    data=result.data,
                    strategies_tried=strategies_tried,
                    duration_ms=result.duration_ms
                )
            else:
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error_code=result.error_code,
                    error_message=result.error,
                    strategies_tried=strategies_tried
                )

        return TaskResult(
            task_id=task.id,
            status=TaskStatus.FAILED,
            error_message="No target URL"
        )

    # ============ 基础设施评估（自动建议） ============

    def evaluate_task_requirements(
        self,
        url: str,
        target_count: int = 100,
        task_type: str = "scrape",
    ) -> Dict[str, Any]:
        """
        评估任务需求并返回基础设施建议

        这是 Agent 自主评估的核心方法。根据用户提出的问题和需求，
        自动判断是否需要搭建 Cookie池、代理池等基础设施。

        Args:
            url: 目标URL
            target_count: 目标数据量
            task_type: 任务类型

        Returns:
            基础设施建议字典

        示例：
            # 用户说：我要爬取京东1000条商品数据
            advice = orchestrator.evaluate_task_requirements(
                url="https://jd.com/search?q=手机",
                target_count=1000
            )
            print(advice["summary"])  # 输出：需要搭建Cookie池，建议50个...
        """
        # 记录评估决策
        self.decision_logger.start_task(f"eval_{url[:30]}")

        # 评估基础设施需求
        recommendations = self.infra_advisor.evaluate(
            url=url,
            task_type=task_type,
            target_count=target_count,
        )

        # 记录建议
        if recommendations["cookie_pool"]["needed"]:
            self.decision_logger.log_decision(
                type=DecisionType.MODULE_SELECT,
                description=f"建议搭建Cookie池: {recommendations['cookie_pool']['suggested_size']}个",
                reason=recommendations["cookie_pool"]["reason"]
            )

        if recommendations["proxy_pool"]["needed"]:
            self.decision_logger.log_decision(
                type=DecisionType.MODULE_SELECT,
                description=f"建议搭建代理池: {recommendations['proxy_pool']['type']}",
                reason=recommendations["proxy_pool"]["reason"]
            )

        self.decision_logger.end_task(save=False)

        return recommendations

    def print_advice(self, url: str, target_count: int = 100) -> str:
        """
        打印任务建议（人类可读格式）

        这是给用户看的友好输出。

        Args:
            url: 目标URL
            target_count: 目标数据量

        Returns:
            建议报告字符串
        """
        recommendations = self.evaluate_task_requirements(url, target_count)
        return recommendations["summary"]

    async def prepare_infrastructure(
        self,
        url: str,
        target_count: int = 100,
        auto_generate_cookies: bool = True,
    ) -> Dict[str, Any]:
        """
        根据评估结果自动准备基础设施

        Args:
            url: 目标URL
            target_count: 目标数据量
            auto_generate_cookies: 是否自动生成Cookie

        Returns:
            准备结果
        """
        from urllib.parse import urlparse

        domain = urlparse(url).netloc.replace("www.", "")
        recommendations = self.evaluate_task_requirements(url, target_count)
        results = {"prepared": [], "skipped": [], "failed": []}

        # 准备Cookie池
        if recommendations["cookie_pool"]["needed"]:
            need_count = recommendations["cookie_pool"].get("need_generate", 0)
            if need_count > 0 and auto_generate_cookies:
                try:
                    pool = self.cookie_pool_manager.get_pool(domain)
                    generated = await pool.generate(count=need_count, url=url)
                    results["prepared"].append(f"Cookie池: 生成了 {generated} 个")
                except Exception as e:
                    results["failed"].append(f"Cookie池生成失败: {e}")
            else:
                results["skipped"].append("Cookie池: 已有足够数量或未启用自动生成")

        # 代理池提示（需要手动配置）
        if recommendations["proxy_pool"]["needed"]:
            results["skipped"].append(f"代理池: 需要手动配置 ({recommendations['proxy_pool']['type']})")

        return results

    # ============ 便捷方法 ============

    def quick_scrape(self, url: str, **kwargs) -> TaskResult:
        """快速抓取"""
        task = Task(description=f"Scrape {url}", target_url=url)
        return asyncio.run(self.execute_task(task))

    def smart_scrape(self, url: str, target_count: int = 100) -> TaskResult:
        """
        智能抓取 - 先评估需求再执行

        这个方法会：
        1. 评估是否需要Cookie池等基础设施
        2. 打印建议给用户
        3. 执行抓取任务

        Args:
            url: 目标URL
            target_count: 目标数据量

        Returns:
            TaskResult
        """
        # 1. 评估需求
        print(f"\n{'='*50}")
        print("[Agent] 正在评估任务需求...")
        advice = self.print_advice(url, target_count)
        print(advice)
        print(f"{'='*50}\n")

        # 2. 执行任务
        task = Task(
            description=f"Smart scrape {url}",
            target_url=url,
            metadata={"target_count": target_count}
        )
        return asyncio.run(self.execute_task(task))

    def list_tools(self) -> list:
        """列出可用工具"""
        return self.mcp.registry.list_tools()
