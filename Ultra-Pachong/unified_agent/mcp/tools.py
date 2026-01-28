"""
MCP工具注册与实现

实现标准 MCP 工具，对接内部模块。
"""

import time
import logging
from typing import Dict, Optional, Callable, Any, List

from .types import Tool, ToolParameter, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册工具"""
        self._tools[tool.name] = tool
        logger.info(f"[ToolRegistry] 注册工具: {tool.name}")

    def unregister(self, name: str):
        """注销工具"""
        if name in self._tools:
            del self._tools[name]

    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> list:
        """列出所有工具Schema"""
        return [tool.to_schema() for tool in self._tools.values()]

    def list_names(self) -> List[str]:
        """列出所有工具名"""
        return list(self._tools.keys())

    def execute(self, name: str, arguments: Dict) -> ToolResult:
        """执行工具"""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Tool not found: {name}",
                error_code="TOOL_NOT_FOUND"
            )

        start = time.time()
        try:
            logger.info(f"[ToolRegistry] 执行: {name}")
            result = tool.handler(**arguments)
            duration = int((time.time() - start) * 1000)

            if isinstance(result, ToolResult):
                result.duration_ms = duration
                return result

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                data=result,
                duration_ms=duration
            )
        except Exception as e:
            logger.error(f"[ToolRegistry] 执行错误: {name} - {e}")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=str(e),
                error_code="EXECUTION_ERROR",
                duration_ms=int((time.time() - start) * 1000)
            )


# ============================================================================
# 内置工具实现
# ============================================================================

def scrape_page(
    url: str,
    selector: Optional[str] = None,
    wait_for: Optional[str] = None,
    method: str = "auto"
) -> ToolResult:
    """
    抓取页面内容

    Args:
        url: 目标URL
        selector: CSS选择器（可选，提取特定内容）
        wait_for: 等待元素出现（可选，用于动态页面）
        method: 抓取方式 auto|request|browser

    Returns:
        ToolResult
    """
    try:
        import httpx

        # 简单请求方式
        if method in ("auto", "request"):
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                response = client.get(url, headers=headers)

                data = {
                    "url": url,
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "content_length": len(response.text),
                }

                # 如果有选择器，尝试提取
                if selector and response.status_code == 200:
                    try:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(response.text, "html.parser")
                        elements = soup.select(selector)
                        data["extracted"] = [el.get_text(strip=True) for el in elements[:10]]
                        data["extracted_count"] = len(elements)
                    except ImportError:
                        data["content"] = response.text[:5000]
                else:
                    data["content"] = response.text[:5000]

                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    data=data,
                    metadata={"method": "request"}
                )

    except ImportError:
        return ToolResult(
            status=ToolResultStatus.ERROR,
            error="httpx not installed",
            error_code="DEPENDENCY_MISSING"
        )
    except Exception as e:
        return ToolResult(
            status=ToolResultStatus.ERROR,
            error=str(e),
            error_code="SCRAPE_ERROR"
        )


def analyze_site(url: str) -> ToolResult:
    """
    分析网站反爬特征

    Args:
        url: 目标URL

    Returns:
        ToolResult with anti-crawl analysis
    """
    try:
        import httpx

        analysis = {
            "url": url,
            "accessible": False,
            "anti_crawl": {
                "has_signature": False,
                "has_captcha": False,
                "has_rate_limit": False,
                "has_waf": False,
            },
            "headers": {},
            "recommended_strategy": "request",
            "difficulty": 1,
        }

        with httpx.Client(timeout=15, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = client.get(url, headers=headers)

            analysis["accessible"] = response.status_code == 200
            analysis["status_code"] = response.status_code
            analysis["headers"] = dict(response.headers)

            # 检测反爬特征
            content = response.text.lower()
            resp_headers = {k.lower(): v for k, v in response.headers.items()}

            # WAF 检测
            server = resp_headers.get("server", "").lower()
            if any(waf in server for waf in ["cloudflare", "akamai", "incapsula"]):
                analysis["anti_crawl"]["has_waf"] = True
                analysis["difficulty"] += 2

            # 签名检测
            if any(sig in content for sig in ["sign=", "signature", "_sign", "h5st"]):
                analysis["anti_crawl"]["has_signature"] = True
                analysis["difficulty"] += 1

            # 验证码检测
            if any(cap in content for cap in ["captcha", "验证码", "recaptcha", "geetest"]):
                analysis["anti_crawl"]["has_captcha"] = True
                analysis["difficulty"] += 2

            # 速率限制检测
            if "retry-after" in resp_headers or response.status_code == 429:
                analysis["anti_crawl"]["has_rate_limit"] = True
                analysis["difficulty"] += 1

            # 推荐策略
            if analysis["difficulty"] >= 3:
                analysis["recommended_strategy"] = "browser"
            elif analysis["anti_crawl"]["has_signature"]:
                analysis["recommended_strategy"] = "api_with_sign"

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data=analysis,
            metadata={"analyzed_at": time.time()}
        )

    except ImportError:
        return ToolResult(
            status=ToolResultStatus.ERROR,
            error="httpx not installed",
            error_code="DEPENDENCY_MISSING"
        )
    except Exception as e:
        return ToolResult(
            status=ToolResultStatus.ERROR,
            error=str(e),
            error_code="ANALYZE_ERROR"
        )


def generate_signature(
    params: Dict[str, Any],
    sign_type: str = "md5",
    secret: str = ""
) -> ToolResult:
    """
    生成签名

    Args:
        params: 待签名参数
        sign_type: 签名类型 md5|sha256|hmac_sha256
        secret: 密钥

    Returns:
        ToolResult with signature
    """
    try:
        from unified_agent.signature import SignatureGenerator, SignType

        gen = SignatureGenerator()

        # 映射签名类型
        type_map = {
            "md5": SignType.MD5,
            "sha256": SignType.SHA256,
            "hmac_sha256": SignType.HMAC_SHA256,
        }
        stype = type_map.get(sign_type, SignType.MD5)

        result = gen.generate(stype, params, secret)

        if result.success:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                data={
                    "signature": result.signature,
                    "sign_type": sign_type,
                    "extra_params": result.extra_params,
                }
            )
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=result.error,
                error_code="SIGN_ERROR"
            )

    except ImportError:
        return ToolResult(
            status=ToolResultStatus.ERROR,
            error="signature module not available",
            error_code="MODULE_MISSING"
        )
    except Exception as e:
        return ToolResult(
            status=ToolResultStatus.ERROR,
            error=str(e),
            error_code="SIGN_ERROR"
        )


def diagnose_error(
    error_message: str,
    status_code: Optional[int] = None
) -> ToolResult:
    """
    诊断错误

    Args:
        error_message: 错误信息
        status_code: HTTP状态码

    Returns:
        ToolResult with diagnosis
    """
    try:
        from unified_agent.diagnosis import Diagnoser

        diagnoser = Diagnoser()
        context = {}
        if status_code:
            context["status_code"] = status_code

        result = diagnoser.diagnose(Exception(error_message), context)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data={
                "error_type": result.error_type,
                "category": result.category.value,
                "severity": result.severity.value,
                "root_cause": result.root_cause,
                "probable_causes": result.probable_causes,
                "recommended_action": result.recommended_solution.action,
                "auto_fixable": result.auto_fixable,
                "confidence": result.confidence,
            }
        )

    except ImportError:
        return ToolResult(
            status=ToolResultStatus.ERROR,
            error="diagnosis module not available",
            error_code="MODULE_MISSING"
        )
    except Exception as e:
        return ToolResult(
            status=ToolResultStatus.ERROR,
            error=str(e),
            error_code="DIAGNOSE_ERROR"
        )


def get_credential(
    domain: Optional[str] = None,
    cred_type: Optional[str] = None
) -> ToolResult:
    """
    获取凭据

    Args:
        domain: 域名筛选
        cred_type: 凭据类型 cookie|token|session

    Returns:
        ToolResult with credential
    """
    try:
        from unified_agent.credential import CredentialPool, CredentialType

        pool = CredentialPool()

        # 转换类型
        ct = None
        if cred_type:
            type_map = {
                "cookie": CredentialType.COOKIE,
                "token": CredentialType.TOKEN,
                "session": CredentialType.SESSION,
            }
            ct = type_map.get(cred_type)

        cred = pool.get_available(domain=domain, cred_type=ct)

        if cred:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                data={
                    "cred_id": cred.cred_id,
                    "cred_type": cred.cred_type.value,
                    "value": cred.value,
                    "domain": cred.domain,
                }
            )
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="No available credential",
                error_code="NO_CREDENTIAL"
            )

    except ImportError:
        return ToolResult(
            status=ToolResultStatus.ERROR,
            error="credential module not available",
            error_code="MODULE_MISSING"
        )
    except Exception as e:
        return ToolResult(
            status=ToolResultStatus.ERROR,
            error=str(e),
            error_code="CREDENTIAL_ERROR"
        )


def list_presets() -> ToolResult:
    """
    列出可用的网站预设配置

    Returns:
        ToolResult with presets list
    """
    try:
        # 内置预设列表
        presets = [
            {"name": "jd", "domain": "jd.com", "description": "京东商城"},
            {"name": "taobao", "domain": "taobao.com", "description": "淘宝"},
            {"name": "bilibili", "domain": "bilibili.com", "description": "B站"},
            {"name": "douyin", "domain": "douyin.com", "description": "抖音"},
            {"name": "xiaohongshu", "domain": "xiaohongshu.com", "description": "小红书"},
            {"name": "zhihu", "domain": "zhihu.com", "description": "知乎"},
            {"name": "weibo", "domain": "weibo.com", "description": "微博"},
        ]

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data={"presets": presets, "count": len(presets)}
        )

    except Exception as e:
        return ToolResult(
            status=ToolResultStatus.ERROR,
            error=str(e),
            error_code="LIST_ERROR"
        )


# ============================================================================
# 默认注册表
# ============================================================================

def create_default_registry() -> ToolRegistry:
    """创建默认工具注册表"""
    registry = ToolRegistry()

    # 核心工具
    registry.register(Tool(
        name="scrape_page",
        description="抓取指定URL的页面内容，支持CSS选择器提取",
        parameters=[
            ToolParameter("url", "string", "目标URL", required=True),
            ToolParameter("selector", "string", "CSS选择器，用于提取特定内容", required=False),
            ToolParameter("wait_for", "string", "等待元素出现（动态页面）", required=False),
            ToolParameter("method", "string", "抓取方式: auto|request|browser", required=False, default="auto"),
        ],
        handler=scrape_page
    ))

    registry.register(Tool(
        name="analyze_site",
        description="分析网站反爬特征，返回难度评估和推荐策略",
        parameters=[
            ToolParameter("url", "string", "目标URL", required=True),
        ],
        handler=analyze_site
    ))

    registry.register(Tool(
        name="generate_signature",
        description="生成请求签名（MD5/SHA256/HMAC）",
        parameters=[
            ToolParameter("params", "object", "待签名的参数字典", required=True),
            ToolParameter("sign_type", "string", "签名类型: md5|sha256|hmac_sha256", required=False, default="md5"),
            ToolParameter("secret", "string", "签名密钥", required=False, default=""),
        ],
        handler=generate_signature
    ))

    registry.register(Tool(
        name="diagnose_error",
        description="诊断错误，返回根因分析和推荐修复方案",
        parameters=[
            ToolParameter("error_message", "string", "错误信息", required=True),
            ToolParameter("status_code", "integer", "HTTP状态码", required=False),
        ],
        handler=diagnose_error
    ))

    registry.register(Tool(
        name="get_credential",
        description="从凭据池获取可用凭据（Cookie/Token）",
        parameters=[
            ToolParameter("domain", "string", "域名筛选", required=False),
            ToolParameter("cred_type", "string", "凭据类型: cookie|token|session", required=False),
        ],
        handler=get_credential
    ))

    registry.register(Tool(
        name="list_presets",
        description="列出可用的网站预设配置",
        parameters=[],
        handler=list_presets
    ))

    return registry
