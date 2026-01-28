"""
签名服务器 - 本地高性能签名生成

核心思路：
1. 浏览器执行签名JS，本地缓存签名结果
2. 通过HTTP API提供签名服务
3. 毫秒级响应，支持高并发

使用场景：
1. 签名算法已逆向，需要高性能执行
2. 签名算法无法逆向，需要浏览器RPC
3. 多进程/多线程共享签名服务

启动方式：
    python -m unified_agent.sign_server --port 8765
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class SignType(Enum):
    """签名类型"""
    MD5 = "md5"
    SHA256 = "sha256"
    HMAC_SHA256 = "hmac_sha256"
    JD_H5ST = "jd_h5st"
    TAOBAO_SIGN = "taobao_sign"
    DOUYIN_XBOGUS = "douyin_xbogus"
    CUSTOM = "custom"


@dataclass
class SignRequest:
    """签名请求"""
    sign_type: str
    params: dict
    timestamp: Optional[int] = None
    extra: Optional[dict] = None


@dataclass
class SignResponse:
    """签名响应"""
    success: bool
    signature: Optional[str] = None
    signed_params: Optional[dict] = None
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class SignCacheEntry:
    """签名缓存条目"""
    key: str
    signature: str
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0


class SignatureCache:
    """签名缓存"""

    def __init__(self, max_size: int = 10000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, SignCacheEntry] = {}

    def _make_key(self, sign_type: str, params: dict) -> str:
        """生成缓存键"""
        content = f"{sign_type}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, sign_type: str, params: dict) -> Optional[str]:
        """获取缓存的签名"""
        key = self._make_key(sign_type, params)
        entry = self.cache.get(key)

        if entry and datetime.now() < entry.expires_at:
            entry.hit_count += 1
            return entry.signature

        # 过期则删除
        if entry:
            del self.cache[key]
        return None

    def set(self, sign_type: str, params: dict, signature: str, ttl: Optional[int] = None):
        """缓存签名"""
        # 清理过期条目
        if len(self.cache) >= self.max_size:
            self._cleanup()

        key = self._make_key(sign_type, params)
        ttl = ttl or self.default_ttl

        self.cache[key] = SignCacheEntry(
            key=key,
            signature=signature,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=ttl),
        )

    def _cleanup(self):
        """清理过期和最少使用的条目"""
        now = datetime.now()
        # 删除过期的
        expired = [k for k, v in self.cache.items() if v.expires_at < now]
        for k in expired:
            del self.cache[k]

        # 如果还是太多，删除命中最少的
        if len(self.cache) >= self.max_size:
            sorted_entries = sorted(self.cache.items(), key=lambda x: x[1].hit_count)
            to_remove = len(self.cache) - self.max_size // 2
            for k, _ in sorted_entries[:to_remove]:
                del self.cache[k]

    def stats(self) -> dict:
        """缓存统计"""
        total_hits = sum(e.hit_count for e in self.cache.values())
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
        }


class SignatureGenerator:
    """签名生成器"""

    def __init__(self):
        self.cache = SignatureCache()
        self.custom_signers: Dict[str, Callable] = {}
        self._register_builtin_signers()

    def _register_builtin_signers(self):
        """注册内置签名器"""
        self.custom_signers["md5"] = self._sign_md5
        self.custom_signers["sha256"] = self._sign_sha256
        self.custom_signers["hmac_sha256"] = self._sign_hmac_sha256

    def register_signer(self, sign_type: str, signer: Callable):
        """注册自定义签名器"""
        self.custom_signers[sign_type] = signer
        logger.info(f"[SignServer] Registered signer: {sign_type}")

    def sign(self, request: SignRequest) -> SignResponse:
        """生成签名"""
        start_time = time.time()

        try:
            # 检查缓存
            cached = self.cache.get(request.sign_type, request.params)
            if cached:
                return SignResponse(
                    success=True,
                    signature=cached,
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # 查找签名器
            signer = self.custom_signers.get(request.sign_type)
            if not signer:
                return SignResponse(
                    success=False,
                    error=f"Unknown sign type: {request.sign_type}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # 执行签名
            signature = signer(request.params, request.timestamp, request.extra)

            # 缓存结果
            self.cache.set(request.sign_type, request.params, signature)

            return SignResponse(
                success=True,
                signature=signature,
                signed_params={**request.params, "sign": signature},
                duration_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"[SignServer] Sign failed: {e}")
            return SignResponse(
                success=False,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )

    # ==================== 内置签名器 ====================

    def _sign_md5(self, params: dict, timestamp: Optional[int], extra: Optional[dict]) -> str:
        """MD5签名"""
        secret = extra.get("secret", "") if extra else ""
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        content = f"{param_str}{secret}"
        return hashlib.md5(content.encode()).hexdigest()

    def _sign_sha256(self, params: dict, timestamp: Optional[int], extra: Optional[dict]) -> str:
        """SHA256签名"""
        secret = extra.get("secret", "") if extra else ""
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        content = f"{param_str}{secret}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _sign_hmac_sha256(self, params: dict, timestamp: Optional[int], extra: Optional[dict]) -> str:
        """HMAC-SHA256签名"""
        import hmac
        secret = extra.get("secret", "").encode() if extra else b""
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        return hmac.new(secret, param_str.encode(), hashlib.sha256).hexdigest()


class BrowserRPCSigner:
    """浏览器RPC签名器

    用于无法逆向的签名算法，通过浏览器执行JS生成签名。
    """

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self._lock = asyncio.Lock()

    async def start(self):
        """启动浏览器"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("[BrowserRPC] Playwright not installed")
            return False

        pw = await async_playwright().start()
        self.browser = await pw.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

        # 注入反检测脚本
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}};
        """)

        logger.info("[BrowserRPC] Browser started")
        return True

    async def stop(self):
        """停止浏览器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None

    async def execute_js(self, js_code: str, *args) -> Any:
        """执行JS代码"""
        if not self.page:
            raise RuntimeError("Browser not started")

        async with self._lock:
            result = await self.page.evaluate(js_code, *args)
            return result

    async def sign_with_js(self, js_function: str, params: dict) -> str:
        """使用JS函数签名"""
        result = await self.execute_js(f"({js_function})(arguments[0])", params)
        return str(result)


