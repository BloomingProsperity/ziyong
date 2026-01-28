"""
签名模块 - 加密参数生成与签名管理

核心功能:
1. 标准签名算法 (OAuth1/JWT/HMAC/AWS等)
2. 平台签名支持 (B站WBI/京东H5ST/抖音X-Bogus等)
3. 签名类型自动检测
4. 签名缓存与验证
5. 错误码统一处理

作者: Ultra Pachong Team
文档: unified_agent/skills/03-signature.md
"""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from urllib.parse import quote, urlencode, parse_qs, urlparse

logger = logging.getLogger(__name__)


# ==================== 错误码定义 ====================

class SignatureErrorCode(str, Enum):
    """签名错误码 (来自03-signature.md)"""
    E_SIG_001 = "E_SIG_001"  # 未检测到签名参数
    E_SIG_002 = "E_SIG_002"  # 签名类型识别失败
    E_SIG_003 = "E_SIG_003"  # 缺少必要凭据
    E_SIG_004 = "E_SIG_004"  # 算法实现不可用
    E_SIG_005 = "E_SIG_005"  # 签名验证失败(403)
    E_SIG_006 = "E_SIG_006"  # 时间戳同步失败
    E_SIG_007 = "E_SIG_007"  # JS执行超时
    E_SIG_008 = "E_SIG_008"  # RPC服务不可用


class SignatureException(Exception):
    """签名异常基类"""
    def __init__(self, code: SignatureErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code.value}] {message}")


# ==================== 数据类型定义 ====================

class SignType(str, Enum):
    """签名类型"""
    # 标准签名
    OAUTH1 = "oauth1"
    OAUTH2 = "oauth2"
    JWT = "jwt"
    HMAC_SHA256 = "hmac_sha256"
    MD5 = "md5"
    SHA256 = "sha256"
    AWS_V4 = "aws_v4"

    # 平台签名
    BILIBILI_WBI = "bilibili_wbi"
    JD_H5ST = "jd_h5st"
    DOUYIN_XBOGUS = "douyin_xbogus"
    XIAOHONGSHU_XS = "xiaohongshu_xs"
    ZHIHU_ZSE96 = "zhihu_zse96"

    # 其他
    CUSTOM = "custom"
    AUTO = "auto"


class SignApproach(str, Enum):
    """签名方案"""
    PURE_ALGO = "pure_algo"      # 纯算法实现
    JS_EXEC = "js_exec"          # JavaScript执行
    RPC = "rpc"                  # RPC调用
    BROWSER = "browser"          # 浏览器执行


@dataclass
class SignatureResult:
    """签名生成结果"""
    status: str  # success / partial / failed
    signature: Optional[str] = None
    signed_params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    approach: SignApproach = SignApproach.PURE_ALGO
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "status": self.status,
            "signature": self.signature,
            "signed_params": self.signed_params,
            "headers": self.headers,
            "approach": self.approach.value if isinstance(self.approach, SignApproach) else self.approach,
            "metadata": self.metadata,
            "warnings": self.warnings,
            "errors": self.errors,
        }


@dataclass
class SignatureRequest:
    """签名请求"""
    params: Dict[str, Any]
    sign_type: str = "auto"
    credentials: Dict[str, Any] = field(default_factory=dict)
    algorithm_impl: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)

    # HTTP相关信息(用于某些签名算法)
    method: str = "GET"
    url: Optional[str] = None


# ==================== 签名缓存 ====================

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    result: SignatureResult
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0


