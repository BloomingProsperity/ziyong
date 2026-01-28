"""
智能信息收集器

自动收集目标网站的所有关键信息，供 AI 分析：
- 所有网络请求 (XHR/Fetch/API)
- Cookie 和 Headers
- 页面结构和元素
- 加密参数识别
- 截图

使用方式：
    collector = InfoCollector(config)
    report = collector.collect("https://example.com")
    # 将 report 发送给 Claude 分析
"""

from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import sync_playwright, Page, Request, Response, Route

from ..core.config import AgentConfig
from .stealth import apply_stealth


@dataclass
class CapturedRequest:
    """捕获的请求"""
    url: str
    method: str
    headers: dict[str, str]
    post_data: str | None
    resource_type: str
    timestamp: str

    # 解析后的信息
    query_params: dict[str, list[str]] = field(default_factory=dict)
    body_params: dict[str, Any] = field(default_factory=dict)
    suspicious_params: list[str] = field(default_factory=list)  # 可能是签名的参数


@dataclass
class CapturedResponse:
    """捕获的响应"""
    url: str
    status: int
    headers: dict[str, str]
    body_preview: str  # 前 2000 字符
    content_type: str
    timestamp: str


@dataclass
class PageElement:
    """页面元素"""
    tag: str
    selector: str
    text: str
    attributes: dict[str, str]
    is_interactive: bool  # 是否可交互（按钮、链接、输入框等）


