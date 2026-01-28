# 11 - 指纹工厂模块 (Fingerprint Factory)

---
name: fingerprint-factory
version: 1.0.0
description: 浏览器指纹生成、管理与一致性维护
triggers:
  - "指纹"
  - "fingerprint"
  - "浏览器特征"
  - "设备模拟"
  - "browser profile"
difficulty: ⭐⭐⭐⭐⭐
---

## 模块目标

**核心原则：给出需求，必须完成。**

| 目标 | 达成标准 |
|------|---------|
| **指纹一致性** | 同一身份多次请求指纹 100% 一致，无矛盾特征 |
| **真实性达标** | 生成的指纹通过 CreepJS/Pixelscan 等检测网站 |
| **组件全覆盖** | Navigator/Screen/WebGL/Canvas/Audio/Font/TLS 全部可控 |
| **档案可持久** | 指纹档案可存储、加载、复用，支持批量管理 |
| **注入可靠** | Playwright/Selenium 注入成功率 100% |

---

## 模块概述

指纹工厂负责生成、管理和维护一致性的浏览器指纹，确保每个虚拟身份在多次请求中保持特征一致，避免被检测为机器人。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           指纹工厂架构                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         指纹生成器 (Generator)                       │  │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│   │  │ Navigator│ │  Screen  │ │  WebGL   │ │  Canvas  │ │  Audio   │  │  │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│   │  │  Fonts   │ │ Plugins  │ │   TLS    │ │  HTTP/2  │ │ Timezone │  │  │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         指纹档案 (Profile)                           │  │
│   │           完整的虚拟身份，所有特征保持内部一致性                        │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                    ┌───────────────┼───────────────┐                        │
│                    ▼               ▼               ▼                        │
│              ┌──────────┐   ┌──────────┐   ┌──────────┐                    │
│              │  持久化   │   │  注入器   │   │  验证器   │                    │
│              │ Storage  │   │ Injector │   │ Validator│                    │
│              └──────────┘   └──────────┘   └──────────┘                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 指纹组成要素

### 完整指纹结构

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import hashlib
import json


class Platform(Enum):
    WINDOWS = "Win32"
    MACOS = "MacIntel"
    LINUX = "Linux x86_64"
    ANDROID = "Linux armv8l"
    IOS = "iPhone"


class Browser(Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"


@dataclass
class NavigatorFingerprint:
    """Navigator 对象指纹"""

    # 基础属性
    user_agent: str
    platform: str
    vendor: str
    vendor_sub: str
    product: str
    product_sub: str
    app_name: str
    app_code_name: str
    app_version: str

    # 语言
    language: str
    languages: List[str]

    # 硬件
    hardware_concurrency: int  # CPU 核心数
    device_memory: int  # 内存 GB
    max_touch_points: int

    # 特性检测
    cookie_enabled: bool = True
    do_not_track: Optional[str] = None
    pdf_viewer_enabled: bool = True
    webdriver: bool = False  # 关键！必须为 False


@dataclass
class ScreenFingerprint:
    """屏幕指纹"""

    width: int
    height: int
    avail_width: int
    avail_height: int
    color_depth: int
    pixel_depth: int
    device_pixel_ratio: float

    # 屏幕方向
    orientation_type: str = "landscape-primary"
    orientation_angle: int = 0


@dataclass
class WebGLFingerprint:
    """WebGL 指纹"""

    vendor: str
    renderer: str

    # WebGL 参数
    max_texture_size: int
    max_vertex_attribs: int
    max_vertex_uniform_vectors: int
    max_varying_vectors: int
    max_fragment_uniform_vectors: int
    max_vertex_texture_image_units: int
    max_texture_image_units: int
    max_combined_texture_image_units: int
    max_cube_map_texture_size: int
    max_render_buffer_size: int
    max_viewport_dims: Tuple[int, int]

    # 扩展
    extensions: List[str] = field(default_factory=list)

    # 着色器精度
    shader_precision: Dict = field(default_factory=dict)


@dataclass
class CanvasFingerprint:
    """Canvas 指纹"""

    # 预生成的 Canvas 数据
    canvas_hash: str  # Canvas 绘制结果的哈希

    # 噪声参数（用于生成一致的噪声）
    noise_seed: int
    noise_amplitude: float = 0.1


@dataclass
class AudioFingerprint:
    """AudioContext 指纹"""

    sample_rate: int
    max_channel_count: int
    number_of_inputs: int
    number_of_outputs: int
    channel_count: int
    channel_count_mode: str
    channel_interpretation: str

    # 音频处理结果哈希
    audio_hash: str
    noise_seed: int


@dataclass
class FontFingerprint:
    """字体指纹"""

    # 可用字体列表
    available_fonts: List[str]

    # 字体度量
    font_metrics: Dict[str, Dict]


@dataclass
class PluginFingerprint:
    """插件指纹"""

    plugins: List[Dict[str, str]]
    mime_types: List[Dict[str, str]]


@dataclass
class TLSFingerprint:
    """TLS/JA3 指纹"""

    ja3_hash: str
    ja3_full: str

    # TLS 配置
    tls_version: str
    cipher_suites: List[str]
    extensions: List[int]
    supported_groups: List[str]
    ec_point_formats: List[str]


@dataclass
class TimezoneFingerprint:
    """时区指纹"""

    timezone: str  # e.g., "Asia/Shanghai"
    timezone_offset: int  # 分钟，e.g., -480

    # Date 格式化结果
    date_format: str
    locale: str


@dataclass
class BrowserProfile:
    """完整浏览器指纹档案"""

    # 唯一标识
    profile_id: str

    # 基础信息
    browser: Browser
    platform: Platform
    browser_version: str

    # 各类指纹
    navigator: NavigatorFingerprint
    screen: ScreenFingerprint
    webgl: WebGLFingerprint
    canvas: CanvasFingerprint
    audio: AudioFingerprint
    fonts: FontFingerprint
    plugins: PluginFingerprint
    tls: TLSFingerprint
    timezone: TimezoneFingerprint

    # 元数据
    created_at: str
    last_used: str
    use_count: int = 0

    # 关联数据
    proxy: Optional[str] = None
    cookies: Dict[str, str] = field(default_factory=dict)
    local_storage: Dict[str, str] = field(default_factory=dict)

    def get_fingerprint_hash(self) -> str:
        """计算指纹哈希用于标识"""
        data = {
            "ua": self.navigator.user_agent,
            "screen": f"{self.screen.width}x{self.screen.height}",
            "webgl": f"{self.webgl.vendor}_{self.webgl.renderer}",
            "canvas": self.canvas.canvas_hash,
            "audio": self.audio.audio_hash,
            "tz": self.timezone.timezone,
        }
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]
```

---

## 指纹生成器

### 一致性指纹生成

```python
import random
from datetime import datetime
import uuid


