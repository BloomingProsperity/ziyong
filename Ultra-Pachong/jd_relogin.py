"""
京东重新登录脚本

清除旧Cookie并等待用户手动登录
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright


async def relogin():
    """重新登录京东"""

    # 清除旧Cookie
    cookie_file = Path("data/cookies.json")
    if cookie_file.exists():
        cookie_file.unlink()
        print("[OK] 已删除旧Cookie文件")

    print("启动浏览器...")

    playwright = await async_playwright().start()

    browser = await playwright.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ]
    )

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )

    page = await context.new_page()

    # 访问登录页
    print("访问京东登录页...")
    await page.goto("https://passport.jd.com/new/login.aspx", timeout=60000)

    print("\n" + "="*60)
    print("请在浏览器中手动登录京东账号!")
    print("登录成功后程序会自动保存Cookie")
    print("="*60 + "\n")

    # 等待跳转到非登录页
    try:
        await page.wait_for_url(
            lambda url: "jd.com" in url and "passport" not in url,
            timeout=300000,  # 5分钟超时
        )
        print("[OK] 检测到登录成功!")

        # 等待Cookie稳定
        await asyncio.sleep(5)

        # 保存Cookie
        cookies = await context.cookies()
        cookie_file.parent.mkdir(parents=True, exist_ok=True)
        cookie_file.write_text(json.dumps(cookies, indent=2), encoding="utf-8")

        # 验证
        cookie_dict = {c["name"]: c["value"] for c in cookies}
        print(f"[OK] Cookie已保存!")
        print(f"    用户: {cookie_dict.get('unick', '未知')}")
        print(f"    PIN: {cookie_dict.get('pin', '未知')}")
        print(f"    文件: {cookie_file.absolute()}")

        # 测试访问产品页
        print("\n测试访问产品页...")
        await page.goto("https://item.jd.com/100012043978.html", timeout=60000)
        await asyncio.sleep(3)

        current_url = page.url
        if "item.jd.com" in current_url:
            print("[OK] 产品页访问正常!")
            await page.screenshot(path="debug_after_login.png")
        else:
            print(f"[!] 产品页被重定向: {current_url}")

    except Exception as e:
        print(f"[X] 登录等待超时: {e}")

    print("\n按Enter关闭浏览器...")
    try:
        input()
    except:
        pass

    await browser.close()
    await playwright.stop()


if __name__ == "__main__":
    asyncio.run(relogin())
