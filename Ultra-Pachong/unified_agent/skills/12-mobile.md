# 12 - 移动端/APP模块 (Mobile & APP)

---
name: mobile-app
version: 1.0.0
description: 移动端应用抓包、逆向与数据采集
triggers:
  - "APP"
  - "移动端"
  - "Android"
  - "iOS"
  - "抓包"
  - "Frida"
difficulty: ⭐⭐⭐⭐⭐
---

## 模块目标

**核心原则：给出需求，必须完成。**

| 目标 | 达成标准 |
|------|---------|
| **流量可抓** | HTTPS 流量 100% 可捕获，SSL Pinning 可绕过 |
| **协议可分析** | API 请求参数、签名算法能完整还原 |
| **逆向可行** | APK/IPA 反编译、Frida Hook、Native 分析有成熟方案 |
| **请求可复现** | 从抓包数据能生成可运行的 Python 代码 |
| **自动化可控** | Appium/ADB 自动化操作稳定可靠 |

---

## 模块概述

移动端模块负责 Android/iOS 应用的流量捕获、协议分析、加密逆向等工作，是获取移动端数据的核心能力。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           移动端抓取架构                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         目标 APP                                     │  │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │  │
│   │  │ 网络请求  │ │ 加密算法  │ │ 签名生成  │ │ 设备指纹  │              │  │
│   │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘              │  │
│   └───────┼────────────┼────────────┼────────────┼──────────────────────┘  │
│           │            │            │            │                          │
│   ┌───────┼────────────┼────────────┼────────────┼──────────────────────┐  │
│   │       ▼            ▼            ▼            ▼                      │  │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │  │
│   │  │ mitmproxy│ │  Frida   │ │ 反编译   │ │ 模拟器   │              │  │
│   │  │ 流量捕获  │ │ Hook注入 │ │ APK/IPA │ │ 自动化   │              │  │
│   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │  │
│   │                        分析层                                       │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         数据采集                                     │  │
│   │            复现请求 | 批量抓取 | 自动化操作                            │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 环境准备

### Android 环境

```bash
# 1. 安装 Android SDK
# 下载: https://developer.android.com/studio

# 2. 安装 ADB
# Windows: scoop install adb
# macOS: brew install android-platform-tools
# Linux: sudo apt install adb

# 3. 验证连接
adb devices

# 4. 安装必要工具
pip install frida-tools
pip install mitmproxy
pip install objection
```

### iOS 环境

```bash
# 1. macOS 必需，安装 Xcode
xcode-select --install

# 2. 安装工具
brew install libimobiledevice
brew install ideviceinstaller

# 3. 越狱设备安装 Frida
# 在 Cydia 中添加源: https://build.frida.re
# 安装 Frida

# 4. 验证连接
frida-ls-devices
```

### 模拟器选择

| 模拟器 | 平台 | Root | 特点 |
|-------|------|------|------|
| Android Studio Emulator | 全平台 | 可选 | 官方，稳定 |
| Genymotion | 全平台 | 内置 | 性能好，商业 |
| MuMu | Windows | 内置 | 国产，游戏优化 |
| 夜神 | Windows | 内置 | 国产，兼容性好 |
| LDPlayer | Windows | 内置 | 国产，游戏优化 |

---

## 流量捕获

### mitmproxy 配置

```python
"""
mitmproxy 抓包脚本
使用: mitmproxy -s capture.py
"""

from mitmproxy import ctx, http
import json
from pathlib import Path
from datetime import datetime


class TrafficCapture:
    """流量捕获"""

    def __init__(self):
        self.output_dir = Path("./captures")
        self.output_dir.mkdir(exist_ok=True)
        self.requests = []

        # 目标域名过滤
        self.target_domains = [
            "api.example.com",
            "m.example.com",
        ]

    def request(self, flow: http.HTTPFlow):
        """请求拦截"""

        # 域名过滤
        if not any(d in flow.request.host for d in self.target_domains):
            return

        # 记录请求
        req_data = {
            "timestamp": datetime.now().isoformat(),
            "method": flow.request.method,
            "url": flow.request.url,
            "headers": dict(flow.request.headers),
            "body": flow.request.text if flow.request.text else None,
        }

        self.requests.append(req_data)
        ctx.log.info(f"[Capture] {flow.request.method} {flow.request.url}")

    def response(self, flow: http.HTTPFlow):
        """响应拦截"""

        if not any(d in flow.request.host for d in self.target_domains):
            return

        # 找到对应请求并添加响应
        for req in reversed(self.requests):
            if req["url"] == flow.request.url:
                req["response"] = {
                    "status_code": flow.response.status_code,
                    "headers": dict(flow.response.headers),
                    "body": self._safe_decode(flow.response.content),
                }
                break

        # 保存到文件
        self._save()

    def _safe_decode(self, content: bytes) -> str:
        """安全解码响应内容"""
        try:
            return content.decode('utf-8')
        except:
            return content.hex()

    def _save(self):
        """保存捕获数据"""
        filepath = self.output_dir / f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.requests, f, ensure_ascii=False, indent=2)


addons = [TrafficCapture()]
```

### 证书安装

#### Android 证书安装

```bash
# 1. 导出 mitmproxy 证书
# 证书位置: ~/.mitmproxy/mitmproxy-ca-cert.cer

# 2. 推送到设备
adb push ~/.mitmproxy/mitmproxy-ca-cert.cer /sdcard/

# 3. 安装证书 (Android 7+)
# 设置 -> 安全 -> 从存储安装证书

# 4. Android 7+ 系统证书安装 (需要 Root)
# 转换证书格式
openssl x509 -inform PEM -subject_hash_old -in mitmproxy-ca-cert.cer | head -1
# 假设输出: c8750f0d

# 重命名并推送
cp mitmproxy-ca-cert.cer c8750f0d.0
adb root
adb remount
adb push c8750f0d.0 /system/etc/security/cacerts/
adb shell chmod 644 /system/etc/security/cacerts/c8750f0d.0
adb reboot
```

#### iOS 证书安装

```bash
# 1. 启动 mitmproxy
mitmproxy --listen-port 8080

# 2. 设备配置代理
# 设置 -> Wi-Fi -> 配置代理 -> 手动
# 服务器: 电脑 IP，端口: 8080

# 3. 访问 mitm.it 下载证书

# 4. 安装证书
# 设置 -> 通用 -> 描述文件 -> 安装

# 5. 信任证书
# 设置 -> 通用 -> 关于本机 -> 证书信任设置 -> 启用
```

### SSL Pinning 绕过

#### 使用 Frida 绕过

