"""
基础设施模块 - 高效抓取基础设施

包含:
- ProxyPool: 代理池 (多代理轮换)
- CookiePool: Cookie池 (免费自动生成)
- SignatureGenerator: 签名服务 (本地高性能)
- MassiveDispatcher: 高并发调度器
"""

from .proxy import (
    ProxyManager,
    ProxyInfo,
    ProxyPool,
    ProxyType,
    ProxyEntry,
    create_kuaidaili_proxy,
    create_residential_proxy,
    list_proxy_providers,
)
from .cookie_pool import (
    CookiePool,
    CookiePoolManager,
    CookieSession,
    InfrastructureAdvisor,
)
from .sign_server import (
    SignatureGenerator,
    SignatureCache,
    SignClient,
    SignRequest,
    SignResponse,
    SignType,
    BrowserRPCSigner,
)
from .dispatcher import (
    MassiveDispatcher,
    DispatchResult,
    DispatchTask,
    TaskStatus,
    RateLimiter,
    batch_fetch,
)

__all__ = [
    # 代理
    "ProxyManager",
    "ProxyInfo",
    "ProxyPool",
    "ProxyType",
    "ProxyEntry",
    "create_kuaidaili_proxy",
    "create_residential_proxy",
    "list_proxy_providers",
    # Cookie池
    "CookiePool",
    "CookiePoolManager",
    "CookieSession",
    "InfrastructureAdvisor",
    # 签名服务
    "SignatureGenerator",
    "SignatureCache",
    "SignClient",
    "SignRequest",
    "SignResponse",
    "SignType",
    "BrowserRPCSigner",
    # 调度器
    "MassiveDispatcher",
    "DispatchResult",
    "DispatchTask",
    "TaskStatus",
    "RateLimiter",
    "batch_fetch",
]
