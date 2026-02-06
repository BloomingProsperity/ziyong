# Huakai-AI 中转站 - 完整部署文档

> 本文档供 AI 助手在新机器上快速部署使用。包含所有服务、配置、踩坑记录。

---

## 一、项目架构总览

```
用户 (Cursor/API客户端)
  ↓ HTTPS
Cloudflare Tunnel (api.huakai123.com)
  ↓ HTTP
New API 网关 (:3001) ← 统一入口，API Key 管理、计费
  ├── Clove-Max  (:5202) ← 1个 Claude Max 账号  ← 日本静态IP-B  [Opus + Sonnet]
  ├── Clove-Pro  (:5201) ← 2个 Claude Pro 账号  ← 日本静态IP-A  [仅 Sonnet]
  ├── Codex-1    (:5005) ← 3个 GPT/Codex 账号   ← 日本静态IP-C
  ├── Codex-2    (:5006) ← Claude OAuth 账号     ← 日本静态IP-D  [仅 Sonnet]
  └── Anti-API   (:8964) ← 3个 Antigravity 账号  ← 日本静态IP-E
```

### 关键结论（踩坑总结）

1. **Claude Opus 只有 Max 账户能用**。Pro 账户通过任何反代（CLIProxyAPI、Clove）都只能出 Sonnet。
2. **Clove 有两种模式**：OAuth(CLI) 模式和网页反代模式。添加 Cookie 走网页反代，需要完成 OAuth 认证才走 CLI 模式。
3. **CLIProxyAPI 的 Claude OAuth 被 Anthropic 限制**：2026年1月起，第三方工具使用 OAuth 请求 Opus 会被降级为 Sonnet。
4. **Cloudflare Tunnel 必须用 QUIC 协议**，HTTP/2 会出现 TLS handshake EOF 错误。
5. **Clash TUN 模式会拦截 Cloudflare Tunnel 流量**，必须在路由排除中添加所有 Cloudflare IP 段。
6. **CLIProxyAPI 不支持 socks5h**，必须用 `socks5://`。

---

## 二、前置条件

### 2.1 软件要求
- Windows 10/11（或 Linux）
- Docker Desktop（含 Docker Compose）
- Cloudflared（推荐 v2026.1.2+，使用 QUIC 协议）
- Clash for Windows（如使用代理上网）
- Git

### 2.2 账号要求
- **Claude 账号**：至少 1 个 Max（用于 Opus），2 个 Pro（用于 Sonnet）
- **GPT/Codex 账号**：ChatGPT Plus/Pro 账号若干
- **Antigravity 账号**：Google 账号若干
- **Cloudflare 账号**：绑定域名 huakai123.com
- **IPRoyal 静态住宅代理**：日本节点若干

### 2.3 代理 IP 分配（IPRoyal 日本静态住宅）

| 组 | 服务 | IP | 端口 | 认证 |
|----|------|----|------|------|
| A | Clove-Pro | 175.29.206.206 | 12324 | 14aea1862cd31:2123e0e0cf |
| B | Clove-Max | 175.29.207.212 | 12324 | 14aea1862cd31:2123e0e0cf |
| C | Codex-1 (GPT) | 175.29.203.124 | 12324 | 14aea1862cd31:2123e0e0cf |
| D | Codex-2 (Claude) | 175.29.206.28 | 12324 | 14aea1862cd31:2123e0e0cf |
| E | Anti-API | 175.29.200.253 | 12324 | 14aea1862cd31:2123e0e0cf |

> 格式：`socks5://用户名:密码@IP:端口`（注意：CLIProxyAPI 不支持 socks5h，Clove 支持 socks5h）

---

## 三、端口映射表

| 宿主端口 | 容器端口 | 服务 | 用途 |
|----------|----------|------|------|
| 3001 | 3000 | new-api | API 网关（统一入口） |
| 5201 | 5201 | clove-pro | Claude Pro 反代 |
| 5202 | 5201 | clove-max | Claude Max 反代 |
| 5005 | 8317 | codex-1 | GPT/Codex 代理 |
| 5006 | 8317 | codex-2 | Claude CLIProxyAPI |
| 1455 | 1455 | codex-1 | OAuth 回调 |
| 1456 | 1455 | codex-2 | OAuth 回调 |
| 54545 | 54545 | codex-2 | Claude OAuth 回调 |
| 8964 | 8964 | anti-api | Antigravity |
| 51121 | 51121 | anti-api | Antigravity OAuth |

