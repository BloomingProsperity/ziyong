# ProtonMail 注册助手 (稳定版)
# 既然全自动被拦截，我们使用最稳妥的“辅助模式”
# 1. 自动打开浏览器
# 2. 生成账号密码并显示在屏幕上
# 3. 自动将密码复制到剪贴板 (方便你粘贴)
# 4. 注册成功后只需按回车，自动保存

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from colorama import Fore, Style, init
import time
import random
import string
import csv
import os
import subprocess

init()

def copy_to_clipboard(text):
    """复制文本到剪贴板 (Windows)"""
    command = f'echo {text}| clip'
    subprocess.check_call(command, shell=True)

def random_string(length=10):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def create_proton_account(proxy_url="http://127.0.0.1:7890"):
    
    username = random_string(10)
    password = random_string(12) + "Aa1!"
    email = f"{username}@proton.me"
    
    print(f"\n{Fore.CYAN}═══════════════════════════════════════════{Style.RESET_ALL}")
    print(f"{Fore.GREEN} 🚀 新账号已生成 (已准备好){Style.RESET_ALL}")
    print(f"  用户名: {Fore.YELLOW}{email}{Style.RESET_ALL}")
    print(f"  密码:   {Fore.YELLOW}{password}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}═══════════════════════════════════════════{Style.RESET_ALL}\n")
    
    # 将密码复制到剪贴板
    try:
        copy_to_clipboard(password)
        print(f"{Fore.GREEN}✓ 密码已自动复制到剪贴板！(直接 Ctrl+V 粘贴){Style.RESET_ALL}")
    except:
        print(f"{Fore.RED}✗ 无法复制密码，请手动复制{Style.RESET_ALL}")

    options = webdriver.ChromeOptions()
    options.add_argument(f'--proxy-server={proxy_url}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--start-maximized')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver_path = os.path.join(os.path.dirname(__file__), 'driver', 'chromedriver.exe')
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print(f"{Fore.YELLOW}正在打开注册页面...{Style.RESET_ALL}")
        driver.get('https://account.proton.me/signup?plan=free')
        
        print(f"\n{Fore.MAGENTA}请操作:{Style.RESET_ALL}")
        print(f"1. 复制用户名: {Fore.WHITE}{username}{Style.RESET_ALL}")
        print(f"2. 在密码框按 {Fore.WHITE}Ctrl+V{Style.RESET_ALL} (密码已在剪贴板)")
        print(f"3. 完成 CAPTCHA")
        print(f"\n{Fore.YELLOW}完成后，回到这里按 Enter 保存...{Style.RESET_ALL}")
        
        input()
        
        # 保存
        with open('accounts.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([email, password, time.strftime('%Y-%m-%d %H:%M:%S')])
            
        print(f"{Fore.GREEN}✓ 账号已保存到 accounts.csv{Style.RESET_ALL}")
        return True
        
    except Exception as e:
        print(f"{Fore.RED}错误: {e}{Style.RESET_ALL}")
        return False
    finally:
        driver.quit()

if __name__ == "__main__":
    print(f"""
{Fore.RED}
    ____             __                   __  ___      _ __
   / __ \\_________  / /_____  ____       /  |/  /___ _(_) /
  / /_/ / ___/ __ \\/ __/ __ \\/ __ \\     / /|_/ / __ `/ / / 
 / ____/ /  / /_/ / /_/ /_/ / / / /    / /  / / /_/ / / /  
/_/   /_/   \\____/\\__/\\____/_/ /_/____/_/  /_/\\__,_/_/_/   
                                /_____/                    
    ProtonMail 注册助手 (稳定版)
{Style.RESET_ALL}""")
    
    proxy = input(f"{Fore.CYAN}代理地址 (回车使用 127.0.0.1:7890): {Style.RESET_ALL}").strip()
    if not proxy:
        proxy = "http://127.0.0.1:7890"
    elif not proxy.startswith('http'):
        proxy = f"http://{proxy}"
    
    while True:
        create_proton_account(proxy)
        if input(f"\n{Fore.CYAN}继续下一个? (y/n): {Style.RESET_ALL}").strip().lower() != 'y':
            break
