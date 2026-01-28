#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试京东爬虫 - 验证所有功能

这个脚本会测试：
1. 环境检测
2. 配置加载
3. Agent 模块集成
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print(" "*25 + "京东爬虫测试")
print("="*70)

# 测试 1: 检测环境
print("\n[测试 1/5] 检测 Python 环境...")
print("-"*70)
print(f"Python 版本: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

# 测试 2: 检测必要的包
print("\n[测试 2/5] 检测必要的包...")
print("-"*70)

required_packages = ['playwright', 'httpx', 'asyncio', 'dotenv']
for pkg in required_packages:
    try:
        if pkg == 'dotenv':
            __import__('dotenv')
        else:
            __import__(pkg)
        print(f"  [OK] {pkg}")
    except ImportError:
        print(f"  [FAIL] {pkg} - 未安装")

# 测试 3: 加载 .env 配置
print("\n[测试 3/5] 加载 .env 配置...")
print("-"*70)

env_file = Path(".env")
if env_file.exists():
    print(f"  [OK] .env 文件存在")

    # 手动加载 .env
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

    # 检查代理配置
    proxy_enabled = os.getenv("PROXY_ENABLED", "false").lower() == "true"
    print(f"  代理启用: {proxy_enabled}")

    if proxy_enabled:
        host = os.getenv("KUAIDAILI_HOST", "")
        port = os.getenv("KUAIDAILI_PORT", "")
        username = os.getenv("KUAIDAILI_USERNAME", "")

        if all([host, port, username]):
            print(f"  [OK] 代理配置: {username}@{host}:{port}")
        else:
            print(f"  [WARN] 代理配置不完整")
else:
    print(f"  [FAIL] .env 文件不存在")

# 测试 4: 导入 Agent 模块
print("\n[测试 4/5] 导入 unified_agent 模块...")
print("-"*70)

try:
    from unified_agent.scraper.jd_comments import JDCommentScraper, BRAND_CONFIGS
    print(f"  [OK] JDCommentScraper 导入成功")
    print(f"  [OK] 预设品牌数: {len(BRAND_CONFIGS)}")
except ImportError as e:
    print(f"  [FAIL] 导入失败: {e}")
    sys.exit(1)

# 测试 5: 检查 Agent 模块集成
print("\n[测试 5/5] 检查 Agent 模块集成...")
print("-"*70)

try:
    scraper = JDCommentScraper(output_dir="data")
    status = scraper.get_agent_status()

    print(f"  diagnosis  (诊断): {'[OK]' if status['diagnosis'] else '[未集成]'}")
    print(f"  recovery   (恢复): {'[OK]' if status['recovery'] else '[未集成]'}")
    print(f"  credential (凭据): {'[OK]' if status['credential'] else '[未集成]'}")
    print(f"  mcp        (工具): {'[OK]' if status['mcp'] else '[未集成]'}")

except Exception as e:
    print(f"  [FAIL] 创建实例失败: {e}")

# 总结
print("\n" + "="*70)
print("测试完成！")
print("="*70)
print("\n如果所有测试都通过，可以运行：")
print("  python -m unified_agent.examples.jd_comment_scraper --good 10 --bad 2")
print("\n这将启动测试模式，每个品牌只爬取 12 条数据")
print("="*70)
