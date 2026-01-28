"""
凭据池模块 - 凭据池管理

管理凭据的生命周期、轮换和选择。
"""

import random
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable

from .types import Credential, CredentialType, CredentialStatus

logger = logging.getLogger(__name__)


class CredentialPool:
    """
    凭据池管理器

    功能:
    - 凭据存储和管理
    - 智能选择（基于权重和成功率）
    - 自动轮换和冷却
    - 状态追踪

    使用示例:
        pool = CredentialPool()

        # 添加凭据
        pool.add(Credential(
            cred_id="user1",
            cred_type=CredentialType.COOKIE,
            value={"session": "xxx"},
            domain="example.com"
        ))

        # 获取可用凭据
        cred = pool.get_available(domain="example.com")

        # 报告使用结果
        pool.report_result(cred.cred_id, success=True)
    """

    def __init__(
        self,
        cooldown_on_fail: int = 60,      # 失败后冷却秒数
        max_fail_count: int = 3,          # 最大连续失败次数
        min_success_rate: float = 0.3,    # 最低成功率
    ):
        """
        初始化凭据池

        Args:
            cooldown_on_fail: 失败后冷却时间（秒）
            max_fail_count: 最大连续失败次数后标记为blocked
            min_success_rate: 最低成功率，低于此值降低权重
        """
        self.credentials: Dict[str, Credential] = {}
        self.cooldown_on_fail = cooldown_on_fail
        self.max_fail_count = max_fail_count
        self.min_success_rate = min_success_rate

        # 当前索引（用于轮询）
        self._current_index = 0

        logger.info("[CredentialPool] 初始化完成")

    # ==================== 基本操作 ====================

    def add(self, credential: Credential) -> bool:
        """
        添加凭据

        Args:
            credential: 凭据对象

        Returns:
            是否添加成功
        """
        if credential.cred_id in self.credentials:
            logger.warning(f"[CredentialPool] 凭据已存在: {credential.cred_id}")
            return False

        self.credentials[credential.cred_id] = credential
        logger.info(f"[CredentialPool] 添加凭据: {credential.cred_id} ({credential.cred_type.value})")
        return True

    def remove(self, cred_id: str) -> bool:
        """
        移除凭据

        Args:
            cred_id: 凭据ID

        Returns:
            是否移除成功
        """
        if cred_id in self.credentials:
            del self.credentials[cred_id]
            logger.info(f"[CredentialPool] 移除凭据: {cred_id}")
            return True
        return False

    def get(self, cred_id: str) -> Optional[Credential]:
        """获取指定凭据"""
        return self.credentials.get(cred_id)

    def list_all(self) -> List[Credential]:
        """列出所有凭据"""
        return list(self.credentials.values())

    # ==================== 选择策略 ====================

    def get_available(
        self,
        domain: Optional[str] = None,
        cred_type: Optional[CredentialType] = None
    ) -> Optional[Credential]:
        """
        获取可用凭据（智能选择）

        Args:
            domain: 筛选域名
            cred_type: 筛选凭据类型

        Returns:
            可用凭据，无可用返回None
        """
        candidates = self._get_candidates(domain, cred_type)

        if not candidates:
            logger.warning("[CredentialPool] 无可用凭据")
            return None

        # 基于权重和成功率选择
        selected = self._weighted_select(candidates)

        if selected:
            logger.debug(f"[CredentialPool] 选择凭据: {selected.cred_id}")

        return selected

    def get_fresh(
        self,
        domain: Optional[str] = None,
        cred_type: Optional[CredentialType] = None
    ) -> Optional[Credential]:
        """
        获取最新鲜的凭据（使用次数最少）

        Args:
            domain: 筛选域名
            cred_type: 筛选凭据类型

        Returns:
            凭据
        """
        candidates = self._get_candidates(domain, cred_type)

        if not candidates:
            return None

        # 按使用次数排序
        candidates.sort(key=lambda c: c.use_count)
        return candidates[0]

    def rotate(
        self,
        domain: Optional[str] = None,
        cred_type: Optional[CredentialType] = None
    ) -> Optional[Credential]:
        """
        轮换凭据（轮询方式）

        Args:
            domain: 筛选域名
            cred_type: 筛选凭据类型

        Returns:
            凭据
        """
        candidates = self._get_candidates(domain, cred_type)

        if not candidates:
            return None

        # 轮询选择
        self._current_index = (self._current_index + 1) % len(candidates)
        return candidates[self._current_index]

    def _get_candidates(
        self,
        domain: Optional[str] = None,
        cred_type: Optional[CredentialType] = None
    ) -> List[Credential]:
        """获取候选凭据"""
        candidates = []

        for cred in self.credentials.values():
            # 检查可用性
            if not cred.is_available:
                continue

            # 检查域名
            if domain and cred.domain and cred.domain != domain:
                continue

            # 检查类型
            if cred_type and cred.cred_type != cred_type:
                continue

            candidates.append(cred)

        return candidates

    def _weighted_select(self, candidates: List[Credential]) -> Optional[Credential]:
        """加权随机选择"""
        if not candidates:
            return None

        # 计算权重
        weights = []
        for cred in candidates:
            # 基础权重
            weight = cred.weight

            # 成功率调整
            if cred.success_rate < self.min_success_rate:
                weight *= 0.5

            # 使用频率调整（使用少的权重高）
            if cred.use_count > 0:
                weight *= 1.0 / (1 + cred.use_count * 0.1)

            weights.append(max(0.1, weight))

        # 加权随机选择
        total = sum(weights)
        r = random.uniform(0, total)

        cumulative = 0
        for cred, weight in zip(candidates, weights):
            cumulative += weight
            if r <= cumulative:
                return cred

        return candidates[-1]

    # ==================== 结果报告 ====================

    def report_result(
        self,
        cred_id: str,
        success: bool,
        cooldown: bool = True
    ):
        """
        报告凭据使用结果

        Args:
            cred_id: 凭据ID
            success: 是否成功
            cooldown: 失败时是否冷却
        """
        cred = self.credentials.get(cred_id)
        if not cred:
            return

        cred.mark_used(success)

        if not success:
            # 检查是否需要冷却
            if cooldown:
                cred.set_cooldown(self.cooldown_on_fail)
                logger.info(f"[CredentialPool] 凭据冷却: {cred_id}")

            # 检查是否需要标记为blocked
            consecutive_fails = self._count_consecutive_fails(cred)
            if consecutive_fails >= self.max_fail_count:
                cred.status = CredentialStatus.BLOCKED
                logger.warning(f"[CredentialPool] 凭据被封禁: {cred_id}")

    def _count_consecutive_fails(self, cred: Credential) -> int:
        """计算连续失败次数（简化实现）"""
        # 实际实现应该记录历史
        if cred.success_rate == 0 and cred.use_count > 0:
            return cred.fail_count
        return 0

    # ==================== 维护操作 ====================

    def refresh_cooldowns(self):
        """刷新冷却状态"""
        now = datetime.now()
        for cred in self.credentials.values():
            if cred.status == CredentialStatus.COOLING:
                if cred.cooldown_until and now >= cred.cooldown_until:
                    cred.clear_cooldown()
                    logger.info(f"[CredentialPool] 凭据冷却结束: {cred.cred_id}")

    def mark_expired(self, cred_id: str):
        """标记凭据过期"""
        cred = self.credentials.get(cred_id)
        if cred:
            cred.status = CredentialStatus.EXPIRED
            logger.info(f"[CredentialPool] 凭据过期: {cred_id}")

    def reactivate(self, cred_id: str):
        """重新激活凭据"""
        cred = self.credentials.get(cred_id)
        if cred:
            cred.status = CredentialStatus.ACTIVE
            cred.clear_cooldown()
            logger.info(f"[CredentialPool] 凭据重新激活: {cred_id}")

    # ==================== 统计 ====================

    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = {
            "total": len(self.credentials),
            "by_status": {},
            "by_type": {},
            "total_uses": 0,
            "total_success": 0,
        }

        for cred in self.credentials.values():
            # 按状态统计
            status = cred.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # 按类型统计
            ctype = cred.cred_type.value
            stats["by_type"][ctype] = stats["by_type"].get(ctype, 0) + 1

            # 使用统计
            stats["total_uses"] += cred.use_count
            stats["total_success"] += cred.success_count

        # 总成功率
        if stats["total_uses"] > 0:
            stats["overall_success_rate"] = stats["total_success"] / stats["total_uses"]
        else:
            stats["overall_success_rate"] = 1.0

        return stats

    def get_available_count(
        self,
        domain: Optional[str] = None,
        cred_type: Optional[CredentialType] = None
    ) -> int:
        """获取可用凭据数量"""
        return len(self._get_candidates(domain, cred_type))
