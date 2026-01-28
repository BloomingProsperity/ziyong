"""
诊断模块 - 自动修复器

负责执行自动修复动作。
"""

import time
import random
import logging
from typing import Any, Callable, Dict, List, Optional

from .types import DiagnosisResult

logger = logging.getLogger(__name__)


class AutoFixer:
    """
    自动修复器

    支持依赖注入，可连接到实际系统组件：
    - proxy_manager: 代理管理器
    - cookie_pool: Cookie池
    - config: 配置对象
    - rate_limiter: 速率限制器

    使用示例:
        fixer = AutoFixer()
        fixer.set_proxy_manager(proxy_manager)
        fixer.set_cookie_pool(cookie_pool)

        result = fixer.fix(diagnosis, context)
    """

    # 常用User-Agent列表
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0",
    ]

    def __init__(self):
        """初始化自动修复器"""
        self.fixers: Dict[str, Callable] = {}
        self.fix_history: List[Dict] = []

        # 外部依赖（通过setter注入）
        self.proxy_manager = None
        self.cookie_pool = None
        self.config = None
        self.rate_limiter = None

        # 状态
        self._rate_factor = 1.0
        self._timeout_factor = 1.0
        self._delay_seconds = 0

        self._register_builtin_fixers()
        logger.info(f"[AutoFixer] 初始化完成，注册 {len(self.fixers)} 个修复器")

    def _register_builtin_fixers(self):
        """注册内置修复器"""
        self.fixers = {
            "retry": self._fix_retry,
            "rotate_ua": self._fix_rotate_ua,
            "refresh_cookie": self._fix_refresh_cookie,
            "reduce_speed": self._fix_reduce_speed,
            "add_delay": self._fix_add_delay,
            "increase_timeout": self._fix_increase_timeout,
            "change_proxy": self._fix_change_proxy,
            "increase_wait": self._fix_increase_wait,
            "regenerate_sign": self._fix_regenerate_sign,
            "restart_browser": self._fix_restart_browser,
            "clear_cache": self._fix_clear_cache,
            "use_backup_selector": self._fix_use_backup_selector,
        }

    # ==================== 依赖注入 ====================

    def set_proxy_manager(self, proxy_manager: Any):
        """设置代理管理器"""
        self.proxy_manager = proxy_manager
        logger.info("[AutoFixer] 代理管理器已设置")

    def set_cookie_pool(self, cookie_pool: Any):
        """设置Cookie池"""
        self.cookie_pool = cookie_pool
        logger.info("[AutoFixer] Cookie池已设置")

    def set_config(self, config: Any):
        """设置配置对象"""
        self.config = config
        logger.info("[AutoFixer] 配置对象已设置")

    def set_rate_limiter(self, rate_limiter: Any):
        """设置速率限制器"""
        self.rate_limiter = rate_limiter
        logger.info("[AutoFixer] 速率限制器已设置")

    def register_fixer(self, action: str, fixer: Callable):
        """注册自定义修复器"""
        self.fixers[action] = fixer
        logger.info(f"[AutoFixer] 注册修复器: {action}")

    # ==================== 主入口 ====================

    def fix(
        self,
        diagnosis: DiagnosisResult,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        尝试自动修复

        Args:
            diagnosis: 诊断结果
            context: 上下文信息

        Returns:
            是否修复成功
        """
        if not diagnosis.auto_fixable:
            logger.info("[AutoFixer] 该错误不可自动修复")
            return False

        context = context or {}
        action = diagnosis.recommended_solution.action

        fixer = self.fixers.get(action)
        if not fixer:
            logger.warning(f"[AutoFixer] 未找到修复器: {action}")
            return False

        try:
            logger.info(f"[AutoFixer] 执行修复: {action}")
            start_time = time.time()

            result = fixer(context)

            elapsed = (time.time() - start_time) * 1000
            self.fix_history.append({
                "action": action,
                "success": result,
                "elapsed_ms": elapsed,
                "timestamp": time.time(),
            })

            logger.info(f"[AutoFixer] 修复{'成功' if result else '失败'}: {action} ({elapsed:.1f}ms)")
            return result

        except Exception as e:
            logger.error(f"[AutoFixer] 修复异常: {action} - {e}")
            return False

    # ==================== 内置修复器 ====================

    def _fix_retry(self, context: Dict) -> bool:
        """修复：重试"""
        delay = context.get("retry_delay", 2)
        logger.info(f"[AutoFixer] 等待 {delay}s 后重试...")
        time.sleep(delay)
        return True

    def _fix_rotate_ua(self, context: Dict) -> bool:
        """修复：更换User-Agent"""
        new_ua = random.choice(self.USER_AGENTS)

        # 方式1: 更新配置
        if self.config and hasattr(self.config, "user_agent"):
            self.config.user_agent = new_ua
            logger.info(f"[AutoFixer] UA已更新: {new_ua[:50]}...")
            return True

        # 方式2: 通过context传出
        context["new_user_agent"] = new_ua
        logger.info(f"[AutoFixer] 新UA已设置到context: {new_ua[:50]}...")
        return True

    def _fix_refresh_cookie(self, context: Dict) -> bool:
        """修复：刷新Cookie"""
        # 方式1: 使用Cookie池
        if self.cookie_pool is not None:
            try:
                if hasattr(self.cookie_pool, "get_fresh"):
                    new_cookie = self.cookie_pool.get_fresh()
                    context["new_cookie"] = new_cookie
                    logger.info("[AutoFixer] 从Cookie池获取新Cookie")
                    return True
                elif hasattr(self.cookie_pool, "rotate"):
                    new_cookie = self.cookie_pool.rotate()
                    context["new_cookie"] = new_cookie
                    logger.info("[AutoFixer] Cookie已轮换")
                    return True
            except Exception as e:
                logger.error(f"[AutoFixer] Cookie刷新失败: {e}")

        # 方式2: 通过回调
        callback = context.get("refresh_cookie_callback")
        if callback and callable(callback):
            try:
                new_cookie = callback()
                context["new_cookie"] = new_cookie
                logger.info("[AutoFixer] 通过回调刷新Cookie")
                return True
            except Exception as e:
                logger.error(f"[AutoFixer] Cookie回调失败: {e}")

        logger.warning("[AutoFixer] 无可用的Cookie刷新方式")
        return False

    def _fix_reduce_speed(self, context: Dict) -> bool:
        """修复：降低请求频率"""
        factor = context.get("reduction_factor", 0.5)

        # 方式1: 使用速率限制器
        if self.rate_limiter is not None:
            try:
                if hasattr(self.rate_limiter, "set_rate"):
                    current = getattr(self.rate_limiter, "rate", 1.0)
                    new_rate = max(0.1, current * factor)
                    self.rate_limiter.set_rate(new_rate)
                    logger.info(f"[AutoFixer] 速率降低: {current} -> {new_rate}")
                    return True
                elif hasattr(self.rate_limiter, "reduce"):
                    self.rate_limiter.reduce(factor)
                    logger.info(f"[AutoFixer] 速率降低 {factor * 100}%")
                    return True
            except Exception as e:
                logger.error(f"[AutoFixer] 速率调整失败: {e}")

        # 方式2: 更新配置
        if self.config is not None:
            if hasattr(self.config, "requests_per_second"):
                old = self.config.requests_per_second
                self.config.requests_per_second = max(0.1, old * factor)
                logger.info(f"[AutoFixer] 配置速率: {old} -> {self.config.requests_per_second}")
                return True

        # 方式3: 记录因子
        self._rate_factor *= factor
        context["rate_factor"] = self._rate_factor
        logger.info(f"[AutoFixer] 速率因子记录: {self._rate_factor}")
        return True

    def _fix_add_delay(self, context: Dict) -> bool:
        """修复：增加请求间隔"""
        add_seconds = context.get("add_delay_seconds", 2)
        self._delay_seconds += add_seconds

        if self.config and hasattr(self.config, "delay_between_requests"):
            self.config.delay_between_requests += add_seconds
            logger.info(f"[AutoFixer] 延迟增加到: {self.config.delay_between_requests}s")
        else:
            context["extra_delay"] = self._delay_seconds
            logger.info(f"[AutoFixer] 额外延迟: {self._delay_seconds}s")

        return True

    def _fix_increase_timeout(self, context: Dict) -> bool:
        """修复：增加超时时间"""
        factor = context.get("timeout_factor", 1.5)
        max_timeout = context.get("max_timeout", 120)

        if self.config is not None:
            for attr in ("timeout", "request_timeout"):
                if hasattr(self.config, attr):
                    old = getattr(self.config, attr)
                    new = min(old * factor, max_timeout)
                    setattr(self.config, attr, new)
                    logger.info(f"[AutoFixer] 超时: {old} -> {new}s")
                    return True

        self._timeout_factor *= factor
        context["timeout_factor"] = self._timeout_factor
        logger.info(f"[AutoFixer] 超时因子: {self._timeout_factor}")
        return True

    def _fix_change_proxy(self, context: Dict) -> bool:
        """修复：切换代理"""
        # 方式1: 使用代理管理器
        if self.proxy_manager is not None:
            try:
                for method in ("rotate", "get_next", "switch"):
                    if hasattr(self.proxy_manager, method):
                        new_proxy = getattr(self.proxy_manager, method)()
                        context["new_proxy"] = new_proxy
                        logger.info(f"[AutoFixer] 代理已切换: {new_proxy}")
                        return True
            except Exception as e:
                logger.error(f"[AutoFixer] 代理切换失败: {e}")

        # 方式2: 从配置轮换
        if self.config and hasattr(self.config, "proxy_list"):
            proxy_list = self.config.proxy_list
            if proxy_list:
                idx = getattr(self.config, "_proxy_idx", 0)
                idx = (idx + 1) % len(proxy_list)
                self.config._proxy_idx = idx
                new_proxy = proxy_list[idx]
                context["new_proxy"] = new_proxy
                if hasattr(self.config, "proxy_url"):
                    self.config.proxy_url = new_proxy
                logger.info(f"[AutoFixer] 代理轮换至: {new_proxy}")
                return True

        # 方式3: 通过回调
        callback = context.get("switch_proxy_callback")
        if callback and callable(callback):
            try:
                new_proxy = callback()
                context["new_proxy"] = new_proxy
                logger.info("[AutoFixer] 通过回调切换代理")
                return True
            except Exception as e:
                logger.error(f"[AutoFixer] 代理回调失败: {e}")

        logger.warning("[AutoFixer] 无可用的代理切换方式")
        return False

    def _fix_increase_wait(self, context: Dict) -> bool:
        """修复：增加等待时间"""
        wait_seconds = context.get("wait_seconds", 5)
        logger.info(f"[AutoFixer] 等待 {wait_seconds}s...")
        time.sleep(wait_seconds)
        return True

    def _fix_regenerate_sign(self, context: Dict) -> bool:
        """修复：重新生成签名"""
        # 通过回调
        callback = context.get("regenerate_sign_callback")
        if callback and callable(callback):
            try:
                params = context.get("sign_params", {})
                new_sign = callback(params)
                context["new_signature"] = new_sign
                logger.info("[AutoFixer] 签名已重新生成")
                return True
            except Exception as e:
                logger.error(f"[AutoFixer] 签名生成失败: {e}")
                return False

        # 标记需要重新签名
        context["need_resign"] = True
        logger.info("[AutoFixer] 已标记需要重新签名")
        return True

    def _fix_restart_browser(self, context: Dict) -> bool:
        """修复：重启浏览器"""
        callback = context.get("restart_browser_callback")
        if callback and callable(callback):
            try:
                callback()
                logger.info("[AutoFixer] 浏览器已重启")
                return True
            except Exception as e:
                logger.error(f"[AutoFixer] 浏览器重启失败: {e}")
                return False

        context["need_restart_browser"] = True
        logger.info("[AutoFixer] 已标记需要重启浏览器")
        return True

    def _fix_clear_cache(self, context: Dict) -> bool:
        """修复：清理缓存"""
        callback = context.get("clear_cache_callback")
        if callback and callable(callback):
            try:
                callback()
                logger.info("[AutoFixer] 缓存已清理")
                return True
            except Exception as e:
                logger.error(f"[AutoFixer] 缓存清理失败: {e}")

        context["need_clear_cache"] = True
        logger.info("[AutoFixer] 已标记需要清理缓存")
        return True

    def _fix_use_backup_selector(self, context: Dict) -> bool:
        """修复：使用备用选择器"""
        backup_selectors = context.get("backup_selectors", {})
        if backup_selectors:
            context["use_selectors"] = backup_selectors
            logger.info(f"[AutoFixer] 使用备用选择器: {list(backup_selectors.keys())}")
            return True

        logger.warning("[AutoFixer] 无备用选择器")
        return False

    # ==================== 状态管理 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取修复统计"""
        success_count = sum(1 for h in self.fix_history if h["success"])
        return {
            "total_fixes": len(self.fix_history),
            "success_count": success_count,
            "success_rate": success_count / len(self.fix_history) if self.fix_history else 0,
            "rate_factor": self._rate_factor,
            "timeout_factor": self._timeout_factor,
            "delay_seconds": self._delay_seconds,
        }

    def reset(self):
        """重置状态"""
        self._rate_factor = 1.0
        self._timeout_factor = 1.0
        self._delay_seconds = 0
        logger.info("[AutoFixer] 状态已重置")
