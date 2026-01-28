"""
代理管理模块

统一管理代理配置，支持:
- 快代理隧道代理 (kdltps.com)
- 住宅代理 (Luminati/Bright Data, Smartproxy, Oxylabs等)
- 代理池 (多代理轮换)
- 代理健康检查
- 代理质量评估

代理类型说明：
- 数据中心代理: 速度快、价格低、易被检测
- 住宅代理: IP信誉高、不易封禁、价格较高
- 移动代理: 最高信誉、最难检测、价格最高
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, List, Dict
from enum import Enum

import httpx

if TYPE_CHECKING:
    from .config import AgentConfig

logger = logging.getLogger(__name__)


class ProxyType(Enum):
    """代理类型"""
    DATACENTER = "datacenter"      # 数据中心代理
    RESIDENTIAL = "residential"    # 住宅代理
    MOBILE = "mobile"              # 移动代理
    ISP = "isp"                    # ISP代理


@dataclass
class ProxyInfo:
    """代理信息"""
    server: str
    username: str | None = None
    password: str | None = None

    @property
    def url(self) -> str:
        """获取完整代理 URL"""
        if self.username and self.password:
            return f"http://{self.username}:{self.password}@{self.server}"
        return f"http://{self.server}"

    @property
    def playwright_config(self) -> dict:
        """获取 Playwright 格式的代理配置"""
        config = {"server": f"http://{self.server}"}
        if self.username:
            config["username"] = self.username
        if self.password:
            config["password"] = self.password
        return config

    @property
    def httpx_config(self) -> str:
        """获取 httpx 格式的代理配置"""
        return self.url


class ProxyManager:
    """代理管理器"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self._current_proxy: ProxyInfo | None = None

    @property
    def enabled(self) -> bool:
        """代理是否启用"""
        return (
            self.config.proxy_enabled
            and bool(self.config.kuaidaili_username)
            and bool(self.config.kuaidaili_password)
        )

    def get_proxy(self) -> ProxyInfo | None:
        """获取代理信息"""
        if not self.enabled:
            return None

        if self._current_proxy is None:
            self._current_proxy = ProxyInfo(
                server=f"{self.config.kuaidaili_host}:{self.config.kuaidaili_port}",
                username=self.config.kuaidaili_username,
                password=self.config.kuaidaili_password,
            )

        return self._current_proxy

    def get_playwright_proxy(self) -> dict | None:
        """获取 Playwright 格式代理配置"""
        proxy = self.get_proxy()
        return proxy.playwright_config if proxy else None

    def get_httpx_proxy(self) -> str | None:
        """获取 httpx 格式代理配置"""
        proxy = self.get_proxy()
        return proxy.httpx_config if proxy else None

    async def check_proxy_health(self, timeout: float = 10.0) -> bool:
        """
        检查代理健康状态

        Args:
            timeout: 超时时间(秒)

        Returns:
            代理是否可用
        """
        proxy = self.get_proxy()
        if not proxy:
            return False

        try:
            async with httpx.AsyncClient(
                proxy=proxy.httpx_config,
                timeout=timeout,
            ) as client:
                response = await client.get("https://httpbin.org/ip")
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Proxy health check passed. IP: {data.get('origin')}")
                    return True
        except Exception as e:
            logger.warning(f"Proxy health check failed: {e}")

        return False

    def check_proxy_health_sync(self, timeout: float = 10.0) -> bool:
        """
        同步检查代理健康状态

        Args:
            timeout: 超时时间(秒)

        Returns:
            代理是否可用
        """
        proxy = self.get_proxy()
        if not proxy:
            logger.info("No proxy configured, skipping health check")
            return True  # 没有配置代理时返回 True

        try:
            # httpx 0.24+ 使用 proxy 参数
            with httpx.Client(
                proxy=proxy.httpx_config,
                timeout=timeout,
            ) as client:
                response = client.get("https://httpbin.org/ip")
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Proxy health check passed. IP: {data.get('origin')}")
                    return True
        except Exception as e:
            logger.warning(f"Proxy health check failed: {e}")

        return False


