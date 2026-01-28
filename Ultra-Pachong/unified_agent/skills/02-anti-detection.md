# 02 - 反检测模块 (Anti-Detection)

---
name: anti-detection
version: 1.0.0
description: 绕过各类网站检测机制
triggers:
  - "反检测"
  - "伪装"
  - "绕过"
  - "stealth"
  - "anti-bot"
dependencies:
  - playwright
  - curl_cffi
---

## 模块目标

**核心原则：给出需求，必须完成。**

| 目标 | 达成标准 |
|------|---------|
| **检测全绕过** | 常见反爬检测点 100% 绕过，无 bot 标记 |
| **指纹全伪装** | TLS/浏览器/设备指纹与真实用户一致 |
| **行为全模拟** | 鼠标/键盘/滚动行为通过行为分析检测 |
| **适配全平台** | Cloudflare/Akamai/PerimeterX 等主流 WAF 可突破 |

## 模块概述

反检测模块负责绕过网站的各类检测机制，是爬虫能否成功的关键。

```
┌─────────────────────────────────────────────────────────────────┐
│                       反检测技术栈                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 5: 行为层 ─────────────────────────────────────────────  │
│  │ 鼠标轨迹 │ 键盘节奏 │ 滚动模式 │ 请求时序 │                   │
│                                                                 │
│  Layer 4: 指纹层 ─────────────────────────────────────────────  │
│  │ Canvas │ WebGL │ Audio │ 字体 │ 屏幕 │                       │
│                                                                 │
│  Layer 3: 浏览器层 ───────────────────────────────────────────  │
│  │ WebDriver │ Chrome对象 │ Plugins │ Permissions │             │
│                                                                 │
│  Layer 2: HTTP层 ─────────────────────────────────────────────  │
│  │ User-Agent │ Headers │ Cookie │ Referer │                    │
│                                                                 │
│  Layer 1: TLS层 ──────────────────────────────────────────────  │
│  │ JA3指纹 │ JA3S指纹 │ HTTP/2指纹 │                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: TLS 层绕过

### JA3 指纹问题

```
问题: Python requests/httpx 的 TLS 指纹与真实浏览器不同
检测: Cloudflare, Akamai 等 CDN 可通过 JA3 指纹识别爬虫
```

### 解决方案

```python
# 方案1: 使用 curl_cffi (推荐)
from curl_cffi import requests

response = requests.get(
    url,
    impersonate="chrome120",  # 模拟 Chrome 120 的 TLS 指纹
)

# 方案2: 使用真实浏览器 (Playwright)
# 自动具有真实的 TLS 指纹
```

### 支持的浏览器指纹

| 指纹名称 | 说明 |
|---------|------|
| `chrome120` | Chrome 120 |
| `chrome119` | Chrome 119 |
| `chrome110` | Chrome 110 |
| `safari17` | Safari 17 |
| `edge120` | Edge 120 |

---

## Layer 2: HTTP 层伪装

### User-Agent 轮换

```python
USER_AGENT_POOL = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",

    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",

    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",

    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",

    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

import random
ua = random.choice(USER_AGENT_POOL)
```

### 完整请求头模拟

```python
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 ...",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}
```

### Referer 链构造

```python
def build_referer_chain(target_url: str) -> list[str]:
    """构造合理的 Referer 链"""
    from urllib.parse import urlparse

    parsed = urlparse(target_url)
    domain = parsed.netloc

    return [
        f"https://www.google.com/search?q={domain}",
        f"https://{domain}/",
        target_url
    ]
```

---

## Layer 3: 浏览器层绕过

### WebDriver 检测绕过

```javascript
// stealth.js - 隐藏 WebDriver 标记

// 1. 删除 webdriver 属性
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// 2. 覆盖 navigator.plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin' },
        { name: 'Chrome PDF Viewer' },
        { name: 'Native Client' }
    ]
});

