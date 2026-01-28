"""
AI 协作接口 (Brain Interface) - 智能升级版

这个模块是 Claude AI 控制 Agent 的统一入口。
Claude 可以通过这个接口：
1. 收集目标网站信息
2. 智能分析网站特征和反爬策略
3. 执行交互操作
4. 调用 API 并自动重试
5. 执行数据抓取

核心功能：
- 智能分析：自动识别网站类型、反爬等级、加密参数
- 预设配置：内置 10+ 主流网站的配置
- 智能重试：自动处理失败，指数退避
- AI 友好：所有输出都优化为 AI 易读格式

使用方式（在 IDE 中由 Claude 调用）：

    from unified_agent import Brain

    brain = Brain()

    # 智能调查（自动分析）
    analysis = brain.smart_investigate("https://jd.com/item/123")
    print(analysis.to_ai_report())  # AI 友好的完整报告

    # 基于分析结果决策
    if analysis.recommended_approach == "direct_api":
        result = brain.call_api(...)
    else:
        result = brain.scrape_page(...)
"""

from __future__ import annotations

import json
import logging
import time
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Callable

import httpx

from ..core.config import AgentConfig
from ..scraper.collector import InfoCollector, SiteReport
from ..scraper.agent import ScraperAgent, ScrapeResult
from ..infra.proxy import ProxyManager
from ..scraper.smart_analyzer import SmartAnalyzer, SiteAnalysis, SignatureAnalysis
from ..scraper.presets import get_preset, get_preset_info, list_presets, SitePreset
from ..infra.cookie_pool import CookiePool, CookiePoolManager, InfrastructureAdvisor, CookieSession

logger = logging.getLogger(__name__)


@dataclass
class ApiCallResult:
    """API 调用结果"""
    success: bool
    status_code: int | None
    headers: dict[str, str]
    body: str | dict | list | None
    error: str | None = None
    retries: int = 0
    response_time_ms: float = 0

    def to_ai_summary(self) -> str:
        """生成 AI 友好的摘要"""
        if self.success:
            body_preview = ""
            if isinstance(self.body, dict):
                body_preview = f"返回 JSON 对象，包含 {len(self.body)} 个字段"
            elif isinstance(self.body, list):
                body_preview = f"返回 JSON 数组，包含 {len(self.body)} 条数据"
            elif isinstance(self.body, str):
                body_preview = f"返回文本，长度 {len(self.body)} 字符"

            return f"[OK] 请求成功 | 状态码: {self.status_code} | {body_preview} | 耗时: {self.response_time_ms:.0f}ms"
        else:
            return f"[FAIL] 请求失败 | 状态码: {self.status_code} | 错误: {self.error} | 重试次数: {self.retries}"


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0  # 基础延迟（秒）
    max_delay: float = 30.0  # 最大延迟
    exponential_base: float = 2.0  # 指数基数
    jitter: bool = True  # 是否添加随机抖动
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)  # 这些状态码会重试