class SignatureCache:
    """签名缓存 - 基于TTL的LRU缓存"""

    def __init__(self, max_size: int = 10000, default_ttl: int = 300):
        """
        初始化缓存

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认TTL(秒)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}

    def _make_key(self, request: SignatureRequest) -> str:
        """生成缓存键"""
        content = json.dumps({
            "sign_type": request.sign_type,
            "params": sorted(request.params.items()),
            "credentials_hash": hashlib.md5(
                json.dumps(sorted(request.credentials.items())).encode()
            ).hexdigest() if request.credentials else ""
        }, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, request: SignatureRequest) -> Optional[SignatureResult]:
        """获取缓存的签名"""
        key = self._make_key(request)
        entry = self.cache.get(key)

        if entry and datetime.now() < entry.expires_at:
            entry.hit_count += 1
            logger.debug(f"[SignCache] Cache hit: {key[:8]}... (hits: {entry.hit_count})")
            return entry.result

        # 过期则删除
        if entry:
            del self.cache[key]
            logger.debug(f"[SignCache] Cache expired: {key[:8]}...")

        return None

    def set(self, request: SignatureRequest, result: SignatureResult, ttl: Optional[int] = None):
        """缓存签名"""
        # 只缓存成功的结果
        if result.status != "success":
            return

        # 清理过期条目
        if len(self.cache) >= self.max_size:
            self._cleanup()

        key = self._make_key(request)
        ttl = ttl or self.default_ttl

        self.cache[key] = CacheEntry(
            key=key,
            result=result,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=ttl),
        )

        logger.debug(f"[SignCache] Cached: {key[:8]}... (TTL: {ttl}s)")

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

        logger.info(f"[SignCache] Cleaned up, current size: {len(self.cache)}")

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("[SignCache] Cache cleared")

    def stats(self) -> dict:
        """缓存统计"""
        total_hits = sum(e.hit_count for e in self.cache.values())
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
            "avg_hits": total_hits / len(self.cache) if self.cache else 0,
        }


# ==================== 签名生成器基类 ====================

class SignatureGenerator(ABC):
    """签名生成器基类"""

    def __init__(self):
        self.name = self.__class__.__name__

    @abstractmethod
    def generate(self, request: SignatureRequest) -> SignatureResult:
        """
        生成签名

        Args:
            request: 签名请求

        Returns:
            签名结果
        """
        raise NotImplementedError

    def _create_success(
        self,
        signature: str,
        signed_params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        approach: SignApproach = SignApproach.PURE_ALGO,
        **metadata
    ) -> SignatureResult:
        """创建成功结果"""
        return SignatureResult(
            status="success",
            signature=signature,
            signed_params=signed_params,
            headers=headers,
            approach=approach,
            metadata=metadata,
        )

    def _create_error(
        self,
        error: str,
        code: Optional[SignatureErrorCode] = None,
        **metadata
    ) -> SignatureResult:
        """创建错误结果"""
        return SignatureResult(
            status="failed",
            errors=[error],
            metadata={"error_code": code.value if code else None, **metadata},
        )

    def verify(self, params: dict, signature: str, **kwargs) -> bool:
        """
        验证签名是否正确

        Args:
            params: 参数字典
            signature: 签名字符串
            **kwargs: 其他验证参数

        Returns:
            是否验证通过
        """
        # 默认实现：重新生成签名并比较
        try:
            request = SignatureRequest(params=params, **kwargs)
            result = self.generate(request)
            return result.status == "success" and result.signature == signature
        except:
            return False


# ==================== 标准签名算法实现 ====================

class MD5Generator(SignatureGenerator):
    """MD5签名生成器 - 简单场景"""

    def generate(self, request: SignatureRequest) -> SignatureResult:
        """
        生成MD5签名

        算法: MD5(sorted_params + secret)
        """
        try:
            secret = request.credentials.get("secret", "")
            sorted_params = sorted(request.params.items())
            param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
            content = f"{param_str}{secret}"

            signature = hashlib.md5(content.encode()).hexdigest()

            signed_params = request.params.copy()
            signed_params["sign"] = signature

            return self._create_success(
                signature=signature,
                signed_params=signed_params,
                algorithm="MD5",
                input_length=len(content),
            )

        except Exception as e:
            return self._create_error(
                f"MD5签名失败: {e}",
                code=SignatureErrorCode.E_SIG_004,
            )


class HMACGenerator(SignatureGenerator):
    """HMAC-SHA256签名生成器"""

    def generate(self, request: SignatureRequest) -> SignatureResult:
        """
        生成HMAC-SHA256签名

        算法: HMAC-SHA256(sorted_params, secret)
        """
        try:
            secret = request.credentials.get("secret", "")
            if not secret:
                return self._create_error(
                    "缺少secret密钥",
                    code=SignatureErrorCode.E_SIG_003,
                )

            sorted_params = sorted(request.params.items())
            param_str = "&".join(f"{k}={v}" for k, v in sorted_params)

            signature = hmac.new(
                secret.encode(),
                param_str.encode(),
                hashlib.sha256
            ).hexdigest()

            signed_params = request.params.copy()
            signed_params["sign"] = signature

            return self._create_success(
                signature=signature,
                signed_params=signed_params,
                algorithm="HMAC-SHA256",
            )

        except Exception as e:
            return self._create_error(
                f"HMAC签名失败: {e}",
                code=SignatureErrorCode.E_SIG_004,
            )


class OAuth1Generator(SignatureGenerator):
    """OAuth 1.0签名生成器"""

    def generate(self, request: SignatureRequest) -> SignatureResult:
        """
        生成OAuth 1.0签名

        算法: HMAC-SHA1
        文档: https://oauth.net/core/1.0a/#signing_process
        """
        try:
            # 验证必要凭据
            consumer_key = request.credentials.get("consumer_key")
            consumer_secret = request.credentials.get("consumer_secret")
            token = request.credentials.get("token", "")
            token_secret = request.credentials.get("token_secret", "")

            if not consumer_key or not consumer_secret:
                return self._create_error(
                    "缺少consumer_key或consumer_secret",
                    code=SignatureErrorCode.E_SIG_003,
                )

            # 构造OAuth参数
            oauth_params = {
                "oauth_consumer_key": consumer_key,
                "oauth_signature_method": "HMAC-SHA1",
                "oauth_timestamp": str(int(time.time())),
                "oauth_nonce": uuid.uuid4().hex,
                "oauth_version": "1.0",
            }

            if token:
                oauth_params["oauth_token"] = token

            # 合并所有参数
            all_params = {**request.params, **oauth_params}

            # 参数排序并编码
            sorted_params = sorted(all_params.items())
            param_str = "&".join(
                f"{quote(str(k), safe='')}={quote(str(v), safe='')}"
                for k, v in sorted_params
            )

            # 构造签名基字符串
            method = request.method.upper()
            url = request.url or ""
            base_string = f"{method}&{quote(url, safe='')}&{quote(param_str, safe='')}"

            # 构造签名密钥
            signing_key = f"{quote(consumer_secret, safe='')}&{quote(token_secret, safe='')}"

            # 生成签名
            signature = hmac.new(
                signing_key.encode(),
                base_string.encode(),
                hashlib.sha1
            ).digest()

            # Base64编码
            import base64
            signature_b64 = base64.b64encode(signature).decode()

            oauth_params["oauth_signature"] = signature_b64

            # 构造Authorization头
            auth_header = "OAuth " + ", ".join(
                f'{k}="{quote(str(v), safe="")}"'
                for k, v in sorted(oauth_params.items())
            )

            return self._create_success(
                signature=signature_b64,
                signed_params=all_params,
                headers={"Authorization": auth_header},
                algorithm="OAuth1-HMAC-SHA1",
            )

        except Exception as e:
            logger.exception("OAuth1签名失败")
            return self._create_error(
                f"OAuth1签名失败: {e}",
                code=SignatureErrorCode.E_SIG_004,
            )


class JWTGenerator(SignatureGenerator):
    """JWT Token生成器"""

    def generate(self, request: SignatureRequest) -> SignatureResult:
        """
        生成JWT Token

        需要安装: pip install PyJWT
        """
        try:
            import jwt
        except ImportError:
            return self._create_error(
                "缺少PyJWT库，请安装: pip install PyJWT",
                code=SignatureErrorCode.E_SIG_004,
            )

        try:
            secret_key = request.credentials.get("secret_key")
            if not secret_key:
                return self._create_error(
                    "缺少secret_key",
                    code=SignatureErrorCode.E_SIG_003,
                )

            algorithm = request.options.get("algorithm", "HS256")

            # 构造payload
            payload = request.params.copy()

            # 添加标准claims
            if "exp" not in payload:
                exp_seconds = request.options.get("expires_in", 3600)
                payload["exp"] = int(time.time()) + exp_seconds

            if "iat" not in payload:
                payload["iat"] = int(time.time())

            # 生成token
            token = jwt.encode(payload, secret_key, algorithm=algorithm)

            return self._create_success(
                signature=token,
                signed_params=payload,
                headers={"Authorization": f"Bearer {token}"},
                algorithm=f"JWT-{algorithm}",
            )

        except Exception as e:
            return self._create_error(
                f"JWT生成失败: {e}",
                code=SignatureErrorCode.E_SIG_004,
            )


# ==================== 平台签名实现 ====================

class BilibiliWBIGenerator(SignatureGenerator):
    """B站WBI签名生成器

    算法: MD5(sorted_params + mixin_key)
    文档: 03-signature.md
    """

    # 混淆表
    MIXIN_KEY_ENC_TAB = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
        27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13
    ]

    def _get_mixin_key(self, orig: str) -> str:
        """根据混淆表生成mixin_key"""
        return ''.join(orig[i] for i in self.MIXIN_KEY_ENC_TAB)[:32]

    def generate(self, request: SignatureRequest) -> SignatureResult:
        """
        生成B站WBI签名

        需要: img_key, sub_key (通过API获取)
        """
        try:
            img_key = request.credentials.get("img_key")
            sub_key = request.credentials.get("sub_key")

            if not img_key or not sub_key:
                return self._create_error(
                    "缺少img_key或sub_key，需要先调用nav接口获取",
                    code=SignatureErrorCode.E_SIG_003,
                )

            # 生成mixin_key
            mixin_key = self._get_mixin_key(img_key + sub_key)

            # 添加时间戳
            params = request.params.copy()
            params['wts'] = int(time.time())

            # 参数排序
            params = dict(sorted(params.items()))

            # 生成签名
            query = urlencode(params)
            w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()

            params['w_rid'] = w_rid

            return self._create_success(
                signature=w_rid,
                signed_params=params,
                algorithm="Bilibili-WBI-MD5",
                mixin_key=mixin_key[:8] + "...",  # 不完整显示密钥
            )

        except Exception as e:
            return self._create_error(
                f"B站WBI签名失败: {e}",
                code=SignatureErrorCode.E_SIG_004,
            )


class CustomJSGenerator(SignatureGenerator):
    """自定义JS签名生成器 - 执行用户提供的算法代码"""

    def generate(self, request: SignatureRequest) -> SignatureResult:
        """
        使用自定义JS代码生成签名

        需要: algorithm_impl (JS代码)
        """
        algorithm_impl = request.algorithm_impl

        if not algorithm_impl:
            return self._create_error(
                "缺少算法实现代码",
                code=SignatureErrorCode.E_SIG_004,
            )

        # 尝试使用js2py执行
        try:
            import js2py
        except ImportError:
            return self._create_error(
                "缺少js2py库，请安装: pip install js2py",
                code=SignatureErrorCode.E_SIG_004,
            )

        try:
            # 执行JS代码
            context = js2py.EvalJs()
            context.execute(algorithm_impl)

            # 调用签名函数（假设函数名为sign）
            signature = context.sign(request.params)

            signed_params = request.params.copy()
            signed_params["sign"] = signature

            return self._create_success(
                signature=str(signature),
                signed_params=signed_params,
                approach=SignApproach.JS_EXEC,
                algorithm="Custom-JS",
            )

        except Exception as e:
            return self._create_error(
                f"JS执行失败: {e}",
                code=SignatureErrorCode.E_SIG_007,
            )


# ==================== 签名管理器 ====================

class SignatureManager:
    """签名管理器 - 统一的签名生成入口"""

    def __init__(self, enable_cache: bool = True):
        """
        初始化签名管理器

        Args:
            enable_cache: 是否启用缓存
        """
        self.generators: Dict[str, SignatureGenerator] = {}
        self.cache = SignatureCache() if enable_cache else None
        self._register_builtin_generators()

        logger.info(f"[SignManager] Initialized with {len(self.generators)} generators")

    def _register_builtin_generators(self):
        """注册内置签名生成器"""
        self.register(SignType.MD5, MD5Generator())
        self.register(SignType.HMAC_SHA256, HMACGenerator())
        self.register(SignType.OAUTH1, OAuth1Generator())
        self.register(SignType.JWT, JWTGenerator())
        self.register(SignType.BILIBILI_WBI, BilibiliWBIGenerator())
        self.register(SignType.CUSTOM, CustomJSGenerator())

    def register(self, sign_type: str, generator: SignatureGenerator):
        """
        注册签名生成器

        Args:
            sign_type: 签名类型
            generator: 生成器实例
        """
        if isinstance(sign_type, SignType):
            sign_type = sign_type.value

        self.generators[sign_type] = generator
        logger.info(f"[SignManager] Registered generator: {sign_type} -> {generator.name}")

    def generate(self, request: SignatureRequest) -> SignatureResult:
        """
        生成签名（主入口）

        Args:
            request: 签名请求

        Returns:
            签名结果
        """
        start_time = time.time()

        try:
            # 自动检测签名类型
            if request.sign_type == SignType.AUTO:
                detected = self.detect_signature_type(request.params)
                if detected:
                    request.sign_type = detected
                    logger.info(f"[SignManager] Auto-detected sign type: {detected}")
                else:
                    return SignatureResult(
                        status="failed",
                        errors=["无法自动检测签名类型，请手动指定sign_type"],
                        metadata={"error_code": SignatureErrorCode.E_SIG_002.value},
                    )

            # 检查缓存
            if self.cache:
                cached = self.cache.get(request)
                if cached:
                    cached.metadata["from_cache"] = True
                    return cached

            # 查找生成器
            generator = self.generators.get(request.sign_type)
            if not generator:
                return SignatureResult(
                    status="failed",
                    errors=[f"不支持的签名类型: {request.sign_type}"],
                    metadata={
                        "error_code": SignatureErrorCode.E_SIG_002.value,
                        "available_types": list(self.generators.keys()),
                    },
                )

            # 生成签名
            result = generator.generate(request)

            # 记录时间
            duration_ms = (time.time() - start_time) * 1000
            result.metadata["duration_ms"] = duration_ms
            result.metadata["generator"] = generator.name

            # 缓存结果
            if self.cache and result.status == "success":
                self.cache.set(request, result)

            logger.info(
                f"[SignManager] Generated signature: "
                f"type={request.sign_type}, "
                f"status={result.status}, "
                f"duration={duration_ms:.2f}ms"
            )

            return result

        except Exception as e:
            logger.exception("签名生成异常")
            return SignatureResult(
                status="failed",
                errors=[f"签名生成异常: {e}"],
                metadata={
                    "error_code": SignatureErrorCode.E_SIG_004.value,
                    "duration_ms": (time.time() - start_time) * 1000,
                },
            )

    def detect_signature_type(self, params: dict) -> Optional[str]:
        """
        自动检测签名类型

        Args:
            params: 参数字典

        Returns:
            检测到的签名类型，如果无法检测则返回None
        """
        # 检查OAuth参数
        if "oauth_consumer_key" in params or "oauth_signature" in params:
            return SignType.OAUTH1.value

        # 检查JWT
        if "Authorization" in params and params["Authorization"].startswith("Bearer "):
            return SignType.JWT.value

        # 检查B站WBI
        if "w_rid" in params or "wts" in params:
            return SignType.BILIBILI_WBI.value

        # 检查京东h5st
        if "h5st" in params:
            return SignType.JD_H5ST.value

        # 检查抖音X-Bogus
        if "X-Bogus" in params or "x-bogus" in params:
            return SignType.DOUYIN_XBOGUS.value

        # 默认通用签名参数
        common_sign_params = ["sign", "signature", "sig"]
        if any(k in params for k in common_sign_params):
            return SignType.MD5.value  # 默认尝试MD5

        return None

    def verify_signature(
        self,
        params: dict,
        signature: str,
        sign_type: str,
        **kwargs
    ) -> bool:
        """
        验证签名是否正确

        Args:
            params: 参数字典
            signature: 签名字符串
            sign_type: 签名类型
            **kwargs: 其他验证参数

        Returns:
            是否验证通过
        """
        generator = self.generators.get(sign_type)
        if not generator:
            logger.warning(f"[SignManager] Unknown sign type for verification: {sign_type}")
            return False

        return generator.verify(params, signature, **kwargs)

    def clear_cache(self):
        """清空缓存"""
        if self.cache:
            self.cache.clear()

    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {
            "generators": list(self.generators.keys()),
            "generator_count": len(self.generators),
        }

        if self.cache:
            stats["cache"] = self.cache.stats()

        return stats


# ==================== 工具函数 ====================

def detect_signature_params(params: dict) -> List[str]:
    """
    检测参数中的签名字段

    Args:
        params: 参数字典

    Returns:
        签名参数名列表
    """
    # 常见签名参数名（来自03-signature.md）
    SIGNATURE_PARAMS = {
        # 通用类
        "sign", "signature", "sig", "hash", "token", "auth",
        # 时间类
        "timestamp", "ts", "t", "time", "_t",
        # 随机类
        "nonce", "random", "r", "_",
        # 平台特定
        "h5st", "x-sign", "x-mini-wua", "anti-content",
        "x-bogus", "a_bogus", "X-s", "X-t", "x-s-common",
        "wbi", "w_rid", "x-zse-96", "x-zse-93",
        # OAuth
        "oauth_signature", "oauth_token", "oauth_consumer_key",
    }

    detected = []
    for key in params.keys():
        if key in SIGNATURE_PARAMS or key.lower() in SIGNATURE_PARAMS:
            detected.append(key)

    return detected


def create_signature_manager(enable_cache: bool = True) -> SignatureManager:
    """
    创建签名管理器（便捷函数）

    Args:
        enable_cache: 是否启用缓存

    Returns:
        签名管理器实例
    """
    return SignatureManager(enable_cache=enable_cache)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    # 创建签名管理器
    manager = create_signature_manager()

    # 示例1: MD5签名
    print("\n=== MD5签名示例 ===")
    request1 = SignatureRequest(
        params={"user_id": "123", "action": "login"},
        sign_type=SignType.MD5,
        credentials={"secret": "my_secret_key"},
    )
    result1 = manager.generate(request1)
    print(f"Status: {result1.status}")
    print(f"Signature: {result1.signature}")
    print(f"Signed Params: {result1.signed_params}")

    # 示例2: HMAC-SHA256签名
    print("\n=== HMAC-SHA256签名示例 ===")
    request2 = SignatureRequest(
        params={"api_key": "abc123", "timestamp": str(int(time.time()))},
        sign_type=SignType.HMAC_SHA256,
        credentials={"secret": "hmac_secret"},
    )
    result2 = manager.generate(request2)
    print(f"Status: {result2.status}")
    print(f"Signature: {result2.signature}")

    # 示例3: B站WBI签名
    print("\n=== B站WBI签名示例 ===")
    request3 = SignatureRequest(
        params={"mid": "123456", "pn": "1", "ps": "20"},
        sign_type=SignType.BILIBILI_WBI,
        credentials={
            "img_key": "0123456789abcdefghijklmnopqrstuvwxyz0123456789ab",
            "sub_key": "fedcba9876543210fedcba9876543210fedcba9876543210",
        },
    )
    result3 = manager.generate(request3)
    print(f"Status: {result3.status}")
    print(f"Signature: {result3.signature}")
    print(f"Signed Params: {result3.signed_params}")

    # 示例4: 自动检测
    print("\n=== 自动检测签名类型 ===")
    request4 = SignatureRequest(
        params={"w_rid": "", "wts": str(int(time.time()))},
        sign_type=SignType.AUTO,
    )
    detected_type = manager.detect_signature_type(request4.params)
    print(f"Detected Type: {detected_type}")

    # 统计信息
    print("\n=== 统计信息 ===")
    stats = manager.get_stats()
    print(f"Available Generators: {stats['generator_count']}")
    print(f"Types: {', '.join(stats['generators'])}")
    print(f"Cache Stats: {stats.get('cache', 'N/A')}")