class FingerprintGenerator:
    """指纹生成器 - 确保内部一致性"""

    # 真实设备数据库
    DEVICE_DATABASE = {
        (Platform.WINDOWS, Browser.CHROME): [
            {
                "screen_resolutions": [
                    (1920, 1080), (2560, 1440), (1366, 768),
                    (1536, 864), (1440, 900), (1280, 720)
                ],
                "device_memory": [4, 8, 16, 32],
                "hardware_concurrency": [4, 6, 8, 12, 16],
                "webgl_vendors": [
                    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060, OpenGL 4.5)"),
                    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060, OpenGL 4.5)"),
                    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 580 Series, OpenGL 4.5)"),
                    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630, OpenGL 4.5)"),
                ],
                "fonts": [
                    "Arial", "Arial Black", "Calibri", "Cambria", "Comic Sans MS",
                    "Consolas", "Courier New", "Georgia", "Impact", "Lucida Console",
                    "Microsoft Sans Serif", "Palatino Linotype", "Segoe UI",
                    "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana"
                ],
            }
        ],
        (Platform.MACOS, Browser.CHROME): [
            {
                "screen_resolutions": [
                    (2560, 1600), (2880, 1800), (1920, 1080),
                    (1680, 1050), (1440, 900)
                ],
                "device_memory": [8, 16, 32, 64],
                "hardware_concurrency": [4, 8, 10, 12],
                "webgl_vendors": [
                    ("Google Inc. (Apple)", "ANGLE (Apple, Apple M1, OpenGL 4.1)"),
                    ("Google Inc. (Apple)", "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)"),
                    ("Google Inc. (Apple)", "ANGLE (Apple, Apple M2, OpenGL 4.1)"),
                    ("Google Inc. (Intel)", "ANGLE (Intel Inc., Intel Iris Plus Graphics, OpenGL 4.1)"),
                ],
                "fonts": [
                    "Arial", "Arial Black", "Comic Sans MS", "Courier New",
                    "Georgia", "Helvetica", "Helvetica Neue", "Impact",
                    "Lucida Grande", "Monaco", "Palatino", "Times",
                    "Times New Roman", "Trebuchet MS", "Verdana"
                ],
            }
        ],
        (Platform.LINUX, Browser.CHROME): [
            {
                "screen_resolutions": [
                    (1920, 1080), (2560, 1440), (1366, 768), (1600, 900)
                ],
                "device_memory": [4, 8, 16, 32],
                "hardware_concurrency": [4, 8, 12, 16],
                "webgl_vendors": [
                    ("Google Inc. (NVIDIA Corporation)", "ANGLE (NVIDIA Corporation, NVIDIA GeForce GTX 1080/PCIe/SSE2, OpenGL 4.6)"),
                    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 5700 XT, OpenGL 4.6)"),
                    ("Google Inc. (Intel)", "ANGLE (Intel, Mesa Intel(R) UHD Graphics 630, OpenGL 4.6)"),
                ],
                "fonts": [
                    "Arial", "Courier New", "DejaVu Sans", "DejaVu Sans Mono",
                    "DejaVu Serif", "Droid Sans", "Droid Sans Mono", "FreeMono",
                    "FreeSans", "FreeSerif", "Liberation Mono", "Liberation Sans",
                    "Liberation Serif", "Noto Sans", "Ubuntu", "Ubuntu Mono"
                ],
            }
        ],
    }

    # Chrome 版本历史（保持更新）
    CHROME_VERSIONS = [
        ("120", "120.0.6099.130"),
        ("121", "121.0.6167.85"),
        ("122", "122.0.6261.94"),
        ("123", "123.0.6312.86"),
        ("124", "124.0.6367.78"),
    ]

    def __init__(self, seed: Optional[int] = None):
        """
        初始化生成器

        Args:
            seed: 随机种子，相同种子生成相同指纹
        """
        self.seed = seed or random.randint(0, 2**32)
        self.rng = random.Random(self.seed)

    def generate_profile(
        self,
        platform: Platform = Platform.WINDOWS,
        browser: Browser = Browser.CHROME,
        locale: str = "zh-CN",
        timezone: str = "Asia/Shanghai",
    ) -> BrowserProfile:
        """
        生成完整的浏览器指纹档案

        Args:
            platform: 目标平台
            browser: 目标浏览器
            locale: 语言区域
            timezone: 时区

        Returns:
            BrowserProfile: 完整指纹档案
        """

        # 获取设备数据库
        device_data = self.DEVICE_DATABASE.get(
            (platform, browser),
            self.DEVICE_DATABASE[(Platform.WINDOWS, Browser.CHROME)]
        )[0]

        # 选择一致的设备配置
        screen_res = self.rng.choice(device_data["screen_resolutions"])
        device_memory = self.rng.choice(device_data["device_memory"])
        hardware_concurrency = self.rng.choice(device_data["hardware_concurrency"])
        webgl_vendor, webgl_renderer = self.rng.choice(device_data["webgl_vendors"])

        # 选择 Chrome 版本
        major_ver, full_ver = self.rng.choice(self.CHROME_VERSIONS)

        # 生成 User-Agent
        user_agent = self._generate_user_agent(platform, browser, full_ver)

        # 生成各类指纹
        navigator = self._generate_navigator(
            platform, browser, user_agent, locale,
            hardware_concurrency, device_memory
        )

        screen = self._generate_screen(screen_res)

        webgl = self._generate_webgl(webgl_vendor, webgl_renderer)

        canvas = self._generate_canvas()

        audio = self._generate_audio()

        fonts = self._generate_fonts(device_data["fonts"])

        plugins = self._generate_plugins(browser)

        tls = self._generate_tls(browser, major_ver)

        tz = self._generate_timezone(timezone, locale)

        # 创建完整档案
        profile = BrowserProfile(
            profile_id=str(uuid.uuid4()),
            browser=browser,
            platform=platform,
            browser_version=full_ver,
            navigator=navigator,
            screen=screen,
            webgl=webgl,
            canvas=canvas,
            audio=audio,
            fonts=fonts,
            plugins=plugins,
            tls=tls,
            timezone=tz,
            created_at=datetime.now().isoformat(),
            last_used=datetime.now().isoformat(),
        )

        return profile

    def _generate_user_agent(
        self,
        platform: Platform,
        browser: Browser,
        version: str
    ) -> str:
        """生成 User-Agent"""

        platform_strings = {
            Platform.WINDOWS: "Windows NT 10.0; Win64; x64",
            Platform.MACOS: "Macintosh; Intel Mac OS X 10_15_7",
            Platform.LINUX: "X11; Linux x86_64",
        }

        platform_str = platform_strings.get(platform, platform_strings[Platform.WINDOWS])

        if browser == Browser.CHROME:
            return f"Mozilla/5.0 ({platform_str}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
        elif browser == Browser.FIREFOX:
            return f"Mozilla/5.0 ({platform_str}; rv:121.0) Gecko/20100101 Firefox/121.0"
        elif browser == Browser.SAFARI:
            return f"Mozilla/5.0 ({platform_str}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        else:
            return f"Mozilla/5.0 ({platform_str}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36 Edg/{version}"

    def _generate_navigator(
        self,
        platform: Platform,
        browser: Browser,
        user_agent: str,
        locale: str,
        hardware_concurrency: int,
        device_memory: int,
    ) -> NavigatorFingerprint:
        """生成 Navigator 指纹"""

        # 语言列表
        language_map = {
            "zh-CN": ["zh-CN", "zh", "en-US", "en"],
            "en-US": ["en-US", "en"],
            "ja-JP": ["ja-JP", "ja", "en-US", "en"],
        }

        return NavigatorFingerprint(
            user_agent=user_agent,
            platform=platform.value,
            vendor="Google Inc." if browser == Browser.CHROME else "",
            vendor_sub="",
            product="Gecko",
            product_sub="20030107" if browser == Browser.FIREFOX else "20100101",
            app_name="Netscape",
            app_code_name="Mozilla",
            app_version=user_agent.replace("Mozilla/", ""),
            language=locale,
            languages=language_map.get(locale, ["en-US", "en"]),
            hardware_concurrency=hardware_concurrency,
            device_memory=device_memory,
            max_touch_points=0 if platform in [Platform.WINDOWS, Platform.MACOS, Platform.LINUX] else 5,
            cookie_enabled=True,
            do_not_track=None,
            pdf_viewer_enabled=True,
            webdriver=False,  # 关键！
        )

    def _generate_screen(self, resolution: Tuple[int, int]) -> ScreenFingerprint:
        """生成屏幕指纹"""

        width, height = resolution

        # 任务栏通常占用一些高度
        taskbar_height = self.rng.choice([40, 48, 60, 0])

        return ScreenFingerprint(
            width=width,
            height=height,
            avail_width=width,
            avail_height=height - taskbar_height,
            color_depth=24,
            pixel_depth=24,
            device_pixel_ratio=self.rng.choice([1.0, 1.25, 1.5, 2.0]),
        )

    def _generate_webgl(self, vendor: str, renderer: str) -> WebGLFingerprint:
        """生成 WebGL 指纹"""

        return WebGLFingerprint(
            vendor=vendor,
            renderer=renderer,
            max_texture_size=16384,
            max_vertex_attribs=16,
            max_vertex_uniform_vectors=4096,
            max_varying_vectors=30,
            max_fragment_uniform_vectors=1024,
            max_vertex_texture_image_units=16,
            max_texture_image_units=16,
            max_combined_texture_image_units=32,
            max_cube_map_texture_size=16384,
            max_render_buffer_size=16384,
            max_viewport_dims=(32767, 32767),
            extensions=[
                "ANGLE_instanced_arrays",
                "EXT_blend_minmax",
                "EXT_color_buffer_half_float",
                "EXT_float_blend",
                "EXT_frag_depth",
                "EXT_shader_texture_lod",
                "EXT_texture_compression_bptc",
                "EXT_texture_compression_rgtc",
                "EXT_texture_filter_anisotropic",
                "EXT_sRGB",
                "OES_element_index_uint",
                "OES_fbo_render_mipmap",
                "OES_standard_derivatives",
                "OES_texture_float",
                "OES_texture_float_linear",
                "OES_texture_half_float",
                "OES_texture_half_float_linear",
                "OES_vertex_array_object",
                "WEBGL_color_buffer_float",
                "WEBGL_compressed_texture_s3tc",
                "WEBGL_compressed_texture_s3tc_srgb",
                "WEBGL_debug_renderer_info",
                "WEBGL_debug_shaders",
                "WEBGL_depth_texture",
                "WEBGL_draw_buffers",
                "WEBGL_lose_context",
            ],
            shader_precision={
                "vertex": {"highFloat": {"precision": 23, "rangeMin": 127, "rangeMax": 127}},
                "fragment": {"highFloat": {"precision": 23, "rangeMin": 127, "rangeMax": 127}},
            },
        )

    def _generate_canvas(self) -> CanvasFingerprint:
        """生成 Canvas 指纹"""

        # 生成唯一但一致的 Canvas 哈希
        seed_bytes = str(self.seed).encode()
        canvas_hash = hashlib.sha256(seed_bytes + b"canvas").hexdigest()[:32]

        return CanvasFingerprint(
            canvas_hash=canvas_hash,
            noise_seed=self.rng.randint(0, 2**32),
            noise_amplitude=self.rng.uniform(0.05, 0.15),
        )

    def _generate_audio(self) -> AudioFingerprint:
        """生成 Audio 指纹"""

        seed_bytes = str(self.seed).encode()
        audio_hash = hashlib.sha256(seed_bytes + b"audio").hexdigest()[:32]

        return AudioFingerprint(
            sample_rate=44100,
            max_channel_count=2,
            number_of_inputs=1,
            number_of_outputs=1,
            channel_count=2,
            channel_count_mode="max",
            channel_interpretation="speakers",
            audio_hash=audio_hash,
            noise_seed=self.rng.randint(0, 2**32),
        )

    def _generate_fonts(self, available_fonts: List[str]) -> FontFingerprint:
        """生成字体指纹"""

        # 随机选择一些字体作为"已安装"
        num_fonts = self.rng.randint(len(available_fonts) - 5, len(available_fonts))
        selected_fonts = self.rng.sample(available_fonts, num_fonts)

        # 生成字体度量
        metrics = {}
        for font in selected_fonts:
            # 每个字体的度量在同一 seed 下保持一致
            font_seed = self.seed + hash(font)
            font_rng = random.Random(font_seed)
            metrics[font] = {
                "width": font_rng.uniform(7.5, 8.5),
                "height": font_rng.uniform(13, 15),
            }

        return FontFingerprint(
            available_fonts=selected_fonts,
            font_metrics=metrics,
        )

    def _generate_plugins(self, browser: Browser) -> PluginFingerprint:
        """生成插件指纹"""

        if browser == Browser.CHROME:
            plugins = [
                {"name": "PDF Viewer", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
                {"name": "Chrome PDF Viewer", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
                {"name": "Chromium PDF Viewer", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
                {"name": "Microsoft Edge PDF Viewer", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
                {"name": "WebKit built-in PDF", "filename": "internal-pdf-viewer", "description": "Portable Document Format"},
            ]
            mime_types = [
                {"type": "application/pdf", "suffixes": "pdf", "description": "Portable Document Format"},
                {"type": "text/pdf", "suffixes": "pdf", "description": "Portable Document Format"},
            ]
        else:
            plugins = []
            mime_types = []

        return PluginFingerprint(plugins=plugins, mime_types=mime_types)

    def _generate_tls(self, browser: Browser, major_version: str) -> TLSFingerprint:
        """生成 TLS/JA3 指纹"""

        # Chrome 的典型 JA3
        if browser == Browser.CHROME:
            cipher_suites = [
                "TLS_AES_128_GCM_SHA256",
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
                "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
                "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
                "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
                "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
                "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
                "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
            ]
            extensions = [0, 23, 65281, 10, 11, 35, 16, 5, 13, 18, 51, 45, 43, 27, 21]
            supported_groups = ["x25519", "secp256r1", "secp384r1"]

            # Chrome 版本对应的 JA3
            ja3_hashes = {
                "120": "cd08e31494f9531f560d64c695473da9",
                "121": "cd08e31494f9531f560d64c695473da9",
                "122": "579ccef312d18482fc42e2b822ca2430",
                "123": "579ccef312d18482fc42e2b822ca2430",
                "124": "579ccef312d18482fc42e2b822ca2430",
            }
            ja3_hash = ja3_hashes.get(major_version, "cd08e31494f9531f560d64c695473da9")
        else:
            # Firefox 的典型配置
            cipher_suites = [
                "TLS_AES_128_GCM_SHA256",
                "TLS_CHACHA20_POLY1305_SHA256",
                "TLS_AES_256_GCM_SHA384",
            ]
            extensions = [0, 23, 65281, 10, 11, 35, 16, 5, 51, 43, 13, 45, 28, 21]
            supported_groups = ["x25519", "secp256r1", "secp384r1", "secp521r1", "ffdhe2048", "ffdhe3072"]
            ja3_hash = "e6589e6bfb3c81269c36d45e55f47b20"

        return TLSFingerprint(
            ja3_hash=ja3_hash,
            ja3_full=f"771,{','.join(cipher_suites)},{','.join(map(str, extensions))}",
            tls_version="TLS 1.3",
            cipher_suites=cipher_suites,
            extensions=extensions,
            supported_groups=supported_groups,
            ec_point_formats=["uncompressed"],
        )

    def _generate_timezone(self, timezone: str, locale: str) -> TimezoneFingerprint:
        """生成时区指纹"""

        timezone_offsets = {
            "Asia/Shanghai": -480,
            "Asia/Tokyo": -540,
            "America/New_York": 300,
            "America/Los_Angeles": 480,
            "Europe/London": 0,
            "Europe/Paris": -60,
        }

        return TimezoneFingerprint(
            timezone=timezone,
            timezone_offset=timezone_offsets.get(timezone, -480),
            date_format="zh-CN" if locale.startswith("zh") else locale,
            locale=locale,
        )
```

---

## 指纹注入器

### Playwright 注入

```python
from playwright.async_api import Page, BrowserContext


class PlaywrightInjector:
    """Playwright 指纹注入器"""

    @staticmethod
    async def inject_profile(
        context: BrowserContext,
        profile: BrowserProfile
    ):
        """
        将指纹注入到浏览器上下文

        Args:
            context: Playwright 浏览器上下文
            profile: 指纹档案
        """

        # 注入 JavaScript 覆盖
        await context.add_init_script(
            PlaywrightInjector._generate_inject_script(profile)
        )

    @staticmethod
    def _generate_inject_script(profile: BrowserProfile) -> str:
        """生成注入脚本"""

        nav = profile.navigator
        screen = profile.screen
        webgl = profile.webgl
        canvas = profile.canvas
        audio = profile.audio
        tz = profile.timezone

        return f"""
        (function() {{
            'use strict';

            // ==================== Navigator ====================
            const navigatorProps = {{
                userAgent: '{nav.user_agent}',
                platform: '{nav.platform}',
                vendor: '{nav.vendor}',
                vendorSub: '{nav.vendor_sub}',
                product: '{nav.product}',
                productSub: '{nav.product_sub}',
                appName: '{nav.app_name}',
                appCodeName: '{nav.app_code_name}',
                appVersion: '{nav.app_version}',
                language: '{nav.language}',
                languages: {json.dumps(nav.languages)},
                hardwareConcurrency: {nav.hardware_concurrency},
                deviceMemory: {nav.device_memory},
                maxTouchPoints: {nav.max_touch_points},
                cookieEnabled: {str(nav.cookie_enabled).lower()},
                pdfViewerEnabled: {str(nav.pdf_viewer_enabled).lower()},
            }};

            for (const [key, value] of Object.entries(navigatorProps)) {{
                Object.defineProperty(navigator, key, {{
                    get: () => value,
                    enumerable: true,
                    configurable: true
                }});
            }}

            // WebDriver 检测绕过 - 关键！
            Object.defineProperty(navigator, 'webdriver', {{
                get: () => undefined,
                enumerable: true,
                configurable: true
            }});

            // 删除 webdriver 相关属性
            delete navigator.__proto__.webdriver;

            // ==================== Screen ====================
            const screenProps = {{
                width: {screen.width},
                height: {screen.height},
                availWidth: {screen.avail_width},
                availHeight: {screen.avail_height},
                colorDepth: {screen.color_depth},
                pixelDepth: {screen.pixel_depth},
            }};

            for (const [key, value] of Object.entries(screenProps)) {{
                Object.defineProperty(screen, key, {{
                    get: () => value,
                    enumerable: true,
                    configurable: true
                }});
            }}

            Object.defineProperty(window, 'devicePixelRatio', {{
                get: () => {screen.device_pixel_ratio},
                enumerable: true,
                configurable: true
            }});

            // ==================== WebGL ====================
            const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {{
                const UNMASKED_VENDOR_WEBGL = 0x9245;
                const UNMASKED_RENDERER_WEBGL = 0x9246;

                if (param === UNMASKED_VENDOR_WEBGL) {{
                    return '{webgl.vendor}';
                }}
                if (param === UNMASKED_RENDERER_WEBGL) {{
                    return '{webgl.renderer}';
                }}
                return originalGetParameter.call(this, param);
            }};

            // WebGL2 也要处理
            if (typeof WebGL2RenderingContext !== 'undefined') {{
                const originalGetParameter2 = WebGL2RenderingContext.prototype.getParameter;
                WebGL2RenderingContext.prototype.getParameter = function(param) {{
                    const UNMASKED_VENDOR_WEBGL = 0x9245;
                    const UNMASKED_RENDERER_WEBGL = 0x9246;

                    if (param === UNMASKED_VENDOR_WEBGL) {{
                        return '{webgl.vendor}';
                    }}
                    if (param === UNMASKED_RENDERER_WEBGL) {{
                        return '{webgl.renderer}';
                    }}
                    return originalGetParameter2.call(this, param);
                }};
            }}

            // ==================== Canvas 指纹噪声 ====================
            const noiseSeed = {canvas.noise_seed};
            const noiseAmplitude = {canvas.noise_amplitude};

            // 伪随机数生成器（确保一致性）
            function mulberry32(a) {{
                return function() {{
                    var t = a += 0x6D2B79F5;
                    t = Math.imul(t ^ t >>> 15, t | 1);
                    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
                    return ((t ^ t >>> 14) >>> 0) / 4294967296;
                }}
            }}

            const rng = mulberry32(noiseSeed);

            // 修改 toDataURL
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type, quality) {{
                const ctx = this.getContext('2d');
                if (ctx) {{
                    const imageData = ctx.getImageData(0, 0, this.width, this.height);
                    const data = imageData.data;

                    // 添加一致的噪声
                    for (let i = 0; i < data.length; i += 4) {{
                        const noise = (rng() - 0.5) * noiseAmplitude * 255;
                        data[i] = Math.max(0, Math.min(255, data[i] + noise));
                        data[i + 1] = Math.max(0, Math.min(255, data[i + 1] + noise));
                        data[i + 2] = Math.max(0, Math.min(255, data[i + 2] + noise));
                    }}

                    ctx.putImageData(imageData, 0, 0);
                }}
                return originalToDataURL.call(this, type, quality);
            }};

            // ==================== AudioContext 指纹噪声 ====================
            const audioNoiseSeed = {audio.noise_seed};
            const audioRng = mulberry32(audioNoiseSeed);

            const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
            AudioContext.prototype.createAnalyser = function() {{
                const analyser = originalCreateAnalyser.call(this);
                const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;

                analyser.getFloatFrequencyData = function(array) {{
                    originalGetFloatFrequencyData.call(this, array);
                    for (let i = 0; i < array.length; i++) {{
                        array[i] += (audioRng() - 0.5) * 0.0001;
                    }}
                }};

                return analyser;
            }};

            // ==================== 时区 ====================
            const targetTimezone = '{tz.timezone}';
            const targetOffset = {tz.timezone_offset};

            // 覆盖 Date 方法
            const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
            Date.prototype.getTimezoneOffset = function() {{
                return targetOffset;
            }};

            // 覆盖 Intl
            const originalDateTimeFormat = Intl.DateTimeFormat;
            Intl.DateTimeFormat = function(locales, options) {{
                options = options || {{}};
                options.timeZone = options.timeZone || targetTimezone;
                return new originalDateTimeFormat(locales, options);
            }};
            Intl.DateTimeFormat.prototype = originalDateTimeFormat.prototype;

            // ==================== 插件 ====================
            const pluginData = {json.dumps([p for p in profile.plugins.plugins])};
            const mimeData = {json.dumps([m for m in profile.plugins.mime_types])};

            // 创建假的 PluginArray
            const fakePlugins = {{}};
            pluginData.forEach((p, i) => {{
                fakePlugins[i] = {{
                    name: p.name,
                    filename: p.filename,
                    description: p.description,
                    length: 1,
                }};
            }});
            fakePlugins.length = pluginData.length;
            fakePlugins.item = (i) => fakePlugins[i];
            fakePlugins.namedItem = (name) => pluginData.find(p => p.name === name);
            fakePlugins.refresh = () => {{}};

            Object.defineProperty(navigator, 'plugins', {{
                get: () => fakePlugins,
                enumerable: true,
                configurable: true
            }});

            // ==================== 权限 API ====================
            if (navigator.permissions) {{
                const originalQuery = navigator.permissions.query;
                navigator.permissions.query = function(parameters) {{
                    if (parameters.name === 'notifications') {{
                        return Promise.resolve({{ state: 'prompt', onchange: null }});
                    }}
                    return originalQuery.call(this, parameters);
                }};
            }}

            // ==================== Automation 检测绕过 ====================

            // Chrome DevTools Protocol 检测
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;

            // Selenium 检测
            delete window._selenium;
            delete window._Selenium_IDE_Recorder;
            delete window.$cdc_asdjflasutopfhvcZLmcfl_;
            delete document.$cdc_asdjflasutopfhvcZLmcfl_;

            // Puppeteer 检测
            delete window.__puppeteer_evaluation_script__;

            // Playwright 检测
            delete window.__playwright;
            delete window.__pw_manual;

            console.log('Fingerprint injection completed');
        }})();
        """


class SeleniumInjector:
    """Selenium 指纹注入器"""

    @staticmethod
    def inject_profile(driver, profile: BrowserProfile):
        """
        将指纹注入到 Selenium WebDriver

        Args:
            driver: Selenium WebDriver
            profile: 指纹档案
        """

        # 使用 CDP 注入
        script = PlaywrightInjector._generate_inject_script(profile)

        # 在页面加载前执行
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': script
        })
```

---

## 指纹持久化

### 档案存储

```python
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime


class ProfileStorage:
    """指纹档案存储管理"""

    def __init__(self, storage_dir: Path = Path("./profiles")):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "index.json"
        self._load_index()

    def _load_index(self):
        """加载索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
        else:
            self.index = {"profiles": [], "last_updated": None}

    def _save_index(self):
        """保存索引"""
        self.index["last_updated"] = datetime.now().isoformat()
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    def save_profile(self, profile: BrowserProfile) -> Path:
        """
        保存指纹档案

        Args:
            profile: 指纹档案

        Returns:
            Path: 保存路径
        """

        # 更新使用信息
        profile.last_used = datetime.now().isoformat()
        profile.use_count += 1

        # 序列化
        profile_dict = self._profile_to_dict(profile)

        # 保存文件
        filepath = self.storage_dir / f"{profile.profile_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profile_dict, f, indent=2, ensure_ascii=False)

        # 更新索引
        self._update_index(profile)

        return filepath

    def load_profile(self, profile_id: str) -> Optional[BrowserProfile]:
        """
        加载指纹档案

        Args:
            profile_id: 档案 ID

        Returns:
            BrowserProfile: 指纹档案
        """

        filepath = self.storage_dir / f"{profile_id}.json"
        if not filepath.exists():
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return self._dict_to_profile(data)

    def list_profiles(
        self,
        platform: Optional[Platform] = None,
        browser: Optional[Browser] = None,
    ) -> List[dict]:
        """
        列出所有档案

        Args:
            platform: 过滤平台
            browser: 过滤浏览器

        Returns:
            List[dict]: 档案摘要列表
        """

        profiles = self.index.get("profiles", [])

        if platform:
            profiles = [p for p in profiles if p["platform"] == platform.value]
        if browser:
            profiles = [p for p in profiles if p["browser"] == browser.value]

        return profiles

    def get_random_profile(
        self,
        platform: Optional[Platform] = None,
        browser: Optional[Browser] = None,
    ) -> Optional[BrowserProfile]:
        """
        随机获取一个档案

        Args:
            platform: 过滤平台
            browser: 过滤浏览器

        Returns:
            BrowserProfile: 随机选择的档案
        """

        profiles = self.list_profiles(platform, browser)
        if not profiles:
            return None

        selected = random.choice(profiles)
        return self.load_profile(selected["profile_id"])

    def delete_profile(self, profile_id: str) -> bool:
        """删除档案"""

        filepath = self.storage_dir / f"{profile_id}.json"
        if filepath.exists():
            filepath.unlink()

            # 更新索引
            self.index["profiles"] = [
                p for p in self.index["profiles"]
                if p["profile_id"] != profile_id
            ]
            self._save_index()
            return True

        return False

    def _update_index(self, profile: BrowserProfile):
        """更新索引"""

        summary = {
            "profile_id": profile.profile_id,
            "browser": profile.browser.value,
            "platform": profile.platform.value,
            "browser_version": profile.browser_version,
            "created_at": profile.created_at,
            "last_used": profile.last_used,
            "use_count": profile.use_count,
            "fingerprint_hash": profile.get_fingerprint_hash(),
        }

        # 更新或添加
        existing = next(
            (i for i, p in enumerate(self.index["profiles"])
             if p["profile_id"] == profile.profile_id),
            None
        )

        if existing is not None:
            self.index["profiles"][existing] = summary
        else:
            self.index["profiles"].append(summary)

        self._save_index()

    def _profile_to_dict(self, profile: BrowserProfile) -> dict:
        """将 Profile 转换为字典"""
        return {
            "profile_id": profile.profile_id,
            "browser": profile.browser.value,
            "platform": profile.platform.value,
            "browser_version": profile.browser_version,
            "navigator": asdict(profile.navigator),
            "screen": asdict(profile.screen),
            "webgl": asdict(profile.webgl),
            "canvas": asdict(profile.canvas),
            "audio": asdict(profile.audio),
            "fonts": asdict(profile.fonts),
            "plugins": asdict(profile.plugins),
            "tls": asdict(profile.tls),
            "timezone": asdict(profile.timezone),
            "created_at": profile.created_at,
            "last_used": profile.last_used,
            "use_count": profile.use_count,
            "proxy": profile.proxy,
            "cookies": profile.cookies,
            "local_storage": profile.local_storage,
        }

    def _dict_to_profile(self, data: dict) -> BrowserProfile:
        """将字典转换为 Profile"""
        return BrowserProfile(
            profile_id=data["profile_id"],
            browser=Browser(data["browser"]),
            platform=Platform(data["platform"]),
            browser_version=data["browser_version"],
            navigator=NavigatorFingerprint(**data["navigator"]),
            screen=ScreenFingerprint(**data["screen"]),
            webgl=WebGLFingerprint(**data["webgl"]),
            canvas=CanvasFingerprint(**data["canvas"]),
            audio=AudioFingerprint(**data["audio"]),
            fonts=FontFingerprint(**data["fonts"]),
            plugins=PluginFingerprint(**data["plugins"]),
            tls=TLSFingerprint(**data["tls"]),
            timezone=TimezoneFingerprint(**data["timezone"]),
            created_at=data["created_at"],
            last_used=data["last_used"],
            use_count=data["use_count"],
            proxy=data.get("proxy"),
            cookies=data.get("cookies", {}),
            local_storage=data.get("local_storage", {}),
        )
```

---

## 指纹一致性验证

### 验证器

```python
from typing import List, Tuple


class FingerprintValidator:
    """指纹一致性验证器"""

    # 已知的不一致组合
    INCONSISTENCY_RULES = [
        # (条件, 检查, 错误消息)
        (
            lambda p: p.platform == Platform.WINDOWS,
            lambda p: "Mac" not in p.navigator.user_agent,
            "Windows 平台但 UA 包含 Mac"
        ),
        (
            lambda p: p.platform == Platform.MACOS,
            lambda p: "Macintosh" in p.navigator.user_agent,
            "macOS 平台但 UA 不包含 Macintosh"
        ),
        (
            lambda p: p.navigator.max_touch_points > 0,
            lambda p: "Mobile" in p.navigator.user_agent or p.platform in [Platform.ANDROID, Platform.IOS],
            "有触摸点但不是移动设备"
        ),
        (
            lambda p: p.screen.device_pixel_ratio > 1.5,
            lambda p: p.screen.width >= 1920 or p.platform == Platform.MACOS,
            "高 DPI 但分辨率不匹配"
        ),
        (
            lambda p: "NVIDIA" in p.webgl.renderer,
            lambda p: p.platform != Platform.MACOS or "M1" not in p.webgl.renderer,
            "NVIDIA GPU 在 Apple Silicon Mac 上不存在"
        ),
        (
            lambda p: p.timezone.timezone == "Asia/Shanghai",
            lambda p: "zh" in p.navigator.language.lower(),
            "中国时区但语言不是中文"
        ),
    ]

    @classmethod
    def validate(cls, profile: BrowserProfile) -> Tuple[bool, List[str]]:
        """
        验证指纹一致性

        Args:
            profile: 指纹档案

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误列表)
        """

        errors = []

        for condition, check, message in cls.INCONSISTENCY_RULES:
            try:
                if condition(profile) and not check(profile):
                    errors.append(message)
            except Exception as e:
                errors.append(f"验证规则执行失败: {e}")

        # 额外检查
        errors.extend(cls._check_webdriver(profile))
        errors.extend(cls._check_automation_artifacts(profile))
        errors.extend(cls._check_version_consistency(profile))

        return len(errors) == 0, errors

    @classmethod
    def _check_webdriver(cls, profile: BrowserProfile) -> List[str]:
        """检查 WebDriver 相关"""
        errors = []

        if profile.navigator.webdriver:
            errors.append("navigator.webdriver 应该为 False")

        return errors

    @classmethod
    def _check_automation_artifacts(cls, profile: BrowserProfile) -> List[str]:
        """检查自动化痕迹"""
        errors = []

        # 检查 UA 中的可疑字符串
        suspicious_strings = ["HeadlessChrome", "Puppeteer", "Selenium", "PhantomJS"]
        for s in suspicious_strings:
            if s in profile.navigator.user_agent:
                errors.append(f"UA 包含可疑字符串: {s}")

        return errors

    @classmethod
    def _check_version_consistency(cls, profile: BrowserProfile) -> List[str]:
        """检查版本一致性"""
        errors = []

        # Chrome 版本应该在 UA 和 browser_version 中一致
        if profile.browser == Browser.CHROME:
            major_version = profile.browser_version.split('.')[0]
            if f"Chrome/{major_version}" not in profile.navigator.user_agent:
                errors.append("浏览器版本与 UA 不一致")

        return errors


# 使用示例
def create_validated_profile() -> BrowserProfile:
    """创建并验证指纹"""

    generator = FingerprintGenerator()

    for attempt in range(10):
        profile = generator.generate_profile(
            platform=Platform.WINDOWS,
            browser=Browser.CHROME,
            locale="zh-CN",
            timezone="Asia/Shanghai",
        )

        is_valid, errors = FingerprintValidator.validate(profile)

        if is_valid:
            return profile
        else:
            print(f"尝试 {attempt + 1}: 指纹无效 - {errors}")

    raise ValueError("无法生成有效指纹")
```

---

## 指纹检测对抗

### 常见检测方法与对抗

```python
class DetectionCountermeasures:
    """检测对抗措施"""

    @staticmethod
    def get_injection_script() -> str:
        """获取完整的对抗注入脚本"""

        return """
        (function() {
            'use strict';

            // ==================== 1. 属性检测对抗 ====================

            // 原型链保护
            const protectProperty = (obj, prop, value) => {
                try {
                    Object.defineProperty(obj, prop, {
                        get: () => value,
                        set: () => {},
                        enumerable: true,
                        configurable: false
                    });
                } catch(e) {}
            };

            // 防止检测属性描述符差异
            const originalGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
            Object.getOwnPropertyDescriptor = function(obj, prop) {
                const desc = originalGetOwnPropertyDescriptor.call(this, obj, prop);
                if (obj === navigator && prop === 'webdriver') {
                    return undefined;
                }
                return desc;
            };

            // ==================== 2. 函数 toString 保护 ====================

            // 保护被覆盖的函数看起来是原生的
            const fakeNativeFunction = (fn, name) => {
                const nativeCode = `function ${name}() { [native code] }`;
                fn.toString = () => nativeCode;
                fn.toLocaleString = () => nativeCode;
                Object.defineProperty(fn, 'name', { value: name });
                return fn;
            };

            // ==================== 3. 堆栈跟踪隐藏 ====================

            const originalError = Error;
            window.Error = function(...args) {
                const error = new originalError(...args);
                // 过滤掉注入脚本的堆栈帧
                if (error.stack) {
                    error.stack = error.stack
                        .split('\\n')
                        .filter(line => !line.includes('injected') && !line.includes('__puppeteer'))
                        .join('\\n');
                }
                return error;
            };
            Error.prototype = originalError.prototype;

            // ==================== 4. 性能指标正常化 ====================

            // 一些网站检查页面加载时间来判断是否是自动化
            const originalPerformanceNow = performance.now;
            let performanceOffset = 0;

            performance.now = function() {
                const realTime = originalPerformanceNow.call(this);
                // 添加随机抖动，模拟真实环境
                return realTime + performanceOffset + (Math.random() * 0.1);
            };

            // ==================== 5. 事件监听器计数正常化 ====================

            // 检测脚本可能计算事件监听器数量
            const originalAddEventListener = EventTarget.prototype.addEventListener;
            const listenerCounts = new WeakMap();

            EventTarget.prototype.addEventListener = function(type, listener, options) {
                // 限制监听器数量的可见性
                return originalAddEventListener.call(this, type, listener, options);
            };

            // ==================== 6. Console 方法保护 ====================

            // 防止通过 console 方法检测
            const originalConsoleLog = console.log;
            console.log = function(...args) {
                // 过滤掉检测相关的日志
                const filtered = args.filter(arg => {
                    if (typeof arg === 'string') {
                        return !arg.includes('webdriver') && !arg.includes('selenium');
                    }
                    return true;
                });
                if (filtered.length > 0) {
                    originalConsoleLog.apply(console, filtered);
                }
            };

            // ==================== 7. iframe 检测对抗 ====================

            // 一些网站在 iframe 中运行检测脚本
            const originalContentWindow = Object.getOwnPropertyDescriptor(
                HTMLIFrameElement.prototype, 'contentWindow'
            );

            Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                get: function() {
                    const win = originalContentWindow.get.call(this);
                    if (win) {
                        // 确保 iframe 中的环境也是干净的
                        try {
                            Object.defineProperty(win.navigator, 'webdriver', {
                                get: () => undefined
                            });
                        } catch(e) {}
                    }
                    return win;
                }
            });

            // ==================== 8. Worker 检测对抗 ====================

            // Web Worker 中也可能运行检测
            const originalWorker = window.Worker;
            window.Worker = function(scriptUrl, options) {
                const worker = new originalWorker(scriptUrl, options);
                // Worker 通信中过滤检测结果
                const originalPostMessage = worker.postMessage;
                worker.postMessage = function(message, transfer) {
                    // 可以在这里拦截和修改消息
                    return originalPostMessage.call(this, message, transfer);
                };
                return worker;
            };

            // ==================== 9. 浏览器特性探测正常化 ====================

            // 一些检测会探测特定浏览器的特有特性
            // 确保特性存在性与 UA 一致

            // Chrome 特有对象
            if (navigator.userAgent.includes('Chrome')) {
                window.chrome = window.chrome || {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() { return {}; },
                    app: {}
                };
            }

            // ==================== 10. RTCPeerConnection 泄露防护 ====================

            // WebRTC 可能泄露真实 IP
            const originalRTCPeerConnection = window.RTCPeerConnection;
            if (originalRTCPeerConnection) {
                window.RTCPeerConnection = function(config, constraints) {
                    // 移除 STUN/TURN 服务器以防止 IP 泄露
                    if (config && config.iceServers) {
                        config.iceServers = [];
                    }
                    return new originalRTCPeerConnection(config, constraints);
                };
                RTCPeerConnection.prototype = originalRTCPeerConnection.prototype;
            }

            console.log('Detection countermeasures active');
        })();
        """
```

---

## 使用示例

### 完整工作流

```python
from unified_agent import Brain
from unified_agent.fingerprint import (
    FingerprintGenerator,
    ProfileStorage,
    PlaywrightInjector,
    FingerprintValidator,
    Platform,
    Browser
)


async def scrape_with_fingerprint():
    """使用指纹档案进行爬取"""

    # 初始化
    brain = Brain()
    generator = FingerprintGenerator()
    storage = ProfileStorage(Path("./profiles"))

    # 尝试加载现有档案或创建新的
    profile = storage.get_random_profile(
        platform=Platform.WINDOWS,
        browser=Browser.CHROME
    )

    if not profile:
        # 创建新档案
        profile = generator.generate_profile(
            platform=Platform.WINDOWS,
            browser=Browser.CHROME,
            locale="zh-CN",
            timezone="Asia/Shanghai"
        )

        # 验证
        is_valid, errors = FingerprintValidator.validate(profile)
        if not is_valid:
            print(f"指纹验证失败: {errors}")
            return

        # 保存
        storage.save_profile(profile)
        print(f"创建新指纹: {profile.profile_id}")
    else:
        print(f"使用现有指纹: {profile.profile_id}")

    # 启动浏览器
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                f'--user-agent={profile.navigator.user_agent}',
            ]
        )

        context = await browser.new_context(
            viewport={
                'width': profile.screen.width,
                'height': profile.screen.height
            },
            locale=profile.timezone.locale,
            timezone_id=profile.timezone.timezone,
        )

        # 注入指纹
        await PlaywrightInjector.inject_profile(context, profile)

        # 加载保存的 Cookie
        if profile.cookies:
            await context.add_cookies([
                {"name": k, "value": v, "domain": ".example.com", "path": "/"}
                for k, v in profile.cookies.items()
            ])

        # 开始爬取
        page = await context.new_page()
        await page.goto("https://example.com")

        # 执行操作...

        # 保存新的 Cookie
        cookies = await context.cookies()
        profile.cookies = {c['name']: c['value'] for c in cookies}
        storage.save_profile(profile)

        await browser.close()


# 批量生成指纹
def generate_profile_pool(count: int = 100):
    """生成指纹池"""

    storage = ProfileStorage()

    platforms = [Platform.WINDOWS, Platform.MACOS, Platform.LINUX]

    for i in range(count):
        generator = FingerprintGenerator(seed=i)
        platform = platforms[i % len(platforms)]

        profile = generator.generate_profile(
            platform=platform,
            browser=Browser.CHROME,
            locale="zh-CN",
            timezone="Asia/Shanghai"
        )

        is_valid, errors = FingerprintValidator.validate(profile)
        if is_valid:
            storage.save_profile(profile)
            print(f"[{i+1}/{count}] 生成: {profile.profile_id[:8]}...")
        else:
            print(f"[{i+1}/{count}] 跳过: {errors}")

    print(f"完成，共 {len(storage.list_profiles())} 个有效指纹")
```

---

## 指纹轮换策略

### 智能轮换

```python
from typing import Dict
from datetime import datetime, timedelta


class ProfileRotator:
    """指纹轮换管理器"""

    def __init__(self, storage: ProfileStorage):
        self.storage = storage
        self.usage_tracker: Dict[str, dict] = {}

    def get_profile(
        self,
        domain: str,
        platform: Optional[Platform] = None,
        max_uses_per_profile: int = 100,
        cooldown_hours: int = 24,
    ) -> Optional[BrowserProfile]:
        """
        智能获取指纹，考虑使用次数和冷却时间

        Args:
            domain: 目标域名
            platform: 目标平台
            max_uses_per_profile: 每个指纹最大使用次数
            cooldown_hours: 冷却时间（小时）

        Returns:
            BrowserProfile: 合适的指纹档案
        """

        profiles = self.storage.list_profiles(platform=platform)
        now = datetime.now()

        # 筛选可用的指纹
        available = []
        for p_info in profiles:
            profile_id = p_info["profile_id"]

            # 获取使用记录
            usage = self.usage_tracker.get(f"{profile_id}:{domain}", {
                "count": 0,
                "last_used": None
            })

            # 检查使用次数
            if usage["count"] >= max_uses_per_profile:
                continue

            # 检查冷却时间
            if usage["last_used"]:
                last_used = datetime.fromisoformat(usage["last_used"])
                if now - last_used < timedelta(hours=cooldown_hours):
                    continue

            available.append((p_info, usage["count"]))

        if not available:
            # 重置最久未使用的指纹
            self._reset_oldest(domain)
            return self.get_profile(domain, platform, max_uses_per_profile, cooldown_hours)

        # 选择使用次数最少的
        available.sort(key=lambda x: x[1])
        selected_info = available[0][0]

        # 加载完整档案
        profile = self.storage.load_profile(selected_info["profile_id"])

        # 更新使用记录
        key = f"{profile.profile_id}:{domain}"
        if key not in self.usage_tracker:
            self.usage_tracker[key] = {"count": 0, "last_used": None}
        self.usage_tracker[key]["count"] += 1
        self.usage_tracker[key]["last_used"] = now.isoformat()

        return profile

    def _reset_oldest(self, domain: str):
        """重置最久未使用的指纹"""

        domain_usage = [
            (k, v) for k, v in self.usage_tracker.items()
            if k.endswith(f":{domain}")
        ]

        if domain_usage:
            # 按最后使用时间排序
            domain_usage.sort(key=lambda x: x[1].get("last_used") or "")
            oldest_key = domain_usage[0][0]
            self.usage_tracker[oldest_key] = {"count": 0, "last_used": None}
```

---

## 在线指纹检测服务

### 常用检测网站

| 网站 | 检测项目 | 网址 |
|-----|---------|-----|
| CreepJS | 全面指纹检测 | https://abrahamjuliot.github.io/creepjs/ |
| Pixelscan | Bot 检测 | https://pixelscan.net/ |
| BrowserLeaks | 指纹泄露 | https://browserleaks.com/ |
| AmIUnique | 指纹唯一性 | https://amiunique.org/ |
| Sannysoft | 自动化检测 | https://bot.sannysoft.com/ |
| Incolumitas | 高级检测 | https://bot.incolumitas.com/ |

### 自动化检测脚本

```python
async def test_fingerprint(profile: BrowserProfile) -> dict:
    """
    在检测网站上测试指纹

    Returns:
        dict: 检测结果
    """

    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await PlaywrightInjector.inject_profile(context, profile)

        page = await context.new_page()

        # 测试 Sannysoft
        await page.goto("https://bot.sannysoft.com/")
        await page.wait_for_timeout(3000)

        # 截图
        await page.screenshot(path=f"test_{profile.profile_id[:8]}.png")

        # 提取结果
        results["sannysoft"] = await page.evaluate("""
            () => {
                const rows = document.querySelectorAll('table tr');
                const results = {};
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 2) {
                        const test = cells[0].textContent.trim();
                        const result = cells[1].textContent.trim();
                        results[test] = result;
                    }
                });
                return results;
            }
        """)

        await browser.close()

    return results
```

---

## 诊断日志

```
# 指纹生成
[FP_GEN] 创建指纹: profile_id={profile_id}
[FP_GEN] 平台: {platform}, 浏览器: {browser} v{version}
[FP_GEN] 屏幕: {width}x{height}, DPI: {dpi}
[FP_GEN] WebGL: {vendor} / {renderer}
[FP_GEN] 时区: {timezone}, 语言: {language}

# 指纹验证
[FP_VALID] 验证指纹一致性: profile_id={profile_id}
[FP_VALID] 检查项: {check_name} = {status}
[FP_VALID] 验证结果: {valid}, 错误: {errors}

# 指纹注入
[FP_INJECT] 注入目标: {browser_type}
[FP_INJECT] Navigator覆盖: {navigator_props}
[FP_INJECT] WebGL覆盖: {webgl_vendor}/{webgl_renderer}
[FP_INJECT] Canvas噪声种子: {noise_seed}

# 指纹存储
[FP_STORE] 保存指纹: {profile_id} -> {filepath}
[FP_STORE] 加载指纹: {profile_id}, 使用次数: {use_count}
[FP_STORE] 指纹池数量: {pool_size}

# 指纹轮换
[FP_ROTATE] 轮换策略: {strategy}
[FP_ROTATE] 当前指纹使用: {current_uses}/{max_uses}
[FP_ROTATE] 冷却中: {cooling_profiles}个

# 检测测试
[FP_TEST] 测试网站: {test_site}
[FP_TEST] 检测结果: {results}
[FP_TEST] 暴露项: {exposed_items}

# 错误情况
[FP_GEN] ERROR: 指纹生成失败: {error}
[FP_VALID] ERROR: 指纹不一致: {inconsistencies}
[FP_INJECT] ERROR: 注入失败: {error}
```

---

## 策略协调

指纹管理策略参考 [16-战术决策模块](16-tactics.md)：
- **指纹被检测** → 立即轮换，原指纹加入冷却
- **检测网站验证不过** → 调整生成参数，确保一致性
- **高频请求** → 增加指纹池容量，缩短轮换周期

---

## 相关模块

- **上游**: [02-反检测模块](02-anti-detection.md) - 基础反检测
- **配合**: [09-JS逆向模块](09-js-reverse.md) - 理解指纹检测代码
- **下游**: [04-请求模块](04-request.md) - 使用指纹发送请求

---

## 常见问题

### Q: 指纹被检测到不一致怎么办？

1. 使用 `FingerprintValidator` 验证指纹
2. 检查平台、UA、WebGL 渲染器是否匹配
3. 确保时区和语言设置一致

### Q: 如何提高指纹的真实性？

1. 从真实设备采集指纹数据
2. 定期更新浏览器版本数据库
3. 使用 CreepJS 等工具验证

### Q: 指纹应该多久更换一次？

- 低频请求: 可以长期使用同一指纹
- 高频请求: 建议每 100-500 次请求更换
- 被封禁时: 立即更换并加入冷却
