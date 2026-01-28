"""
反检测模块

整合 playwright-stealth 和自定义反检测脚本，用于绕过网站的爬虫检测。

支持:
- WebDriver 标记隐藏
- Canvas/Audio/ClientRects 指纹随机化
- WebGL 伪装
- 自动化痕迹清理
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

# 尝试导入 playwright-stealth
try:
    from playwright_stealth import stealth_async
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False


async def apply_stealth(page: Page, locale: str = "zh-CN") -> None:
    """
    应用全套反检测措施 (异步)

    Args:
        page: Playwright 页面对象
        locale: 语言环境
    """
    # 1. 使用 playwright-stealth (如果可用)
    if HAS_STEALTH:
        await stealth_async(page)

    # 2. 注入额外的反检测脚本
    # 为了增强反检测能力，启用额外的反检测脚本
    await page.add_init_script(EXTRA_STEALTH_JS)


# 额外的反检测 JavaScript (整合自原项目的 analyzer.py)
EXTRA_STEALTH_JS = r"""
() => {
    // ========== 1. iframe contentWindow 代理 ==========
    try {
        const addContentWindowProxy = (iframe) => {
            const contentWindowProxy = {
                get(target, key) {
                    if (key === 'self' || key === 'window') return iframe.contentWindow;
                    if (key === 'chrome') return window.chrome;
                    const val = target[key];
                    if (typeof val === 'function') return val.bind(target);
                    return val;
                }
            };
            if (!iframe.contentWindow) return;
            const proxy = new Proxy(iframe.contentWindow, contentWindowProxy);
            Object.defineProperty(iframe, 'contentWindow', {
                get: () => proxy,
                configurable: true
            });
        };

        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (node.tagName === 'IFRAME') addContentWindowProxy(node);
                }
            }
        });
        observer.observe(document.documentElement, { childList: true, subtree: true });
        document.querySelectorAll('iframe').forEach(addContentWindowProxy);
    } catch (e) {}

    // ========== 2. 媒体编解码器支持 ==========
    try {
        const originalCanPlayType = HTMLMediaElement.prototype.canPlayType;
        HTMLMediaElement.prototype.canPlayType = function(type) {
            const normalizedType = type.replace(/\s/g, '').toLowerCase();
            if (normalizedType.includes('webm') || normalizedType.includes('vp8') ||
                normalizedType.includes('vp9') || normalizedType.includes('opus')) return 'probably';
            if (normalizedType.includes('mp4') || normalizedType.includes('avc1') ||
                normalizedType.includes('h264') || normalizedType.includes('aac')) return 'probably';
            return originalCanPlayType.call(this, type);
        };
    } catch (e) {}

    // ========== 3. window.outerWidth/outerHeight ==========
    try {
        if (window.outerWidth === 0) {
            Object.defineProperty(window, 'outerWidth', { get: () => window.innerWidth });
        }
        if (window.outerHeight === 0) {
            Object.defineProperty(window, 'outerHeight', { get: () => window.innerHeight + 85 });
        }
    } catch (e) {}

    // ========== 4. WebGL2 伪装 ==========
    try {
        const getParameterProxyHandler = {
            apply(target, thisArg, args) {
                const param = args[0];
                if (param === 37445) return 'Intel Inc.';
                if (param === 37446) return 'Intel Iris OpenGL Engine';
                return Reflect.apply(target, thisArg, args);
            }
        };
        if (WebGLRenderingContext.prototype.getParameter) {
            WebGLRenderingContext.prototype.getParameter = new Proxy(
                WebGLRenderingContext.prototype.getParameter, getParameterProxyHandler
            );
        }
        if (typeof WebGL2RenderingContext !== 'undefined' && WebGL2RenderingContext.prototype.getParameter) {
            WebGL2RenderingContext.prototype.getParameter = new Proxy(
                WebGL2RenderingContext.prototype.getParameter, getParameterProxyHandler
            );
        }
    } catch (e) {}

    // ========== 5. 电池 API 伪装 ==========
    try {
        if (navigator.getBattery) {
            navigator.getBattery = async () => ({
                charging: true, chargingTime: 0, dischargingTime: Infinity, level: 1,
                addEventListener: () => {}, removeEventListener: () => {}
            });
        }
    } catch (e) {}

    // ========== 6. 清理自动化痕迹 ==========
    try {
        const automationProps = [
            '__playwright', '__puppeteer', '__selenium', '__webdriver',
            '__driver_evaluate', '__webdriver_evaluate', '__selenium_evaluate',
            '__fxdriver_evaluate', '__driver_unwrapped', '__webdriver_unwrapped',
            '__selenium_unwrapped', '__fxdriver_unwrapped', '_Selenium_IDE_Recorder',
            'calledSelenium', '_selenium', 'domAutomation', 'domAutomationController'
        ];
        automationProps.forEach(prop => { try { delete window[prop]; } catch (e) {} });

        const docProps = ['$cdc_asdjflasutopfhvcZLmcfl_', '$wdc_', '$chrome_asyncScriptInfo'];
        docProps.forEach(prop => { try { delete document[prop]; } catch (e) {} });
    } catch (e) {}

    // ========== 7. 防止 toString 检测 ==========
    try {
        const originalToString = Function.prototype.toString;
        const customToString = function() {
            if (this === customToString) return 'function toString() { [native code] }';
            return originalToString.call(this);
        };
        Object.defineProperty(Function.prototype, 'toString', {
            value: customToString, writable: true, configurable: true
        });
    } catch (e) {}

    // ========== 8. Connection RTT 伪装 ==========
    try {
        if (navigator.connection) {
            Object.defineProperty(navigator.connection, 'rtt', { get: () => 100, configurable: true });
        }
    } catch (e) {}

    // ========== 9. Canvas 指纹随机化 ==========
    try {
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            if (this.width === 0 || this.height === 0) return originalToDataURL.apply(this, arguments);
            const ctx = this.getContext('2d');
            if (ctx) {
                const imageData = ctx.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] ^= (Math.random() * 2) | 0;
                }
                ctx.putImageData(imageData, 0, 0);
            }
            return originalToDataURL.apply(this, arguments);
        };
    } catch (e) {}

    // ========== 10. AudioContext 指纹随机化 ==========
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
            const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
            AudioContext.prototype.createAnalyser = function() {
                const analyser = originalCreateAnalyser.call(this);
                const originalGetFloatFrequencyData = analyser.getFloatFrequencyData.bind(analyser);
                analyser.getFloatFrequencyData = function(array) {
                    originalGetFloatFrequencyData(array);
                    for (let i = 0; i < array.length; i++) array[i] += (Math.random() - 0.5) * 0.1;
                };
                return analyser;
            };
        }
    } catch (e) {}

    // ========== 11. ClientRects 指纹随机化 ==========
    try {
        const noise = () => (Math.random() - 0.5) * 0.01;
        const originalGetClientRects = Element.prototype.getClientRects;
        Element.prototype.getClientRects = function() {
            const rects = originalGetClientRects.call(this);
            if (rects.length === 0) return rects;
            const newRects = [];
            for (let i = 0; i < rects.length; i++) {
                newRects.push({
                    ...rects[i],
                    x: rects[i].x + noise(), y: rects[i].y + noise(),
                    width: rects[i].width + noise(), height: rects[i].height + noise(),
                    top: rects[i].top + noise(), right: rects[i].right + noise(),
                    bottom: rects[i].bottom + noise(), left: rects[i].left + noise()
                });
            }
            return newRects;
        };

        const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
        Element.prototype.getBoundingClientRect = function() {
            const rect = originalGetBoundingClientRect.call(this);
            return {
                ...rect, x: rect.x + noise(), y: rect.y + noise(),
                width: rect.width + noise(), height: rect.height + noise(),
                top: rect.top + noise(), right: rect.right + noise(),
                bottom: rect.bottom + noise(), left: rect.left + noise()
            };
        };
    } catch (e) {}

    // ========== 12. 设备属性伪装 ==========
    try {
        Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0, configurable: true });
        Object.defineProperty(navigator, 'deviceMemory', { get: () => 8, configurable: true });

        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format', length: 1 },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '', length: 1 },
                    { name: 'Native Client', filename: 'internal-nacl-plugin', description: '', length: 2 }
                ];
                plugins.item = (i) => plugins[i];
                plugins.namedItem = (name) => plugins.find(p => p.name === name);
                plugins.refresh = () => {};
                Object.setPrototypeOf(plugins, PluginArray.prototype);
                return plugins;
            },
            configurable: true
        });

        Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
        Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
    } catch (e) {}

    // ========== 13. Performance API 伪装 ==========
    try {
        const originalNow = performance.now;
        performance.now = function() {
            return Math.floor(originalNow.call(performance) * 10) / 10;
        };

        if (performance.memory) {
            Object.defineProperty(performance, 'memory', {
                get: () => ({
                    jsHeapSizeLimit: 2172649472,
                    totalJSHeapSize: 19330842,
                    usedJSHeapSize: 17403494
                })
            });
        }
    } catch (e) {}
}
"""
