"""决策日志 (来自 17-feedback-loop) - 记录每个决策"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
from pathlib import Path


class DecisionType(str, Enum):
    """决策类型"""
    MODULE_SELECT = "module_select"      # 选择模块
    STRATEGY_SELECT = "strategy_select"  # 选择策略
    ERROR_HANDLE = "error_handle"        # 错误处理
    RETRY = "retry"                      # 重试决策
    ABORT = "abort"                      # 放弃决策


class DecisionOutcome(str, Enum):
    """决策结果"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    PENDING = "pending"


@dataclass
class Decision:
    """决策记录"""
    task_id: str
    type: DecisionType
    description: str                      # 决策描述
    reason: str                           # 决策原因

    # 上下文
    context: Dict[str, Any] = field(default_factory=dict)
    alternatives: List[str] = field(default_factory=list)  # 备选方案

    # 结果
    outcome: DecisionOutcome = DecisionOutcome.PENDING
    outcome_reason: str = ""

    # 时间
    timestamp: datetime = field(default_factory=datetime.now)


class DecisionLogger:
    """决策日志记录器"""

    def __init__(self, log_dir: str = "data/decisions"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_task: Optional[str] = None
        self._decisions: List[Decision] = []

    def start_task(self, task_id: str):
        """开始新任务"""
        self._current_task = task_id
        self._decisions = []

    def log(self, decision: Decision):
        """记录决策"""
        self._decisions.append(decision)

    def log_decision(self, type: DecisionType, description: str,
                     reason: str, **kwargs) -> Decision:
        """便捷记录方法"""
        decision = Decision(
            task_id=self._current_task or "unknown",
            type=type,
            description=description,
            reason=reason,
            **kwargs
        )
        self.log(decision)
        return decision

    def update_outcome(self, decision: Decision, outcome: DecisionOutcome,
                       reason: str = ""):
        """更新决策结果"""
        decision.outcome = outcome
        decision.outcome_reason = reason

    def end_task(self, save: bool = True) -> List[Decision]:
        """结束任务，返回所有决策"""
        if save and self._current_task:
            self._save_decisions()
        decisions = self._decisions
        self._decisions = []
        self._current_task = None
        return decisions

    def _save_decisions(self):
        """保存决策日志"""
        if not self._decisions:
            return

        filename = f"{self._current_task}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = self.log_dir / filename

        data = []
        for d in self._decisions:
            data.append({
                "task_id": d.task_id,
                "type": d.type.value,
                "description": d.description,
                "reason": d.reason,
                "context": d.context,
                "alternatives": d.alternatives,
                "outcome": d.outcome.value,
                "outcome_reason": d.outcome_reason,
                "timestamp": d.timestamp.isoformat()
            })

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_failed_decisions(self) -> List[Decision]:
        """获取失败的决策（用于学习）"""
        return [d for d in self._decisions if d.outcome == DecisionOutcome.FAILED]