```python
"""
SSL Pinning 绕过脚本
使用: frida -U -f com.example.app -l ssl_bypass.js --no-pause
"""

SSL_BYPASS_SCRIPT = """
'use strict';

// 通用 SSL Pinning 绕过
Java.perform(function() {
    console.log('[*] SSL Pinning Bypass loaded');

    // ==================== OkHttp3 ====================
    try {
        var CertificatePinner = Java.use('okhttp3.CertificatePinner');
        CertificatePinner.check.overload('java.lang.String', 'java.util.List').implementation = function(hostname, peerCertificates) {
            console.log('[+] OkHttp3 CertificatePinner.check() bypassed for: ' + hostname);
            return;
        };
    } catch (e) {
        console.log('[-] OkHttp3 not found');
    }

    // ==================== TrustManagerImpl ====================
    try {
        var TrustManagerImpl = Java.use('com.android.org.conscrypt.TrustManagerImpl');
        TrustManagerImpl.verifyChain.implementation = function(untrustedChain, trustAnchorChain, host, clientAuth, ocspData, tlsSctData) {
            console.log('[+] TrustManagerImpl.verifyChain() bypassed for: ' + host);
            return untrustedChain;
        };
    } catch (e) {
        console.log('[-] TrustManagerImpl not found');
    }

    // ==================== X509TrustManager ====================
    try {
        var X509TrustManager = Java.use('javax.net.ssl.X509TrustManager');
        var TrustManager = Java.registerClass({
            name: 'com.custom.TrustManager',
            implements: [X509TrustManager],
            methods: {
                checkClientTrusted: function(chain, authType) {},
                checkServerTrusted: function(chain, authType) {},
                getAcceptedIssuers: function() { return []; }
            }
        });
    } catch (e) {
        console.log('[-] X509TrustManager bypass failed');
    }

    // ==================== SSLContext ====================
    try {
        var SSLContext = Java.use('javax.net.ssl.SSLContext');
        SSLContext.init.overload('[Ljavax.net.ssl.KeyManager;', '[Ljavax.net.ssl.TrustManager;', 'java.security.SecureRandom').implementation = function(keyManager, trustManager, secureRandom) {
            console.log('[+] SSLContext.init() bypassed');
            var TrustManagerImpl = Java.use('com.custom.TrustManager');
            var TrustManagers = [TrustManagerImpl.$new()];
            this.init(keyManager, TrustManagers, secureRandom);
        };
    } catch (e) {
        console.log('[-] SSLContext bypass failed');
    }

    // ==================== WebViewClient ====================
    try {
        var WebViewClient = Java.use('android.webkit.WebViewClient');
        WebViewClient.onReceivedSslError.implementation = function(view, handler, error) {
            console.log('[+] WebViewClient.onReceivedSslError() bypassed');
            handler.proceed();
        };
    } catch (e) {
        console.log('[-] WebViewClient not found');
    }

    // ==================== HttpsURLConnection ====================
    try {
        var HttpsURLConnection = Java.use('javax.net.ssl.HttpsURLConnection');
        HttpsURLConnection.setDefaultHostnameVerifier.implementation = function(hostnameVerifier) {
            console.log('[+] HttpsURLConnection.setDefaultHostnameVerifier() bypassed');
            return;
        };
        HttpsURLConnection.setSSLSocketFactory.implementation = function(factory) {
            console.log('[+] HttpsURLConnection.setSSLSocketFactory() bypassed');
            return;
        };
    } catch (e) {
        console.log('[-] HttpsURLConnection bypass failed');
    }

    console.log('[*] SSL Pinning Bypass complete');
});
"""


def bypass_ssl_pinning(package_name: str):
    """
    绕过 SSL Pinning

    Args:
        package_name: APP 包名
    """
    import frida

    device = frida.get_usb_device()

    # 启动或附加
    try:
        session = device.attach(package_name)
    except:
        pid = device.spawn([package_name])
        session = device.attach(pid)
        device.resume(pid)

    # 注入脚本
    script = session.create_script(SSL_BYPASS_SCRIPT)
    script.on('message', lambda msg, data: print(f"[Frida] {msg}"))
    script.load()

    print(f"[*] SSL Pinning bypass active for {package_name}")
    return session
```

#### 使用 Objection 绕过

```bash
# 安装 objection
pip install objection

# 启动并注入
objection -g com.example.app explore

# 在 objection shell 中
android sslpinning disable

# 或者一键绕过
objection -g com.example.app explore -s "android sslpinning disable"
```

---

## APK 逆向分析

### 工具链

```bash
# 1. apktool - APK 解包/重打包
# 下载: https://ibotpeaches.github.io/Apktool/
apktool d app.apk -o app_decoded

# 2. jadx - DEX 反编译为 Java
# 下载: https://github.com/skylot/jadx
jadx-gui app.apk

# 3. dex2jar - DEX 转 JAR
d2j-dex2jar app.apk

# 4. jd-gui - JAR 查看
jd-gui app-dex2jar.jar

# 5. Ghidra - Native 库分析
# 下载: https://ghidra-sre.org/
```

### 自动化分析脚本

