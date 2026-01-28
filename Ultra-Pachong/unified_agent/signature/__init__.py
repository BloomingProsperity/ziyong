"""
签名模块 (Signature Module)

模块职责:
- 标准签名算法 (MD5, SHA, HMAC, JWT, OAuth)
- 平台签名生成 (JD, Douyin, Bilibili等)
- 签名工具函数

使用示例:
    from unified_agent.signature import SignatureGenerator, PlatformSigner

    # 标准签名
    generator = SignatureGenerator()
    sign = generator.generate("md5", params, secret)

    # 平台签名
    signer = PlatformSigner()
    sign = signer.sign_bilibili_wbi(params, img_key, sub_key)
"""

from .types import SignType, SignResult
from .standard import StandardSigner
from .platform import PlatformSigner
from .generator import SignatureGenerator

__all__ = [
    # Types
    "SignType",
    "SignResult",
    # Classes
    "StandardSigner",
    "PlatformSigner",
    "SignatureGenerator",
]
