"""
恢复模块 - 动作处理器

实现具体的恢复动作。
"""

import time
import random
import logging
from typing import Any, Callable, Dict, Optional

from .types import RecoveryAction

logger = logging.getLogger(__name__)


class ActionHandler:
    """
    恢复动作处理器

    支持依赖注入，可连接到实际系统组件。

    使用示例:
        handler = ActionHandler()
        handler.set_proxy_manager(proxy_manager)
        handler.set_config(config)

        success = handler.execute(RecoveryAction.SWITCH_PROXY, context)
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
    ]

    def __init__(self):
        """初始化"""
        # 外部依赖
        self.proxy_manager = None
        self.config = None
        self.browser_context = None
        self.rate_limiter = None
        self.cookie_pool = None

        # 状态
        self._rate_factor = 1.0
        self._timeout_factor = 1.0

        # 动作映射
        self._handlers: Dict[RecoveryAction, Callable] = {
            RecoveryAction.RETRY: self._action_retry,
            RecoveryAction.SWITCH_PROXY: self._action_switch_proxy,
            RecoveryAction.WAIT_COOLDOWN: self._action_wait_cooldown,
            RecoveryAction.REDUCE_RATE: self._action_reduce_rate,
            RecoveryAction.INCREASE_TIMEOUT: self._action_increase_timeout,
            RecoveryAction.RESTART_BROWSER: self._action_restart_browser,
            RecoveryAction.CHANGE_USER_AGENT: self._action_change_user_agent,
            RecoveryAction.ROTATE_COOKIE: self._action_rotate_cookie,
            RecoveryAction.CLEAR_CACHE: self._action_clear_cache,
            RecoveryAction.ESCALATE_TO_USER: self._action_escalate_to_user,
            RecoveryAction.WAIT_PAGE_LOAD: self._action_wait_page_load,
            RecoveryAction.USE_BACKUP_SELECTOR: self._action_use_backup_selector,
        }

    # ==================== 依赖注入 ====================

    def set_proxy_manager(self, proxy_manager: Any):
        self.proxy_manager = proxy_manager

    def set_config(self, config: Any):
        self.config = config

    def set_browser_context(self, browser_context: Any):
        self.browser_context = browser_context

    def set_rate_limiter(self, rate_limiter: Any):
        self.rate_limiter = rate_limiter

    def set_cookie_pool(self, cookie_pool: Any):
        self.cookie_pool = cookie_pool

    # ==================== 执行入口 ====================

    def execute(
        self,
        action: RecoveryAction,
        context: Dict[str, Any]
    ) -> bool:
        """
        执行恢复动作

        Args:
            action: 恢复动作
            context: 上下文信息

        Returns:
            是否成功
        """
        handler = self._handlers.get(action)
        if handler:
            try:
                logger.info(f"[ActionHandler] 执行: {action.value}")
                return handler(context)
            except Exception as e:
                logger.error(f"[ActionHandler] 执行失败: {action.value} - {e}")
                return False
        else:
            logger.warning(f"[ActionHandler] 未实现: {action.value}")
            return False

    # ==================== 动作实现 ====================

    def _action_retry(self, context: Dict) -> bool:
        """重试"""
        delay = context.get("retry_delay", 3)
        logger.info(f"[ActionHandler] 等待 {delay}s 后重试")
        time.sleep(delay)
        return True

    def _action_switch_proxy(self, context: Dict) -> bool:
        """切换代理"""
        # 使用代理管理器
        if self.proxy_manager:
            for method in ("rotate", "get_next", "switch"):
                if hasattr(self.proxy_manager, method):
                    try:
                        new_proxy = getattr(self.proxy_manager, method)()
                        context["new_proxy"] = new_proxy
                        logger.info(f"[ActionHandler] 代理切换: {new_proxy}")
                        return True
                    except Exception as e:
                        logger.error(f"[ActionHandler] 代理切换失败: {e}")

        # 使用配置
        if self.config and hasattr(self.config, "proxy_list"):
            proxy_list = self.config.proxy_list
            if proxy_list:
                idx = getattr(self.config, "_proxy_idx", 0)
                idx = (idx + 1) % len(proxy_list)
                self.config._proxy_idx = idx
                context["new_proxy"] = proxy_list[idx]
                logger.info(f"[ActionHandler] 代理轮换: {proxy_list[idx]}")
                return True

        # 通过回调
        callback = context.get("switch_proxy_callback")
        if callback and callable(callback):
            try:
                context["new_proxy"] = callback()
                return True
            except Exception as e:
                logger.error(f"[ActionHandler] 代理回调失败: {e}")

        logger.warning("[ActionHandler] 无可用代理切换方式")
        return False

    def _action_wait_cooldown(self, context: Dict) -> bool:
        """等待冷却"""
        cooldown = context.get("cooldown_seconds", 30)
        max_wait = context.get("max_cooldown", 60)
        actual = min(cooldown, max_wait)
        logger.info(f"[ActionHandler] 等待冷却 {actual}s")
        time.sleep(actual)
        return True

    def _action_reduce_rate(self, context: Dict) -> bool:
        """降低速率"""
        factor = context.get("reduction_factor", 0.5)

        if self.rate_limiter:
            if hasattr(self.rate_limiter, "set_rate"):
                current = getattr(self.rate_limiter, "rate", 1.0)
                new_rate = max(0.1, current * factor)
                self.rate_limiter.set_rate(new_rate)
                logger.info(f"[ActionHandler] 速率: {current} -> {new_rate}")
                return True

        if self.config and hasattr(self.config, "requests_per_second"):
            old = self.config.requests_per_second
            self.config.requests_per_second = max(0.1, old * factor)
            logger.info(f"[ActionHandler] 配置速率: {old} -> {self.config.requests_per_second}")
            return True

        self._rate_factor *= factor
        context["rate_factor"] = self._rate_factor
        logger.info(f"[ActionHandler] 速率因子: {self._rate_factor}")
        return True

    def _action_increase_timeout(self, context: Dict) -> bool:
        """增加超时"""
        factor = context.get("timeout_factor", 1.5)
        max_timeout = 120

        if self.config:
            for attr in ("timeout", "request_timeout"):
                if hasattr(self.config, attr):
                    old = getattr(self.config, attr)
                    new = min(old * factor, max_timeout)
                    setattr(self.config, attr, new)
                    logger.info(f"[ActionHandler] 超时: {old} -> {new}s")
                    return True

        self._timeout_factor *= factor
        context["timeout_factor"] = self._timeout_factor
        logger.info(f"[ActionHandler] 超时因子: {self._timeout_factor}")
        return True

    def _action_restart_browser(self, context: Dict) -> bool:
        """重启浏览器"""
        if self.browser_context:
            try:
                browser = getattr(self.browser_context, "browser", None)
                if hasattr(self.browser_context, "close"):
                    self.browser_context.close()
                if browser and hasattr(browser, "new_context"):
                    self.browser_context = browser.new_context()
                    logger.info("[ActionHandler] 浏览器已重启")
                    return True
            except Exception as e:
                logger.error(f"[ActionHandler] 浏览器重启失败: {e}")

        callback = context.get("restart_browser_callback")
        if callback and callable(callback):
            try:
                callback()
                return True
            except Exception as e:
                logger.error(f"[ActionHandler] 浏览器回调失败: {e}")

        context["need_restart_browser"] = True
        return True

    def _action_change_user_agent(self, context: Dict) -> bool:
        """更换UA"""
        new_ua = random.choice(self.USER_AGENTS)

        if self.config and hasattr(self.config, "user_agent"):
            self.config.user_agent = new_ua
            logger.info(f"[ActionHandler] UA: {new_ua[:50]}...")
            return True

        context["new_user_agent"] = new_ua
        return True

    def _action_rotate_cookie(self, context: Dict) -> bool:
        """轮换Cookie"""
        if self.cookie_pool:
            for method in ("get_fresh", "rotate"):
                if hasattr(self.cookie_pool, method):
                    try:
                        new_cookie = getattr(self.cookie_pool, method)()
                        context["new_cookie"] = new_cookie
                        logger.info("[ActionHandler] Cookie已轮换")
                        return True
                    except Exception as e:
                        logger.error(f"[ActionHandler] Cookie轮换失败: {e}")

        callback = context.get("get_cookie_callback")
        if callback and callable(callback):
            try:
                context["new_cookie"] = callback()
                return True
            except Exception:
                pass

        return False

    def _action_clear_cache(self, context: Dict) -> bool:
        """清理缓存"""
        if self.browser_context and hasattr(self.browser_context, "clear_cookies"):
            try:
                self.browser_context.clear_cookies()
                logger.info("[ActionHandler] 缓存已清理")
                return True
            except Exception as e:
                logger.error(f"[ActionHandler] 缓存清理失败: {e}")

        return True

    def _action_escalate_to_user(self, context: Dict) -> bool:
        """升级到用户"""
        logger.warning("[ActionHandler] 需要用户介入")
        callback = context.get("notify_user_callback")
        if callback and callable(callback):
            try:
                callback(context.get("error_message", "需要人工处理"))
            except Exception:
                pass
        return False

    def _action_wait_page_load(self, context: Dict) -> bool:
        """等待页面加载"""
        wait = context.get("page_load_wait", 5)
        logger.info(f"[ActionHandler] 等待页面加载 {wait}s")
        time.sleep(wait)
        return True

    def _action_use_backup_selector(self, context: Dict) -> bool:
        """使用备用选择器"""
        backup = context.get("backup_selectors", {})
        if backup:
            context["use_selectors"] = backup
            logger.info(f"[ActionHandler] 使用备用选择器: {list(backup.keys())}")
            return True
        return False

    # ==================== 状态管理 ====================

    def get_stats(self) -> Dict[str, Any]:
        return {
            "rate_factor": self._rate_factor,
            "timeout_factor": self._timeout_factor,
        }

    def reset(self):
        self._rate_factor = 1.0
        self._timeout_factor = 1.0