// 3. 覆盖 navigator.languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en']
});
```

### Chrome 对象注入

```javascript
// 注入 window.chrome 对象
window.chrome = {
    runtime: {
        onConnect: { addListener: () => {} },
        onMessage: { addListener: () => {} }
    },
    loadTimes: () => ({
        requestTime: Date.now() / 1000,
        startLoadTime: Date.now() / 1000,
        commitLoadTime: Date.now() / 1000,
        finishDocumentLoadTime: Date.now() / 1000,
        finishLoadTime: Date.now() / 1000,
    }),
    csi: () => ({
        onloadT: Date.now(),
        startE: Date.now(),
        tran: 15
    }),
};
```

### Permissions API 覆盖

```javascript
// 覆盖权限查询
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
```

---

## Layer 4: 指纹层随机化

### Canvas 指纹

```javascript
// Canvas 噪声注入
const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    if (type === 'image/png') {
        const context = this.getContext('2d');
        const imageData = context.getImageData(0, 0, this.width, this.height);

        // 添加细微噪声
        for (let i = 0; i < imageData.data.length; i += 4) {
            imageData.data[i] += Math.floor(Math.random() * 2);     // R
            imageData.data[i+1] += Math.floor(Math.random() * 2);   // G
            imageData.data[i+2] += Math.floor(Math.random() * 2);   // B
        }

        context.putImageData(imageData, 0, 0);
    }
    return originalToDataURL.apply(this, arguments);
};
```

### WebGL 指纹

```javascript
// WebGL 渲染器伪装
const getParameterProxyHandler = {
    apply: function(target, thisArg, args) {
        const param = args[0];
        const gl = thisArg;

        // UNMASKED_VENDOR_WEBGL
        if (param === 37445) {
            return 'Google Inc. (NVIDIA)';
        }
        // UNMASKED_RENDERER_WEBGL
        if (param === 37446) {
            return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)';
        }

        return target.apply(thisArg, args);
    }
};

// 应用到 WebGL 和 WebGL2
WebGLRenderingContext.prototype.getParameter = new Proxy(
    WebGLRenderingContext.prototype.getParameter,
    getParameterProxyHandler
);
```

### Audio 指纹

```javascript
// AudioContext 指纹随机化
const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
AudioContext.prototype.createAnalyser = function() {
    const analyser = originalCreateAnalyser.apply(this, arguments);

    const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
    analyser.getFloatFrequencyData = function(array) {
        originalGetFloatFrequencyData.apply(this, arguments);
        // 添加噪声
        for (let i = 0; i < array.length; i++) {
            array[i] += Math.random() * 0.0001;
        }
    };

    return analyser;
};
```

---

## Layer 5: 行为层模拟

### 鼠标轨迹模拟

```python
import random
import math

def generate_mouse_path(start: tuple, end: tuple, steps: int = 20) -> list[tuple]:
    """生成贝塞尔曲线鼠标轨迹"""

    # 生成控制点
    ctrl1 = (
        start[0] + (end[0] - start[0]) * random.uniform(0.2, 0.4),
        start[1] + random.uniform(-50, 50)
    )
    ctrl2 = (
        start[0] + (end[0] - start[0]) * random.uniform(0.6, 0.8),
        end[1] + random.uniform(-50, 50)
    )

    # 生成路径点
    path = []
    for i in range(steps + 1):
        t = i / steps

        # 三次贝塞尔曲线
        x = (1-t)**3 * start[0] + 3*(1-t)**2*t * ctrl1[0] + 3*(1-t)*t**2 * ctrl2[0] + t**3 * end[0]
        y = (1-t)**3 * start[1] + 3*(1-t)**2*t * ctrl1[1] + 3*(1-t)*t**2 * ctrl2[1] + t**3 * end[1]

        # 添加微小抖动
        x += random.uniform(-2, 2)
        y += random.uniform(-2, 2)

        path.append((int(x), int(y)))

    return path

# Playwright 中使用
async def human_like_click(page, selector):
    element = await page.query_selector(selector)
    box = await element.bounding_box()

    # 生成轨迹
    start = (random.randint(0, 100), random.randint(0, 100))
    end = (box['x'] + box['width']/2, box['y'] + box['height']/2)
    path = generate_mouse_path(start, end)

    # 执行移动
    for x, y in path:
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.01, 0.03))

    # 点击
    await page.mouse.click(end[0], end[1])
```

### 键盘输入模拟

```python
async def human_like_type(page, selector, text):
    """模拟人类打字"""
    await page.click(selector)

    for char in text:
        # 随机延迟 (模拟打字速度)
        delay = random.uniform(0.05, 0.2)

        # 偶尔打错并纠正
        if random.random() < 0.02:
            wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
            await page.keyboard.type(wrong_char, delay=delay)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            await page.keyboard.press('Backspace')

        await page.keyboard.type(char, delay=delay)
