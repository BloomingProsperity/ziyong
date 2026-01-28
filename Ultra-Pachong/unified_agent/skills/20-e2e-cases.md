# 20-e2e-cases.md - 端到端案例库

## 模块目标

| 目标 | KPI | 验收标准 |
|------|-----|----------|
| 提供真实可复制的完整案例 | 案例覆盖率 ≥ 90% 场景 | 参照案例可完成类似任务 |
| 每个案例都能直接执行 | 案例可运行率 100% | 无需修改即可跑通 |
| 从案例学习通用方法论 | 举一反三能力 | 新网站能找到对应参考 |

**核心原则**：`给出需求，必须完成` - 案例不是展示，是实战指南。

---

## 一、案例分类索引

```
案例库
├── 简单案例 (无反爬/弱反爬)
│   ├── Case-01: 静态页面采集 (新闻网站)
│   ├── Case-02: 简单API采集 (公开数据接口)
│   └── Case-03: 简单登录后采集 (表单登录)
├── 中等案例 (常规反爬)
│   ├── Case-04: Cookie验证网站
│   ├── Case-05: 简单签名参数网站
│   ├── Case-06: 图形验证码网站
│   └── Case-07: 动态加载网站 (无限滚动)
├── 困难案例 (强反爬)
│   ├── Case-08: 复杂签名网站 (京东h5st)
│   ├── Case-09: 指纹检测网站 (Cloudflare)
│   └── Case-10: 多因素验证网站
└── 特殊案例
    ├── Case-11: WebSocket实时数据
    ├── Case-12: GraphQL接口
    ├── Case-13: APP数据抓取
    └── Case-14: 微信小程序数据
```

---

## 二、简单案例

### Case-01: 静态页面采集 (新闻网站)

**场景描述**
```
目标: 采集某新闻网站的文章列表和正文
特征: 纯服务端渲染，无JS依赖，无反爬
URL类型: https://news.example.com/list?page=1
```

**执行流程**

```
Step 1: 侦查 (01-reconnaissance)
│
├─→ 输入: "https://news.example.com"
├─→ 执行:
│   brain.smart_investigate(url)
│
├─→ 预期发现:
│   - 反爬等级: LOW
│   - 渲染方式: SSR (服务端渲染)
│   - 数据位置: HTML 内嵌
│   - 推荐方式: 直接HTTP请求
│
└─→ 决策: 无需浏览器，使用 requests 即可

Step 2: 请求 (04-request)
│
├─→ 获取列表页:
│   response = brain.call_api(
│       url="https://news.example.com/list?page=1",
│       method="GET"
│   )
│
├─→ 检查响应:
│   - 状态码: 200 ✓
│   - 内容: HTML ✓
│
└─→ 进入解析

Step 3: 解析 (05-parsing)
│
├─→ 列表页解析:
│   articles = brain.scrape_page(
│       html=response.text,
│       selectors={
│           "title": ".article-title a",
│           "link": ".article-title a::attr(href)",
│           "date": ".article-date",
│           "summary": ".article-summary"
│       }
│   )
│
├─→ 正文页解析 (循环每篇文章):
│   for article in articles:
│       detail = brain.call_api(article['link'])
│       content = brain.scrape_page(
│           html=detail.text,
│           selectors={
│               "title": "h1.title",
│               "content": ".article-body",
│               "author": ".author-name",
│               "publish_time": ".publish-time"
│           }
│       )
│
└─→ 数据验证:
    - 检查 title 不为空
    - 检查 content 长度 > 100

Step 4: 存储 (06-storage)
│
├─→ 保存数据:
│   brain.export_data(
│       data=all_articles,
│       format="json",
│       path="news_articles.json"
│   )
│
└─→ 完成

Step 5: 分页处理 (07-scheduling)
│
├─→ 发现分页:
│   total_pages = brain.detect_pagination(html)
│
├─→ 批量采集:
│   all_urls = [f"https://news.example.com/list?page={i}"
│               for i in range(1, total_pages + 1)]
│
│   results = brain.batch_call_api(
│       urls=all_urls,
│       concurrency=5,  # 并发数
│       delay=(1, 2)    # 随机延迟 1-2 秒
│   )
│
└─→ 完成
```

**完整代码**

```python
from unified_agent import Brain

brain = Brain()

# 1. 侦查
analysis = brain.smart_investigate("https://news.example.com")
print(f"反爬等级: {analysis.difficulty}")
print(f"推荐方式: {analysis.recommended_approach}")

# 2. 获取列表页
list_url = "https://news.example.com/list?page=1"
response = brain.call_api(list_url)

# 3. 解析列表
articles = brain.scrape_page(
    html=response.text,
    selectors={
        "items": {
            "selector": ".article-item",
            "fields": {
                "title": ".article-title a::text",
                "link": ".article-title a::attr(href)",
                "date": ".article-date::text"
            }
        }
    }
)

# 4. 解析正文
for article in articles['items']:
    detail_response = brain.call_api(article['link'])
    article['content'] = brain.scrape_page(
        html=detail_response.text,
        selectors={"content": ".article-body"}
    )['content']

# 5. 存储
brain.export_data(articles['items'], path="news.json")
```

