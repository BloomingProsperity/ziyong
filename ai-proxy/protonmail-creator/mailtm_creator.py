# Mail.tm 批量账号生成器
# 无需浏览器，秒级生成，无验证

import requests
import random
import string
import time
import csv
import os
from colorama import Fore, Style, init

init()

BASE_URL = "https://api.mail.tm"

def random_string(length=10):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_domain():
    """获取可用域名"""
    try:
        response = requests.get(f"{BASE_URL}/domains")
        if response.status_code == 200:
            domains = response.json()['hydra:member']
            return domains[0]['domain']
        return None
    except Exception as e:
        print(f"{Fore.RED}获取域名失败: {e}{Style.RESET_ALL}")
        return None

def create_account(domain, proxy=None):
    """创建账号"""
    username = random_string(10)
    password = random_string(12) + "Aa1!"
    email = f"{username}@{domain}"
    
    payload = {
        "address": email,
        "password": password
    }
    
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    try:
        response = requests.post(f"{BASE_URL}/accounts", json=payload, proxies=proxies, timeout=10)
        
        if response.status_code == 201:
            data = response.json()
            print(f"{Fore.GREEN}✓ 成功创建: {Fore.YELLOW}{email}{Style.RESET_ALL}")
            return {
                "email": email,
                "password": password,
                "id": data['id'],
                "created_at": time.strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            print(f"{Fore.RED}创建失败 ({response.status_code}): {response.text}{Style.RESET_ALL}")
            return None
            
    except Exception as e:
        print(f"{Fore.RED}请求错误: {e}{Style.RESET_ALL}")
        return None

def main():
    print(f"""
{Fore.CYAN}
    __  ___      _ __  __          
   /  |/  /___ _(_) / / /_  ____   
  / /|_/ / __ `/ / / / __/ / __ \  
 / /  / / /_/ / / / / /_  / / / /  
/_/  /_/\__,_/_/_/  \__/ /_/ /_/   
                                   
    Mail.tm 批量账号生成器 (自动版)
{Style.RESET_ALL}""")

    # 硬编码配置，避免输入问题
    PROXY = "http://127.0.0.1:7890"
    COUNT = 5
    
    # 验证代理
    print(f"设定代理: {PROXY}")
    print("正在获取可用域名...")
    domain = get_domain()
    if not domain:
        print(f"{Fore.RED}无法获取域名！请检查网络或代理连接。{Style.RESET_ALL}")
        # 尝试不使用代理重试
        print(f"{Fore.YELLOW}尝试不使用代理重试...{Style.RESET_ALL}")
        PROXY = None
        domain = get_domain()
        if not domain:
            print(f"{Fore.RED}彻底失败，请检查网络。{Style.RESET_ALL}")
            return

    print(f"使用域名: {Fore.GREEN}@{domain}{Style.RESET_ALL}")
    
    results = []
    print(f"\n开始生成 {COUNT} 个账号...\n")
    
    for i in range(COUNT):
        acc = create_account(domain, PROXY)
        if acc:
            results.append(acc)
        time.sleep(1) 
            
    # 保存
    if results:
        csv_file = 'mailtm_accounts.csv'
        
        # 读取现有数据以保留（如果有）
        existing_data = []
        if os.path.exists(csv_file):
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    existing_data = list(reader)
            except:
                pass
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['email', 'password', 'id', 'created_at']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(existing_data + results)
            
        print(f"\n{Fore.GREEN}全部完成！共保存 {len(results)} 个新账号到 {csv_file}{Style.RESET_ALL}")
        print(f"文件绝对路径: {os.path.abspath(csv_file)}")

if __name__ == "__main__":
    main()
