"""
智能分析模块

自动分析网站特征，给出：
- 网站类型识别
- 反爬强度评估
- 加密参数深度分析
- 建议的抓取策略
- 下一步操作建议

这个模块的输出是专门为 AI 设计的，便于 Claude 理解和决策。
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlparse


@dataclass
class SignatureAnalysis:
    """签名参数分析结果"""
    param_name: str
    param_value: str
    pattern_type: Literal["timestamp", "hash", "token", "nonce", "unknown"]
    length: int
    charset: str  # "hex", "base64", "numeric", "alphanumeric", "mixed"
    appears_dynamic: bool  # 是否看起来是动态生成的
    possible_algorithm: str | None  # 可能的算法
    confidence: float  # 置信度 0-1
    notes: str


@dataclass
class SiteAnalysis:
    """网站深度分析结果"""
    # 基本信息
    url: str
    domain: str
    site_type: str  # "ecommerce", "social", "news", "video", "unknown"
    site_name: str | None  # 识别出的网站名称

    # 反爬评估
    anti_scrape_level: Literal["low", "medium", "high", "extreme"]
    anti_scrape_features: list[str]  # 检测到的反爬特征

    # 登录状态
    login_required: bool
    login_detected: bool  # 是否检测到已登录
    login_suggestion: str | None

    # API 分析
    api_endpoints: list[dict[str, Any]]
    main_data_api: dict[str, Any] | None  # 主要数据接口

    # 签名分析
    signature_params: list[SignatureAnalysis]
    encryption_complexity: Literal["none", "simple", "moderate", "complex"]

    # 建议
    recommended_approach: str  # "direct_api", "browser_scrape", "hybrid", "need_reverse"
    next_steps: list[str]  # 建议的下一步操作
    warnings: list[str]  # 警告信息

    # 预设匹配
    matched_preset: str | None  # 匹配到的预设配置名称

    def to_ai_report(self, use_emoji: bool = False) -> str:
        """
        生成 AI 友好的分析报告

        Args:
            use_emoji: 是否使用 emoji（Windows 终端可能不支持）
        """
        # 根据 use_emoji 选择符号
        if use_emoji:
            e = {"search": "🔍", "info": "📋", "shield": "🛡️", "lock": "🔐",
                 "api": "🔌", "bulb": "💡", "warn": "⚠️", "yes": "✅", "no": "❌",
                 "low": "🟢", "medium": "🟡", "high": "🟠", "extreme": "🔴", "unknown": "⚪"}
        else:
            e = {"search": "[分析]", "info": "[信息]", "shield": "[反爬]", "lock": "[登录]",
                 "api": "[API]", "bulb": "[建议]", "warn": "[注意]", "yes": "[是]", "no": "[否]",
                 "low": "[低]", "medium": "[中]", "high": "[高]", "extreme": "[极高]", "unknown": "[-]"}

        lines = [
            f"# {e['search']} 网站智能分析报告",
            "",
            f"## {e['info']} 基本信息",
            f"- **域名**: {self.domain}",
            f"- **网站类型**: {self.site_type}",
            f"- **识别为**: {self.site_name or '未知网站'}",
        ]

        if self.matched_preset:
            lines.append(f"- **匹配预设**: {e['yes']} {self.matched_preset}")
        lines.append("")

        # 反爬评估
        level_mark = e.get(self.anti_scrape_level, e['unknown'])
        lines.extend([
            f"## {e['shield']} 反爬评估",
            f"- **防护等级**: {level_mark} {self.anti_scrape_level.upper()}",
        ])
        if self.anti_scrape_features:
            lines.append("- **检测到的防护措施**:")
            for feature in self.anti_scrape_features:
                lines.append(f"  - {feature}")
        lines.append("")

        # 登录状态
        login_status = e['yes'] if self.login_detected else e['no']
        lines.extend([
            f"## {e['lock']} 登录状态",
            f"- **需要登录**: {'是' if self.login_required else '否'}",
            f"- **当前状态**: {'已登录 ' + login_status if self.login_detected else '未登录 ' + e['no']}",
        ])
        if self.login_suggestion:
            lines.append(f"- **建议**: {self.login_suggestion}")
        lines.append("")

        # API 分析
        lines.append(f"## {e['api']} API 分析")
        if self.main_data_api:
            lines.extend([
                "### 主要数据接口",
                f"- **URL**: `{self.main_data_api.get('url', 'N/A')}`",
                f"- **方法**: {self.main_data_api.get('method', 'GET')}",
                f"- **参数**: {json.dumps(self.main_data_api.get('params', []), ensure_ascii=False)}",
            ])
        lines.append(f"\n共发现 **{len(self.api_endpoints)}** 个 API 端点")
        lines.append("")

        # 签名分析
        lines.extend([
            f"## {e['lock']} 加密/签名分析",
            f"- **复杂度**: {self.encryption_complexity}",
        ])
        if self.signature_params:
            lines.append("- **可疑参数**:")
            for sig in self.signature_params:
                lines.append(f"  - `{sig.param_name}`: {sig.pattern_type}")
                if sig.possible_algorithm:
                    lines.append(f"    可能算法: {sig.possible_algorithm}")
                lines.append(f"    置信度: {sig.confidence:.0%}")
        else:
            lines.append(f"- 未检测到明显的加密参数 {e['yes']}")
        lines.append("")

        # 建议
        approach_desc = {
            "direct_api": "直接调用 API（最高效）",
            "browser_scrape": "浏览器渲染抓取",
            "hybrid": "混合模式（浏览器获取签名 + API 抓取）",
            "need_reverse": "需要逆向分析加密算法",
        }
        lines.extend([
            f"## {e['bulb']} 建议",
            f"### 推荐方案: {approach_desc.get(self.recommended_approach, self.recommended_approach)}",
            "",
            "### 下一步操作:",
        ])
        for i, step in enumerate(self.next_steps, 1):
            lines.append(f"{i}. {step}")

        if self.warnings:
            lines.extend([
                "",
                f"### {e['warn']} 注意事项:",
            ])
            for warning in self.warnings:
                lines.append(f"- {warning}")

        return "\n".join(lines)


class SmartAnalyzer:
    """智能分析器"""

    # 常见网站识别规则
    SITE_PATTERNS = {
        "jd.com": {"name": "京东", "type": "ecommerce", "anti_level": "extreme"},
        "taobao.com": {"name": "淘宝", "type": "ecommerce", "anti_level": "extreme"},
        "tmall.com": {"name": "天猫", "type": "ecommerce", "anti_level": "extreme"},
        "pinduoduo.com": {"name": "拼多多", "type": "ecommerce", "anti_level": "high"},
        "1688.com": {"name": "1688", "type": "ecommerce", "anti_level": "high"},
        "amazon": {"name": "亚马逊", "type": "ecommerce", "anti_level": "high"},
        "douyin.com": {"name": "抖音", "type": "video", "anti_level": "extreme"},
        "kuaishou.com": {"name": "快手", "type": "video", "anti_level": "extreme"},
        "xiaohongshu.com": {"name": "小红书", "type": "social", "anti_level": "high"},
        "weibo.com": {"name": "微博", "type": "social", "anti_level": "medium"},
        "zhihu.com": {"name": "知乎", "type": "social", "anti_level": "medium"},
        "bilibili.com": {"name": "B站", "type": "video", "anti_level": "medium"},
        "dangdang.com": {"name": "当当", "type": "ecommerce", "anti_level": "low"},
        "suning.com": {"name": "苏宁", "type": "ecommerce", "anti_level": "medium"},
    }

    # 加密参数特征
    SIGNATURE_PATTERNS = {
        "h5st": {"type": "hash", "algorithm": "京东 H5ST 签名", "complexity": "complex"},
        "sign": {"type": "hash", "algorithm": "通用签名", "complexity": "moderate"},
        "_sign": {"type": "hash", "algorithm": "通用签名", "complexity": "moderate"},
        "signature": {"type": "hash", "algorithm": "通用签名", "complexity": "moderate"},
        "token": {"type": "token", "algorithm": "Token 认证", "complexity": "simple"},
        "timestamp": {"type": "timestamp", "algorithm": None, "complexity": "simple"},
        "_t": {"type": "timestamp", "algorithm": None, "complexity": "simple"},
        "nonce": {"type": "nonce", "algorithm": "随机数", "complexity": "simple"},
        "appkey": {"type": "token", "algorithm": "App Key", "complexity": "simple"},
    }

    def analyze(self, report) -> SiteAnalysis:
        """
        深度分析收集到的信息

        Args:
            report: SiteReport 对象（来自 InfoCollector）

        Returns:
            SiteAnalysis 对象
        """
        from .collector import SiteReport

        parsed = urlparse(report.url)
        domain = parsed.netloc.lower()

        # 识别网站
        site_info = self._identify_site(domain)

        # 分析反爬特征
        anti_scrape = self._analyze_anti_scrape(report, site_info)

        # 分析登录状态
        login_info = self._analyze_login(report)

        # 分析 API
        api_analysis = self._analyze_apis(report)

        # 分析签名参数
        signature_analysis = self._analyze_signatures(report)

        # 生成建议
        recommendations = self._generate_recommendations(
            site_info, anti_scrape, login_info, api_analysis, signature_analysis
        )

        return SiteAnalysis(
            url=report.url,
            domain=domain,
            site_type=site_info.get("type", "unknown"),
            site_name=site_info.get("name"),
            anti_scrape_level=anti_scrape["level"],
            anti_scrape_features=anti_scrape["features"],
            login_required=login_info["required"],
            login_detected=login_info["detected"],
            login_suggestion=login_info["suggestion"],
            api_endpoints=api_analysis["endpoints"],
            main_data_api=api_analysis["main_api"],
            signature_params=signature_analysis["params"],
            encryption_complexity=signature_analysis["complexity"],
            recommended_approach=recommendations["approach"],
            next_steps=recommendations["steps"],
            warnings=recommendations["warnings"],
            matched_preset=site_info.get("preset"),
        )

    def _identify_site(self, domain: str) -> dict:
        """识别网站"""
        for pattern, info in self.SITE_PATTERNS.items():
            if pattern in domain:
                return {**info, "preset": info["name"]}
        return {"name": None, "type": "unknown", "anti_level": "medium", "preset": None}

    def _analyze_anti_scrape(self, report, site_info: dict) -> dict:
        """分析反爬特征"""
        features = []
        level = site_info.get("anti_level", "medium")

        # 检查 Cookie 数量和类型
        cookie_names = [c.get("name", "").lower() for c in report.cookies]

        # 常见反爬 Cookie
        anti_cookies = ["__jda", "__jdb", "__jdc", "__jdu", "_tb_token_", "cna", "mtop"]
        for ac in anti_cookies:
            if any(ac in cn for cn in cookie_names):
                features.append(f"检测到反爬 Cookie: {ac}")

        # 检查是否有验证码相关请求
        for req in report.all_requests:
            url_lower = req.url.lower()
            if any(kw in url_lower for kw in ["captcha", "verify", "slider", "jschl"]):
                features.append("检测到验证码/滑块请求")
                level = "high" if level != "extreme" else level

        # 检查加密参数数量
        if len(report.detected_encryption_params) > 3:
            features.append(f"检测到 {len(report.detected_encryption_params)} 个加密参数")
            if level == "low":
                level = "medium"
            elif level == "medium":
                level = "high"

        # 检查是否有 WebSocket
        for req in report.all_requests:
            if "ws://" in req.url or "wss://" in req.url:
                features.append("使用 WebSocket 通信")

        return {"level": level, "features": features}

    def _analyze_login(self, report) -> dict:
        """分析登录状态"""
        result = {
            "required": False,
            "detected": False,
            "suggestion": None,
        }

        # 检查登录相关 Cookie
        login_cookies = ["token", "session", "user", "uid", "login", "auth"]
        cookie_names = [c.get("name", "").lower() for c in report.cookies]

        has_login_cookie = any(
            any(lc in cn for lc in login_cookies)
            for cn in cookie_names
        )

        if has_login_cookie:
            result["detected"] = True

        # 检查页面中是否有登录提示
        html_lower = report.page_html.lower() if report.page_html else ""

        login_hints = ["请登录", "请先登录", "login required", "sign in", "登录后"]
        if any(hint in html_lower for hint in login_hints):
            result["required"] = True
            if not result["detected"]:
                result["suggestion"] = "建议先手动登录，然后保存 Cookie 再进行抓取"

        return result

    def _analyze_apis(self, report) -> dict:
        """分析 API 端点"""
        endpoints = []
        main_api = None

        # 数据 API 的特征
        data_keywords = ["list", "search", "query", "product", "item", "comment", "review", "data"]

        for req in report.api_requests:
            endpoint = {
                "url": req.url,
                "method": req.method,
                "params": list(req.query_params.keys()) + list(req.body_params.keys()),
                "has_signature": bool(req.suspicious_params),
            }
            endpoints.append(endpoint)

            # 判断是否是主要数据接口
            url_lower = req.url.lower()
            if any(kw in url_lower for kw in data_keywords):
                if main_api is None or len(endpoint["params"]) > len(main_api.get("params", [])):
                    main_api = endpoint

        return {"endpoints": endpoints, "main_api": main_api}

    def _analyze_signatures(self, report) -> list[SignatureAnalysis]:
        """深度分析签名参数"""
        params = []
        complexity = "none"

        all_suspicious = set()
        param_values = {}

        # 收集所有可疑参数
        for req in report.api_requests:
            for param in req.suspicious_params:
                all_suspicious.add(param)
                # 获取参数值
                value = req.query_params.get(param, [None])[0] or req.body_params.get(param)
                if value:
                    param_values[param] = str(value) if not isinstance(value, str) else value

        # 分析每个参数
        for param in all_suspicious:
            value = param_values.get(param, "")
            analysis = self._analyze_single_param(param, value)
            params.append(analysis)

            # 更新复杂度
            if analysis.pattern_type in ("hash",) and analysis.confidence > 0.7:
                if complexity in ("none", "simple"):
                    complexity = "moderate"
                if len(value) > 32:
                    complexity = "complex"

        # 检查是否有已知的复杂签名
        for param in all_suspicious:
            param_lower = param.lower()
            if "h5st" in param_lower:
                complexity = "complex"

        return {"params": params, "complexity": complexity}

    def _analyze_single_param(self, name: str, value: str) -> SignatureAnalysis:
        """分析单个参数"""
        name_lower = name.lower()
        value = value or ""

        # 默认值
        pattern_type = "unknown"
        charset = "mixed"
        possible_algorithm = None
        confidence = 0.5

        # 检测长度
        length = len(value)

        # 检测字符集
        if re.match(r'^[0-9]+$', value):
            charset = "numeric"
            if length == 10 or length == 13:
                pattern_type = "timestamp"
                possible_algorithm = "Unix 时间戳"
                confidence = 0.9
        elif re.match(r'^[0-9a-fA-F]+$', value):
            charset = "hex"
            if length == 32:
                pattern_type = "hash"
                possible_algorithm = "MD5"
                confidence = 0.8
            elif length == 40:
                pattern_type = "hash"
                possible_algorithm = "SHA1"
                confidence = 0.8
            elif length == 64:
                pattern_type = "hash"
                possible_algorithm = "SHA256"
                confidence = 0.8
        elif re.match(r'^[0-9a-zA-Z+/=]+$', value):
            charset = "base64"
            if len(value) % 4 == 0:
                pattern_type = "token"
                possible_algorithm = "Base64 编码"
                confidence = 0.7
        elif re.match(r'^[0-9a-zA-Z]+$', value):
            charset = "alphanumeric"

        # 根据参数名调整
        if any(kw in name_lower for kw in ["sign", "signature", "hash"]):
            pattern_type = "hash"
            confidence = max(confidence, 0.8)
        elif any(kw in name_lower for kw in ["token", "auth", "key"]):
            pattern_type = "token"
            confidence = max(confidence, 0.7)
        elif any(kw in name_lower for kw in ["time", "_t", "ts"]):
            pattern_type = "timestamp"
            confidence = max(confidence, 0.7)
        elif any(kw in name_lower for kw in ["nonce", "rand"]):
            pattern_type = "nonce"
            confidence = max(confidence, 0.7)

        # 检查是否看起来是动态的
        appears_dynamic = (
            pattern_type in ("hash", "nonce") or
            (pattern_type == "timestamp" and length >= 10)
        )

        # 生成说明
        notes = f"长度 {length}, 字符集 {charset}"
        if possible_algorithm:
            notes += f", 可能是 {possible_algorithm}"

        return SignatureAnalysis(
            param_name=name,
            param_value=value[:50] + "..." if len(value) > 50 else value,
            pattern_type=pattern_type,
            length=length,
            charset=charset,
            appears_dynamic=appears_dynamic,
            possible_algorithm=possible_algorithm,
            confidence=confidence,
            notes=notes,
        )

    def _generate_recommendations(
        self,
        site_info: dict,
        anti_scrape: dict,
        login_info: dict,
        api_analysis: dict,
        signature_analysis: dict,
    ) -> dict:
        """生成建议"""
        steps = []
        warnings = []
        approach = "browser_scrape"  # 默认

        # 根据反爬等级决定基础策略
        if anti_scrape["level"] == "low":
            approach = "direct_api" if api_analysis["main_api"] else "browser_scrape"
        elif anti_scrape["level"] == "medium":
            approach = "browser_scrape"
        elif anti_scrape["level"] in ("high", "extreme"):
            if signature_analysis["complexity"] == "complex":
                approach = "need_reverse"
            else:
                approach = "hybrid"

        # 生成步骤建议 (不使用 emoji，避免 Windows 终端编码问题)
        if login_info["required"] and not login_info["detected"]:
            steps.append("[登录] 先手动登录网站，然后调用 `brain.save_cookies()` 保存登录态")
            warnings.append("此网站需要登录才能获取完整数据")

        if approach == "direct_api" and api_analysis["main_api"]:
            main_api = api_analysis["main_api"]
            steps.append(f"[API] 直接调用 API: `brain.call_api('{main_api['url']}')`")
            if main_api.get("has_signature"):
                steps.append("[注意] API 需要签名参数，可能需要先从浏览器获取")

        elif approach == "browser_scrape":
            steps.append("[浏览器] 使用浏览器抓取: `brain.scrape_page(url)`")
            steps.append("[选择器] 或者指定选择器: `brain.scrape_with_selector(url, selector, fields)`")

        elif approach == "hybrid":
            steps.append("[混合] 使用混合模式:")
            steps.append("   1. `brain.interact()` 触发请求并捕获签名")
            steps.append("   2. 分析签名参数规律")
            steps.append("   3. `brain.call_api()` 直接调用 API")

        elif approach == "need_reverse":
            steps.append("[逆向] 此网站加密较复杂，建议:")
            steps.append("   1. 使用 `brain.interact()` 多次操作，收集更多签名样本")
            steps.append("   2. 分析签名参数的变化规律")
            steps.append("   3. 考虑使用浏览器作为签名服务器（RPC 模式）")
            warnings.append("此网站使用复杂加密，可能需要逆向分析")

        # 添加代理建议
        if anti_scrape["level"] in ("high", "extreme"):
            steps.append("[代理] 建议启用代理: `AgentConfig.for_kuaidaili(username, password)`")
            warnings.append("高防护网站建议使用代理避免 IP 被封")

        # 特定网站建议
        if site_info.get("name") == "京东":
            warnings.append("京东使用 H5ST 签名，需要特殊处理")
            steps.append("[提示] 可以使用项目中的 `jd_rpc_signer` 获取签名")

        return {"approach": approach, "steps": steps, "warnings": warnings}