---

## 四、部署步骤

### 4.1 克隆项目

```bash
git clone https://github.com/BloomingProsperity/ziyong.git
cd ziyong
```

### 4.2 准备目录结构

确保以下目录存在：
```bash
mkdir -p cli-proxy-api/auth-1
mkdir -p cli-proxy-api/auth-2
mkdir -p clove/data-pro
mkdir -p clove/data-max
mkdir -p antigravity/data
mkdir -p new-api/data
```

### 4.3 启动核心服务

```bash
# 启动所有服务
docker-compose up -d

# 或者逐个启动
docker-compose up -d new-api      # 先启动网关
docker-compose up -d clove-pro    # Claude Pro
docker-compose up -d clove-max    # Claude Max (Opus)
docker-compose up -d codex-1      # GPT
docker-compose up -d anti-api     # Antigravity
```

### 4.4 添加账号

#### Clove（Claude Pro/Max）

1. 浏览器打开 Clove 管理页面：
   - Pro: http://localhost:5201 密钥: `sk-1m7c09yOPIlV4C10SnYO1II04Cxqf6fg`
   - Max: http://localhost:5202 密钥: `sk-KMq95WvrUmhSdwRqkOdOMxpdljJh02wH`

2. 获取 Cookie：
   - 登录 https://claude.ai
   - F12 → Application → Cookies → claude.ai → 复制 `sessionKey` 的值
   - 格式: `sessionKey=sk-ant-sid01-xxxxxxx`

3. 在 Clove 管理页面「添加 Cookie」，粘贴完整的 `sessionKey=sk-ant-sid01-xxx`

4. **重要：完成 OAuth 认证**（否则只走网页反代，Max 才能出 Opus）
   - 在 Clove 管理页面点击账号的「OAuth 认证」按钮
   - 完成浏览器授权流程

#### CLIProxyAPI（GPT/Codex）

```bash
# 进入容器进行 OAuth 登录
docker exec -it codex-1 sh
./CLIProxyAPI --codex-login
# 按提示在浏览器完成登录

# Claude 账号（如需要）
docker exec -it codex-2 sh
./CLIProxyAPI --claude-login
```

#### Antigravity（Google/Gemini）

打开 http://localhost:8964，按提示添加 Google 账号。

### 4.5 配置 New API 网关

打开 http://localhost:3001 进入管理后台。

#### 添加渠道

**渠道 1 - Claude Opus（走 Clove Max）**
- 名称: `Claude-Opus`
- 类型: `Anthropic Claude`
- Base URL: `http://clove-max:5201`
- 密钥: `sk-KMq95WvrUmhSdwRqkOdOMxpdljJh02wH`
- 模型: `claude-opus-4-5-20251101`

**渠道 2 - Claude Sonnet（走 Clove Pro）**
- 名称: `Claude-Sonnet`
- 类型: `Anthropic Claude`
- Base URL: `http://clove-pro:5201`
- 密钥: `sk-1m7c09yOPIlV4C10SnYO1II04Cxqf6fg`
- 模型: `claude-sonnet-4-5-20250929`

**渠道 3 - GPT（走 Codex-1）**
- 名称: `GPT-Codex`
- 类型: `OpenAI`
- Base URL: `http://codex-1:8317`
- 密钥: `sk-t62tslySgJ1ZaesZF1D608QHFs1xXxjj`
- 模型: 按需添加 GPT 模型名

#### 创建令牌

给用户创建令牌（sk-xxx），设置可用模型和额度。

#### 模型倍率

如果提示「模型倍率未配置」，需要在 **设置 → 运营设置 → 模型倍率** 中添加：
```
claude-opus-4-5-20251101=1
claude-sonnet-4-5-20250929=1
```
或者开启**自用模式**跳过计费。

---

## 五、Cloudflare Tunnel 配置

### 5.1 安装 Cloudflared

下载 cloudflared v2026.1.2+：https://github.com/cloudflare/cloudflared/releases

### 5.2 创建 Tunnel（首次）