```python
import subprocess
import os
from pathlib import Path
from typing import Dict, List
import re
import json


class APKAnalyzer:
    """APK 自动化分析"""

    def __init__(self, apk_path: str):
        self.apk_path = Path(apk_path)
        self.output_dir = Path(f"./analysis_{self.apk_path.stem}")
        self.output_dir.mkdir(exist_ok=True)

    def analyze(self) -> Dict:
        """完整分析流程"""

        results = {
            "package_info": self.get_package_info(),
            "permissions": self.get_permissions(),
            "activities": self.get_activities(),
            "services": self.get_services(),
            "receivers": self.get_receivers(),
            "native_libs": self.get_native_libs(),
            "api_endpoints": self.find_api_endpoints(),
            "encryption_methods": self.find_encryption(),
            "hardcoded_secrets": self.find_secrets(),
        }

        # 保存结果
        with open(self.output_dir / "analysis.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        return results

    def get_package_info(self) -> Dict:
        """获取包信息"""

        result = subprocess.run(
            ["aapt", "dump", "badging", str(self.apk_path)],
            capture_output=True,
            text=True
        )

        info = {}
        for line in result.stdout.split('\n'):
            if line.startswith("package:"):
                match = re.search(r"name='([^']+)'", line)
                if match:
                    info["package_name"] = match.group(1)
                match = re.search(r"versionName='([^']+)'", line)
                if match:
                    info["version_name"] = match.group(1)
                match = re.search(r"versionCode='([^']+)'", line)
                if match:
                    info["version_code"] = match.group(1)

        return info

    def get_permissions(self) -> List[str]:
        """获取权限列表"""

        result = subprocess.run(
            ["aapt", "dump", "permissions", str(self.apk_path)],
            capture_output=True,
            text=True
        )

        permissions = []
        for line in result.stdout.split('\n'):
            if "uses-permission:" in line:
                match = re.search(r"name='([^']+)'", line)
                if match:
                    permissions.append(match.group(1))

        return permissions

    def decompile(self) -> Path:
        """反编译 APK"""

        output = self.output_dir / "decompiled"

        subprocess.run([
            "apktool", "d",
            str(self.apk_path),
            "-o", str(output),
            "-f"
        ], check=True)

        return output

    def find_api_endpoints(self) -> List[str]:
        """查找 API 端点"""

        decompiled = self.decompile()
        endpoints = set()

        # 搜索 URL 模式
        url_pattern = re.compile(
            r'https?://[^\s"\'\)\]\}]+',
            re.IGNORECASE
        )

        for smali_file in decompiled.rglob("*.smali"):
            content = smali_file.read_text(errors='ignore')
            matches = url_pattern.findall(content)
            endpoints.update(matches)

        return list(endpoints)

    def find_encryption(self) -> List[Dict]:
        """查找加密方法"""

        decompiled = self.output_dir / "decompiled"
        if not decompiled.exists():
            self.decompile()

        encryption_patterns = [
            (r'Ljavax/crypto/Cipher', 'AES/DES Cipher'),
            (r'Ljava/security/MessageDigest', 'Hash (MD5/SHA)'),
            (r'Ljavax/crypto/Mac', 'HMAC'),
            (r'Ljava/security/Signature', 'Digital Signature'),
            (r'Ljavax/crypto/spec/SecretKeySpec', 'Secret Key'),
            (r'Lorg/bouncycastle', 'BouncyCastle'),
            (r'Lcom/google/crypto/tink', 'Google Tink'),
        ]

        results = []
        for smali_file in decompiled.rglob("*.smali"):
            content = smali_file.read_text(errors='ignore')
            for pattern, name in encryption_patterns:
                if re.search(pattern, content):
                    results.append({
                        "type": name,
                        "file": str(smali_file.relative_to(decompiled)),
                    })

        return results

    def find_secrets(self) -> List[Dict]:
        """查找硬编码密钥"""

        decompiled = self.output_dir / "decompiled"

        secret_patterns = [
            (r'["\']([A-Za-z0-9+/]{32,}={0,2})["\']', 'Base64 Key'),
            (r'["\']([a-f0-9]{32})["\']', 'MD5 Hash'),
            (r'["\']([a-f0-9]{64})["\']', 'SHA256 Hash'),
            (r'(?:api[_-]?key|apikey)["\s:=]+["\']([^"\']+)["\']', 'API Key'),
            (r'(?:secret|password|passwd)["\s:=]+["\']([^"\']+)["\']', 'Secret'),
        ]

        secrets = []
        for smali_file in decompiled.rglob("*.smali"):
            content = smali_file.read_text(errors='ignore')
            for pattern, secret_type in secret_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if len(match) > 8:  # 过滤太短的
                        secrets.append({
                            "type": secret_type,
                            "value": match[:50] + "..." if len(match) > 50 else match,
                            "file": str(smali_file.relative_to(decompiled)),
                        })

        return secrets

    def get_native_libs(self) -> List[str]:
        """获取 Native 库列表"""

        import zipfile

        libs = []
        with zipfile.ZipFile(self.apk_path, 'r') as z:
            for name in z.namelist():
                if name.startswith('lib/') and name.endswith('.so'):
                    libs.append(name)

        return libs

    def get_activities(self) -> List[str]:
        """获取 Activity 列表"""
        # 从 AndroidManifest.xml 解析
        decompiled = self.output_dir / "decompiled"
        if not decompiled.exists():
            self.decompile()

        manifest = decompiled / "AndroidManifest.xml"
        content = manifest.read_text()

        activities = re.findall(r'android:name="([^"]+)"', content)
        return [a for a in activities if 'Activity' in a or a.startswith('.')]

    def get_services(self) -> List[str]:
        """获取 Service 列表"""
        decompiled = self.output_dir / "decompiled"
        manifest = decompiled / "AndroidManifest.xml"
        content = manifest.read_text()

        services = []
        in_service = False
        for line in content.split('\n'):
            if '<service' in line:
                in_service = True
            if in_service and 'android:name=' in line:
                match = re.search(r'android:name="([^"]+)"', line)
                if match:
                    services.append(match.group(1))
                in_service = False

        return services

    def get_receivers(self) -> List[str]:
        """获取 Receiver 列表"""
        decompiled = self.output_dir / "decompiled"
        manifest = decompiled / "AndroidManifest.xml"
        content = manifest.read_text()

        receivers = []
        in_receiver = False
        for line in content.split('\n'):
            if '<receiver' in line:
                in_receiver = True
            if in_receiver and 'android:name=' in line:
                match = re.search(r'android:name="([^"]+)"', line)
                if match:
                    receivers.append(match.group(1))
                in_receiver = False

        return receivers
```

---

## Frida 动态分析

### 基础 Hook

