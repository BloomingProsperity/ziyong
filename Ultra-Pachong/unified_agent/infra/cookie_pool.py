"""
Cookie Pool - 免费Cookie池

核心思路：通过浏览器自动访问目标网站，收集匿名Cookie。
无需购买，完全免费，自动化生成。

使用场景：
1. 目标网站需要Cookie才能访问
2. 单个Cookie被风控后需要切换
3. 高并发需要多个会话

工作流程：
1. 启动无头浏览器
2. 访问目标网站（模拟真实用户）
3. 等待网站设置Cookie
4. 收集并存储Cookie
5. 按需分发Cookie
"""

from __future__ import annotations

import json
import time
import random
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CookieStatus(Enum):
    """Cookie状态"""
    FRESH = "fresh"           # 新鲜可用
    USED = "used"             # 已使用中
    COOLDOWN = "cooldown"     # 冷却中
    EXPIRED = "expired"       # 已过期
    BLOCKED = "blocked"       # 被封禁


@dataclass
class CookieSession:
    """Cookie会话"""
    id: str                                    # 唯一ID
    domain: str                                # 目标域名
    cookies: dict[str, str]                    # Cookie字典
    user_agent: str                            # 对应的UA
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None
    use_count: int = 0
    status: CookieStatus = CookieStatus.FRESH
    expires_at: Optional[datetime] = None      # 过期时间
    fail_count: int = 0                        # 失败次数

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "domain": self.domain,
            "cookies": self.cookies,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "use_count": self.use_count,
            "status": self.status.value,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "fail_count": self.fail_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CookieSession":
        return cls(
            id=data["id"],
            domain=data["domain"],
            cookies=data["cookies"],
            user_agent=data["user_agent"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used_at=datetime.fromisoformat(data["last_used_at"]) if data.get("last_used_at") else None,
            use_count=data.get("use_count", 0),
            status=CookieStatus(data.get("status", "fresh")),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            fail_count=data.get("fail_count", 0),
        )

    def is_valid(self) -> bool:
        """检查Cookie是否有效"""
        if self.status in (CookieStatus.EXPIRED, CookieStatus.BLOCKED):
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            self.status = CookieStatus.EXPIRED
            return False
        return True

    def mark_used(self):
        """标记为已使用"""
        self.last_used_at = datetime.now()
        self.use_count += 1
        self.status = CookieStatus.USED

    def mark_failed(self):
        """标记失败"""
        self.fail_count += 1
        if self.fail_count >= 3:
            self.status = CookieStatus.BLOCKED

    def cooldown(self, seconds: int = 60):
        """进入冷却"""
        self.status = CookieStatus.COOLDOWN


class CookiePool:
    """
    免费Cookie池

    自动通过浏览器访问网站生成Cookie，无需购买。

    使用方式：
        pool = CookiePool("jd.com")

        # 自动生成10个Cookie
        await pool.generate(count=10)

        # 获取一个可用Cookie
        session = pool.get()
        if session:
            # 使用 session.cookies 发起请求
            pass

        # 标记成功或失败
        pool.mark_success(session.id)
        pool.mark_failed(session.id)
    """

    # 常用User-Agent列表
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]

    def __init__(
        self,
        domain: str,
        storage_path: str = "./data/cookies",
        max_pool_size: int = 50,
        cookie_lifetime_hours: int = 24,
        cooldown_seconds: int = 60,
    ):
        """
        初始化Cookie池

        Args:
            domain: 目标域名 (如 "jd.com")
            storage_path: Cookie存储路径
            max_pool_size: 最大池大小
            cookie_lifetime_hours: Cookie有效期（小时）
            cooldown_seconds: 使用后冷却时间（秒）
        """
        self.domain = domain
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.pool_file = self.storage_path / f"{domain.replace('.', '_')}_pool.json"

        self.max_pool_size = max_pool_size
        self.cookie_lifetime = timedelta(hours=cookie_lifetime_hours)
        self.cooldown_seconds = cooldown_seconds

        self.sessions: dict[str, CookieSession] = {}
        self._load()

    def _load(self):
        """从文件加载Cookie池"""
        if self.pool_file.exists():
            try:
                data = json.loads(self.pool_file.read_text(encoding="utf-8"))
                for session_data in data.get("sessions", []):
                    session = CookieSession.from_dict(session_data)
                    if session.is_valid():
                        self.sessions[session.id] = session
                logger.info(f"[CookiePool] Loaded {len(self.sessions)} cookies for {self.domain}")
            except Exception as e:
                logger.error(f"[CookiePool] Failed to load: {e}")

    def _save(self):
        """保存Cookie池到文件"""
        data = {
            "domain": self.domain,
            "updated_at": datetime.now().isoformat(),
            "sessions": [s.to_dict() for s in self.sessions.values()],
        }
        self.pool_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _generate_id(self, cookies: dict) -> str:
        """生成Cookie会话ID"""
        content = json.dumps(cookies, sort_keys=True) + str(time.time())
        return hashlib.md5(content.encode()).hexdigest()[:12]

    async def generate(
        self,
        count: int = 5,
        url: Optional[str] = None,
        wait_seconds: float = 3.0,
        actions: Optional[list[dict]] = None,
    ) -> int:
        """
        自动生成Cookie（通过浏览器访问）

        Args:
            count: 要生成的数量
            url: 目标URL，默认为 https://{domain}
            wait_seconds: 等待Cookie设置的时间
            actions: 可选的页面交互动作

        Returns:
            成功生成的数量
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("[CookiePool] Playwright not installed. Run: pip install playwright && playwright install chromium")
            return 0

        target_url = url or f"https://www.{self.domain}"
        generated = 0

        logger.info(f"[CookiePool] Generating {count} cookies for {self.domain}...")

        async with async_playwright() as p:
            for i in range(count):
                if len(self.sessions) >= self.max_pool_size:
                    logger.warning(f"[CookiePool] Pool is full ({self.max_pool_size})")
                    break

                try:
                    # 选择随机UA
                    user_agent = random.choice(self.USER_AGENTS)

                    # 启动浏览器
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--disable-dev-shm-usage',
                        ]
                    )

                    context = await browser.new_context(
                        user_agent=user_agent,
                        viewport={'width': 1920, 'height': 1080},
                        locale='zh-CN',
                    )

                    page = await context.new_page()

                    # 注入反检测脚本
                    await page.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        window.chrome = {runtime: {}};
                    """)

                    # 访问页面
                    await page.goto(target_url, wait_until='networkidle', timeout=30000)

                    # 等待Cookie设置
                    await page.wait_for_timeout(int(wait_seconds * 1000))

                    # 执行可选动作（模拟真实用户）
                    if actions:
                        for action in actions:
                            await self._execute_action(page, action)
                    else:
                        # 默认：随机滚动
                        await page.evaluate("window.scrollBy(0, Math.random() * 500)")
                        await page.wait_for_timeout(1000)

                    # 收集Cookie
                    cookies_list = await context.cookies()
                    cookies = {c['name']: c['value'] for c in cookies_list if self.domain in c.get('domain', '')}

                    if cookies:
                        session = CookieSession(
                            id=self._generate_id(cookies),
                            domain=self.domain,
                            cookies=cookies,
                            user_agent=user_agent,
                            expires_at=datetime.now() + self.cookie_lifetime,
                        )
                        self.sessions[session.id] = session
                        generated += 1
                        logger.info(f"[CookiePool] Generated cookie {i+1}/{count}: {len(cookies)} items")

                    await browser.close()

                    # 随机延迟，避免被检测
                    if i < count - 1:
                        await self._random_delay()

                except Exception as e:
                    logger.error(f"[CookiePool] Failed to generate cookie {i+1}: {e}")

        self._save()
        logger.info(f"[CookiePool] Generated {generated} cookies. Pool size: {len(self.sessions)}")
        return generated

    async def _execute_action(self, page, action: dict):
        """执行页面动作"""
        action_type = action.get("type")

        if action_type == "click":
            await page.click(action["selector"])
        elif action_type == "scroll":
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
        elif action_type == "wait":
            await page.wait_for_timeout(int(action.get("seconds", 1) * 1000))
        elif action_type == "hover":
            await page.hover(action["selector"])

    async def _random_delay(self):
        """随机延迟"""
        import asyncio
        delay = random.uniform(2, 5)
        await asyncio.sleep(delay)

    def get(self, prefer_fresh: bool = True) -> Optional[CookieSession]:
        """
        获取一个可用的Cookie

        Args:
            prefer_fresh: 是否优先使用新鲜Cookie

        Returns:
            CookieSession 或 None
        """
        # 清理过期Cookie
        self._cleanup()

        # 按优先级排序：新鲜 > 冷却完成 > 已使用
        available = []
        now = datetime.now()

        for session in self.sessions.values():
            if not session.is_valid():
                continue

            if session.status == CookieStatus.FRESH:
                available.insert(0, session)  # 新鲜优先
            elif session.status == CookieStatus.COOLDOWN:
                # 检查冷却是否完成
                if session.last_used_at:
                    cooldown_end = session.last_used_at + timedelta(seconds=self.cooldown_seconds)
                    if now > cooldown_end:
                        session.status = CookieStatus.FRESH
                        available.append(session)
            elif session.status == CookieStatus.USED:
                if not prefer_fresh:
                    available.append(session)

        if available:
            session = available[0]
            session.mark_used()
            self._save()
            return session

        return None

    def mark_success(self, session_id: str):
        """标记Cookie使用成功"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.cooldown(self.cooldown_seconds)
            self._save()

    def mark_failed(self, session_id: str):
        """标记Cookie使用失败"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.mark_failed()
            if session.status == CookieStatus.BLOCKED:
                logger.warning(f"[CookiePool] Cookie {session_id} blocked, removing")
            self._save()

    def _cleanup(self):
        """清理过期和无效Cookie"""
        to_remove = [sid for sid, s in self.sessions.items() if not s.is_valid()]
        for sid in to_remove:
            del self.sessions[sid]
        if to_remove:
            self._save()
            logger.info(f"[CookiePool] Cleaned up {len(to_remove)} invalid cookies")

    def stats(self) -> dict:
        """获取池统计信息"""
        self._cleanup()

        status_counts = {s.value: 0 for s in CookieStatus}
        total_uses = 0

        for session in self.sessions.values():
            status_counts[session.status.value] += 1
            total_uses += session.use_count

        return {
            "domain": self.domain,
            "total": len(self.sessions),
            "max_size": self.max_pool_size,
            "by_status": status_counts,
            "total_uses": total_uses,
            "fill_rate": f"{len(self.sessions) / self.max_pool_size * 100:.1f}%",
        }

    def need_refill(self, threshold: float = 0.3) -> bool:
        """检查是否需要补充Cookie"""
        available = sum(
            1 for s in self.sessions.values()
            if s.is_valid() and s.status in (CookieStatus.FRESH, CookieStatus.COOLDOWN)
        )
        return available < self.max_pool_size * threshold


