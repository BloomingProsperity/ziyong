#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试代理是否可用
"""

import os
import sys
from pathlib import Path

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
print(" "*25 + "代理测试")
print("="*70)

# 检查代理配置
proxy_enabled = os.getenv("PROXY_ENABLED", "false").lower() == "true"
print(f"\n[1/3] 代理启用: {proxy_enabled}")

if not proxy_enabled:
    print("\n代理未启用，跳过测试")
    sys.exit(0)

host = os.getenv("KUAIDAILI_HOST", "")
port = os.getenv("KUAIDAILI_PORT", "")
username = os.getenv("KUAIDAILI_USERNAME", "")
password = os.getenv("KUAIDAILI_PASSWORD", "")

if not all([host, port, username, password]):
    print("\n[错误] 代理配置不完整")
    sys.exit(1)

proxy_url = f"http://{username}:{password}@{host}:{port}"
print(f"代理地址: http://{username}:***@{host}:{port}")

# 测试 HTTP 代理
print(f"\n[2/3] 测试 HTTP 代理连接...")

try:
    import httpx
    import asyncio

    async def test_proxy():
        try:
            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=30
            ) as client:
                response = await client.get("http://httpbin.org/ip")
                if response.status_code == 200:
                    data = response.json()
                    print(f"  [OK] 代理连接成功")
                    print(f"  代理IP: {data.get('origin')}")
                    return True
                else:
                    print(f"  [错误] 状态码: {response.status_code}")
                    return False
        except Exception as e:
            print(f"  [错误] {e}")
            return False

    result = asyncio.run(test_proxy())

    if not result:
        print("\n代理测试失败，可能的原因：")
        print("  1. 代理用户名或密码错误")
        print("  2. 代理服务器无法连接")
        print("  3. 代理已过期或欠费")
        print("\n请检查代理配置或联系代理服务商")
        sys.exit(1)

except ImportError:
    print("  [错误] httpx 未安装，无法测试")
    print("  运行: pip install httpx")
    sys.exit(1)

# 测试 Playwright 代理
print(f"\n[3/3] 测试 Playwright 代理连接...")

try:
    from playwright.sync_api import sync_playwright
    from urllib.parse import urlparse

    parsed = urlparse(proxy_url)
    proxy_config = {
        "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
        "username": parsed.username,
        "password": parsed.password,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(proxy=proxy_config)
        page = context.new_page()

        try:
            page.goto("http://httpbin.org/ip", timeout=30000)
            content = page.content()

            if "origin" in content:
                print(f"  [OK] Playwright 代理连接成功")
            else:
                print(f"  [警告] 页面加载了，但内容可能不对")

        except Exception as e:
            print(f"  [错误] {e}")
            browser.close()
            sys.exit(1)

        browser.close()

except ImportError:
    print("  [错误] playwright 未安装")
    sys.exit(1)

print("\n" + "="*70)
print("✓ 代理测试全部通过！可以正常使用")
print("="*70)
