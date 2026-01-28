"""
签名模块 - 签名生成器

统一签名入口，支持标准算法和平台签名。
"""

import logging
from typing import Any, Callable, Dict, Optional

from .types import SignType, SignResult
from .standard import StandardSigner
from .platform import PlatformSigner

logger = logging.getLogger(__name__)


class SignatureGenerator:
    """
    签名生成器

    统一的签名入口，自动路由到合适的签名器。

    使用示例:
        generator = SignatureGenerator()

        # 标准签名
        result = generator.generate(SignType.MD5, params, secret)

        # 平台签名
        result = generator.generate(
            SignType.BILIBILI_WBI,
            params,
            img_key="xxx",
            sub_key="yyy"
        )

        # 自定义签名
        generator.register_custom("my_sign", my_sign_func)
        result = generator.generate("my_sign", params)
    """

    # 标准签名类型
    STANDARD_TYPES = {
        SignType.MD5,
        SignType.SHA256,
        SignType.SHA1,
        SignType.HMAC_SHA256,
        SignType.HMAC_MD5,
        SignType.JWT,
        SignType.OAUTH1,
        SignType.OAUTH2,
        SignType.AWS_V4,
    }

    # 平台签名类型
    PLATFORM_TYPES = {
        SignType.BILIBILI_WBI,
        SignType.JD_H5ST,
        SignType.DOUYIN_XBOGUS,
        SignType.TAOBAO_H5,
        SignType.XIAOHONGSHU_XS,
    }

    def __init__(self):
        """初始化"""
        self.standard_signer = StandardSigner()
        self.platform_signer = PlatformSigner()
        self.custom_signers: Dict[str, Callable] = {}

        logger.info("[SignatureGenerator] 初始化完成")

    def generate(
        self,
        sign_type: SignType | str,
        params: Dict[str, Any],
        secret: str = "",
        **kwargs
    ) -> SignResult:
        """
        生成签名

        Args:
            sign_type: 签名类型
            params: 参数
            secret: 密钥（标准签名需要）
            **kwargs: 额外参数

        Returns:
            签名结果
        """
        # 转换为 SignType
        if isinstance(sign_type, str):
            try:
                sign_type = SignType(sign_type)
            except ValueError:
                # 尝试自定义签名
                if sign_type in self.custom_signers:
                    return self._call_custom_signer(sign_type, params, secret, **kwargs)
                return SignResult(
                    success=False,
                    signature="",
                    sign_type=SignType.CUSTOM,
                    extra_params={},
                    headers={},
                    error=f"未知签名类型: {sign_type}"
                )

        # 路由到合适的签名器
        if sign_type in self.STANDARD_TYPES:
            return self.standard_signer.sign(sign_type, params, secret, **kwargs)

        elif sign_type in self.PLATFORM_TYPES:
            return self.platform_signer.sign(sign_type, params, **kwargs)

        elif sign_type == SignType.CUSTOM:
            custom_name = kwargs.get("custom_name", "")
            if custom_name in self.custom_signers:
                return self._call_custom_signer(custom_name, params, secret, **kwargs)
            return SignResult(
                success=False,
                signature="",
                sign_type=SignType.CUSTOM,
                extra_params={},
                headers={},
                error="未指定自定义签名器"
            )

        else:
            return SignResult(
                success=False,
                signature="",
                sign_type=sign_type,
                extra_params={},
                headers={},
                error=f"不支持的签名类型: {sign_type.value}"
            )

    def _call_custom_signer(
        self,
        name: str,
        params: Dict[str, Any],
        secret: str,
        **kwargs
    ) -> SignResult:
        """调用自定义签名器"""
        signer = self.custom_signers.get(name)
        if not signer:
            return SignResult(
                success=False,
                signature="",
                sign_type=SignType.CUSTOM,
                extra_params={},
                headers={},
                error=f"未找到自定义签名器: {name}"
            )

        try:
            result = signer(params, secret, **kwargs)

            # 如果返回的是字符串，包装为 SignResult
            if isinstance(result, str):
                return SignResult(
                    success=True,
                    signature=result,
                    sign_type=SignType.CUSTOM,
                    extra_params={"sign": result},
                    headers={}
                )

            # 如果返回的是 SignResult
            if isinstance(result, SignResult):
                return result

            # 其他情况
            return SignResult(
                success=True,
                signature=str(result),
                sign_type=SignType.CUSTOM,
                extra_params={},
                headers={}
            )

        except Exception as e:
            logger.error(f"[SignatureGenerator] 自定义签名失败: {e}")
            return SignResult(
                success=False,
                signature="",
                sign_type=SignType.CUSTOM,
                extra_params={},
                headers={},
                error=str(e)
            )

    # ==================== 自定义签名 ====================

    def register_custom(self, name: str, signer: Callable):
        """
        注册自定义签名器

        Args:
            name: 签名器名称
            signer: 签名函数，签名为 (params, secret, **kwargs) -> str | SignResult
        """
        self.custom_signers[name] = signer
        logger.info(f"[SignatureGenerator] 注册自定义签名器: {name}")

    def unregister_custom(self, name: str):
        """移除自定义签名器"""
        if name in self.custom_signers:
            del self.custom_signers[name]
            logger.info(f"[SignatureGenerator] 移除自定义签名器: {name}")

    # ==================== 便捷方法 ====================

    def md5(self, params: Dict[str, Any], secret: str = "") -> SignResult:
        """MD5签名"""
        return self.generate(SignType.MD5, params, secret)

    def sha256(self, params: Dict[str, Any], secret: str = "") -> SignResult:
        """SHA256签名"""
        return self.generate(SignType.SHA256, params, secret)

    def hmac_sha256(self, params: Dict[str, Any], secret: str) -> SignResult:
        """HMAC-SHA256签名"""
        return self.generate(SignType.HMAC_SHA256, params, secret)

    def jwt(
        self,
        payload: Dict[str, Any],
        secret: str,
        algorithm: str = "HS256",
        exp_seconds: int = 3600
    ) -> SignResult:
        """JWT签名"""
        return self.generate(
            SignType.JWT,
            payload,
            secret,
            algorithm=algorithm,
            exp_seconds=exp_seconds
        )

    def bilibili_wbi(
        self,
        params: Dict[str, Any],
        img_key: str,
        sub_key: str
    ) -> SignResult:
        """Bilibili WBI签名"""
        return self.generate(
            SignType.BILIBILI_WBI,
            params,
            img_key=img_key,
            sub_key=sub_key
        )

    # ==================== 工具方法 ====================

    def get_supported_types(self) -> list:
        """获取支持的签名类型"""
        types = list(self.STANDARD_TYPES) + list(self.PLATFORM_TYPES)
        if self.custom_signers:
            types.append(SignType.CUSTOM)
        return [t.value for t in types]

    def get_custom_signers(self) -> list:
        """获取已注册的自定义签名器"""
        return list(self.custom_signers.keys())
