---
skill_id: "24-credential-pool"
name: "凭据池管理"
version: "1.0.0"
status: "stable"                    # draft | beta | stable | deprecated
implementation_status: "partial"    # none | partial | complete
difficulty: 3
category: "infrastructure"

description: "统一管理账号、会话、Cookie和凭据的生命周期"

triggers:
  - "需要登录态访问数据时"
  - "账号轮换时"
  - "会话过期时"

dependencies:
  required:
    - skill: "15-compliance"
      reason: "凭据脱敏和安全存储"
  optional:
    - skill: "10-captcha"
      reason: "登录时可能需要验证码"

external_dependencies:
  required: []
  optional:
    - name: "cryptography"
      version: ">=41.0.0"
      condition: "加密存储凭据"
      type: "python_package"
      install: "pip install cryptography"
    - name: "redis"
      version: ">=6.0"
      condition: "分布式会话共享"
      type: "service"

inputs:
  - name: "site"
    type: "string"
    required: true
  - name: "purpose"
    type: "string"
    required: false

outputs:
  - name: "credential"
    type: "Credential"

slo:
  - metric: "凭据可用率"
    target: ">= 95%"
    scope: "正常账号池"
    degradation: "使用备用账号或提示用户"
  - metric: "会话刷新成功率"
    target: ">= 90%"
    scope: "未被封禁账号"
    degradation: "重新登录或标记账号异常"

tags: ["账号", "会话", "Cookie", "凭据"]
---

# 24-credential-pool.md - 账号会话凭据池

## 模块目标

| 目标 | SLO | 适用范围 | 降级策略 |
|------|-----|----------|----------|
| 提供可用凭据 | 获取成功率 ≥95% | 有效账号池 | 使用备用账号/提示用户 |
| 自动刷新会话 | 刷新成功率 ≥90% | 未封禁账号 | 重新登录/标记异常 |
| 凭据安全存储 | 零明文泄露 | 所有凭据 | 加密失败则不存储 |
| 账号健康管理 | 异常检出率 ≥95% | 活跃账号 | 定期全量检查 |

---

## 一、凭据类型

### 1.1 凭据分类

```
凭据类型
├── 账号凭据 (Account Credentials)
│   ├── 用户名/密码
│   ├── 手机号/验证码
│   └── 第三方OAuth
├── 会话凭据 (Session Credentials)
│   ├── Session Cookie
│   ├── JWT Token
│   └── Access Token
├── 设备凭据 (Device Credentials)
│   ├── 设备ID
│   ├── 设备指纹
│   └── 推送Token
└── API凭据 (API Credentials)
    ├── API Key
    ├── Secret Key
    └── OAuth Client
```

### 1.2 凭据数据模型

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List

class CredentialType(Enum):
    ACCOUNT = "account"       # 账号密码
    SESSION = "session"       # 会话Cookie
    TOKEN = "token"           # Token
    API_KEY = "api_key"       # API密钥
    DEVICE = "device"         # 设备凭据

class CredentialStatus(Enum):
    ACTIVE = "active"         # 正常可用
    COOLING = "cooling"       # 冷却中
    CHALLENGED = "challenged" # 需要验证
    SUSPENDED = "suspended"   # 临时封禁
    BANNED = "banned"         # 永久封禁
    EXPIRED = "expired"       # 已过期

@dataclass
class Credential:
    """凭据基类"""
    id: str
    site: str
    type: CredentialType
    status: CredentialStatus = CredentialStatus.ACTIVE

    # 时间管理
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None

    # 使用统计
    use_count: int = 0
    success_count: int = 0
    fail_count: int = 0

    # 健康度 (0-100)
    health_score: int = 100

    # 关联数据
    metadata: Dict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

@dataclass
class AccountCredential(Credential):
    """账号凭据"""
    username: str = ""
    password: str = ""  # 加密存储
    phone: Optional[str] = None
    email: Optional[str] = None

    # 安全设置
    two_factor_enabled: bool = False
    recovery_codes: List[str] = field(default_factory=list)

