"""Core module - 基础类型、配置和任务模型"""
from .types import TaskStatus, TaskType, Difficulty
from .task import Task, TaskResult
from .deps import DependencyManager, ensure_deps, check_deps
from .config import AgentConfig

__all__ = [
    'TaskStatus', 'TaskType', 'Difficulty',
    'Task', 'TaskResult',
    'DependencyManager', 'ensure_deps', 'check_deps',
    'AgentConfig',
]