```bash
cloudflared tunnel login
cloudflared tunnel create huakai-api
```

### 5.3 配置文件

文件位置: `~/.cloudflared/config.yml`

```yaml
tunnel: <你的tunnel-id>
credentials-file: ~/.cloudflared/<tunnel-id>.json
protocol: quic    # 必须用 QUIC！HTTP/2 会 TLS handshake EOF

ingress:
  - hostname: api.huakai123.com
    service: http://localhost:3001
  - hostname: huakai123.com
    service: http://localhost:8080
  - hostname: www.huakai123.com
    service: http://localhost:8080
  - service: http_status:404
```

### 5.4 DNS 配置

在 Cloudflare Dashboard 添加 CNAME：
```
api.huakai123.com  → <tunnel-id>.cfargotunnel.com
huakai123.com      → <tunnel-id>.cfargotunnel.com
www.huakai123.com  → <tunnel-id>.cfargotunnel.com
```

### 5.5 启动 Tunnel

```bash
# 前台运行
cloudflared tunnel run

# 后台运行（Windows）
powershell -Command "Start-Process cloudflared -ArgumentList 'tunnel','run' -WindowStyle Hidden"

# 安装为系统服务（推荐）
cloudflared service install
```

---

## 六、网络问题排查（重要！）

### 6.1 Clash TUN 模式冲突

**问题**：Clash TUN 模式会拦截 Cloudflare Tunnel 的流量，导致 TLS handshake 失败。

**解决方案**：在 Clash 配置 `cfw-settings.yaml` 中添加路由排除：

```yaml
cfw-bypass:
  - localhost
  - 127.*
  - 10.*
  - 172.16.*
  - 172.17.*
  - 172.18.*
  - 172.19.*
  - 172.20.*
  - 192.168.*
  - <local>

# TUN 模式路由排除
inet4-route-exclude-address:
  - 127.0.0.0/8
  # IPRoyal 代理 IP（直连，不经过 Clash）
  - 175.29.203.124/32
  - 175.29.206.206/32
  - 175.29.207.212/32
  - 175.29.206.28/32
  - 175.29.200.253/32
  # Cloudflare 全部 IP 段（必须排除！否则 Tunnel 无法连接）
  - 173.245.48.0/20
  - 103.21.244.0/22
  - 103.22.200.0/22
  - 103.31.4.0/22
  - 141.101.64.0/18
  - 108.162.192.0/18
  - 190.93.240.0/20
  - 188.114.96.0/20
  - 197.234.240.0/22
  - 198.41.128.0/17
  - 162.158.0.0/15
  - 104.16.0.0/13
  - 104.24.0.0/14
  - 172.64.0.0/13
```

### 6.2 Cloudflare Tunnel 协议

**必须使用 QUIC**。如果用 HTTP/2 会出现：
```
TLS handshake with edge error: EOF
```

在 config.yml 中设置：
```yaml
protocol: quic
```

### 6.3 CLIProxyAPI 代理协议

**不支持 socks5h**，只支持 `socks5://`。如果用 socks5h 会报错：
```
unsupported proxy scheme: socks5h
```

### 6.4 Docker 内部网络

New API 连接下游服务时必须用 **Docker 容器名**，不要用 localhost：
```
正确: http://clove-max:5201
错误: http://localhost:5202
```

### 6.5 延迟优化

- 通过 Docker 内部网络（容器名）路由，避免走宿主机端口绕一圈
- Cloudflare Tunnel 公网访问会增加 1-3 秒延迟
- 代理 IP 本身有 1-2 秒延迟

---

## 七、服务 API Key 汇总

| 服务 | 密钥 | 用途 |
|------|------|------|
| Clove Pro | `sk-1m7c09yOPIlV4C10SnYO1II04Cxqf6fg` | New API 连接用 |
| Clove Max | `sk-KMq95WvrUmhSdwRqkOdOMxpdljJh02wH` | New API 连接用 |
| Codex-1 (GPT) | `sk-t62tslySgJ1ZaesZF1D608QHFs1xXxjj` | New API 连接用 |
| Codex-2 (Claude) | `sk-claude-huakai-2024` | New API 连接用 |
| New API Session | `@njIJcImSeD3golbGFDz01S5xCaBGXZ@l9Nhngi40` | 环境变量 |

