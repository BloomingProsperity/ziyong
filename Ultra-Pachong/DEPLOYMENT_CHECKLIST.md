# 🚀 Ultra Pachong 部署检查清单

**版本**: 1.0
**日期**: 2026-01-28

---

## 📋 部署前检查

### 1. 环境准备

- [ ] Docker 已安装（版本 >= 20.10）
  ```bash
  docker --version
  ```

- [ ] Docker Compose 已安装（版本 >= 2.0）
  ```bash
  docker-compose --version
  ```

- [ ] 系统资源检查
  ```bash
  # 可用内存 >= 4GB
  free -h

  # 可用磁盘 >= 10GB
  df -h
  ```

- [ ] 网络连通性
  ```bash
  # 测试外网访问
  curl -I https://www.baidu.com

  # 测试Docker Hub访问
  docker pull hello-world
  ```

### 2. 配置文件准备

- [ ] 复制环境变量配置
  ```bash
  cp .env.example .env
  ```

- [ ] 编辑 `.env` 文件，填入必要配置
  - [ ] `PROXY_ENABLED` - 是否使用代理
  - [ ] `PROXY_SERVER` - 代理服务器地址（如需要）
  - [ ] `KUAIDAILI_API_KEY` - 快代理密钥（如需要）
  - [ ] `CAPTCHA_API_KEY` - 验证码服务密钥（如需要）
  - [ ] `DB_PASSWORD` - 数据库密码（生产环境必改）
  - [ ] `LOG_LEVEL` - 日志级别

- [ ] 创建必要的目录
  ```bash
  mkdir -p data logs cache knowledge config
  ```

- [ ] 设置目录权限
  ```bash
  chmod 755 data logs cache knowledge
  ```

### 3. 代码审计修复确认

- [x] __main__.py 导入路径已修复
  - 已从 `from .orchestrator` 改为 `from .api.orchestrator`

- [x] requirements.txt 已更新
  - 包含 playwright、ddddocr、opencv-python、PyJWT 等

- [ ] 核心模块可导入（可选验证）
  ```bash
  # 如果有Python环境，可提前验证
  python -c "from unified_agent.core.signature import SignatureManager; print('OK')"
  ```

---

## 🏗️ 构建和启动

### 选项 A: 生产环境完整部署

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动所有服务（应用+Redis+PostgreSQL）
docker-compose up -d

# 3. 查看启动日志
docker-compose logs -f ultra-pachong

# 4. 等待服务就绪（观察日志中的 ✅ 标记）
```

### 选项 B: 仅核心服务部署

```bash
# 1. 构建镜像
docker-compose build ultra-pachong

# 2. 仅启动主应用
docker-compose up -d ultra-pachong

# 3. 查看日志
docker-compose logs -f ultra-pachong
```

### 选项 C: 开发环境部署

```bash
# 1. 构建开发镜像
docker build -f Dockerfile.dev -t ultra-pachong:dev .

# 2. 启动开发容器
docker run -it --rm \
  -v $(pwd):/app \
  -p 8000:8000 \
  --name ultra-pachong-dev \
  ultra-pachong:dev

# 3. 在容器内运行测试
pytest tests/ -v
```

---

## ✅ 部署后验证

### 1. 服务状态检查

```bash
# 检查容器是否运行
docker-compose ps

# 应该看到:
# NAME                STATUS
# ultra-pachong       Up (healthy)
# ultra-pachong-db    Up (healthy)  # 如果启动了数据库
# ultra-pachong-redis Up            # 如果启动了Redis
```

### 2. 健康检查

```bash
# Docker自动健康检查
docker inspect ultra-pachong | grep -A 10 Health

# 手动验证核心模块
docker exec ultra-pachong python -c "
from unified_agent.core.signature import SignatureManager
from unified_agent.core.scheduling import create_scheduler
from unified_agent.core.diagnosis import create_diagnoser
from unified_agent.core.assessment import create_assessment
print('✅ Core modules OK')
"

# 验证高级功能（需要playwright）
docker exec ultra-pachong python -c "
from unified_agent.api.brain import Brain
print('✅ Brain module OK')
"
```

### 3. 日志检查

```bash
# 查看启动日志
docker-compose logs ultra-pachong | grep "✅"

# 应该看到:
# ✅ PostgreSQL is ready
# ✅ Redis is ready
# ✅ Playwright browsers OK
# ✅ Core modules OK
# ✅ Brain module OK
```

### 4. 功能测试

```bash
# 进入容器
docker exec -it ultra-pachong bash

# 测试签名功能
python -c "
from unified_agent.core.signature import SignatureManager, SignatureRequest, SignType
manager = SignatureManager()
request = SignatureRequest(
    params={'test': 'value'},
    sign_type=SignType.MD5,
    credentials={'secret': 'test_secret'}
)
result = manager.generate(request)
assert result.status == 'success'
print(f'✅ Signature test passed: {result.signature}')
"

# 测试调度功能
python -c "
import asyncio
from unified_agent.core.scheduling import create_scheduler, Task