**注意事项**
- 控制请求频率，尊重 robots.txt
- 检查是否有分页
- 处理相对路径 URL

---

### Case-02: 简单API采集 (公开数据接口)

**场景描述**
```
目标: 采集某平台公开的JSON API数据
特征: RESTful API，返回JSON，无需认证
URL类型: https://api.example.com/v1/products?page=1&limit=20
```

**执行流程**

```
Step 1: 侦查 - 发现API
│
├─→ 打开 DevTools → Network → XHR/Fetch
├─→ 观察请求:
│   GET /v1/products?page=1&limit=20
│   Response: {"data": [...], "total": 1000, "page": 1}
│
├─→ 分析:
│   - 无签名参数 ✓
│   - 无认证头 ✓
│   - 分页参数明确 ✓
│
└─→ 决策: 直接调用API

Step 2: 测试API
│
├─→ 复制请求:
│   curl "https://api.example.com/v1/products?page=1&limit=20"
│
├─→ 验证响应:
│   - 状态: 200 ✓
│   - 数据完整 ✓
│
└─→ 确认可行

Step 3: 批量采集
│
├─→ 计算总页数:
│   total_pages = ceil(response['total'] / response['limit'])
│
├─→ 构建所有URL:
│   urls = [f"api_url?page={i}&limit=20" for i in range(1, total_pages+1)]
│
├─→ 并发请求:
│   results = brain.batch_call_api(urls, concurrency=10)
│
└─→ 合并数据

Step 4: 数据验证
│
├─→ 检查:
│   - 总数是否匹配
│   - 是否有重复
│   - 是否有缺失
│
└─→ 验证通过 → 存储
```

**完整代码**

```python
import math
from unified_agent import Brain

brain = Brain()

# 1. 获取第一页，确定总数
first_page = brain.call_api(
    url="https://api.example.com/v1/products",
    params={"page": 1, "limit": 100}
)

data = first_page.json()
total = data['total']
limit = 100
total_pages = math.ceil(total / limit)

print(f"总数据: {total}, 总页数: {total_pages}")

# 2. 构建所有请求
all_data = data['data']  # 第一页数据

# 3. 批量获取剩余页
if total_pages > 1:
    urls = [
        f"https://api.example.com/v1/products?page={i}&limit={limit}"
        for i in range(2, total_pages + 1)
    ]

    responses = brain.batch_call_api(
        urls=urls,
        concurrency=5,
        delay=(0.5, 1)
    )

    for resp in responses:
        all_data.extend(resp.json()['data'])

# 4. 验证
assert len(all_data) == total, f"数据不完整: {len(all_data)} vs {total}"

# 5. 存储
brain.export_data(all_data, path="products.json")
print(f"采集完成: {len(all_data)} 条")
```

---

### Case-03: 简单登录后采集 (表单登录)

**场景描述**
```
目标: 登录后采集用户相关数据
特征: Cookie-based 会话，表单登录，无验证码
流程: 登录 → 获取Session → 访问受保护页面
```

**执行流程**

```
Step 1: 分析登录流程
│
├─→ 打开登录页: https://example.com/login
├─→ 查看登录表单:
│   <form action="/login" method="POST">
│     <input name="username">
│     <input name="password">
│     <input name="csrf_token" type="hidden" value="xxx">
│   </form>
│
├─→ 注意:
│   - 是否有 CSRF token (需要先GET获取)
│   - 登录后 Cookie 变化
│   - 是否有重定向
│
└─→ 记录登录参数

Step 2: 执行登录
│
├─→ 获取登录页 (取CSRF):
│   login_page = brain.call_api("https://example.com/login")
│   csrf = brain.extract(login_page, 'input[name="csrf_token"]::attr(value)')
│
├─→ 提交登录:
│   response = brain.call_api(
│       url="https://example.com/login",
│       method="POST",
│       data={
│           "username": "your_username",
│           "password": "your_password",
│           "csrf_token": csrf
│       },
│       allow_redirects=True
│   )
│
├─→ 验证登录:
│   - 检查是否跳转到登录后页面
│   - 检查是否有 session cookie
│   - 检查页面是否有登录成功标识
│
└─→ 保存会话

Step 3: 访问受保护数据
│
├─→ 使用已登录会话:
│   data_page = brain.call_api(
│       url="https://example.com/user/data",
│       use_session=True  # 使用保存的cookie
│   )
│
├─→ 验证数据:
│   - 是否返回了预期数据
│   - 是否被重定向回登录页 (登录失效)
│
└─→ 解析数据

Step 4: 会话管理
│
├─→ 保存会话:
│   brain.save_session("example_session")
│
├─→ 下次使用:
│   brain.load_session("example_session")
│
└─→ 检查会话是否有效:
    is_valid = brain.check_session_valid("https://example.com/user")
```

**完整代码**