@dataclass
class SessionCredential(Credential):
    """会话凭据"""
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    local_storage: Dict[str, str] = field(default_factory=dict)

    # 来源账号
    source_account_id: Optional[str] = None

@dataclass
class TokenCredential(Credential):
    """Token凭据"""
    access_token: str = ""
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    scope: List[str] = field(default_factory=list)
```

---

## 二、凭据池管理

### 2.1 凭据池架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Credential Pool                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Site: jd.com   │  │ Site: taobao    │  │  Site: ...      │ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤ │
│  │ Active: 5       │  │ Active: 3       │  │                 │ │
│  │ Cooling: 2      │  │ Cooling: 1      │  │                 │ │
│  │ Suspended: 1    │  │ Suspended: 0    │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Pool Manager                          │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  - 凭据分配 (Round-robin / Random / Health-based)        │   │
│  │  - 状态追踪 (使用记录 / 成功率 / 冷却)                    │   │
│  │  - 自动刷新 (Session / Token)                            │   │
│  │  - 健康检查 (定期验证 / 异常检测)                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 凭据池实现

```python
from typing import Optional, List
from datetime import datetime, timedelta
import random

class CredentialPool:
    """凭据池管理器"""

    def __init__(self, storage: CredentialStorage):
        self.storage = storage
        self.allocation_strategy = "health_based"  # round_robin | random | health_based

    def get_credential(
        self,
        site: str,
        credential_type: CredentialType = CredentialType.SESSION,
        purpose: str = None
    ) -> Optional[Credential]:
        """获取可用凭据"""

        # 1. 获取该站点所有凭据
        credentials = self.storage.get_by_site(site, credential_type)

        # 2. 过滤可用凭据
        available = [c for c in credentials if self._is_available(c)]

        if not available:
            return None

        # 3. 按策略选择
        if self.allocation_strategy == "round_robin":
            credential = self._select_round_robin(available)
        elif self.allocation_strategy == "random":
            credential = random.choice(available)
        else:  # health_based
            credential = self._select_by_health(available)

        # 4. 标记使用
        self._mark_used(credential, purpose)

        return credential

    def _is_available(self, credential: Credential) -> bool:
        """检查凭据是否可用"""
        now = datetime.now()

        # 状态检查
        if credential.status not in [CredentialStatus.ACTIVE]:
            return False

        # 过期检查
        if credential.expires_at and credential.expires_at < now:
            return False

        # 冷却检查
        if credential.cooldown_until and credential.cooldown_until > now:
            return False

        return True

    def _select_by_health(self, credentials: List[Credential]) -> Credential:
        """按健康度选择 (加权随机)"""
        total_health = sum(c.health_score for c in credentials)
        r = random.uniform(0, total_health)

        cumulative = 0
        for c in credentials:
            cumulative += c.health_score
            if r <= cumulative:
                return c

        return credentials[-1]

    def _mark_used(self, credential: Credential, purpose: str = None):
        """标记凭据使用"""
        credential.last_used_at = datetime.now()
        credential.use_count += 1
        self.storage.update(credential)

    def report_result(
        self,
        credential: Credential,
        success: bool,
        error_type: str = None
    ):
        """报告使用结果"""
        if success:
            credential.success_count += 1
            # 提升健康度
            credential.health_score = min(100, credential.health_score + 1)
        else:
            credential.fail_count += 1
            # 降低健康度
            credential.health_score = max(0, credential.health_score - 10)

            # 特定错误处理
            if error_type == "BLOCKED":
                self._handle_blocked(credential)
            elif error_type == "CHALLENGED":
                self._handle_challenged(credential)
            elif error_type == "EXPIRED":
                self._handle_expired(credential)

        self.storage.update(credential)

    def _handle_blocked(self, credential: Credential):
        """处理被封禁"""
        credential.status = CredentialStatus.SUSPENDED
        credential.cooldown_until = datetime.now() + timedelta(hours=24)

    def _handle_challenged(self, credential: Credential):
        """处理需要验证"""
        credential.status = CredentialStatus.CHALLENGED
        # 触发验证流程 (异步)

    def _handle_expired(self, credential: Credential):
        """处理过期"""
        credential.status = CredentialStatus.EXPIRED
        # 触发刷新流程 (异步)

    def add_cooldown(self, credential: Credential, seconds: int):
        """添加冷却时间"""
        credential.cooldown_until = datetime.now() + timedelta(seconds=seconds)
        self.storage.update(credential)