```

### 请求时序人类化

```python
def human_delay() -> float:
    """生成人类化的请求延迟"""

    # 基础延迟 1-3 秒
    base = random.uniform(1.0, 3.0)

    # 10% 概率长停顿 (模拟阅读)
    if random.random() < 0.1:
        base += random.uniform(5.0, 15.0)

    # 5% 概率短暂快速 (模拟熟练操作)
    if random.random() < 0.05:
        base = random.uniform(0.3, 0.8)

    return base
```

---

## 检测点速查表

| 检测项 | 检测方法 | 绕过方案 | 难度 |
|--------|---------|---------|------|
| WebDriver | `navigator.webdriver` | stealth.js 注入 | ⭐ |
| Headless | `navigator.plugins.length` | 伪造 plugins | ⭐ |
| Chrome 对象 | `window.chrome` | 注入 chrome 对象 | ⭐ |
| 自动化框架 | `window.cdc_*` | 清除自动化痕迹 | ⭐⭐ |
| Canvas | `toDataURL()` | 噪声注入 | ⭐⭐ |
| WebGL | `getParameter()` | 伪造渲染器 | ⭐⭐ |
| Audio | `AudioContext` | 指纹随机化 | ⭐⭐ |
| 字体 | CSS font enumeration | 伪造字体列表 | ⭐⭐ |
| TLS | JA3 指纹 | curl_cffi/真实浏览器 | ⭐⭐⭐ |
| 行为 | 鼠标/键盘/时序 | 贝塞尔曲线模拟 | ⭐⭐⭐ |

---

## 配置示例

```python
from unified_agent import AgentConfig

config = AgentConfig(
    # 浏览器配置
    headless=True,

    # User-Agent 随机化
    user_agent=None,  # None = 随机选择

    # 视口随机化
    viewport_width=1920,
    viewport_height=1080,

    # 语言/时区伪装
    locale="zh-CN",
    timezone="Asia/Shanghai",

    # 代理 (隐藏真实IP)
    proxy_enabled=True,
)

brain = Brain(config)
```

---

## 反检测检查清单

使用前检查以下项目：

- [ ] WebDriver 标记已隐藏
- [ ] Chrome 对象已注入
- [ ] Navigator 属性已伪装
- [ ] Canvas 指纹已随机化
- [ ] WebGL 信息已伪造
- [ ] User-Agent 与指纹一致
- [ ] TLS 指纹正确 (使用 curl_cffi)
- [ ] 鼠标行为人类化
- [ ] 请求时序随机化
- [ ] 代理 IP 正常

---

## 诊断日志

```
# 伪装初始化
[STEALTH] 加载反检测配置: stealth_full
[STEALTH] 注入 stealth.js: webdriver=hidden, chrome=injected
[STEALTH] TLS 指纹: chrome120 (curl_cffi)

# 指纹检查
[STEALTH] Canvas 指纹: 已随机化 (噪声注入)
[STEALTH] WebGL 信息: NVIDIA GeForce GTX 1080
[STEALTH] Audio 指纹: 已扰动

# 行为模拟
[STEALTH] 鼠标移动: 贝塞尔曲线 (20 步, 0.5s)
[STEALTH] 键盘输入: 人类化延迟 (50-200ms)
[STEALTH] 请求间隔: 2.3s (人类化随机)

# 检测结果
[STEALTH] 通过检测: WebDriver=OK, Headless=OK, Canvas=OK
[STEALTH] 风险评估: low (得分: 3/25)

# 警告与错误
[STEALTH] WARN: 检测到 Cloudflare 5秒盾
[STEALTH] WARN: 触发验证码，需要人工处理
[STEALTH] ERROR: TLS 指纹被识别，切换浏览器方案
[STEALTH] BLOCK: 行为分析失败，参考 16-tactics 切换策略
```

---

## 相关模块

- **上游**: [01-侦查模块](01-reconnaissance.md) - 分析检测点
- **下游**: [03-签名模块](03-signature.md) - 签名生成
- **配合**: [04-请求模块](04-request.md) - 发送请求
- **配合**: [16-战术模块](16-tactics.md) - 检测被拦截时切换策略