```python
from unified_agent import Brain

brain = Brain()

# 配置
LOGIN_URL = "https://example.com/login"
DATA_URL = "https://example.com/user/orders"
USERNAME = "your_username"
PASSWORD = "your_password"

# 1. 获取登录页，提取CSRF
login_page = brain.call_api(LOGIN_URL)
csrf_token = brain.scrape_page(
    html=login_page.text,
    selectors={"csrf": 'input[name="csrf_token"]::attr(value)'}
)['csrf']

print(f"获取到 CSRF Token: {csrf_token[:20]}...")

# 2. 执行登录
login_response = brain.call_api(
    url=LOGIN_URL,
    method="POST",
    data={
        "username": USERNAME,
        "password": PASSWORD,
        "csrf_token": csrf_token
    }
)

# 3. 验证登录是否成功
if "logout" in login_response.text or "Welcome" in login_response.text:
    print("登录成功!")
    brain.save_session("example_session")
else:
    raise Exception("登录失败，请检查凭据")

# 4. 访问受保护数据
data_response = brain.call_api(DATA_URL)
orders = brain.scrape_page(
    html=data_response.text,
    selectors={
        "orders": {
            "selector": ".order-item",
            "fields": {
                "order_id": ".order-id::text",
                "amount": ".order-amount::text",
                "status": ".order-status::text"
            }
        }
    }
)

# 5. 存储
brain.export_data(orders['orders'], path="my_orders.json")
```

---

## 三、中等案例

### Case-04: Cookie验证网站

**场景描述**
```
目标: 网站通过特定Cookie验证访问
特征: 必须携带特定Cookie才能获取数据
类型: 反爬Cookie、设备Cookie、轨迹Cookie等
```

**执行流程**

```
Step 1: 侦查 - 发现Cookie要求
│
├─→ 直接请求API:
│   curl "https://example.com/api/data"
│   → 响应: {"error": "invalid session"} 或 403
│
├─→ 使用浏览器请求同一接口:
│   → 响应: 正常数据
│
├─→ 对比差异:
│   浏览器请求多了 Cookie: _session=xxx; _device=yyy
│
└─→ 确认: 需要特定Cookie

Step 2: 分析Cookie来源
│
├─→ Cookie类型判断:
│   │
│   ├─ 服务端设置的 (Set-Cookie)
│   │   └─→ 访问特定页面自动获取
│   │
│   ├─ JS生成的
│   │   └─→ 需要执行JS或逆向
│   │
│   └─ 需要登录获取的
│       └─→ 先完成登录流程
│
├─→ 本案例: JS生成的 _device cookie
│
└─→ 选择方案: 使用浏览器自动化

Step 3: 使用浏览器获取Cookie
│
├─→ 启动浏览器:
│   browser = brain.launch_browser(headless=True)
│   page = browser.new_page()
│
├─→ 访问目标页面 (触发Cookie生成):
│   page.goto("https://example.com")
│   page.wait_for_timeout(3000)  # 等待JS执行
│
├─→ 提取Cookie:
│   cookies = page.context.cookies()
│   device_cookie = next(c for c in cookies if c['name'] == '_device')
│
└─→ 保存Cookie供后续使用

Step 4: 使用Cookie请求API
│
├─→ 带Cookie请求:
│   response = brain.call_api(
│       url="https://example.com/api/data",
│       cookies={"_device": device_cookie['value']}
│   )
│
├─→ 验证:
│   - 响应正常 ✓
│   - 数据完整 ✓
│
└─→ 继续采集

Step 5: Cookie刷新策略
│
├─→ Cookie有效期监控:
│   - 记录Cookie获取时间
│   - 设置刷新阈值 (如 1 小时)
│
├─→ 自动刷新:
│   if cookie_age > threshold:
│       重新获取cookie
│
└─→ 失败时自动刷新:
    if response.status == 403:
        refresh_cookie()
        retry()
```

**完整代码**

```python
from unified_agent import Brain
import time

brain = Brain()

class CookieManager:
    def __init__(self):
        self.cookies = {}
        self.last_refresh = 0
        self.refresh_interval = 3600  # 1小时

    def need_refresh(self):
        return time.time() - self.last_refresh > self.refresh_interval

    def refresh_cookies(self):
        """使用浏览器获取新Cookie"""
        browser = brain.launch_browser(headless=True)
        page = browser.new_page()

        try:
            page.goto("https://example.com")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)  # 等待JS生成Cookie

            all_cookies = page.context.cookies()
            self.cookies = {c['name']: c['value'] for c in all_cookies}
            self.last_refresh = time.time()

            print(f"Cookie刷新成功: {list(self.cookies.keys())}")
        finally:
            browser.close()

        return self.cookies

    def get_cookies(self):
        if self.need_refresh() or not self.cookies:
            return self.refresh_cookies()
        return self.cookies

# 使用
cookie_mgr = CookieManager()

def fetch_data(url):
    cookies = cookie_mgr.get_cookies()
    response = brain.call_api(url, cookies=cookies)

    if response.status_code == 403:
        # Cookie失效，强制刷新
        cookies = cookie_mgr.refresh_cookies()
        response = brain.call_api(url, cookies=cookies)

    return response.json()

# 采集数据
data = fetch_data("https://example.com/api/products")
print(f"获取到 {len(data)} 条数据")
```

---

### Case-05: 简单签名参数网站

**场景描述**
```
目标: 接口需要签名参数验证
特征: URL中有 sign/signature/token 等参数
难度: 签名算法较简单 (MD5/时间戳)
```