@dataclass
class SiteReport:
    """网站信息收集报告"""
    url: str
    title: str
    timestamp: str

    # Cookie 信息
    cookies: list[dict[str, Any]]

    # 网络请求
    api_requests: list[CapturedRequest]  # XHR/Fetch 请求
    all_requests: list[CapturedRequest]  # 所有请求

    # 响应信息
    api_responses: list[CapturedResponse]

    # 页面信息
    page_html: str  # 完整 HTML
    interactive_elements: list[PageElement]  # 可交互元素
    forms: list[dict[str, Any]]  # 表单信息

    # 识别的模式
    detected_encryption_params: list[str]  # 可能的加密参数名
    detected_api_patterns: list[dict[str, Any]]  # API 模式

    # 截图
    screenshot_b64: str | None

    # 控制台日志
    console_logs: list[str]

    # 错误
    errors: list[str]

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "url": self.url,
            "title": self.title,
            "timestamp": self.timestamp,
            "cookies": self.cookies,
            "api_requests": [
                {
                    "url": r.url,
                    "method": r.method,
                    "headers": r.headers,
                    "post_data": r.post_data,
                    "query_params": r.query_params,
                    "body_params": r.body_params,
                    "suspicious_params": r.suspicious_params,
                }
                for r in self.api_requests
            ],
            "api_responses": [
                {
                    "url": r.url,
                    "status": r.status,
                    "content_type": r.content_type,
                    "body_preview": r.body_preview,
                }
                for r in self.api_responses
            ],
            "interactive_elements_count": len(self.interactive_elements),
            "interactive_elements": [
                {"tag": e.tag, "selector": e.selector, "text": e.text[:100]}
                for e in self.interactive_elements[:50]
            ],
            "forms": self.forms,
            "detected_encryption_params": self.detected_encryption_params,
            "detected_api_patterns": self.detected_api_patterns,
            "console_logs": self.console_logs[-50:],  # 最后 50 条
            "errors": self.errors,
            "has_screenshot": bool(self.screenshot_b64),
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def summary_for_ai(self) -> str:
        """生成供 AI 分析的摘要（优化版）"""
        lines = [
            "# [报告] 网站信息收集报告",
            "",
            "## [信息] 基本信息",
            f"| 属性 | 值 |",
            f"|------|-----|",
            f"| URL | `{self.url}` |",
            f"| 标题 | {self.title} |",
            f"| 收集时间 | {self.timestamp} |",
            f"| API 请求数 | {len(self.api_requests)} |",
            f"| 加密参数数 | {len(self.detected_encryption_params)} |",
            "",
        ]

        # Cookie 摘要（分组展示重要的）
        lines.append(f"## [Cookie] Cookie 摘要 (共 {len(self.cookies)} 个)")
        if self.cookies:
            important_cookies = []
            other_cookies = []
            for c in self.cookies:
                name = c.get('name', '')
                if any(kw in name.lower() for kw in ['token', 'session', 'user', 'auth', 'login', 'key']):
                    important_cookies.append(c)
                else:
                    other_cookies.append(c)

            if important_cookies:
                lines.append("### [关键] 关键 Cookie")
                for c in important_cookies[:5]:
                    val = str(c.get('value', ''))[:30]
                    lines.append(f"- `{c.get('name')}`: `{val}{'...' if len(str(c.get('value', ''))) > 30 else ''}`")

            if other_cookies:
                lines.append(f"\n其他 Cookie: {', '.join(c.get('name', '') for c in other_cookies[:10])}")
        lines.append("")

        # API 请求摘要（更结构化）
        lines.append(f"## [API] API 请求 (共 {len(self.api_requests)} 个)")
        if self.api_requests:
            lines.append("")
            for i, r in enumerate(self.api_requests[:15], 1):
                # 简化 URL 显示
                parsed = urlparse(r.url)
                short_url = f"{parsed.netloc}{parsed.path[:50]}{'...' if len(parsed.path) > 50 else ''}"

                lines.append(f"### 请求 {i}: `{r.method}` {short_url}")

                # 参数表格
                if r.query_params or r.body_params:
                    lines.append("| 参数名 | 类型 | 值预览 | 可疑 |")
                    lines.append("|--------|------|--------|------|")

                    all_params = []
                    for k, v in r.query_params.items():
                        val = str(v[0] if isinstance(v, list) else v)[:30]
                        suspicious = "[!]" if k in r.suspicious_params else ""
                        all_params.append(f"| `{k}` | Query | `{val}` | {suspicious} |")

                    for k, v in r.body_params.items() if isinstance(r.body_params, dict) else []:
                        val = str(v)[:30]
                        suspicious = "[!]" if k in r.suspicious_params else ""
                        all_params.append(f"| `{k}` | Body | `{val}` | {suspicious} |")

                    lines.extend(all_params[:10])
                    if len(all_params) > 10:
                        lines.append(f"| ... | | 还有 {len(all_params) - 10} 个参数 | |")

                lines.append("")

            if len(self.api_requests) > 15:
                lines.append(f"*还有 {len(self.api_requests) - 15} 个 API 请求未显示*")
        lines.append("")

        # 加密参数（醒目展示）
        lines.append("## [加密] 检测到的加密参数")
        if self.detected_encryption_params:
            lines.append("```")
            lines.append(", ".join(self.detected_encryption_params))
            lines.append("```")
            lines.append("")
            lines.append("**建议**: 这些参数可能需要特殊处理（签名、Token等）")
        else:
            lines.append("[OK] 未检测到明显的加密参数")
        lines.append("")

        # 可交互元素（按类型分组）
        lines.append(f"## [元素] 可交互元素 (共 {len(self.interactive_elements)} 个)")
        if self.interactive_elements:
            by_tag = {}
            for e in self.interactive_elements:
                tag = e.tag
                if tag not in by_tag:
                    by_tag[tag] = []
                by_tag[tag].append(e)

            for tag, elements in list(by_tag.items())[:5]:
                lines.append(f"\n### {tag.upper()} ({len(elements)} 个)")
                for e in elements[:5]:
                    text = e.text[:40] if e.text else "(无文本)"
                    lines.append(f"- `{e.selector}`: {text}")
                if len(elements) > 5:
                    lines.append(f"  *还有 {len(elements) - 5} 个...*")
        lines.append("")

        # 表单信息
        if self.forms:
            lines.append(f"## [表单] 表单 (共 {len(self.forms)} 个)")
            for i, f in enumerate(self.forms[:5], 1):
                action = f.get('action', '(无)')[:50]
                method = f.get('method', 'GET')
                fields = f.get('fields', [])
                lines.append(f"\n### 表单 {i}")
                lines.append(f"- **Action**: `{action}`")
                lines.append(f"- **Method**: {method}")
                lines.append(f"- **字段**: {', '.join(field.get('name', '?') for field in fields[:8])}")
            lines.append("")

        # 错误和警告
        if self.errors:
            lines.append("## [警告] 错误和警告")
            for e in self.errors[:5]:
                lines.append(f"- {e[:100]}")
            if len(self.errors) > 5:
                lines.append(f"*还有 {len(self.errors) - 5} 个错误*")
            lines.append("")

        # 快速建议
        lines.extend([
            "---",
            "## [建议] 快速建议",
        ])

        if len(self.api_requests) > 0:
            lines.append("- [OK] 检测到 API 请求，可以尝试直接调用")
        if self.detected_encryption_params:
            lines.append("- [!] 有加密参数，可能需要分析签名算法")
        if any('login' in c.get('name', '').lower() for c in self.cookies):
            lines.append("- [登录] 检测到登录态，建议保存 Cookie")
        if len(self.interactive_elements) > 50:
            lines.append("- [页面] 页面元素较多，建议使用选择器定位")

        return "\n".join(lines)

    def get_api_summary(self) -> str:
        """获取 API 摘要（简洁版）"""
        lines = ["# API 列表", ""]
        for r in self.api_requests:
            parsed = urlparse(r.url)
            lines.append(f"- `{r.method}` {parsed.path}")
            if r.suspicious_params:
                lines.append(f"  [!] 可疑参数: {r.suspicious_params}")
        return "\n".join(lines)

    def get_cookies_dict(self) -> dict[str, str]:
        """获取 Cookie 字典"""
        return {c.get('name'): c.get('value') for c in self.cookies if c.get('name')}