```python
"""
Frida 动态分析工具集
"""

import frida
from typing import Callable, Optional
import json


class FridaHooker:
    """Frida Hook 管理器"""

    def __init__(self, package_name: str, device: str = "usb"):
        self.package_name = package_name

        if device == "usb":
            self.device = frida.get_usb_device()
        else:
            self.device = frida.get_device(device)

        self.session = None
        self.script = None

    def spawn_and_attach(self):
        """启动并附加"""
        pid = self.device.spawn([self.package_name])
        self.session = self.device.attach(pid)
        self.device.resume(pid)
        return self

    def attach(self):
        """附加到运行中的进程"""
        self.session = self.device.attach(self.package_name)
        return self

    def inject(self, script_code: str, on_message: Optional[Callable] = None):
        """注入脚本"""
        self.script = self.session.create_script(script_code)

        def default_handler(message, data):
            if message['type'] == 'send':
                print(f"[*] {message['payload']}")
            elif message['type'] == 'error':
                print(f"[!] {message['stack']}")

        self.script.on('message', on_message or default_handler)
        self.script.load()
        return self

    def detach(self):
        """断开连接"""
        if self.session:
            self.session.detach()


# 常用 Hook 脚本

HOOK_CRYPTO = """
'use strict';

Java.perform(function() {
    console.log('[*] Crypto Hook loaded');

    // Hook Cipher
    var Cipher = Java.use('javax.crypto.Cipher');

    Cipher.getInstance.overload('java.lang.String').implementation = function(transformation) {
        console.log('[Cipher] Algorithm: ' + transformation);
        return this.getInstance(transformation);
    };

    Cipher.init.overload('int', 'java.security.Key').implementation = function(opmode, key) {
        var mode = opmode == 1 ? 'ENCRYPT' : 'DECRYPT';
        console.log('[Cipher] Mode: ' + mode);

        var keyBytes = key.getEncoded();
        console.log('[Cipher] Key: ' + bytesToHex(keyBytes));

        return this.init(opmode, key);
    };

    Cipher.doFinal.overload('[B').implementation = function(input) {
        console.log('[Cipher] Input: ' + bytesToHex(input));
        var result = this.doFinal(input);
        console.log('[Cipher] Output: ' + bytesToHex(result));
        return result;
    };

    // Hook MessageDigest
    var MessageDigest = Java.use('java.security.MessageDigest');

    MessageDigest.getInstance.overload('java.lang.String').implementation = function(algorithm) {
        console.log('[Hash] Algorithm: ' + algorithm);
        return this.getInstance(algorithm);
    };

    MessageDigest.digest.overload('[B').implementation = function(input) {
        console.log('[Hash] Input: ' + bytesToHex(input));
        console.log('[Hash] Input (String): ' + bytesToString(input));
        var result = this.digest(input);
        console.log('[Hash] Output: ' + bytesToHex(result));
        return result;
    };

    // Hook Mac (HMAC)
    var Mac = Java.use('javax.crypto.Mac');

    Mac.getInstance.overload('java.lang.String').implementation = function(algorithm) {
        console.log('[HMAC] Algorithm: ' + algorithm);
        return this.getInstance(algorithm);
    };

    Mac.init.overload('java.security.Key').implementation = function(key) {
        console.log('[HMAC] Key: ' + bytesToHex(key.getEncoded()));
        return this.init(key);
    };

    Mac.doFinal.overload('[B').implementation = function(input) {
        console.log('[HMAC] Input: ' + bytesToHex(input));
        var result = this.doFinal(input);
        console.log('[HMAC] Output: ' + bytesToHex(result));
        return result;
    };

    // 辅助函数
    function bytesToHex(bytes) {
        var hex = '';
        for (var i = 0; i < bytes.length; i++) {
            hex += ('0' + (bytes[i] & 0xFF).toString(16)).slice(-2);
        }
        return hex;
    }

    function bytesToString(bytes) {
        var result = '';
        for (var i = 0; i < bytes.length; i++) {
            result += String.fromCharCode(bytes[i] & 0xFF);
        }
        return result;
    }
});
"""


HOOK_HTTP = """
'use strict';

Java.perform(function() {
    console.log('[*] HTTP Hook loaded');

    // Hook OkHttp3 Request
    try {
        var Request = Java.use('okhttp3.Request');
        var Buffer = Java.use('okio.Buffer');

        var RealCall = Java.use('okhttp3.RealCall');
        RealCall.execute.implementation = function() {
            var request = this.request();
            console.log('\\n[OkHttp] ========== Request ==========');
            console.log('[OkHttp] URL: ' + request.url().toString());
            console.log('[OkHttp] Method: ' + request.method());

            // 打印 Headers
            var headers = request.headers();
            for (var i = 0; i < headers.size(); i++) {
                console.log('[OkHttp] Header: ' + headers.name(i) + ': ' + headers.value(i));
            }

            // 打印 Body
            var body = request.body();
            if (body != null) {
                var buffer = Buffer.$new();
                body.writeTo(buffer);
                console.log('[OkHttp] Body: ' + buffer.readUtf8());
            }

            var response = this.execute();

            console.log('[OkHttp] ========== Response ==========');
            console.log('[OkHttp] Code: ' + response.code());

            return response;
        };
    } catch (e) {
        console.log('[-] OkHttp3 hook failed: ' + e);
    }

    // Hook HttpURLConnection
    try {
        var HttpURLConnection = Java.use('java.net.HttpURLConnection');

        HttpURLConnection.getInputStream.implementation = function() {
            console.log('[HttpURLConnection] URL: ' + this.getURL().toString());
            return this.getInputStream();
        };
    } catch (e) {
        console.log('[-] HttpURLConnection hook failed');
    }
});
"""


HOOK_JSON = """
'use strict';

Java.perform(function() {
    console.log('[*] JSON Hook loaded');

    // Hook JSONObject
    var JSONObject = Java.use('org.json.JSONObject');

    JSONObject.$init.overload('java.lang.String').implementation = function(json) {
        console.log('[JSONObject] Parse: ' + json.substring(0, Math.min(500, json.length)));
        return this.$init(json);
    };

    JSONObject.toString.implementation = function() {
        var result = this.toString();
        console.log('[JSONObject] ToString: ' + result.substring(0, Math.min(500, result.length)));
        return result;
    };

    // Hook Gson
    try {
        var Gson = Java.use('com.google.gson.Gson');

        Gson.toJson.overload('java.lang.Object').implementation = function(obj) {
            var result = this.toJson(obj);
            console.log('[Gson] toJson: ' + result.substring(0, Math.min(500, result.length)));
            return result;
        };

        Gson.fromJson.overload('java.lang.String', 'java.lang.Class').implementation = function(json, clazz) {
            console.log('[Gson] fromJson: ' + json.substring(0, Math.min(500, json.length)));
            return this.fromJson(json, clazz);
        };
    } catch (e) {
        console.log('[-] Gson not found');
    }
});
"""


HOOK_SIGNATURE = """
'use strict';

Java.perform(function() {
    console.log('[*] Signature Hook loaded');

    // 追踪所有包含 sign/signature 的方法调用
    Java.enumerateLoadedClasses({
        onMatch: function(className) {
            if (className.includes('sign') || className.includes('Sign') ||
                className.includes('encrypt') || className.includes('Encrypt')) {

                try {
                    var clazz = Java.use(className);
                    var methods = clazz.class.getDeclaredMethods();

                    methods.forEach(function(method) {
                        var methodName = method.getName();

                        try {
                            // Hook 所有方法
                            clazz[methodName].overloads.forEach(function(overload) {
                                overload.implementation = function() {
                                    console.log('\\n[Sign] ' + className + '.' + methodName);
                                    console.log('[Sign] Args: ' + JSON.stringify(arguments));

                                    var result = this[methodName].apply(this, arguments);
                                    console.log('[Sign] Return: ' + result);

                                    return result;
                                };
                            });
                        } catch (e) {}
                    });
                } catch (e) {}
            }
        },
        onComplete: function() {
            console.log('[*] Signature method scan complete');
        }
    });
});
"""
```

### Native Hook

