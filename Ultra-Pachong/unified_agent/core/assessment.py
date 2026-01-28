"""
资源评估模块 - 根据目标网站评估所需资源

核心功能:
1. 代理需求判断
2. 账号需求判断
3. 签名服务需求判断
4. 成本与时间预估
5. 配置代码生成

作者: Ultra Pachong Team
文档: unified_agent/skills/00-quick-start.md
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================

class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class ProxyType(str, Enum):
    """代理类型"""
    NONE = "none"
    DATACENTER = "datacenter"  # 数据中心代理
    RESIDENTIAL = "residential"  # 住宅代理
    MOBILE = "mobile"  # 移动代理


# ==================== 数据类型定义 ====================

@dataclass
class ProxyAdvice:
    """代理建议"""
    required: bool
    reason: str
    proxy_type: ProxyType = ProxyType.NONE
    recommendation: str = ""
    estimated_cost: str = "免费"  # "免费" or "约￥X/月"


@dataclass
class AccountAdvice:
    """账号建议"""
    required: bool
    reason: str
    min_accounts: int = 0
    recommended_accounts: int = 0
    account_type: str = ""  # "普通用户" / "会员" / "企业账号"
    notes: List[str] = field(default_factory=list)


@dataclass
class SignatureAdvice:
    """签名服务建议"""
    required: bool
    reason: str
    complexity: str = "simple"  # simple / medium / complex / extreme
    recommendation: str = ""


@dataclass
class ResourcePlan:
    """资源需求计划"""
    # 代理
    needs_proxy: bool
    proxy_advice: ProxyAdvice

    # 账号
    needs_login: bool
    account_advice: AccountAdvice

    # 签名服务
    needs_signature_service: bool
    signature_advice: SignatureAdvice

    # 时间与成本
    estimated_time: str  # "5-10分钟" / "1-2小时" / "1-3天"
    estimated_cost: str  # "免费" / "约￥100/月" / "约￥500/月"

    # 推荐配置
    recommended_config: Dict[str, Any]

    # 风险等级
    risk_level: RiskLevel

    # 额外建议
    notes: List[str] = field(default_factory=list)

    def to_report(self) -> str:
        """生成资源评估报告"""
        risk_emoji = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.HIGH: "🔴",
            RiskLevel.EXTREME: "⚫",
        }

        report = f"""
# 资源需求评估报告

## 难度评估
- **风险等级**: {risk_emoji[self.risk_level]} {self.risk_level.value.upper()}
- **预估时间**: {self.estimated_time}
- **预估成本**: {self.estimated_cost}

## 代理需求
**是否需要**: {'✅ 需要' if self.needs_proxy else '❌ 不需要'}
- **原因**: {self.proxy_advice.reason}
"""
        if self.needs_proxy:
            report += f"- **代理类型**: {self.proxy_advice.proxy_type.value}\n"
            report += f"- **建议**: {self.proxy_advice.recommendation}\n"
            report += f"- **成本**: {self.proxy_advice.estimated_cost}\n"

        report += f"""
## 账号需求
**是否需要**: {'✅ 需要' if self.needs_login else '❌ 不需要'}
- **原因**: {self.account_advice.reason}
"""
        if self.needs_login:
            report += f"- **最少账号数**: {self.account_advice.min_accounts}\n"
            report += f"- **推荐账号数**: {self.account_advice.recommended_accounts}\n"
            report += f"- **账号类型**: {self.account_advice.account_type}\n"
            if self.account_advice.notes:
                report += "- **注意事项**:\n"
                for note in self.account_advice.notes:
                    report += f"  - {note}\n"

        report += f"""
