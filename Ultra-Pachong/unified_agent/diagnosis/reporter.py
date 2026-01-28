"""
诊断模块 - 报告生成器

负责生成各种格式的诊断报告。
"""

import json
from typing import List

from .types import DiagnosisResult


class DiagnosisReporter:
    """诊断报告生成器"""

    @staticmethod
    def to_text(result: DiagnosisResult) -> str:
        """生成文本格式报告"""
        return result.to_report()

    @staticmethod
    def to_json(result: DiagnosisResult) -> str:
        """生成JSON格式报告"""
        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    @staticmethod
    def to_markdown(result: DiagnosisResult) -> str:
        """生成Markdown格式报告"""
        lines = [
            f"# 诊断报告",
            "",
            f"**时间**: {result.diagnosed_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 错误信息",
            "",
            f"| 项目 | 内容 |",
            f"|------|------|",
            f"| 类型 | {result.error_type} |",
            f"| 错误码 | {result.error_code or 'N/A'} |",
            f"| 分类 | {result.category.value} |",
            f"| 严重程度 | {result.severity.value} |",
            "",
            "## 诊断分析",
            "",
            f"**根因**: {result.root_cause}",
            "",
            f"**置信度**: {result.confidence:.0%}",
            "",
            "### 可能原因",
            "",
        ]

        for i, cause in enumerate(result.probable_causes, 1):
            lines.append(f"{i}. {cause}")

        lines.extend([
            "",
            "## 解决方案",
            "",
            f"**推荐方案**: {result.recommended_solution.action}",
            "",
            f"> {result.recommended_solution.description}",
            "",
            f"**可自动修复**: {'是' if result.auto_fixable else '否'}",
            "",
            "### 全部方案",
            "",
            "| 动作 | 描述 | 成功率 | 可自动 |",
            "|------|------|--------|--------|",
        ])

        for s in result.solutions:
            auto = "✓" if s.auto_fixable else "✗"
            lines.append(f"| {s.action} | {s.description} | {s.estimated_success_rate:.0%} | {auto} |")

        return "\n".join(lines)

    @staticmethod
    def to_summary(result: DiagnosisResult) -> str:
        """生成简短摘要"""
        return (
            f"[{result.severity.value.upper()}] {result.error_type}: {result.root_cause} "
            f"→ 建议: {result.recommended_solution.action}"
        )

    @staticmethod
    def batch_report(results: List[DiagnosisResult]) -> str:
        """批量生成报告摘要"""
        if not results:
            return "无诊断结果"

        lines = [
            f"# 批量诊断报告 ({len(results)} 条)",
            "",
            "| # | 类型 | 严重程度 | 根因 | 建议动作 |",
            "|---|------|----------|------|----------|",
        ]

        for i, r in enumerate(results, 1):
            lines.append(
                f"| {i} | {r.error_type} | {r.severity.value} | "
                f"{r.root_cause[:30]}... | {r.recommended_solution.action} |"
            )

        # 统计
        severity_counts = {}
        for r in results:
            severity_counts[r.severity.value] = severity_counts.get(r.severity.value, 0) + 1

        lines.extend([
            "",
            "## 统计",
            "",
        ])
        for sev, count in sorted(severity_counts.items()):
            lines.append(f"- {sev}: {count}")

        return "\n".join(lines)
