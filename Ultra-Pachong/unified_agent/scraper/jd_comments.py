"""
京东评论爬虫模块 - 集成 Unified Agent 系统

实现京东商品评论的采集，集成 Agent 核心模块：
- diagnosis: 错误诊断与分析
- recovery: 故障自动恢复  
- credential: Cookie/凭据池管理
- mcp: MCP工具协议

使用方式:
    from unified_agent.scraper.jd_comments import JDCommentScraper
    
    scraper = JDCommentScraper()
    await scraper.init_browser()
    await scraper.login()  # 手动登录
    comments = await scraper.scrape_brand_comments("美的", good=1350, bad=150)
    scraper.export_csv(comments, "output.csv")
"""

import asyncio
import csv
import hashlib
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


# ============================================================================
# 集成 Agent 核心模块 (延迟导入)
# ============================================================================

def _get_diagnoser():
    """获取诊断器 (延迟导入)"""
    try:
        from unified_agent.diagnosis import Diagnoser
        return Diagnoser()
    except ImportError:
        return None

def _get_recovery_tree():
    """获取故障决策树 (延迟导入)"""
    try:
        from unified_agent.recovery import FaultDecisionTree
        return FaultDecisionTree()
    except ImportError:
        return None

def _get_credential_pool():
    """获取凭据池 (延迟导入)"""
    try:
        from unified_agent.credential import CredentialPool, CredentialType, Credential
        return CredentialPool(), CredentialType, Credential
    except ImportError:
        return None, None, None

def _get_mcp_server():
    """获取MCP服务器 (延迟导入)"""
    try:
        from unified_agent.mcp import MCPServer
        return MCPServer()
    except ImportError:
        return None


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class Comment:
    """评论数据模型"""
    user_id: str                    # 用户ID (脱敏)
    comment_time: str               # 评论时间
    brand: str                      # 品牌
    price: float                    # 价格
    content: str                    # 评论内容
    score: int                      # 评分 (1-5)
    comment_type: str               # 好评/中评/差评
    sku_id: str = ""                # 商品SKU
    product_name: str = ""          # 商品名称
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "comment_time": self.comment_time,
            "brand": self.brand,
            "price": self.price,
            "content": self.content,
            "score": self.score,
            "comment_type": self.comment_type,
            "sku_id": self.sku_id,
            "product_name": self.product_name,
        }
    
    def to_homework_dict(self) -> Dict[str, Any]:
        """转换为作业需求格式（中文字段名）"""
        return {
            "用户ID": self.user_id,
            "产品系列": self.brand,
            "产品款式": self.product_name,
            "产品价格": self.price,
            "评分": self.comment_type,
            "评论时间": self.comment_time,
            "评论内容": self.content,
        }
    
    def dedup_key(self) -> str:
        """生成去重键"""
        content_prefix = self.content[:50] if len(self.content) >= 50 else self.content
        return hashlib.md5(f"{self.user_id}:{content_prefix}".encode()).hexdigest()


@dataclass 
class BrandConfig:
    """品牌配置"""
    name: str                       # 品牌名称
    keywords: List[str]             # 搜索关键词
    sku_ids: List[str] = field(default_factory=list)  # 商品SKU列表


# ============================================================================
# 品牌配置
# ============================================================================

BRAND_CONFIGS: List[BrandConfig] = [
    BrandConfig("美的", [], sku_ids=["100314457924", "100229300385"]),  # 移除无效SKU
    BrandConfig("格力", [], sku_ids=["100008581210", "100012502996", "100018265254"]),
    BrandConfig("小米", [], sku_ids=["100035246998", "100047361951"]),
    BrandConfig("海尔", [], sku_ids=["100006179005", "100012172366"]),
    BrandConfig("海信", [], sku_ids=["100009077773", "100020907068"]),
    BrandConfig("TCL", [], sku_ids=["100012521374", "100031211072"]),
    BrandConfig("奥克斯", [], sku_ids=["100008348542", "100018673486"]),
    BrandConfig("新飞", [], sku_ids=["10051132809623"]),
    BrandConfig("长虹", [], sku_ids=["100012082698"]),
    BrandConfig("松下", [], sku_ids=["100006652018"]),
]


# ============================================================================
# 数据清洗器
# ============================================================================

class CommentCleaner:
    """评论数据清洗器"""
    
    # 无效评论模式
    INVALID_PATTERNS = [
        r"^此用户未填写评价内容",
        r"^用户未填写评价",
        r"^默认好评",
        r"^系统默认",
        r"^买家未填写",
        r"^暂无评价",
        r"^[。，、！？\s\.\,\!\?]+$",  # 纯标点
        r"^[\U0001F300-\U0001F9FF\s]+$",  # 纯表情
    ]
    
    # 广告关键词
    AD_KEYWORDS = [
        "加微信", "加我", "联系方式", "代理", "招商", "赚钱",
        "优惠券", "领券", "返现", "私聊", "加群",
    ]
    
    def __init__(self, min_length: int = 10):
        self.min_length = min_length
        self._invalid_patterns = [re.compile(p, re.IGNORECASE) for p in self.INVALID_PATTERNS]
        self._seen_keys: Set[str] = set()
    
    def is_valid(self, comment: Comment) -> bool:
        """检查评论是否有效"""
        content = comment.content.strip()
        
        # 长度检查
        if len(content) < self.min_length:
            return False
        
        # 无效模式检查
        for pattern in self._invalid_patterns:
            if pattern.search(content):
                return False
        
        # 广告检查
        for keyword in self.AD_KEYWORDS:
            if keyword in content:
                return False
        
        return True
    
    def is_duplicate(self, comment: Comment) -> bool:
        """检查是否重复"""
        key = comment.dedup_key()
        if key in self._seen_keys:
            return True
        self._seen_keys.add(key)
        return False
    
    def clean(self, comment: Comment) -> Optional[Comment]:
        """清洗评论，返回None表示无效"""
        if not self.is_valid(comment):
            return None
        if self.is_duplicate(comment):
            return None
        
        # 清理内容
        comment.content = self._clean_content(comment.content)
        return comment
    
    def _clean_content(self, content: str) -> str:
        """清理评论内容"""
        # 去除首尾空白
        content = content.strip()
        # 合并多个空白字符
        content = re.sub(r'\s+', ' ', content)
        # 去除特殊控制字符
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
        return content
    
    def reset(self):
        """重置去重缓存"""
        self._seen_keys.clear()
    
    def stats(self) -> Dict[str, int]:
        """返回统计信息"""
        return {
            "unique_comments": len(self._seen_keys)
        }


# ============================================================================
# H5ST RPC 签名桥接
# ============================================================================