**执行流程**

```
Step 1: 发现签名参数
│
├─→ 观察请求:
│   GET /api/data?ts=1706345678&sign=a1b2c3d4...
│
├─→ 多次请求对比:
│   请求1: ts=1706345678, sign=a1b2c3d4
│   请求2: ts=1706345679, sign=e5f6g7h8
│
├─→ 规律分析:
│   - ts 是时间戳 (秒级)
│   - sign 随时间变化，长度32 (可能是MD5)
│
└─→ 需要找到签名算法

Step 2: 定位签名代码
│
├─→ 搜索关键字:
│   - 在 Sources 面板搜索 "sign"
│   - 搜索 "md5", "hmac", "crypto"
│
├─→ 设置断点:
│   - 在网络请求发出前设置 XHR 断点
│   - 单步调试追踪
│
├─→ 找到签名函数:
│   function getSign(params) {
│       let str = Object.keys(params).sort().map(k => `${k}=${params[k]}`).join('&');
│       str += '&key=secret123';
│       return md5(str);
│   }
│
└─→ 记录算法

Step 3: 复现签名算法
│
├─→ Python实现:
│   import hashlib
│
│   def generate_sign(params, secret='secret123'):
│       sorted_str = '&'.join(f'{k}={v}' for k, v in sorted(params.items()))
│       sign_str = f'{sorted_str}&key={secret}'
│       return hashlib.md5(sign_str.encode()).hexdigest()
│
├─→ 验证:
│   - 使用相同参数生成签名
│   - 对比与网站生成的签名是否一致
│
└─→ 验证通过

Step 4: 使用签名请求
│
├─→ 构建请求:
│   import time
│
│   params = {
│       'page': 1,
│       'limit': 20,
│       'ts': int(time.time())
│   }
│   params['sign'] = generate_sign(params)
│
│   response = brain.call_api(url, params=params)
│
└─→ 请求成功
```

**完整代码**

```python
import hashlib
import time
from unified_agent import Brain

brain = Brain()

# 签名配置
SECRET_KEY = "secret123"
BASE_URL = "https://api.example.com/data"

def generate_sign(params: dict) -> str:
    """生成签名"""
    # 按key排序
    sorted_items = sorted(params.items())
    # 拼接字符串
    sign_str = '&'.join(f'{k}={v}' for k, v in sorted_items)
    # 加上密钥
    sign_str += f'&key={SECRET_KEY}'
    # MD5
    return hashlib.md5(sign_str.encode()).hexdigest()

def fetch_with_sign(page: int, limit: int = 20) -> dict:
    """带签名的请求"""
    params = {
        'page': page,
        'limit': limit,
        'ts': int(time.time())
    }
    params['sign'] = generate_sign(params)

    response = brain.call_api(BASE_URL, params=params)

    if response.status_code != 200:
        raise Exception(f"请求失败: {response.status_code}")

    return response.json()

# 测试
data = fetch_with_sign(page=1)
print(f"获取数据: {data}")

# 批量采集
all_data = []
for page in range(1, 11):
    result = fetch_with_sign(page)
    all_data.extend(result['data'])
    time.sleep(1)  # 请求间隔

brain.export_data(all_data, path="signed_data.json")
```

---

### Case-06: 图形验证码网站

**场景描述**
```
目标: 请求或登录时出现图形验证码
特征: 简单图片验证码 (4-6位数字/字母)
方案: OCR识别或打码平台
```

**执行流程**

```
Step 1: 分析验证码
│
├─→ 获取验证码图片:
│   GET /captcha/image?r=random
│   Response: 图片二进制
│
├─→ 关联机制:
│   - 验证码与 session/cookie 绑定
│   - 或返回 captcha_id 需要一起提交
│
├─→ 图片分析:
│   - 类型: 数字+字母
│   - 长度: 4位
│   - 干扰: 少量干扰线
│   - 难度: 简单 (适合OCR)
│
└─→ 选择方案: 使用 ddddocr

Step 2: 验证码识别
│
├─→ OCR方案:
│   import ddddocr
│
│   ocr = ddddocr.DdddOcr()
│
│   # 获取验证码图片
│   img_response = brain.call_api("/captcha/image")
│
│   # 识别
│   code = ocr.classification(img_response.content)
│
├─→ 打码平台方案 (复杂验证码):
│   from third_party import CaptchaSolver
│
│   solver = CaptchaSolver(api_key="xxx")
│   code = solver.solve(img_response.content)
│
└─→ 返回识别结果

Step 3: 提交验证
│
├─→ 登录+验证码:
│   response = brain.call_api(
│       url="/login",
│       method="POST",
│       data={
│           "username": "user",
│           "password": "pass",
│           "captcha": code
│       }
│   )
│
├─→ 验证结果:
│   if "验证码错误" in response.text:
│       # 重新获取并识别
│       retry()
│   else:
│       # 成功
│
└─→ 设置重试上限 (防止无限循环)

Step 4: 错误处理
│
├─→ 识别失败:
│   - 重新获取验证码
│   - 最多重试 5 次
│
├─→ 连续失败:
│   - 切换识别方案 (OCR → 打码平台)
│   - 增加延迟
│
└─→ 最终失败:
    - 记录失败验证码图片
    - 报告用户
```

