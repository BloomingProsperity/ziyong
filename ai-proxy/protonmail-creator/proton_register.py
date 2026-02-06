# ProtonMail 全自动注册脚本 (修复版 v2)
# 直接访问免费计划URL，使用正确的选择器

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from colorama import Fore, Style, init
import time
import random
import string
import csv
import os

init()

def random_string(length=10):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def create_proton_account(proxy_url="http://127.0.0.1:7890"):
    """全自动创建 ProtonMail 账号"""
    
    username = random_string(10)
    password = random_string(12) + "Aa1!"  # 确保密码强度
    
    print(f"\n{Fore.CYAN}═══════════════════════════════════════════{Style.RESET_ALL}")
    print(f"{Fore.GREEN}生成的账号信息:{Style.RESET_ALL}")
    print(f"  邮箱: {Fore.YELLOW}{username}@proton.me{Style.RESET_ALL}")
    print(f"  密码: {Fore.YELLOW}{password}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}═══════════════════════════════════════════{Style.RESET_ALL}\n")
    
    # 配置浏览器
    options = webdriver.ChromeOptions()
    options.add_argument(f'--proxy-server={proxy_url}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--start-maximized')
    options.add_argument('--lang=en-US')  # 使用英文界面更稳定
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver_path = os.path.join(os.path.dirname(__file__), 'driver', 'chromedriver.exe')
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 30)
    
    try:
        # 直接访问免费计划注册页面
        print(f"{Fore.YELLOW}[1/5] 打开免费计划注册页面...{Style.RESET_ALL}")
        driver.get('https://account.proton.me/signup?plan=free')
        time.sleep(5)  # 等待页面完全加载
        
        # 填写用户名 - 使用 ID 选择器
        print(f"{Fore.YELLOW}[2/5] 填写用户名: {username}{Style.RESET_ALL}")
        try:
            # 尝试多种选择器
            username_input = None
            selectors = [
                (By.ID, "email"),
                (By.ID, "username"),
                (By.CSS_SELECTOR, "input[id='email']"),
                (By.CSS_SELECTOR, "input[name='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='username']"),
                (By.CSS_SELECTOR, "input[placeholder*='用户名']"),
            ]
            
            for sel_type, sel_value in selectors:
                try:
                    username_input = wait.until(EC.presence_of_element_located((sel_type, sel_value)))
                    if username_input and username_input.is_displayed():
                        print(f"  找到用户名输入框: {sel_value}")
                        break
                except:
                    continue
            
            if username_input:
                username_input.clear()
                time.sleep(0.3)
                username_input.send_keys(username)
                print(f"{Fore.GREEN}  ✓ 用户名已填写{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}  ✗ 无法找到用户名输入框{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}  用户名填写错误: {e}{Style.RESET_ALL}")
        
        time.sleep(1)
        
        # 填写密码 - 明确使用 ID
        print(f"{Fore.YELLOW}[3/5] 填写密码...{Style.RESET_ALL}")
        try:
            password_input = driver.find_element(By.ID, "password")
            password_input.clear()
            time.sleep(0.3)
            password_input.send_keys(password)
            print(f"{Fore.GREEN}  ✓ 密码已填写{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}  密码填写错误: {e}{Style.RESET_ALL}")
        
        time.sleep(1)
        
        # 填写确认密码 - 明确使用 ID
        print(f"{Fore.YELLOW}[4/5] 填写确认密码...{Style.RESET_ALL}")
        try:
            confirm_input = driver.find_element(By.ID, "repeat-password")
            confirm_input.clear()
            time.sleep(0.3)
            confirm_input.send_keys(password)
            print(f"{Fore.GREEN}  ✓ 确认密码已填写{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}  确认密码填写错误: {e}{Style.RESET_ALL}")
        
        time.sleep(1)
        
        # 尝试点击创建账号按钮
        print(f"{Fore.YELLOW}[5/5] 点击创建账号按钮...{Style.RESET_ALL}")
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()
            print(f"{Fore.GREEN}  ✓ 已点击创建按钮{Style.RESET_ALL}")
        except:
            print(f"{Fore.YELLOW}  需要手动点击创建按钮{Style.RESET_ALL}")
        
        print(f"\n{Fore.GREEN}══════════════════════════════════════════════════════{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  表单填写完成！{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  请在浏览器中:{Style.RESET_ALL}")
        print(f"    1. 检查用户名是否正确填入")
        print(f"    2. 完成 CAPTCHA 人机验证")
        print(f"    3. 点击创建账号按钮 (如未点击)")
        print(f"{Fore.GREEN}══════════════════════════════════════════════════════{Style.RESET_ALL}\n")
        
        input(f"{Fore.CYAN}完成注册后按 Enter 保存账号...{Style.RESET_ALL}")
        
        # 保存账号
        csv_path = os.path.join(os.path.dirname(__file__), 'accounts.csv')
        file_exists = os.path.exists(csv_path)
        
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['Email', 'Password', 'Created'])
            writer.writerow([f'{username}@proton.me', password, time.strftime('%Y-%m-%d %H:%M:%S')])
        
        print(f"{Fore.GREEN}✓ 账号已保存到 accounts.csv{Style.RESET_ALL}")
        return True
        
    except Exception as e:
        print(f"{Fore.RED}错误: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        driver.quit()

def main():
    print(f"""
{Fore.RED}
    ____             __              __  ___      _ __
   / __ \\_________  / /_____  ____  /  |/  /___ _(_) /
  / /_/ / ___/ __ \\/ __/ __ \\/ __ \\/ /|_/ / __ `/ / / 
 / ____/ /  / /_/ / /_/ /_/ / / / / /  / / /_/ / / /  
/_/   /_/   \\____/\\__/\\____/_/ /_/_/  /_/\\__,_/_/_/   

    全自动注册脚本 v2 (修复版)
    - 直接访问免费计划
    - 使用正确的选择器
{Style.RESET_ALL}""")
    
    proxy = input(f"{Fore.CYAN}代理地址 (回车使用 127.0.0.1:7890): {Style.RESET_ALL}").strip()
    if not proxy:
        proxy = "http://127.0.0.1:7890"
    elif not proxy.startswith('http'):
        proxy = f"http://{proxy}"
    
    print(f"{Fore.GREEN}使用代理: {proxy}{Style.RESET_ALL}")
    
    count = input(f"{Fore.CYAN}要创建几个账号? (默认 1): {Style.RESET_ALL}").strip()
    count = int(count) if count.isdigit() else 1
    
    for i in range(count):
        print(f"\n{Fore.MAGENTA}═══ 正在创建第 {i+1}/{count} 个账号 ═══{Style.RESET_ALL}")
        create_proton_account(proxy)
        
        if i < count - 1:
            print(f"\n{Fore.YELLOW}准备创建下一个账号...{Style.RESET_ALL}")
            time.sleep(2)
    
    print(f"\n{Fore.GREEN}全部完成！共创建 {count} 个账号，已保存到 accounts.csv{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