class JDSignerRPC:
    """
    京东 H5ST RPC 签名器
    
    通过 Playwright 浏览器调用京东原生签名函数
    """
    
    # RPC 注入脚本
    RPC_INJECT_SCRIPT = """
    window.__jdRpcReady = false;
    window.__jdSignQueue = [];
    
    // 等待签名函数加载
    const waitForSign = setInterval(() => {
        if (window._jdJsBridgeRecv || window.jdSign || window._jd || window.h5st) {
            window.__jdRpcReady = true;
            clearInterval(waitForSign);
            console.log('[JD-RPC] 签名函数已就绪');
        }
    }, 500);
    
    // RPC 签名接口
    window.getJdSign = async function(functionId, body, appid) {
        return new Promise((resolve, reject) => {
            try {
                // 尝试多种签名方式
                let sign = null;
                
                // 方式1: h5st 对象
                if (window.h5st && typeof window.h5st.sign === 'function') {
                    sign = window.h5st.sign({
                        functionId: functionId,
                        body: body,
                        appid: appid || 'jd-m-ware'
                    });
                }
                // 方式2: _jd 对象
                else if (window._jd && window._jd.sign) {
                    sign = window._jd.sign({
                        functionId: functionId,
                        body: body
                    });
                }
                // 方式3: 直接返回模拟签名 (降级)
                else {
                    const ts = Date.now();
                    sign = {
                        h5st: ts + ';' + Math.random().toString(36).substr(2, 16),
                        timestamp: ts
                    };
                }
                
                resolve(sign);
            } catch (e) {
                reject(e.message);
            }
        });
    };
    
    console.log('[JD-RPC] RPC桥接已注入');
    """
    
    def __init__(self, page=None):
        self.page = page
        self._ready = False
    
    async def inject(self, page):
        """注入RPC脚本"""
        self.page = page
        await page.evaluate(self.RPC_INJECT_SCRIPT)
        # 等待签名函数就绪
        await asyncio.sleep(2)
        self._ready = True
        logger.info("[JDSignerRPC] RPC脚本已注入")
    
    async def sign(
        self, 
        function_id: str, 
        body: Dict[str, Any],
        appid: str = "jd-m-ware"
    ) -> Dict[str, Any]:
        """
        获取H5ST签名
        
        Args:
            function_id: API函数名
            body: 请求体
            appid: 应用ID
            
        Returns:
            签名结果 {"h5st": "...", "timestamp": ...}
        """
        if not self.page:
            raise RuntimeError("Page not set, call inject() first")

        try:
            # 使用evaluate传递参数，避免JS注入问题
            body_str = json.dumps(body, ensure_ascii=False, separators=(',', ':'))
            result = await self.page.evaluate(
                """
                async ([functionId, bodyStr, appid]) => {
                    return await window.getJdSign(functionId, bodyStr, appid);
                }
                """,
                [function_id, body_str, appid]
            )
            return result
        except Exception as e:
            logger.warning(f"[JDSignerRPC] 签名失败: {e}, 使用降级方案")
            # 降级: 返回时间戳签名
            ts = int(time.time() * 1000)
            return {
                "h5st": f"{ts};fallback;{random.randint(1000, 9999)}",
                "timestamp": ts
            }


# ============================================================================
# 京东评论API
# ============================================================================

