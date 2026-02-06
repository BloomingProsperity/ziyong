# ProtonMail 全自动注册脚本 (Playwright 版)
# 使用下一代自动化技术，完美解决 Shadow DOM 和定位问题

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
        
        # 启动浏览器 (带代理)
        browser = p.chromium.launch(
            headless=False,
            proxy={"server": proxy_url} if proxy_url else None,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        
        # 创建上下文 (更像真实用户)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        for i in range(count):
            page = context.new_page()
            
            username = random_string(10)
            password = random_string(12) + "Aa1!"
            
            print(f"\n═══════════════════════════════════════════")
            print(f"生成的账号信息 ({i+1}/{count}):")
            print(f"  邮箱: {username}@proton.me")
            print(f"  密码: {password}")
            print(f"═══════════════════════════════════════════\n")
            
            try:
                print(f"[1/4] 打开注册页面...")
                page.goto('https://account.proton.me/signup?plan=free', timeout=60000)
                
                # 等待页面加载
                page.wait_for_load_state("networkidle")
                
                # ----------------------------------------------------------------
                # 填写用户名 - 使用 get_by_label (Playwright 的强项)
                # ----------------------------------------------------------------
                print(f"[2/4] 填写用户名: {username}")
                
                # 尝试多种定位方式，Playwright 会自动穿透 Shadow DOM
                frame = page.frame_locator("iframe").first if page.frames else page
                
                # 优先尝试 Label 定位
                try:
                    page.get_by_label("Username", exact=False).fill(username, timeout=2000)
                    print("  ✓ 使用 Label 'Username' 填入")
                except:
                    # 尝试 Placeholder
                    try:
                        page.get_by_placeholder("Username", exact=False).fill(username, timeout=2000)
                        print("  ✓ 使用 Placeholder 'Username' 填入")
                    except:
                        # 尝试 Frame 内部
                        try:
                            # 有时候它是在 iframe 里的
                            iframe = page.frame_locator("#signup-iframe") 
                            iframe.get_by_label("Username").fill(username)
                            print("  ✓ 在 iframe 中填入")
                        except:
                            # 最后的绝招：ID
                            if page.locator("#email").is_visible():
                                page.locator("#email").fill(username)
                            elif page.locator("input[type='email']").is_visible():
                                page.locator("input[type='email']").fill(username)
                            else:
                                # 盲填第一个输入框
                                page.locator("input").first.fill(username)
                                print("  ⚠️ 盲填第一个输入框")

                time.sleep(1)

                # ----------------------------------------------------------------
                # 填写密码
                # ----------------------------------------------------------------
                print(f"[3/4] 填写密码...")
                try:
                    # 密码框通常有两个 (Password, Confirm/Repeat)
                    # Playwright 可以精准定位
                    page.get_by_label("Password", exact=True).fill(password)
                    print("  ✓ 填入密码")
                except:
                    page.locator("input[type='password']").first.fill(password)

                time.sleep(0.5)

                try:
                    page.get_by_label("Repeat password", exact=False).fill(password)
                    print("  ✓ 填入确认密码")
                except:
                    try:
                        page.get_by_label("Confirm password", exact=False).fill(password)
                    except:
                        # 找第二个密码框
                        pws = page.locator("input[type='password']")
                        if pws.count() > 1:
                            pws.nth(1).fill(password)

                time.sleep(1)

                # ----------------------------------------------------------------
                # 提交
                # ----------------------------------------------------------------
                print(f"[4/4] 提交...")
                try:
                    create_btn = page.get_by_role("button", name="Create account", exact=False)
                    if create_btn.is_visible():
                        create_btn.click()
                    else:
                        page.locator("button[type='submit']").click()
                    print("  ✓ 点击创建按钮")
                except:
                    pass

                print(f"\n══════════════════════════════════════════════════════")
                print(f"  请在浏览器中完成 CAPTCHA 验证")
                print(f"══════════════════════════════════════════════════════\n")
                
                input(f"完成注册后按 Enter 保存账号...")
                
                # 保存
                with open('accounts.csv', 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([f'{username}@proton.me', password, time.strftime('%Y-%m-%d %H:%M:%S')])
                
                print(f"✓ 账号已保存")
                
            except Exception as e:
                print(f"❌ 错误: {e}")
            
            finally:
                if i < count - 1:
                    print("准备下一个...")
                    page.close()
                else:
                    browser.close()

if __name__ == "__main__":
    import sys
    # 设置 HOME 环境变量，防止 Playwright 报错
    os.environ["HOME"] = os.environ.get("USERPROFILE")
    
    print("""
    Playwright ProtonMail 注册机
    """)
    
    proxy_in = input("代理地址 (回车 127.0.0.1:7890): ").strip()
    if not proxy_in:
        proxy_in = "http://127.0.0.1:7890"
    elif not proxy_in.startswith("http"):
        proxy_in = f"http://{proxy_in}"
        
    create_proton_account(1, proxy_in)
