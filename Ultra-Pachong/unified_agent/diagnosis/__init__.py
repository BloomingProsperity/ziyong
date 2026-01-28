"""
诊断模块 (Diagnosis Module)

模块职责:
- 错误分析与分类
- 根因诊断
- 自动修复
- 诊断报告生成

使用示例:
    from unified_agent.diagnosis import Diagnoser, AutoFixer
    
    diagnoser = Diagnoser()
    result = diagnoser.diagnose(error, context)
    
    fixer = AutoFixer()
    fixer.fix(result, context)
"""

from .types import (
    Severity,
    ErrorCategory,
    Solution,
    DiagnosisResult,
)
from .classifier import ErrorClassifier
from .analyzer import ErrorAnalyzer
from .fixer import AutoFixer
from .reporter import DiagnosisReporter
from .diagnoser import Diagnoser

__all__ = [
    # Types
    "Severity",
    "ErrorCategory",
    "Solution",
    "DiagnosisResult",
    # Classes
    "ErrorClassifier",
    "ErrorAnalyzer",
    "AutoFixer",
    "DiagnosisReporter",
    "Diagnoser",
]