---

## 八、给用户的接入信息

```
API 地址: https://api.huakai123.com/v1
API 密钥: （在 New API 后台创建令牌）
可用模型:
  - claude-opus-4-5-20251101  (Claude Opus，最强推理)
  - claude-sonnet-4-5-20250929 (Claude Sonnet，日常编码)
  - gpt-5-codex 等 GPT 模型

Cursor 配置:
  Settings → Models → OpenAI API Key → 填入 sk-xxx
  Base URL → https://api.huakai123.com/v1
```

---

## 九、模型路由策略

| 用户请求模型 | New API 渠道 | 上游服务 | 实际模型 |
|-------------|-------------|----------|---------|
| claude-opus-4-5-20251101 | Claude-Opus | Clove Max (5202) | 真 Opus |
| claude-sonnet-4-5-20250929 | Claude-Sonnet | Clove Pro (5201) | 真 Sonnet |
| gpt-5-* | GPT-Codex | Codex-1 (5005) | GPT |

**重要**：不要把 Pro 账号分配给 Opus 渠道，Pro 出不了真 Opus！

---

## 十、常用运维命令

```bash
# 查看所有容器状态
docker ps

# 查看某服务日志
docker logs clove-max --tail 50
docker logs codex-1 --tail 50

# 重启服务
docker-compose restart clove-max

# 重建服务（配置变更后）
docker-compose up -d --force-recreate clove-max

# 更新镜像
docker-compose pull
docker-compose up -d

# 启动 Cloudflare Tunnel
cloudflared tunnel run

# 测试 API（本地）
curl http://localhost:3001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-用户令牌" \
  -d '{"model":"claude-sonnet-4-5-20250929","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'

# 测试 API（公网）
curl https://api.huakai123.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-用户令牌" \
  -d '{"model":"claude-opus-4-5-20251101","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
```

---

## 十一、文件结构

```
ziyong/
├── docker-compose.yml          # 主编排文件（核心）
├── DEPLOYMENT.md               # 本文档
├── .gitignore
│
├── clove/                      # Clove 反代（Claude）
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── data-pro/               # Pro 账号数据（需添加 Cookie）
│   └── data-max/               # Max 账号数据（需添加 Cookie）
│
├── cli-proxy-api/              # CLIProxyAPI（GPT + Claude）
│   ├── config-1/config.yaml    # GPT 组配置
│   ├── config-2/config.yaml    # Claude 组配置
│   ├── auth-1/                 # GPT OAuth token（需登录生成）
│   └── auth-2/                 # Claude OAuth token（需登录生成）
│
├── new-api/                    # New API 网关
│   ├── docker-compose.yml
│   └── data/                   # SQLite 数据库
│
├── antigravity/                # Antigravity（Google/Gemini）
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── data/
│
├── claude-code-proxy/          # Claude Code Proxy（备用）
│   ├── docker-compose.yml
│   └── server/
│
├── website/                    # 落地页
│   ├── index.html
│   └── style.css
│
├── ai-proxy/                   # 邮箱注册工具等
├── fuclaude/                   # FuClaude + Nginx + WireGuard
├── clawdbot/                   # OpenClaw
└── openclaw_data/              # OpenClaw 数据
```

---

## 十二、踩坑记录

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| Cloudflare Tunnel TLS handshake EOF | 使用了 HTTP/2 协议 | 改为 `protocol: quic` |
| Tunnel 连不上 | Clash TUN 拦截了 Cloudflare IP | 在 Clash 路由排除中加 Cloudflare IP 段 |
| New API 连接超时 | 渠道 Base URL 用了外部地址 | 改为 Docker 容器名 `http://clove-max:5201` |
| CLIProxyAPI 代理报错 | 使用了 socks5h 协议 | 改为 `socks5://` |
| 请求 Opus 返回 Sonnet | Pro 账户无 Opus 权限 | Opus 必须用 Max 账户 |
| Claude 自我识别为 Sonnet | CLIProxyAPI 的已知问题 | 用 Clove 替代 CLIProxyAPI |
| 模型倍率未配置 | New API 需要模型定价 | 设置模型倍率或开自用模式 |
| GitHub 推送被拒 | 代码含 Anthropic Session ID | .gitignore 排除敏感文件 |
