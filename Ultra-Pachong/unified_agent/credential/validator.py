"""
凭据池模块 - 凭据验证器

验证凭据的有效性。
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from .types import Credential, CredentialType, CredentialStatus

logger = logging.getLogger(__name__)


class CredentialValidator:
    """
    凭据验证器

    支持自定义验证逻辑。

    使用示例:
        validator = CredentialValidator()

        # 注册验证器
        validator.register(CredentialType.COOKIE, my_cookie_validator)

        # 验证凭据
        is_valid = validator.validate(credential)
    """

    def __init__(self):
        """初始化"""
        self._validators: Dict[CredentialType, Callable] = {}
        self._register_default_validators()

    def _register_default_validators(self):
        """注册默认验证器"""
        self._validators[CredentialType.TOKEN] = self._validate_token
        self._validators[CredentialType.API_KEY] = self._validate_api_key

    def register(
        self,
        cred_type: CredentialType,
        validator: Callable[[Credential], bool]
    ):
        """
        注册验证器

        Args:
            cred_type: 凭据类型
            validator: 验证函数，接受Credential返回bool
        """
        self._validators[cred_type] = validator
        logger.info(f"[CredentialValidator] 注册验证器: {cred_type.value}")

    def validate(self, credential: Credential) -> bool:
        """
        验证凭据

        Args:
            credential: 凭据对象

        Returns:
            是否有效
        """
        # 检查基本属性
        if not self._validate_basic(credential):
            return False

        # 调用类型特定验证器
        validator = self._validators.get(credential.cred_type)
        if validator:
            try:
                return validator(credential)
            except Exception as e:
                logger.error(f"[CredentialValidator] 验证异常: {e}")
                return False

        # 无特定验证器，默认有效
        return True

    def _validate_basic(self, credential: Credential) -> bool:
        """基本验证"""
        # 检查状态
        if credential.status in (CredentialStatus.EXPIRED, CredentialStatus.INVALID):
            logger.debug(f"[CredentialValidator] 凭据状态无效: {credential.cred_id}")
            return False

        # 检查过期时间
        if credential.expires_at and datetime.now() > credential.expires_at:
            logger.debug(f"[CredentialValidator] 凭据已过期: {credential.cred_id}")
            return False

        # 检查值是否存在
        if not credential.value:
            logger.debug(f"[CredentialValidator] 凭据值为空: {credential.cred_id}")
            return False

        return True

    def _validate_token(self, credential: Credential) -> bool:
        """验证Token"""
        value = credential.value

        # 检查token字段
        token = value.get("token") or value.get("access_token")
        if not token:
            return False

        # 检查长度
        if len(token) < 10:
            return False

        return True

    def _validate_api_key(self, credential: Credential) -> bool:
        """验证API Key"""
        value = credential.value

        # 检查key字段
        key = value.get("api_key") or value.get("key")
        if not key:
            return False

        # 检查格式（简单验证）
        if len(key) < 8:
            return False

        return True

    def batch_validate(self, credentials: list) -> Dict[str, bool]:
        """
        批量验证

        Args:
            credentials: 凭据列表

        Returns:
            验证结果字典 {cred_id: is_valid}
        """
        results = {}
        for cred in credentials:
            results[cred.cred_id] = self.validate(cred)
        return results
