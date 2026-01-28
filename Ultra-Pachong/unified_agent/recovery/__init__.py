"""
恢复模块 (Recovery Module)

模块职责:
- 故障分类
- 决策树匹配
- 自动恢复执行
- 恢复结果追踪

使用示例:
    from unified_agent.recovery import FaultDecisionTree, RecoveryExecutor

    tree = FaultDecisionTree()
    decision = tree.diagnose(error, context)

    executor = RecoveryExecutor()
    result = executor.execute(decision, context)
"""

from .types import (
    FaultCategory,
    FaultSeverity,
    RecoveryAction,
    FaultDecision,
    RecoveryResult,
)
from .decision_tree import FaultDecisionTree
from .executor import RecoveryExecutor
from .actions import ActionHandler

__all__ = [
    # Types
    "FaultCategory",
    "FaultSeverity",
    "RecoveryAction",
    "FaultDecision",
    "RecoveryResult",
    # Classes
    "FaultDecisionTree",
    "RecoveryExecutor",
    "ActionHandler",
]
