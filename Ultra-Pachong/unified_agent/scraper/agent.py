"""
统一采集 Agent

整合以下功能到一个简洁的 Agent:
1. 自动获取网站信息并进行抓取
2. 配置快代理 API
3. 进行网络活动抓取
4. 执行真正的代码逻辑

使用示例:
    agent = ScraperAgent(config)

    # 方式1: 自动分析并抓取
    results = agent.scrape("https://example.com/products")

    # 方式2: 仅分析页面结构
    analysis = agent.analyze("https://example.com/products")

    # 方式3: 使用自定义选择器抓取
    results = agent.scrape_with_selector(
        "https://example.com/products",
        item_selector=".product-card",
        fields=[
            {"name": "title", "selector": "h2.title", "attr": "text"},
            {"name": "price", "selector": ".price", "attr": "text"},
            {"name": "url", "selector": "a", "attr": "href"},
        ]
    )
"""

from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from playwright.sync_api import sync_playwright, Page, BrowserContext, Browser

from ..core.config import AgentConfig
from ..infra.proxy import ProxyManager
from .stealth import apply_stealth

logger = logging.getLogger(__name__)


@dataclass
class FieldConfig:
    """字段配置"""
    name: str
    selector: str
    attr: str = "text"  # text, html, href, src, 或任意属性名
    regex: str | None = None  # 可选的正则提取


@dataclass
class PageAnalysis:
    """页面分析结果"""
    url: str
    title: str
    page_type: str  # product_list, article_list, search_results, detail, unknown
    lists: list[dict]  # 检测到的列表结构
    pagination: dict  # 分页信息
    screenshot_b64: str | None = None


@dataclass
class ScrapeResult:
    """抓取结果"""
    url: str
    success: bool
    data: list[dict[str, Any]] = field(default_factory=list)
    total_items: int = 0
    pages_scraped: int = 0
    duration_seconds: float = 0.0
    error: str | None = None
    screenshot_b64: str | None = None


