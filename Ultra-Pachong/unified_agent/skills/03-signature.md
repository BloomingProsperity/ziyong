---
skill_id: "03-signature"
name: "签名模块"
version: "1.2.0"
status: "stable"                    # draft | beta | stable | deprecated
implementation_status: "partial"    # none | partial | complete
difficulty: 4
category: "core"

description: "加密参数分析与签名生成"

triggers:
  - condition: "request.has_signature == true"
  - pattern: "(签名|加密参数|h5st|sign|逆向)"

dependencies:
  required:
    - skill: "01-reconnaissance"
      reason: "发现签名参数"
      min_version: "1.1.0"
  optional:
    - skill: "09-js-reverse"
      reason: "复杂签名逆向"
      condition: "complexity >= high"
      fallback: "使用RPC方案"
    - skill: "02-anti-detection"
      reason: "环境伪装"
      condition: "enterprise_antibot == true"

external_dependencies:
  required:
    - name: "pycryptodome"
      version: ">=3.19.0"
      type: "python_package"
      install: "pip install pycryptodome"
  optional:
    - name: "js2py"
      version: ">=0.74"
      condition: "Python执行JS"
      type: "python_package"
      install: "pip install js2py"
    - name: "PyExecJS"
      version: ">=1.5.1"
      condition: "Node.js执行"
      type: "python_package"
      install: "pip install PyExecJS"
    - name: "curl_cffi"
      version: ">=0.6.0"
      condition: "TLS指纹伪装(DataDome等)"
      type: "python_package"
      install: "pip install curl_cffi"

inputs:
  - name: "params"
    type: "dict"
    required: true
    description: "待签名的请求参数"
  - name: "sign_type"
    type: "string"
    required: false
    description: "签名类型(oauth1/jwt/aws_v4/custom)"
  - name: "algorithm_impl"
    type: "string"
    required: false
    description: "算法实现代码(来自09-js-reverse)"

outputs:
  - name: "signature"
    type: "string"
    description: "生成的签名字符串"
  - name: "signed_params"
    type: "dict"
    description: "包含签名的完整参数"
  - name: "headers"
    type: "dict"
    description: "需要添加的请求头(如Authorization)"
  - name: "approach"
    type: "enum"
    description: "pure_algo | js_exec | rpc | browser"

slo:
  - metric: "签名生成成功率"
    target: "≥ 95%"
    scope: "标准API签名 (OAuth/JWT/AWS)"
    measurement: "成功生成签名数 / 尝试生成总数"
    degradation:
      - level: 1
        condition: "成功率 < 95%"
        action: "检查密钥配置,切换到JS执行"
      - level: 2
        condition: "成功率 < 80%"
        action: "降级到RPC/浏览器方案"
  - metric: "平台签名成功率"
    target: "≥ 85%"
    scope: "京东/淘宝/抖音/B站等主流平台"
    measurement: "签名验证通过数 / 签名生成总数"
    degradation:
      - level: 1
        condition: "成功率 < 85%"
        action: "调用09-js-reverse更新算法"
      - level: 2
        condition: "成功率 < 70%"
        action: "切换浏览器执行"
  - metric: "企业反爬绕过率"
    target: "≥ 70%"
    scope: "Cloudflare/Akamai/PerimeterX"
    measurement: "请求成功数 / 请求总数"
    degradation:
      - level: 1
        condition: "成功率 < 70%"
        action: "增强TLS指纹伪装+行为模拟"
      - level: 2
        condition: "成功率 < 50%"
        action: "使用真实浏览器+代理池"
  - metric: "签名生成时间"
    target: "< 500ms"
    scope: "纯算法方案"
    degradation:
      - level: 1
        condition: "时间 > 500ms"
        action: "优化算法实现,使用缓存"

enterprise_antibot_matrix:
  - system: "Cloudflare"
    difficulty: 4
    approach: "JS Challenge绕过 + TLS指纹"
  - system: "Akamai"
    difficulty: 5
    approach: "sensor_data逆向 / 真实浏览器"
  - system: "PerimeterX"
    difficulty: 5
    approach: "行为模拟 + 指纹伪装"
  - system: "DataDome"
    difficulty: 4
    approach: "TLS指纹 (curl_cffi)"
  - system: "Kasada"
    difficulty: 5
    approach: "WASM逆向 / PoW计算"
  - system: "Shape/F5"
    difficulty: 5
    approach: "多态JS分析 + 请求签名"

risks:
  - risk: "签名算法更新"
    impact: "现有实现失效,所有请求失败"
    mitigation: "监控签名验证成功率,快速响应更新"
  - risk: "密钥泄露检测"
    impact: "账号被封禁"
    mitigation: "使用账号池,分散风险"
  - risk: "时间同步问题"
    impact: "timestamp类签名验证失败"
    mitigation: "使用NTP同步或从服务器获取时间"

limitations:
  - "不支持需要硬件设备的签名(如USB Key)"
  - "不支持需要人机验证的场景"
  - "不保证签名算法永久有效(可能随时更新)"

tags:
  - "signature"
  - "encryption"
  - "oauth"
  - "jwt"
  - "anti-bot"
---

# 03 - 签名模块 (Signature)

## 模块目标

| 目标 | SLO | 适用范围 | 降级策略 |
|------|-----|----------|----------|
| 签名生成 | 成功率 ≥ 95% | 已知算法 | RPC/浏览器执行 |
| 算法复现 | 主流平台覆盖 | 京东/淘宝/抖音等 | 补环境方案 |
| 方案选择 | 自动选择最优 | 所有场景 | 人工干预 |
| 验证通过 | 通过率 ≥ 95% | 签名后请求 | 重试+换方案 |

---

## 代码实现状态

> **当前状态**: ✅ 核心已实现 (2026-01-28更新)

| 功能模块 | 实现状态 | 代码位置 | 说明 |
|---------|---------|---------|------|
| **核心签名管理器** | ✅ 完整实现 | `unified_agent/core/signature.py` | SignatureManager统一入口 |
| 标准签名(MD5/HMAC) | ✅ 完整实现 | `unified_agent/core/signature.py:207-279` | MD5Generator, HMACGenerator |
| OAuth 1.0签名 | ✅ 完整实现 | `unified_agent/core/signature.py:282-384` | OAuth1Generator完整实现 |
| JWT签名 | ✅ 完整实现 | `unified_agent/core/signature.py:387-441` | JWTGenerator (需要PyJWT库) |
| B站WBI签名 | ✅ 完整实现 | `unified_agent/core/signature.py:447-516` | BilibiliWBIGenerator |
| 自定义JS签名 | ✅ 完整实现 | `unified_agent/core/signature.py:519-567` | CustomJSGenerator (需要js2py) |
| 签名缓存 | ✅ 完整实现 | `unified_agent/core/signature.py:121-195` | SignatureCache (TTL+LRU) |
| 签名类型检测 | ✅ 完整实现 | `unified_agent/core/signature.py:688-717` | detect_signature_type() |
| 签名验证 | ✅ 完整实现 | `unified_agent/core/signature.py:719-738` | verify_signature() |
| 京东H5ST | ❌ 未实现 | `N/A` | 建议使用RPC方案 |
| 抖音X-Bogus | ❌ 未实现 | `N/A` | 建议使用RPC方案 |
| 签名识别器 | ⚠️ 基础实现 | `unified_agent/scraper/smart_analyzer.py` | 可识别常见签名参数 |
| RPC客户端 | ⚠️ 部分实现 | `unified_agent/infra/sign_server.py` | 有基础框架,需完善 |

**快速开始**:
```python
from unified_agent.core.signature import SignatureManager, SignatureRequest, SignType

# 创建签名管理器
manager = SignatureManager()

# MD5签名示例
request = SignatureRequest(
    params={"user_id": "123", "action": "login"},
    sign_type=SignType.MD5,
    credentials={"secret": "my_secret_key"}
)
result = manager.generate(request)
print(result.signature)  # 输出签名

# B站WBI签名示例
request = SignatureRequest(
    params={"mid": "123456", "pn": "1"},
    sign_type=SignType.BILIBILI_WBI,
    credentials={"img_key": "...", "sub_key": "..."}
)
result = manager.generate(request)
print(result.signed_params)  # 包含w_rid的完整参数
```

---

## 接口定义

### 输入

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| params | dict | 是 | - | 待签名的请求参数 |
| sign_type | string | 否 | "auto" | oauth1/oauth2/jwt/aws_v4/custom/auto |
| credentials | dict | 否 | {} | 认证凭据(key/secret/token等) |
| algorithm_impl | string | 否 | null | 算法代码(来自09-js-reverse) |
| options | dict | 否 | {} | 额外选项 |