**完整代码**

```python
import ddddocr
from unified_agent import Brain

brain = Brain()
ocr = ddddocr.DdddOcr()

MAX_RETRY = 5

def get_captcha() -> tuple:
    """获取验证码图片和ID"""
    response = brain.call_api("https://example.com/captcha/image")
    captcha_id = response.headers.get('X-Captcha-Id')
    return response.content, captcha_id

def recognize_captcha(image_bytes: bytes) -> str:
    """识别验证码"""
    return ocr.classification(image_bytes)

def login_with_captcha(username: str, password: str) -> bool:
    """带验证码的登录"""

    for attempt in range(MAX_RETRY):
        # 1. 获取验证码
        img_bytes, captcha_id = get_captcha()

        # 2. 识别
        code = recognize_captcha(img_bytes)
        print(f"尝试 {attempt + 1}: 识别结果 = {code}")

        # 3. 提交登录
        response = brain.call_api(
            url="https://example.com/login",
            method="POST",
            data={
                "username": username,
                "password": password,
                "captcha": code,
                "captcha_id": captcha_id
            }
        )

        # 4. 验证结果
        if "验证码错误" in response.text or "captcha" in response.text.lower():
            print("验证码错误，重试...")
            continue

        if "登录成功" in response.text or response.url.endswith("/dashboard"):
            print("登录成功!")
            return True

        if "密码错误" in response.text:
            raise Exception("用户名或密码错误")

    raise Exception(f"验证码识别失败，已重试 {MAX_RETRY} 次")

# 使用
try:
    success = login_with_captcha("your_user", "your_pass")
except Exception as e:
    print(f"登录失败: {e}")
```

---

### Case-07: 动态加载网站 (无限滚动)

**场景描述**
```
目标: 数据通过滚动动态加载
特征: 页面初始少量数据，滚动到底部加载更多
技术: Ajax/Fetch 分页或无限滚动
```

**执行流程**

```
Step 1: 分析加载机制
│
├─→ 打开 DevTools → Network
├─→ 滚动页面，观察请求:
│   GET /api/items?offset=0&limit=20
│   GET /api/items?offset=20&limit=20
│   GET /api/items?offset=40&limit=20
│
├─→ 分析:
│   - 使用 offset 分页
│   - 每次加载 20 条
│   - 可以直接调用API
│
└─→ 不需要模拟滚动，直接调API

Step 2: 直接调用API (优选)
│
├─→ 循环请求:
│   offset = 0
│   all_data = []
│
│   while True:
│       data = brain.call_api(f"/api/items?offset={offset}&limit=20")
│       items = data.json()['items']
│
│       if not items:  # 没有更多数据
│           break
│
│       all_data.extend(items)
│       offset += 20
│
└─→ 采集完成

Step 3: 如果必须模拟滚动 (无API)
│
├─→ 使用浏览器:
│   page = browser.new_page()
│   page.goto(url)
│
│   # 滚动加载
│   previous_height = 0
│   while True:
│       # 滚动到底部
│       page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
│       page.wait_for_timeout(2000)  # 等待加载
│
│       # 检查是否还有新内容
│       current_height = page.evaluate("document.body.scrollHeight")
│       if current_height == previous_height:
│           break
│       previous_height = current_height
│
│   # 提取数据
│   items = page.query_selector_all(".item")
│
└─→ 采集完成
```

**完整代码 - API方式**

```python
from unified_agent import Brain

brain = Brain()

def fetch_infinite_scroll_api(base_url: str, limit: int = 20) -> list:
    """通过API获取无限滚动数据"""
    all_data = []
    offset = 0

    while True:
        response = brain.call_api(
            url=base_url,
            params={'offset': offset, 'limit': limit}
        )

        data = response.json()
        items = data.get('items', [])

        if not items:
            print(f"加载完成，共 {len(all_data)} 条")
            break

        all_data.extend(items)
        offset += limit
        print(f"已加载: {len(all_data)} 条")

    return all_data

# 使用
data = fetch_infinite_scroll_api("https://example.com/api/items")
brain.export_data(data, path="infinite_data.json")
```

**完整代码 - 浏览器模拟滚动**

```python
from unified_agent import Brain

brain = Brain()

def fetch_infinite_scroll_browser(url: str, max_scrolls: int = 100) -> list:
    """通过浏览器模拟滚动获取数据"""
    browser = brain.launch_browser(headless=True)
    page = browser.new_page()

    try:
        page.goto(url)
        page.wait_for_load_state("networkidle")

        previous_count = 0
        scroll_count = 0

        while scroll_count < max_scrolls:
            # 滚动到底部
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)  # 等待加载

            # 统计当前数据量
            current_count = page.evaluate("document.querySelectorAll('.item').length")

            if current_count == previous_count:
                # 连续2次没有新数据，确认加载完成
                page.wait_for_timeout(3000)
                final_count = page.evaluate("document.querySelectorAll('.item').length")
                if final_count == current_count:
                    break

            previous_count = current_count
            scroll_count += 1
            print(f"滚动 {scroll_count} 次，当前 {current_count} 条")

        # 提取所有数据
        items = page.evaluate("""
            Array.from(document.querySelectorAll('.item')).map(el => ({
                title: el.querySelector('.title')?.textContent,
                link: el.querySelector('a')?.href,
                price: el.querySelector('.price')?.textContent
            }))
        """)

        return items

    finally:
        browser.close()

# 使用
data = fetch_infinite_scroll_browser("https://example.com/products")
brain.export_data(data, path="scroll_data.json")
```

