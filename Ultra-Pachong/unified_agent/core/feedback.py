"""
反馈循环模块 (Feedback Loop Module)

功能:
- 执行追溯系统
- 数据验证系统
- 经验学习系统
- 反馈调节器
- 知识积累与进化

错误码: E_FEEDBACK_001 ~ E_FEEDBACK_004
"""

import hashlib
import json
import re
import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 错误码定义
# ============================================================================

class FeedbackError(Exception):
    """反馈循环错误基类"""
    def __init__(self, code: str, message: str, details: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


# 错误码
E_FEEDBACK_001 = "E_FEEDBACK_001"  # 决策记录失败
E_FEEDBACK_002 = "E_FEEDBACK_002"  # 数据验证失败
E_FEEDBACK_003 = "E_FEEDBACK_003"  # 经验记录失败
E_FEEDBACK_004 = "E_FEEDBACK_004"  # 反馈调节失败


# ============================================================================
# 枚举
# ============================================================================

class DecisionType(Enum):
    """决策类型"""
    ENTRY_SELECTION = "entry_selection"      # 入口选择
    STRATEGY_SWITCH = "strategy_switch"      # 策略切换
    PARAMETER_ADJUST = "parameter_adjust"    # 参数调整
    ERROR_RECOVERY = "error_recovery"        # 错误恢复
    DATA_VALIDATION = "data_validation"      # 数据验证


class ValidationResult(Enum):
    """验证结果"""
    VALID = "valid"                  # 有效
    SUSPICIOUS = "suspicious"        # 可疑
    INVALID = "invalid"              # 无效
    UNVERIFIABLE = "unverifiable"    # 无法验证


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class Decision:
    """决策记录"""
    id: str                                  # 唯一ID
    timestamp: datetime                      # 时间戳
    type: DecisionType                       # 决策类型

    # 决策依据
    context: Dict[str, Any]                  # 上下文状态
    options: List[str]                       # 可选方案
    selected: str                            # 选择的方案
    reason: str                              # 选择理由

    # 决策结果
    outcome: Optional[str] = None            # 执行结果
    success: Optional[bool] = None           # 是否成功
    metrics: Dict[str, float] = field(default_factory=dict)  # 指标

    # 追溯链
    parent_id: Optional[str] = None          # 父决策ID
    triggered_by: Optional[str] = None       # 触发原因


@dataclass
class DataValidation:
    """数据验证结果"""
    field: str
    value: Any
    result: ValidationResult
    method: str                      # 验证方法
    evidence: str                    # 验证依据
    confidence: float                # 置信度 0-1


@dataclass
class Experience:
    """经验记录"""
    id: str
    timestamp: datetime

    # 场景
    domain: str                      # 目标域名
    task_type: str                   # 任务类型
    context: Dict[str, Any]          # 上下文

    # 策略
    strategy: str                    # 使用的策略
    parameters: Dict[str, Any]       # 参数配置

    # 结果
    success: bool                    # 是否成功
    metrics: Dict[str, float]        # 指标
    error: Optional[str] = None      # 错误信息

    # 归纳
    lesson: Optional[str] = None     # 经验教训
    tags: List[str] = field(default_factory=list)


@dataclass
class FeedbackSignal:
    """反馈信号"""
    timestamp: datetime
    signal_type: str           # success/failure/warning/metric
    value: float               # 信号值
    source: str                # 来源
    context: Dict              # 上下文


# ============================================================================
# 决策日志器
# ============================================================================

class DecisionLogger:
    """决策日志器"""

    def __init__(self, storage_path: str = "./decisions"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.current_session: List[Decision] = []
        self.session_id = self._generate_session_id()

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return hashlib.md5(
            f"{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

    def log_decision(
        self,
        type: DecisionType,
        context: Dict,
        options: List[str],
        selected: str,
        reason: str,
        parent_id: str = None,
    ) -> Decision:
        """
        记录决策

        Args:
            type: 决策类型
            context: 上下文
            options: 可选方案
            selected: 选择的方案
            reason: 选择理由
            parent_id: 父决策ID

        Returns:
            决策对象
        """
        if not reason or len(reason) < 10:
            raise FeedbackError(
                E_FEEDBACK_001,
                "决策理由不能为空或过短，必须说明依据",
                {"reason": reason}
            )

        decision = Decision(
            id=f"{self.session_id}_{len(self.current_session):04d}",
            timestamp=datetime.now(),
            type=type,
            context=context,
            options=options,
            selected=selected,
            reason=reason,
            parent_id=parent_id,
        )

        self.current_session.append(decision)
        self._persist(decision)

        logger.info(f"[DECISION] 记录决策: {decision.id} - {decision.selected}")

        return decision

    def update_outcome(
        self,
        decision_id: str,
        outcome: str,
        success: bool,
        metrics: Dict[str, float] = None
    ):
        """更新决策结果"""
        for d in self.current_session:
            if d.id == decision_id:
                d.outcome = outcome
                d.success = success
                d.metrics = metrics or {}
                self._persist(d)
                logger.info(f"[DECISION] 更新结果: {decision_id} - {outcome}")
                break

    def get_trace(self, decision_id: str) -> List[Decision]:
        """获取决策链路 - 追溯所有相关决策"""
        trace = []
        current = self._find_decision(decision_id)

        while current:
            trace.insert(0, current)
            if current.parent_id:
                current = self._find_decision(current.parent_id)
            else:
                break

        return trace

    def _find_decision(self, decision_id: str) -> Optional[Decision]:
        """查找决策"""
        for d in self.current_session:
            if d.id == decision_id:
                return d
        return None

    def _persist(self, decision: Decision):
        """持久化存储"""
        file_path = self.storage_path / f"session_{self.session_id}.jsonl"
        with open(file_path, "a", encoding="utf-8") as f:
            data = {
                "id": decision.id,
                "timestamp": decision.timestamp.isoformat(),
                "type": decision.type.value,
                "context": decision.context,
                "options": decision.options,
                "selected": decision.selected,
                "reason": decision.reason,
                "outcome": decision.outcome,
                "success": decision.success,
                "metrics": decision.metrics,
            }
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def export_report(self) -> str:
        """导出决策报告"""
        report = ["# 决策追溯报告\n"]
        report.append(f"会话ID: {self.session_id}\n")
        report.append(f"决策数: {len(self.current_session)}\n\n")

        for d in self.current_session:
            report.append(f"## [{d.id}] {d.type.value}\n")
            report.append(f"- 时间: {d.timestamp}\n")
            report.append(f"- 选项: {d.options}\n")
            report.append(f"- 选择: {d.selected}\n")
            report.append(f"- 理由: {d.reason}\n")
            if d.outcome:
                report.append(f"- 结果: {d.outcome} ({'成功' if d.success else '失败'})\n")
            report.append("\n")

        return "".join(report)


# ============================================================================
# 数据验证器
# ============================================================================

class DataValidator:
    """
    数据验证器

    核心原则:
    1. 不允许胡编乱造数据
    2. 无法验证的数据要标记
    3. 可疑数据需要交叉验证
    """

    # 数据格式规则
    FORMAT_RULES = {
        "price": {
            "pattern": r"^\d+(\.\d{1,2})?$",
            "range": (0, 10000000),
            "description": "价格必须是正数，最多2位小数"
        },
        "phone": {
            "pattern": r"^1[3-9]\d{9}$",
            "description": "中国大陆手机号格式"
        },
        "email": {
            "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$",
            "description": "邮箱格式"
        },
        "url": {
            "pattern": r"^https?://[\w\.-]+",
            "description": "URL格式"
        },
        "date": {
            "pattern": r"^\d{4}-\d{2}-\d{2}$",
            "description": "日期格式 YYYY-MM-DD"
        },
    }

    def __init__(self):
        self.validation_log: List[DataValidation] = []

    def validate_item(
        self,
        data: Dict[str, Any],
        schema: Dict[str, str],
    ) -> Dict[str, DataValidation]:
        """
        验证单条数据

        Args:
            data: 待验证数据
            schema: 字段类型定义 {"price": "price", "phone": "phone"}

        Returns:
            各字段验证结果
        """
        results = {}

        for field, value in data.items():
            field_type = schema.get(field)

            if field_type:
                result = self._validate_field(field, value, field_type)
            else:
                result = DataValidation(
                    field=field,
                    value=value,
                    result=ValidationResult.UNVERIFIABLE,
                    method="no_schema",
                    evidence="字段未定义验证规则",
                    confidence=0.5
                )

            results[field] = result
            self.validation_log.append(result)

        return results

    def _validate_field(
        self,
        field: str,
        value: Any,
        field_type: str
    ) -> DataValidation:
        """验证单个字段"""

        if value is None or value == "":
            return DataValidation(
                field=field,
                value=value,
                result=ValidationResult.INVALID,
                method="empty_check",
                evidence="值为空",
                confidence=1.0
            )

        rule = self.FORMAT_RULES.get(field_type)
        if not rule:
            return DataValidation(
                field=field,
                value=value,
                result=ValidationResult.UNVERIFIABLE,
                method="no_rule",
                evidence=f"未定义 {field_type} 类型的验证规则",
                confidence=0.5
            )

        # 格式检查
        if "pattern" in rule:
            if not re.match(rule["pattern"], str(value)):
                return DataValidation(
                    field=field,
                    value=value,
                    result=ValidationResult.INVALID,
                    method="pattern_match",
                    evidence=f"不匹配格式: {rule['description']}",
                    confidence=0.9
                )

        # 范围检查
        if "range" in rule:
            try:
                num_value = float(value)
                min_val, max_val = rule["range"]
                if not (min_val <= num_value <= max_val):
                    return DataValidation(
                        field=field,
                        value=value,
                        result=ValidationResult.SUSPICIOUS,
                        method="range_check",
                        evidence=f"值 {num_value} 超出正常范围 [{min_val}, {max_val}]",
                        confidence=0.7
                    )
            except (ValueError, TypeError):
                pass

        return DataValidation(
            field=field,
            value=value,
            result=ValidationResult.VALID,
            method="all_checks_passed",
            evidence="通过所有验证",
            confidence=0.9
        )

    def cross_validate(
        self,
        data: Dict[str, Any],
        other_sources: List[Dict[str, Any]],
        key_fields: List[str],
    ) -> Dict[str, DataValidation]:
        """
        交叉验证 - 与其他数据源对比

        防止数据投毒和伪造
        """
        results = {}

        for field in key_fields:
            our_value = data.get(field)
            other_values = [s.get(field) for s in other_sources if s.get(field)]

            if not other_values:
                results[field] = DataValidation(
                    field=field,
                    value=our_value,
                    result=ValidationResult.UNVERIFIABLE,
                    method="cross_validate",
                    evidence="无其他数据源可对比",
                    confidence=0.5
                )
                continue

            # 检查一致性
            match_count = sum(1 for v in other_values if self._values_match(our_value, v))
            match_rate = match_count / len(other_values)

            if match_rate >= 0.8:
                results[field] = DataValidation(
                    field=field,
                    value=our_value,
                    result=ValidationResult.VALID,
                    method="cross_validate",
                    evidence=f"{match_rate:.0%} 数据源一致",
                    confidence=match_rate
                )
            elif match_rate >= 0.5:
                results[field] = DataValidation(
                    field=field,
                    value=our_value,
                    result=ValidationResult.SUSPICIOUS,
                    method="cross_validate",
                    evidence=f"仅 {match_rate:.0%} 数据源一致，需人工确认",
                    confidence=match_rate
                )
            else:
                results[field] = DataValidation(
                    field=field,
                    value=our_value,
                    result=ValidationResult.INVALID,
                    method="cross_validate",
                    evidence=f"与多数数据源不一致 ({match_rate:.0%})，可能是假数据",
                    confidence=1 - match_rate
                )

        return results

    def _values_match(self, v1: Any, v2: Any, tolerance: float = 0.1) -> bool:
        """检查两个值是否匹配"""
        if v1 == v2:
            return True

        # 数值容差匹配
        try:
            n1, n2 = float(v1), float(v2)
            return abs(n1 - n2) / max(n1, n2, 1) <= tolerance
        except (ValueError, TypeError):
            pass

        # 字符串相似度
        if isinstance(v1, str) and isinstance(v2, str):
            # 简单相似度检查
            v1_lower, v2_lower = v1.lower(), v2.lower()
            if v1_lower == v2_lower:
                return True
            # 包含关系
            if v1_lower in v2_lower or v2_lower in v1_lower:
                return True

        return False

    def generate_report(self) -> str:
        """生成验证报告"""
        total = len(self.validation_log)
        if total == 0:
            return "# 数据验证报告\n\n无验证记录"

        valid = sum(1 for v in self.validation_log if v.result == ValidationResult.VALID)
        suspicious = sum(1 for v in self.validation_log if v.result == ValidationResult.SUSPICIOUS)
        invalid = sum(1 for v in self.validation_log if v.result == ValidationResult.INVALID)

        report = [
            "# 数据验证报告\n",
            f"- 总字段: {total}\n",
            f"- 有效: {valid} ({valid / total * 100:.1f}%)\n",
            f"- 可疑: {suspicious} ({suspicious / total * 100:.1f}%)\n",
            f"- 无效: {invalid} ({invalid / total * 100:.1f}%)\n",
            "\n## 问题字段\n",
        ]

        for v in self.validation_log:
            if v.result in [ValidationResult.SUSPICIOUS, ValidationResult.INVALID]:
                report.append(f"- [{v.result.value}] {v.field}: {v.evidence}\n")

        return "".join(report)


# ============================================================================
# 知识库
# ============================================================================

class KnowledgeBase:
    """知识库 - 积累的经验和规律"""

    def __init__(self, storage_path: str = "./knowledge"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.experiences: List[Experience] = []

        # 域名知识
        self.domain_knowledge: Dict[str, Dict] = defaultdict(dict)

        # 策略知识
        self.strategy_effectiveness: Dict[str, Dict[str, float]] = defaultdict(dict)

        # 错误模式
        self.error_patterns: Dict[str, List[str]] = defaultdict(list)

    def record_experience(
        self,
        domain: str,
        task_type: str,
        context: Dict,
        strategy: str,
        parameters: Dict,
        success: bool,
        metrics: Dict[str, float],
        error: str = None,
    ) -> Experience:
        """记录经验"""
        exp = Experience(
            id=f"exp_{len(self.experiences):06d}",
            timestamp=datetime.now(),
            domain=domain,
            task_type=task_type,
            context=context,
            strategy=strategy,
            parameters=parameters,
            success=success,
            metrics=metrics,
            error=error,
        )

        self.experiences.append(exp)
        self._update_knowledge(exp)

        logger.info(f"[LEARN] 记录经验: {domain} / {strategy} - {'成功' if success else '失败'}")

        return exp

    def _update_knowledge(self, exp: Experience):
        """从经验中更新知识"""

        # 更新域名知识
        dk = self.domain_knowledge[exp.domain]
        if "attempts" not in dk:
            dk["attempts"] = 0
            dk["successes"] = 0
            dk["best_strategy"] = None
            dk["avg_metrics"] = {}

        dk["attempts"] += 1
        if exp.success:
            dk["successes"] += 1
        dk["success_rate"] = dk["successes"] / dk["attempts"]

        # 更新策略效果
        key = f"{exp.domain}:{exp.strategy}"
        if key not in self.strategy_effectiveness:
            self.strategy_effectiveness[key] = {
                "attempts": 0,
                "successes": 0,
                "total_metrics": {}
            }

        se = self.strategy_effectiveness[key]
        se["attempts"] += 1
        if exp.success:
            se["successes"] += 1
        se["success_rate"] = se["successes"] / se["attempts"]

        # 找出最佳策略
        best = None
        best_rate = 0
        for k, v in self.strategy_effectiveness.items():
            if k.startswith(f"{exp.domain}:") and v["success_rate"] > best_rate:
                best_rate = v["success_rate"]
                best = k.split(":")[1]
        dk["best_strategy"] = best

        # 记录错误模式
        if not exp.success and exp.error:
            self.error_patterns[exp.domain].append(exp.error)

    def get_recommendation(
        self,
        domain: str,
        task_type: str,
        context: Dict = None,
    ) -> Dict:
        """
        根据历史经验给出推荐

        这是"进化"能力的体现 - 基于历史学习
        """
        dk = self.domain_knowledge.get(domain, {})

        recommendation = {
            "has_experience": bool(dk),
            "success_rate": dk.get("success_rate", 0),
            "best_strategy": dk.get("best_strategy"),
            "warnings": [],
            "suggestions": [],
        }

        # 基于历史成功率给建议
        if recommendation["success_rate"] < 0.5:
            recommendation["warnings"].append(
                f"历史成功率低 ({recommendation['success_rate']:.0%})，建议谨慎"
            )

        # 基于错误模式给建议
        errors = self.error_patterns.get(domain, [])
        if errors:
            common_errors = self._find_common_patterns(errors)
            for err in common_errors[:3]:
                recommendation["warnings"].append(f"常见错误: {err}")

        # 推荐最佳策略
        if recommendation["best_strategy"]:
            se = self.strategy_effectiveness.get(
                f"{domain}:{recommendation['best_strategy']}"
            )
            if se:
                recommendation["suggestions"].append(
                    f"推荐策略: {recommendation['best_strategy']} "
                    f"(成功率 {se['success_rate']:.0%})"
                )

        return recommendation

    def _find_common_patterns(self, errors: List[str], min_count: int = 2) -> List[str]:
        """找出常见错误模式"""
        # 简化错误信息
        simplified = []
        for err in errors:
            # 提取关键词
            keywords = ["blocked", "captcha", "rate limit", "timeout", "sign", "token"]
            for kw in keywords:
                if kw in err.lower():
                    simplified.append(kw)
                    break
            else:
                simplified.append(err[:50])

        counter = Counter(simplified)
        return [item for item, count in counter.most_common() if count >= min_count]

    def summarize_domain(self, domain: str) -> str:
        """
        归纳总结某个域名的经验

        这是"数据搜集整理归纳"能力的体现
        """
        dk = self.domain_knowledge.get(domain, {})

        if not dk:
            return f"# {domain}\n\n无历史数据"

        # 获取该域名所有经验
        domain_exps = [e for e in self.experiences if e.domain == domain]

        # 策略统计
        strategy_stats = defaultdict(lambda: {"attempts": 0, "successes": 0})
        for exp in domain_exps:
            strategy_stats[exp.strategy]["attempts"] += 1
            if exp.success:
                strategy_stats[exp.strategy]["successes"] += 1

        # 生成报告
        report = [
            f"# {domain} 经验总结\n\n",
            f"## 基础统计\n",
            f"- 总尝试: {dk.get('attempts', 0)}\n",
            f"- 成功率: {dk.get('success_rate', 0):.1%}\n",
            f"- 最佳策略: {dk.get('best_strategy', '未知')}\n\n",
            f"## 策略效果\n\n",
            "| 策略 | 尝试 | 成功 | 成功率 |\n",
            "|------|------|------|--------|\n",
        ]

        for strategy, stats in strategy_stats.items():
            rate = stats["successes"] / stats["attempts"] if stats["attempts"] else 0
            report.append(
                f"| {strategy} | {stats['attempts']} | "
                f"{stats['successes']} | {rate:.1%} |\n"
            )

        # 常见错误
        errors = self.error_patterns.get(domain, [])
        if errors:
            report.append("\n## 常见错误\n\n")
            for err in self._find_common_patterns(errors)[:5]:
                report.append(f"- {err}\n")

        # 经验教训
        lessons = [e.lesson for e in domain_exps if e.lesson]
        if lessons:
            report.append("\n## 经验教训\n\n")
            for lesson in lessons[:5]:
                report.append(f"- {lesson}\n")

        return "".join(report)

    def add_lesson(self, experience_id: str, lesson: str):
        """添加经验教训"""
        for exp in self.experiences:
            if exp.id == experience_id:
                exp.lesson = lesson
                logger.info(f"[LEARN] 添加经验教训: {experience_id}")
                break


# ============================================================================
# 反馈控制器
# ============================================================================

class FeedbackController:
    """
    反馈控制器

    核心功能:
    1. 收集反馈信号
    2. 分析趋势
    3. 自动调整
    4. 防止震荡
    """

    def __init__(
        self,
        window_size: int = 50,
        adjustment_threshold: float = 0.3,
        cooldown_seconds: int = 30,
    ):
        self.window_size = window_size
        self.adjustment_threshold = adjustment_threshold
        self.cooldown_seconds = cooldown_seconds

        # 信号窗口
        self.signals: deque = deque(maxlen=window_size)

        # 调整历史
        self.adjustments: List[Dict] = []
        self.last_adjustment: Optional[datetime] = None

        # 当前参数
        self.current_params: Dict = {
            "rate_limit": 1.0,       # 请求速率
            "retry_delay": 1.0,      # 重试延迟
            "concurrent": 5,         # 并发数
            "proxy_rotate": 10,      # 代理轮换频率
        }

        # 参数边界
        self.param_bounds = {
            "rate_limit": (0.1, 10.0),
            "retry_delay": (0.5, 30.0),
            "concurrent": (1, 50),
            "proxy_rotate": (1, 100),
        }

    def receive_signal(self, signal: FeedbackSignal):
        """接收反馈信号"""
        self.signals.append(signal)

        # 检查是否需要调整
        if self._should_adjust():
            self._auto_adjust()

    def _should_adjust(self) -> bool:
        """判断是否需要调整"""
        # 信号不足
        if len(self.signals) < 10:
            return False

        # 冷却期内
        if self.last_adjustment:
            elapsed = (datetime.now() - self.last_adjustment).total_seconds()
            if elapsed < self.cooldown_seconds:
                return False

        # 计算最近的成功率
        recent = list(self.signals)[-20:]
        success_count = sum(1 for s in recent if s.signal_type == "success")
        success_rate = success_count / len(recent)

        # 成功率变化过大
        if success_rate < 0.5:
            return True

        return False

    def _auto_adjust(self):
        """自动调整参数"""
        # 分析当前状态
        recent = list(self.signals)[-20:]
        success_count = sum(1 for s in recent if s.signal_type == "success")
        success_rate = success_count / len(recent)

        # 分析错误类型
        error_signals = [s for s in recent if s.signal_type == "failure"]
        rate_limit_errors = sum(
            1 for s in error_signals
            if "rate" in s.context.get("error", "").lower()
        )
        block_errors = sum(
            1 for s in error_signals
            if "block" in s.context.get("error", "").lower()
        )

        adjustments = {}
        reasons = []

        # 根据错误类型调整
        if rate_limit_errors > 3:
            # 触发限流，降低速度
            new_rate = self.current_params["rate_limit"] * 0.5
            new_rate = max(new_rate, self.param_bounds["rate_limit"][0])
            adjustments["rate_limit"] = new_rate
            reasons.append(f"限流错误多，降低速率 -> {new_rate:.1f}/s")

            new_concurrent = max(1, self.current_params["concurrent"] - 2)
            adjustments["concurrent"] = new_concurrent
            reasons.append(f"降低并发 -> {new_concurrent}")

        if block_errors > 3:
            # 触发封禁，加快代理轮换
            new_rotate = max(1, self.current_params["proxy_rotate"] // 2)
            adjustments["proxy_rotate"] = new_rotate
            reasons.append(f"封禁错误多，加快代理轮换 -> 每{new_rotate}次")

        if success_rate > 0.9 and not adjustments:
            # 成功率高，可以适当提速
            new_rate = min(
                self.current_params["rate_limit"] * 1.2,
                self.param_bounds["rate_limit"][1]
            )
            adjustments["rate_limit"] = new_rate
            reasons.append(f"成功率高，尝试提速 -> {new_rate:.1f}/s")

        # 应用调整
        if adjustments:
            self.current_params.update(adjustments)
            self.last_adjustment = datetime.now()

            self.adjustments.append({
                "timestamp": datetime.now(),
                "success_rate": success_rate,
                "adjustments": adjustments,
                "reasons": reasons,
            })

            logger.info(f"[FEEDBACK] 自动调整: {'; '.join(reasons)}")

    def get_params(self) -> Dict:
        """获取当前参数"""
        return self.current_params.copy()

    def report_adjustment_history(self) -> str:
        """报告调整历史"""
        if not self.adjustments:
            return "无调整记录"

        report = ["# 参数调整历史\n\n"]
        for adj in self.adjustments[-10:]:
            report.append(f"## {adj['timestamp']}\n")
            report.append(f"- 成功率: {adj['success_rate']:.1%}\n")
            report.append(f"- 调整: {adj['adjustments']}\n")
            report.append(f"- 原因: {'; '.join(adj['reasons'])}\n\n")

        return "".join(report)


# ============================================================================
# 使用示例
# ============================================================================

def example_usage():
    """使用示例"""
    print("=" * 80)
    print("反馈循环模块 - 使用示例")
    print("=" * 80)

    # 1. 决策追溯
    print("\n示例 1: 决策追溯")
    print("-" * 80)
    logger_obj = DecisionLogger()

    d1 = logger_obj.log_decision(
        type=DecisionType.ENTRY_SELECTION,
        context={"domain": "jd.com"},
        options=["API", "Mobile", "Web"],
        selected="Mobile",
        reason="历史数据显示移动端成功率85%，高于Web的60%"
    )
    logger_obj.update_outcome(d1.id, "成功获取数据", True, {"items": 100})

    print(f"决策ID: {d1.id}")
    print(f"决策类型: {d1.type.value}")
    print(f"选择: {d1.selected}")
    print(f"理由: {d1.reason}")
    print(f"结果: {d1.outcome}")

    # 2. 数据验证
    print("\n示例 2: 数据验证")
    print("-" * 80)
    validator = DataValidator()

    test_data = {
        "price": "99.99",
        "phone": "13800138000",
        "email": "test@example.com",
        "url": "https://example.com"
    }

    schema = {
        "price": "price",
        "phone": "phone",
        "email": "email",
        "url": "url"
    }

    results = validator.validate_item(test_data, schema)
    for field, result in results.items():
        print(f"{field}: {result.result.value} - {result.evidence}")

    # 3. 经验学习
    print("\n示例 3: 经验学习")
    print("-" * 80)
    kb = KnowledgeBase()

    # 记录几次经验
    for i in range(5):
        kb.record_experience(
            domain="jd.com",
            task_type="product_scrape",
            context={},
            strategy="mobile_api" if i % 2 == 0 else "web_scrape",
            parameters={},
            success=i % 3 != 0,  # 部分成功
            metrics={"items": 100},
            error="rate limit" if i % 3 == 0 else None
        )

    # 获取推荐
    recommendation = kb.get_recommendation("jd.com", "product_scrape")
    print(f"有经验: {recommendation['has_experience']}")
    print(f"成功率: {recommendation['success_rate']:.1%}")
    print(f"最佳策略: {recommendation['best_strategy']}")
    if recommendation['warnings']:
        print(f"警告: {recommendation['warnings']}")
    if recommendation['suggestions']:
        print(f"建议: {recommendation['suggestions']}")

    # 4. 反馈调节
    print("\n示例 4: 反馈调节")
    print("-" * 80)
    controller = FeedbackController()

    # 模拟接收信号
    for i in range(15):
        signal = FeedbackSignal(
            timestamp=datetime.now(),
            signal_type="success" if i % 3 != 0 else "failure",
            value=1.0 if i % 3 != 0 else 0.0,
            source="task_executor",
            context={"error": "rate limit" if i % 3 == 0 else ""}
        )
        controller.receive_signal(signal)

    params = controller.get_params()
    print(f"当前参数: {params}")


if __name__ == "__main__":
    example_usage()