class Brain:
    """
    AI 大脑接口 - 智能升级版

    这是 Claude 控制 Agent 的统一入口。
    所有方法都设计为易于 AI 调用和理解。

    核心能力：
    1. 智能调查：自动识别网站特征、反爬策略
    2. 预设配置：内置主流网站配置
    3. 智能重试：自动处理失败
    4. AI 友好：输出优化为 AI 易读格式
    """

    def __init__(self, config: AgentConfig | None = None, retry_config: RetryConfig | None = None):
        """
        初始化 Brain

        Args:
            config: Agent 配置对象，如果不传则使用默认配置
            retry_config: 重试配置对象
        """
        self.config = config or AgentConfig()
        self.retry_config = retry_config or RetryConfig()
        self.collector = InfoCollector(self.config)
        self.scraper = ScraperAgent(self.config)
        self.proxy_manager = ProxyManager(self.config)
        self.analyzer = SmartAnalyzer()

        # Cookie池和基础设施评估
        self.cookie_pool_manager = CookiePoolManager(str(self.config.data_dir / "cookies"))
        self.infra_advisor = InfrastructureAdvisor(self.cookie_pool_manager)

        # 存储收集到的信息，供后续使用
        self._last_report: SiteReport | None = None
        self._last_analysis: SiteAnalysis | None = None
        self._collected_cookies: dict[str, str] = {}
        self._collected_headers: dict[str, str] = {}
        self._request_count: int = 0
        self._error_count: int = 0
        self._current_cookie_session: CookieSession | None = None

    # ==================== 第一阶段：信息收集 ====================

    def investigate(
        self,
        url: str,
        wait_seconds: float = 5.0,
        scroll: bool = True,
        take_screenshot: bool = True,
    ) -> SiteReport:
        """
        调查目标网站

        这是第一步，收集网站的所有信息供 AI 分析。

        Args:
            url: 目标 URL
            wait_seconds: 等待时间（让 AJAX 加载完成）
            scroll: 是否滚动页面
            take_screenshot: 是否截图

        Returns:
            SiteReport 对象，包含所有收集到的信息

        示例：
            report = brain.investigate("https://jd.com")
            print(report.summary_for_ai())  # 打印摘要供 AI 分析
        """
        logger.info(f"Investigating: {url}")
        report = self.collector.collect(
            url=url,
            wait_seconds=wait_seconds,
            scroll=scroll,
            take_screenshot=take_screenshot,
        )

        # 存储信息供后续使用
        self._last_report = report
        self._update_collected_data(report)

        logger.info(f"Investigation complete. Found {len(report.api_requests)} API requests")
        return report

    def smart_investigate(
        self,
        url: str,
        wait_seconds: float = 5.0,
        scroll: bool = True,
        take_screenshot: bool = True,
    ) -> SiteAnalysis:
        """
        智能调查目标网站（推荐使用）

        这是升级版的 investigate 方法，会自动：
        1. 收集网站信息
        2. 识别网站类型
        3. 评估反爬强度
        4. 分析加密参数
        5. 生成操作建议

        Args:
            url: 目标 URL
            wait_seconds: 等待时间
            scroll: 是否滚动页面
            take_screenshot: 是否截图

        Returns:
            SiteAnalysis 对象，包含智能分析结果
            使用 .to_ai_report() 获取 AI 友好的报告

        示例：
            analysis = brain.smart_investigate("https://jd.com")
            print(analysis.to_ai_report())  # 完整的 AI 分析报告
            print(f"反爬等级: {analysis.anti_scrape_level}")
            print(f"推荐方案: {analysis.recommended_approach}")
        """
        logger.info(f"Smart investigating: {url}")

        # 先检查是否有预设配置
        preset_info = get_preset_info(url)
        if preset_info.get("found"):
            logger.info(f"Found preset for: {preset_info.get('name')}")

        # 收集信息
        report = self.investigate(url, wait_seconds, scroll, take_screenshot)

        # 智能分析
        analysis = self.analyzer.analyze(report)
        self._last_analysis = analysis

        logger.info(
            f"Smart analysis complete. "
            f"Type: {analysis.site_type}, "
            f"Anti-scrape: {analysis.anti_scrape_level}, "
            f"Approach: {analysis.recommended_approach}"
        )

        return analysis

    def get_recommendation(self, url: str | None = None) -> str:
        """
        获取快速建议

        如果已经做过分析，直接返回建议；
        否则先进行快速分析。

        Returns:
            AI 友好的建议文本
        """
        if self._last_analysis:
            return self._last_analysis.to_ai_report()

        if url:
            analysis = self.smart_investigate(url)
            return analysis.to_ai_report()

        return "请先调用 smart_investigate(url) 进行分析"

    def get_preset(self, url: str) -> SitePreset | None:
        """
        获取网站预设配置

        Args:
            url: URL 或域名

        Returns:
            SitePreset 或 None
        """
        return get_preset(url)

    def list_supported_sites(self) -> list[str]:
        """列出所有支持的预设网站"""
        return list_presets()

    def interact(
        self,
        url: str,
        actions: list[dict[str, Any]],
        wait_between: float = 1.0,
    ) -> SiteReport:
        """
        带交互的信息收集

        当需要点击按钮、填写表单等操作来触发 API 请求时使用。

        Args:
            url: 目标 URL
            actions: 动作列表，支持的动作类型：
                - {"type": "click", "selector": "#button"}
                - {"type": "fill", "selector": "#input", "value": "text"}
                - {"type": "wait", "seconds": 2}
                - {"type": "scroll"}
                - {"type": "hover", "selector": ".menu"}
            wait_between: 动作之间的等待时间

        Returns:
            SiteReport 对象

        示例：
            report = brain.interact("https://example.com", [
                {"type": "click", "selector": ".search-btn"},
                {"type": "wait", "seconds": 2},
            ])
        """
        logger.info(f"Interacting with: {url}, actions: {len(actions)}")
        report = self.collector.collect_with_interaction(
            url=url,
            actions=actions,
            wait_between_actions=wait_between,
        )

        self._last_report = report
        self._update_collected_data(report)

        logger.info(f"Interaction complete. Found {len(report.api_requests)} API requests")
        return report

    # ==================== 第二阶段：API 调用 ====================

    def call_api(
        self,
        url: str,
        method: Literal["GET", "POST", "PUT", "DELETE"] = "GET",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        form_body: dict[str, Any] | None = None,
        use_collected_cookies: bool = True,
        timeout: float = 30.0,
        retry: bool = True,
    ) -> ApiCallResult:
        """
        直接调用 API（带智能重试）

        当 AI 分析出 API 结构后，可以直接调用。
        内置智能重试机制，自动处理临时错误。

        Args:
            url: API URL
            method: 请求方法
            headers: 请求头
            params: URL 参数
            json_body: JSON 请求体
            form_body: 表单请求体
            use_collected_cookies: 是否使用之前收集的 Cookie
            timeout: 超时时间
            retry: 是否启用智能重试

        Returns:
            ApiCallResult 对象

        示例：
            result = brain.call_api(
                url="https://api.example.com/data",
                method="POST",
                headers={"Content-Type": "application/json"},
                json_body={"page": 1, "size": 20},
            )
            print(result.to_ai_summary())
        """
        logger.info(f"Calling API: {method} {url}")
        self._request_count += 1

        # 构建请求头
        final_headers = self._build_headers(headers, use_collected_cookies)

        # 执行请求（带重试）
        max_attempts = self.retry_config.max_retries + 1 if retry else 1
        last_error = None
        retries = 0

        for attempt in range(max_attempts):
            start_time = time.time()
            try:
                result = self._execute_api_call(
                    url, method, final_headers, params, json_body, form_body, timeout
                )
                result.response_time_ms = (time.time() - start_time) * 1000
                result.retries = retries

                # 检查是否需要重试
                if result.success:
                    return result

                if result.status_code in self.retry_config.retry_on_status:
                    if attempt < max_attempts - 1:
                        delay = self._calculate_retry_delay(attempt)
                        logger.warning(
                            f"Request failed with {result.status_code}, "
                            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_attempts})"
                        )
                        time.sleep(delay)
                        retries += 1
                        continue

                return result

            except Exception as e:
                last_error = str(e)
                self._error_count += 1

                if attempt < max_attempts - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.warning(
                        f"Request error: {e}, "
                        f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_attempts})"
                    )
                    time.sleep(delay)
                    retries += 1
                    continue

        return ApiCallResult(
            success=False,
            status_code=None,
            headers={},
            body=None,
            error=last_error,
            retries=retries,
            response_time_ms=0,
        )

    def _build_headers(
        self,
        custom_headers: dict[str, str] | None,
        use_collected_cookies: bool,
    ) -> dict[str, str]:
        """构建请求头"""
        final_headers = {}

        # 添加收集的 Cookie
        if use_collected_cookies and self._collected_cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self._collected_cookies.items())
            final_headers["Cookie"] = cookie_str

        # 添加收集的其他头
        if self._collected_headers:
            final_headers.update(self._collected_headers)

        # 添加自定义头
        if custom_headers:
            final_headers.update(custom_headers)

        return final_headers

    def _execute_api_call(
        self,
        url: str,
        method: str,
        headers: dict[str, str],
        params: dict[str, Any] | None,
        json_body: dict[str, Any] | None,
        form_body: dict[str, Any] | None,
        timeout: float,
    ) -> ApiCallResult:
        """执行单次 API 调用"""
        proxy = self.proxy_manager.get_httpx_proxy()

        with httpx.Client(proxy=proxy, timeout=timeout, follow_redirects=True) as client:
            response = client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body,
                data=form_body,
            )

            # 解析响应
            body: str | dict | list | None = None
            content_type = response.headers.get("content-type", "")

            if "json" in content_type:
                try:
                    body = response.json()
                except:
                    body = response.text
            else:
                body = response.text

            return ApiCallResult(
                success=response.status_code < 400,
                status_code=response.status_code,
                headers=dict(response.headers),
                body=body,
            )

    def _calculate_retry_delay(self, attempt: int) -> float:
        """计算重试延迟（指数退避 + 抖动）"""
        delay = self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt)
        delay = min(delay, self.retry_config.max_delay)

        if self.retry_config.jitter:
            delay = delay * (0.5 + random.random())

        return delay

    def batch_call_api(
        self,
        requests: list[dict[str, Any]],
        delay_between: float = 1.0,
        stop_on_error: bool = False,
    ) -> list[ApiCallResult]:
        """
        批量调用 API

        Args:
            requests: 请求列表，每个请求是一个字典，包含 call_api 的参数
            delay_between: 请求之间的延迟（秒）
            stop_on_error: 遇到错误是否停止

        Returns:
            结果列表

        示例：
            results = brain.batch_call_api([
                {"url": "https://api.example.com/page/1"},
                {"url": "https://api.example.com/page/2"},
                {"url": "https://api.example.com/page/3"},
            ])
        """
        results = []
        for i, req in enumerate(requests):
            logger.info(f"Batch request {i + 1}/{len(requests)}")

            result = self.call_api(**req)
            results.append(result)

            if not result.success and stop_on_error:
                logger.warning(f"Stopping batch due to error: {result.error}")
                break

            if i < len(requests) - 1:
                time.sleep(delay_between)

        return results

    # ==================== 第三阶段：数据抓取 ====================

    def scrape_page(
        self,
        url: str,
        max_pages: int = 1,
    ) -> ScrapeResult:
        """
        抓取页面数据

        使用智能提取从页面 DOM 中提取数据。

        Args:
            url: 目标 URL
            max_pages: 最大翻页数

        Returns:
            ScrapeResult 对象
        """
        return self.scraper.scrape(url, max_pages=max_pages)

    def scrape_with_selector(
        self,
        url: str,
        item_selector: str,
        fields: list[dict[str, str]],
        max_pages: int = 1,
    ) -> ScrapeResult:
        """
        使用自定义选择器抓取

        Args:
            url: 目标 URL
            item_selector: 列表项选择器
            fields: 字段配置列表
            max_pages: 最大翻页数

        Returns:
            ScrapeResult 对象

        示例：
            result = brain.scrape_with_selector(
                url="https://example.com/products",
                item_selector=".product-card",
                fields=[
                    {"name": "title", "selector": ".title", "attr": "text"},
                    {"name": "price", "selector": ".price", "attr": "text"},
                ],
            )
        """
        return self.scraper.scrape_with_selector(
            url=url,
            item_selector=item_selector,
            fields=fields,
            max_pages=max_pages,
        )

    # ==================== 工具方法 ====================

    def get_last_report(self) -> SiteReport | None:
        """获取上次收集的报告"""
        return self._last_report

    def get_collected_cookies(self) -> dict[str, str]:
        """获取收集到的 Cookie"""
        return self._collected_cookies.copy()

    def set_cookies(self, cookies: dict[str, str]) -> None:
        """手动设置 Cookie"""
        self._collected_cookies.update(cookies)

    def set_headers(self, headers: dict[str, str]) -> None:
        """手动设置请求头"""
        self._collected_headers.update(headers)

    def save_report(self, report: SiteReport, filename: str | None = None) -> Path:
        """
        保存报告到文件

        Args:
            report: SiteReport 对象
            filename: 文件名（不含扩展名）

        Returns:
            保存的文件路径
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}"

        output_path = self.config.data_dir / f"{filename}.json"
        output_path.write_text(report.to_json(), encoding="utf-8")

        # 保存截图
        if report.screenshot_b64:
            import base64
            screenshot_path = self.config.data_dir / f"{filename}_screenshot.png"
            screenshot_path.write_bytes(base64.b64decode(report.screenshot_b64))

        logger.info(f"Report saved: {output_path}")
        return output_path

    def export_data(self, data: list[dict], filename: str, format: Literal["json", "csv"] = "json") -> Path:
        """导出数据"""
        return self.scraper.export_data(data, filename, format)

    def _update_collected_data(self, report: SiteReport) -> None:
        """从报告中更新收集的数据"""
        # 更新 Cookie
        for cookie in report.cookies:
            name = cookie.get("name")
            value = cookie.get("value")
            if name and value:
                self._collected_cookies[name] = value

        # 从 API 请求中提取常见请求头
        for req in report.api_requests:
            for header in ["User-Agent", "Referer", "Origin", "X-Requested-With"]:
                if header in req.headers and header not in self._collected_headers:
                    self._collected_headers[header] = req.headers[header]

    # ==================== 状态和统计 ====================

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            "request_count": self._request_count,
            "error_count": self._error_count,
            "success_rate": (
                (self._request_count - self._error_count) / self._request_count * 100
                if self._request_count > 0
                else 0
            ),
            "cookies_collected": len(self._collected_cookies),
            "headers_collected": len(self._collected_headers),
            "last_analysis": self._last_analysis.site_name if self._last_analysis else None,
        }

    def get_status_report(self, use_emoji: bool = True) -> str:
        """
        获取状态报告（AI 友好格式）

        Args:
            use_emoji: 是否使用 emoji（Windows 终端可能不支持）
        """
        stats = self.get_stats()

        # emoji 或 ASCII 替代
        e = {
            "brain": "🧠" if use_emoji else "[Brain]",
            "stats": "📊" if use_emoji else "[Stats]",
            "cookie": "🍪" if use_emoji else "[Cookie]",
            "search": "🔍" if use_emoji else "[Search]",
        }

        lines = [
            f"# {e['brain']} Brain 状态报告",
            "",
            f"## {e['stats']} 统计数据",
            f"- 请求次数: {stats['request_count']}",
            f"- 错误次数: {stats['error_count']}",
            f"- 成功率: {stats['success_rate']:.1f}%",
            "",
            f"## {e['cookie']} 收集的数据",
            f"- Cookie 数量: {stats['cookies_collected']}",
            f"- Header 数量: {stats['headers_collected']}",
        ]

        if stats['last_analysis']:
            lines.extend([
                "",
                f"## {e['search']} 上次分析",
                f"- 网站: {stats['last_analysis']}",
                f"- 反爬等级: {self._last_analysis.anti_scrape_level}",
                f"- 推荐方案: {self._last_analysis.recommended_approach}",
            ])

        return "\n".join(lines)

    def reset(self) -> None:
        """重置状态"""
        self._last_report = None
        self._last_analysis = None
        self._collected_cookies.clear()
        self._collected_headers.clear()
        self._request_count = 0
        self._error_count = 0
        logger.info("Brain state reset")

    def get_last_analysis(self) -> SiteAnalysis | None:
        """获取上次的智能分析结果"""
        return self._last_analysis

    # ==================== 基础设施评估（自动建议） ====================

    def evaluate_requirements(
        self,
        url: str,
        target_count: int = 100,
        auto_analyze: bool = True,
    ) -> str:
        """
        评估任务需求并给出基础设施建议

        这是 Agent 自主评估的核心方法。根据目标URL和数据量，
        自动判断是否需要 Cookie池、代理池、签名服务等。

        Args:
            url: 目标URL
            target_count: 目标数据量
            auto_analyze: 是否自动进行网站分析

        Returns:
            人类可读的建议报告

        示例：
            # Agent 根据用户需求自动评估
            report = brain.evaluate_requirements(
                url="https://jd.com/search?q=手机",
                target_count=1000
            )
            print(report)  # 输出基础设施建议
        """
        logger.info(f"Evaluating requirements for: {url}")

        # 获取分析结果
        analysis_dict = None
        if auto_analyze and not self._last_analysis:
            try:
                analysis = self.smart_investigate(url)
                analysis_dict = {
                    "anti_scrape_level": analysis.anti_scrape_level,
                    "signatures_detected": [s.param_name for s in analysis.signature_params],
                    "cookies_detected": list(self._collected_cookies.keys()),
                }
            except Exception as e:
                logger.warning(f"Auto-analyze failed: {e}")
        elif self._last_analysis:
            analysis_dict = {
                "anti_scrape_level": self._last_analysis.anti_scrape_level,
                "signatures_detected": [s.param_name for s in self._last_analysis.signature_params],
                "cookies_detected": list(self._collected_cookies.keys()),
            }

        # 评估基础设施需求
        recommendations = self.infra_advisor.evaluate(
            url=url,
            target_count=target_count,
            analysis_result=analysis_dict,
        )

        return recommendations["summary"]

    def get_cookie_pool(self, domain: str) -> CookiePool:
        """获取指定域名的Cookie池"""
        return self.cookie_pool_manager.get_pool(domain)

    async def prepare_cookie_pool(
        self,
        url: str,
        count: int = 10,
        wait_seconds: float = 3.0,
    ) -> int:
        """
        为目标URL准备Cookie池（自动生成）

        Args:
            url: 目标URL
            count: 要生成的Cookie数量
            wait_seconds: 每次访问的等待时间

        Returns:
            成功生成的数量
        """
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace("www.", "")

        pool = self.cookie_pool_manager.get_pool(domain)
        return await pool.generate(count=count, url=url, wait_seconds=wait_seconds)

    def use_pool_cookie(self, url: str) -> bool:
        """
        从Cookie池获取Cookie并应用

        Args:
            url: 目标URL

        Returns:
            是否成功获取并应用Cookie
        """
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace("www.", "")

        pool = self.cookie_pool_manager.get_pool(domain)
        session = pool.get()

        if session:
            self._current_cookie_session = session
            self._collected_cookies.update(session.cookies)
            self._collected_headers["User-Agent"] = session.user_agent
            logger.info(f"Applied cookie from pool: {session.id}")
            return True

        return False

    def report_cookie_result(self, success: bool):
        """
        报告Cookie使用结果（用于反馈学习）

        Args:
            success: 是否成功
        """
        if self._current_cookie_session:
            from urllib.parse import urlparse
            domain = self._current_cookie_session.domain
            pool = self.cookie_pool_manager.get_pool(domain)

            if success:
                pool.mark_success(self._current_cookie_session.id)
            else:
                pool.mark_failed(self._current_cookie_session.id)

            self._current_cookie_session = None

    def cookie_pool_stats(self, url: str) -> dict:
        """获取Cookie池统计"""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace("www.", "")
        pool = self.cookie_pool_manager.get_pool(domain)
        return pool.stats()


# ==================== 便捷函数 ====================

def quick_investigate(url: str) -> str:
    """
    快速调查网站并返回摘要

    这是最简单的使用方式，返回可读的摘要。

    Args:
        url: 目标 URL

    Returns:
        摘要字符串，可直接由 AI 分析
    """
    brain = Brain(AgentConfig(proxy_enabled=False, headless=True))
    report = brain.investigate(url)
    return report.summary_for_ai()


def quick_smart_investigate(url: str) -> str:
    """
    快速智能调查（推荐）

    返回完整的 AI 分析报告，包括：
    - 网站识别
    - 反爬评估
    - 加密分析
    - 操作建议

    Args:
        url: 目标 URL

    Returns:
        AI 友好的完整分析报告
    """
    brain = Brain(AgentConfig(proxy_enabled=False, headless=True))
    analysis = brain.smart_investigate(url)
    return analysis.to_ai_report()


def quick_scrape(url: str, max_pages: int = 3) -> list[dict]:
    """
    快速抓取数据

    Args:
        url: 目标 URL
        max_pages: 最大翻页数

    Returns:
        数据列表
    """
    brain = Brain(AgentConfig(proxy_enabled=False, headless=True))
    result = brain.scrape_page(url, max_pages=max_pages)
    return result.data if result.success else []


def get_site_info(url: str) -> dict:
    """
    获取网站预设信息

    快速查看网站是否有预设配置及相关信息。

    Args:
        url: URL 或域名

    Returns:
        预设信息字典
    """
    return get_preset_info(url)