**credentials 结构**:
```python
{
    # OAuth 1.0
    "consumer_key": "xxx",
    "consumer_secret": "xxx",
    "token": "xxx",
    "token_secret": "xxx",

    # OAuth 2.0
    "access_token": "xxx",

    # JWT
    "secret_key": "xxx",

    # AWS Signature V4
    "access_key": "xxx",
    "secret_key": "xxx",
    "region": "us-east-1",
    "service": "s3",

    # Custom
    "app_key": "xxx",
    "app_secret": "xxx",
}
```

### 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| status | enum | success / partial / failed |
| signature | string | 签名字符串 |
| signed_params | dict | 包含签名的完整参数 |
| headers | dict | 需要添加的请求头 |
| approach | enum | pure_algo / js_exec / rpc / browser |
| metadata | dict | 元数据(版本/时间戳/指纹等) |
| warnings | list[str] | 警告信息 |
| errors | list[str] | 错误列表(可为空) |

### 错误码

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| E_SIG_001 | 未检测到签名参数 | 检查API是否真的需要签名,重新侦查 |
| E_SIG_002 | 签名类型识别失败 | 手动指定sign_type参数 |
| E_SIG_003 | 缺少必要凭据 | 补充credentials(key/secret/token) |
| E_SIG_004 | 算法实现不可用 | 调用09-js-reverse分析算法 |
| E_SIG_005 | 签名验证失败(403) | 检查时间戳/参数顺序/编码格式 |
| E_SIG_006 | 时间戳同步失败 | 使用服务器时间或NTP同步 |
| E_SIG_007 | JS执行超时 | 增加timeout或切换RPC方案 |
| E_SIG_008 | RPC服务不可用 | 启动sign_server或使用浏览器方案 |

---

## Skill 交互

### 上游 (谁调用我)

| Skill | 调用场景 | 传入数据 |
|-------|----------|----------|
| 01-reconnaissance | 检测到签名参数时 | signature_params(参数名列表), api_request |
| 18-brain-controller | 标准任务流程 | params, sign_type(如已知) |
| 04-request | 发送请求前 | params(待签名参数) |

### 下游 (我调用谁)

| Skill | 调用场景 | 传出数据 |
|-------|----------|----------|
| 09-js-reverse | 复杂签名需要逆向时 | js_code(签名JS), target_function |
| 02-anti-detection | 企业反爬系统时 | stealth_config(TLS指纹/Canvas等) |
| 04-request | 签名生成后 | signed_params, headers |

### 调用时序图

```
01-reconnaissance (检测签名)
   │
   ▼
03-signature.detect_type()
   │
   ├─ 标准签名 (OAuth/JWT/AWS)
   │     └─→ 03-signature.generate_standard()
   │           └─→ 返回signed_params
   │
   ├─ 平台签名 (京东/淘宝/B站)
   │     ├─→ 检查是否有算法实现
   │     │     ├─ 有 → execute_algorithm()
   │     │     └─ 无 → 09-js-reverse.analyze()
   │     └─→ 返回signed_params
   │
   └─ 企业反爬 (Cloudflare/Akamai)
         ├─→ 02-anti-detection.prepare()
         ├─→ 选择方案(JS执行/RPC/浏览器)
         └─→ 返回signed_params + headers

04-request (携带签名请求)
   │
   ├─ 成功(200) → 验证通过
   └─ 失败(403) → 08-diagnosis + 重试
```

---

## 模块概述

签名模块负责分析和生成 API 请求所需的加密参数，是应对高等级反爬的核心能力。

```
┌─────────────────────────────────────────────────────────────────┐
│                        签名破解流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │ 参数识别  │───▶│ 特征分析  │───▶│ 算法定位  │───▶│ 方案选择 │ │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│        │               │               │               │       │
│        ▼               ▼               ▼               ▼       │
│  检测加密参数     分析值特征       定位生成代码     选择实现方式  │
│  sign, token    长度、字符集      JS混淆分析      纯算/RPC/AST  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 签名参数识别

### 常见签名参数

```python
SIGNATURE_PARAMS = {
    # === 通用类 ===
    "sign": "通用签名",
    "signature": "通用签名",
    "sig": "通用签名缩写",
    "hash": "哈希签名",
    "token": "访问令牌",
    "auth": "认证参数",

    # === 时间类 ===
    "timestamp": "时间戳",
    "ts": "时间戳缩写",
    "t": "时间戳缩写",
    "time": "时间",
    "_t": "时间戳",

    # === 随机类 ===
    "nonce": "随机数",
    "random": "随机数",
    "r": "随机数缩写",
    "_": "jQuery随机数",

    # === 平台特定 ===
    "h5st": "京东H5签名",
    "x-sign": "阿里系签名",
    "x-mini-wua": "阿里小程序签名",
    "anti-content": "拼多多反爬参数",
    "x-bogus": "抖音签名",
    "a_bogus": "抖音辅助签名",
    "X-s": "小红书签名",
    "X-t": "小红书时间戳",
    "x-s-common": "小红书通用签名",
    "wbi": "B站签名",
    "w_rid": "B站签名",
    "x-zse-96": "知乎签名",
    "x-zse-93": "知乎版本标识",
}
```

---

## 签名特征分析

### SignatureAnalysis 结构

```python
@dataclass
class SignatureAnalysis:
    # 基础信息
    param_name: str           # 参数名
    sample_value: str         # 样本值

    # 格式分析
    length: int               # 长度
    charset: str              # 字符集: hex|base64|alphanumeric|mixed
    has_separator: bool       # 是否有分隔符
    separator: str | None     # 分隔符: _|-|.|;

    # 结构分析
    segments: list[dict]      # 分段信息
    has_timestamp: bool       # 是否含时间戳
    timestamp_format: str     # 时间戳格式: unix_ms|unix_s|custom
    has_nonce: bool           # 是否含随机数

    # 算法评估
    complexity: str           # 复杂度: low|medium|high|extreme
    estimated_algorithm: str  # 预估算法
    confidence: float         # 置信度 0-1

    # 破解建议
    suggested_approach: str   # 建议方案
    reference_links: list     # 参考资料
```

### 字符集识别

```python
def detect_charset(value: str) -> str:
    """识别签名字符集"""
    import re

    if re.match(r'^[0-9a-f]+$', value.lower()):
        return "hex"
    elif re.match(r'^[A-Za-z0-9+/]+=*$', value):
        return "base64"
    elif re.match(r'^[0-9]+$', value):
        return "numeric"
    elif re.match(r'^[A-Za-z0-9]+$', value):
        return "alphanumeric"
    else:
        return "mixed"
```

### 结构分段分析

```python
def analyze_segments(value: str) -> list[dict]:
    """分析签名分段结构"""

    # 常见分隔符
    for sep in ['_', '-', ';', '|', '.']:
        if sep in value:
            parts = value.split(sep)
            return [
                {
                    "index": i,
                    "value": part,
                    "length": len(part),
                    "type": detect_charset(part),
                    "possible_meaning": guess_meaning(part)
                }
                for i, part in enumerate(parts)
            ]

    return [{"index": 0, "value": value, "length": len(value)}]

def guess_meaning(segment: str) -> str:
    """推测分段含义"""
    length = len(segment)

    # 时间戳特征
    if length == 13 and segment.isdigit():
        return "timestamp_ms"
    if length == 10 and segment.isdigit():
        return "timestamp_s"

    # 常见长度
    if length == 32:
        return "md5_hash"
    if length == 40:
        return "sha1_hash"
    if length == 64:
        return "sha256_hash"

    # 短随机数
    if length <= 8 and segment.isalnum():
        return "nonce"

    return "unknown"