class JDCommentAPI:
    """京东评论API封装"""
    
    BASE_URL = "https://api.m.jd.com/client.action"
    
    # 评分映射
    SCORE_MAP = {
        "good": 3,      # 好评
        "medium": 2,    # 中评
        "bad": 1,       # 差评
    }
    
    def __init__(self, signer: JDSignerRPC = None, proxy: Optional[str] = None):
        self.signer = signer
        self.proxy = proxy  # 保存代理配置
        self._cookies: Dict[str, str] = {}
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://item.jd.com/",
            "Origin": "https://item.jd.com",
        }

        # 解析代理配置（如果提供）
        self._proxy_url = None
        if self.proxy:
            # httpx 直接使用代理URL字符串
            self._proxy_url = self.proxy
            from urllib.parse import urlparse
            parsed = urlparse(self.proxy)
            logger.info(f"[JDCommentAPI] API请求将使用代理: {parsed.username}@{parsed.hostname}:{parsed.port}")
    
    def set_cookies(self, cookies: Dict[str, str]):
        """设置Cookie"""
        self._cookies = cookies
    
    async def get_comments(
        self,
        sku_id: str,
        score: str = "good",
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """
        获取商品评论
        
        Args:
            sku_id: 商品SKU ID
            score: 评分类型 good/medium/bad
            page: 页码
            page_size: 每页数量
            
        Returns:
            API响应数据
        """
        function_id = "getCommentListWithCard"
        
        body = {
            "productId": sku_id,
            "sortType": 5,
            "page": page,
            "pageSize": page_size,
            "score": self.SCORE_MAP.get(score, 3),
            "isShadowSku": 0,
        }
        
        # 获取签名
        sign_result = {}
        if self.signer:
            sign_result = await self.signer.sign(function_id, body)
        
        # 构建请求参数
        params = {
            "functionId": function_id,
            "body": json.dumps(body, ensure_ascii=False, separators=(',', ':')),
            "appid": "item-v3",
            "client": "pc",
            "clientVersion": "1.0.0",
            "t": sign_result.get("timestamp", int(time.time() * 1000)),
        }
        
        if sign_result.get("h5st"):
            params["h5st"] = sign_result["h5st"]
        
        # 发送请求
        try:
            import httpx

            # 构建httpx客户端配置（应用代理）
            client_config = {"timeout": 30}
            if self._proxy_url:
                client_config["proxy"] = self._proxy_url

            async with httpx.AsyncClient(**client_config) as client:
                # 构建Cookie字符串
                cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
                headers = {**self._headers, "Cookie": cookie_str}

                response = await client.get(
                    self.BASE_URL,
                    params=params,
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    # 调试: 打印响应结构的关键字段
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"[JDCommentAPI] 响应keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                    # 打印到控制台帮助调试
                    print(f"      [DEBUG] API响应keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                    if isinstance(data, dict):
                        # 显示一些关键信息
                        if "code" in data:
                            print(f"      [DEBUG] code={data.get('code')}, msg={data.get('msg', data.get('message', ''))}")
                        if "commentInfoList" in data:
                            print(f"      [DEBUG] commentInfoList 数量: {len(data.get('commentInfoList', []))}")
                        if "comments" in data:
                            print(f"      [DEBUG] comments 数量: {len(data.get('comments', []))}")
                        if "result" in data and isinstance(data["result"], dict):
                            print(f"      [DEBUG] result keys: {list(data['result'].keys())}")
                    return data
                else:
                    logger.error(f"[JDCommentAPI] 请求失败: {response.status_code}")
                    return {"error": response.status_code, "status_code": response.status_code}

        except Exception as e:
            logger.error(f"[JDCommentAPI] 请求异常: {e}")
            return {"error": str(e)}
    
    def parse_comments(
        self, 
        response: Dict[str, Any],
        brand: str,
        sku_id: str,
        price: float = 0.0
    ) -> List[Comment]:
        """
        解析评论数据
        
        Args:
            response: API响应
            brand: 品牌名
            sku_id: SKU ID
            price: 商品价格
            
        Returns:
            评论列表
        """
        comments = []

        try:
            # 尝试多种可能的响应路径
            comment_list = []

            # 路径1: response.comments
            if not comment_list and response.get("comments"):
                comment_list = response.get("comments", [])
                print(f"      [DEBUG] 从 comments 获取到 {len(comment_list)} 条")

            # 路径2: response.result.comments
            if not comment_list and response.get("result", {}).get("comments"):
                comment_list = response.get("result", {}).get("comments", [])
                print(f"      [DEBUG] 从 result.comments 获取到 {len(comment_list)} 条")

            # 路径3: response.commentInfoList (京东新API格式)
            if not comment_list and response.get("commentInfoList"):
                comment_list = response.get("commentInfoList", [])
                print(f"      [DEBUG] 从 commentInfoList 获取到 {len(comment_list)} 条")

            # 路径4: response.data.comments
            if not comment_list and response.get("data", {}).get("comments"):
                comment_list = response.get("data", {}).get("comments", [])
                print(f"      [DEBUG] 从 data.comments 获取到 {len(comment_list)} 条")

            # 路径5: response.data.result.comments
            if not comment_list and response.get("data", {}).get("result", {}).get("comments"):
                comment_list = response.get("data", {}).get("result", {}).get("comments", [])
                print(f"      [DEBUG] 从 data.result.comments 获取到 {len(comment_list)} 条")

            # 路径6: response.hotCommentTagStatistics 有时评论在这里
            if not comment_list and response.get("hotCommentTagStatistics"):
                # 这个字段通常不包含评论内容，跳过
                pass

            if not comment_list:
                print(f"      [DEBUG] 未找到评论数据，响应keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")
            
            for item in comment_list:
                # 解析用户ID (脱敏)
                user_id = item.get("id", "") or item.get("guid", "")
                if not user_id:
                    nickname = item.get("nickname", "")
                    user_id = hashlib.md5(nickname.encode()).hexdigest()[:12]
                else:
                    user_id = str(user_id)[:12]  # 脱敏
                
                # 解析评论时间
                comment_time = item.get("creationTime", "") or item.get("referenceTime", "")
                
                # 解析评分
                score = item.get("score", 5)
                
                # 确定评论类型
                if score >= 4:
                    comment_type = "好评"
                elif score == 3:
                    comment_type = "中评"
                else:
                    comment_type = "差评"
                
                # 解析评论内容
                content = item.get("content", "")
                
                # 解析商品信息
                product_name = item.get("productName", "") or item.get("referenceName", "")
                
                # 价格
                item_price = price
                if item.get("productSales"):
                    try:
                        item_price = float(item.get("productSales", {}).get("price", price))
                    except:
                        pass
                
                comment = Comment(
                    user_id=user_id,
                    comment_time=comment_time,
                    brand=brand,
                    price=item_price,
                    content=content,
                    score=score,
                    comment_type=comment_type,
                    sku_id=sku_id,
                    product_name=product_name,
                )
                comments.append(comment)
                
        except Exception as e:
            logger.error(f"[JDCommentAPI] 解析失败: {e}")
        
        return comments


# ============================================================================
# 主爬虫类
# ============================================================================

from unified_agent.scraper.stealth import apply_stealth

class JDCommentScraper:
    """
    京东评论爬虫 - 集成 Unified Agent 系统
    
    集成模块:
    - diagnosis: 错误诊断与分析
    - recovery: 故障自动恢复
    - credential: Cookie/凭据池管理
    - mcp: MCP工具协议
    
    使用方式:
        scraper = JDCommentScraper()
        await scraper.init_browser()
        await scraper.login()
        comments = await scraper.scrape_all_brands()
        scraper.export_csv(comments)
    """
    
    def __init__(
        self,
        output_dir: str = "data",
        request_delay: tuple = (3, 6),  # 增加延迟，避免超频（1秒5次限制）
        proxy: Optional[str] = None,
        max_retries: int = 5,  # 增加重试次数，应对66%失败率
    ):
        """
        初始化爬虫
        
        Args:
            output_dir: 输出目录
            request_delay: 请求间隔 (最小秒, 最大秒)
            proxy: 代理地址 (可选)
            max_retries: 最大重试次数
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.request_delay = request_delay
        self.proxy = proxy
        self.max_retries = max_retries
        
        self.browser = None
        self.context = None
        self.page = None

        self.signer = JDSignerRPC()
        self.api = JDCommentAPI(proxy=proxy)  # 传递代理给API（仅用于数据采集）
        self.cleaner = CommentCleaner()
        
        self._cookies: Dict[str, str] = {}
        self._stats = {
            "total_requests": 0,
            "total_comments": 0,
            "valid_comments": 0,
            "duplicates": 0,
            "errors": 0,
            "recoveries": 0,
        }
        
        # ============ 集成 Agent 核心模块 ============
        
        # 1. 诊断模块 - 错误分析
        self.diagnoser = _get_diagnoser()
        if self.diagnoser:
            logger.info("[Agent] 诊断模块已加载")
        
        # 2. 恢复模块 - 故障自动恢复
        self.recovery_tree = _get_recovery_tree()
        if self.recovery_tree:
            logger.info("[Agent] 恢复模块已加载")
        
        # 3. 凭据池 - Cookie管理
        self.credential_pool, self.CredentialType, self.Credential = _get_credential_pool()
        if self.credential_pool:
            logger.info("[Agent] 凭据池模块已加载")
        
        # 4. MCP服务器 - 工具协议
        self.mcp_server = _get_mcp_server()
        if self.mcp_server:
            logger.info("[Agent] MCP服务器已加载")
        
        # 记录Agent集成状态
        self._agent_status = {
            "diagnosis": self.diagnoser is not None,
            "recovery": self.recovery_tree is not None,
            "credential": self.credential_pool is not None,
            "mcp": self.mcp_server is not None,
        }
        
        logger.info(f"[JDCommentScraper] Agent集成状态: {self._agent_status}")
    
    async def init_browser(self):
        """初始化浏览器（使用直连，不使用代理）"""
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()

            # 启动浏览器 - 始终使用直连（快速、稳定）
            # 代理只用于后续的API请求，不用于页面导航和登录
            launch_args = {
                "headless": False,  # 需要手动登录，所以不能无头
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--no-proxy-server",  # 强制不使用代理
                ]
            }

            logger.info("[JDCommentScraper] 浏览器使用直连（不使用代理），代理仅用于API数据采集")

            self.browser = await self._playwright.chromium.launch(**launch_args)
            self.context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            self.page = await self.context.new_page()
            
            # 应用反检测措施 (恢复启用)
            await apply_stealth(self.page)
            logger.info("[JDCommentScraper] 反检测模块已注入")
            
            logger.info("[JDCommentScraper] 浏览器已启动")
            return True
            
        except ImportError:
            logger.error("[JDCommentScraper] playwright 未安装，请运行: pip install playwright && playwright install chromium")
            return False
        except Exception as e:
            logger.error(f"[JDCommentScraper] 浏览器启动失败: {e}")
            return False
    
    async def login(self, timeout: int = 300):
        """
        打开京东登录页面，等待用户手动登录
        
        Args:
            timeout: 等待超时时间 (秒)
        """
        if not self.page:
            raise RuntimeError("请先调用 init_browser()")
            
        # 1. 尝试加载本地Cookie
        if await self._load_local_cookies():
            logger.info("[JDCommentScraper] 已加载本地Cookie，验证中...")
            # 访问首页验证（使用 domcontentloaded，代理慢需要更长超时）
            try:
                await self.page.goto("https://www.jd.com/", wait_until="domcontentloaded", timeout=120000)  # 2分钟超时
                await asyncio.sleep(3)  # 等待页面稳定
            except Exception as e:
                logger.warning(f"[JDCommentScraper] 首页访问超时，尝试继续: {e}")
                # 即使超时，也尝试获取 Cookie

            cookies = await self.context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}

            # 检查登录相关Cookie是否存在（京东使用 "pin" 而不是 "pt_pin"）
            if cookie_dict.get("pin") or cookie_dict.get("pinId") or cookie_dict.get("pt_key") or cookie_dict.get("pt_pin"):
                self._cookies = cookie_dict
                self.api.set_cookies(cookie_dict)

                # 访问商品页面以加载h5st签名SDK
                await self._load_h5st_sdk()

                # 注入RPC
                await self.signer.inject(self.page)
                self.api.signer = self.signer

                # 显示用户信息
                user_nick = cookie_dict.get("unick", "未知用户")
                user_pin = cookie_dict.get("pin", "")
                print(f"\n[✓] 本地Cookie有效，免登录！")
                print(f"    用户: {user_nick} ({user_pin})")
                logger.info(f"[JDCommentScraper] 使用已保存的Cookie登录: {user_pin}")
                return True
            else:
                logger.warning("[JDCommentScraper] 本地Cookie已失效（缺少登录凭据）")
        
        # 2. 访问京东登录页（代理慢需要更长超时）
        await self.page.goto("https://passport.jd.com/new/login.aspx", wait_until="domcontentloaded", timeout=120000)  # 2分钟超时
        await asyncio.sleep(3)  # 等待页面稳定
        
        print("\n" + "="*60)
        print("请在浏览器中手动登录京东账号")
        print("程序正在监听页面跳转，一旦跳转到京东首页即视为登录成功...")
        print("="*60 + "\n")
        
        try:
            # 等待URL跳转到京东主域 (不包含 passport)
            # 设置较长的超时时间 (10分钟)
            await self.page.wait_for_url(
                lambda url: "jd.com" in url and "passport" not in url,
                timeout=600000, 
                wait_until="domcontentloaded"
            )
            
            # 等待几秒确保Cookie写入
            await asyncio.sleep(3)
            
            # 抓取所有Cookie
            cookies = await self.context.cookies()
            cookie_dict = {c["name"]: c["value"] for c in cookies}
            
            self._cookies = cookie_dict
            self.api.set_cookies(cookie_dict)

            # 访问商品页面以加载h5st签名SDK
            await self._load_h5st_sdk()

            # 注入RPC
            await self.signer.inject(self.page)
            self.api.signer = self.signer

            # 保存到本地文件
            await self._save_local_cookies(cookies)
            
            # ====== 使用 Agent 凭据池保存 Cookie ======
            if self.credential_pool and self.Credential and self.CredentialType:
                self._save_cookie_to_pool(cookie_dict)
            
            print("\n[✓] 检测到页面跳转，登录成功！Cookie已保存")
            logger.info("[JDCommentScraper] 登录成功")
            return True
            
        except Exception as e:
            print(f"\n[✗] 登录等待超时或异常: {e}")
            logger.warning(f"[JDCommentScraper] 登录异常: {e}")
            return False
        logger.warning("[JDCommentScraper] 登录超时")
        return False

    async def _load_h5st_sdk(self) -> bool:
        """
        访问商品详情页以加载h5st签名SDK

        h5st签名函数只在商品详情页加载，需要先访问任意商品页面
        """
        # 使用一个稳定的商品SKU (京东自营商品)
        test_sku = "100012043978"  # 一个稳定存在的商品
        product_url = f"https://item.jd.com/{test_sku}.html"

        try:
            print("    正在加载签名SDK...")
            await self.page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)  # 等待JS加载

            # 检查h5st是否加载
            has_h5st = await self.page.evaluate("""
                () => {
                    return !!(window.h5st || window._jd || window.jdSign);
                }
            """)

            if has_h5st:
                logger.info("[JDCommentScraper] h5st SDK已加载")
                print("    [✓] 签名SDK加载成功")
                return True
            else:
                # 尝试等待更长时间
                await asyncio.sleep(5)
                has_h5st = await self.page.evaluate("""
                    () => {
                        return !!(window.h5st || window._jd || window.jdSign);
                    }
                """)
                if has_h5st:
                    logger.info("[JDCommentScraper] h5st SDK已加载 (延迟)")
                    print("    [✓] 签名SDK加载成功")
                    return True

            logger.warning("[JDCommentScraper] h5st SDK未检测到，将使用降级签名")
            print("    [!] 签名SDK未检测到，使用降级模式")
            return False

        except Exception as e:
            logger.warning(f"[JDCommentScraper] 加载h5st SDK失败: {e}")
            print(f"    [!] 签名SDK加载失败: {e}")
            return False

    async def _load_local_cookies(self) -> bool:
        """加载本地Cookie文件"""
        cookie_file = self.output_dir / "cookies.json"
        if not cookie_file.exists():
            return False
            
        try:
            content = cookie_file.read_text(encoding="utf-8")
            cookies = json.loads(content)
            await self.context.add_cookies(cookies)
            return True
        except Exception as e:
            logger.error(f"加载Cookie失败: {e}")
            return False

    async def _save_local_cookies(self, cookies: List[Dict]):
        """保存Cookie到本地文件"""
        try:
            cookie_file = self.output_dir / "cookies.json"
            cookie_file.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
            logger.info(f"Cookie已保存至: {cookie_file}")
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
    
    async def search_products(
        self, 
        keyword: str, 
        max_items: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索商品获取SKU列表
        
        Args:
            keyword: 搜索关键词
            max_items: 最大商品数
            
        Returns:
            商品列表 [{"sku_id": "...", "name": "...", "price": ...}]
        """
        products = []
        
        try:
            # 访问搜索页（代理慢需要更长超时）
            search_url = f"https://search.jd.com/Search?keyword={keyword}&enc=utf-8"
            logger.info(f"访问搜索页: {search_url}")
            await self.page.goto(search_url, wait_until="domcontentloaded", timeout=120000)  # 2分钟超时
            await asyncio.sleep(5)  # 等待页面JS执行和商品加载
            
            # 检查是否有验证码或拦截
            title = await self.page.title()
            page_content = await self.page.content()

            if "验证" in title or "安全" in title or "验证一下" in page_content or "购物无忧" in page_content:
                logger.warning(f"[!] 京东触发人机验证，需要手动完成")
                await self.page.screenshot(path="search_blocked.png")

                print("\n" + "="*60)
                print("[!] 京东触发了人机验证！")
                print("请在浏览器中完成验证:")
                print("  1. 点击 '快速验证' 按钮")
                print("  2. 完成滑块/点选验证")
                print("  3. 验证成功后会自动继续")
                print("="*60 + "\n")

                # 等待验证完成（检测页面是否有商品列表）
                try:
                    # 等待最多2分钟，检查是否出现商品列表
                    await self.page.wait_for_selector(".gl-item, .j-sku-item", timeout=120000)
                    print("[✓] 验证完成！继续搜索...")
                    logger.info("[JDCommentScraper] 验证完成")
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"[JDCommentScraper] 验证超时: {e}")
                    print("[✗] 验证超时，跳过此次搜索")
                    return products

            # 滚动加载更多
            for _ in range(3):
                await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(1)
            
            # 提取商品信息 (尝试多种选择器)
            items = await self.page.query_selector_all(".gl-item")
            if not items:
                items = await self.page.query_selector_all(".j-sku-item")
            
            if not items:
                logger.warning("未找到商品元素，保存页面快照")
                await self.page.screenshot(path="search_empty.png")
                # 打印部分源码以供调试
                content = await self.page.content()
                logger.info(f"页面源码长度: {len(content)}")
            
            for item in items[:max_items]:
                try:
                    # SKU ID
                    sku_id = await item.get_attribute("data-sku")
                    if not sku_id:
                        continue
                    
                    # 商品名
                    name_el = await item.query_selector(".p-name em")
                    name = await name_el.inner_text() if name_el else ""

                    # 过滤：只保留一级能效的商品
                    if not any(keyword in name for keyword in ["一级", "1级", "新一级", "新国标一级", "APF一级"]):
                        continue

                    # 价格
                    price_el = await item.query_selector(".p-price strong i")
                    price_text = await price_el.inner_text() if price_el else "0"
                    try:
                        price = float(price_text)
                    except:
                        price = 0.0

                    products.append({
                        "sku_id": sku_id,
                        "name": name,
                        "price": price,
                    })
                    
                except Exception as e:
                    continue
            
            logger.info(f"[JDCommentScraper] 搜索 '{keyword}' 找到 {len(products)} 个商品")
            print(f"    搜索 '{keyword}' 找到 {len(products)} 个商品")
            
        except Exception as e:
            logger.error(f"[JDCommentScraper] 搜索失败: {e}")
            print(f"    [!] 搜索失败: {e}")
            await self.page.screenshot(path="search_error.png")
        
        return products
    
    async def scrape_product_comments(
        self,
        sku_id: str,
        brand: str,
        price: float,
        good_count: int = 0,
        bad_count: int = 0,
    ) -> List[Comment]:
        """
        爬取单个商品的评论
        
        Args:
            sku_id: 商品SKU ID
            brand: 品牌名
            price: 商品价格
            good_count: 需要的好评数量
            bad_count: 需要的差评数量
            
        Returns:
            清洗后的评论列表
        """
        comments = []
        
        # 爬取好评
        if good_count > 0:
            good_comments = await self._fetch_comments(
                sku_id, brand, price, "good", good_count
            )
            comments.extend(good_comments)
        
        # 爬取差评
        if bad_count > 0:
            bad_comments = await self._fetch_comments(
                sku_id, brand, price, "bad", bad_count
            )
            comments.extend(bad_comments)
        
        return comments
    
    async def _fetch_comments(
        self,
        sku_id: str,
        brand: str,
        price: float,
        score_type: str,
        target_count: int,
    ) -> List[Comment]:
        """
        获取指定类型的评论 - 使用页面抓取方式

        直接从商品详情页抓取评论，绕过API签名问题
        """
        comments = []
        max_pages = 20  # 最多翻页数

        try:
            # 1. 访问商品详情页
            product_url = f"https://item.jd.com/{sku_id}.html"
            await self.page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            # 检查是否被重定向
            current_url = self.page.url
            if "item.jd.com" not in current_url:
                logger.warning(f"[JDCommentScraper] SKU {sku_id} 页面被重定向: {current_url}")
                return comments

            # 2. 滚动到评论区域（多次滚动确保触发加载）
            for i in range(3):
                await self.page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {0.3 + i * 0.2})")
                await asyncio.sleep(1)

            # 3. 滚动到评论区并点击"查看全部评价"
            await self.page.evaluate("""
                () => {
                    // 滚动到评论区域
                    const commentRoot = document.querySelector('.comment-root, .comment, #comment');
                    if (commentRoot) {
                        commentRoot.scrollIntoView({behavior: 'smooth', block: 'start'});
                    }

                    // 点击"查看全部评价"链接
                    const viewAllLinks = document.querySelectorAll('a, span, div');
                    for (const el of viewAllLinks) {
                        const text = el.textContent;
                        if (text && (text.includes('查看全部') || text.includes('全部评价') || text.includes('更多评价'))) {
                            el.click();
                            break;
                        }
                    }
                }
            """)
            await asyncio.sleep(3)

            # 4. 继续滚动加载更多评论（不再跳转URL，避免触发反爬）
            for _ in range(3):
                await self.page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1)

            # 6. 等待评论列表加载
            try:
                await self.page.wait_for_selector(".comment-item, .comment-con, .J-comment-item, [class*='CommentItem'], .comment-user", timeout=10000)
            except:
                logger.warning(f"[JDCommentScraper] SKU {sku_id} 评论加载超时")

            # 7. 点击评分筛选 (好评/差评)
            await self.page.evaluate(f"""
                () => {{
                    const scoreType = "{score_type}";
                    const filterText = scoreType === "good" ? "好评" : "差评";

                    // 尝试多种方式点击筛选按钮
                    const allElements = document.querySelectorAll('li, span, div, a, button');
                    for (const el of allElements) {{
                        if (el.textContent.includes(filterText) && el.textContent.length < 20) {{
                            el.click();
                            break;
                        }}
                    }}
                }}
            """)
            await asyncio.sleep(2)

            # 5. 抓取评论
            current_page = 1
            while len(comments) < target_count and current_page <= max_pages:
                # 等待评论列表加载
                await asyncio.sleep(1)

                # 抓取当前页评论
                page_comments = await self._extract_comments_from_page(sku_id, brand, price, score_type)

                if not page_comments:
                    logger.info(f"[JDCommentScraper] SKU {sku_id} 第{current_page}页无评论，停止")
                    break

                # 清洗并添加评论
                for comment in page_comments:
                    cleaned = self.cleaner.clean(comment)
                    if cleaned:
                        comments.append(cleaned)
                        self._stats["valid_comments"] += 1
                        self._stats["total_comments"] += 1

                        if len(comments) >= target_count:
                            break
                    else:
                        self._stats["duplicates"] += 1

                if len(comments) >= target_count:
                    break

                # 点击下一页
                next_btn = await self.page.query_selector(".ui-pager-next:not(.ui-pager-disabled), .comment-pager .ui-pager-next")
                if next_btn:
                    await next_btn.click()
                    await asyncio.sleep(2)
                    current_page += 1
                else:
                    break

        except Exception as e:
            logger.error(f"[JDCommentScraper] 页面抓取失败: {e}")
            self._stats["errors"] += 1

        return comments

    async def _extract_comments_from_page(
        self,
        sku_id: str,
        brand: str,
        price: float,
        score_type: str,
    ) -> List[Comment]:
        """从当前页面提取评论"""
        comments = []

        try:
            # 调试：截图查看页面状态
            await self.page.screenshot(path=f"debug_sku_{sku_id}.png")

            # 使用JavaScript提取评论数据
            js_comments = await self.page.evaluate("""
                () => {
                    const results = [];
                    const seen = new Set();  // 去重用

                    // 方法1: 遍历所有可能包含评论的文本节点
                    const commentRoot = document.querySelector('.comment-root, .comment, #comment');
                    if (commentRoot) {
                        // 获取所有文本内容较长的元素
                        const walker = document.createTreeWalker(
                            commentRoot,
                            NodeFilter.SHOW_TEXT,
                            null,
                            false
                        );
                        let node;
                        while (node = walker.nextNode()) {
                            const text = node.textContent.trim();
                            // 过滤掉太短或已见过的文本
                            if (text.length > 20 && !seen.has(text)) {
                                // 检查是否像评论内容（排除标题、日期等）
                                const isLikelyComment = (
                                    !text.includes('评价') &&
                                    !text.includes('晒单') &&
                                    !text.match(/^\\d{4}[-\\/]\\d{2}[-\\/]\\d{2}/) &&
                                    !text.match(/^\\d+人觉得有用/) &&
                                    text.length < 500
                                );
                                if (isLikelyComment) {
                                    seen.add(text);
                                    results.push({
                                        content: text,
                                        user: '',
                                        time: ''
                                    });
                                }
                            }
                        }
                    }

                    // 方法2: 查找包含评论用户信息的元素
                    if (results.length === 0) {
                        const userElements = document.querySelectorAll('.comment-user, [class*="user"]');
                        for (const userEl of userElements) {
                            let container = userEl.closest('[class*="comment"]') || userEl.parentElement?.parentElement;
                            if (!container) continue;

                            const contentEl = container.querySelector('p, [class*="content"], [class*="con"]');
                            const content = contentEl ? contentEl.textContent.trim() : '';

                            if (content && content.length > 10 && !seen.has(content)) {
                                seen.add(content);
                                results.push({
                                    content: content,
                                    user: userEl.textContent.trim().substring(0, 20),
                                    time: ''
                                });
                            }
                        }
                    }

                    // 方法3: 尝试找所有长文本段落
                    if (results.length === 0) {
                        const paragraphs = document.querySelectorAll('.comment-root p, .comment p, [class*="Comment"] p');
                        for (const p of paragraphs) {
                            const text = p.textContent.trim();
                            if (text.length > 15 && !seen.has(text)) {
                                seen.add(text);
                                results.push({
                                    content: text,
                                    user: '',
                                    time: ''
                                });
                            }
                        }
                    }

                    // 返回调试信息
                    return {
                        comments: results.slice(0, 30),
                        debugInfo: {
                            url: window.location.href,
                            hasCommentUser: document.querySelectorAll('.comment-user').length,
                            hasCommentRoot: !!document.querySelector('.comment-root'),
                            commentRootText: document.querySelector('.comment-root')?.innerText?.substring(0, 200) || 'N/A'
                        }
                    };
                }
            """)

            debug_info = js_comments.get('debugInfo', {})
            print(f"      [DEBUG] 页面: {debug_info}")

            # 使用JS提取的评论
            extracted_comments = js_comments.get('comments', [])
            print(f"      [DEBUG] JS提取到 {len(extracted_comments)} 条评论")

            if extracted_comments:
                # 将JS提取的评论转换为Comment对象
                for item in extracted_comments:
                    try:
                        content = item.get('content', '').strip()
                        if not content or len(content) < 10:
                            continue

                        user_name = item.get('user', '')
                        user_id = hashlib.md5(user_name.encode()).hexdigest()[:12] if user_name else hashlib.md5(content[:20].encode()).hexdigest()[:12]
                        comment_time = item.get('time', '')

                        # 确定评分和类型
                        if score_type == "good":
                            score = 5
                            comment_type = "好评"
                        else:
                            score = 1
                            comment_type = "差评"

                        comment = Comment(
                            user_id=user_id,
                            comment_time=comment_time.strip(),
                            brand=brand,
                            price=price,
                            content=content,
                            score=score,
                            comment_type=comment_type,
                            sku_id=sku_id,
                            product_name=f"{brand}空调",
                        )
                        comments.append(comment)

                    except Exception as e:
                        continue

        except Exception as e:
            logger.error(f"[JDCommentScraper] 提取评论失败: {e}")

        return comments
    
    async def _request_with_recovery(
        self,
        sku_id: str,
        score_type: str,
        page: int,
    ) -> Dict[str, Any]:
        """
        带恢复机制的请求
        
        集成 Agent recovery 模块进行故障自动恢复
        """
        self._stats["total_requests"] += 1
        
        for attempt in range(self.max_retries):
            response = await self.api.get_comments(
                sku_id=sku_id,
                score=score_type,
                page=page,
                page_size=10,
            )
            
            # 成功则返回
            if "error" not in response:
                return response
            
            # ====== 使用 Agent 恢复模块 ======
            if self.recovery_tree and attempt < self.max_retries - 1:
                error_msg = str(response.get("error", ""))
                status_code = response.get("status_code", 0)
                
                # 获取故障决策
                decision = self.recovery_tree.diagnose(
                    error_msg, 
                    {"status_code": status_code}
                )
                
                if decision:
                    logger.info(f"[Agent恢复] 尝试恢复: {decision.recovery_actions}")
                    print(f"    [恢复] 执行: {[a.value for a in decision.recovery_actions[:2]]}")
                    
                    # 执行恢复动作
                    for action in decision.recovery_actions[:2]:  # 最多执行2个动作
                        success = await self._execute_recovery_action(action.value)
                        if success:
                            self._stats["recoveries"] += 1
                            break
                    
                    # 等待后重试
                    await asyncio.sleep(random.uniform(3, 6))
                    continue
            
            # 最后一次尝试失败
            return response
        
        return {"error": "max_retries_exceeded"}
    
    async def _execute_recovery_action(self, action: str) -> bool:
        """
        执行恢复动作
        
        Args:
            action: 动作名称
            
        Returns:
            是否成功
        """
        try:
            if action == "retry":
                await asyncio.sleep(2)
                return True
                
            elif action == "wait_cooldown":
                logger.info("[恢复] 等待冷却...")
                await asyncio.sleep(random.uniform(10, 20))
                return True
                
            elif action == "reduce_rate":
                # 增加请求间隔
                old_delay = self.request_delay
                self.request_delay = (
                    self.request_delay[0] * 1.5,
                    self.request_delay[1] * 1.5
                )
                logger.info(f"[恢复] 降低请求频率: {old_delay} -> {self.request_delay}")
                return True
                
            elif action == "change_user_agent":
                # 切换 User-Agent
                new_ua = random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
                ])
                self.api._headers["User-Agent"] = new_ua
                logger.info(f"[恢复] 切换UA: {new_ua[:50]}...")
                return True
                
            elif action == "rotate_cookie":
                # 如果有凭据池，尝试切换Cookie
                if self.credential_pool:
                    cred = self.credential_pool.get_available(domain="jd.com")
                    if cred:
                        logger.info("[恢复] 从凭据池获取新Cookie")
                        return True
                return False
                
            elif action == "restart_browser":
                # 重启浏览器
                if self.browser:
                    logger.info("[恢复] 重启浏览器...")
                    await self.browser.close()
                    await asyncio.sleep(2)
                    await self.init_browser()
                    return True
                return False
                
            else:
                logger.debug(f"[恢复] 未知动作: {action}")
                return False
                
        except Exception as e:
            logger.error(f"[恢复] 执行失败: {e}")
            return False
    
    async def scrape_brand_comments(
        self,
        brand_config: BrandConfig,
        good_count: int = 1350,
        bad_count: int = 150,
    ) -> List[Comment]:
        """
        爬取单个品牌的评论
        
        Args:
            brand_config: 品牌配置
            good_count: 好评数量
            bad_count: 差评数量
            
        Returns:
            评论列表
        """
        brand = brand_config.name
        comments = []

        logger.info(f"[JDCommentScraper] 开始爬取品牌: {brand}")
        print(f"\n>>> 正在爬取 {brand} 的评论 (目标: {good_count}好评 + {bad_count}差评)")

        # 优先使用预设的SKU列表（避免搜索触发验证码）
        products = []
        if brand_config.sku_ids:
            print(f"    使用预设SKU列表 ({len(brand_config.sku_ids)}个商品)")
            for sku_id in brand_config.sku_ids:
                products.append({
                    "sku_id": sku_id,
                    "name": f"{brand}空调",
                    "price": 0.0,  # 价格从评论API获取
                })
        else:
            # 如果没有预设SKU，则搜索
            print(f"    搜索商品...")
            for keyword in brand_config.keywords:
                found = await self.search_products(keyword, max_items=5)
                products.extend(found)
                if len(products) >= 10:
                    break

        if not products:
            logger.warning(f"[JDCommentScraper] 品牌 {brand} 没有找到商品")
            return comments
        
        # 计算每个商品需要爬取的数量
        good_per_product = good_count // len(products) + 1
        bad_per_product = bad_count // len(products) + 1
        
        collected_good = 0
        collected_bad = 0
        
        for product in products:
            # 检查是否已达目标
            need_good = max(0, good_count - collected_good)
            need_bad = max(0, bad_count - collected_bad)
            
            if need_good == 0 and need_bad == 0:
                break
            
            # 爬取评论
            product_comments = await self.scrape_product_comments(
                sku_id=product["sku_id"],
                brand=brand,
                price=product["price"],
                good_count=min(need_good, good_per_product),
                bad_count=min(need_bad, bad_per_product),
            )
            
            # 统计
            for c in product_comments:
                if c.comment_type == "好评":
                    collected_good += 1
                else:
                    collected_bad += 1
            
            comments.extend(product_comments)

            print(f"    {product['name'][:30]}... 收集 {len(product_comments)} 条")

            # 产品间延迟，避免触发反爬
            await asyncio.sleep(random.uniform(5, 10))

        print(f"    >>> {brand} 完成: 好评{collected_good}, 差评{collected_bad}")
        logger.info(f"[JDCommentScraper] {brand} 爬取完成: {len(comments)} 条")
        
        return comments
    
    async def scrape_all_brands(
        self,
        brands: List[BrandConfig] = None,
        good_per_brand: int = 1350,
        bad_per_brand: int = 150,
    ) -> List[Comment]:
        """
        爬取所有品牌的评论
        
        Args:
            brands: 品牌配置列表 (默认使用内置配置)
            good_per_brand: 每品牌好评数
            bad_per_brand: 每品牌差评数
            
        Returns:
            全部评论列表
        """
        if brands is None:
            brands = BRAND_CONFIGS
        
        all_comments = []
        
        print("\n" + "="*60)
        print(f"开始爬取 {len(brands)} 个品牌的评论")
        print(f"目标: 每品牌 {good_per_brand} 好评 + {bad_per_brand} 差评")
        print("="*60)
        
        for i, brand_config in enumerate(brands, 1):
            print(f"\n[{i}/{len(brands)}] 处理品牌: {brand_config.name}")
            
            # 每个品牌重置去重缓存
            self.cleaner.reset()
            
            comments = await self.scrape_brand_comments(
                brand_config,
                good_count=good_per_brand,
                bad_count=bad_per_brand,
            )
            all_comments.extend(comments)
            
            # 品牌间隔
            await asyncio.sleep(5)
        
        print("\n" + "="*60)
        print(f"爬取完成! 总计: {len(all_comments)} 条评论")
        print("="*60)
        
        return all_comments
    
    def export_csv(
        self, 
        comments: List[Comment], 
        filename: str = "jd_ac_comments.csv",
        homework_format: bool = True,
    ) -> Path:
        """
        导出CSV文件
        
        Args:
            comments: 评论列表
            filename: 文件名
            homework_format: 是否使用作业格式（中文字段名）
            
        Returns:
            输出文件路径
        """
        output_path = self.output_dir / filename
        
        if homework_format:
            # 作业格式：中文字段名
            fieldnames = ["用户ID", "产品系列", "产品款式", "产品价格", "评分", "评论时间", "评论内容"]
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for comment in comments:
                    writer.writerow(comment.to_homework_dict())
        else:
            # 原始格式：英文字段名
            fieldnames = [
                "user_id", "comment_time", "brand", "price", 
                "content", "score", "comment_type", "sku_id", "product_name"
            ]
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for comment in comments:
                    writer.writerow(comment.to_dict())
        
        print(f"\n[✓] CSV已导出: {output_path}")
        logger.info(f"[JDCommentScraper] CSV导出: {output_path}")
        
        return output_path
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            **self._stats,
            **self.cleaner.stats(),
            "agent_status": self._agent_status,
        }
        
        # 添加 MCP 服务器统计
        if self.mcp_server:
            stats["mcp_stats"] = self.mcp_server.get_stats()
        
        return stats
    
    # ==================== Agent 集成方法 ====================
    
    def _save_cookie_to_pool(self, cookies: Dict[str, str]):
        """
        将 Cookie 保存到凭据池
        
        使用 Agent credential 模块
        """
        try:
            import json
            cookie_str = json.dumps(cookies)
            
            cred = self.Credential(
                cred_id=f"jd_cookie_{int(time.time())}",
                cred_type=self.CredentialType.COOKIE,
                value=cookie_str,
                domain="jd.com",
            )
            
            self.credential_pool.add(cred)
            logger.info("[Agent凭据池] Cookie已保存")
            
        except Exception as e:
            logger.warning(f"[Agent凭据池] 保存失败: {e}")
    
    def get_agent_status(self) -> Dict[str, bool]:
        """获取 Agent 模块集成状态"""
        return self._agent_status
    
    def use_mcp_tool(self, tool_name: str, **kwargs) -> Any:
        """
        使用 MCP 工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        if not self.mcp_server:
            logger.warning("[MCP] MCP服务器未加载")
            return None
        
        result = self.mcp_server.call(tool_name, **kwargs)
        return result
    
    def diagnose_last_error(self, error: Exception, context: Dict = None) -> Optional[Dict]:
        """
        诊断错误
        
        使用 Agent diagnosis 模块
        
        Args:
            error: 异常对象
            context: 上下文信息
            
        Returns:
            诊断结果
        """
        if not self.diagnoser:
            return None
        
        result = self.diagnoser.diagnose(error, context or {})
        return {
            "error_type": result.error_type,
            "category": result.category.value,
            "severity": result.severity.value,
            "root_cause": result.root_cause,
            "recommended_action": result.recommended_solution.action,
            "auto_fixable": result.auto_fixable,
        }
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, '_playwright'):
            await self._playwright.stop()
        logger.info("[JDCommentScraper] 浏览器已关闭")


# ============================================================================
# 便捷函数
# ============================================================================

async def run_scraper(
    output_file: str = "jd_ac_comments.csv",
    proxy: str = None,
):
    """
    运行爬虫的便捷函数
    
    集成 Unified Agent 系统:
    - diagnosis: 错误诊断
    - recovery: 故障恢复
    - credential: 凭据管理
    - mcp: 工具协议
    
    Args:
        output_file: 输出文件名
        proxy: 代理地址
    """
    print("\n" + "="*60)
    print("  Unified Agent - 京东评论爬虫")
    print("="*60)
    
    scraper = JDCommentScraper(proxy=proxy)
    
    # 显示 Agent 模块状态
    agent_status = scraper.get_agent_status()
    print("\nAgent 模块状态:")
    print(f"  - 诊断模块 (diagnosis): {'✓' if agent_status['diagnosis'] else '✗'}")
    print(f"  - 恢复模块 (recovery):  {'✓' if agent_status['recovery'] else '✗'}")
    print(f"  - 凭据池 (credential):  {'✓' if agent_status['credential'] else '✗'}")
    print(f"  - MCP服务 (mcp):        {'✓' if agent_status['mcp'] else '✗'}")
    
    try:
        # 初始化
        print("\n[1/4] 启动浏览器...")
        if not await scraper.init_browser():
            return
        
        # 登录
        print("[2/4] 等待登录...")
        if not await scraper.login():
            return
        
        # 爬取
        print("[3/4] 开始爬取...")
        comments = await scraper.scrape_all_brands()
        
        # 导出
        print("[4/4] 导出数据...")
        if comments:
            scraper.export_csv(comments, output_file)
            
            # 打印统计
            stats = scraper.get_stats()
            print("\n" + "="*60)
            print("统计信息:")
            print("="*60)
            print(f"  - 总请求数: {stats['total_requests']}")
            print(f"  - 总评论数: {stats['total_comments']}")
            print(f"  - 有效评论: {stats['valid_comments']}")
            print(f"  - 去重/无效: {stats['duplicates']}")
            print(f"  - 错误次数: {stats.get('errors', 0)}")
            print(f"  - 恢复次数: {stats.get('recoveries', 0)}")
            
            if stats.get('mcp_stats'):
                print(f"  - MCP调用: {stats['mcp_stats'].get('total_calls', 0)}")
        
    finally:
        await scraper.close()


# 入口点
if __name__ == "__main__":
    asyncio.run(run_scraper())