class InfoCollector:
    """智能信息收集器"""

    # 可能是加密/签名参数的关键词
    ENCRYPTION_KEYWORDS = [
        'sign', 'signature', 'token', 'h5st', 'timestamp', 'nonce',
        'encrypt', 'hash', 'key', 'secret', 'auth', 'ticket',
        '_t', '_s', '_sign', '_token', 'appkey', 'appsecret',
    ]

    def __init__(self, config: AgentConfig | None = None):
        self.config = config or AgentConfig()
        self._requests: list[CapturedRequest] = []
        self._responses: list[CapturedResponse] = []
        self._console_logs: list[str] = []
        self._errors: list[str] = []

    def collect(
        self,
        url: str,
        wait_seconds: float = 5.0,
        scroll: bool = True,
        click_elements: list[str] | None = None,
        take_screenshot: bool = True,
    ) -> SiteReport:
        """
        收集网站信息

        Args:
            url: 目标 URL
            wait_seconds: 等待时间（让 AJAX 请求完成）
            scroll: 是否滚动页面
            click_elements: 要点击的元素选择器列表
            take_screenshot: 是否截图

        Returns:
            SiteReport 对象
        """
        self._requests = []
        self._responses = []
        self._console_logs = []
        self._errors = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.config.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )

            context = browser.new_context(
                user_agent=self.config.get_random_user_agent(),
                viewport=self.config.get_random_viewport(),
                locale=self.config.locale,
                timezone_id=self.config.timezone,
            )

            page = context.new_page()

            # 应用反检测
            if self.config.stealth_enabled:
                apply_stealth(page, self.config.locale)

            # 监听网络请求
            page.on("request", self._on_request)
            page.on("response", self._on_response)

            # 监听控制台
            page.on("console", lambda msg: self._console_logs.append(f"[{msg.type}] {msg.text}"))

            # 监听错误
            page.on("pageerror", lambda err: self._errors.append(str(err)))

            try:
                # 访问页面
                page.goto(url, wait_until="domcontentloaded", timeout=self.config.navigation_timeout_ms)

                # 等待初始加载
                time.sleep(2)

                # 滚动页面
                if scroll:
                    self._scroll_page(page)

                # 点击指定元素
                if click_elements:
                    for selector in click_elements:
                        try:
                            el = page.query_selector(selector)
                            if el and el.is_visible():
                                el.click()
                                time.sleep(1)
                        except Exception as e:
                            self._errors.append(f"Click failed ({selector}): {e}")

                # 等待 AJAX 请求完成
                time.sleep(wait_seconds)

                # 收集信息
                cookies = context.cookies()
                page_html = page.content()
                interactive_elements = self._collect_interactive_elements(page)
                forms = self._collect_forms(page)

                # 截图
                screenshot_b64 = None
                if take_screenshot:
                    screenshot_bytes = page.screenshot(full_page=True)
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

                # 分析请求，识别 API 和加密参数
                api_requests = [r for r in self._requests if r.resource_type in ('xhr', 'fetch')]
                detected_params = self._detect_encryption_params(api_requests)
                api_patterns = self._detect_api_patterns(api_requests)

                return SiteReport(
                    url=page.url,
                    title=page.title(),
                    timestamp=datetime.now().isoformat(),
                    cookies=cookies,
                    api_requests=api_requests,
                    all_requests=self._requests,
                    api_responses=[r for r in self._responses if '/api' in r.url or r.content_type.startswith('application/json')],
                    page_html=page_html,
                    interactive_elements=interactive_elements,
                    forms=forms,
                    detected_encryption_params=detected_params,
                    detected_api_patterns=api_patterns,
                    screenshot_b64=screenshot_b64,
                    console_logs=self._console_logs,
                    errors=self._errors,
                )

            finally:
                context.close()
                browser.close()

    def collect_with_interaction(
        self,
        url: str,
        actions: list[dict[str, Any]],
        wait_between_actions: float = 1.0,
    ) -> SiteReport:
        """
        带交互的信息收集

        Args:
            url: 目标 URL
            actions: 动作列表，每个动作是一个字典:
                - {"type": "click", "selector": ".button"}
                - {"type": "fill", "selector": "#input", "value": "text"}
                - {"type": "wait", "seconds": 2}
                - {"type": "scroll"}
            wait_between_actions: 动作间隔

        Returns:
            SiteReport 对象
        """
        self._requests = []
        self._responses = []
        self._console_logs = []
        self._errors = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.config.headless,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = browser.new_context(
                user_agent=self.config.get_random_user_agent(),
                viewport=self.config.get_random_viewport(),
                locale=self.config.locale,
                timezone_id=self.config.timezone,
            )

            page = context.new_page()

            if self.config.stealth_enabled:
                apply_stealth(page, self.config.locale)

            page.on("request", self._on_request)
            page.on("response", self._on_response)
            page.on("console", lambda msg: self._console_logs.append(f"[{msg.type}] {msg.text}"))

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=self.config.navigation_timeout_ms)
                time.sleep(2)

                # 执行动作序列
                for action in actions:
                    action_type = action.get("type")

                    try:
                        if action_type == "click":
                            selector = action.get("selector")
                            el = page.query_selector(selector)
                            if el and el.is_visible():
                                el.click()

                        elif action_type == "fill":
                            selector = action.get("selector")
                            value = action.get("value", "")
                            page.fill(selector, value)

                        elif action_type == "wait":
                            seconds = action.get("seconds", 1)
                            time.sleep(seconds)

                        elif action_type == "scroll":
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                        elif action_type == "hover":
                            selector = action.get("selector")
                            page.hover(selector)

                        time.sleep(wait_between_actions)

                    except Exception as e:
                        self._errors.append(f"Action failed ({action}): {e}")

                # 收集最终信息
                cookies = context.cookies()
                page_html = page.content()
                interactive_elements = self._collect_interactive_elements(page)
                forms = self._collect_forms(page)

                screenshot_bytes = page.screenshot(full_page=True)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

                api_requests = [r for r in self._requests if r.resource_type in ('xhr', 'fetch')]
                detected_params = self._detect_encryption_params(api_requests)
                api_patterns = self._detect_api_patterns(api_requests)

                return SiteReport(
                    url=page.url,
                    title=page.title(),
                    timestamp=datetime.now().isoformat(),
                    cookies=cookies,
                    api_requests=api_requests,
                    all_requests=self._requests,
                    api_responses=[r for r in self._responses if r.content_type.startswith('application/json')],
                    page_html=page_html,
                    interactive_elements=interactive_elements,
                    forms=forms,
                    detected_encryption_params=detected_params,
                    detected_api_patterns=api_patterns,
                    screenshot_b64=screenshot_b64,
                    console_logs=self._console_logs,
                    errors=self._errors,
                )

            finally:
                context.close()
                browser.close()

    def _on_request(self, request: Request) -> None:
        """处理请求"""
        try:
            parsed = urlparse(request.url)
            query_params = parse_qs(parsed.query)

            # 解析 POST body
            body_params = {}
            post_data = request.post_data
            if post_data:
                try:
                    body_params = json.loads(post_data)
                except:
                    try:
                        body_params = dict(parse_qs(post_data))
                    except:
                        pass

            # 识别可疑参数
            suspicious = []
            all_params = list(query_params.keys()) + list(body_params.keys())
            for param in all_params:
                param_lower = param.lower()
                if any(kw in param_lower for kw in self.ENCRYPTION_KEYWORDS):
                    suspicious.append(param)

            captured = CapturedRequest(
                url=request.url,
                method=request.method,
                headers=dict(request.headers),
                post_data=post_data,
                resource_type=request.resource_type,
                timestamp=datetime.now().isoformat(),
                query_params=query_params,
                body_params=body_params,
                suspicious_params=suspicious,
            )
            self._requests.append(captured)

        except Exception as e:
            self._errors.append(f"Request capture error: {e}")

    def _on_response(self, response: Response) -> None:
        """处理响应"""
        try:
            content_type = response.headers.get("content-type", "")

            # 只捕获 JSON 响应的内容
            body_preview = ""
            if "json" in content_type:
                try:
                    body = response.text()
                    body_preview = body[:2000]
                except:
                    pass

            captured = CapturedResponse(
                url=response.url,
                status=response.status,
                headers=dict(response.headers),
                body_preview=body_preview,
                content_type=content_type,
                timestamp=datetime.now().isoformat(),
            )
            self._responses.append(captured)

        except Exception as e:
            self._errors.append(f"Response capture error: {e}")

    def _scroll_page(self, page: Page) -> None:
        """滚动页面"""
        for pos in [0.3, 0.5, 0.7, 1.0]:
            try:
                page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {pos})")
                time.sleep(0.8)
            except:
                pass
        page.evaluate("window.scrollTo(0, 0)")

    def _collect_interactive_elements(self, page: Page) -> list[PageElement]:
        """收集可交互元素"""
        js = """
        () => {
            const elements = [];
            const selectors = 'a, button, input, select, textarea, [onclick], [role="button"], [tabindex]';

            document.querySelectorAll(selectors).forEach((el, index) => {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) return;

                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') return;

                // 生成选择器
                let selector = el.tagName.toLowerCase();
                if (el.id) {
                    selector = '#' + el.id;
                } else if (el.className) {
                    const classes = String(el.className).split(/\\s+/).filter(c => c && c.length < 30).slice(0, 2);
                    if (classes.length) selector += '.' + classes.join('.');
                }

                elements.push({
                    tag: el.tagName.toLowerCase(),
                    selector: selector,
                    text: (el.textContent || el.value || '').trim().slice(0, 100),
                    attributes: {
                        id: el.id || '',
                        class: el.className || '',
                        type: el.type || '',
                        name: el.name || '',
                        href: el.href || '',
                        placeholder: el.placeholder || '',
                    }
                });
            });

            return elements.slice(0, 200);
        }
        """
        try:
            raw = page.evaluate(js)
            return [
                PageElement(
                    tag=e["tag"],
                    selector=e["selector"],
                    text=e["text"],
                    attributes=e["attributes"],
                    is_interactive=True,
                )
                for e in raw
            ]
        except:
            return []

    def _collect_forms(self, page: Page) -> list[dict]:
        """收集表单信息"""
        js = """
        () => {
            const forms = [];
            document.querySelectorAll('form').forEach(form => {
                const fields = [];
                form.querySelectorAll('input, select, textarea').forEach(field => {
                    fields.push({
                        tag: field.tagName.toLowerCase(),
                        name: field.name || '',
                        type: field.type || '',
                        id: field.id || '',
                        required: field.required,
                    });
                });

                forms.push({
                    action: form.action || '',
                    method: form.method || 'GET',
                    id: form.id || '',
                    fields: fields,
                });
            });
            return forms;
        }
        """
        try:
            return page.evaluate(js)
        except:
            return []

    def _detect_encryption_params(self, requests: list[CapturedRequest]) -> list[str]:
        """检测可能的加密参数"""
        all_suspicious = set()
        for req in requests:
            all_suspicious.update(req.suspicious_params)
        return list(all_suspicious)

    def _detect_api_patterns(self, requests: list[CapturedRequest]) -> list[dict]:
        """检测 API 模式"""
        patterns = []
        seen_urls = set()

        for req in requests:
            parsed = urlparse(req.url)
            base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

            if base_url in seen_urls:
                continue
            seen_urls.add(base_url)

            patterns.append({
                "url": base_url,
                "method": req.method,
                "params": list(req.query_params.keys()) + list(req.body_params.keys()),
                "suspicious": req.suspicious_params,
                "has_body": bool(req.post_data),
            })

        return patterns[:30]  # 最多 30 个
