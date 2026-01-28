"""
凭据池模块 - 类型定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class CredentialType(str, Enum):
    """凭据类型"""
    COOKIE = "cookie"           # Cookie
    TOKEN = "token"             # Token (Bearer等)
    SESSION = "session"         # Session ID
    API_KEY = "api_key"         # API Key
    USERNAME_PASSWORD = "username_password"  # 用户名密码
    OAUTH = "oauth"             # OAuth凭据


class CredentialStatus(str, Enum):
    """凭据状态"""
    ACTIVE = "active"           # 活跃可用
    COOLING = "cooling"         # 冷却中
    EXPIRED = "expired"         # 已过期
    BLOCKED = "blocked"         # 被封禁
    INVALID = "invalid"         # 无效


@dataclass
class Credential:
    """凭据"""
    cred_id: str                # 唯一标识
    cred_type: CredentialType   # 凭据类型
    value: Dict[str, Any]       # 凭据值

    # 状态
    status: CredentialStatus = CredentialStatus.ACTIVE
    
    # 元数据
    domain: str = ""            # 适用域名
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # 统计
    use_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    cooldown_until: Optional[datetime] = None

    # 权重
    weight: float = 1.0         # 选择权重

    def to_dict(self) -> dict:
        return {
            "cred_id": self.cred_id,
            "cred_type": self.cred_type.value,
            "status": self.status.value,
            "domain": self.domain,
            "use_count": self.use_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "success_rate": self.success_rate,
            "weight": self.weight,
        }

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.use_count == 0:
            return 1.0
        return self.success_count / self.use_count

    @property
    def is_available(self) -> bool:
        """是否可用"""
        if self.status not in (CredentialStatus.ACTIVE, CredentialStatus.COOLING):
            return False

        # 检查冷却
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            return False

        # 检查过期
        if self.expires_at and datetime.now() > self.expires_at:
            return False

        return True

    def mark_used(self, success: bool = True):
        """标记使用"""
        self.use_count += 1
        self.last_used_at = datetime.now()

        if success:
            self.success_count += 1
        else:
            self.fail_count += 1

    def set_cooldown(self, seconds: int):
        """设置冷却"""
        from datetime import timedelta
        self.cooldown_until = datetime.now() + timedelta(seconds=seconds)
        self.status = CredentialStatus.COOLING

    def clear_cooldown(self):
        """清除冷却"""
        self.cooldown_until = None
        if self.status == CredentialStatus.COOLING:
            self.status = CredentialStatus.ACTIVE
