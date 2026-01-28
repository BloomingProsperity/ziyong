"""
签名模块 - 标准签名器

实现标准签名算法：MD5, SHA, HMAC, JWT, OAuth等。
"""

import hashlib
import hmac
import time
import base64
import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode

from .types import SignType, SignResult

logger = logging.getLogger(__name__)


class StandardSigner:
    """
    标准签名器

    支持常见的签名算法和协议。
    """

    def __init__(self):
        """初始化"""
        self._signers = {
            SignType.MD5: self._sign_md5,
            SignType.SHA256: self._sign_sha256,
            SignType.SHA1: self._sign_sha1,
            SignType.HMAC_SHA256: self._sign_hmac_sha256,
            SignType.HMAC_MD5: self._sign_hmac_md5,
            SignType.JWT: self._sign_jwt,
            SignType.OAUTH1: self._sign_oauth1,
        }

    def sign(
        self,
        sign_type: SignType,
        params: Dict[str, Any],
        secret: str = "",
        **kwargs
    ) -> SignResult:
        """
        生成签名

        Args:
            sign_type: 签名类型
            params: 参数
            secret: 密钥
            **kwargs: 额外参数

        Returns:
            签名结果
        """
        signer = self._signers.get(sign_type)
        if not signer:
            return SignResult(
                success=False,
                signature="",
                sign_type=sign_type,
                extra_params={},
                headers={},
                error=f"不支持的签名类型: {sign_type.value}"
            )

        try:
            return signer(params, secret, **kwargs)
        except Exception as e:
            logger.error(f"[StandardSigner] 签名失败: {e}")
            return SignResult(
                success=False,
                signature="",
                sign_type=sign_type,
                extra_params={},
                headers={},
                error=str(e)
            )

    # ==================== MD5 ====================

    def _sign_md5(
        self,
        params: Dict[str, Any],
        secret: str,
        **kwargs
    ) -> SignResult:
        """MD5签名"""
        # 参数排序
        sorted_params = sorted(params.items())

        # 拼接字符串
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        if secret:
            param_str += secret

        # 计算MD5
        signature = hashlib.md5(param_str.encode()).hexdigest()

        # 大小写
        if kwargs.get("uppercase", False):
            signature = signature.upper()

        return SignResult(
            success=True,
            signature=signature,
            sign_type=SignType.MD5,
            extra_params={"sign": signature},
            headers={}
        )

    # ==================== SHA256 ====================

    def _sign_sha256(
        self,
        params: Dict[str, Any],
        secret: str,
        **kwargs
    ) -> SignResult:
        """SHA256签名"""
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        if secret:
            param_str += secret

        signature = hashlib.sha256(param_str.encode()).hexdigest()

        return SignResult(
            success=True,
            signature=signature,
            sign_type=SignType.SHA256,
            extra_params={"sign": signature},
            headers={}
        )

    # ==================== SHA1 ====================

    def _sign_sha1(
        self,
        params: Dict[str, Any],
        secret: str,
        **kwargs
    ) -> SignResult:
        """SHA1签名"""
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        if secret:
            param_str += secret

        signature = hashlib.sha1(param_str.encode()).hexdigest()

        return SignResult(
            success=True,
            signature=signature,
            sign_type=SignType.SHA1,
            extra_params={"sign": signature},
            headers={}
        )

    # ==================== HMAC-SHA256 ====================

    def _sign_hmac_sha256(
        self,
        params: Dict[str, Any],
        secret: str,
        **kwargs
    ) -> SignResult:
        """HMAC-SHA256签名"""
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)

        signature = hmac.new(
            secret.encode(),
            param_str.encode(),
            hashlib.sha256
        ).hexdigest()

        return SignResult(
            success=True,
            signature=signature,
            sign_type=SignType.HMAC_SHA256,
            extra_params={"sign": signature},
            headers={}
        )

    # ==================== HMAC-MD5 ====================

    def _sign_hmac_md5(
        self,
        params: Dict[str, Any],
        secret: str,
        **kwargs
    ) -> SignResult:
        """HMAC-MD5签名"""
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)

        signature = hmac.new(
            secret.encode(),
            param_str.encode(),
            hashlib.md5
        ).hexdigest()

        return SignResult(
            success=True,
            signature=signature,
            sign_type=SignType.HMAC_MD5,
            extra_params={"sign": signature},
            headers={}
        )

    # ==================== JWT ====================

    def _sign_jwt(
        self,
        params: Dict[str, Any],
        secret: str,
        **kwargs
    ) -> SignResult:
        """JWT签名"""
        algorithm = kwargs.get("algorithm", "HS256")
        exp_seconds = kwargs.get("exp_seconds", 3600)

        # Header
        header = {
            "alg": algorithm,
            "typ": "JWT"
        }

        # Payload
        payload = {
            **params,
            "iat": int(time.time()),
            "exp": int(time.time()) + exp_seconds
        }

        # 编码
        def b64_encode(data: dict) -> str:
            json_str = json.dumps(data, separators=(',', ':'))
            return base64.urlsafe_b64encode(json_str.encode()).rstrip(b'=').decode()

        header_b64 = b64_encode(header)
        payload_b64 = b64_encode(payload)
        message = f"{header_b64}.{payload_b64}"

        # 签名
        if algorithm == "HS256":
            sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
        elif algorithm == "HS384":
            sig = hmac.new(secret.encode(), message.encode(), hashlib.sha384).digest()
        elif algorithm == "HS512":
            sig = hmac.new(secret.encode(), message.encode(), hashlib.sha512).digest()
        else:
            return SignResult(
                success=False,
                signature="",
                sign_type=SignType.JWT,
                extra_params={},
                headers={},
                error=f"不支持的JWT算法: {algorithm}"
            )

        sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b'=').decode()
        token = f"{message}.{sig_b64}"

        return SignResult(
            success=True,
            signature=token,
            sign_type=SignType.JWT,
            extra_params={},
            headers={"Authorization": f"Bearer {token}"}
        )

    # ==================== OAuth1 ====================

    def _sign_oauth1(
        self,
        params: Dict[str, Any],
        secret: str,
        **kwargs
    ) -> SignResult:
        """OAuth1签名"""
        import uuid

        consumer_key = kwargs.get("consumer_key", "")
        consumer_secret = kwargs.get("consumer_secret", secret)
        token = kwargs.get("token", "")
        token_secret = kwargs.get("token_secret", "")
        method = kwargs.get("method", "GET").upper()
        url = kwargs.get("url", "")

        # OAuth参数
        oauth_params = {
            "oauth_consumer_key": consumer_key,
            "oauth_nonce": uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_version": "1.0",
        }
        if token:
            oauth_params["oauth_token"] = token

        # 合并参数
        all_params = {**params, **oauth_params}
        sorted_params = sorted(all_params.items())
        param_str = "&".join(f"{quote(str(k), safe='')}"
                            f"={quote(str(v), safe='')}"
                            for k, v in sorted_params)

        # 基础字符串
        base_string = "&".join([
            method,
            quote(url, safe=''),
            quote(param_str, safe='')
        ])

        # 签名密钥
        signing_key = f"{quote(consumer_secret, safe='')}&{quote(token_secret, safe='')}"

        # HMAC-SHA1签名
        sig = hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
        signature = base64.b64encode(sig).decode()

        oauth_params["oauth_signature"] = signature

        # 生成Authorization header
        auth_header = "OAuth " + ", ".join(
            f'{k}="{quote(str(v), safe="")}"'
            for k, v in sorted(oauth_params.items())
        )

        return SignResult(
            success=True,
            signature=signature,
            sign_type=SignType.OAUTH1,
            extra_params=oauth_params,
            headers={"Authorization": auth_header}
        )
