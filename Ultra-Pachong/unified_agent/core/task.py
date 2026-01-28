"""任务模型 - 定义任务结构和结果"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any, Dict, List
from uuid import uuid4

from .types import TaskStatus, TaskType, Difficulty


@dataclass
class Task:
    """任务定义"""
    # 必填
    description: str                           # 用户原始描述

    # 自动生成
    id: str = field(default_factory=lambda: str(uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)

    # 分析后填充
    task_type: TaskType = TaskType.EXPLICIT
    difficulty: Difficulty = Difficulty.EASY
    target_url: Optional[str] = None
    target_data: Optional[List[str]] = None    # 要提取的字段

    # 执行状态
    status: TaskStatus = TaskStatus.PENDING

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    status: TaskStatus

    # 成功时
    data: Optional[Any] = None
    data_count: int = 0

    # 失败时
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    # 统计
    duration_ms: int = 0
    retries: int = 0

    # 用于学习
    strategies_tried: List[str] = field(default_factory=list)
    knowledge_gained: Optional[Dict] = None


@dataclass
class ExecutionContext:
    """执行上下文 - 贯穿整个任务生命周期"""
    task: Task

    # 当前状态
    current_step: str = ""
    current_module: str = ""

    # 累积数据
    collected_data: List[Any] = field(default_factory=list)
    errors: List[Dict] = field(default_factory=list)
    decisions: List[Dict] = field(default_factory=list)

    # 资源
    session_id: Optional[str] = None
    proxy_id: Optional[str] = None
