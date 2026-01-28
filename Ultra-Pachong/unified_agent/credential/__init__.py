"""
凭据池模块 (Credential Pool Module)

模块职责:
- 凭据存储与管理
- 凭据验证与刷新
- 凭据轮换策略
- 安全存储

使用示例:
    from unified_agent.credential import CredentialPool, Credential

    pool = CredentialPool()
    pool.add(Credential(
        cred_id="user1",
        cred_type=CredentialType.COOKIE,
        value={"session": "xxx"}
    ))

    cred = pool.get_available()
"""

from .types import CredentialType, CredentialStatus, Credential
from .pool import CredentialPool
from .validator import CredentialValidator
from .storage import CredentialStorage

__all__ = [
    # Types
    "CredentialType",
    "CredentialStatus",
    "Credential",
    # Classes
    "CredentialPool",
    "CredentialValidator",
    "CredentialStorage",
]