```javascript
// native_hook.js - Hook Native 库函数

'use strict';

// Hook libc 函数
Interceptor.attach(Module.findExportByName("libc.so", "open"), {
    onEnter: function(args) {
        this.path = args[0].readUtf8String();
        console.log("[open] " + this.path);
    },
    onLeave: function(retval) {
        console.log("[open] fd: " + retval);
    }
});

// Hook libssl
var SSL_write = Module.findExportByName("libssl.so", "SSL_write");
if (SSL_write) {
    Interceptor.attach(SSL_write, {
        onEnter: function(args) {
            var data = args[1].readByteArray(args[2].toInt32());
            console.log("[SSL_write] " + hexdump(data, { length: Math.min(256, args[2].toInt32()) }));
        }
    });
}

var SSL_read = Module.findExportByName("libssl.so", "SSL_read");
if (SSL_read) {
    Interceptor.attach(SSL_read, {
        onLeave: function(retval) {
            if (retval.toInt32() > 0) {
                var data = this.context.x1.readByteArray(retval.toInt32());
                console.log("[SSL_read] " + hexdump(data, { length: Math.min(256, retval.toInt32()) }));
            }
        }
    });
}

// Hook 自定义 so 库
var targetLib = "libexample.so";
var targetFunc = "Java_com_example_Native_sign";

var funcAddr = Module.findExportByName(targetLib, targetFunc);
if (funcAddr) {
    Interceptor.attach(funcAddr, {
        onEnter: function(args) {
            console.log("[Native] " + targetFunc + " called");
            // JNI 函数参数: args[0] = JNIEnv*, args[1] = jobject, args[2...] = 实际参数

            // 读取 Java String 参数
            var jstring = args[2];
            var JNIEnv = Java.vm.getEnv();
            var str = JNIEnv.getStringUtfChars(jstring, null).readUtf8String();
            console.log("[Native] Input: " + str);
        },
        onLeave: function(retval) {
            // 读取返回的 Java String
            var JNIEnv = Java.vm.getEnv();
            var result = JNIEnv.getStringUtfChars(retval, null).readUtf8String();
            console.log("[Native] Output: " + result);
        }
    });
}

// 枚举所有导出函数
console.log("\\n[*] Exported functions in " + targetLib + ":");
Module.enumerateExports(targetLib, {
    onMatch: function(exp) {
        console.log("  " + exp.type + " " + exp.name + " @ " + exp.address);
    },
    onComplete: function() {}
});
```

---

## iOS 逆向

### 工具链

```bash
# 1. class-dump - 导出 Objective-C 头文件
# 下载: https://github.com/nygard/class-dump
class-dump -H Example.app -o headers/

# 2. Hopper Disassembler - 反汇编 (商业)
# 或使用 Ghidra (免费)

# 3. IDA Pro - 逆向 (商业)
# 或使用 Binary Ninja

# 4. Frida - 动态分析
frida -U -f com.example.app -l script.js

# 5. Objection
objection -g com.example.app explore
```

### iOS Frida Hook

```javascript
// ios_hook.js

'use strict';

// Hook Objective-C 方法
if (ObjC.available) {
    console.log('[*] iOS Hook loaded');

    // Hook NSURLSession
    var NSURLSession = ObjC.classes.NSURLSession;

    Interceptor.attach(NSURLSession['- dataTaskWithRequest:completionHandler:'].implementation, {
        onEnter: function(args) {
            var request = ObjC.Object(args[2]);
            console.log('[NSURLSession] URL: ' + request.URL().absoluteString());
            console.log('[NSURLSession] Method: ' + request.HTTPMethod());

            var headers = request.allHTTPHeaderFields();
            if (headers) {
                console.log('[NSURLSession] Headers: ' + headers.description());
            }

            var body = request.HTTPBody();
            if (body) {
                var bodyStr = ObjC.classes.NSString.alloc().initWithData_encoding_(body, 4); // NSUTF8StringEncoding
                console.log('[NSURLSession] Body: ' + bodyStr);
            }
        }
    });

    // Hook 加密相关
    var CCCrypt = Module.findExportByName('libcommonCrypto.dylib', 'CCCrypt');
    if (CCCrypt) {
        Interceptor.attach(CCCrypt, {
            onEnter: function(args) {
                this.operation = args[0].toInt32() === 0 ? 'Encrypt' : 'Decrypt';
                this.algorithm = ['AES128', 'DES', '3DES', 'CAST', 'RC4', 'RC2', 'Blowfish'][args[1].toInt32()];
                this.keyLength = args[4].toInt32();
                this.dataLength = args[6].toInt32();

                console.log('[CCCrypt] ' + this.operation + ' with ' + this.algorithm);
                console.log('[CCCrypt] Key (' + this.keyLength + ' bytes): ' + hexdump(args[3], { length: this.keyLength }));
                console.log('[CCCrypt] Data (' + this.dataLength + ' bytes): ' + hexdump(args[5], { length: Math.min(64, this.dataLength) }));
            },
            onLeave: function(retval) {
                if (retval.toInt32() === 0) { // kCCSuccess
                    console.log('[CCCrypt] Success');
                }
            }
        });
    }

    // Hook Keychain
    var SecItemCopyMatching = Module.findExportByName('Security', 'SecItemCopyMatching');
    if (SecItemCopyMatching) {
        Interceptor.attach(SecItemCopyMatching, {
            onEnter: function(args) {
                var query = ObjC.Object(args[0]);
                console.log('[Keychain] Query: ' + query.description());
            },
            onLeave: function(retval) {
                if (retval.toInt32() === 0) { // errSecSuccess
                    console.log('[Keychain] Item found');
                }
            }
        });
    }

    // Hook UserDefaults
    var NSUserDefaults = ObjC.classes.NSUserDefaults;

    Interceptor.attach(NSUserDefaults['- objectForKey:'].implementation, {
        onEnter: function(args) {
            this.key = ObjC.Object(args[2]).toString();
        },
        onLeave: function(retval) {
            var value = ObjC.Object(retval);
            if (value) {
                console.log('[UserDefaults] Get: ' + this.key + ' = ' + value.description());
            }
        }
    });

    Interceptor.attach(NSUserDefaults['- setObject:forKey:'].implementation, {
        onEnter: function(args) {
            var value = ObjC.Object(args[2]);
            var key = ObjC.Object(args[3]);
            console.log('[UserDefaults] Set: ' + key + ' = ' + value.description());
        }
    });

} else {
    console.log('[-] Objective-C runtime not available');
}
```

---

## 模拟器自动化

### Appium 自动化

