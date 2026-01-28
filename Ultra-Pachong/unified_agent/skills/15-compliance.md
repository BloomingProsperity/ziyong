# 15 - 数据安全模块 (Data Security)

---
name: data-security
version: 1.2.0
description: PII脱敏与密钥管理
triggers:
  - "PII"
  - "脱敏"
  - "密钥"
  - "凭证"
  - "敏感信息"
difficulty: ⭐⭐
---

## 模块目标

**核心原则：给出需求，必须完成。**

| 目标 | 达成标准 |
|------|---------|
| **PII 自动脱敏** | 爬取数据中的敏感信息 100% 检测并脱敏 |
| **密钥零泄露** | API Key、Token、密码永远不出现在日志/输出中 |
| **凭证自动续期** | 有时效凭证在过期前自动刷新，爬虫不中断 |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据安全能力                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                       PII 检测与脱敏                               │    │
│   │  手机号 | 邮箱 | 身份证 | 银行卡 | IP地址 | 自定义模式            │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                       密钥与凭证管理                               │    │
│   │  加密存储 | 自动轮换 | 过期检测 | 刷新回调                        │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## PII 检测与脱敏

```python
"""
PII (个人身份信息) 检测与脱敏
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import re
from datetime import datetime


class PIIType(Enum):
    """PII 类型"""
    EMAIL = "email"
    PHONE = "phone"
    ID_NUMBER = "id_number"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    BANK_CARD = "bank_card"


@dataclass
class PIIPattern:
    """PII 匹配模式"""
    pii_type: PIIType
    pattern: str
    description: str


# 预定义模式
PII_PATTERNS = [
    PIIPattern(PIIType.EMAIL, r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', "邮箱"),
    PIIPattern(PIIType.PHONE, r'1[3-9]\d{9}', "中国手机号"),
    PIIPattern(PIIType.ID_NUMBER, r'\d{17}[\dXx]', "身份证号"),
    PIIPattern(PIIType.CREDIT_CARD, r'\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}', "信用卡号"),
    PIIPattern(PIIType.IP_ADDRESS, r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', "IPv4地址"),
    PIIPattern(PIIType.BANK_CARD, r'\d{16,19}', "银行卡号"),
]


@dataclass
class PIIMatch:
    """PII 匹配结果"""
    pii_type: PIIType
    original: str
    masked: str
    position: tuple


class PIIDetector:
    """PII 检测器"""

    def __init__(self, patterns: List[PIIPattern] = None):
        self.patterns = patterns or PII_PATTERNS
        self._compiled = {p.pii_type: re.compile(p.pattern) for p in self.patterns}

    def detect(self, text: str) -> List[PIIMatch]:
        """检测文本中的 PII"""
        results = []
        for pii_type, regex in self._compiled.items():
            for match in regex.finditer(text):
                value = match.group()
                results.append(PIIMatch(
                    pii_type=pii_type,
                    original=value,
                    masked=self._mask(value, pii_type),
                    position=(match.start(), match.end())
                ))
        return results

    def mask_all(self, text: str) -> str:
        """脱敏所有 PII"""
        matches = self.detect(text)
        # 倒序替换，避免位置偏移
        for m in sorted(matches, key=lambda x: x.position[0], reverse=True):
            text = text[:m.position[0]] + m.masked + text[m.position[1]:]
        return text

    def _mask(self, value: str, pii_type: PIIType) -> str:
        """脱敏规则"""
        if pii_type == PIIType.EMAIL:
            parts = value.split('@')
            return f"{parts[0][0]}***@{parts[1][0]}***.{parts[1].split('.')[-1]}"
        elif pii_type == PIIType.PHONE:
            return f"{value[:3]}****{value[-4:]}"
        elif pii_type == PIIType.ID_NUMBER:
            return f"{value[:6]}********{value[-4:]}"
        elif pii_type in (PIIType.CREDIT_CARD, PIIType.BANK_CARD):
            return f"{value[:4]}********{value[-4:]}"
        elif pii_type == PIIType.IP_ADDRESS:
            parts = value.split('.')
            return f"{parts[0]}.{parts[1]}.*.*"
        return '*' * len(value)


# 使用示例
detector = PIIDetector()
text = "联系方式: 13812345678, email: test@example.com"
print(detector.mask_all(text))
# 输出: 联系方式: 138****5678, email: t***@e***.com
```

---

## 密钥管理

