# Ultra Pachong - Production Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 安装系统依赖（playwright需要）
RUN apt-get update && apt-get install -y \
    # 基础工具
    wget \
    curl \
    git \
    # Playwright依赖
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    # 图像处理依赖（ddddocr/opencv）
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgthread-2.0-0 \
    # 清理缓存
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY unified_agent/requirements.txt /app/requirements.txt

# 安装Python依赖
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# 安装Playwright浏览器（仅Chromium）
RUN playwright install chromium && \
    playwright install-deps chromium

# 复制项目文件
COPY . /app/

# 创建数据目录
RUN mkdir -p /app/data /app/logs /app/cache

# 设置权限
RUN chmod -R 755 /app

# 暴露端口（如需要HTTP服务）
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "from unified_agent.api.orchestrator import AgentOrchestrator; print('OK')" || exit 1

# 默认命令
CMD ["python", "-m", "unified_agent"]
