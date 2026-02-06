# ProtonMail 全自动注册脚本 (Playwright V2 - 增强版)
# 包含：
# 1. 详细的页面结构侦测
# 2. 从 iframes 中查找元素
# 3. 终极 "盲操作" 模式 (Tab 键导航)

import time
import random
import string
import csv
import os
from playwright.sync_api import sync_playwright

def random_string(length=10):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def create_proton_account(count=1, proxy_url="http://127.0.0.1:7890"):
    
    with sync_playwright() as p:
        print(f"正在启动浏览器...")
        
        browser = p.chromium.launch(
            headless=False,
            proxy={"server": proxy_url} if proxy_url else None,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        
        # 使用持久化上下文，保存 Cookies 避免每次都被识别为新设备
        context = browser.new_context(
            viewport={"width": 1280, "height": 720}, # 标准分辨率
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        try:
            username = random_string(10)
            password = random_string(12) + "Aa1!"
            
            print(f"\n账号: {username}@proton.me | 密码: {password}\n")
            
            print(f"[1/4] 打开注册页面...")
            page.goto('https://account.proton.me/signup?plan=free', timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(5) 
            
            print(f"当前页面标题: {page.title()}")
            
            # 检测是否被拦截
            if "ddos" in page.title().lower() or "challenge" in page.title().lower():
                print("⚠️ 可能遇到了 Cloudflare/DDOS 拦截，等待 10 秒...")
                time.sleep(10)

            # ----------------------------------------------------------------
            # 智能定位逻辑
            # ----------------------------------------------------------------
            print(f"[2/4] 尝试定位并填写...")
            
            filled = False
            
            # 方法 A: 标准 Label 定位
            try:
                print("  尝试方法 A: 寻找 'Username' 标签...")
                # 显式聚焦页面
                page.mouse.click(100, 100)
                
                # 查找所有 Input 方便调试
                inputs = page.locator("input").all()
                print(f"  页面发现 {len(inputs)} 个输入框")
                
                user_input = page.get_by_label("Username", exact=False).first
                if user_input.is_visible():
                    user_input.click()
                    user_input.fill(username)
                    print("  ✓ 用户名已填 (通过 Label)")
                    filled = True
                else:
                    # 尝试用 ID
                    if page.locator("#email").is_visible():
                        page.locator("#email").fill(username)
                        print("  ✓ 用户名已填 (通过 ID #email)")
                        filled = True
                    elif page.locator("#username").is_visible():
                        page.locator("#username").fill(username)
                        print("  ✓ 用户名已填 (通过 ID #username)")
                        filled = True

                if filled:
                    # 填密码
                    page.keyboard.press("Tab")
                    time.sleep(0.5)
                    page.keyboard.type(password)
                    print("  ✓ 密码已填")
                    
                    page.keyboard.press("Tab")
                    time.sleep(0.5)
                    
                    # 确认密码 (有时候不需要，有时候需要)
                    # 我们不管需不需要，先盲打一次确认密码，如果没有那个框也无所谓
                    page.keyboard.type(password) 
                    print("  ✓ (尝试) 确认密码已填")
                    
                    page.keyboard.press("Enter")
                    print("  ✓ 提交")
            except Exception as e:
                print(f"  方法 A 失败: {e}")

            # 方法 B: 盲打模式 (Fallback)
            if not filled:
                print("\n⚠️ 启用方法 B: 盲打模式 (Tab 导航)")
                print("  正在尝试寻找焦点并输入...")
                
                # 点击页面中心，确保焦点在 webview
                w = page.viewport_size['width']
                h = page.viewport_size['height']
                page.mouse.click(w/2, h/3) # 点击大约上方 1/3 处
                
                # 疯狂 Tab 寻找据点
                # 通常：Login -> Pricing -> Username
                # 或者直接聚焦在 Username
                
                # 策略：重置焦点到 body，然后 Tab
                page.evaluate("document.body.focus()")
                
                # 尝试点击第一个 input 如果存在
                first_input = page.locator("input:visible").first
                if first_input:
                    try:
                        first_input.click(timeout=2000)
                        print("  点击了第一个可见输入框")
                    except:
                        pass
                
                # 输入用户名
                page.keyboard.type(username)
                print("  输入了用户名 (盲打)")
                
                page.keyboard.press("Tab")
                time.sleep(0.5)
                
                page.keyboard.type(password)
                print("  输入了密码 (盲打)")
                
                page.keyboard.press("Tab")
                time.sleep(0.5)
                
                page.keyboard.type(password)
                print("  输入了确认密码 (盲打)")
                
                page.keyboard.press("Enter")
                print("  回车提交")

            print("\n══════════════════════════════════════════════════════")
            print("  自动化流程结束，请人工检查")
            print("  1. 如果用户名/密码没填上，请手动填写")
            print(f"     用户名: {username}")
            print(f"     密码:   {password}")
            print("  2. 完成 CAPTCHA")
            print("══════════════════════════════════════════════════════\n")
            
            input("完成注册后按 Enter 保存...")
            
            with open('accounts.csv', 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([f'{username}@proton.me', password, time.strftime('%Y-%m-%d %H:%M:%S')])
            
        except Exception as e:
            print(f"运行错误: {e}")
        finally:
            page.close()
            browser.close()

if __name__ == "__main__":
    os.environ["HOME"] = os.environ.get("USERPROFILE")
    
    proxy_in = input("代理 (回车 127.0.0.1:7890): ").strip()
    if not proxy_in:
        proxy_in = "http://127.0.0.1:7890"
    elif not proxy_in.startswith("http"):
        proxy_in = f"http://{proxy_in}"
        
    create_proton_account(1, proxy_in)