## 签名服务需求
**是否需要**: {'✅ 需要' if self.needs_signature_service else '❌ 不需要'}
- **原因**: {self.signature_advice.reason}
"""
        if self.needs_signature_service:
            report += f"- **复杂度**: {self.signature_advice.complexity}\n"
            report += f"- **建议**: {self.signature_advice.recommendation}\n"

        report += "\n## 推荐配置\n\n```python\n"
        report += self._generate_config_code()
        report += "\n```\n"

        if self.notes:
            report += "\n## 额外建议\n\n"
            for note in self.notes:
                report += f"- {note}\n"

        return report

    def _generate_config_code(self) -> str:
        """生成配置代码"""
        lines = ["from unified_agent import Brain, AgentConfig", ""]
        lines.append("# 创建配置")
        lines.append("config = AgentConfig(")

        config_items = []

        # 代理配置
        if self.needs_proxy:
            config_items.append("    # 代理配置")
            config_items.append("    proxy_enabled=True,")
            config_items.append('    proxy_url="http://your-proxy.com:8080",')
            config_items.append('    # proxy_username="user",')
            config_items.append('    # proxy_password="pass",')

        # 速率配置
        rps = self.recommended_config.get("requests_per_second", 1.0)
        config_items.append("    # 请求频率")
        config_items.append(f"    requests_per_second={rps},")

        # 并发配置
        concurrency = self.recommended_config.get("concurrency", 5)
        config_items.append("    # 并发数")
        config_items.append(f"    concurrency={concurrency},")

        # 超时配置
        timeout = self.recommended_config.get("timeout", 30)
        config_items.append("    # 超时时间")
        config_items.append(f"    timeout={timeout},")

        # Cookie配置
        if self.needs_login:
            config_items.append("    # Cookie配置")
            config_items.append("    cookies={")
            config_items.append('        "session_id": "your_session_id",')
            config_items.append("        # 添加其他Cookie")
            config_items.append("    },")

        lines.append("\n".join(config_items))
        lines.append(")")
        lines.append("")
        lines.append("# 创建Brain")
        lines.append("brain = Brain(config)")

        return "\n".join(lines)


# ==================== 资源评估器 ====================

class ResourceAssessment:
    """资源需求评估器"""

    def __init__(self):
        """初始化评估器"""
        logger.info("[ResourceAssessment] Initialized")

    def assess(
        self,
        url: str,
        target_count: int,
        analysis: Optional[Dict[str, Any]] = None,
    ) -> ResourcePlan:
        """
        评估资源需求

        Args:
            url: 目标URL
            target_count: 目标数据量
            analysis: 侦查分析结果（SiteAnalysis）

        Returns:
            资源需求计划
        """
        logger.info(f"[ResourceAssessment] Assessing: url={url}, target_count={target_count}")

        # 如果没有分析结果，使用默认值
        if not analysis:
            analysis = {
                "anti_scrape_level": "medium",
                "requires_login": False,
                "has_signature": False,
                "detection_risks": [],
            }

        anti_scrape_level = analysis.get("anti_scrape_level", "medium")
        requires_login = analysis.get("requires_login", False)
        has_signature = analysis.get("has_signature", False)
        detection_risks = analysis.get("detection_risks", [])

        # 评估代理需求
        proxy_advice = self._assess_proxy(
            anti_scrape_level,
            target_count,
            detection_risks,
        )

        # 评估账号需求
        account_advice = self._assess_account(
            requires_login,
            anti_scrape_level,
            target_count,
        )

        # 评估签名服务需求
        signature_advice = self._assess_signature(
            has_signature,
            anti_scrape_level,
        )

        # 确定风险等级
        risk_level = self._determine_risk_level(anti_scrape_level)

        # 预估时间
        estimated_time = self._estimate_time(
            target_count,
            anti_scrape_level,
            proxy_advice.required,
        )

        # 预估成本
        estimated_cost = self._estimate_cost(
            proxy_advice,
            account_advice,
            anti_scrape_level,
        )

        # 生成推荐配置
        recommended_config = self._generate_recommended_config(
            anti_scrape_level,
            proxy_advice.required,
            target_count,
        )

        # 额外建议
        notes = self._generate_notes(
            anti_scrape_level,
            proxy_advice.required,
            account_advice.required,
            signature_advice.required,
        )

        plan = ResourcePlan(
            needs_proxy=proxy_advice.required,
            proxy_advice=proxy_advice,
            needs_login=account_advice.required,
            account_advice=account_advice,
            needs_signature_service=signature_advice.required,
            signature_advice=signature_advice,
            estimated_time=estimated_time,
            estimated_cost=estimated_cost,
            recommended_config=recommended_config,
            risk_level=risk_level,
            notes=notes,
        )

        logger.info(
            f"[ResourceAssessment] Assessment complete: "
            f"proxy={proxy_advice.required}, "
            f"login={account_advice.required}, "
            f"signature={signature_advice.required}, "
            f"risk={risk_level.value}"
        )

        return plan

    def _assess_proxy(
        self,
        anti_scrape_level: str,
        target_count: int,
        detection_risks: List[str],
    ) -> ProxyAdvice:
        """评估代理需求"""
        # 规则1: 反爬等级极高，必须使用住宅代理
        if anti_scrape_level == "extreme":
            return ProxyAdvice(
                required=True,
                reason="目标网站反爬等级极高，必须使用代理",
                proxy_type=ProxyType.RESIDENTIAL,
                recommendation="推荐使用住宅代理，数据中心代理容易被识别",
                estimated_cost="约￥500-2000/月",
            )

        # 规则2: 反爬等级高，需要数据中心代理
        if anti_scrape_level == "high":
            return ProxyAdvice(
                required=True,
                reason="目标网站有IP频率限制",
                proxy_type=ProxyType.DATACENTER,
                recommendation="可使用数据中心代理，性价比更高",
                estimated_cost="约￥100-500/月",
            )

        # 规则3: 大规模请求，建议使用代理
        if target_count > 1000:
            return ProxyAdvice(
                required=True,
                reason=f"计划请求量({target_count})较大，建议使用代理分散请求",
                proxy_type=ProxyType.DATACENTER,
                estimated_cost="约￥100-300/月",
            )

        # 规则4: 检测到IP限制
        if "ip_blocking" in detection_risks or "rate_limiting" in detection_risks:
            return ProxyAdvice(
                required=True,
                reason="检测到网站有IP封禁或限流机制",
                proxy_type=ProxyType.DATACENTER,
                estimated_cost="约￥100-300/月",
            )

        # 规则5: 小规模+低反爬，不需要代理
        if anti_scrape_level in ["low", "medium"] and target_count < 500:
            return ProxyAdvice(
                required=False,
                reason="小规模抓取 + 反爬等级不高，可以不用代理",
                recommendation="控制好请求频率即可（建议1-2次/秒）",
            )

        # 默认：中等规模，建议使用代理
        return ProxyAdvice(
            required=False,
            reason="可选使用代理，能提高稳定性",
            proxy_type=ProxyType.DATACENTER,
            recommendation="如果遇到429错误，建议启用代理",
            estimated_cost="约￥100-300/月",
        )

    def _assess_account(
        self,
        requires_login: bool,
        anti_scrape_level: str,
        target_count: int,
    ) -> AccountAdvice:
        """评估账号需求"""
        # 规则1: 不需要登录
        if not requires_login:
            return AccountAdvice(
                required=False,
                reason="目标网站不需要登录",
            )

        # 规则2: 需要登录 + 反爬极高 → 多账号
        if anti_scrape_level == "extreme":
            recommended = max(5, target_count // 200)
            return AccountAdvice(
                required=True,
                reason="需要登录 + 反爬等级极高",
                min_accounts=3,
                recommended_accounts=recommended,
                account_type="普通用户账号",
                notes=[
                    "建议使用多个账号轮换，避免单账号请求过多被封",
                    "账号之间需要间隔足够时间",
                    "准备备用账号以防封号",
                ],
            )

        # 规则3: 需要登录 + 反爬高 → 2-3个账号
        if anti_scrape_level == "high":
            return AccountAdvice(
                required=True,
                reason="需要登录 + 反爬等级较高",
                min_accounts=1,
                recommended_accounts=3,
                account_type="普通用户账号",
                notes=[
                    "建议准备2-3个账号备用",
                    "控制单账号请求频率",
                ],
            )

        # 规则4: 需要登录 + 低/中反爬 → 1个账号
        return AccountAdvice(
            required=True,
            reason="需要登录才能访问数据",
            min_accounts=1,
            recommended_accounts=1,
            account_type="普通用户账号",
            notes=["控制请求频率，避免触发限流"],
        )

    def _assess_signature(
        self,
        has_signature: bool,
        anti_scrape_level: str,
    ) -> SignatureAdvice:
        """评估签名服务需求"""
        if not has_signature:
            return SignatureAdvice(
                required=False,
                reason="目标网站无签名参数",
            )

        # 规则1: 极高反爬 + 签名 → 复杂签名
        if anti_scrape_level == "extreme":
            return SignatureAdvice(
                required=True,
                reason="检测到复杂签名算法（如京东h5st、淘宝mtop）",
                complexity="extreme",
                recommendation="建议使用浏览器RPC方案或专业签名服务",
            )

        # 规则2: 高反爬 + 签名 → 中等签名
        if anti_scrape_level == "high":
            return SignatureAdvice(
                required=True,
                reason="检测到签名参数，需要实现签名算法",
                complexity="medium",
                recommendation="可以尝试逆向签名算法，或使用浏览器执行JS",
            )

        # 规则3: 低/中反爬 + 签名 → 简单签名
        return SignatureAdvice(
            required=True,
            reason="检测到简单签名参数",
            complexity="simple",
            recommendation="通常是MD5/HMAC等标准算法，容易实现",
        )

    def _determine_risk_level(self, anti_scrape_level: str) -> RiskLevel:
        """确定风险等级"""
        mapping = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "extreme": RiskLevel.EXTREME,
        }
        return mapping.get(anti_scrape_level, RiskLevel.MEDIUM)

    def _estimate_time(
        self,
        target_count: int,
        anti_scrape_level: str,
        needs_proxy: bool,
    ) -> str:
        """预估时间"""
        # 基础速率（请求/秒）
        rates = {
            "low": 5.0,
            "medium": 2.0,
            "high": 1.0,
            "extreme": 0.3,
        }

        rate = rates.get(anti_scrape_level, 1.0)

        # 如果不需要代理，可以稍微快一些
        if not needs_proxy and anti_scrape_level in ["low", "medium"]:
            rate *= 1.5

        # 预估秒数
        estimated_seconds = target_count / rate

        # 转换为友好格式
        if estimated_seconds < 60:
            return f"{int(estimated_seconds)}秒"
        elif estimated_seconds < 3600:
            minutes = int(estimated_seconds / 60)
            return f"{minutes}-{minutes + 5}分钟"
        elif estimated_seconds < 86400:
            hours = int(estimated_seconds / 3600)
            return f"{hours}-{hours + 1}小时"
        else:
            days = int(estimated_seconds / 86400)
            return f"{days}-{days + 1}天"

    def _estimate_cost(
        self,
        proxy_advice: ProxyAdvice,
        account_advice: AccountAdvice,
        anti_scrape_level: str,
    ) -> str:
        """预估成本"""
        if not proxy_advice.required and not account_advice.required:
            return "免费"

        costs = []

        # 代理成本
        if proxy_advice.required:
            if proxy_advice.proxy_type == ProxyType.RESIDENTIAL:
                costs.append(("代理", 500, 2000))
            elif proxy_advice.proxy_type == ProxyType.DATACENTER:
                costs.append(("代理", 100, 500))

        # 账号成本（通常免费，除非是付费会员）
        # 这里假设都是免费注册账号

        if not costs:
            return "约￥50-100/月"

        # 计算总成本
        total_min = sum(c[1] for c in costs)
        total_max = sum(c[2] for c in costs)

        return f"约￥{total_min}-{total_max}/月"

    def _generate_recommended_config(
        self,
        anti_scrape_level: str,
        needs_proxy: bool,
        target_count: int,
    ) -> Dict[str, Any]:
        """生成推荐配置"""
        # 请求频率
        rps_mapping = {
            "low": 5.0,
            "medium": 2.0,
            "high": 1.0,
            "extreme": 0.3,
        }
        rps = rps_mapping.get(anti_scrape_level, 1.0)

        # 并发数
        concurrency_mapping = {
            "low": 10,
            "medium": 5,
            "high": 3,
            "extreme": 1,
        }
        concurrency = concurrency_mapping.get(anti_scrape_level, 5)

        # 超时时间
        timeout_mapping = {
            "low": 30,
            "medium": 30,
            "high": 60,
            "extreme": 120,
        }
        timeout = timeout_mapping.get(anti_scrape_level, 30)

        return {
            "requests_per_second": rps,
            "concurrency": concurrency,
            "timeout": timeout,
            "max_retries": 3,
        }

    def _generate_notes(
        self,
        anti_scrape_level: str,
        needs_proxy: bool,
        needs_login: bool,
        needs_signature: bool,
    ) -> List[str]:
        """生成额外建议"""
        notes = []

        # 反爬等级建议
        if anti_scrape_level == "extreme":
            notes.append("⚠️ 目标网站反爬极强，建议先小规模测试")
            notes.append("💡 考虑降低目标数据量，分批次抓取")

        if anti_scrape_level == "high":
            notes.append("⚠️ 建议增加随机延迟，模拟人类行为")

        # 代理建议
        if needs_proxy:
            notes.append("🌐 代理推荐: 亿牛云、芝麻代理、快代理")

        # 账号建议
        if needs_login:
            notes.append("👤 请确保Cookie有效期足够长")

        # 签名建议
        if needs_signature:
            notes.append("🔐 签名算法可能需要时间逆向，建议先尝试浏览器RPC方案")

        # 通用建议
        notes.append("📊 建议先运行 smart_investigate() 完整侦查")
        notes.append("🔍 遇到问题时，查看日志并使用诊断模块分析")

        return notes


# ==================== 配置代码生成 ====================

def generate_config_code(plan: ResourcePlan) -> str:
    """
    生成配置代码

    Args:
        plan: 资源计划

    Returns:
        Python配置代码
    """
    return plan._generate_config_code()


# ==================== 工具函数 ====================

def create_assessment() -> ResourceAssessment:
    """创建资源评估器（便捷函数）"""
    return ResourceAssessment()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    # 创建评估器
    assessment = create_assessment()

    # 示例1: 低反爬网站，小规模
    print("\n=== 场景1: 低反爬 + 小规模 ===")
    plan1 = assessment.assess(
        url="https://example.com",
        target_count=100,
        analysis={
            "anti_scrape_level": "low",
            "requires_login": False,
            "has_signature": False,
            "detection_risks": [],
        },
    )
    print(plan1.to_report())

    # 示例2: 高反爬网站，需要登录
    print("\n=== 场景2: 高反爬 + 需要登录 ===")
    plan2 = assessment.assess(
        url="https://jd.com",
        target_count=5000,
        analysis={
            "anti_scrape_level": "high",
            "requires_login": True,
            "has_signature": True,
            "detection_risks": ["ip_blocking", "rate_limiting"],
        },
    )
    print(plan2.to_report())

    # 示例3: 极高反爬网站
    print("\n=== 场景3: 极高反爬 ===")
    plan3 = assessment.assess(
        url="https://taobao.com",
        target_count=10000,
        analysis={
            "anti_scrape_level": "extreme",
            "requires_login": True,
            "has_signature": True,
            "detection_risks": ["ip_blocking", "fingerprinting", "behavior_analysis"],
        },
    )
    print(plan3.to_report())