```python
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class AppiumAutomation:
    """Appium 移动端自动化"""

    def __init__(self, package_name: str, activity_name: str):
        self.package_name = package_name
        self.activity_name = activity_name
        self.driver = None

    def connect(self, device_name: str = "emulator-5554"):
        """连接设备"""

        options = UiAutomator2Options()
        options.platform_name = "Android"
        options.device_name = device_name
        options.app_package = self.package_name
        options.app_activity = self.activity_name
        options.no_reset = True
        options.new_command_timeout = 300

        self.driver = webdriver.Remote(
            command_executor='http://localhost:4723',
            options=options
        )

        return self

    def wait_for_element(self, locator, timeout=10):
        """等待元素"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(locator)
        )

    def click(self, resource_id: str):
        """点击元素"""
        element = self.wait_for_element((AppiumBy.ID, f"{self.package_name}:id/{resource_id}"))
        element.click()

    def input_text(self, resource_id: str, text: str):
        """输入文本"""
        element = self.wait_for_element((AppiumBy.ID, f"{self.package_name}:id/{resource_id}"))
        element.clear()
        element.send_keys(text)

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500):
        """滑动"""
        self.driver.swipe(start_x, start_y, end_x, end_y, duration)

    def scroll_down(self):
        """向下滚动"""
        size = self.driver.get_window_size()
        self.swipe(
            size['width'] // 2,
            size['height'] * 3 // 4,
            size['width'] // 2,
            size['height'] // 4
        )

    def get_page_source(self) -> str:
        """获取页面源码"""
        return self.driver.page_source

    def screenshot(self, filename: str):
        """截图"""
        self.driver.save_screenshot(filename)

    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.quit()


# 使用示例
def scrape_app_data():
    """抓取 APP 数据"""

    app = AppiumAutomation(
        package_name="com.example.app",
        activity_name=".MainActivity"
    )

    try:
        app.connect()

        # 登录
        app.input_text("username", "user123")
        app.input_text("password", "pass123")
        app.click("login_button")

        # 等待加载
        import time
        time.sleep(3)

        # 滚动并抓取数据
        for i in range(5):
            page_source = app.get_page_source()
            # 解析 XML 获取数据
            # ...
            app.scroll_down()
            time.sleep(1)

    finally:
        app.close()
```

### ADB 自动化

```python
import subprocess
from typing import List, Tuple
import time


class ADBAutomation:
    """ADB 自动化"""

    def __init__(self, device_id: str = None):
        self.device_id = device_id
        self.adb_prefix = ["adb"]
        if device_id:
            self.adb_prefix = ["adb", "-s", device_id]

    def execute(self, command: List[str]) -> str:
        """执行 ADB 命令"""
        result = subprocess.run(
            self.adb_prefix + command,
            capture_output=True,
            text=True
        )
        return result.stdout

    def shell(self, command: str) -> str:
        """执行 Shell 命令"""
        return self.execute(["shell", command])

    def tap(self, x: int, y: int):
        """点击坐标"""
        self.shell(f"input tap {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 500):
        """滑动"""
        self.shell(f"input swipe {x1} {y1} {x2} {y2} {duration}")

    def input_text(self, text: str):
        """输入文本"""
        # 需要处理特殊字符
        escaped = text.replace(" ", "%s").replace("'", "\\'")
        self.shell(f"input text '{escaped}'")

    def keyevent(self, keycode: int):
        """发送按键事件"""
        self.shell(f"input keyevent {keycode}")

    def back(self):
        """返回键"""
        self.keyevent(4)

    def home(self):
        """Home 键"""
        self.keyevent(3)

    def screenshot(self, local_path: str):
        """截图"""
        remote_path = "/sdcard/screenshot.png"
        self.shell(f"screencap -p {remote_path}")
        self.execute(["pull", remote_path, local_path])
        self.shell(f"rm {remote_path}")

    def get_current_activity(self) -> str:
        """获取当前 Activity"""
        result = self.shell("dumpsys activity activities | grep mResumedActivity")
        return result.strip()

    def start_app(self, package: str, activity: str):
        """启动应用"""
        self.shell(f"am start -n {package}/{activity}")

    def stop_app(self, package: str):
        """停止应用"""
        self.shell(f"am force-stop {package}")

    def install_apk(self, apk_path: str):
        """安装 APK"""
        self.execute(["install", "-r", apk_path])

    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        result = self.shell("wm size")
        # 输出格式: Physical size: 1080x1920
        match = result.strip().split(": ")[-1]
        width, height = map(int, match.split("x"))
        return width, height


# 使用示例
def automated_scraping():
    """自动化抓取"""

    adb = ADBAutomation()

    # 启动应用
    adb.start_app("com.example.app", ".MainActivity")
    time.sleep(3)

    # 获取屏幕尺寸
    width, height = adb.get_screen_size()

    # 滚动抓取
    for i in range(10):
        # 截图
        adb.screenshot(f"page_{i}.png")

        # 向下滑动
        adb.swipe(
            width // 2, height * 3 // 4,
            width // 2, height // 4,
            duration=300
        )
        time.sleep(1)
```

---

## 设备指纹

### Android 设备指纹

