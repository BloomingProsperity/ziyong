"""
网站预设配置

为常见网站提供开箱即用的配置，包括：
- 登录页面地址
- 数据 API 端点
- 选择器配置
- 特殊处理逻辑

使用方式：
    preset = get_preset("jd.com")
    if preset:
        # 使用预设配置
        ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class SitePreset:
    """网站预设配置"""
    name: str  # 网站名称
    domains: list[str]  # 匹配的域名
    site_type: str  # 网站类型

    # 登录配置
    login_url: str | None = None
    login_check_selector: str | None = None  # 检测是否登录的选择器
    login_check_cookie: str | None = None  # 检测是否登录的 Cookie 名

    # API 配置
    api_base: str | None = None
    main_apis: list[dict[str, Any]] = field(default_factory=list)

    # 列表页配置
    list_item_selector: str | None = None
    list_fields: list[dict[str, str]] = field(default_factory=list)

    # 分页配置
    pagination_type: str = "click"  # "click", "scroll", "url_param"
    next_page_selector: str | None = None
    page_param_name: str | None = None

    # 特殊处理
    requires_signature: bool = False
    signature_params: list[str] = field(default_factory=list)
    anti_scrape_notes: str | None = None

    # 建议的交互流程
    suggested_actions: list[dict[str, Any]] = field(default_factory=list)

    # 额外说明
    notes: str | None = None


# ============ 预设配置定义 ============

PRESETS: dict[str, SitePreset] = {}


def register_preset(preset: SitePreset) -> None:
    """注册预设配置"""
    for domain in preset.domains:
        PRESETS[domain] = preset


def get_preset(url_or_domain: str) -> SitePreset | None:
    """
    获取网站预设配置

    Args:
        url_or_domain: URL 或域名

    Returns:
        SitePreset 或 None
    """
    from urllib.parse import urlparse

    # 提取域名
    if url_or_domain.startswith("http"):
        domain = urlparse(url_or_domain).netloc.lower()
    else:
        domain = url_or_domain.lower()

    # 精确匹配
    if domain in PRESETS:
        return PRESETS[domain]

    # 模糊匹配
    for preset_domain, preset in PRESETS.items():
        if preset_domain in domain:
            return preset

    return None


def list_presets() -> list[str]:
    """列出所有预设网站"""
    return list(set(p.name for p in PRESETS.values()))


# ============ 京东 ============
register_preset(SitePreset(
    name="京东",
    domains=["jd.com", "m.jd.com", "item.jd.com", "search.jd.com"],
    site_type="ecommerce",

    login_url="https://passport.jd.com/new/login.aspx",
    login_check_cookie="pt_key",

    api_base="https://api.m.jd.com",
    main_apis=[
        {
            "name": "商品评论",
            "url": "https://api.m.jd.com/client.action",
            "method": "POST",
            "function": "getCommentListWithCard",
            "params": ["productId", "sortType", "page", "pageSize", "score"],
            "requires_h5st": True,
        },
        {
            "name": "商品详情",
            "url": "https://api.m.jd.com/client.action",
            "method": "POST",
            "function": "getProductInfo",
            "params": ["skuId"],
            "requires_h5st": True,
        },
    ],

    list_item_selector=".gl-item",
    list_fields=[
        {"name": "title", "selector": ".p-name a em", "attr": "text"},
        {"name": "price", "selector": ".p-price strong i", "attr": "text"},
        {"name": "url", "selector": ".p-name a", "attr": "href"},
        {"name": "shop", "selector": ".p-shop a", "attr": "text"},
    ],

    pagination_type="click",
    next_page_selector=".pn-next",

    requires_signature=True,
    signature_params=["h5st", "x-api-eid-token"],
    anti_scrape_notes="京东使用 H5ST 签名算法，建议使用 RPC 模式获取签名",

    suggested_actions=[
        {"type": "wait", "seconds": 2},
        {"type": "scroll"},
        {"type": "wait", "seconds": 1},
    ],

    notes="京东反爬较严，建议：1. 使用登录态 2. 使用代理 3. 控制请求频率",
))


# ============ 淘宝/天猫 ============
register_preset(SitePreset(
    name="淘宝",
    domains=["taobao.com", "m.taobao.com", "s.taobao.com", "item.taobao.com"],
    site_type="ecommerce",

    login_url="https://login.taobao.com/",
    login_check_cookie="_tb_token_",

    list_item_selector='[class*="Card--card"]',
    list_fields=[
        {"name": "title", "selector": '[class*="Title"]', "attr": "text"},
        {"name": "price", "selector": '[class*="Price"]', "attr": "text"},
        {"name": "shop", "selector": '[class*="Shop"]', "attr": "text"},
    ],

    pagination_type="scroll",

    requires_signature=True,
    signature_params=["sign", "_m_h5_tk"],
    anti_scrape_notes="淘宝使用 mtop 签名，需要逆向 _m_h5_tk 生成算法",

    notes="淘宝强制登录才能搜索，建议使用 Session 保存登录态",
))


# ============ 天猫 ============
register_preset(SitePreset(
    name="天猫",
    domains=["tmall.com", "detail.tmall.com", "list.tmall.com"],
    site_type="ecommerce",

    login_url="https://login.tmall.com/",
    login_check_cookie="_tb_token_",

    list_item_selector='[class*="product-item"]',

    requires_signature=True,
    signature_params=["sign", "_m_h5_tk"],

    notes="天猫与淘宝共享登录态和签名机制",
))


# ============ 拼多多 ============
register_preset(SitePreset(
    name="拼多多",
    domains=["pinduoduo.com", "mobile.pinduoduo.com", "yangkeduo.com"],
    site_type="ecommerce",

    login_url="https://mobile.pinduoduo.com/login.html",

    list_item_selector='[class*="goods-card"]',
    list_fields=[
        {"name": "title", "selector": '[class*="title"]', "attr": "text"},
        {"name": "price", "selector": '[class*="price"]', "attr": "text"},
    ],

    pagination_type="scroll",

    requires_signature=True,
    anti_scrape_notes="拼多多使用 anti-content 签名",

    notes="拼多多主要是移动端，建议使用移动端 UA",
))


# ============ 1688 ============
register_preset(SitePreset(
    name="1688",
    domains=["1688.com", "detail.1688.com", "s.1688.com"],
    site_type="ecommerce",

    login_url="https://login.1688.com/",
    login_check_cookie="cna",

    list_item_selector='[class*="offer-item"]',
    list_fields=[
        {"name": "title", "selector": '[class*="title"]', "attr": "text"},
        {"name": "price", "selector": '[class*="price"]', "attr": "text"},
        {"name": "min_order", "selector": '[class*="moq"]', "attr": "text"},
    ],

    pagination_type="click",
    next_page_selector=".fui-next",

    notes="1688 是 B2B 平台，价格通常是区间价",
))


# ============ 小红书 ============
register_preset(SitePreset(
    name="小红书",
    domains=["xiaohongshu.com", "www.xiaohongshu.com", "xhslink.com"],
    site_type="social",

    login_url="https://www.xiaohongshu.com/",
    login_check_cookie="web_session",

    list_item_selector='[class*="note-item"]',
    list_fields=[
        {"name": "title", "selector": '[class*="title"]', "attr": "text"},
        {"name": "author", "selector": '[class*="author"]', "attr": "text"},
        {"name": "likes", "selector": '[class*="like"]', "attr": "text"},
    ],

    pagination_type="scroll",

    requires_signature=True,
    signature_params=["x-s", "x-t"],
    anti_scrape_notes="小红书使用 x-s 签名，需要逆向",

    notes="小红书需要登录才能查看完整内容",
))


# ============ 微博 ============
register_preset(SitePreset(
    name="微博",
    domains=["weibo.com", "m.weibo.cn", "s.weibo.com"],
    site_type="social",

    login_url="https://passport.weibo.com/sso/signin",
    login_check_cookie="SUB",

    list_item_selector='[class*="card-wrap"]',
    list_fields=[
        {"name": "content", "selector": '[class*="txt"]', "attr": "text"},
        {"name": "author", "selector": '[class*="name"]', "attr": "text"},
        {"name": "time", "selector": '[class*="from"]', "attr": "text"},
    ],

    pagination_type="scroll",

    notes="微博热搜可以不登录访问，个人主页需要登录",
))


# ============ 知乎 ============
register_preset(SitePreset(
    name="知乎",
    domains=["zhihu.com", "www.zhihu.com", "zhuanlan.zhihu.com"],
    site_type="social",

    login_url="https://www.zhihu.com/signin",
    login_check_cookie="z_c0",

    list_item_selector='[class*="ContentItem"]',
    list_fields=[
        {"name": "title", "selector": '[class*="Title"]', "attr": "text"},
        {"name": "excerpt", "selector": '[class*="RichContent"]', "attr": "text"},
        {"name": "author", "selector": '[class*="AuthorInfo"]', "attr": "text"},
        {"name": "votes", "selector": '[class*="VoteButton"]', "attr": "text"},
    ],

    pagination_type="scroll",

    notes="知乎部分内容需要登录，API 较友好",
))


# ============ B站 ============
register_preset(SitePreset(
    name="哔哩哔哩",
    domains=["bilibili.com", "www.bilibili.com", "m.bilibili.com"],
    site_type="video",

    login_url="https://passport.bilibili.com/login",
    login_check_cookie="SESSDATA",

    api_base="https://api.bilibili.com",
    main_apis=[
        {
            "name": "视频信息",
            "url": "https://api.bilibili.com/x/web-interface/view",
            "method": "GET",
            "params": ["bvid"],
            "requires_wbi": True,
        },
        {
            "name": "评论",
            "url": "https://api.bilibili.com/x/v2/reply/main",
            "method": "GET",
            "params": ["type", "oid", "pn"],
            "requires_wbi": True,
        },
    ],

    list_item_selector=".bili-video-card",
    list_fields=[
        {"name": "title", "selector": ".bili-video-card__info--tit", "attr": "text"},
        {"name": "author", "selector": ".bili-video-card__info--author", "attr": "text"},
        {"name": "views", "selector": ".bili-video-card__stats--item", "attr": "text"},
    ],

    pagination_type="scroll",

    requires_signature=True,
    signature_params=["wts", "w_rid"],
    anti_scrape_notes="B站使用 WBI 签名，可通过分析 wbi_img 获取密钥",

    notes="B站 API 相对友好，但部分接口需要 WBI 签名",
))


# ============ 抖音 ============
register_preset(SitePreset(
    name="抖音",
    domains=["douyin.com", "www.douyin.com"],
    site_type="video",

    login_url="https://www.douyin.com/",

    list_item_selector='[class*="video-card"]',

    requires_signature=True,
    signature_params=["X-Bogus", "a_bogus", "_signature"],
    anti_scrape_notes="抖音反爬极强，使用多层签名 + 设备指纹",

    notes="抖音是最难抓取的平台之一，建议考虑其他数据源",
))


# ============ 当当 ============
register_preset(SitePreset(
    name="当当",
    domains=["dangdang.com", "search.dangdang.com", "product.dangdang.com"],
    site_type="ecommerce",

    list_item_selector=".list_aa li, .bigimg li",
    list_fields=[
        {"name": "title", "selector": ".name a", "attr": "text"},
        {"name": "price", "selector": ".price .num", "attr": "text"},
        {"name": "url", "selector": ".name a", "attr": "href"},
        {"name": "author", "selector": ".search_book_author a", "attr": "text"},
    ],

    pagination_type="click",
    next_page_selector=".next a",

    requires_signature=False,
    anti_scrape_notes="当当反爬较弱，可直接抓取",

    notes="当当是比较友好的电商网站，适合练手",
))


# ============ 苏宁 ============
register_preset(SitePreset(
    name="苏宁",
    domains=["suning.com", "search.suning.com", "product.suning.com"],
    site_type="ecommerce",

    list_item_selector=".product-box",
    list_fields=[
        {"name": "title", "selector": ".title-selling-point a", "attr": "text"},
        {"name": "price", "selector": ".price-box .def-price", "attr": "text"},
        {"name": "url", "selector": ".title-selling-point a", "attr": "href"},
    ],

    pagination_type="click",
    next_page_selector=".next",

    notes="苏宁反爬中等，建议使用代理",
))


# ============ 辅助函数 ============

def get_preset_info(url: str) -> dict[str, Any]:
    """
    获取网站预设信息摘要

    返回适合 AI 阅读的格式
    """
    preset = get_preset(url)
    if not preset:
        return {"found": False, "message": "未找到预设配置，将使用通用模式"}

    return {
        "found": True,
        "name": preset.name,
        "type": preset.site_type,
        "login_required": bool(preset.login_check_cookie),
        "has_api_config": bool(preset.main_apis),
        "requires_signature": preset.requires_signature,
        "signature_params": preset.signature_params,
        "anti_scrape_notes": preset.anti_scrape_notes,
        "notes": preset.notes,
        "list_selector": preset.list_item_selector,
        "suggested_actions": preset.suggested_actions,
    }