# ==================== FastAPI 服务器 ====================

def create_app():
    """创建FastAPI应用"""
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
    except ImportError:
        logger.error("[SignServer] FastAPI not installed. Run: pip install fastapi uvicorn")
        return None

    app = FastAPI(title="Sign Server", description="本地签名服务")
    generator = SignatureGenerator()

    class SignRequestModel(BaseModel):
        sign_type: str
        params: dict
        timestamp: Optional[int] = None
        extra: Optional[dict] = None

    class SignResponseModel(BaseModel):
        success: bool
        signature: Optional[str] = None
        signed_params: Optional[dict] = None
        error: Optional[str] = None
        duration_ms: float = 0

    @app.post("/sign", response_model=SignResponseModel)
    async def sign(req: SignRequestModel):
        """生成签名"""
        request = SignRequest(
            sign_type=req.sign_type,
            params=req.params,
            timestamp=req.timestamp,
            extra=req.extra,
        )
        response = generator.sign(request)
        return SignResponseModel(**response.__dict__)

    @app.get("/stats")
    async def stats():
        """获取统计信息"""
        return {
            "cache": generator.cache.stats(),
            "signers": list(generator.custom_signers.keys()),
        }

    @app.get("/health")
    async def health():
        """健康检查"""
        return {"status": "ok", "time": datetime.now().isoformat()}

    return app


# ==================== 客户端 ====================

class SignClient:
    """签名服务客户端"""

    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url.rstrip("/")

    def sign(
        self,
        sign_type: str,
        params: dict,
        timestamp: Optional[int] = None,
        extra: Optional[dict] = None,
    ) -> SignResponse:
        """请求签名"""
        import httpx

        response = httpx.post(
            f"{self.base_url}/sign",
            json={
                "sign_type": sign_type,
                "params": params,
                "timestamp": timestamp,
                "extra": extra,
            },
            timeout=10.0,
        )

        data = response.json()
        return SignResponse(**data)

    def health(self) -> bool:
        """检查服务健康状态"""
        import httpx
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=5.0)
            return response.status_code == 200
        except:
            return False


# ==================== CLI 入口 ====================

def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Sign Server - 本地签名服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8765, help="监听端口")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("请先安装: pip install uvicorn")
        return

    app = create_app()
    if app:
        print(f"[SignServer] Starting on http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