class ScraperAgent:
    """
    统一采集 Agent

    自动处理:
    - 代理配置 (快代理)
    - 反检测 (stealth)
    - 页面分析
    - 数据提取
    - 分页处理
    """

    def __init__(self, config: AgentConfig | None = None):
        """
        初始化 Agent

        Args:
            config: Agent 配置，如果为 None 则使用默认配置
        """
        self.config = config or AgentConfig()
        self.proxy_manager = ProxyManager(self.config)
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    def analyze(self, url: str, take_screenshot: bool = True) -> PageAnalysis:
        """
        分析页面结构

        自动检测:
        - 列表容器和选择器
        - 字段类型 (价格、标题、图片等)
        - 分页模式

        Args:
            url: 要分析的 URL
            take_screenshot: 是否截图

        Returns:
            PageAnalysis 对象
        """
        with sync_playwright() as p:
            browser, context, page = self._create_browser_context(p)

            try:
                # 访问页面
                page.goto(url, wait_until="domcontentloaded", timeout=self.config.navigation_timeout_ms)

                # 滚动触发懒加载
                self._scroll_page(page)

                # 执行分析
                analysis_result = page.evaluate(ANALYSIS_JS)

                # 截图
                screenshot_b64 = None
                if take_screenshot:
                    screenshot_bytes = page.screenshot(full_page=False)
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

                return PageAnalysis(
                    url=page.url,
                    title=page.title(),
                    page_type=analysis_result.get("pageType", "unknown"),
                    lists=analysis_result.get("lists", []),
                    pagination=analysis_result.get("pagination", {}),
                    screenshot_b64=screenshot_b64,
                )

            finally:
                context.close()
                browser.close()

    def scrape(
        self,
        url: str,
        max_pages: int | None = None,
        take_screenshot: bool = False,
    ) -> ScrapeResult:
        """
        自动抓取页面数据

        自动分析页面结构并提取数据，支持分页。

        Args:
            url: 起始 URL
            max_pages: 最大翻页数 (默认使用配置值)
            take_screenshot: 是否截图

        Returns:
            ScrapeResult 对象
        """
        max_pages = max_pages or self.config.max_pages
        start_time = time.time()
        all_data: list[dict] = []
        pages_scraped = 0

        with sync_playwright() as p:
            browser, context, page = self._create_browser_context(p)

            try:
                # 访问页面
                page.goto(url, wait_until="domcontentloaded", timeout=self.config.navigation_timeout_ms)
                self._scroll_page(page)

                while pages_scraped < max_pages:
                    pages_scraped += 1

                    # 提取数据
                    rows = self._smart_extract(page)
                    all_data.extend(rows)

                    logger.info(f"Page {pages_scraped}: extracted {len(rows)} items")

                    # 尝试翻页
                    if pages_scraped < max_pages:
                        if not self._try_next_page(page):
                            break
                        time.sleep(self.config.page_load_delay)

                # 截图
                screenshot_b64 = None
                if take_screenshot:
                    screenshot_bytes = page.screenshot(full_page=False)
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

                return ScrapeResult(
                    url=url,
                    success=True,
                    data=all_data,
                    total_items=len(all_data),
                    pages_scraped=pages_scraped,
                    duration_seconds=round(time.time() - start_time, 2),
                    screenshot_b64=screenshot_b64,
                )

            except Exception as e:
                logger.error(f"Scrape failed: {e}")
                return ScrapeResult(
                    url=url,
                    success=False,
                    error=str(e),
                    pages_scraped=pages_scraped,
                    duration_seconds=round(time.time() - start_time, 2),
                )

            finally:
                context.close()
                browser.close()

    def scrape_with_selector(
        self,
        url: str,
        item_selector: str,
        fields: list[dict] | list[FieldConfig],
        max_pages: int | None = None,
    ) -> ScrapeResult:
        """
        使用自定义选择器抓取数据

        Args:
            url: 起始 URL
            item_selector: 列表项选择器
            fields: 字段配置列表
            max_pages: 最大翻页数

        Returns:
            ScrapeResult 对象
        """
        max_pages = max_pages or self.config.max_pages
        start_time = time.time()
        all_data: list[dict] = []
        pages_scraped = 0

        # 转换字段配置
        field_configs = []
        for f in fields:
            if isinstance(f, FieldConfig):
                field_configs.append({"name": f.name, "selector": f.selector, "attr": f.attr, "regex": f.regex})
            else:
                field_configs.append(f)

        with sync_playwright() as p:
            browser, context, page = self._create_browser_context(p)

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=self.config.navigation_timeout_ms)
                self._scroll_page(page)

                while pages_scraped < max_pages:
                    pages_scraped += 1

                    # 使用自定义选择器提取
                    rows = self._extract_with_selector(page, item_selector, field_configs)
                    all_data.extend(rows)

                    logger.info(f"Page {pages_scraped}: extracted {len(rows)} items")

                    # 尝试翻页
                    if pages_scraped < max_pages:
                        if not self._try_next_page(page):
                            break
                        time.sleep(self.config.page_load_delay)

                return ScrapeResult(
                    url=url,
                    success=True,
                    data=all_data,
                    total_items=len(all_data),
                    pages_scraped=pages_scraped,
                    duration_seconds=round(time.time() - start_time, 2),
                )

            except Exception as e:
                logger.error(f"Scrape failed: {e}")
                return ScrapeResult(
                    url=url,
                    success=False,
                    error=str(e),
                    pages_scraped=pages_scraped,
                    duration_seconds=round(time.time() - start_time, 2),
                )

            finally:
                context.close()
                browser.close()

    def save_session(self, session_name: str, page: Page | None = None) -> bool:
        """
        保存登录态

        Args:
            session_name: session 名称
            page: 如果提供则使用此页面的 context

        Returns:
            是否成功
        """
        try:
            session_path = self.config.sessions_dir / f"{session_name}.json"
            if page:
                page.context.storage_state(path=str(session_path))
            elif self._context:
                self._context.storage_state(path=str(session_path))
            else:
                return False
            logger.info(f"Session saved: {session_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def load_session(self, session_name: str) -> dict | None:
        """
        加载登录态

        Args:
            session_name: session 名称

        Returns:
            session 数据或 None
        """
        session_path = self.config.sessions_dir / f"{session_name}.json"
        if session_path.exists():
            return json.loads(session_path.read_text(encoding="utf-8"))
        return None

    def export_data(self, data: list[dict], filename: str, format: Literal["json", "csv"] = "json") -> Path:
        """
        导出数据

        Args:
            data: 数据列表
            filename: 文件名 (不含扩展名)
            format: 导出格式

        Returns:
            导出文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.config.data_dir / f"{filename}_{timestamp}.{format}"

        if format == "json":
            output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        elif format == "csv":
            import csv
            if data:
                with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)

        logger.info(f"Data exported: {output_path}")
        return output_path

    # ============ 私有方法 ============

    def _create_browser_context(self, playwright) -> tuple[Browser, BrowserContext, Page]:
        """创建浏览器上下文"""
        # 启动浏览器
        browser = playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
            ]
        )

        # 构建上下文参数
        context_kwargs = {
            "user_agent": self.config.get_random_user_agent(),
            "viewport": self.config.get_random_viewport(),
            "locale": self.config.locale,
            "timezone_id": self.config.timezone,
        }

        # 添加代理
        proxy_config = self.proxy_manager.get_playwright_proxy()
        if proxy_config:
            context_kwargs["proxy"] = proxy_config
            logger.info(f"Using proxy: {proxy_config['server']}")

        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        # 应用反检测
        if self.config.stealth_enabled:
            apply_stealth(page, self.config.locale)

        page.set_default_timeout(self.config.timeout_ms)

        return browser, context, page

    def _scroll_page(self, page: Page) -> None:
        """滚动页面触发懒加载"""
        time.sleep(1.5)

        # 多次滚动
        scroll_positions = [0.3, 0.5, 0.7, 0.9, 1.0]
        for pos in scroll_positions[:self.config.scroll_count]:
            try:
                page.evaluate(f"() => window.scrollTo(0, document.body.scrollHeight * {pos})")
                time.sleep(self.config.scroll_delay)
            except Exception:
                pass

        # 滚回顶部
        page.evaluate("() => window.scrollTo(0, 0)")
        time.sleep(0.5)

    def _smart_extract(self, page: Page) -> list[dict]:
        """智能提取数据"""
        try:
            rows = page.evaluate(SMART_EXTRACT_JS)
            if isinstance(rows, list) and len(rows) > 0:
                return rows
        except Exception:
            pass

        # 回退: 提取所有链接
        try:
            anchors = page.eval_on_selector_all(
                "a[href]",
                "els => els.slice(0, 200).map(a => ({title: (a.textContent||'').trim(), url: a.href}))",
            )
            seen = set()
            result = []
            for a in anchors:
                href = str(a.get("url") or "").strip()
                if not href or href in seen:
                    continue
                seen.add(href)
                result.append(a)
            return result
        except Exception:
            return []

    def _extract_with_selector(self, page: Page, item_selector: str, fields: list[dict]) -> list[dict]:
        """使用自定义选择器提取数据"""
        payload = {"itemSelector": item_selector, "fields": fields}
        return page.evaluate(SELECTOR_EXTRACT_JS, payload)

    def _try_next_page(self, page: Page) -> bool:
        """尝试翻到下一页"""
        # 常见的下一页按钮选择器
        next_patterns = [
            'a[rel="next"]',
            'button[aria-label*="next" i]',
            'a[aria-label*="next" i]',
            '[class*="next"]:not([class*="disabled"])',
            'a:has-text("Next")',
            'a:has-text("下一页")',
            'button:has-text("Next")',
            'button:has-text("下一页")',
        ]

        for pattern in next_patterns:
            try:
                next_btn = page.query_selector(pattern)
                if next_btn and next_btn.is_visible():
                    next_btn.click()
                    page.wait_for_load_state("networkidle", timeout=10000)
                    return True
            except Exception:
                continue

        # 尝试无限滚动
        try:
            prev_height = page.evaluate("() => document.body.scrollHeight")
            page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            new_height = page.evaluate("() => document.body.scrollHeight")
            if new_height > prev_height:
                return True
        except Exception:
            pass

        return False


# ============ JavaScript 代码 ============

ANALYSIS_JS = r"""
() => {
    const result = { lists: [], pagination: { mode: 'none' }, pageType: 'unknown' };

    // 检测页面类型
    const url = window.location.href.toLowerCase();
    const title = document.title.toLowerCase();
    if (/search|query|q=|keyword/.test(url) || /搜索|search/.test(title)) {
        result.pageType = 'search_results';
    } else if (/products?|catalog|shop|商品/.test(url + title)) {
        result.pageType = 'product_list';
    } else if (/articles?|news|blog|posts?|文章/.test(url + title)) {
        result.pageType = 'article_list';
    } else if (/detail|item\/\d|product\/\d|详情/.test(url)) {
        result.pageType = 'detail';
    }

    // 检测列表
    const containerSelectors = [
        '[class*="grid"] > *', '[class*="list"] > *', '[class*="card"]',
        '[class*="product"]', '[class*="item"]', 'ul > li', 'article'
    ];

    for (const selector of containerSelectors) {
        try {
            const els = document.querySelectorAll(selector);
            if (els.length >= 3) {
                const visible = Array.from(els).filter(el => {
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && style.visibility !== 'hidden';
                });
                if (visible.length >= 3) {
                    result.lists.push({
                        itemSelector: selector,
                        itemCount: visible.length,
                        sampleText: (visible[0].textContent || '').trim().slice(0, 100)
                    });
                }
            }
        } catch (e) {}
    }

    // 检测分页
    const nextPatterns = ['a[rel="next"]', '[class*="next"]:not([class*="disabled"])'];
    for (const pattern of nextPatterns) {
        try {
            const el = document.querySelector(pattern);
            if (el) {
                result.pagination = { mode: 'click', nextSelector: pattern };
                break;
            }
        } catch (e) {}
    }
    // 检测中文下一页
    if (result.pagination.mode === 'none') {
        const allLinks = document.querySelectorAll('a, button');
        for (const el of allLinks) {
            if ((el.textContent || '').includes('下一页')) {
                result.pagination = { mode: 'click', nextSelector: null, description: '下一页按钮' };
                break;
            }
        }
    }

    return result;
}
"""

SMART_EXTRACT_JS = r"""
() => {
    const getText = (el) => (el?.textContent || '').trim().replace(/\s+/g, ' ');

    const extractNumber = (text) => {
        const match = String(text || '').match(/([\d,]+\.?\d*)/);
        return match ? parseFloat(match[1].replace(/,/g, '')) : null;
    };

    const extractPrice = (text) => {
        const s = String(text || '').replace(/\s+/g, ' ').trim();
        let m = s.match(/\b(USD|EUR|CNY|RMB|HKD)\s*([0-9.,]+)\b/i);
        if (m) return extractNumber(m[2]);
        m = s.match(/([$€£¥])\s*([0-9.,]+)/);
        if (m) return extractNumber(m[2]);
        return null;
    };

    // 查找卡片容器
    const containerSelectors = [
        '[class*="grid"] > *', '[class*="list"] > *', '[class*="card"]',
        '[class*="product"]', '[class*="item"]', 'ul > li', 'article'
    ];

    let cards = [];
    for (const selector of containerSelectors) {
        const els = document.querySelectorAll(selector);
        if (els.length >= 3) {
            const visible = Array.from(els).filter(el => {
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' &&
                       (getText(el).length > 10 || el.querySelector('img'));
            });
            if (visible.length > cards.length) cards = visible;
        }
    }

    if (cards.length >= 3) {
        return cards.slice(0, 200).map(card => {
            const data = {};
            const mainLink = card.querySelector('a[href]');
            if (mainLink) {
                data.url = mainLink.href;
                const linkText = getText(mainLink);
                if (linkText && linkText.length < 200) data.title = linkText;
            }

            const heading = card.querySelector('h1, h2, h3, h4, [class*="title"], [class*="name"]');
            if (heading) {
                const headingText = getText(heading);
                if (headingText && headingText.length < 200) data.title = headingText;
            }

            const priceEl = card.querySelector('[class*="price"], [class*="cost"], [data-price]');
            if (priceEl) {
                const priceText = getText(priceEl);
                data.price = extractPrice(priceText) || extractNumber(priceText);
                data.price_text = priceText;
            }

            const img = card.querySelector('img[src]');
            if (img) {
                data.image = img.src;
                if (img.alt) data.image_alt = img.alt;
            }

            if (!data.title) data.title = getText(card).slice(0, 200);
            data.full_text = getText(card).slice(0, 500);

            return data;
        });
    }

    // 回退: 提取链接
    const anchors = document.querySelectorAll('a[href]');
    const seen = new Set();
    const results = [];
    for (const a of anchors) {
        if (results.length >= 200) break;
        const href = a.href;
        if (!href || seen.has(href)) continue;
        seen.add(href);
        const text = getText(a);
        if (text) results.push({ title: text, url: href });
    }
    return results;
}
"""

SELECTOR_EXTRACT_JS = r"""
(payload) => {
    const normalize = (s) => String(s || '').trim().replace(/\s+/g, ' ');
    const getBySelector = (root, sel) => { try { return root.querySelector(sel); } catch { return null; } };

    const getAttrValue = (el, attr) => {
        if (!el) return null;
        const a = String(attr || 'text');
        if (a === 'text') return normalize(el.textContent);
        if (a === 'html') return String(el.innerHTML || '');
        if (a === 'href') return el.href || el.getAttribute('href');
        if (a === 'src') return el.src || el.getAttribute('src');
        return el.getAttribute(a);
    };

    const items = Array.from(document.querySelectorAll(payload.itemSelector)).slice(0, 200);
    return items.map((item) => {
        const out = {};
        for (const f of payload.fields) {
            const el = f.selector ? getBySelector(item, f.selector) : item;
            let v = getAttrValue(el, f.attr);
            if (f.regex && v) {
                try {
                    const r = new RegExp(f.regex);
                    const m = v.match(r);
                    v = m ? (m[1] ?? m[0]) : null;
                } catch {}
            }
            out[f.name] = v;
        }
        if (!out.url) {
            const a = item.querySelector('a[href]');
            if (a) out.url = a.href;
        }
        return out;
    });
}
"""
