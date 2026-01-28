# 🐳 Ultra Pachong Docker 部署指南

**更新日期**: 2026-01-28

---

## 📋 目录

1. [快速开始](#快速开始)
2. [生产环境部署](#生产环境部署)
3. [开发环境配置](#开发环境配置)
4. [配置说明](#配置说明)
5. [常见问题](#常见问题)
6. [性能优化](#性能优化)

---

## 🚀 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

### 一键启动

```bash
# 1. 克隆/进入项目目录
cd "New Python"

# 2. 复制环境变量配置
cp .env.example .env

# 3. 编辑配置（可选）
nano .env

# 4. 构建并启动
docker-compose up -d

# 5. 查看日志
docker-compose logs -f ultra-pachong

# 6. 验证运行状态
docker-compose ps
```

### 停止服务

```bash
# 停止但保留数据
docker-compose stop

# 停止并删除容器（保留数据卷）
docker-compose down

# 停止并删除所有数据
docker-compose down -v
```

---

## 🏢 生产环境部署

### 完整部署（带数据库和缓存）

```bash
# 启动所有服务
docker-compose up -d ultra-pachong redis postgres

# 查看所有服务状态
docker-compose ps

# 服务说明:
# - ultra-pachong: 主应用（必须）
# - redis: 缓存和队列（推荐）
# - postgres: 知识库持久化（推荐）
```

### 仅核心服务部署

```bash
# 只启动主应用（不依赖数据库）
docker-compose up -d ultra-pachong
```

### 健康检查

```bash
# 检查容器健康状态
docker-compose ps

# 手动健康检查
docker exec ultra-pachong python -c "
from unified_agent.api.orchestrator import AgentOrchestrator
agent = AgentOrchestrator()
print('✅ Ultra Pachong is healthy')
"

# 查看资源使用
docker stats ultra-pachong
```

### 扩容部署

```bash
# 启动多个实例（负载均衡）
docker-compose up -d --scale ultra-pachong=3

# 使用nginx作为负载均衡器
# 需要额外配置nginx.conf
```

---

## 💻 开发环境配置

### 使用开发版Dockerfile

```bash
# 构建开发镜像
docker build -f Dockerfile.dev -t ultra-pachong:dev .

# 启动开发容器（交互模式）
docker run -it --rm \
  -v $(pwd):/app \
  -v ultra-pachong-dev-cache:/app/cache \
  -p 8000:8000 \
  -p 5678:5678 \
  --name ultra-pachong-dev \
  ultra-pachong:dev

# 在容器内运行测试
pytest tests/ -v

# 在容器内启动应用
python -m unified_agent
```

### 开发环境特性

开发镜像 (`Dockerfile.dev`) 包含:
- ✅ 完整的调试工具 (ipdb, ipython)
- ✅ 代码质量工具 (black, flake8, mypy)
- ✅ 性能分析工具 (py-spy, memory-profiler)
- ✅ 多浏览器支持 (chromium + firefox)
- ✅ 交互式shell

---

## ⚙️ 配置说明

### 环境变量

在 `.env` 文件中配置：

```bash
# === 代理配置 ===
PROXY_ENABLED=true
PROXY_SERVER=http://proxy.example.com:8080
KUAIDAILI_API_KEY=your_api_key

# === 浏览器配置 ===
HEADLESS=true              # 无头模式
BROWSER_TIMEOUT=30000      # 超时时间(ms)

# === 日志配置 ===
LOG_LEVEL=INFO            # DEBUG/INFO/WARNING/ERROR

# === 数据库配置 ===
DB_USER=pachong
DB_PASSWORD=secure_password
DB_HOST=postgres
DB_PORT=5432

# === 第三方服务 ===
CAPTCHA_API_KEY=your_key
OPENAI_API_KEY=your_key

# === 性能配置 ===
MAX_CONCURRENCY=10
RATE_LIMIT=5.0
```

### 卷挂载说明

```yaml
volumes:
  - ./data:/app/data           # 数据持久化
  - ./logs:/app/logs           # 日志文件
  - ./cache:/app/cache         # 缓存数据
  - ./knowledge:/app/knowledge # 知识库
  - ./config:/app/config:ro    # 配置文件(只读)
```

### 资源限制

在 `docker-compose.yml` 中调整：

```yaml
deploy:
  resources:
    limits:
      cpus: '2'      # 最大CPU核心数
      memory: 4G     # 最大内存
    reservations:
      cpus: '1'      # 预留CPU
      memory: 2G     # 预留内存
```

---

## 🔍 常见问题

### 1. Playwright浏览器未安装

**症状**: `Executable doesn't exist at ...`

**解决方案**:
```bash
# 进入容器手动安装
docker exec -it ultra-pachong bash
playwright install chromium

# 或重新构建镜像
docker-compose build --no-cache ultra-pachong
```

### 2. 内存不足

**症状**: 容器频繁重启，OOM错误

**解决方案**:
```bash
# 增加内存限制（docker-compose.yml）
memory: 8G  # 改为8GB

# 或减少并发数（.env）
MAX_CONCURRENCY=5
```

### 3. 数据库连接失败

**症状**: `could not connect to server`

**解决方案**:
```bash
# 检查postgres容器状态
docker-compose ps postgres

# 查看postgres日志
docker-compose logs postgres

# 确认网络连接
docker exec ultra-pachong nc -zv postgres 5432
```

### 4. 无法访问外网

**症状**: 请求超时，无法抓取

**解决方案**:
```bash
# 检查Docker网络
docker network inspect ultra-pachong_ultra-pachong-network

# 测试网络连通性
docker exec ultra-pachong curl -I https://www.baidu.com

# 配置代理（.env）
PROXY_ENABLED=true
PROXY_SERVER=http://your-proxy:8080
```

### 5. 权限问题

**症状**: `Permission denied` 错误

**解决方案**:
```bash
# 修复宿主机目录权限
sudo chown -R $(id -u):$(id -g) data/ logs/ cache/

# 或在Dockerfile中设置用户
USER 1000:1000
```

---

## 🚄 性能优化

### 1. 镜像大小优化

```dockerfile
# 使用多阶段构建
FROM python:3.11-slim as builder
...

FROM python:3.11-slim
COPY --from=builder ...
```

### 2. 构建缓存优化

```bash
# 使用BuildKit
DOCKER_BUILDKIT=1 docker-compose build

# 清理旧镜像
docker image prune -a
```

### 3. 网络性能优化

```yaml
# docker-compose.yml
networks:
  ultra-pachong-network:
    driver: bridge
    driver_opts:
      com.docker.network.driver.mtu: 1500
```

### 4. 存储性能优化

```yaml
# 使用tmpfs加速临时文件
services:
  ultra-pachong:
    tmpfs:
      - /tmp
      - /app/cache:size=1G
```

### 5. 日志性能优化

```yaml
# 限制日志大小
logging:
  driver: "json-file"
  options:
    max-size: "10m"  # 单个日志文件最大10MB
    max-file: "3"    # 保留3个日志文件
```

---

## 📊 监控和维护

### 日志查看

```bash
# 实时日志
docker-compose logs -f ultra-pachong

# 最近100行日志
docker-compose logs --tail=100 ultra-pachong

# 导出日志
docker-compose logs ultra-pachong > app.log
```

### 资源监控

```bash
# 实时资源使用
docker stats ultra-pachong

# 磁盘使用
docker system df

# 详细镜像信息
docker images ultra-pachong --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
```

### 备份和恢复

```bash
# 备份数据卷
docker run --rm \
  -v ultra-pachong_postgres-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/postgres-backup-$(date +%Y%m%d).tar.gz -C /data .

# 恢复数据卷
docker run --rm \
  -v ultra-pachong_postgres-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/postgres-backup-20260128.tar.gz -C /data
```

---

## 🔒 安全建议

### 1. 不要在镜像中硬编码密钥

```bash
# ❌ 错误
ENV API_KEY=your_secret_key

# ✅ 正确 - 使用环境变量或secrets
docker run -e API_KEY=${API_KEY} ...
```

### 2. 使用非root用户

```dockerfile
# 创建普通用户
RUN useradd -m -u 1000 pachong
USER pachong
```

### 3. 定期更新基础镜像

```bash
# 更新基础镜像
docker pull python:3.11-slim

# 重新构建
docker-compose build --no-cache
```

### 4. 扫描安全漏洞

```bash
# 使用trivy扫描
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image ultra-pachong:latest
```

---

## 📞 故障排查

### 容器启动失败

```bash
# 查看详细错误
docker-compose logs ultra-pachong

# 查看容器状态
docker inspect ultra-pachong

# 进入容器调试
docker-compose run --rm ultra-pachong /bin/bash
```

### 性能问题

```bash
# CPU分析
docker exec ultra-pachong py-spy top --pid 1

# 内存分析
docker exec ultra-pachong python -m memory_profiler script.py

# 网络分析
docker exec ultra-pachong tcpdump -i any port 80
```

---

## 🎯 最佳实践

1. **始终使用 `.env` 文件管理配置**
2. **生产环境使用具体版本号而非 `latest` 标签**
3. **定期备份数据卷**
4. **监控容器资源使用情况**
5. **使用健康检查确保服务可用性**
6. **日志输出到持久化存储**
7. **使用 docker-compose 管理多容器应用**

---

## 📚 相关文档

- [Docker官方文档](https://docs.docker.com/)
- [Playwright Docker文档](https://playwright.dev/docs/docker)
- [Ultra Pachong 主文档](README.md)
- [审计报告](AUDIT_FINAL_REPORT.md)

---

**Docker配置创建时间**: 2026-01-28
**维护者**: Claude Sonnet 4.5