def create_kuaidaili_proxy(
    username: str,
    password: str,
    host: str = "z109.kdltps.com",
    port: int = 15818,
) -> ProxyInfo:
    """
    创建快代理配置

    Args:
        username: 快代理用户名
        password: 快代理密码
        host: 快代理主机地址
        port: 快代理端口

    Returns:
        ProxyInfo 对象
    """
    return ProxyInfo(
        server=f"{host}:{port}",
        username=username,
        password=password,
    )


# ==================== 代理池 ====================

@dataclass
class ProxyEntry:
    """代理池条目"""
    proxy: ProxyInfo
    proxy_type: ProxyType = ProxyType.DATACENTER
    success_count: int = 0
    fail_count: int = 0
    last_used: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    avg_response_time: float = 0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 0.5

    @property
    def is_available(self) -> bool:
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            return False
        return True

    def mark_success(self, response_time: float = 0):
        self.success_count += 1
        self.last_used = datetime.now()
        if response_time > 0:
            # 移动平均
            self.avg_response_time = (self.avg_response_time * 0.7 + response_time * 0.3)

    def mark_failed(self, cooldown_seconds: int = 60):
        self.fail_count += 1
        self.last_used = datetime.now()
        # 失败后冷却
        if self.fail_count >= 3:
            self.cooldown_until = datetime.now() + timedelta(seconds=cooldown_seconds)


class ProxyPool:
    """
    代理池 - 支持多代理轮换

    功能：
    - 多代理轮换
    - 自动故障转移
    - 智能负载均衡
    - 质量评估
    """

    def __init__(self):
        self.proxies: List[ProxyEntry] = []
        self._index = 0

    def add(
        self,
        server: str,
        username: str = None,
        password: str = None,
        proxy_type: ProxyType = ProxyType.DATACENTER,
    ):
        """添加代理"""
        proxy = ProxyInfo(server=server, username=username, password=password)
        entry = ProxyEntry(proxy=proxy, proxy_type=proxy_type)
        self.proxies.append(entry)
        logger.info(f"[ProxyPool] Added proxy: {server} ({proxy_type.value})")

    def add_list(self, proxies: List[Dict]):
        """批量添加代理

        Args:
            proxies: 代理列表，格式:
                [
                    {"server": "ip:port", "username": "u", "password": "p", "type": "residential"},
                    ...
                ]
        """
        for p in proxies:
            proxy_type = ProxyType(p.get("type", "datacenter"))
            self.add(
                server=p["server"],
                username=p.get("username"),
                password=p.get("password"),
                proxy_type=proxy_type,
            )

    def get(self, prefer_residential: bool = False) -> Optional[str]:
        """
        获取一个可用代理

        Args:
            prefer_residential: 是否优先住宅代理

        Returns:
            代理URL字符串
        """
        if not self.proxies:
            return None

        # 过滤可用代理
        available = [p for p in self.proxies if p.is_available]
        if not available:
            return None

        # 优先住宅代理
        if prefer_residential:
            residential = [p for p in available if p.proxy_type == ProxyType.RESIDENTIAL]
            if residential:
                available = residential

        # 按成功率排序
        available.sort(key=lambda x: x.success_rate, reverse=True)

        # 加权随机选择（成功率高的权重大）
        if len(available) > 1:
            weights = [p.success_rate + 0.1 for p in available]
            entry = random.choices(available, weights=weights, k=1)[0]
        else:
            entry = available[0]

        return entry.proxy.url

    def get_entry(self, proxy_url: str) -> Optional[ProxyEntry]:
        """根据URL获取代理条目"""
        for entry in self.proxies:
            if entry.proxy.url == proxy_url:
                return entry
        return None

    def mark_success(self, proxy_url: str, response_time: float = 0):
        """标记代理成功"""
        entry = self.get_entry(proxy_url)
        if entry:
            entry.mark_success(response_time)

    def mark_failed(self, proxy_url: str):
        """标记代理失败"""
        entry = self.get_entry(proxy_url)
        if entry:
            entry.mark_failed()

    def stats(self) -> Dict:
        """获取统计信息"""
        by_type = {}
        for entry in self.proxies:
            t = entry.proxy_type.value
            if t not in by_type:
                by_type[t] = {"count": 0, "available": 0}
            by_type[t]["count"] += 1
            if entry.is_available:
                by_type[t]["available"] += 1

        return {
            "total": len(self.proxies),
            "available": sum(1 for p in self.proxies if p.is_available),
            "by_type": by_type,
            "avg_success_rate": sum(p.success_rate for p in self.proxies) / len(self.proxies) if self.proxies else 0,
        }

    def remove_bad(self, min_success_rate: float = 0.3, min_requests: int = 10):
        """移除低质量代理"""
        to_remove = []
        for entry in self.proxies:
            total = entry.success_count + entry.fail_count
            if total >= min_requests and entry.success_rate < min_success_rate:
                to_remove.append(entry)

        for entry in to_remove:
            self.proxies.remove(entry)
            logger.info(f"[ProxyPool] Removed bad proxy: {entry.proxy.server} (rate: {entry.success_rate:.1%})")