```

---

## 三、会话生命周期

### 3.1 会话状态机

```
                    ┌──────────────────────────┐
                    │                          │
                    ▼                          │
    ┌─────────┐  登录成功  ┌─────────┐   刷新成功   │
    │  INIT   │──────────►│ ACTIVE  │◄─────────────┘
    └─────────┘            └────┬────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              ▼                 ▼                 ▼
        ┌──────────┐     ┌──────────┐     ┌──────────┐
        │ EXPIRED  │     │CHALLENGED│     │ BLOCKED  │
        └────┬─────┘     └────┬─────┘     └────┬─────┘
             │                │                 │
             │ 刷新           │ 通过验证         │ 冷却结束
             │                │                 │
             └────────────────┴─────────────────┘
                              │
                              ▼
                         ┌─────────┐
                         │ ACTIVE  │
                         └─────────┘

     如果多次失败:
        ┌──────────┐
        │  BANNED  │  (永久封禁，需人工处理)
        └──────────┘
```

### 3.2 会话刷新策略

```python
class SessionRefresher:
    """会话刷新器"""

    # 刷新策略配置
    REFRESH_STRATEGIES = {
        "jd.com": {
            "method": "cookie_refresh",
            "refresh_before_expire": 3600,  # 过期前1小时刷新
            "max_age": 86400 * 7,  # 最长7天
        },
        "taobao.com": {
            "method": "token_refresh",
            "refresh_before_expire": 1800,
            "max_age": 86400 * 30,
        },
        "default": {
            "method": "relogin",
            "refresh_before_expire": 1800,
            "max_age": 86400,
        }
    }

    async def refresh_session(
        self,
        session: SessionCredential
    ) -> tuple[bool, SessionCredential]:
        """刷新会话"""

        strategy = self.REFRESH_STRATEGIES.get(
            session.site,
            self.REFRESH_STRATEGIES["default"]
        )

        if strategy["method"] == "cookie_refresh":
            return await self._refresh_by_cookie(session)
        elif strategy["method"] == "token_refresh":
            return await self._refresh_by_token(session)
        else:
            return await self._refresh_by_relogin(session)

    async def _refresh_by_cookie(
        self,
        session: SessionCredential
    ) -> tuple[bool, SessionCredential]:
        """通过访问刷新Cookie"""
        try:
            # 访问一个会刷新cookie的页面
            response = await self.client.get(
                f"https://{session.site}/",
                cookies=session.cookies
            )

            if response.status_code == 200:
                # 更新cookies
                session.cookies.update(dict(response.cookies))
                session.expires_at = datetime.now() + timedelta(days=7)
                return True, session

            return False, session

        except Exception as e:
            return False, session

    async def _refresh_by_token(
        self,
        session: SessionCredential
    ) -> tuple[bool, SessionCredential]:
        """通过Refresh Token刷新"""
        # 需要关联的TokenCredential
        token = self.get_associated_token(session)
        if not token or not token.refresh_token:
            return False, session

        try:
            # 调用刷新接口
            response = await self.client.post(
                f"https://{session.site}/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": token.refresh_token
                }
            )

            if response.status_code == 200:
                data = response.json()
                token.access_token = data["access_token"]
                token.expires_at = datetime.now() + timedelta(
                    seconds=data.get("expires_in", 3600)
                )
                return True, session

            return False, session

        except Exception:
            return False, session

    async def _refresh_by_relogin(
        self,
        session: SessionCredential
    ) -> tuple[bool, SessionCredential]:
        """重新登录"""
        # 获取关联的账号凭据
        account = self.get_source_account(session)
        if not account:
            return False, session

        # 执行登录流程
        new_session = await self.login_handler.login(
            session.site,
            account
        )

        if new_session:
            return True, new_session

        return False, session