---

## 四、困难案例

### Case-08: 复杂签名网站 (京东h5st)

**场景描述**
```
目标: 京东商品数据采集
特征: h5st 签名参数 (版本4.x)
难度: ⚫ Extreme - 需要JS逆向
```

**执行流程**

```
Step 1: 侦查
│
├─→ 分析请求:
│   GET /api/product?skuId=xxx&h5st=20240127...
│
├─→ 签名特征:
│   - h5st 格式: 日期+版本+hash1+hash2+hash3+hash4
│   - 每次请求都变化
│   - 与请求参数相关
│
└─→ 需要逆向

Step 2: JS逆向 (参考 09-js-reverse.md)
│
├─→ 定位签名入口:
│   - 搜索 "h5st"
│   - 设置 XHR 断点
│   - 追踪调用栈
│
├─→ 分析算法:
│   - 使用了 AES 加密
│   - 包含设备指纹
│   - 时间戳验证
│
├─→ 两种方案:
│   A. 补环境执行原JS
│   B. RPC调用浏览器
│
└─→ 选择: RPC方案 (更稳定)

Step 3: 实现RPC服务
│
├─→ 浏览器端:
│   // 在控制台执行
│   window.getH5st = function(params) {
│       return window._jdSign.sign(params);
│   };
│
├─→ Python端:
│   def get_h5st(params):
│       # 通过 CDP 协议调用
│       result = page.evaluate(f"window.getH5st({json.dumps(params)})")
│       return result
│
└─→ 签名可用

Step 4: 采集数据
│
├─→ 构建请求:
│   params = {'skuId': '12345678'}
│   h5st = get_h5st(params)
│   params['h5st'] = h5st
│
│   response = brain.call_api(api_url, params=params)
│
└─→ 成功获取数据
```

**参考流程图**

```
┌─────────────────────────────────────────────────────────────────┐
│                     京东 h5st 采集流程                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐ │
│   │ 启动浏览器│───▶│ 登录京东  │───▶│ 注入RPC  │───▶│ 开始采集│ │
│   └──────────┘    └──────────┘    └──────────┘    └─────────┘ │
│                                                        │       │
│                                                        ▼       │
│   ┌─────────────────────────────────────────────────────────┐ │
│   │                    采集循环                               │ │
│   │                                                         │ │
│   │   ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐ │ │
│   │   │构建参数│───▶│调用RPC │───▶│获取h5st│───▶│发送请求│ │ │
│   │   └────────┘    │签名    │    └────────┘    └───┬────┘ │ │
│   │                 └────────┘                      │       │ │
│   │                                                 ▼       │ │
│   │   ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐ │ │
│   │   │存储数据│◀───│解析数据│◀───│验证响应│◀───│接收响应│ │ │
│   │   └────────┘    └────────┘    └────────┘    └────────┘ │ │
│   │                                                         │ │
│   └─────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Case-09: 指纹检测网站 (Cloudflare)

**场景描述**
```
目标: 采集受Cloudflare保护的网站
特征: 5秒盾、人机验证、指纹检测
方案: 真实浏览器 + 指纹伪装 + 行为模拟
```

**执行流程**

```
Step 1: 分析保护机制
│
├─→ 访问网站:
│   - 出现 "Checking your browser" 页面
│   - 5秒后可能通过或出现验证码
│
├─→ 检测项:
│   - TLS/JA3 指纹
│   - 浏览器指纹 (Canvas/WebGL)
│   - 行为指纹 (鼠标/键盘)
│
└─→ 需要全方位伪装

Step 2: 配置浏览器
│
├─→ 使用 undetected-chromedriver 或 playwright-stealth:
│   from playwright_stealth import stealth_sync
│
│   browser = playwright.chromium.launch(headless=False)
│   context = browser.new_context()
│   stealth_sync(context)
│   page = context.new_page()
│
├─→ 指纹注入 (参考 11-fingerprint.md):
│   - 固定Canvas指纹
│   - 固定WebGL参数
│   - 设置合理的navigator属性
│
└─→ 配置完成

Step 3: 通过人机验证
│
├─→ 访问页面:
│   page.goto(url)
│
├─→ 等待验证:
│   # 等待页面跳转或内容加载
│   page.wait_for_selector("body:not([data-cf-challenge])", timeout=30000)
│
├─→ 如果出现验证码:
│   - Cloudflare Turnstile: 可能需要人工处理
│   - 或使用第三方验证码解决服务
│
└─→ 验证通过

