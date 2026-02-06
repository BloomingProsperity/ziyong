# 多账号环境隔离部署指南

## 架构图

```
用户 → Cloudflare Tunnel → New API (:3001) 统一入口
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    Claude 渠道          GPT 渠道         Antigravity 渠道
     │        │          │        │              │
  clove-pro  clove-max  chat2api-1 chat2api-2  anti-api
  (:5201)    (:5202)    (:5005)    (:5006)     (:8964)
  2个Pro     1个Max     2-3个GPT   2-3个GPT    3个Google
     │        │          │        │              │
  IP-A      IP-B       IP-C     IP-D          IP-E
```

## 环境隔离说明

| 隔离维度 | 实现方式 |
|----------|----------|
| **网络隔离** | 每组服务独立 Docker 网络，容器互不可见 |
| **IP 隔离** | 每组服务配独立静态代理 IP |
| **数据隔离** | 每个实例独立 data 目录，互不干扰 |
| **密钥隔离** | 每个实例独立 API Key |
| **指纹隔离** | clove 自带 TLS/UA 伪装；chat2api 独立实例 |

## 第一步：购买静态 IP

需要 5 个美国静态住宅 IP（SOCKS5 协议），推荐：
- Proxy-Cheap: https://www.proxy-cheap.com/services/static-residential-proxies
- Webshare: https://www.webshare.io/features/socks5-proxy

买到后记录格式为: `socks5://用户名:密码@IP:端口`

## 第二步：修改配置

编辑 `docker-compose.isolated.yml`：

1. 填入每组的 `PROXY_URL`（取消注释并替换）
2. 修改每组的 `API_KEYS` 为强密码
3. 修改 `SESSION_SECRET` 为强密码

## 第三步：创建数据目录

```bash
mkdir -p clove/data-pro clove/data-max
mkdir -p ai-proxy/gpt-proxy/data-1 ai-proxy/gpt-proxy/data-2
mkdir -p antigravity/data
```

## 第四步：启动所有服务

```bash
docker compose -f docker-compose.isolated.yml up -d
```

## 第五步：添加账号

### Claude 账号（clove-pro / clove-max）

通过 API 添加 Cookie：

```bash
# 添加到 clove-pro（Pro 账号）
curl -X POST http://localhost:5201/accounts \
  -H "Authorization: Bearer sk-clove-pro-changeme" \
  -H "Content-Type: application/json" \
  -d '{"cookie": "第1个Pro账号的cookie"}'

curl -X POST http://localhost:5201/accounts \
  -H "Authorization: Bearer sk-clove-pro-changeme" \
  -H "Content-Type: application/json" \
  -d '{"cookie": "第2个Pro账号的cookie"}'

# 添加到 clove-max（Max 账号）
curl -X POST http://localhost:5202/accounts \
  -H "Authorization: Bearer sk-clove-max-changeme" \
  -H "Content-Type: application/json" \
  -d '{"cookie": "Max账号的cookie"}'
```

### GPT 账号（chat2api）

启动后访问 Token 管理接口添加：

- chat2api-1: http://localhost:5005/tokens
- chat2api-2: http://localhost:5006/tokens

### Antigravity 账号（anti-api）

访问管理面板添加 Google 账号：

- 面板: http://localhost:8964/quota
- 路由: http://localhost:8964/routing

## 第六步：配置 New API 渠道

在 http://localhost:3001 → 渠道管理 → 添加渠道：

| 渠道名称 | 类型 | Base URL | API Key |
|----------|------|----------|---------|
| Claude-Pro | Anthropic Claude | `http://clove-pro:5201` | sk-clove-pro-changeme |
| Claude-Max | Anthropic Claude | `http://clove-max:5201` | sk-clove-max-changeme |
| GPT-组1 | 自定义 | `http://chat2api-1:5005/v1` | sk-gpt-group1-changeme |
| GPT-组2 | 自定义 | `http://chat2api-2:5005/v1` | sk-gpt-group2-changeme |
| Antigravity | 自定义 | `http://anti-api:8964` | (看anti-api的配置) |

> 注意：因为都在 gateway-net 网络里，New API 可以直接用容器名访问，不需要 host.docker.internal

## 日常维护

### 查看状态
```bash
docker compose -f docker-compose.isolated.yml ps
```

### 查看日志
```bash
docker compose -f docker-compose.isolated.yml logs -f clove-pro
docker compose -f docker-compose.isolated.yml logs -f chat2api-1
```

### 重启某个服务
```bash
docker compose -f docker-compose.isolated.yml restart clove-pro
```

### 停止所有服务
```bash
docker compose -f docker-compose.isolated.yml down
```
