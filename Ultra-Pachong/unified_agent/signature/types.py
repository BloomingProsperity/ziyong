"""
签名模块 - 类型定义
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class SignType(str, Enum):
    """签名类型"""
    # 标准算法
    MD5 = "md5"
    SHA256 = "sha256"
    SHA1 = "sha1"
    HMAC_SHA256 = "hmac_sha256"
    HMAC_MD5 = "hmac_md5"

    # 标准协议
    JWT = "jwt"
    OAUTH1 = "oauth1"
    OAUTH2 = "oauth2"
    AWS_V4 = "aws_v4"

    # 平台签名
    BILIBILI_WBI = "bilibili_wbi"
    JD_H5ST = "jd_h5st"
    DOUYIN_XBOGUS = "douyin_xbogus"
    TAOBAO_H5 = "taobao_h5"
    XIAOHONGSHU_XS = "xiaohongshu_xs"

    # 自定义
    CUSTOM = "custom"


@dataclass
class SignResult:
    """签名结果"""
    success: bool
    signature: str
    sign_type: SignType
    extra_params: Dict[str, Any]  # 额外需要添加的参数
    headers: Dict[str, str]       # 需要添加的请求头
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "signature": self.signature,
            "sign_type": self.sign_type.value,
            "extra_params": self.extra_params,
            "headers": self.headers,
            "error": self.error,
        }
