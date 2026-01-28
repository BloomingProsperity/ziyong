"""
调试脚本 - 检查JD页面实际状态
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright


async def debug_jd_page():
    """调试JD产品页面"""

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

    # 加载Cookie
    cookie_file = Path("data/cookies.json")
    if cookie_file.exists():
        try:
            cookies = json.loads(cookie_file.read_text(encoding="utf-8"))
            await context.add_cookies(cookies)
            print("已加载Cookie")
        except Exception as e:
            print(f"Cookie加载失败: {e}")

    # 访问首页验证登录
    print("访问京东首页...")
    await page.goto("https://www.jd.com/", wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(3)

    # 检查登录状态
    cookies = await context.cookies()
    cookie_dict = {c["name"]: c["value"] for c in cookies}
    if cookie_dict.get("pin") or cookie_dict.get("pt_key"):
        print(f"已登录: {cookie_dict.get('unick', '未知用户')}")
    else:
        print("未登录，请在浏览器中登录...")
        input("登录完成后按Enter继续...")

    # 访问一个产品页面
    sku_id = "100012043978"  # 一个常用的测试SKU
    product_url = f"https://item.jd.com/{sku_id}.html"

    print(f"\n访问产品页面: {product_url}")
    await page.goto(product_url, wait_until="domcontentloaded", timeout=60000)

    print("等待页面加载...")
    await asyncio.sleep(5)

    # 保存截图
    await page.screenshot(path="debug_product_page.png")
    print("截图已保存: debug_product_page.png")

    # 检查页面URL
    current_url = page.url
    print(f"当前URL: {current_url}")

    if "item.jd.com" not in current_url:
        print("警告: 页面被重定向!")
        await page.screenshot(path="debug_redirected.png")

    # 检查是否有验证码/风控
    content = await page.content()
    if "验证" in content or "安全" in content or "risk" in content.lower():
        print("警告: 可能触发了风控/验证码!")
        await page.screenshot(path="debug_risk.png")

    # 滚动到评论区
    print("\n滚动到评论区...")
    for i in range(5):
        await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {0.2 * (i+1)})")
        await asyncio.sleep(2)

    await page.screenshot(path="debug_scrolled.png")
    print("截图已保存: debug_scrolled.png")

    # 尝试找到评论区
    print("\n检查评论区...")
    comment_info = await page.evaluate("""
        () => {
            const info = {};

            // 检查评论容器
            info.hasCommentRoot = !!document.querySelector('.comment-root, .comment, #comment');
            info.hasCommentItems = document.querySelectorAll('.comment-item, .comment-con').length;

            // 获取页面主要文本内容（用于调试）
            const commentRoot = document.querySelector('.comment-root, .comment, #comment');
            if (commentRoot) {
                info.commentRootText = commentRoot.innerText.substring(0, 500);
            }

            // 检查是否有iframe
            info.iframeCount = document.querySelectorAll('iframe').length;

            return info;
        }
    """)

    print(f"评论容器: {comment_info.get('hasCommentRoot')}")
    print(f"评论项数量: {comment_info.get('hasCommentItems')}")
    print(f"iframe数量: {comment_info.get('iframeCount')}")

    if comment_info.get('commentRootText'):
        print(f"\n评论区文本预览:\n{comment_info.get('commentRootText')[:300]}...")

    # 等待用户观察
    print("\n\n浏览器将保持打开状态，请手动检查页面。")
    print("按Enter关闭浏览器...")
    input()

    await browser.close()
    await playwright.stop()


if __name__ == "__main__":
    asyncio.run(debug_jd_page())
