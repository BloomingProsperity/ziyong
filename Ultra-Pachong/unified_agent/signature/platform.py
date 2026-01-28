"""
签名模块 - 平台签名器

实现各大平台的签名算法：Bilibili, JD, Douyin等。
"""

import hashlib
import time
import logging
from functools import reduce
from typing import Any, Dict, List, Optional

from .types import SignType, SignResult

logger = logging.getLogger(__name__)


class PlatformSigner:
    """
    平台签名器

    支持主流平台的签名算法。
    """

    # Bilibili WBI 混淆表
    WBI_MIXIN_TABLE = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
        27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
        37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
        22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
    ]

    def __init__(self):
        """初始化"""
        self._signers = {
            SignType.BILIBILI_WBI: self._sign_bilibili_wbi,
            SignType.JD_H5ST: self._sign_jd_h5st,
            SignType.DOUYIN_XBOGUS: self._sign_douyin_xbogus,
        }

    def sign(
        self,
        sign_type: SignType,
        params: Dict[str, Any],
        **kwargs
    ) -> SignResult:
        """
        生成平台签名

        Args:
            sign_type: 签名类型
            params: 参数
            **kwargs: 平台特定参数

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
                error=f"不支持的平台签名: {sign_type.value}"
            )

        try:
            return signer(params, **kwargs)
        except Exception as e:
            logger.error(f"[PlatformSigner] 签名失败: {e}")
            return SignResult(
                success=False,
                signature="",
                sign_type=sign_type,
                extra_params={},
                headers={},
                error=str(e)
            )

    # ==================== Bilibili WBI ====================

    def _sign_bilibili_wbi(
        self,
        params: Dict[str, Any],
        **kwargs
    ) -> SignResult:
        """
        Bilibili WBI 签名

        Args:
            params: 请求参数
            img_key: img_key (从 nav API 获取)
            sub_key: sub_key (从 nav API 获取)

        Returns:
            签名结果
        """
        img_key = kwargs.get("img_key", "")
        sub_key = kwargs.get("sub_key", "")

        if not img_key or not sub_key:
            return SignResult(
                success=False,
                signature="",
                sign_type=SignType.BILIBILI_WBI,
                extra_params={},
                headers={},
                error="缺少 img_key 或 sub_key"
            )

        # 生成 mixin_key
        mixin_key = self._get_wbi_mixin_key(img_key + sub_key)

        # 添加时间戳
        params = {**params, "wts": int(time.time())}

        # 过滤特殊字符
        params = {
            k: self._filter_wbi_chars(str(v))
            for k, v in params.items()
        }

        # 排序并拼接
        sorted_params = sorted(params.items())
        query = "&".join(f"{k}={v}" for k, v in sorted_params)

        # 计算签名
        sign_str = query + mixin_key
        w_rid = hashlib.md5(sign_str.encode()).hexdigest()

        return SignResult(
            success=True,
            signature=w_rid,
            sign_type=SignType.BILIBILI_WBI,
            extra_params={"w_rid": w_rid, "wts": params["wts"]},
            headers={}
        )

    def _get_wbi_mixin_key(self, raw_key: str) -> str:
        """生成WBI混淆密钥"""
        # 确保 raw_key 足够长（至少64字符）
        if len(raw_key) < 64:
            # 填充到64字符
            raw_key = (raw_key * (64 // len(raw_key) + 1))[:64]
        
        return reduce(
            lambda acc, idx: acc + raw_key[idx],
            self.WBI_MIXIN_TABLE,
            ""
        )[:32]

    def _filter_wbi_chars(self, value: str) -> str:
        """过滤WBI特殊字符"""
        chars_to_remove = "!'()*"
        for char in chars_to_remove:
            value = value.replace(char, "")
        return value

    # ==================== 京东 H5ST ====================

    def _sign_jd_h5st(
        self,
        params: Dict[str, Any],
        **kwargs
    ) -> SignResult:
        """
        京东 H5ST 签名

        注意：这是简化版实现，完整版需要JS环境执行。

        Args:
            params: 请求参数
            fp: fingerprint
            appid: 应用ID

        Returns:
            签名结果
        """
        fp = kwargs.get("fp", "")
        appid = kwargs.get("appid", "")
        timestamp = kwargs.get("timestamp", str(int(time.time() * 1000)))

        # 基础参数
        h5st_params = {
            "appid": appid,
            "body": params.get("body", ""),
            "functionId": params.get("functionId", ""),
            "t": timestamp,
        }

        # 排序拼接
        sorted_items = sorted(h5st_params.items())
        base_str = "&".join(f"{k}:{v}" for k, v in sorted_items)

        # 简化签名（实际需要复杂的加密算法）
        sign_input = f"{base_str}&fp:{fp}"
        signature = hashlib.md5(sign_input.encode()).hexdigest()

        # 生成 h5st
        h5st = f"{timestamp};{fp};{appid};{signature}"

        return SignResult(
            success=True,
            signature=h5st,
            sign_type=SignType.JD_H5ST,
            extra_params={"h5st": h5st},
            headers={}
        )

    # ==================== 抖音 X-Bogus ====================

    def _sign_douyin_xbogus(
        self,
        params: Dict[str, Any],
        **kwargs
    ) -> SignResult:
        """
        抖音 X-Bogus 签名

        注意：这是简化版实现，完整版需要逆向JS代码。

        Args:
            params: 请求参数
            user_agent: User-Agent

        Returns:
            签名结果
        """
        user_agent = kwargs.get("user_agent", "")
        url_path = kwargs.get("url_path", "")

        # 构建查询字符串
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))

        # 简化签名逻辑（实际需要复杂的加密）
        timestamp = int(time.time())
        sign_input = f"{query}&{user_agent}&{timestamp}"
        hash_val = hashlib.md5(sign_input.encode()).hexdigest()

        # 编码为X-Bogus格式（简化）
        x_bogus = self._encode_xbogus(hash_val, timestamp)

        return SignResult(
            success=True,
            signature=x_bogus,
            sign_type=SignType.DOUYIN_XBOGUS,
            extra_params={"X-Bogus": x_bogus},
            headers={"X-Bogus": x_bogus}
        )

    def _encode_xbogus(self, hash_val: str, timestamp: int) -> str:
        """编码X-Bogus（简化实现）"""
        # 实际实现需要复杂的编码算法
        # 这里仅作示意
        import base64
        raw = f"{hash_val}|{timestamp}"
        return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")

    # ==================== 工具方法 ====================

    def sign_bilibili_wbi(
        self,
        params: Dict[str, Any],
        img_key: str,
        sub_key: str
    ) -> SignResult:
        """便捷方法：Bilibili WBI签名"""
        return self._sign_bilibili_wbi(params, img_key=img_key, sub_key=sub_key)

    def sign_jd_h5st(
        self,
        params: Dict[str, Any],
        fp: str,
        appid: str
    ) -> SignResult:
        """便捷方法：京东H5ST签名"""
        return self._sign_jd_h5st(params, fp=fp, appid=appid)

    def sign_douyin_xbogus(
        self,
        params: Dict[str, Any],
        user_agent: str
    ) -> SignResult:
        """便捷方法：抖音X-Bogus签名"""
        return self._sign_douyin_xbogus(params, user_agent=user_agent)
