# 万能临时邮箱生成器 (Mail.tm + Mail.gw)
# 支持多域名选择，自动代理

import requests
import random
import string
import time
import csv
import os
from colorama import Fore, Style, init

init()

PROVIDERS = {
    "1": {"name": "Mail.tm", "url": "https://api.mail.tm"},
    "2": {"name": "Mail.gw", "url": "https://api.mail.gw"}
}

def random_string(length=10):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

import subprocess
import json

KNOWN_DOMAINS = {
    "1": ["virgilian.com"],
    "2": ["oakon.com", "teihu.com", "raleigh-construction.com", "pastryofistanbul.com", "questtechsystems.com"]
}

def create_account_curl(base_url, domain, proxy=None):
    """使用 Curl 创建账号 (更稳定)"""
    username = random_string(10)
    password = random_string(12) + "Aa1!"
    email = f"{username}@{domain}"
    
    data = json.dumps({
        "address": email,
        "password": password
    })
    
    payload_file = f"payload_{random_string(5)}.json"
    with open(payload_file, "w", encoding="utf-8") as f:
        f.write(data)
        
    cmd = [
        "curl.exe", "-s", "-X", "POST", f"{base_url}/accounts",
        "-H", "Content-Type: application/json",
        "-d", f"@{payload_file}"
    ]
    
    if proxy:
        cmd.extend(["-x", proxy])
        
    try:
        # 运行 Curl
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            try:
                resp_json = json.loads(result.stdout)
                if 'id' in resp_json:
                    print(f"{Fore.GREEN}✓ 成功: {Fore.YELLOW}{email}{Style.RESET_ALL}")
                    return {
                        "email": email,
                        "password": password,
                        "provider": base_url,
                        "created_at": time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                else:
                    print(f"{Fore.RED}失败: {result.stdout[:100]}{Style.RESET_ALL}")
            except:
                 # 这种API有时返回空如果失败，或HTML
                 print(f"{Fore.RED}解析失败: {result.stdout[:50]}{Style.RESET_ALL}")
        else:
             print(f"{Fore.RED}Curl 错误: {result.stderr}{Style.RESET_ALL}")
             
    except Exception as e:
        print(f"{Fore.RED}执行错误: {e}{Style.RESET_ALL}")
        return None
    finally:
        if os.path.exists(payload_file):
            os.remove(payload_file)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', type=str, choices=['1', '2'], default='2', help='1: Mail.tm, 2: Mail.gw')
    parser.add_argument('--count', type=int, default=5)
    parser.add_argument('--proxy', type=str, default="http://127.0.0.1:7890")
    args = parser.parse_args()

    print(f"""
{Fore.CYAN}
    Uni-Mail Creator v2.0 (Curl Edition)
    Provider: {PROVIDERS[args.provider]['name']}
    Count: {args.count}
{Style.RESET_ALL}""")

    provider = PROVIDERS[args.provider]
    BASE_URL = provider["url"]
    
    # 直接使用已知域名
    domains = KNOWN_DOMAINS[args.provider]
    
    results = []
    print(f"使用域名池: {domains}")
    print(f"\n开始生成 {args.count} 个账号...\n")
    
    for i in range(args.count):
        # 随机选一个域名
        domain = random.choice(domains)
        acc = create_account_curl(BASE_URL, domain, args.proxy)
        if acc:
            results.append(acc)
        time.sleep(1)
            
    if results:
        csv_file = 'universal_accounts.csv'
        file_exists = os.path.exists(csv_file)
        
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            fieldnames = ['email', 'password', 'provider', 'created_at']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(results)
            
        print(f"\n{Fore.GREEN}完成！已保存 {len(results)} 个账号到 {csv_file}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
