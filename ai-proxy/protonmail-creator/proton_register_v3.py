# ProtonMail 全自动注册脚本 (修复版 v3)
# 使用基于文本标签的XPath定位，解决ID变化问题

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
    password = random_string(12) + "Aa1!"
    
    print(f"\n{Fore.CYAN}═══════════════════════════════════════════{Style.RESET_ALL}")
    print(f"{Fore.GREEN}生成的账号信息:{Style.RESET_ALL}")
    print(f"  邮箱: {Fore.YELLOW}{username}@proton.me{Style.RESET_ALL}")
    print(f"  密码: {Fore.YELLOW}{password}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}═══════════════════════════════════════════{Style.RESET_ALL}\n")
    
    # 配置 Chrome
    options = webdriver.ChromeOptions()
    options.add_argument(f'--proxy-server={proxy_url}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--start-maximized')
    options.add_argument('--lang=en-US')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver_path = os.path.join(os.path.dirname(__file__), 'driver', 'chromedriver.exe')
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 30)
    
    try:
        # 直接访问免费计划
        print(f"{Fore.YELLOW}[1/4] 打开注册页面...{Style.RESET_ALL}")
        driver.get('https://account.proton.me/signup?plan=free')
        time.sleep(6)  # 等待加载
        
        # 调试：打印所有 input 标签以便排错
        try:
            inputs = driver.find_elements(By.TAG_NAME, "input")
            print(f"页面发现 {len(inputs)} 个输入框")
            for i, inp in enumerate(inputs):
                try:
                    print(f"  Input {i}: id='{inp.get_attribute('id')}', name='{inp.get_attribute('name')}', type='{inp.get_attribute('type')}'")
                except:
                    pass
        except:
            pass

        # ----------------------------------------------------------------
        # 填写用户名 (Username)
        # ----------------------------------------------------------------
        print(f"{Fore.YELLOW}[2/4] 填写用户名: {username}{Style.RESET_ALL}")
        try:
            # 策略1: 找 id="email" (最常见)
            # 策略2: 找包含 "Username" 标签附近的 input
            # 策略3: 找页面第一个可见的文本输入框
            
            username_input = None
            
            # 尝试通过 Label 定位
            try:
                # 查找包含 Username 文字的 Label，然后找其关联的 input
                label = driver.find_element(By.XPATH, "//label[contains(., 'Username')]")
                id_val = label.get_attribute("for")
                if id_val:
                    username_input = driver.find_element(By.ID, id_val)
                    print("  通过 Label 'Username' 找到输入框")
                else:
                    # 如果没有 for 属性，找 label 内部或后面的 input
                    username_input = label.find_element(By.XPATH, "./following::input[1]")
                    print("  通过 Label 'Username' 邻近元素找到输入框")
            except:
                pass
            
            # 如果没找到，尝试通过 ID 列表
            if not username_input:
                for uid in ["email", "username", "id-signup-username"]:
                    try:
                        inp = driver.find_element(By.ID, uid)
                        if inp.is_displayed():
                            username_input = inp
                            print(f"  通过 ID '{uid}' 找到输入框")
                            break
                    except:
                        pass
            
            if username_input:
                driver.execute_script("arguments[0].scrollIntoView(true);", username_input)
                time.sleep(0.5)
                username_input.click()
                username_input.clear() # 重要！
                # 模拟逐字输入
                for char in username:
                    username_input.send_keys(char)
                    time.sleep(0.05)
                print(f"{Fore.GREEN}  ✓ 用户名已填写{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}  ✗ 无法找到用户名输入框 (尝试盲填第一个文本框){Style.RESET_ALL}")
                # 最后的绝招：填第一个可见的 text/email 输入框
                inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='email']")
                for inp in inputs:
                    if inp.is_displayed():
                        inp.clear()
                        inp.send_keys(username)
                        print(f"{Fore.GREEN}  ✓ 盲填了第一个输入框{Style.RESET_ALL}")
                        break
        except Exception as e:
            print(f"{Fore.RED}  用户名填写失败: {e}{Style.RESET_ALL}")

        time.sleep(1)

        # ----------------------------------------------------------------
        # 填写密码 (Password)
        # ----------------------------------------------------------------
        print(f"{Fore.YELLOW}[3/4] 填写密码...{Style.RESET_ALL}")
        try:
            password_input = None
            
            # 策略1: Label 定位
            try:
                label = driver.find_element(By.XPATH, "//label[contains(., 'Password')]")
                id_val = label.get_attribute("for")
                if id_val:
                    password_input = driver.find_element(By.ID, id_val)
                else:
                    password_input = label.find_element(By.XPATH, "./following::input[1]")
            except:
                pass
            
            # 策略2: ID 定位
            if not password_input:
                try:
                    password_input = driver.find_element(By.ID, "password")
                except:
                    pass
            
            # 策略3: 找第一个 type='password' 的框
            if not password_input:
                pw_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                if len(pw_inputs) > 0:
                    password_input = pw_inputs[0]
            
            if password_input:
                password_input.click()
                password_input.clear()
                password_input.send_keys(password)
                print(f"{Fore.GREEN}  ✓ 密码已填写{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}  ✗ 无法找到密码输入框{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}  密码填写失败: {e}{Style.RESET_ALL}")
            
        time.sleep(1)

        # ----------------------------------------------------------------
        # 填写确认密码 (Confirm/Repeat Password)
        # ----------------------------------------------------------------
        print(f"{Fore.YELLOW}[4/4] 填写确认密码...{Style.RESET_ALL}")
        try:
            confirm_input = None
            
            # 策略1: Label 定位 (Confirm password 或 Repeat password)
            try:
                label = driver.find_element(By.XPATH, "//label[contains(., 'Confirm') or contains(., 'Repeat')]")
                id_val = label.get_attribute("for")
                if id_val:
                    confirm_input = driver.find_element(By.ID, id_val)
                else:
                    confirm_input = label.find_element(By.XPATH, "./following::input[1]")
            except:
                pass
            
            # 策略2: ID 定位
            if not confirm_input:
                for pid in ["repeat-password", "passwordc", "confirm-password"]:
                    try:
                        confirm_input = driver.find_element(By.ID, pid)
                        break
                    except:
                        pass
            
            # 策略3: 找第二个 type='password' 的框
            if not confirm_input:
                pw_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                if len(pw_inputs) > 1:
                    confirm_input = pw_inputs[1]
            
            if confirm_input:
                confirm_input.click()
                confirm_input.clear()
                confirm_input.send_keys(password)
                print(f"{Fore.GREEN}  ✓ 确认密码已填写{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}  ✗ 无法找到确认密码输入框{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}  确认密码填写失败: {e}{Style.RESET_ALL}")

        time.sleep(1)
        
        # ----------------------------------------------------------------
        # 提交 (Submit)
        # ----------------------------------------------------------------
        try:
            # 尝试点击提交按钮
            btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            btn.click()
            print(f"{Fore.GREEN}  ✓ 已点击创建账号按钮{Style.RESET_ALL}")
        except:
            pass
            
        print(f"\n{Fore.GREEN}══════════════════════════════════════════════════════{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  自动化填写结束{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  (如果仍有未填写的项，请手动补充){Style.RESET_ALL}")
        print(f"{Fore.GREEN}══════════════════════════════════════════════════════{Style.RESET_ALL}\n")
        
        input(f"{Fore.CYAN}完成注册后按 Enter 保存账号...{Style.RESET_ALL}")
        
        # 保存
        with open('accounts.csv', 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([f'{username}@proton.me', password, time.strftime('%Y-%m-%d %H:%M:%S')])
        
        print(f"{Fore.GREEN}✓ 账号已保存{Style.RESET_ALL}")
        return True
        
    except Exception as e:
        print(f"{Fore.RED}运行错误: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        driver.quit()

if __name__ == "__main__":
    create_proton_account()