```

---

## 四、登录挑战处理

### 4.1 挑战类型

```python
class ChallengeType(Enum):
    CAPTCHA_IMAGE = "captcha_image"       # 图形验证码
    CAPTCHA_SLIDER = "captcha_slider"     # 滑块验证码
    CAPTCHA_CLICK = "captcha_click"       # 点选验证码
    SMS_CODE = "sms_code"                 # 短信验证码
    EMAIL_CODE = "email_code"             # 邮箱验证码
    TWO_FACTOR = "two_factor"             # 两步验证
    DEVICE_VERIFY = "device_verify"       # 设备验证
    SECURITY_QUESTION = "security_question"  # 安全问题
```

### 4.2 挑战处理器

```python
class ChallengeHandler:
    """登录挑战处理器"""

    def __init__(self, captcha_solver, notification_service):
        self.captcha_solver = captcha_solver
        self.notification = notification_service

    async def handle_challenge(
        self,
        challenge_type: ChallengeType,
        challenge_data: dict,
        credential: Credential
    ) -> tuple[bool, str]:
        """处理登录挑战"""

        if challenge_type == ChallengeType.CAPTCHA_IMAGE:
            return await self._handle_image_captcha(challenge_data)

        elif challenge_type == ChallengeType.CAPTCHA_SLIDER:
            return await self._handle_slider_captcha(challenge_data)

        elif challenge_type == ChallengeType.SMS_CODE:
            return await self._handle_sms_code(challenge_data, credential)

        elif challenge_type == ChallengeType.TWO_FACTOR:
            return await self._handle_two_factor(challenge_data, credential)

        else:
            # 无法自动处理，请求人工介入
            return await self._request_human_intervention(
                challenge_type, challenge_data, credential
            )

    async def _handle_image_captcha(self, data: dict) -> tuple[bool, str]:
        """处理图形验证码"""
        image_url = data.get("image_url")
        image_data = data.get("image_data")

        if image_data:
            code = await self.captcha_solver.solve_image(image_data)
        elif image_url:
            image = await self.fetch_image(image_url)
            code = await self.captcha_solver.solve_image(image)
        else:
            return False, ""

        return True, code

    async def _handle_slider_captcha(self, data: dict) -> tuple[bool, str]:
        """处理滑块验证码"""
        bg_image = data.get("bg_image")
        slider_image = data.get("slider_image")

        if not bg_image or not slider_image:
            return False, ""

        # 计算滑动距离
        distance = await self.captcha_solver.solve_slider(bg_image, slider_image)

        # 生成滑动轨迹
        track = self._generate_slider_track(distance)

        return True, {"distance": distance, "track": track}

    async def _handle_sms_code(
        self,
        data: dict,
        credential: Credential
    ) -> tuple[bool, str]:
        """处理短信验证码"""
        phone = credential.phone if hasattr(credential, 'phone') else None

        if not phone:
            return False, ""

        # 请求发送短信
        await self._trigger_sms(data.get("send_url"), phone)

        # 等待用户输入 (通过通知服务)
        code = await self.notification.request_input(
            title="需要短信验证码",
            message=f"请输入发送到 {phone[-4:].rjust(11, '*')} 的验证码",
            timeout=300  # 5分钟超时
        )

        if code:
            return True, code

        return False, ""

    async def _request_human_intervention(
        self,
        challenge_type: ChallengeType,
        data: dict,
        credential: Credential
    ) -> tuple[bool, str]:
        """请求人工介入"""

        # 发送通知
        await self.notification.send_alert(
            level="warning",
            title=f"需要人工处理: {challenge_type.value}",
            message=f"账号 {credential.id} 遇到无法自动处理的挑战",
            data=data
        )

        # 标记凭据状态
        credential.status = CredentialStatus.CHALLENGED

        # 等待人工处理
        result = await self.notification.wait_for_response(
            credential.id,
            timeout=3600  # 1小时超时
        )

        return result is not None, result or ""

    def _generate_slider_track(self, distance: int) -> list:
        """生成人类化滑动轨迹"""
        track = []
        current = 0
        t = 0

        # 加速阶段
        while current < distance * 0.7:
            move = random.randint(5, 15)
            current += move
            t += random.randint(10, 30)
            track.append({"x": current, "y": random.randint(-2, 2), "t": t})

        # 减速阶段
        while current < distance:
            move = random.randint(1, 5)
            current = min(current + move, distance)
            t += random.randint(30, 80)
            track.append({"x": current, "y": random.randint(-1, 1), "t": t})

        return track
