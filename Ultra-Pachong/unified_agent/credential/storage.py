"""
凭据池模块 - 凭据存储

持久化存储凭据。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .types import Credential, CredentialType, CredentialStatus

logger = logging.getLogger(__name__)


class CredentialStorage:
    """
    凭据存储

    支持文件存储（JSON格式）。
    敏感信息加密存储（需配置密钥）。

    使用示例:
        storage = CredentialStorage("./credentials")

        # 保存凭据
        storage.save(credential)

        # 加载凭据
        cred = storage.load("user1")

        # 加载所有
        all_creds = storage.load_all()
    """

    def __init__(
        self,
        storage_path: str = "./credentials",
        encrypt: bool = False
    ):
        """
        初始化存储

        Args:
            storage_path: 存储目录路径
            encrypt: 是否加密存储（需额外配置）
        """
        self.storage_path = Path(storage_path)
        self.encrypt = encrypt

        # 确保目录存在
        self.storage_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"[CredentialStorage] 初始化: {self.storage_path}")

    # ==================== 基本操作 ====================

    def save(self, credential: Credential) -> bool:
        """
        保存凭据

        Args:
            credential: 凭据对象

        Returns:
            是否保存成功
        """
        try:
            file_path = self._get_file_path(credential.cred_id)
            data = self._serialize(credential)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"[CredentialStorage] 保存凭据: {credential.cred_id}")
            return True

        except Exception as e:
            logger.error(f"[CredentialStorage] 保存失败: {e}")
            return False

    def load(self, cred_id: str) -> Optional[Credential]:
        """
        加载凭据

        Args:
            cred_id: 凭据ID

        Returns:
            凭据对象，不存在返回None
        """
        try:
            file_path = self._get_file_path(cred_id)

            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return self._deserialize(data)

        except Exception as e:
            logger.error(f"[CredentialStorage] 加载失败: {e}")
            return None

    def delete(self, cred_id: str) -> bool:
        """
        删除凭据

        Args:
            cred_id: 凭据ID

        Returns:
            是否删除成功
        """
        try:
            file_path = self._get_file_path(cred_id)

            if file_path.exists():
                file_path.unlink()
                logger.info(f"[CredentialStorage] 删除凭据: {cred_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"[CredentialStorage] 删除失败: {e}")
            return False

    def load_all(self) -> List[Credential]:
        """
        加载所有凭据

        Returns:
            凭据列表
        """
        credentials = []

        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cred = self._deserialize(data)
                if cred:
                    credentials.append(cred)
            except Exception as e:
                logger.error(f"[CredentialStorage] 加载文件失败 {file_path}: {e}")

        logger.info(f"[CredentialStorage] 加载 {len(credentials)} 个凭据")
        return credentials

    def save_all(self, credentials: List[Credential]) -> int:
        """
        批量保存凭据

        Args:
            credentials: 凭据列表

        Returns:
            成功保存数量
        """
        saved = 0
        for cred in credentials:
            if self.save(cred):
                saved += 1
        return saved

    # ==================== 序列化 ====================

    def _serialize(self, credential: Credential) -> dict:
        """序列化凭据"""
        data = {
            "cred_id": credential.cred_id,
            "cred_type": credential.cred_type.value,
            "value": credential.value,
            "status": credential.status.value,
            "domain": credential.domain,
            "created_at": credential.created_at.isoformat(),
            "last_used_at": credential.last_used_at.isoformat() if credential.last_used_at else None,
            "expires_at": credential.expires_at.isoformat() if credential.expires_at else None,
            "use_count": credential.use_count,
            "success_count": credential.success_count,
            "fail_count": credential.fail_count,
            "weight": credential.weight,
        }

        # 加密敏感字段
        if self.encrypt:
            data["value"] = self._encrypt_value(credential.value)

        return data

    def _deserialize(self, data: dict) -> Optional[Credential]:
        """反序列化凭据"""
        try:
            value = data["value"]

            # 解密敏感字段
            if self.encrypt:
                value = self._decrypt_value(value)

            cred = Credential(
                cred_id=data["cred_id"],
                cred_type=CredentialType(data["cred_type"]),
                value=value,
                status=CredentialStatus(data.get("status", "active")),
                domain=data.get("domain", ""),
                use_count=data.get("use_count", 0),
                success_count=data.get("success_count", 0),
                fail_count=data.get("fail_count", 0),
                weight=data.get("weight", 1.0),
            )

            # 解析时间字段
            if data.get("created_at"):
                cred.created_at = datetime.fromisoformat(data["created_at"])
            if data.get("last_used_at"):
                cred.last_used_at = datetime.fromisoformat(data["last_used_at"])
            if data.get("expires_at"):
                cred.expires_at = datetime.fromisoformat(data["expires_at"])

            return cred

        except Exception as e:
            logger.error(f"[CredentialStorage] 反序列化失败: {e}")
            return None

    def _get_file_path(self, cred_id: str) -> Path:
        """获取凭据文件路径"""
        # 清理文件名中的特殊字符
        safe_id = "".join(c if c.isalnum() or c in "_-" else "_" for c in cred_id)
        return self.storage_path / f"{safe_id}.json"

    # ==================== 加密（简化实现）====================

    def _encrypt_value(self, value: dict) -> str:
        """加密值（简化实现，实际应使用加密库）"""
        import base64
        json_str = json.dumps(value)
        return base64.b64encode(json_str.encode()).decode()

    def _decrypt_value(self, encrypted: str) -> dict:
        """解密值"""
        import base64
        json_str = base64.b64decode(encrypted.encode()).decode()
        return json.loads(json_str)

    # ==================== 工具方法 ====================

    def list_ids(self) -> List[str]:
        """列出所有凭据ID"""
        ids = []
        for file_path in self.storage_path.glob("*.json"):
            ids.append(file_path.stem)
        return ids

    def exists(self, cred_id: str) -> bool:
        """检查凭据是否存在"""
        return self._get_file_path(cred_id).exists()

    def clear_all(self) -> int:
        """清空所有凭据"""
        count = 0
        for file_path in self.storage_path.glob("*.json"):
            try:
                file_path.unlink()
                count += 1
            except Exception:
                pass
        logger.info(f"[CredentialStorage] 清空 {count} 个凭据")
        return count
