#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试爬虫到登录前的所有步骤

这个脚本会测试：
1. 环境检测
2. 代理配置
3. 浏览器启动
4. 访问京东首页（测试代理是否工作）
5. 然后立即关闭（不需要登录）
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载 .env
env_file = Path(".env")
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

print("="*70)
print(" "*20 + "爬虫启动测试（到登录前）")
print("="*70)

async def test_scraper():
    """测试爬虫启动"""

    print("\n[1/5] 导入模块...")
    try:
        from unified_agent.scraper.jd_comments import JDCommentScraper
        from unified_agent.examples.jd_comment_scraper import get_proxy_from_env
        print("  [OK] 模块导入成功")
    except Exception as e:
        print(f"  [错误] {e}")
        return False

    print("\n[2/5] 创建爬虫实例...")
    try:
        proxy = get_proxy_from_env()
        scraper = JDCommentScraper(
            output_dir="data",
            request_delay=(2, 5),
            proxy=proxy
        )

        if proxy:
            print(f"  [OK] 代理已配置")
        else:
            print(f"  [提示] 未使用代理")

        status = scraper.get_agent_status()
        print(f"  [OK] Agent 模块集成:")
        print(f"      - diagnosis:  {status['diagnosis']}")
        print(f"      - recovery:   {status['recovery']}")
        print(f"      - credential: {status['credential']}")
        print(f"      - mcp:        {status['mcp']}")
    except Exception as e:
        print(f"  [错误] {e}")
        return False

    print("\n[3/5] 启动浏览器...")
    try:
        success = await scraper.init_browser()
        if not success:
            print(f"  [错误] 浏览器启动失败")
            return False
        print(f"  [OK] 浏览器已启动")
        print(f"  [OK] 反检测已注入")
    except Exception as e:
        print(f"  [错误] {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n[4/5] 测试访问京东首页（通过代理）...")
    try:
        # 尝试访问京东首页，测试代理
        await scraper.page.goto("https://www.jd.com/", wait_until="domcontentloaded", timeout=30000)

        title = await scraper.page.title()
        print(f"  [OK] 页面加载成功")
        print(f"  [OK] 页面标题: {title[:50]}...")

        # 检查是否被代理拦截
        if "ERR_" in title or "错误" in title:
            print(f"  [警告] 页面可能有问题")
        else:
            print(f"  [OK] 代理工作正常")

    except Exception as e:
        print(f"  [错误] 访问失败: {e}")
        await scraper.close()
        return False

    print("\n[5/5] 关闭浏览器...")
    try:
        await scraper.close()
        print(f"  [OK] 浏览器已关闭")
    except Exception as e:
        print(f"  [警告] 关闭时出错: {e}")

    return True

# 运行测试
print("\n开始测试...")
print("-"*70)

try:
    result = asyncio.run(test_scraper())

    print("\n" + "="*70)
    if result:
        print("✓ 测试通过！所有步骤都正常")
        print("="*70)
        print("\n可以运行正式爬虫了：")
        print("  双击 '【修复后】测试运行.bat'")
        print("\n注意：正式运行时需要手动登录京东账号")
    else:
        print("✗ 测试失败，请检查错误信息")
        print("="*70)

except KeyboardInterrupt:
    print("\n\n测试被中断")
except Exception as e:
    print(f"\n\n测试异常: {e}")
    import traceback
    traceback.print_exc()
