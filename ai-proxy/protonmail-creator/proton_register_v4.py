# ProtonMail 全自动注册脚本 (修复版 v4)
# 终极方案：使用 Tab 键导航模拟

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
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
    password = random_string(12) + "Aa1!"
    
    print(f"\n{Fore.CYAN}═══════════════════════════════════════════{Style.RESET_ALL}")
    print(f"{Fore.GREEN}生成的账号信息:{Style.RESET_ALL}")
    print(f"  邮箱: {Fore.YELLOW}{username}@proton.me{Style.RESET_ALL}")
    print(f"  密码: {Fore.YELLOW}{password}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}═══════════════════════════════════════════{Style.RESET_ALL}\n")
    
    options = webdriver.ChromeOptions()
    options.add_argument(f'--proxy-server={proxy_url}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--start-maximized')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver_path = os.path.join(os.path.dirname(__file__), 'driver', 'chromedriver.exe')
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 30)
    actions = ActionChains(driver)
    
    try:
        print(f"{Fore.YELLOW}[1/4] 打开注册页面...{Style.RESET_ALL}")
        driver.get('https://account.proton.me/signup?plan=free')
        time.sleep(8)  # 给足时间加载
        
        # 1. 先定位到密码框 (因为之前成功了)
        print(f"{Fore.YELLOW}[2/4] 定位输入框...{Style.RESET_ALL}")
        
        # 尝试点击页面任意空白处以确保焦点在页面上
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            body.click()
        except:
            pass
            
        password_input = None
        try:
            # 尝试通过多种方式找到密码框
            selectors = [
                 (By.ID, "password"),
                 (By.CSS_SELECTOR, "input[type='password']"),
                 (By.XPATH, "//label[contains(., 'Password')]/following::input[1]")
            ]
            
            for by, val in selectors:
                try:
                    password_input = driver.find_element(by, val)
                    if password_input.is_displayed():
                        break
                except:
                    continue
        except:
            pass
            
        if password_input:
            print(f"  定位到密码框，准备倒推到用户名框...")
            password_input.click()
            time.sleep(0.5)
            
            # 从密码框 Shift+Tab 跳回用户名框
            # 通常密码框上面是“显示/隐藏密码”按钮，或者是“用户名”
            # 我们尝试多按几次 Shift+Tab 直到聚焦到文本框
            
            actions.key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()
            time.sleep(0.2)
            
            # 再试一次，以防中间有什么隐藏元素
            # 检查当前焦点元素是否是 input type='text' 或 'email'
            
            active_ele = driver.switch_to.active_element
            # 如果是用户名框，现在的 active_ele 应该是 input
            
            print(f"{Fore.YELLOW}[3/4] 模拟键盘填写信息...{Style.RESET_ALL}")
            
            # 填写用户名
            actions.send_keys(username).perform()
            print(f"{Fore.GREEN}  ✓ 尝试输入用户名{Style.RESET_ALL}")
            time.sleep(0.5)
            
            # Tab 切换到密码框
            actions.send_keys(Keys.TAB).perform()
            time.sleep(0.2)
            
            # 填写密码
            actions.send_keys(password).perform()
            print(f"{Fore.GREEN}  ✓ 尝试输入密码{Style.RESET_ALL}")
            time.sleep(0.5)
            
            # Tab 切换到确认密码框
            actions.send_keys(Keys.TAB).perform()
            time.sleep(0.2)
            
            # 填写确认密码
            actions.send_keys(password).perform()
            print(f"{Fore.GREEN}  ✓ 尝试输入确认密码{Style.RESET_ALL}")
            time.sleep(0.5)
            
            # Tab 切换到提交按钮并回车
            actions.send_keys(Keys.TAB).perform()
            time.sleep(0.2)
            actions.send_keys(Keys.ENTER).perform()
            print(f"{Fore.GREEN}  ✓ 尝试提交{Style.RESET_ALL}")
            
        else:
            print(f"{Fore.RED}  无法定位任何输入框，尝试纯盲打模式{Style.RESET_ALL}")
            # 绝望模式：狂按 Tab 找位置
            # 通常页面加载后焦点不在输入框，我们按几次 Tab
            actions.send_keys(Keys.TAB).perform()
            time.sleep(0.2)
            actions.send_keys(Keys.TAB).perform()
            time.sleep(0.2)
            
            actions.send_keys(username).perform()
            actions.send_keys(Keys.TAB).perform()
            actions.send_keys(password).perform()
            actions.send_keys(Keys.TAB).perform()
            actions.send_keys(password).perform()
            actions.send_keys(Keys.ENTER).perform()

        print(f"\n{Fore.GREEN}══════════════════════════════════════════════════════{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  已执行键盘模拟{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  (请在浏览器中确认并补充遗漏项){Style.RESET_ALL}")
        print(f"{Fore.GREEN}══════════════════════════════════════════════════════{Style.RESET_ALL}\n")
        
        input(f"{Fore.CYAN}完成注册后按 Enter 保存账号...{Style.RESET_ALL}")
        
        with open('accounts.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([f'{username}@proton.me', password, time.strftime('%Y-%m-%d %H:%M:%S')])
            
        return True
        
    except Exception as e:
        print(f"{Fore.RED}错误: {e}{Style.RESET_ALL}")
        return False
    finally:
        driver.quit()

if __name__ == "__main__":
    create_proton_account()