async def test():
    scheduler = create_scheduler(concurrency=2)
    async def dummy_task(x):
        return x * 2
    tasks = [Task(id=f't{i}', func=dummy_task, args=(i,)) for i in range(5)]
    result = await scheduler.schedule(tasks)
    assert result.success == 5
    print(f'✅ Scheduler test passed: {result.success} tasks completed')

asyncio.run(test())
"
```

### 5. 资源使用检查

```bash
# 查看资源使用情况
docker stats ultra-pachong --no-stream

# 确认:
# - CPU使用率 < 80%
# - 内存使用 < 3GB（限制4GB）
# - 网络正常
```

---

## 🔧 常见问题处理

### 问题 1: 容器启动失败

**检查步骤**:
```bash
# 1. 查看详细错误
docker-compose logs ultra-pachong

# 2. 查看容器状态
docker-compose ps

# 3. 检查磁盘空间
df -h

# 4. 检查内存
free -h
```

**常见原因**:
- 磁盘空间不足 → 清理 `docker system prune -a`
- 内存不足 → 增加系统内存或减少并发数
- 端口占用 → 修改 `docker-compose.yml` 端口映射

### 问题 2: Playwright浏览器未安装

**症状**: 日志显示 `Executable doesn't exist`

**解决方案**:
```bash
# 方案1: 重新构建镜像（推荐）
docker-compose build --no-cache ultra-pachong

# 方案2: 手动安装
docker exec ultra-pachong playwright install chromium
docker exec ultra-pachong playwright install-deps chromium
```

### 问题 3: 模块导入失败

**症状**: `ModuleNotFoundError: No module named 'xxx'`

**解决方案**:
```bash
# 检查依赖安装
docker exec ultra-pachong pip list | grep playwright
docker exec ultra-pachong pip list | grep ddddocr

# 重新安装依赖
docker exec ultra-pachong pip install -r requirements.txt
```

### 问题 4: 数据库连接失败

**症状**: `could not connect to server: Connection refused`

**解决方案**:
```bash
# 检查postgres容器
docker-compose ps postgres

# 查看postgres日志
docker-compose logs postgres

# 测试连接
docker exec ultra-pachong nc -zv postgres 5432

# 重启postgres
docker-compose restart postgres
```

### 问题 5: 网络访问失败

**症状**: 无法访问外网，请求超时

**解决方案**:
```bash
# 测试容器网络
docker exec ultra-pachong ping -c 3 8.8.8.8
docker exec ultra-pachong curl -I https://www.baidu.com

# 配置代理（编辑.env）
PROXY_ENABLED=true
PROXY_SERVER=http://your-proxy:8080

# 重启容器
docker-compose restart ultra-pachong
```

---

## 📊 监控和维护

### 日常监控

```bash
# 1. 实时日志
docker-compose logs -f ultra-pachong

# 2. 资源监控
watch -n 5 'docker stats ultra-pachong --no-stream'

# 3. 磁盘使用
du -sh data/ logs/ cache/

# 4. 容器状态
docker-compose ps
```

### 定期维护

```bash
# 每周: 清理日志
find logs/ -name "*.log" -mtime +7 -delete

# 每月: 备份数据
tar czf backup-$(date +%Y%m%d).tar.gz data/ knowledge/

# 每月: 清理Docker
docker system prune -f

# 每季度: 更新镜像
docker-compose pull
docker-compose up -d
```

---

## 🔒 安全检查

- [ ] `.env` 文件权限设置为 600
  ```bash
  chmod 600 .env
  ```

- [ ] 修改了默认数据库密码
  ```bash
  # 检查 .env 中的 DB_PASSWORD
  grep DB_PASSWORD .env
  ```

- [ ] 生产环境使用强密码（至少16位）

- [ ] API密钥没有硬编码在代码中

- [ ] 日志文件不包含敏感信息
  ```bash
  # 检查日志
  grep -i "password\|token\|secret" logs/*.log
  ```

- [ ] 防火墙配置正确（仅开放必要端口）

- [ ] 定期更新基础镜像和依赖

---

## 📈 性能优化检查

- [ ] 根据实际负载调整并发数（MAX_CONCURRENCY）

- [ ] 根据目标网站调整请求速率（RATE_LIMIT）

- [ ] 启用Redis缓存（生产环境推荐）

- [ ] 使用PostgreSQL持久化知识库（生产环境推荐）

- [ ] 配置日志轮转避免磁盘占满

- [ ] 监控内存使用，必要时增加限制

---

## ✨ 部署成功标志

当看到以下所有标志时，部署成功:

```
✅ Container ultra-pachong is Up and healthy
✅ Playwright browsers installed
✅ Core modules imported successfully
✅ Brain module loaded
✅ Database connection established (if enabled)
✅ Redis connection established (if enabled)
✅ Health check passing
✅ No error logs in the last 5 minutes
```

---

## 📞 获取帮助

如果遇到问题:

1. 查看 [DOCKER_GUIDE.md](DOCKER_GUIDE.md) 详细文档
2. 查看 [AUDIT_FINAL_REPORT.md](AUDIT_FINAL_REPORT.md) 代码审计报告
3. 查看 GitHub Issues
4. 联系维护团队

---

**检查清单版本**: 1.0
**最后更新**: 2026-01-28
**维护者**: Claude Sonnet 4.5