```

---

## 主流网站签名解析

### 京东 H5ST

```
签名示例: 20240101120000000;1234567890123;abcdef;a1b2c3d4e5f6...
结构: 时间戳;指纹ID;版本;哈希值
算法: HMAC-SHA256
```

**分析要点**:
```python
H5ST_STRUCTURE = {
    "format": "{timestamp};{fp};{version};{hash}",
    "segments": [
        {"name": "timestamp", "length": 17, "type": "datetime"},
        {"name": "fingerprint", "length": 13, "type": "numeric"},
        {"name": "version", "length": 6, "type": "alphanumeric"},
        {"name": "hash", "length": 64, "type": "hex"},
    ],
    "algorithm": "HMAC-SHA256",
    "key_source": "动态生成，与设备指纹绑定",
    "difficulty": "extreme",
}
```

**破解方案**:
1. AST 反混淆定位签名函数
2. 补环境执行 JS
3. 或使用 Playwright 执行获取

---

### 淘宝/天猫 MTOP

```
签名示例: a1b2c3d4e5f6g7h8
结构: 单段哈希
算法: 自定义 (基于 MD5)
```

**分析要点**:
```python
MTOP_STRUCTURE = {
    "format": "{hash}",
    "params": ["appKey", "t", "api", "v", "data"],
    "algorithm": "自定义MD5变体",
    "key": "从页面获取 appKey",
    "difficulty": "high",
}
```

---

### 抖音 X-Bogus

```
签名示例: DFSzswVOxGsANxYftx3G3C9WKa9e
结构: 单段编码
算法: 自定义 (WASM)
```

**分析要点**:
```python
XBOGUS_STRUCTURE = {
    "format": "{encoded}",
    "length": 28,
    "charset": "alphanumeric",
    "algorithm": "WASM加密",
    "implementation": "bdms.js 中的 WASM 模块",
    "difficulty": "extreme",
}
```

---

### 小红书 X-s

```
签名示例: XYZ123...
结构: Base64编码
算法: 自定义加密
```

**分析要点**:
```python
XS_STRUCTURE = {
    "params": ["X-s", "X-t", "X-s-common"],
    "X-s": {
        "description": "主签名",
        "algorithm": "自定义",
    },
    "X-t": {
        "description": "时间戳",
        "format": "unix_ms",
    },
    "difficulty": "high",
}
```

---

### B站 WBI

```
签名示例: w_rid=a1b2c3d4...&wts=1234567890
结构: MD5(排序参数 + mixin_key)
算法: MD5
```

**分析要点**:
```python
WBI_STRUCTURE = {
    "params": ["w_rid", "wts"],
    "algorithm": "MD5",
    "steps": [
        "1. 获取 img_key 和 sub_key",
        "2. 合并得到 mixin_key",
        "3. 按照混淆表重排",
        "4. 参数排序拼接",
        "5. MD5(sorted_params + mixin_key)",
    ],
    "difficulty": "medium",
}
```

**Python实现**:
```python
import hashlib
from urllib.parse import urlencode

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13
]

def get_mixin_key(orig: str) -> str:
    return ''.join(orig[i] for i in MIXIN_KEY_ENC_TAB)[:32]

def sign_wbi(params: dict, img_key: str, sub_key: str) -> dict:
    mixin_key = get_mixin_key(img_key + sub_key)

    params['wts'] = int(time.time())
    params = dict(sorted(params.items()))

    query = urlencode(params)
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()

    params['w_rid'] = w_rid
    return params
```

---

## API标准签名

### OAuth 1.0 签名

```
签名格式: oauth_signature=xxx
算法: HMAC-SHA1
```

**签名流程**:
```python
OAUTH1_STRUCTURE = {
    "params": [
        "oauth_consumer_key",
        "oauth_token",
        "oauth_signature_method",
        "oauth_timestamp",
        "oauth_nonce",
        "oauth_version",
        "oauth_signature"
    ],
    "algorithm": "HMAC-SHA1",
    "steps": [
        "1. 收集所有参数(包括query和body)",
        "2. 按key字母序排序",
        "3. URL编码并拼接为字符串",
        "4. 构造签名基字符串: METHOD&URL&PARAMS",
        "5. 构造签名密钥: consumer_secret&token_secret",
        "6. HMAC-SHA1签名并Base64编码"
    ],
    "difficulty": "medium"
}
```

**Python实现**:
```python
import hmac
import hashlib
import base64
import time
import uuid
from urllib.parse import quote, urlencode

def oauth1_sign(
    method: str,
    url: str,
    params: dict,
    consumer_key: str,
    consumer_secret: str,
    token: str = "",
    token_secret: str = ""
) -> dict:
    """OAuth 1.0 签名"""
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_version": "1.0",
    }
    if token:
        oauth_params["oauth_token"] = token

    # 合并所有参数
    all_params = {**params, **oauth_params}

    # 排序并编码
    sorted_params = sorted(all_params.items())
    param_string = "&".join(f"{quote(k, safe='')}={quote(str(v), safe='')}"
                           for k, v in sorted_params)

    # 构造签名基字符串
    base_string = f"{method.upper()}&{quote(url, safe='')}&{quote(param_string, safe='')}"

    # 构造签名密钥
    signing_key = f"{quote(consumer_secret, safe='')}&{quote(token_secret, safe='')}"

    # HMAC-SHA1签名
    signature = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()

    oauth_params["oauth_signature"] = signature
    return oauth_params
```

---

### OAuth 2.0 / Bearer Token

```
签名格式: Authorization: Bearer {access_token}
算法: 无签名(Token认证)
```

**认证结构**:
```python
OAUTH2_STRUCTURE = {
    "grant_types": [
        "authorization_code",  # 授权码模式
        "client_credentials",  # 客户端模式
        "refresh_token",       # 刷新令牌
    ],
    "token_endpoint": "/oauth/token",
    "headers": {
        "Authorization": "Bearer {access_token}"
    },
    "refresh_flow": [
        "1. 检测access_token过期",
        "2. 使用refresh_token请求新token",
        "3. 更新存储的token"
    ],
    "difficulty": "low"
}
```

**Python实现**:
```python
import httpx
from dataclasses import dataclass
from typing import Optional

@dataclass
class OAuth2Token:
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None

    def get_header(self) -> dict:
        return {"Authorization": f"{self.token_type} {self.access_token}"}