```python
from dataclasses import dataclass
from typing import Optional
import random
import hashlib


@dataclass
class AndroidDeviceFingerprint:
    """Android 设备指纹"""

    # 设备标识
    android_id: str
    imei: str  # 现在很难获取
    device_id: str

    # 硬件信息
    brand: str
    model: str
    manufacturer: str
    product: str
    device: str
    board: str
    hardware: str

    # 系统信息
    android_version: str
    sdk_int: int
    build_id: str
    build_fingerprint: str

    # 屏幕
    screen_width: int
    screen_height: int
    screen_density: int

    # 网络
    wifi_mac: str  # 现在返回随机值
    bluetooth_mac: str

    # SIM
    operator: str
    sim_serial: str


class AndroidFingerprintGenerator:
    """Android 指纹生成器"""

    # 真实设备数据
    DEVICES = [
        {
            "brand": "Xiaomi",
            "model": "Redmi Note 12",
            "manufacturer": "Xiaomi",
            "product": "sunstone",
            "device": "sunstone",
            "board": "sunstone",
            "hardware": "qcom",
            "android_versions": ["12", "13"],
            "screen": (1080, 2400, 440),
        },
        {
            "brand": "HUAWEI",
            "model": "P40 Pro",
            "manufacturer": "HUAWEI",
            "product": "ELS-AN00",
            "device": "HWELS",
            "board": "ELS",
            "hardware": "kirin990",
            "android_versions": ["10", "11", "12"],
            "screen": (1200, 2640, 441),
        },
        {
            "brand": "OPPO",
            "model": "Find X5",
            "manufacturer": "OPPO",
            "product": "PFFM10",
            "device": "OP5261",
            "board": "lahaina",
            "hardware": "qcom",
            "android_versions": ["12", "13"],
            "screen": (1080, 2400, 440),
        },
        {
            "brand": "vivo",
            "model": "X80",
            "manufacturer": "vivo",
            "product": "PD2186",
            "device": "PD2186",
            "board": "lahaina",
            "hardware": "qcom",
            "android_versions": ["12", "13"],
            "screen": (1080, 2400, 398),
        },
        {
            "brand": "samsung",
            "model": "SM-S9080",
            "manufacturer": "samsung",
            "product": "r0sxxx",
            "device": "r0s",
            "board": "s5e9925",
            "hardware": "exynos",
            "android_versions": ["12", "13", "14"],
            "screen": (1440, 3088, 500),
        },
    ]

    # 运营商
    OPERATORS = [
        ("46000", "中国移动"),
        ("46001", "中国联通"),
        ("46003", "中国电信"),
    ]

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def generate(self) -> AndroidDeviceFingerprint:
        """生成设备指纹"""

        device_template = self.rng.choice(self.DEVICES)
        android_version = self.rng.choice(device_template["android_versions"])
        operator_code, operator_name = self.rng.choice(self.OPERATORS)

        # 生成各种 ID
        android_id = self._generate_android_id()
        device_id = self._generate_device_id()
        build_id = self._generate_build_id(android_version)

        # SDK 版本映射
        sdk_map = {"10": 29, "11": 30, "12": 31, "13": 33, "14": 34}
        sdk_int = sdk_map.get(android_version, 31)

        # Build fingerprint
        build_fingerprint = (
            f"{device_template['brand']}/{device_template['product']}/"
            f"{device_template['device']}:{android_version}/{build_id}/"
            f"{self._generate_build_number()}:user/release-keys"
        )

        return AndroidDeviceFingerprint(
            android_id=android_id,
            imei=self._generate_imei(),
            device_id=device_id,
            brand=device_template["brand"],
            model=device_template["model"],
            manufacturer=device_template["manufacturer"],
            product=device_template["product"],
            device=device_template["device"],
            board=device_template["board"],
            hardware=device_template["hardware"],
            android_version=android_version,
            sdk_int=sdk_int,
            build_id=build_id,
            build_fingerprint=build_fingerprint,
            screen_width=device_template["screen"][0],
            screen_height=device_template["screen"][1],
            screen_density=device_template["screen"][2],
            wifi_mac=self._generate_mac(),
            bluetooth_mac=self._generate_mac(),
            operator=operator_code,
            sim_serial=self._generate_sim_serial(),
        )

    def _generate_android_id(self) -> str:
        """生成 Android ID (16位十六进制)"""
        return ''.join(self.rng.choices('0123456789abcdef', k=16))

    def _generate_device_id(self) -> str:
        """生成设备 ID"""
        return ''.join(self.rng.choices('0123456789abcdef', k=16))

    def _generate_imei(self) -> str:
        """生成 IMEI (15位数字)"""
        # TAC (8位) + Serial (6位) + Check (1位)
        tac = ''.join(self.rng.choices('0123456789', k=8))
        serial = ''.join(self.rng.choices('0123456789', k=6))
        # Luhn 校验位
        imei_without_check = tac + serial
        check = self._luhn_checksum(imei_without_check)
        return imei_without_check + str(check)

    def _luhn_checksum(self, number: str) -> int:
        """Luhn 校验算法"""
        digits = [int(d) for d in number]
        odd_sum = sum(digits[-1::-2])
        even_sum = sum(sum(divmod(2 * d, 10)) for d in digits[-2::-2])
        return (10 - (odd_sum + even_sum) % 10) % 10

    def _generate_mac(self) -> str:
        """生成 MAC 地址"""
        mac = [self.rng.randint(0, 255) for _ in range(6)]
        mac[0] = (mac[0] & 0xfe) | 0x02  # 本地管理地址
        return ':'.join(f'{b:02x}' for b in mac)

    def _generate_build_id(self, android_version: str) -> str:
        """生成 Build ID"""
        prefixes = {
            "10": "QKQ1",
            "11": "RKQ1",
            "12": "SKQ1",
            "13": "TKQ1",
            "14": "UP1A",
        }
        prefix = prefixes.get(android_version, "SKQ1")
        suffix = ''.join(self.rng.choices('0123456789', k=6))
        return f"{prefix}.{suffix}.001"

    def _generate_build_number(self) -> str:
        """生成 Build Number"""
        return ''.join(self.rng.choices('0123456789', k=10))

    def _generate_sim_serial(self) -> str:
        """生成 SIM 序列号 (20位)"""
        return ''.join(self.rng.choices('0123456789', k=20))
```

### Frida 注入设备指纹

```javascript
// inject_device_fingerprint.js

'use strict';

const fingerprint = {
    android_id: '${android_id}',
    device_id: '${device_id}',
    brand: '${brand}',
    model: '${model}',
    manufacturer: '${manufacturer}',
    android_version: '${android_version}',
    sdk_int: ${sdk_int},
    build_fingerprint: '${build_fingerprint}',
};

Java.perform(function() {
    console.log('[*] Device Fingerprint Injection');

    // Hook Settings.Secure.getString
    var Settings = Java.use('android.provider.Settings$Secure');
    Settings.getString.implementation = function(resolver, name) {
        if (name === 'android_id') {
            console.log('[Settings] android_id -> ' + fingerprint.android_id);
            return fingerprint.android_id;
        }
        return this.getString(resolver, name);
    };

    // Hook Build 类
    var Build = Java.use('android.os.Build');

    // 字段替换
    Build.BRAND.value = fingerprint.brand;
    Build.MODEL.value = fingerprint.model;
    Build.MANUFACTURER.value = fingerprint.manufacturer;
    Build.FINGERPRINT.value = fingerprint.build_fingerprint;

    var VERSION = Java.use('android.os.Build$VERSION');
    VERSION.RELEASE.value = fingerprint.android_version;
    VERSION.SDK_INT.value = fingerprint.sdk_int;

    // Hook TelephonyManager
    var TelephonyManager = Java.use('android.telephony.TelephonyManager');

    TelephonyManager.getDeviceId.overload().implementation = function() {
        console.log('[TelephonyManager] getDeviceId -> ' + fingerprint.device_id);
        return fingerprint.device_id;
    };

    TelephonyManager.getImei.overload().implementation = function() {
        console.log('[TelephonyManager] getImei -> ' + fingerprint.device_id);
        return fingerprint.device_id;
    };

    // Hook WifiInfo
    try {
        var WifiInfo = Java.use('android.net.wifi.WifiInfo');
        WifiInfo.getMacAddress.implementation = function() {
            console.log('[WifiInfo] getMacAddress -> 02:00:00:00:00:00');
            return '02:00:00:00:00:00';
        };
    } catch(e) {}

    console.log('[*] Device fingerprint injection complete');
});
```

---

## 请求复现

### 从抓包数据生成代码