# ==================== 住宅代理服务商配置 ====================

RESIDENTIAL_PROVIDERS = {
    "brightdata": {
        "name": "Bright Data (Luminati)",
        "format": "http://{username}:{password}@brd.superproxy.io:{port}",
        "default_port": 22225,
        "features": ["residential", "datacenter", "mobile"],
        "docs": "https://brightdata.com/",
    },
    "smartproxy": {
        "name": "Smartproxy",
        "format": "http://{username}:{password}@gate.smartproxy.com:{port}",
        "default_port": 7000,
        "features": ["residential", "datacenter"],
        "docs": "https://smartproxy.com/",
    },
    "oxylabs": {
        "name": "Oxylabs",
        "format": "http://{username}:{password}@pr.oxylabs.io:{port}",
        "default_port": 7777,
        "features": ["residential", "datacenter", "mobile"],
        "docs": "https://oxylabs.io/",
    },
    "ipidea": {
        "name": "IPIDEA",
        "format": "http://{username}:{password}@proxy.ipidea.io:{port}",
        "default_port": 2333,
        "features": ["residential"],
        "docs": "https://www.ipidea.net/",
    },
}


def create_residential_proxy(
    provider: str,
    username: str,
    password: str,
    port: int = None,
    country: str = None,
    session: str = None,
) -> ProxyInfo:
    """
    创建住宅代理配置

    Args:
        provider: 服务商 (brightdata/smartproxy/oxylabs/ipidea)
        username: 用户名
        password: 密码
        port: 端口（可选，使用默认）
        country: 国家代码（如 cn, us）
        session: 会话ID（保持同一IP）

    Returns:
        ProxyInfo 对象

    示例:
        # Bright Data
        proxy = create_residential_proxy(
            provider="brightdata",
            username="your_username",
            password="your_password",
            country="cn"
        )
    """
    if provider not in RESIDENTIAL_PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}. Supported: {list(RESIDENTIAL_PROVIDERS.keys())}")

    config = RESIDENTIAL_PROVIDERS[provider]
    port = port or config["default_port"]

    # 构造用户名（带国家/会话）
    final_username = username
    if country:
        final_username += f"-country-{country}"
    if session:
        final_username += f"-session-{session}"

    # 解析服务器地址
    server = config["format"].format(
        username=final_username,
        password=password,
        port=port
    ).replace("http://", "").split("@")[1]

    return ProxyInfo(
        server=server,
        username=final_username,
        password=password,
    )


def list_proxy_providers() -> Dict:
    """列出支持的代理服务商"""
    return {k: {"name": v["name"], "features": v["features"]} for k, v in RESIDENTIAL_PROVIDERS.items()}