```

---

## 五、安全存储

### 5.1 加密存储

```python
from cryptography.fernet import Fernet
import json
import os

class SecureCredentialStorage:
    """安全凭据存储"""

    def __init__(self, encryption_key: bytes = None):
        if encryption_key:
            self.fernet = Fernet(encryption_key)
        else:
            # 从环境变量获取或生成
            key = os.getenv("CREDENTIAL_ENCRYPTION_KEY")
            if not key:
                key = Fernet.generate_key()
                print(f"警告: 使用临时密钥，请设置 CREDENTIAL_ENCRYPTION_KEY")
            self.fernet = Fernet(key)

    def encrypt_credential(self, credential: Credential) -> bytes:
        """加密凭据"""
        # 提取敏感字段
        sensitive_data = self._extract_sensitive(credential)

        # 加密
        encrypted = self.fernet.encrypt(
            json.dumps(sensitive_data).encode()
        )

        return encrypted

    def decrypt_credential(self, encrypted: bytes, credential_type: type) -> Credential:
        """解密凭据"""
        decrypted = self.fernet.decrypt(encrypted)
        data = json.loads(decrypted.decode())

        return credential_type(**data)

    def _extract_sensitive(self, credential: Credential) -> dict:
        """提取敏感字段"""
        sensitive_fields = {
            "password", "cookies", "access_token", "refresh_token",
            "api_key", "secret_key", "recovery_codes"
        }

        data = {}
        for field, value in credential.__dict__.items():
            if field in sensitive_fields:
                data[field] = value

        return data

    def save(self, credential: Credential, path: str):
        """保存凭据到文件"""
        encrypted = self.encrypt_credential(credential)

        # 非敏感数据明文存储
        metadata = {
            "id": credential.id,
            "site": credential.site,
            "type": credential.type.value,
            "status": credential.status.value,
            "created_at": credential.created_at.isoformat(),
            # 敏感数据加密
            "encrypted_data": encrypted.decode()
        }

        with open(path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def load(self, path: str) -> Credential:
        """从文件加载凭据"""
        with open(path) as f:
            metadata = json.load(f)

        encrypted = metadata["encrypted_data"].encode()
        credential_type = self._get_credential_type(metadata["type"])

        credential = self.decrypt_credential(encrypted, credential_type)

        # 恢复非敏感字段
        credential.id = metadata["id"]
        credential.site = metadata["site"]
        credential.status = CredentialStatus(metadata["status"])

        return credential
```

### 5.2 最小泄露原则

```python
class CredentialAccessControl:
    """凭据访问控制"""

    # 凭据字段访问级别
    ACCESS_LEVELS = {
        "public": ["id", "site", "type", "status", "health_score"],
        "internal": ["created_at", "last_used_at", "use_count"],
        "sensitive": ["cookies", "headers"],
        "secret": ["password", "access_token", "refresh_token", "api_key"]
    }

    def get_safe_view(
        self,
        credential: Credential,
        access_level: str = "public"
    ) -> dict:
        """获取安全视图 (隐藏敏感字段)"""
        allowed_fields = set()

        if access_level == "public":
            allowed_fields = set(self.ACCESS_LEVELS["public"])
        elif access_level == "internal":
            allowed_fields = set(
                self.ACCESS_LEVELS["public"] +
                self.ACCESS_LEVELS["internal"]
            )
        elif access_level == "sensitive":
            allowed_fields = set(
                self.ACCESS_LEVELS["public"] +
                self.ACCESS_LEVELS["internal"] +
                self.ACCESS_LEVELS["sensitive"]
            )
        # secret 级别需要特殊权限

        result = {}
        for field, value in credential.__dict__.items():
            if field in allowed_fields:
                result[field] = value
            elif field in self.ACCESS_LEVELS["secret"]:
                result[field] = "***REDACTED***"
            elif field in self.ACCESS_LEVELS["sensitive"]:
                result[field] = self._mask_sensitive(value)

        return result

    def _mask_sensitive(self, value) -> str:
        """掩码敏感值"""
        if isinstance(value, dict):
            return {k: "***" for k in value.keys()}
        elif isinstance(value, str):
            if len(value) > 8:
                return value[:4] + "***" + value[-4:]
            return "***"
        return "***"
```

---

## 六、Skill 交互

### 上游

| 调用者 | 场景 | 传入数据 |
|--------|------|----------|
| 04-request | 需要登录态请求 | site, purpose |
| 18-brain | 任务需要账号 | site, requirements |

### 下游

| 被调用者 | 场景 | 传出数据 |
|----------|------|----------|
| 10-captcha | 登录验证码 | captcha_data |
| 15-compliance | 凭据脱敏 | raw_credential |

### 接口定义

```python
# 输入
class GetCredentialRequest:
    site: str
    credential_type: CredentialType = CredentialType.SESSION
    purpose: str = None
    prefer_fresh: bool = False

# 输出
class GetCredentialResponse:
    status: str  # success | no_available | all_blocked
    credential: Optional[Credential]
    alternatives: List[str]  # 备选方案建议
    warnings: List[str]
```

---

## 七、诊断日志

```
# 凭据获取
[CRED] 请求凭据: site={site}, type={type}
[CRED] 可用凭据: {count}个
[CRED] 选择凭据: {credential_id}, health={health_score}

# 会话刷新
[CRED] 会话即将过期: {credential_id}, expires_in={seconds}s
[CRED] 开始刷新会话: method={method}
[CRED] 刷新结果: {success}, new_expires={expires_at}

# 挑战处理
[CRED] 遇到挑战: {challenge_type}
[CRED] 处理挑战: {handler}
[CRED] 挑战结果: {success}

# 异常情况
[CRED] 凭据被封禁: {credential_id}, reason={reason}
[CRED] 无可用凭据: site={site}, total={total}, blocked={blocked}
[CRED] 健康度下降: {credential_id}, {old_score} -> {new_score}
```

---

## 八、配置选项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `credential.storage_path` | string | "./credentials" | 存储路径 |
| `credential.encryption_key` | string | env | 加密密钥 |
| `credential.allocation_strategy` | string | "health_based" | 分配策略 |
| `credential.cooldown_seconds` | int | 300 | 默认冷却时间 |
| `credential.health_check_interval` | int | 3600 | 健康检查间隔 |
| `credential.auto_refresh` | bool | true | 自动刷新会话 |

---

## 变更历史

| 版本 | 日期 | 变更类型 | 说明 |
|------|------|----------|------|
| 1.0.0 | 2026-01-27 | initial | 初始版本 |

---

## 关联模块

- **15-compliance.md** - 凭据安全
- **10-captcha.md** - 验证码处理
- **04-request.md** - 请求使用凭据
- **06-storage.md** - 会话持久化