```python
import json
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse, parse_qs


class RequestReplicator:
    """请求复现器"""

    def __init__(self, capture_file: str):
        with open(capture_file, 'r', encoding='utf-8') as f:
            self.captures = json.load(f)

    def analyze_requests(self) -> Dict:
        """分析捕获的请求"""

        analysis = {
            "endpoints": {},
            "auth_headers": [],
            "signing_params": [],
        }

        for req in self.captures:
            url = req["url"]
            parsed = urlparse(url)
            endpoint = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

            if endpoint not in analysis["endpoints"]:
                analysis["endpoints"][endpoint] = {
                    "method": req["method"],
                    "count": 0,
                    "sample_headers": req["headers"],
                    "sample_params": parse_qs(parsed.query),
                }

            analysis["endpoints"][endpoint]["count"] += 1

            # 识别认证头
            for header, value in req["headers"].items():
                header_lower = header.lower()
                if any(k in header_lower for k in ["auth", "token", "cookie", "sign"]):
                    if header not in analysis["auth_headers"]:
                        analysis["auth_headers"].append(header)

            # 识别签名参数
            params = parse_qs(parsed.query)
            for param in params.keys():
                if any(k in param.lower() for k in ["sign", "token", "timestamp", "nonce"]):
                    if param not in analysis["signing_params"]:
                        analysis["signing_params"].append(param)

        return analysis

    def generate_python_code(self, endpoint: str) -> str:
        """生成 Python 请求代码"""

        # 找到对应的请求
        req = None
        for r in self.captures:
            if endpoint in r["url"]:
                req = r
                break

        if not req:
            return "# 未找到匹配的请求"

        code = '''
import httpx

url = "{url}"

headers = {headers}

{body_code}

response = httpx.{method}(
    url,
    headers=headers,
    {body_param}
)

print(response.status_code)
print(response.json())
'''.format(
            url=req["url"],
            headers=json.dumps(req["headers"], indent=4, ensure_ascii=False),
            method=req["method"].lower(),
            body_code=f'data = {json.dumps(req.get("body", {}), indent=4, ensure_ascii=False)}' if req.get("body") else '# No body',
            body_param='data=data' if req.get("body") else ''
        )

        return code

    def generate_curl(self, endpoint: str) -> str:
        """生成 cURL 命令"""

        req = None
        for r in self.captures:
            if endpoint in r["url"]:
                req = r
                break

        if not req:
            return "# 未找到匹配的请求"

        curl_parts = [f'curl -X {req["method"]}']

        # Headers
        for header, value in req["headers"].items():
            curl_parts.append(f"  -H '{header}: {value}'")

        # Body
        if req.get("body"):
            curl_parts.append(f"  -d '{req['body']}'")

        curl_parts.append(f"  '{req['url']}'")

        return " \\\n".join(curl_parts)


# 使用示例
def replicate_from_capture():
    """从抓包复现请求"""

    replicator = RequestReplicator("captures/capture_20240101.json")

    # 分析
    analysis = replicator.analyze_requests()
    print("发现的端点:")
    for endpoint, info in analysis["endpoints"].items():
        print(f"  {info['method']} {endpoint} ({info['count']}次)")

    print(f"\n认证头: {analysis['auth_headers']}")
    print(f"签名参数: {analysis['signing_params']}")

    # 生成代码
    code = replicator.generate_python_code("api.example.com/v1/products")
    print("\n生成的 Python 代码:")
    print(code)
```

---

## 诊断日志

```
# 环境准备
[MOBILE_ENV] 设备连接: {device_id}
[MOBILE_ENV] 平台: {platform} (Android/iOS)
[MOBILE_ENV] 系统版本: {os_version}
[MOBILE_ENV] Root/越狱状态: {rooted}

# 流量捕获
[CAPTURE] mitmproxy启动: 端口={port}
[CAPTURE] 证书安装: {cert_status}
[CAPTURE] 捕获请求: {method} {url}
[CAPTURE] 请求头: {headers}
[CAPTURE] 请求体: {body}

# SSL Pinning
[SSL_PIN] 检测到SSL Pinning: {app_package}
[SSL_PIN] 绕过方法: {method} (Frida/Objection)
[SSL_PIN] 绕过结果: {success}

# APK分析
[APK] 解包: {apk_path}
[APK] 包名: {package_name}, 版本: {version}
[APK] 发现API端点: {endpoints}
[APK] 发现加密方法: {encryption_methods}
[APK] 发现密钥: {secrets}

# Frida Hook
[FRIDA] 附加进程: {package_name}, PID={pid}
[FRIDA] Hook类: {class_name}.{method_name}
[FRIDA] 捕获参数: {arguments}
[FRIDA] 捕获返回: {return_value}

# 设备指纹
[DEVICE_FP] 生成设备指纹: {device_id}
[DEVICE_FP] 品牌: {brand}, 型号: {model}
[DEVICE_FP] Android ID: {android_id}

# 自动化
[AUTO] Appium连接: {device}
[AUTO] 操作: {action} @ {element}
[AUTO] 截图: {screenshot_path}

# 错误情况
[CAPTURE] ERROR: 证书安装失败: {error}
[SSL_PIN] ERROR: 绕过失败: {error}
[FRIDA] ERROR: Hook失败: {error}
[AUTO] ERROR: 元素未找到: {selector}
```

---

## 策略协调

移动端逆向策略参考 [16-战术决策模块](16-tactics.md)：
- **抓包失败** → 尝试不同 SSL Pinning 绕过方法
- **Native 加密** → 评估 Frida Hook vs 静态逆向
- **协议复杂** → 考虑自动化抓包而非完全逆向

---

## 相关模块

- **上游**: [09-JS逆向模块](09-js-reverse.md) - Native 逆向方法
- **配合**: [03-签名模块](03-signature.md) - 移动端签名算法
- **配合**: [11-指纹工厂模块](11-fingerprint.md) - 设备指纹生成
- **下游**: [04-请求模块](04-request.md) - 复现请求

---

## 常见问题

### Q: 抓不到 HTTPS 流量？

1. 确认证书已正确安装到系统证书存储
2. 检查应用是否有 SSL Pinning
3. 使用 Frida/Objection 绕过 SSL Pinning
4. 检查应用是否使用了证书透明度检查

### Q: Frida 无法附加进程？

1. 确认设备已 Root/越狱
2. 检查 Frida 服务端版本是否与客户端匹配
3. 确认目标进程正在运行
4. 检查 SELinux 设置（Android）

### Q: 模拟器被检测？

1. 使用真机或高仿模拟器
2. 修改模拟器特征（build.prop 等）
3. 使用 Magisk Hide
4. Hook 检测函数返回假值

### Q: 如何绕过 Root 检测？

1. 使用 Magisk Hide
2. Frida Hook RootBeer 等检测库
3. 修改 su 文件路径
4. Hook 文件检测 API
