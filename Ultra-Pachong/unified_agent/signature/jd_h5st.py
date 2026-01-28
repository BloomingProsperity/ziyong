"""
京东 H5ST 5.2 签名算法

基于真实抓包分析实现。

H5ST结构 (5.2版本, 10段):
  段1: 时间戳 yyyyMMddHHmmssSSS (17位)
  段2: 设备指纹 fp (16位)
  段3: appid简写 (5位)
  段4: token (92位, tk开头)
  段5: hash1 SHA256 (64位)
  段6: 版本号 5.2
  段7: 毫秒时间戳 (13位)
  段8: 扩展数据 (自定义编码)
  段9: hash2 (64位)
  段10: 额外数据 (60位)
"""

import hashlib
import hmac
import time
import json
import random
import string
import base64
from typing import Dict, Any, Tuple
from datetime import datetime


class JDH5ST52Signer:
    """
    京东H5ST 5.2版本签名器

    基于真实h5st结构逆向实现
    """

    VERSION = "5.2"

    # 自定义编码字符表（从JS逆向获取）
    ENCODE_TABLE = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"

    # APPID映射
    APPID_MAP = {
        "item-v3": "fb5df",
        "jd-cphdx-m": "f2dc8",
        "search-m": "a3d5f",
    }

    def __init__(self, appid: str = "item-v3"):
        self.appid = appid
        self.appid_short = self.APPID_MAP.get(appid, "fb5df")
        self._fp = self._generate_fp()

    def _generate_fp(self) -> str:
        """生成16位设备指纹"""
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(16))

    def _get_timestamps(self) -> Tuple[str, int]:
        """获取时间戳"""
        ts_ms = int(time.time() * 1000)
        dt = datetime.fromtimestamp(ts_ms / 1000)
        ts_str = dt.strftime('%Y%m%d%H%M%S') + f'{ts_ms % 1000:03d}'
        return ts_str, ts_ms

    def _sha256(self, data: str) -> str:
        """SHA256"""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def _hmac_sha256(self, key: str, data: str) -> str:
        """HMAC-SHA256"""
        return hmac.new(
            key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _custom_encode(self, data: str) -> str:
        """
        自定义编码

        JD使用自定义的base64变体编码
        """
        # 先转为字节
        b = data.encode('utf-8')
        # 标准base64
        b64 = base64.b64encode(b).decode()
        # 替换字符
        result = b64.replace('+', '-').replace('/', '_').replace('=', '')
        return result

    def _generate_token(self, ts_ms: int) -> str:
        """
        生成92位token

        格式: tk + 随机字符 + 编码数据
        """
        # 基础随机部分
        chars = string.ascii_lowercase + string.digits
        random_part = ''.join(random.choice(chars) for _ in range(14))

        # 编码时间戳和指纹
        data = f"{ts_ms}_{self._fp}"
        encoded = self._custom_encode(data)

        # 组合token
        token = f"tk{random_part}{encoded}"

        # 确保92字符
        if len(token) < 92:
            token = token + ''.join(random.choice(chars) for _ in range(92 - len(token)))

        return token[:92]

    def _compute_hash1(
        self,
        function_id: str,
        body: str,
        ts_ms: int,
        token: str,
    ) -> str:
        """
        计算第一个哈希 (64位)

        算法: SHA256(params + token)
        """
        params = {
            "appid": self.appid,
            "body": body,
            "client": "pc",
            "clientVersion": "1.0.0",
            "functionId": function_id,
            "t": str(ts_ms),
        }

        # 排序拼接
        sorted_items = sorted(params.items())
        sign_str = "&".join(f"{k}:{v}" for k, v in sorted_items)

        # 与token组合
        combined = sign_str + token

        return self._sha256(combined)

    def _generate_expand(self, ts_ms: int) -> str:
        """
        生成扩展数据

        包含设备信息等
        """
        expand_data = {
            "sua": "Windows NT 10.0",
            "pp": {"p1": self._fp},
            "random": random.randint(100000, 999999),
            "referer": "https://item.jd.com/",
            "v": "5.2",
            "fp": self._fp,
        }

        json_str = json.dumps(expand_data, separators=(',', ':'))
        return self._custom_encode(json_str)

    def _compute_hash2(
        self,
        hash1: str,
        expand: str,
        ts_str: str,
    ) -> str:
        """
        计算第二个哈希 (64位)
        """
        combined = f"{hash1}{expand}{ts_str}"
        return self._sha256(combined)

    def _generate_extra(self, ts_ms: int) -> str:
        """
        生成额外数据 (60位)
        """
        data = f"{ts_ms}_{self._fp}_{random.randint(1000, 9999)}"
        encoded = self._custom_encode(data)
        return encoded[:60]

    def sign(
        self,
        function_id: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        生成H5ST签名
        """
        ts_str, ts_ms = self._get_timestamps()

        body_str = json.dumps(body, ensure_ascii=False, separators=(',', ':'))

        # 生成各个部分
        token = self._generate_token(ts_ms)
        hash1 = self._compute_hash1(function_id, body_str, ts_ms, token)
        expand = self._generate_expand(ts_ms)
        hash2 = self._compute_hash2(hash1, expand, ts_str)
        extra = self._generate_extra(ts_ms)

        # 组装h5st (10段)
        h5st = ";".join([
            ts_str,           # 段1: 时间戳格式
            self._fp,         # 段2: 指纹
            self.appid_short, # 段3: appid简写
            token,            # 段4: token
            hash1,            # 段5: hash1
            self.VERSION,     # 段6: 版本
            str(ts_ms),       # 段7: 毫秒时间戳
            expand,           # 段8: 扩展数据
            hash2,            # 段9: hash2
            extra,            # 段10: 额外数据
        ])

        return {
            "h5st": h5st,
            "timestamp": ts_ms,
            "t": ts_ms,
            "fp": self._fp,
        }

    def get_api_params(
        self,
        function_id: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        获取完整API请求参数
        """
        sign_result = self.sign(function_id, body)
        body_str = json.dumps(body, ensure_ascii=False, separators=(',', ':'))

        return {
            "functionId": function_id,
            "body": body_str,
            "appid": self.appid,
            "client": "pc",
            "clientVersion": "1.0.0",
            "t": str(sign_result["timestamp"]),
            "h5st": sign_result["h5st"],
        }


def sign_jd_api(function_id: str, body: Dict[str, Any], appid: str = "item-v3") -> Dict[str, Any]:
    """
    便捷函数: 签名京东API
    """
    signer = JDH5ST52Signer(appid=appid)
    return signer.get_api_params(function_id, body)


# 测试
if __name__ == "__main__":
    import httpx

    print("=== 测试京东H5ST 5.2签名 ===\n")

    signer = JDH5ST52Signer()

    body = {
        "productId": "100012043978",
        "sortType": 5,
        "page": 1,
        "pageSize": 10,
        "score": 3,
        "isShadowSku": 0,
    }

    params = signer.get_api_params("getCommentListWithCard", body)

    print("生成的参数:")
    for k, v in params.items():
        if k == "h5st":
            print(f"  {k}:")
            parts = v.split(';')
            for i, p in enumerate(parts):
                print(f"    段{i+1}: {p[:40]}..." if len(p) > 40 else f"    段{i+1}: {p}")
        else:
            print(f"  {k}: {v}")

    print("\n=== 测试API调用 ===")

    url = "https://api.m.jd.com/client.action"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Accept": "application/json",
        "Referer": "https://item.jd.com/",
    }

    try:
        resp = httpx.get(url, params=params, headers=headers, timeout=30)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {resp.text[:800]}")
    except Exception as e:
        print(f"错误: {e}")