Step 4: 采集数据
│
├─→ 保持会话:
│   - 保存 cf_clearance cookie
│   - 后续请求携带该cookie
│
├─→ 注意:
│   - 请求频率不能太高
│   - 保持浏览器打开
│   - 定期刷新cookie
│
└─→ 持续采集
```

---

### Case-10: 多因素验证网站

**场景描述**
```
目标: 需要短信/邮箱验证码的网站
特征: 登录后还需要验证手机/邮箱
方案: 需要用户配合或接码平台
```

**执行流程**

```
Step 1: 分析验证流程
│
├─→ 登录流程:
│   1. 输入用户名密码 → 提交
│   2. 发送短信验证码 → 用户收到短信
│   3. 输入验证码 → 验证通过
│   4. 获取登录态
│
└─→ 验证码发送到用户手机

Step 2: 方案选择
│
├─→ 方案A: 用户手动输入
│   - 程序暂停
│   - 提示用户输入收到的验证码
│   - 继续执行
│
├─→ 方案B: 接码平台
│   - 使用第三方虚拟号码
│   - 通过API获取验证码
│   - 自动填入
│
├─→ 方案C: 邮箱验证码
│   - 使用IMAP读取邮件
│   - 解析验证码
│
└─→ 选择合适方案

Step 3: 实现 (用户手动输入)
│
├─→ 代码:
│   # 1. 提交登录
│   brain.call_api("/login", data={...})
│
│   # 2. 触发发送验证码
│   brain.call_api("/send-sms")
│
│   # 3. 等待用户输入
│   code = input("请输入收到的验证码: ")
│
│   # 4. 提交验证码
│   brain.call_api("/verify", data={"code": code})
│
└─→ 登录成功

Step 4: 会话保持
│
├─→ 登录成功后保存会话
├─→ 下次直接使用保存的cookie
├─→ 检测会话是否失效
└─→ 失效则重新验证
```

---

## 五、特殊案例

### Case-11: WebSocket实时数据

**场景描述**
```
目标: 采集通过WebSocket推送的实时数据
特征: ws:// 或 wss:// 连接，持续推送数据
示例: 股票行情、直播弹幕、实时消息
```

**执行流程**

```
Step 1: 分析WebSocket
│
├─→ DevTools → Network → WS
├─→ 观察:
│   - 连接URL: wss://ws.example.com/stream
│   - 协议: 可能需要特定子协议
│   - 认证: 可能需要token
│   - 消息格式: JSON/Binary
│
└─→ 记录连接参数

Step 2: 建立连接
│
├─→ 使用 websockets 库:
│   import websockets
│   import asyncio
│
│   async def connect():
│       uri = "wss://ws.example.com/stream"
│       async with websockets.connect(uri) as ws:
│           # 发送订阅消息
│           await ws.send('{"action":"subscribe","channel":"data"}')
│
│           # 接收数据
│           async for message in ws:
│               data = json.loads(message)
│               process(data)
│
└─→ 连接成功

Step 3: 处理认证
│
├─→ 如果需要token:
│   - 先通过HTTP获取token
│   - 在WS连接URL中携带: wss://...?token=xxx
│   - 或在连接后发送认证消息
│
└─→ 认证通过

Step 4: 数据处理
│
├─→ 实时保存:
│   - 写入文件
│   - 存入数据库
│   - 发送到消息队列
│
├─→ 心跳保持:
│   - 定期发送ping
│   - 响应服务器ping
│
└─→ 断线重连:
    - 监控连接状态
    - 断开后自动重连
```

**完整代码**

```python
import asyncio
import websockets
import json
from datetime import datetime