class OAuth2Client:
    """OAuth 2.0 客户端"""

    def __init__(self, client_id: str, client_secret: str, token_url: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.token: Optional[OAuth2Token] = None

    def get_token_client_credentials(self) -> OAuth2Token:
        """客户端凭证模式获取Token"""
        response = httpx.post(self.token_url, data={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        })
        data = response.json()
        self.token = OAuth2Token(**data)
        return self.token

    def refresh_access_token(self) -> OAuth2Token:
        """刷新Token"""
        if not self.token or not self.token.refresh_token:
            raise ValueError("No refresh token available")

        response = httpx.post(self.token_url, data={
            "grant_type": "refresh_token",
            "refresh_token": self.token.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        })
        data = response.json()
        self.token = OAuth2Token(**data)
        return self.token
```

---

### JWT (JSON Web Token)

```
签名格式: Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
结构: header.payload.signature
算法: HS256/RS256/ES256
```

**JWT结构**:
```python
JWT_STRUCTURE = {
    "format": "{header}.{payload}.{signature}",
    "header": {
        "alg": "HS256|RS256|ES256",
        "typ": "JWT"
    },
    "payload": {
        "iss": "签发者",
        "sub": "主题",
        "aud": "受众",
        "exp": "过期时间",
        "iat": "签发时间",
        "jti": "JWT ID"
    },
    "algorithms": {
        "HS256": "HMAC-SHA256 (对称密钥)",
        "RS256": "RSA-SHA256 (非对称密钥)",
        "ES256": "ECDSA-SHA256 (椭圆曲线)"
    },
    "difficulty": "low"
}
```

**Python实现**:
```python
import json
import hmac
import hashlib
import base64
import time

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def base64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    data += '=' * padding
    return base64.urlsafe_b64decode(data)

def create_jwt(payload: dict, secret: str, algorithm: str = "HS256") -> str:
    """创建JWT Token"""
    header = {"alg": algorithm, "typ": "JWT"}

    # 编码header和payload
    header_b64 = base64url_encode(json.dumps(header).encode())
    payload_b64 = base64url_encode(json.dumps(payload).encode())

    # 签名
    message = f"{header_b64}.{payload_b64}"
    if algorithm == "HS256":
        signature = hmac.new(
            secret.encode(), message.encode(), hashlib.sha256
        ).digest()
    else:
        raise NotImplementedError(f"Algorithm {algorithm} not implemented")

    signature_b64 = base64url_encode(signature)
    return f"{message}.{signature_b64}"

def decode_jwt(token: str, secret: str, verify: bool = True) -> dict:
    """解码JWT Token"""
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")

    header = json.loads(base64url_decode(parts[0]))
    payload = json.loads(base64url_decode(parts[1]))

    if verify:
        expected = create_jwt(payload, secret, header['alg'])
        if token != expected:
            raise ValueError("Invalid signature")

        # 检查过期
        if 'exp' in payload and payload['exp'] < time.time():
            raise ValueError("Token expired")

    return payload

# 使用示例
payload = {
    "sub": "user123",
    "iat": int(time.time()),
    "exp": int(time.time()) + 3600,
}
token = create_jwt(payload, "your-secret-key")
```

---

### AWS Signature V4

```
签名格式: Authorization: AWS4-HMAC-SHA256 Credential=.../aws4_request, SignedHeaders=..., Signature=...
算法: HMAC-SHA256 (4层嵌套)
```

**签名结构**:
```python
AWS_SIGV4_STRUCTURE = {
    "algorithm": "AWS4-HMAC-SHA256",
    "components": [
        "CanonicalRequest",
        "StringToSign",
        "SigningKey",
        "Signature"
    ],
    "steps": [
        "1. 创建规范请求(CanonicalRequest)",
        "2. 创建待签字符串(StringToSign)",
        "3. 计算签名密钥(4层HMAC)",
        "4. 计算签名",
        "5. 添加到Authorization头"
    ],
    "difficulty": "high"
}
```

**Python实现**:
```python
import hmac
import hashlib
from datetime import datetime
from urllib.parse import quote

def sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()

def get_signature_key(secret_key: str, date_stamp: str,
                      region: str, service: str) -> bytes:
    """生成签名密钥(4层HMAC)"""
    k_date = sign(f"AWS4{secret_key}".encode(), date_stamp)
    k_region = sign(k_date, region)
    k_service = sign(k_region, service)
    k_signing = sign(k_service, "aws4_request")
    return k_signing

def aws_sigv4_sign(
    method: str,
    url: str,
    headers: dict,
    body: str,
    access_key: str,
    secret_key: str,
    region: str,
    service: str
) -> dict:
    """AWS Signature V4 签名"""
    t = datetime.utcnow()
    amz_date = t.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = t.strftime('%Y%m%d')

    # 解析URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.netloc
    uri = parsed.path or '/'
    query = parsed.query

    # 规范请求
    canonical_headers = f"host:{host}\nx-amz-date:{amz_date}\n"
    signed_headers = "host;x-amz-date"
    payload_hash = hashlib.sha256(body.encode()).hexdigest()

    canonical_request = f"{method}\n{uri}\n{query}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

    # 待签字符串
    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = f"{algorithm}\n{amz_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"

    # 签名
    signing_key = get_signature_key(secret_key, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    # 授权头
    authorization = f"{algorithm} Credential={access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"

    return {
        "Authorization": authorization,
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash
    }
```

---

## 企业级反爬系统签名

> **难度等级**: EXTREME | 这些是世界上最难破解的反爬系统

### Akamai Bot Manager

```
签名参数: _abck, bm_sz, sensor_data
难度: ★★★★★ (极难)
检测维度: 200+ 浏览器指纹点
```

**签名结构分析**:
```python
AKAMAI_STRUCTURE = {
    "cookies": {
        "_abck": "动态生成的主Cookie，包含验证状态",
        "bm_sz": "初始Cookie，包含会话信息",
        "ak_bmsc": "辅助Cookie",
    },
    "sensor_data": {
        "description": "核心指纹数据，经过多层编码",
        "length": "2000-8000字符",
        "encoding": "自定义编码 + 位运算 + 混淆",
        "structure": [
            "版本号",
            "设备指纹 (Canvas/WebGL/Audio)",
            "行为数据 (鼠标/键盘/触摸)",
            "时间戳序列",
            "DOM结构哈希",
            "JS执行环境检测结果",
        ]
    },
    "versions": {
        "1.x": "早期版本，较易破解",
        "2.x": "增加WASM验证",
        "3.x": "当前版本，极难破解",
    },
    "detection_points": [
        "navigator属性完整性",
        "WebDriver检测",
        "Chrome DevTools检测",
        "Headless浏览器检测",
        "Canvas指纹一致性",
        "WebGL渲染器检测",
        "Audio指纹",
        "字体枚举",
        "时区/语言一致性",
        "屏幕分辨率合理性",
        "鼠标移动轨迹自然度",
        "键盘输入节奏",
    ],
    "difficulty": "extreme",
    "recommended_approach": "真实浏览器 + 行为模拟"
}
```

**sensor_data 生成流程**:
```
┌──────────────────────────────────────────────────────────────┐
│                 Akamai sensor_data 生成流程                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐     │
│  │ 环境收集 │──▶│ 指纹计算 │──▶│ 行为记录 │──▶│ 编码加密 │     │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘     │
│       │             │             │             │           │
│       ▼             ▼             ▼             ▼           │
│  navigator      Canvas         mouse          自定义编码     │
│  screen         WebGL          keyboard       位运算混淆     │
│  window         Audio          touch          时间戳绑定     │
│  document       Font           scroll         版本号前缀     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**破解策略**:
```python
AKAMAI_STRATEGIES = {
    "level_1": {
        "name": "基础绕过",
        "method": "使用真实浏览器 (Playwright/Puppeteer)",
        "success_rate": "60-70%",
        "detection_risk": "高",
    },
    "level_2": {
        "name": "指纹伪装",
        "method": "浏览器 + 指纹插件 (puppeteer-extra-stealth)",
        "success_rate": "70-80%",
        "detection_risk": "中",
    },
    "level_3": {
        "name": "行为模拟",
        "method": "浏览器 + 真实鼠标轨迹 + 键盘节奏",
        "success_rate": "85-90%",
        "detection_risk": "低",
    },
    "level_4": {
        "name": "完整复现",
        "method": "逆向sensor_data生成算法 + 补环境",
        "success_rate": "90-95%",
        "detection_risk": "极低",
        "difficulty": "需要数周逆向工作",
    }
}
```

---

### Cloudflare Challenge

```
签名参数: cf_clearance, __cf_bm, cf_chl_opt
难度: ★★★★☆ (很难)
检测维度: JS Challenge + Turnstile
```

**签名结构分析**:
```python
CLOUDFLARE_STRUCTURE = {
    "cookies": {
        "cf_clearance": "通过Challenge后获得，有效期通常15-30分钟",
        "__cf_bm": "Bot Management Cookie",
        "cf_chl_opt": "Challenge选项",
    },
    "challenge_types": {
        "js_challenge": {
            "description": "JavaScript计算挑战",
            "duration": "5秒等待",
            "detection": "JS执行环境验证",
        },
        "managed_challenge": {
            "description": "交互式验证 (Turnstile)",
            "detection": "行为分析 + 指纹",
        },
        "interactive_challenge": {
            "description": "强制人机验证",
            "detection": "需要人工干预",
        }
    },
    "turnstile": {
        "token_name": "cf-turnstile-response",
        "algorithm": "WASM + Worker隔离",
        "validity": "300秒",
    },
    "difficulty": "high",
}
```

**Python绕过模板**:
```python
import asyncio
from playwright.async_api import async_playwright

class CloudflareBypass:
    """Cloudflare Challenge 绕过器"""

    def __init__(self):
        self.cf_clearance = None
        self.user_agent = None

    async def solve_challenge(self, url: str, timeout: int = 30) -> dict:
        """解决Cloudflare Challenge"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,  # Cloudflare检测headless
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                ]
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )

            page = await context.new_page()

            # 注入反检测脚本
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
            """)

            # 访问目标
            await page.goto(url, wait_until='networkidle')

            # 等待Challenge完成
            try:
                await page.wait_for_function(
                    "!document.querySelector('#challenge-running')",
                    timeout=timeout * 1000
                )
            except:
                pass

            # 提取Cookie
            cookies = await context.cookies()
            cf_cookies = {c['name']: c['value'] for c in cookies
                        if 'cf' in c['name'].lower()}

            self.cf_clearance = cf_cookies.get('cf_clearance')
            self.user_agent = await page.evaluate('navigator.userAgent')

            await browser.close()

            return {
                'cookies': cf_cookies,
                'user_agent': self.user_agent,
                'success': bool(self.cf_clearance)
            }
```

---

### PerimeterX (Human Challenge)

```
签名参数: _px, _pxhd, _pxvid, _pxde
难度: ★★★★★ (极难)
检测维度: 行为分析 + 设备指纹 + 机器学习
```

**签名结构分析**:
```python
PERIMETERX_STRUCTURE = {
    "cookies": {
        "_px": "主验证Cookie",
        "_pxhd": "设备指纹哈希",
        "_pxvid": "访客ID",
        "_pxde": "加密数据",
        "_pxff_*": "功能标志",
    },
    "payload": {
        "name": "PX Payload",
        "transport": "POST /api/v2/collector",
        "format": "JSON (加密)",
        "fields": [
            "PX103",  # 设备指纹
            "PX259",  # 行为数据
            "PX322",  # 时间戳
            "PX425",  # Canvas指纹
            "PX504",  # WebGL指纹
        ]
    },
    "detection_methods": [
        "鼠标移动熵值分析",
        "点击位置热力图",
        "滚动行为模式",
        "键盘输入间隔",
        "页面停留时间",
        "请求时序分析",
        "Canvas渲染差异",
        "WebGL参数指纹",
        "Audio Context指纹",
        "设备内存/CPU核数",
    ],
    "ml_model": {
        "type": "行为序列分类",
        "features": "200+ 维度",
        "update_frequency": "实时更新",
    },
    "difficulty": "extreme",
}
```

**行为数据格式**:
```python
PX_BEHAVIOR_DATA = {
    "mouse_events": [
        # [timestamp, x, y, event_type]
        [1706345678000, 523, 234, "move"],
        [1706345678050, 525, 236, "move"],
        [1706345678100, 530, 240, "click"],
    ],
    "keyboard_events": [
        # [timestamp, key_code, event_type]
        [1706345679000, 65, "keydown"],
        [1706345679080, 65, "keyup"],
    ],
    "scroll_events": [
        # [timestamp, scroll_x, scroll_y]
        [1706345680000, 0, 150],
    ],
    "touch_events": [],  # 移动端
}
```

---

### DataDome

```
签名参数: datadome
难度: ★★★★☆ (很难)
检测维度: 实时行为分析 + 设备指纹
```

**签名结构分析**:
```python
DATADOME_STRUCTURE = {
    "cookie": {
        "name": "datadome",
        "length": "~300字符",
        "encoding": "自定义Base64变体",
        "validity": "会话级别",
    },
    "api_endpoint": "/js/",
    "challenge_flow": [
        "1. 首次请求返回403 + JS挑战",
        "2. 执行JS生成设备指纹",
        "3. 提交指纹获取datadome cookie",
        "4. 携带cookie重新请求",
    ],
    "detection_signals": [
        "TLS指纹 (JA3/JA4)",
        "HTTP/2指纹",
        "请求头顺序",
        "Canvas/WebGL指纹",
        "屏幕/窗口尺寸",
        "时区/语言",
        "插件列表",
    ],
    "difficulty": "high",
}
```

**TLS指纹绕过**:
```python
# 使用 curl_cffi 模拟真实浏览器TLS指纹
from curl_cffi import requests

def datadome_request(url: str, datadome_cookie: str = None):
    """DataDome请求 (带TLS指纹伪装)"""

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    cookies = {}
    if datadome_cookie:
        cookies['datadome'] = datadome_cookie

    response = requests.get(
        url,
        headers=headers,
        cookies=cookies,
        impersonate="chrome120",  # 模拟Chrome 120 TLS指纹
    )

    return response
```

---

### Kasada (Polyform)

```
签名参数: x-kpsdk-ct, x-kpsdk-cd, x-kpsdk-v
难度: ★★★★★ (极难)
检测维度: WASM验证 + 行为分析
```

**签名结构分析**:
```python
KASADA_STRUCTURE = {
    "headers": {
        "x-kpsdk-ct": "客户端令牌 (加密)",
        "x-kpsdk-cd": "客户端数据 (设备指纹)",
        "x-kpsdk-v": "SDK版本",
        "x-kpsdk-r": "请求标识",
    },
    "workflow": [
        "1. 加载 /ips.js (混淆的SDK)",
        "2. SDK加载WASM模块",
        "3. WASM执行PoW(工作量证明)",
        "4. 收集设备指纹",
        "5. 生成加密令牌",
        "6. 请求携带令牌头",
    ],
    "pow": {
        "description": "Proof of Work计算",
        "algorithm": "SHA256迭代",
        "difficulty": "动态调整",
        "purpose": "增加自动化成本",
    },
    "wasm_analysis": {
        "size": "~500KB",
        "obfuscation": "控制流平坦化 + 字符串加密",
        "anti_debug": "检测断点 + 时间检测",
    },
    "difficulty": "extreme",
}
```

---

### Imperva/Incapsula

```
签名参数: reese84, ___utmvc, incap_ses_*
难度: ★★★★☆ (很难)
检测维度: 设备指纹 + Bot签名
```

**签名结构分析**:
```python
IMPERVA_STRUCTURE = {
    "cookies": {
        "reese84": "主验证Token (长字符串)",
        "___utmvc": "设备指纹Cookie",
        "incap_ses_*": "会话Cookie",
        "visid_incap_*": "访客ID",
    },
    "reese84_format": {
        "encoding": "Base64 + 自定义加密",
        "content": [
            "设备指纹哈希",
            "浏览器特征",
            "时间戳",
            "随机数",
        ],
    },
    "detection_methods": [
        "JavaScript执行验证",
        "Cookie支持检测",
        "请求头完整性",
        "User-Agent一致性",
        "TLS指纹",
    ],
    "difficulty": "high",
}
```

---

### Shape Security (F5)

```
签名参数: 动态Cookie名称, _imp_apg_r_
难度: ★★★★★ (极难)
检测维度: 深度行为分析 + 请求签名
```

**签名结构分析**:
```python
SHAPE_STRUCTURE = {
    "characteristics": {
        "dynamic_names": "Cookie/参数名称动态变化",
        "request_signing": "每个请求都需要签名",
        "polymorphic_js": "JS代码每次访问都不同",
    },
    "detection_layers": [
        "Layer 1: 被动指纹 (TLS/HTTP头)",
        "Layer 2: 主动指纹 (JS探测)",
        "Layer 3: 行为分析 (鼠标/键盘)",
        "Layer 4: 请求签名验证",
        "Layer 5: 异常模式检测",
    ],
    "anti_automation": [
        "代码多态性",
        "变量名随机化",
        "API调用顺序验证",
        "时序分析",
    ],
    "difficulty": "extreme",
    "note": "Shape是最难破解的商业反爬之一",
}
```

---

## 高级算法解析技术

### WASM逆向分析

```
适用: Akamai 3.x, Kasada, 部分抖音X-Bogus
工具: wasm2wat, Ghidra, IDA Pro
```

**WASM分析流程**:
```python
WASM_ANALYSIS = {
    "tools": {
        "wasm2wat": "WASM转文本格式",
        "wasm-decompile": "WASM反编译",
        "Ghidra": "二进制分析 (带WASM插件)",
        "Chrome DevTools": "WASM调试",
    },
    "analysis_steps": [
        "1. 提取WASM文件 (从JS或网络请求)",
        "2. 转换为WAT文本格式",
        "3. 识别导入/导出函数",
        "4. 分析内存布局",
        "5. Hook关键函数",
        "6. 动态调试追踪数据流",
    ],
    "common_patterns": {
        "crypto": "查找常量 (MD5/SHA/AES魔数)",
        "encoding": "查找Base64表",
        "fingerprint": "查找Canvas/WebGL调用",
    }
}
```

**WASM Hook技术**:
```javascript
// 在浏览器中Hook WASM函数
(function() {
    const originalInstantiate = WebAssembly.instantiate;

    WebAssembly.instantiate = async function(bufferSource, importObject) {
        console.log('[WASM] Instantiate called');

        // Hook导入函数
        if (importObject && importObject.env) {
            for (let key in importObject.env) {
                if (typeof importObject.env[key] === 'function') {
                    const original = importObject.env[key];
                    importObject.env[key] = function(...args) {
                        console.log(`[WASM Import] ${key}:`, args);
                        return original.apply(this, args);
                    };
                }
            }
        }

        const result = await originalInstantiate.apply(this, arguments);

        // Hook导出函数
        const exports = result.instance.exports;
        for (let key in exports) {
            if (typeof exports[key] === 'function') {
                const original = exports[key];
                exports[key] = function(...args) {
                    console.log(`[WASM Export] ${key}:`, args);
                    const ret = original.apply(this, args);
                    console.log(`[WASM Export] ${key} returned:`, ret);
                    return ret;
                };
            }
        }

        // Hook内存访问
        if (exports.memory) {
            console.log('[WASM] Memory size:', exports.memory.buffer.byteLength);
        }

        return result;
    };
})();
```

---

### Protobuf解码

```
适用: Google系、部分API使用二进制协议
工具: protoc, blackboxprotobuf
```

**Protobuf分析**:
```python
# 使用 blackboxprotobuf 解码未知protobuf
import blackboxprotobuf

def decode_protobuf(data: bytes) -> dict:
    """解码未知Protobuf数据"""
    message, typedef = blackboxprotobuf.decode_message(data)
    return {
        "message": message,
        "typedef": typedef,
    }

def analyze_protobuf_field(data: bytes):
    """分析Protobuf字段结构"""
    message, typedef = blackboxprotobuf.decode_message(data)

    print("=== Protobuf Structure ===")
    for field_num, field_type in typedef.items():
        value = message.get(field_num, "N/A")
        print(f"Field {field_num}: {field_type} = {value}")

# 常见Protobuf特征识别
PROTOBUF_SIGNATURES = {
    "wire_types": {
        0: "Varint (int32, int64, bool)",
        1: "64-bit (fixed64, double)",
        2: "Length-delimited (string, bytes, nested)",
        5: "32-bit (fixed32, float)",
    },
    "common_fields": {
        1: "通常是ID或版本",
        2: "通常是名称或数据",
        3: "通常是时间戳",
    }
}
```

---

### 设备指纹算法逆向

#### Canvas指纹

```python
CANVAS_FINGERPRINT = {
    "principle": "相同代码在不同设备上渲染结果不同",
    "detection_points": [
        "字体渲染差异",
        "抗锯齿算法",
        "GPU渲染差异",
        "系统字体列表",
    ],
    "generation": """
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillText('Hello, World!', 0, 0);
        return canvas.toDataURL();
    """,
    "spoofing": {
        "method": "在toDataURL前注入噪声",
        "code": """
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function() {
                const ctx = this.getContext('2d');
                // 添加不可见噪声
                const imageData = ctx.getImageData(0, 0, this.width, this.height);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] ^= (Math.random() * 2) | 0;
                }
                ctx.putImageData(imageData, 0, 0);
                return originalToDataURL.apply(this, arguments);
            };
        """
    }
}
```

#### WebGL指纹

```python
WEBGL_FINGERPRINT = {
    "detection_points": [
        "WEBGL_debug_renderer_info (显卡信息)",
        "支持的扩展列表",
        "最大纹理大小",
        "着色器精度",
        "渲染结果差异",
    ],
    "key_parameters": [
        "UNMASKED_VENDOR_WEBGL",
        "UNMASKED_RENDERER_WEBGL",
        "MAX_TEXTURE_SIZE",
        "MAX_VERTEX_ATTRIBS",
    ],
    "spoofing": """
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(param) {
            // 伪装显卡信息
            if (param === 37445) return 'Google Inc. (Intel)';
            if (param === 37446) return 'ANGLE (Intel, Intel(R) UHD Graphics 630, OpenGL 4.1)';
            return getParameter.apply(this, arguments);
        };
    """
}
```

#### AudioContext指纹

```python
AUDIO_FINGERPRINT = {
    "principle": "音频处理在不同硬件上产生细微差异",
    "generation_method": [
        "创建OscillatorNode",
        "通过DynamicsCompressorNode处理",
        "分析输出的频率数据",
        "计算特征哈希",
    ],
    "fingerprint_code": """
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const analyser = audioCtx.createAnalyser();
        const gain = audioCtx.createGain();
        const compressor = audioCtx.createDynamicsCompressor();

        oscillator.type = 'triangle';
        oscillator.frequency.value = 10000;

        compressor.threshold.value = -50;
        compressor.knee.value = 40;
        compressor.ratio.value = 12;
        compressor.attack.value = 0;
        compressor.release.value = 0.25;

        oscillator.connect(compressor);
        compressor.connect(analyser);
        analyser.connect(gain);
        gain.connect(audioCtx.destination);
        gain.gain.value = 0;

        oscillator.start(0);
        // 分析频率数据生成指纹
    """,
    "spoofing": "注入AudioContext噪声或返回固定值"
}
```

---

### 自定义加密算法识别

```python
CRYPTO_IDENTIFICATION = {
    "md5_signatures": [
        0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476,  # 初始值
        [7, 12, 17, 22],  # 移位表
    ],
    "sha256_signatures": [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,  # H0-H3
        0x428a2f98, 0x71374491,  # K表开头
    ],
    "aes_signatures": [
        0x63, 0x7c, 0x77, 0x7b,  # S-box开头
        [0x01, 0x02, 0x04, 0x08],  # 轮常量
    ],
    "base64_table": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",

    "detection_method": """
        1. 在反混淆后的代码中搜索这些常量
        2. 如果发现变体，分析变体规律
        3. 通过已知输入输出验证算法
        4. 对比标准库实现确认
    """
}
```

**算法识别自动化**:
```python
import re

class CryptoDetector:
    """加密算法自动识别"""

    SIGNATURES = {
        "MD5": {
            "constants": [0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476],
            "patterns": [r"0x67452301", r"1732584193"],
        },
        "SHA256": {
            "constants": [0x6a09e667, 0xbb67ae85, 0x3c6ef372],
            "patterns": [r"0x6a09e667", r"1779033703"],
        },
        "AES": {
            "constants": [0x63, 0x7c, 0x77, 0x7b],
            "patterns": [r"\[99,\s*124,\s*119,\s*123"],
        },
        "HMAC": {
            "patterns": [r"0x36", r"0x5c", r"ipad", r"opad"],
        },
    }

    def detect(self, code: str) -> list:
        """检测代码中使用的加密算法"""
        detected = []

        for algo, sig in self.SIGNATURES.items():
            for pattern in sig.get("patterns", []):
                if re.search(pattern, code, re.I):
                    detected.append({
                        "algorithm": algo,
                        "confidence": "high",
                        "pattern": pattern,
                    })
                    break

        return detected

    def analyze_custom(self, code: str) -> dict:
        """分析可能的自定义算法"""
        analysis = {
            "has_bitwise": bool(re.search(r"[&|^~]|<<|>>", code)),
            "has_loop": bool(re.search(r"for\s*\(|while\s*\(", code)),
            "has_array_access": bool(re.search(r"\[\d+\]|\[i\]", code)),
            "possible_block_cipher": False,
            "possible_hash": False,
        }

        # 块密码特征: 固定块大小操作
        if re.search(r"16|32|64|128", code) and analysis["has_loop"]:
            analysis["possible_block_cipher"] = True

        # 哈希特征: 位运算 + 循环 + 常量
        if analysis["has_bitwise"] and analysis["has_loop"]:
            analysis["possible_hash"] = True

        return analysis
```

---

## 破解方案选择

### 方案对比

| 方案 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| **纯算法复现** | 算法已知、复杂度低 | 性能高、无依赖 | 需要逆向能力 |
| **JS引擎执行** | 复杂混淆、WASM | 稳定可靠 | 性能较低 |
| **RPC调用** | 无法还原算法 | 简单直接 | 需要维护服务 |
| **浏览器执行** | 极端反爬 | 最真实 | 性能最低 |
| **补环境** | 中等复杂度 | 平衡方案 | 需要分析环境 |

### 决策流程

```
                    ┌────────────────┐
                    │ 分析签名复杂度  │
                    └───────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
        ┌─────────┐   ┌─────────┐   ┌─────────┐
        │  low    │   │ medium  │   │ high+   │
        │ ───────│   │ ───────│   │ ───────│
        │ 纯算复现 │   │ 补环境  │   │ JS引擎  │
        └─────────┘   └─────────┘   └─────────┘
              │             │             │
              ▼             ▼             ▼
        ┌─────────┐   ┌─────────┐   ┌─────────┐
        │ Python  │   │ Node.js │   │Playwright│
        │ 原生实现 │   │ + Mock  │   │ evaluate│
        └─────────┘   └─────────┘   └─────────┘
```

---

## JS 逆向技术

### AST 反混淆

```python
# 使用 babel 反混淆
DEOBFUSCATION_STEPS = [
    "1. 定位目标 JS 文件",
    "2. 使用 babel-parser 解析为 AST",
    "3. 移除控制流平坦化",
    "4. 还原字符串加密",
    "5. 删除无用代码",
    "6. 重命名变量函数",
    "7. 美化输出",
]
```

### 补环境技术

```javascript
// 创建浏览器环境 mock
const jsdom = require("jsdom");
const { JSDOM } = jsdom;

const dom = new JSDOM(`<!DOCTYPE html><html><body></body></html>`, {
    url: "https://target-site.com",
    referrer: "https://target-site.com",
    contentType: "text/html",
    includeNodeLocations: true,
    storageQuota: 10000000,
});

global.window = dom.window;
global.document = dom.window.document;
global.navigator = dom.window.navigator;
global.location = dom.window.location;

// 补充特定对象
global.window.localStorage = {
    getItem: (key) => null,
    setItem: (key, value) => {},
};
```

### Playwright 执行

```python
async def get_signature_via_browser(page, params):
    """通过浏览器执行获取签名"""

    # 注入参数
    await page.evaluate(f"window.__params = {json.dumps(params)}")

    # 执行签名函数
    result = await page.evaluate("""
        () => {
            // 假设目标签名函数是 window.sign
            return window.sign(window.__params);
        }
    """)

    return result
```

---

## 签名生成器接口

```python
from abc import ABC, abstractmethod

class SignatureGenerator(ABC):
    """签名生成器基类"""

    @abstractmethod
    def generate(self, params: dict) -> str:
        """生成签名"""
        pass

    @abstractmethod
    def validate(self, params: dict, signature: str) -> bool:
        """验证签名"""
        pass

class JDH5STGenerator(SignatureGenerator):
    """京东 H5ST 签名生成器"""

    def __init__(self, js_path: str = None):
        self.js_context = self._init_js_context(js_path)

    def generate(self, params: dict) -> str:
        # 实现签名生成
        pass

class BiliWBIGenerator(SignatureGenerator):
    """B站 WBI 签名生成器"""

    def generate(self, params: dict) -> str:
        return sign_wbi(params, self.img_key, self.sub_key)
```

---

## 调试技巧

### Chrome DevTools 断点

```javascript
// 1. XHR 断点
// Network -> XHR/fetch Breakpoints -> 添加URL包含关键词

// 2. DOM 断点
// Elements -> 右键元素 -> Break on -> attribute modifications

// 3. 事件断点
// Sources -> Event Listener Breakpoints -> XHR

// 4. 条件断点
// Sources -> 行号右键 -> Add conditional breakpoint
// 输入: arguments[0].includes('sign')
```

### Hook 技巧

```javascript
// Hook JSON.stringify 查看签名参数
const originalStringify = JSON.stringify;
JSON.stringify = function() {
    console.log('JSON.stringify called:', arguments);
    return originalStringify.apply(this, arguments);
};

// Hook XMLHttpRequest 查看请求
const originalOpen = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function() {
    console.log('XHR open:', arguments);
    return originalOpen.apply(this, arguments);
};

// Hook fetch
const originalFetch = window.fetch;
window.fetch = function() {
    console.log('Fetch:', arguments);
    return originalFetch.apply(this, arguments);
};
```

---

## 使用示例

### 示例1: OAuth 1.0 签名 - Twitter API

**场景**: 调用Twitter API需要OAuth 1.0签名

```python
from unified_agent import Brain

brain = Brain()

# 1. 准备凭据
credentials = {
    "consumer_key": "your_consumer_key",
    "consumer_secret": "your_consumer_secret",
    "token": "your_access_token",
    "token_secret": "your_token_secret",
}

# 2. 生成签名
result = brain.signature.generate(
    params={"status": "Hello World", "include_entities": "true"},
    sign_type="oauth1",
    credentials=credentials,
)

# 3. 使用签名发送请求
if result.status == "success":
    response = httpx.post(
        "https://api.twitter.com/1.1/statuses/update.json",
        params=result.signed_params,
        headers=result.headers,  # 包含Authorization头
    )
    print(response.json())
```

**预期输出**:
```python
{
    "status": "success",
    "signature": "tR3+Ty81lMeYAr/Fid0kMTYa/WM=",
    "signed_params": {
        "status": "Hello World",
        "include_entities": "true",
        "oauth_consumer_key": "xxx",
        "oauth_nonce": "xxx",
        "oauth_signature": "tR3+Ty81lMeYAr/Fid0kMTYa/WM=",
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": "1706432100",
        "oauth_token": "xxx",
        "oauth_version": "1.0",
    },
    "headers": {
        "Authorization": 'OAuth oauth_consumer_key="xxx", ...'
    },
    "approach": "pure_algo",
}
```

---

### 示例2: JWT Token - API认证

**场景**: 生成JWT Token用于API认证

```python
# 1. 生成JWT
result = brain.signature.generate_jwt(
    payload={"user_id": 123, "role": "admin", "exp": time.time() + 3600},
    secret="your_jwt_secret",
    algorithm="HS256",
)

# 2. 使用JWT访问API
headers = {"Authorization": f"Bearer {result.signature}"}
response = httpx.get("https://api.example.com/protected", headers=headers)
```

**预期输出**:
```python
{
    "status": "success",
    "signature": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjMsInJvbGUiOiJhZG1pbiIsImV4cCI6MTcwNjQzNTcwMH0.abc123...",
    "approach": "pure_algo",
    "metadata": {
        "algorithm": "HS256",
        "expires_at": 1706435700,
    },
}
```

---

### 示例3: B站WBI签名 - 真实案例

**场景**: 爬取B站用户信息,需要WBI签名

```python
# 1. 获取img_key和sub_key(从nav接口获取)
nav_url = "https://api.bilibili.com/x/web-interface/nav"
nav_data = httpx.get(nav_url).json()
img_url = nav_data["data"]["wbi_img"]["img_url"]
sub_url = nav_data["data"]["wbi_img"]["sub_url"]

img_key = img_url.split("/")[-1].split(".")[0]
sub_key = sub_url.split("/")[-1].split(".")[0]

# 2. 生成WBI签名
params = {"mid": 123456789}

result = brain.signature.generate_wbi(
    params=params,
    img_key=img_key,
    sub_key=sub_key,
)

# 3. 请求用户信息
response = httpx.get(
    "https://api.bilibili.com/x/space/wbi/acc/info",
    params=result.signed_params,
)
print(response.json())
```

**预期输出**:
```python
{
    "status": "success",
    "signed_params": {
        "mid": 123456789,
        "wts": 1706432100,
        "w_rid": "a1b2c3d4e5f6...",
    },
    "approach": "pure_algo",
    "metadata": {
        "img_key": "xxxyyy...",
        "sub_key": "zzzaaa...",
        "mixin_key": "abcdef...",
    },
}
```

---

### 示例4: 京东H5ST - RPC方案

**场景**: 京东H5ST极度复杂,使用RPC方案

```python
# 1. 启动RPC服务(在浏览器中执行)
# 需要先在真实浏览器中注入RPC脚本

# 2. 连接RPC服务
rpc_client = brain.signature.connect_rpc("ws://127.0.0.1:9999")

# 3. 调用签名函数
params = {"functionId": "productDetail", "body": "{}", "appid": "item-v3"}

result = rpc_client.generate(
    method="_ste.sign", params=params, timeout=5
)

# 4. 使用签名请求
if result.status == "success":
    response = httpx.post(
        "https://api.m.jd.com/client.action",
        data=result.signed_params,
    )
```

**预期输出**:
```python
{
    "status": "success",
    "signature": "20240128120000000;1234567890123;4.7;a1b2c3d4...",
    "signed_params": {
        "functionId": "productDetail",
        "body": "{}",
        "appid": "item-v3",
        "h5st": "20240128120000000;1234567890123;4.7;a1b2c3d4...",
    },
    "approach": "rpc",
    "metadata": {
        "rpc_endpoint": "ws://127.0.0.1:9999",
        "execution_time": 0.234,
    },
}
```

---

### 示例5: Cloudflare Challenge绕过

**场景**: 绕过Cloudflare JS Challenge获取cf_clearance

```python
import asyncio

# 1. 启动浏览器解决Challenge
result = await brain.signature.solve_cloudflare(
    url="https://example.com", timeout=30
)

# 2. 获取cf_clearance cookie
if result.status == "success":
    cf_cookies = result.headers["cookies"]

    # 3. 使用cookie访问
    response = httpx.get(
        "https://example.com/api/data",
        cookies=cf_cookies,
        headers={"User-Agent": result.metadata["user_agent"]},
    )
    print(response.text)
```

**预期输出**:
```python
{
    "status": "success",
    "headers": {
        "cookies": {
            "cf_clearance": "xxxyyy...",
            "__cf_bm": "zzzaaa...",
        },
        "User-Agent": "Mozilla/5.0 ...",
    },
    "approach": "browser",
    "metadata": {
        "challenge_type": "js_challenge",
        "solve_time": 5.3,
        "browser": "chromium",
    },
}
```

---

## 配置选项

### 全局配置

```python
# config.py

SIGNATURE_CONFIG = {
    # 标准签名配置
    "standard": {
        "oauth1_method": "HMAC-SHA1",
        "jwt_algorithm": "HS256",
        "aws_region": "us-east-1",
    },
    # 平台签名配置
    "platforms": {
        "bilibili": {
            "wbi_cache_ttl": 300,  # WBI密钥缓存时间(秒)
        },
        "jingdong": {
            "h5st_version": "4.7",
            "rpc_timeout": 5,
        },
    },
    # 企业反爬配置
    "enterprise": {
        "cloudflare": {
            "solver_timeout": 30,
            "max_retries": 3,
        },
        "datadome": {
            "tls_impersonate": "chrome120",
        },
    },
    # 缓存配置
    "cache": {
        "enabled": True,
        "ttl": 300,  # 默认缓存时间
        "max_size": 1000,
    },
    # 降级策略
    "fallback": {
        "auto_downgrade": True,
        "max_retries": 3,
        "retry_delay": 1,
    },
}
```

### 运行时配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| use_cache | bool | True | 是否使用签名缓存 |
| timeout | int | 5 | 签名生成超时(秒) |
| verify | bool | True | 是否验证签名正确性 |
| log_level | str | "INFO" | 日志级别 |
| save_algorithm | bool | False | 是否保存算法代码 |

---

## 诊断日志

### 标准日志格式

```
[SIGNATURE] <阶段> <操作>: <详情>
```

### 正常流程日志

```
# 签名识别
[SIGNATURE] DETECT 开始分析签名参数
[SIGNATURE] DETECT 检测到参数: sign, timestamp, nonce
[SIGNATURE] DETECT 参数分析: sign(hex,32字符), timestamp(unix_ms)
[SIGNATURE] DETECT 评估类型: custom (自定义签名)
[SIGNATURE] DETECT 评估复杂度: high

# 标准签名生成
[SIGNATURE] GENERATE 签名类型: oauth1
[SIGNATURE] GENERATE 参数排序: 完成 (5个参数)
[SIGNATURE] GENERATE 构造签名基串: GET&https%3A%2F%2Fapi.twitter.com...
[SIGNATURE] GENERATE HMAC-SHA1签名: 完成
[SIGNATURE] GENERATE Base64编码: 完成
[SIGNATURE] GENERATE 签名生成成功: tR3+Ty81lMeYAr/Fid0kMTYa/WM=

# 平台签名生成(B站WBI)
[SIGNATURE] PLATFORM 平台: bilibili
[SIGNATURE] PLATFORM 算法: wbi
[SIGNATURE] PLATFORM 获取mixin_key: 完成
[SIGNATURE] PLATFORM 参数排序: mid=123, wts=1706432100
[SIGNATURE] PLATFORM MD5计算: 完成
[SIGNATURE] PLATFORM 签名生成: w_rid=a1b2c3d4...

# 复杂签名(京东H5ST - RPC)
[SIGNATURE] COMPLEX 平台: jingdong h5st
[SIGNATURE] COMPLEX 检查算法库: 未找到实现
[SIGNATURE] COMPLEX 选择方案: rpc (复杂度extreme)
[SIGNATURE] RPC 连接服务: ws://127.0.0.1:9999
[SIGNATURE] RPC 调用函数: _ste.sign
[SIGNATURE] RPC 执行时间: 0.234s
[SIGNATURE] RPC 签名生成: 20240128120000000;1234...

# 企业反爬(Cloudflare)
[SIGNATURE] ENTERPRISE 系统: cloudflare
[SIGNATURE] ENTERPRISE 检测类型: js_challenge
[SIGNATURE] ENTERPRISE 启动浏览器: chromium headless=False
[SIGNATURE] ENTERPRISE 访问页面: https://example.com
[SIGNATURE] ENTERPRISE 等待Challenge完成: ...
[SIGNATURE] ENTERPRISE Challenge解决: 耗时5.3s
[SIGNATURE] ENTERPRISE 提取Cookie: cf_clearance=xxxyyy...
[SIGNATURE] ENTERPRISE 绕过成功

# 验证阶段
[SIGNATURE] VERIFY 发送测试请求: GET /api/data
[SIGNATURE] VERIFY 响应状态: 200 OK
[SIGNATURE] VERIFY 签名验证: 成功
[SIGNATURE] VERIFY 缓存签名: ttl=300s
```

### 错误日志格式

```
# 签名识别失败
[SIGNATURE] DETECT ERROR: 未检测到签名参数
[SIGNATURE] DETECT 检查的参数: url_params, headers, body
[SIGNATURE] DETECT 建议: 重新侦查或手动指定签名参数

# 凭据缺失
[SIGNATURE] GENERATE ERROR: 缺少必要凭据
[SIGNATURE] GENERATE 需要: consumer_key, consumer_secret
[SIGNATURE] GENERATE 建议: 补充credentials参数

# 签名验证失败
[SIGNATURE] VERIFY ERROR: 签名验证失败 (响应403)
[SIGNATURE] VERIFY 请求URL: https://api.example.com/data
[SIGNATURE] VERIFY 签名值: xxxyyy...
[SIGNATURE] VERIFY 可能原因:
[SIGNATURE] VERIFY   - 时间戳不同步
[SIGNATURE] VERIFY   - 参数顺序错误
[SIGNATURE] VERIFY   - 编码格式不一致
[SIGNATURE] VERIFY   - 算法已更新
[SIGNATURE] VERIFY 建议: 调用09-js-reverse重新分析算法

# 算法执行失败
[SIGNATURE] EXECUTE ERROR: JS执行超时 (>5s)
[SIGNATURE] EXECUTE 代码长度: 1.2MB
[SIGNATURE] EXECUTE 依赖检测: 需要window, navigator, crypto
[SIGNATURE] EXECUTE 建议: 切换RPC方案

# RPC连接失败
[SIGNATURE] RPC ERROR: 连接失败: Connection refused
[SIGNATURE] RPC 地址: ws://127.0.0.1:9999
[SIGNATURE] RPC 建议: 启动sign_server或使用浏览器方案

# 企业反爬失败
[SIGNATURE] ENTERPRISE ERROR: Cloudflare Challenge解决失败
[SIGNATURE] ENTERPRISE Challenge类型: managed_challenge (交互式)
[SIGNATURE] ENTERPRISE 可能原因: 需要人工验证
[SIGNATURE] ENTERPRISE 建议: 使用Turnstile解决方案或2Captcha服务
```

### AI 自诊断检查点

```python
AI_DIAGNOSTIC_CHECKLIST = [
    # 签名识别检查
    {
        "checkpoint": "DETECT_SIGNATURE",
        "checks": [
            "签名参数名是否常见? (sign/signature/token)",
            "是否在URL参数/Header/Body中?",
            "是否有时间戳/随机数配合?",
            "签名格式是否符合标准算法特征?",
        ],
        "auto_fix": [
            "搜索SIGNATURE_KEYWORDS列表",
            "检查所有请求位置(params/headers/body)",
            "调用01-reconnaissance重新捕获",
        ],
    },
    # 凭据检查
    {
        "checkpoint": "CHECK_CREDENTIALS",
        "checks": [
            "OAuth需要: consumer_key/secret, token/secret?",
            "JWT需要: secret_key?",
            "AWS需要: access_key/secret_key/region/service?",
            "自定义需要: app_key/app_secret?",
        ],
        "auto_fix": [
            "检查24-credential-pool",
            "提示用户提供凭据",
            "尝试从页面提取(如img_key/sub_key)",
        ],
    },
    # 签名验证检查
    {
        "checkpoint": "VERIFY_SIGNATURE",
        "checks": [
            "时间戳是否同步? (±5秒内)",
            "参数是否按字母序排序?",
            "URL编码是否一致?",
            "签名方法是否正确? (HMAC-SHA1/256)",
        ],
        "auto_fix": [
            "使用服务器时间(从响应头获取)",
            "强制参数排序",
            "统一使用RFC3986编码",
            "尝试不同签名算法",
        ],
    },
    # 复杂签名检查
    {
        "checkpoint": "COMPLEX_SIGNATURE",
        "checks": [
            "是否需要设备指纹?",
            "是否需要Canvas/WebGL指纹?",
            "是否有反调试/反爬检测?",
            "是否使用WASM加密?",
        ],
        "auto_fix": [
            "调用11-fingerprint生成指纹",
            "调用02-anti-detection绕过检测",
            "切换RPC方案",
            "使用真实浏览器",
        ],
    },
]
```

---

## 相关模块

- **上游**: [01-侦查模块](01-reconnaissance.md) - 发现签名参数
- **上游**: [02-反检测模块](02-anti-detection.md) - 环境伪装
- **下游**: [04-请求模块](04-request.md) - 携带签名请求
- **配合**: [16-战术模块](16-tactics.md) - 签名失败时切换策略，检测钓鱼算法

## FAQ

### Q: 如何判断网站需要什么类型的签名?

A: 按以下顺序检查:
```python
# 1. 检查Authorization头
if "Bearer" in headers:
    return "jwt" or "oauth2"
elif "OAuth" in headers:
    return "oauth1"
elif "AWS4-HMAC-SHA256" in headers:
    return "aws_v4"

# 2. 检查URL参数
if "sign" in params or "signature" in params:
    return "custom"  # 自定义签名

# 3. 检查平台特征
if "h5st" in params:
    return "jd_h5st"
elif "x-bogus" in headers:
    return "douyin_xbogus"
elif "w_rid" in params:
    return "bilibili_wbi"

# 4. 检查企业反爬
if "cf_clearance" in cookies:
    return "cloudflare"
elif "_abck" in cookies:
    return "akamai"
```

### Q: 签名验证失败(403)常见原因?

A: 按概率排序:
1. **时间戳问题 (40%)**: 本地时间不准或格式错误
2. **参数顺序 (25%)**: 未按要求排序
3. **编码问题 (20%)**: URL编码不一致
4. **算法更新 (10%)**: 签名算法已变化
5. **其他 (5%)**: 设备指纹/Cookie/Header缺失

### Q: 如何选择合适的签名方案?

A: pure_algo > js_exec > rpc (按性能排序)

---

## 变更历史

| 版本 | 日期 | 变更类型 | 说明 |
|------|------|----------|------|
| 1.2.0 | 2026-01-28 | enhancement | 完善文档:添加代码实现状态/接口定义/错误码/Skill交互/使用示例/配置选项/诊断日志/FAQ |
| 1.1.0 | 2026-01-27 | feature | 添加企业反爬系统分析 |
| 1.0.1 | 2026-01-26 | fix | 修正B站WBI算法实现 |
| 1.0.0 | 2026-01-25 | initial | 初始版本 |

---

## 相关模块

- **上游**: [01-侦查模块](01-reconnaissance.md) - 发现签名参数
- **配合**: [09-JS逆向模块](09-js-reverse.md) - 复杂签名深度逆向
- **配合**: [02-反检测模块](02-anti-detection.md) - 企业反爬环境伪装
- **下游**: [04-请求模块](04-request.md) - 携带签名发送请求
- **协调**: [16-战术模块](16-tactics.md) - 签名失败时切换策略
