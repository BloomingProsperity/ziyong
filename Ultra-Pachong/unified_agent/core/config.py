"""
统一配置模块

集中管理所有配置项:
- 快代理 API 配置
- 浏览器配置
- 反检测配置
- 采集参数
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class AgentConfig:
    """Agent 统一配置"""

    # ============ 快代理配置 ============
    # 快代理隧道代理地址 (默认使用项目中的配置)
    kuaidaili_host: str = "z109.kdltps.com"
    kuaidaili_port: int = 15818
    kuaidaili_username: str = ""
    kuaidaili_password: str = ""

    # 是否启用代理
    proxy_enabled: bool = True

    # ============ 浏览器配置 ============
    headless: bool = True
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
    timeout_ms: int = 30000
    navigation_timeout_ms: int = 45000

    # ============ 反检测配置 ============
    stealth_enabled: bool = True
    randomize_fingerprint: bool = True
    locale: str = "zh-CN"
    timezone: str = "Asia/Shanghai"

    # User-Agent 池
    user_agents: list[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ])

    # 常见 viewport 尺寸
    viewports: list[dict] = field(default_factory=lambda: [
        {"width": 1920, "height": 1080},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1366, "height": 768},
    ])

    # ============ 采集配置 ============
    max_pages: int = 10  # 最大翻页数
    scroll_count: int = 5  # 滚动次数
    scroll_delay: float = 0.8  # 滚动间隔(秒)
    page_load_delay: float = 2.0  # 页面加载后等待时间

    # 重试配置
    max_retries: int = 3
    retry_delay_base_ms: int = 1000
    retry_delay_max_ms: int = 30000

    # ============ 数据存储 ============
    data_dir: Path = field(default_factory=lambda: Path("data/unified_agent"))
    sessions_dir: Path = field(default_factory=lambda: Path("data/scraper/sessions"))

    def __post_init__(self):
        """初始化后处理，支持从环境变量加载"""
        # 从环境变量加载快代理配置
        if not self.kuaidaili_username:
            self.kuaidaili_username = os.getenv("KUAIDAILI_USERNAME", "")
        if not self.kuaidaili_password:
            self.kuaidaili_password = os.getenv("KUAIDAILI_PASSWORD", "")
        if os.getenv("KUAIDAILI_HOST"):
            self.kuaidaili_host = os.getenv("KUAIDAILI_HOST", self.kuaidaili_host)
        if os.getenv("KUAIDAILI_PORT"):
            self.kuaidaili_port = int(os.getenv("KUAIDAILI_PORT", str(self.kuaidaili_port)))

        # 确保目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    @property
    def proxy_url(self) -> str | None:
        """获取完整的代理 URL"""
        if not self.proxy_enabled:
            return None
        if not self.kuaidaili_username or not self.kuaidaili_password:
            return None
        return f"http://{self.kuaidaili_username}:{self.kuaidaili_password}@{self.kuaidaili_host}:{self.kuaidaili_port}"

    @property
    def proxy_config(self) -> dict | None:
        """获取 Playwright 代理配置"""
        if not self.proxy_enabled:
            return None
        if not self.kuaidaili_username or not self.kuaidaili_password:
            return None
        return {
            "server": f"http://{self.kuaidaili_host}:{self.kuaidaili_port}",
            "username": self.kuaidaili_username,
            "password": self.kuaidaili_password,
        }

    def get_random_user_agent(self) -> str:
        """获取随机 User-Agent"""
        return random.choice(self.user_agents)

    def get_random_viewport(self) -> dict:
        """获取随机 viewport"""
        return random.choice(self.viewports)

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """从环境变量创建配置"""
        return cls(
            kuaidaili_host=os.getenv("KUAIDAILI_HOST", "z109.kdltps.com"),
            kuaidaili_port=int(os.getenv("KUAIDAILI_PORT", "15818")),
            kuaidaili_username=os.getenv("KUAIDAILI_USERNAME", ""),
            kuaidaili_password=os.getenv("KUAIDAILI_PASSWORD", ""),
            proxy_enabled=os.getenv("PROXY_ENABLED", "true").lower() in ("true", "1", "yes"),
            headless=os.getenv("HEADLESS", "true").lower() in ("true", "1", "yes"),
            max_pages=int(os.getenv("MAX_PAGES", "10")),
        )

    @classmethod
    def for_kuaidaili(cls, username: str, password: str, **kwargs) -> "AgentConfig":
        """快速创建快代理配置"""
        return cls(
            kuaidaili_username=username,
            kuaidaili_password=password,
            proxy_enabled=True,
            **kwargs,
        )