class WebSocketCollector:
    def __init__(self, url: str, output_file: str):
        self.url = url
        self.output_file = output_file
        self.running = False

    async def connect(self):
        self.running = True

        while self.running:
            try:
                async with websockets.connect(self.url) as ws:
                    print(f"已连接: {self.url}")

                    # 发送订阅
                    await ws.send(json.dumps({
                        "action": "subscribe",
                        "channels": ["market_data"]
                    }))

                    # 接收数据
                    async for message in ws:
                        await self.handle_message(message)

            except websockets.exceptions.ConnectionClosed:
                print("连接断开，5秒后重连...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"错误: {e}，10秒后重连...")
                await asyncio.sleep(10)

    async def handle_message(self, message: str):
        try:
            data = json.loads(message)
            data['received_at'] = datetime.now().isoformat()

            # 保存到文件
            with open(self.output_file, 'a') as f:
                f.write(json.dumps(data) + '\n')

            print(f"收到: {data.get('type', 'unknown')}")
        except json.JSONDecodeError:
            print(f"无法解析消息: {message[:100]}")

    def stop(self):
        self.running = False

# 使用
async def main():
    collector = WebSocketCollector(
        url="wss://ws.example.com/stream",
        output_file="ws_data.jsonl"
    )
    await collector.connect()

asyncio.run(main())
```

---

### Case-12: GraphQL接口

**场景描述**
```
目标: 采集使用GraphQL的网站
特征: 单一端点，POST请求，query/mutation
URL: /graphql 或 /api/graphql
```

**执行流程**

```
Step 1: 发现GraphQL端点
│
├─→ Network观察:
│   POST /graphql
│   Content-Type: application/json
│   Body: {"query": "...", "variables": {...}}
│
├─→ 特征:
│   - 单一URL多种数据
│   - 请求体包含query字段
│
└─→ 确认是GraphQL

Step 2: 分析Schema
│
├─→ 尝试内省查询:
│   query = """
│   {
│     __schema {
│       types { name }
│       queryType { fields { name } }
│     }
│   }
│   """
│
├─→ 如果内省被禁用:
│   - 从网络请求中收集query
│   - 分析前端代码
│
└─→ 获取可用查询

Step 3: 构建查询
│
├─→ 根据需求构建:
│   query = """
│   query GetProducts($page: Int!, $limit: Int!) {
│       products(page: $page, limit: $limit) {
│           id
│           name
│           price
│           description
│       }
│   }
│   """
│
│   variables = {"page": 1, "limit": 20}
│
└─→ 准备请求

Step 4: 发送请求
│
├─→ 执行:
│   response = brain.call_api(
│       url="/graphql",
│       method="POST",
│       json={
│           "query": query,
│           "variables": variables
│       }
│   )
│
│   data = response.json()['data']['products']
│
└─→ 获取数据
```

**完整代码**

```python
from unified_agent import Brain

brain = Brain()

GRAPHQL_ENDPOINT = "https://api.example.com/graphql"

def graphql_query(query: str, variables: dict = None) -> dict:
    """执行GraphQL查询"""
    response = brain.call_api(
        url=GRAPHQL_ENDPOINT,
        method="POST",
        json={
            "query": query,
            "variables": variables or {}
        }
    )

    result = response.json()

    if 'errors' in result:
        raise Exception(f"GraphQL错误: {result['errors']}")

    return result['data']

# 查询产品列表
PRODUCTS_QUERY = """
query GetProducts($page: Int!, $limit: Int!) {
    products(page: $page, limit: $limit) {
        edges {
            node {
                id
                name
                price
                category
                images { url }
            }
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""

# 采集所有产品
all_products = []
page = 1
has_next = True

while has_next:
    result = graphql_query(PRODUCTS_QUERY, {"page": page, "limit": 50})

    products = result['products']['edges']
    all_products.extend([p['node'] for p in products])

    has_next = result['products']['pageInfo']['hasNextPage']
    page += 1

    print(f"已获取 {len(all_products)} 个产品")

brain.export_data(all_products, path="graphql_products.json")
```

---

### Case-13: APP数据抓取

**场景描述**
```
目标: 获取手机APP的数据
特征: 需要抓包获取API，可能有SSL Pinning
方案: mitmproxy + Frida
```

**详细流程请参考 12-mobile.md**

**简化流程**

```
Step 1: 抓包准备
│
├─→ 安装mitmproxy
├─→ 配置代理
├─→ 安装CA证书
└─→ 启动抓包

Step 2: 绕过SSL Pinning (如需要)
│
├─→ 使用Frida脚本
├─→ hook关键函数
└─→ 绕过证书验证

Step 3: 分析请求
│
├─→ 观察API结构
├─→ 分析签名参数
└─→ 记录认证方式

Step 4: 复现请求
│
├─→ 实现签名算法
├─→ 模拟请求头
└─→ 采集数据
```

---

### Case-14: 微信小程序数据

**场景描述**
```
目标: 采集微信小程序数据
特征: 需要特殊工具和方法
方案: 抓包 + 反编译 + 模拟请求
```

**执行流程**

```
Step 1: 获取小程序包
│
├─→ 使用 UnpackMiniprogram 等工具
├─→ 解密 wxapkg 文件
└─→ 获取源代码

Step 2: 分析代码
│
├─→ 找到 API 请求
├─→ 分析签名/加密
└─→ 记录参数

Step 3: 模拟请求
│
├─→ 构建必要header:
│   - content-type
│   - referer
│   - 微信特有header
│
├─→ 处理认证:
│   - 获取 session_key
│   - 处理用户授权
│
└─→ 发送请求

Step 4: 数据采集
│
├─→ 保持会话
├─→ 处理分页
└─→ 存储数据
```

---

## 诊断日志格式

```yaml
e2e_case_execution:
  case_id: "case-xx"
  target_url: "目标URL"
  start_time: "开始时间"

  steps:
    - step: 1
      module: "reconnaissance"
      action: "分析目标"
      result: "success"
      findings: ["反爬等级LOW", "SSR渲染"]

    - step: 2
      module: "request"
      action: "获取页面"
      result: "success"
      details: "200 OK, 50KB"

    - step: 3
      module: "parsing"
      action: "提取数据"
      result: "success"
      count: 100

  end_time: "结束时间"
  total_duration: "耗时"
  outcome: "success"
  data_count: 100

  lessons:
    - "该网站无反爬，直接HTTP即可"
    - "分页参数为page，从1开始"
```

---

## 关联模块

- **01-reconnaissance.md** - 侦查方法
- **04-request.md** - 请求配置
- **05-parsing.md** - 数据解析
- **09-js-reverse.md** - JS逆向
- **10-captcha.md** - 验证码处理
- **11-fingerprint.md** - 指纹伪装
- **12-mobile.md** - 移动端抓取
- **18-brain-controller.md** - 执行控制
- **19-fault-decision-tree.md** - 故障处理
