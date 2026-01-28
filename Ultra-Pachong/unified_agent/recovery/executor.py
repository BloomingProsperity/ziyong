"""
恢复模块 - 恢复执行器

协调执行恢复动作。
"""

import time
import logging
from typing import Any, Dict, List, Optional

from .types import FaultDecision, RecoveryAction, RecoveryResult
from .actions import ActionHandler

logger = logging.getLogger(__name__)


class RecoveryExecutor:
    """
    恢复执行器

    协调执行多个恢复动作。

    使用示例:
        executor = RecoveryExecutor()
        executor.set_proxy_manager(proxy_manager)

        result = executor.execute(decision, context)
        if result.success:
            print("恢复成功")
    """

    def __init__(self, max_attempts: int = 3):
        """
        初始化执行器

        Args:
            max_attempts: 最大尝试次数
        """
        self.max_attempts = max_attempts
        self.action_handler = ActionHandler()
        self.execution_log: List[Dict] = []
        self._recovery_count = 0

    # ==================== 依赖注入 ====================

    def set_proxy_manager(self, proxy_manager: Any):
        self.action_handler.set_proxy_manager(proxy_manager)

    def set_config(self, config: Any):
        self.action_handler.set_config(config)

    def set_browser_context(self, browser_context: Any):
        self.action_handler.set_browser_context(browser_context)

    def set_rate_limiter(self, rate_limiter: Any):
        self.action_handler.set_rate_limiter(rate_limiter)

    def set_cookie_pool(self, cookie_pool: Any):
        self.action_handler.set_cookie_pool(cookie_pool)

    # ==================== 执行 ====================

    def execute(
        self,
        decision: FaultDecision,
        context: Optional[Dict[str, Any]] = None
    ) -> RecoveryResult:
        """
        执行恢复

        Args:
            decision: 故障决策
            context: 上下文信息

        Returns:
            恢复结果
        """
        context = context or {}
        start_time = time.time()
        actions_taken: List[RecoveryAction] = []
        errors: List[str] = []

        logger.info(f"[Executor] 开始恢复: {decision.fault_category.value}")
        logger.info(f"[Executor] 计划动作: {[a.value for a in decision.recovery_actions]}")

        # 检查是否可自动恢复
        if not decision.auto_recoverable:
            logger.warning("[Executor] 该故障不可自动恢复")
            return RecoveryResult(
                success=False,
                actions_taken=[],
                outcome="需要人工介入",
                cost_time_ms=(time.time() - start_time) * 1000,
                errors=["故障不可自动恢复"]
            )

        # 依次执行恢复动作
        for action in decision.recovery_actions:
            try:
                success = self.action_handler.execute(action, context)
                actions_taken.append(action)

                if success:
                    logger.info(f"[Executor] 动作成功: {action.value}")
                    self._recovery_count += 1

                    self.execution_log.append({
                        "timestamp": time.time(),
                        "fault_category": decision.fault_category.value,
                        "action": action.value,
                        "success": True
                    })

                    # 成功后停止
                    break
                else:
                    logger.warning(f"[Executor] 动作失败: {action.value}")
                    errors.append(f"{action.value} 失败")

            except Exception as e:
                logger.error(f"[Executor] 动作异常: {action.value} - {e}")
                errors.append(f"{action.value} 异常: {str(e)}")

        cost_time = (time.time() - start_time) * 1000
        success = len(actions_taken) > 0 and len(errors) < len(actions_taken)

        result = RecoveryResult(
            success=success,
            actions_taken=actions_taken,
            outcome="成功恢复" if success else "恢复失败",
            cost_time_ms=cost_time,
            errors=errors
        )

        logger.info(f"[Executor] 结果: {result.outcome} ({cost_time:.1f}ms)")

        return result

    def execute_single(
        self,
        action: RecoveryAction,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        执行单个动作

        Args:
            action: 恢复动作
            context: 上下文

        Returns:
            是否成功
        """
        context = context or {}
        return self.action_handler.execute(action, context)

    # ==================== 状态管理 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取恢复统计"""
        return {
            "total_recoveries": self._recovery_count,
            "execution_log_count": len(self.execution_log),
            "action_handler_stats": self.action_handler.get_stats(),
        }

    def reset(self):
        """重置状态"""
        self.action_handler.reset()
        self._recovery_count = 0
        logger.info("[Executor] 状态已重置")


# ==================== 便捷函数 ====================

def recover_from_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> RecoveryResult:
    """
    便捷函数：从错误恢复

    Args:
        error: 异常对象
        context: 上下文

    Returns:
        恢复结果
    """
    from .decision_tree import FaultDecisionTree

    tree = FaultDecisionTree()
    decision = tree.diagnose(error, context)

    executor = RecoveryExecutor()
    return executor.execute(decision, context)
