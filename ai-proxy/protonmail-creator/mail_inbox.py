# Mail.tm/Mail.gw 收信工具
# 用于接收 Teams 邀请邮件并提取链接

import requests
import csv
import time
import re
import os
import json
import urllib3
from colorama import Fore, Style, init

init()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 从 universal_accounts.csv 读取账号
CSV_FILE = 'universal_accounts.csv'

def get_token(base_url, email, password, proxy=None):
    """登录获取 Token"""
    try:
        proxies = {"http": proxy, "https": proxy} if proxy else None
        data = {"address": email, "password": password}
        resp = requests.post(f"{base_url}/token", json=data, proxies=proxies, verify=False, timeout=10)
        if resp.status_code == 200:
            return resp.json()['token']
        return None
    except:
        return None

def get_messages(base_url, token, proxy=None):
    """获取邮件列表"""
    try:
        proxies = {"http": proxy, "https": proxy} if proxy else None
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{base_url}/messages", headers=headers, proxies=proxies, verify=False, timeout=10)
        if resp.status_code == 200:
            return resp.json()['hydra:member']
        return []
    except:
        return []

def get_message_content(base_url, token, msg_id, proxy=None):
    """获取邮件具体内容"""
    try:
        proxies = {"http": proxy, "https": proxy} if proxy else None
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{base_url}/messages/{msg_id}", headers=headers, proxies=proxies, verify=False, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except:
        return None

def main():
    print(f"{Fore.CYAN}正在读取 {CSV_FILE}...{Style.RESET_ALL}")
    
    accounts = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                accounts.append(row)
    
    if not accounts:
        print(f"{Fore.RED}没有找到账号，请先生成！{Style.RESET_ALL}")
        return

    print(f"找到 {len(accounts)} 个账号，开始轮询收件箱 (按 Ctrl+C 停止)...")
    print(f"{Fore.YELLOW}提示: 请在 Teams 后台发送邀请给这些邮箱{Style.RESET_ALL}\n")

    PROXY = "http://127.0.0.1:7890"

    # 缓存已处理的邮件 ID，避免重复提示
    processed_ids = set()

    while True:
        try:
            for acc in accounts:
                email = acc['email']
                pwd = acc['password']
                # 兼容旧版 csv 可能没有 provider 字段，默认 mail.gw 因为最近生成的是它
                provider_url = acc.get('provider', 'https://api.mail.gw') 
                
                # 登录
                token = get_token(provider_url, email, pwd, PROXY)
                if not token:
                    print(f"\r{Fore.RED}[x] 登录失败: {email}{Style.RESET_ALL}", end="")
                    continue
                
                # 查信
                msgs = get_messages(provider_url, token, PROXY)
                
                for msg in msgs:
                    mid = msg['id']
                    if mid in processed_ids:
                        continue
                        
                    processed_ids.add(mid)
                    subject = msg['subject']
                    intro = msg.get('intro', '')
                    
                    print(f"\n{Fore.GREEN}══════════════════════════════════════════════════{Style.RESET_ALL}")
                    print(f"📬 收到新邮件！ -> {Fore.YELLOW}{email}{Style.RESET_ALL}")
                    print(f"主题: {subject}")
                    print(f"简介: {intro}")
                    
                    # 获取全文以提取连接
                    full_msg = get_message_content(provider_url, token, mid, PROXY)
                    if full_msg:
                        # 简单的正则尝试提取 http 链接
                        links = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', str(full_msg))
                        if links:
                            print(f"{Fore.CYAN}🔗 发现链接 (可能是邀请链接):{Style.RESET_ALL}")
                            # 过滤一些无用资源链接，主要找邀请相关的
                            for l in links:
                                if "openai" in l or "click" in l or "verify" in l or "token" in l:
                                    print(f"   {l}")
                    
                    print(f"{Fore.GREEN}══════════════════════════════════════════════════{Style.RESET_ALL}\n")

            print(f"\r正在监控 {len(accounts)} 个账号... {time.strftime('%H:%M:%S')}", end="")
            time.sleep(10) # 每10秒轮询一次
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            pass

if __name__ == "__main__":
    main()
