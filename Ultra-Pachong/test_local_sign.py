"""
测试本地签名服务器
"""

import httpx
import json
import urllib.parse

def test_local_sign():
    """测试本地签名服务器"""

    # 1. 检查服务器健康状态
    print("=== 1. 检查签名服务器 ===")
    try:
        resp = httpx.get("http://127.0.0.1:18888/health", timeout=5)
        print(f"健康检查: {resp.json()}")
    except Exception as e:
        print(f"错误: 签名服务器未运行 - {e}")
        print("请先运行: node unified_agent/infra/jd_sign_server.js")
        return

    # 2. 调用签名API
    print("\n=== 2. 生成签名 ===")
    body = {
        "productId": "100012043978",
        "sortType": 5,
        "page": 1,
        "pageSize": 10,
        "score": 0,
        "isShadowSku": 0
    }

    body_str = json.dumps(body, separators=(',', ':'))
    body_encoded = urllib.parse.quote(body_str)

    sign_url = f"http://127.0.0.1:18888/sign?functionId=getCommentListWithCard&body={body_encoded}"

    try:
        resp = httpx.get(sign_url, timeout=10)
        sign_result = resp.json()

        if "error" in sign_result:
            print(f"签名错误: {sign_result['error']}")
            return

        print(f"签名成功!")
        print(f"  h5st长度: {len(sign_result['h5st'])}")

        h5st_parts = sign_result['h5st'].split(';')
        print(f"  h5st段数: {len(h5st_parts)}")
        for i, part in enumerate(h5st_parts):
            display = part[:40] + "..." if len(part) > 40 else part
            print(f"    段{i+1}: {display}")

    except Exception as e:
        print(f"签名请求失败: {e}")
        return

    # 3. 调用京东API
    print("\n=== 3. 测试京东API ===")

    jd_url = "https://api.m.jd.com/client.action"
    params = {
        "functionId": "getCommentListWithCard",
        "body": body_str,
        "appid": "item-v3",
        "client": "pc",
        "clientVersion": "1.0.0",
        "t": str(sign_result['t']),
        "h5st": sign_result['h5st'],
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://item.jd.com/100012043978.html",
        "Origin": "https://item.jd.com",
    }

    try:
        resp = httpx.get(jd_url, params=params, headers=headers, timeout=30)
        print(f"状态码: {resp.status_code}")

        try:
            data = resp.json()
            print(f"响应code: {data.get('code', 'N/A')}")

            if data.get('code') == '0':
                print("签名验证成功!")
                comments = data.get('comments', [])
                print(f"获取到 {len(comments)} 条评论")
                if comments:
                    print(f"第一条评论: {comments[0].get('content', '')[:100]}...")
            else:
                print(f"API返回错误: {data}")

        except:
            print(f"响应内容: {resp.text[:500]}")

    except Exception as e:
        print(f"API请求失败: {e}")


if __name__ == "__main__":
    test_local_sign()