```python
"""
密钥加密存储
"""

import os
import base64
import json
from typing import Optional, Dict
from pathlib import Path
from cryptography.fernet import Fernet


class SecretManager:
    """密钥管理器 - 加密存储敏感信息"""

    def __init__(self, master_key: str = None):
        key = master_key or os.environ.get("MASTER_KEY")
        if not key:
            raise ValueError("Master key required")

        # 转换为 Fernet 兼容格式
        if len(key) != 44:
            key = base64.urlsafe_b64encode(key.ljust(32)[:32].encode()).decode()

        self.cipher = Fernet(key.encode())
        self._store: Dict[str, str] = {}

    def set(self, name: str, value: str):
        """加密存储"""
        self._store[name] = self.cipher.encrypt(value.encode()).decode()

    def get(self, name: str) -> Optional[str]:
        """解密读取"""
        if name not in self._store:
            return None
        return self.cipher.decrypt(self._store[name].encode()).decode()

    def save(self, path: Path):
        """持久化到文件"""
        with open(path, 'w') as f:
            json.dump(self._store, f)

    def load(self, path: Path):
        """从文件加载"""
        if path.exists():
            with open(path, 'r') as f:
                self._store = json.load(f)

    @staticmethod
    def generate_key() -> str:
        """生成新密钥"""
        return Fernet.generate_key().decode()
```

---

## 凭证轮换

```python
"""
凭证自动轮换
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable
import threading


@dataclass
class Credential:
    """凭证"""
    name: str
    value: str
    created_at: datetime
    expires_at: Optional[datetime]
    refresh_func: Optional[Callable[[], str]] = None

    @property
    def needs_refresh(self) -> bool:
        if not self.expires_at:
            return False
        # 提前 10% 时间刷新
        lifetime = (self.expires_at - self.created_at).total_seconds()
        threshold = self.expires_at - timedelta(seconds=lifetime * 0.1)
        return datetime.now() > threshold


class CredentialRotator:
    """凭证轮换器"""

    def __init__(self):
        self.credentials: Dict[str, Credential] = {}
        self._lock = threading.Lock()

    def register(self, name: str, value: str,
                 expires_in: timedelta = None,
                 refresh_func: Callable[[], str] = None):
        """注册凭证"""
        with self._lock:
            self.credentials[name] = Credential(
                name=name,
                value=value,
                created_at=datetime.now(),
                expires_at=datetime.now() + expires_in if expires_in else None,
                refresh_func=refresh_func
            )

    def get(self, name: str) -> Optional[str]:
        """获取凭证（自动刷新）"""
        with self._lock:
            cred = self.credentials.get(name)
            if not cred:
                return None

            if cred.needs_refresh and cred.refresh_func:
                try:
                    cred.value = cred.refresh_func()
                    cred.created_at = datetime.now()
                    if cred.expires_at:
                        lifetime = (cred.expires_at - cred.created_at)
                        cred.expires_at = datetime.now() + lifetime
                except Exception as e:
                    print(f"[CRED] 刷新失败 {name}: {e}")

            return cred.value


# 使用示例
rotator = CredentialRotator()

# 注册 OAuth Token
rotator.register(
    name="access_token",
    value="initial_token",
    expires_in=timedelta(hours=1),
    refresh_func=lambda: "new_token_from_api"
)

token = rotator.get("access_token")
```

---

## 数据保留策略

```python
class DataRetention:
    """数据保留策略"""

    POLICIES = {
        "raw_html": 7,      # 原始HTML保留7天
        "parsed_data": 30,  # 解析数据保留30天
        "logs": 90,         # 日志保留90天
    }

    @classmethod
    def should_delete(cls, data_type: str, created_at: datetime) -> bool:
        days = cls.POLICIES.get(data_type, 30)
        return (datetime.now() - created_at).days > days
```

---

## 诊断日志

```
[PII] 检测到 3 处敏感信息: phone=1, email=1, id=1
[PII] 脱敏完成: 138****5678

[SECRET] 密钥已加密存储: api_key
[SECRET] 密钥读取成功: api_key

[CRED] access_token 即将过期 (剩余 5 分钟)
[CRED] 刷新成功: access_token
[CRED] 刷新失败: access_token - ConnectionError
```

---

## 相关模块

- **配合**: [06-存储模块](06-storage.md) - 数据持久化
- **配合**: [16-战术模块](16-tactics.md) - 风险评估