class CookiePoolManager:
    """
    多域名Cookie池管理器

    统一管理多个网站的Cookie池。
    """

    def __init__(self, storage_path: str = "./data/cookies"):
        self.storage_path = Path(storage_path)
        self.pools: dict[str, CookiePool] = {}

    def get_pool(self, domain: str) -> CookiePool:
        """获取或创建指定域名的Cookie池"""
        if domain not in self.pools:
            self.pools[domain] = CookiePool(domain, str(self.storage_path))
        return self.pools[domain]

    def stats(self) -> dict:
        """获取所有池的统计"""
        return {
            domain: pool.stats()
            for domain, pool in self.pools.items()
        }


# ==================== 基础设施评估器 ====================

class InfrastructureAdvisor:
    """
    基础设施评估器

    根据任务需求，自动评估是否需要Cookie池、代理池等基础设施。
    这就是Agent自主建议用户搭建基础设施的核心逻辑。
    """

    # 需要Cookie池的网站特征
    COOKIE_REQUIRED_INDICATORS = [
        "set-cookie",           # 响应包含set-cookie头
        "__cf_bm",              # Cloudflare
        "JSESSIONID",           # Java session
        "__jda", "__jdb",       # 京东
        "unb", "_m_h5_tk",      # 淘宝
        "_ga", "_gid",          # Google Analytics
        "BAIDUID",              # 百度
    ]

    # 高风控网站列表
    HIGH_RISK_DOMAINS = [
        "jd.com", "taobao.com", "tmall.com",
        "amazon.com", "amazon.cn",
        "meituan.com", "dianping.com",
        "douyin.com", "tiktok.com",
        "weibo.com", "zhihu.com",
    ]

    def __init__(self, cookie_pool_manager: Optional[CookiePoolManager] = None):
        self.pool_manager = cookie_pool_manager or CookiePoolManager()

    def evaluate(
        self,
        url: str,
        task_type: str = "scrape",
        target_count: int = 100,
        analysis_result: Optional[dict] = None,
    ) -> dict:
        """
        评估任务需要的基础设施

        Args:
            url: 目标URL
            task_type: 任务类型 (scrape/api/monitor)
            target_count: 目标数据量
            analysis_result: 网站分析结果（来自Brain.smart_investigate）

        Returns:
            基础设施建议
        """
        from urllib.parse import urlparse

        domain = urlparse(url).netloc.replace("www.", "")

        recommendations = {
            "domain": domain,
            "url": url,
            "cookie_pool": {
                "needed": False,
                "reason": "",
                "suggested_size": 0,
                "current_size": 0,
            },
            "proxy_pool": {
                "needed": False,
                "reason": "",
                "type": "none",  # none/free/residential
            },
            "sign_server": {
                "needed": False,
                "reason": "",
            },
            "priority": [],  # 按优先级排序的建议
            "summary": "",
        }

        # 1. 评估Cookie池需求
        cookie_needed, cookie_reason = self._evaluate_cookie_need(
            domain, target_count, analysis_result
        )
        if cookie_needed:
            pool = self.pool_manager.get_pool(domain)
            current_size = len(pool.sessions)
            suggested_size = self._calculate_pool_size(target_count)

            recommendations["cookie_pool"] = {
                "needed": True,
                "reason": cookie_reason,
                "suggested_size": suggested_size,
                "current_size": current_size,
                "need_generate": max(0, suggested_size - current_size),
            }
            recommendations["priority"].append("cookie_pool")

        # 2. 评估代理池需求
        proxy_needed, proxy_reason, proxy_type = self._evaluate_proxy_need(
            domain, target_count, analysis_result
        )
        if proxy_needed:
            recommendations["proxy_pool"] = {
                "needed": True,
                "reason": proxy_reason,
                "type": proxy_type,
            }
            recommendations["priority"].append("proxy_pool")

        # 3. 评估签名服务需求
        sign_needed, sign_reason = self._evaluate_sign_need(analysis_result)
        if sign_needed:
            recommendations["sign_server"] = {
                "needed": True,
                "reason": sign_reason,
            }
            recommendations["priority"].append("sign_server")

        # 生成摘要
        recommendations["summary"] = self._generate_summary(recommendations)

        return recommendations

    def _evaluate_cookie_need(
        self,
        domain: str,
        target_count: int,
        analysis: Optional[dict],
    ) -> tuple[bool, str]:
        """评估是否需要Cookie池"""
        reasons = []

        # 高风控网站
        if any(d in domain for d in self.HIGH_RISK_DOMAINS):
            reasons.append(f"{domain} 是高风控网站")

        # 大量数据采集
        if target_count > 100:
            reasons.append(f"目标数据量大（{target_count}条），需要会话复用")

        # 分析结果显示需要Cookie
        if analysis:
            anti_level = analysis.get("anti_scrape_level", 0)
            if anti_level >= 3:
                reasons.append(f"反爬等级高（{anti_level}/5）")

            cookies_detected = analysis.get("cookies_detected", [])
            if any(ind in str(cookies_detected) for ind in self.COOKIE_REQUIRED_INDICATORS):
                reasons.append("检测到关键Cookie")

        if reasons:
            return True, "；".join(reasons)
        return False, ""

    def _evaluate_proxy_need(
        self,
        domain: str,
        target_count: int,
        analysis: Optional[dict],
    ) -> tuple[bool, str, str]:
        """评估是否需要代理池"""
        if target_count > 500:
            return True, f"大量请求（{target_count}）需要IP轮换", "residential"

        if any(d in domain for d in self.HIGH_RISK_DOMAINS) and target_count > 100:
            return True, "高风控网站+中等数据量", "residential"

        if analysis:
            if analysis.get("ip_block_risk", False):
                return True, "检测到IP封禁风险", "residential"

        return False, "", "none"

    def _evaluate_sign_need(self, analysis: Optional[dict]) -> tuple[bool, str]:
        """评估是否需要签名服务"""
        if not analysis:
            return False, ""

        signatures = analysis.get("signatures_detected", [])
        if signatures:
            return True, f"检测到签名参数：{', '.join(signatures[:3])}"

        return False, ""

    def _calculate_pool_size(self, target_count: int) -> int:
        """计算建议的Cookie池大小"""
        # 每个Cookie平均可用10次
        base_size = target_count // 10
        # 加上20%冗余
        return max(10, int(base_size * 1.2))

    def _generate_summary(self, recommendations: dict) -> str:
        """生成人类可读的摘要"""
        lines = [f"## 基础设施评估报告 - {recommendations['domain']}\n"]

        if not recommendations["priority"]:
            lines.append("当前任务无需特殊基础设施，可直接执行。")
            return "\n".join(lines)

        lines.append("### 建议配置：\n")

        if recommendations["cookie_pool"]["needed"]:
            cp = recommendations["cookie_pool"]
            lines.append(f"1. **Cookie池**（优先级：高）")
            lines.append(f"   - 原因：{cp['reason']}")
            lines.append(f"   - 当前：{cp['current_size']} 个")
            lines.append(f"   - 建议：{cp['suggested_size']} 个")
            if cp.get("need_generate", 0) > 0:
                lines.append(f"   - 需生成：{cp['need_generate']} 个")
                lines.append(f"   - 命令：`await pool.generate(count={cp['need_generate']})`")
            lines.append("")

        if recommendations["proxy_pool"]["needed"]:
            pp = recommendations["proxy_pool"]
            lines.append(f"2. **代理池**（类型：{pp['type']}）")
            lines.append(f"   - 原因：{pp['reason']}")
            if pp["type"] == "residential":
                lines.append("   - 建议：使用住宅代理服务")
            lines.append("")

        if recommendations["sign_server"]["needed"]:
            ss = recommendations["sign_server"]
            lines.append(f"3. **签名服务**")
            lines.append(f"   - 原因：{ss['reason']}")
            lines.append("")

        return "\n".join(lines)
