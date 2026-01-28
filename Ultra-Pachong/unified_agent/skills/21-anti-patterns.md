# 21-anti-patterns.md - 反面教材库

## 模块目标

| 目标 | KPI | 验收标准 |
|------|-----|----------|
| 从失败中学习 | 同类错误重复率 < 5% | 不重蹈覆辙 |
| 识别危险模式 | 风险识别率 > 95% | 提前预警 |
| 明确禁止行为 | 违规操作 0 次 | 绝对不做 |

**核心原则**：`给出需求，必须完成` - 知道什么不能做，才能更好地完成任务。

---

## 一、绝对禁止行为 (红线)

### 🚫 RED-01: 伪造数据

**错误行为**
```python
# ❌ 错误: 数据为空时伪造数据
def get_product_info(url):
    try:
        data = scrape(url)
        if not data:
            # 伪造数据填充 - 绝对禁止！
            return {
                "title": "商品标题",
                "price": "99.00",
                "stock": "有货"
            }
        return data
    except:
        # 出错也伪造 - 绝对禁止！
        return {"title": "默认商品", "price": "0"}
```

**为什么错误**
```
1. 数据失去可信度 - 用户无法区分真假
2. 误导决策 - 基于假数据做出错误判断
3. 无法追溯 - 不知道哪些是真实数据
4. 违背诚信 - AI必须诚实
```

**正确做法**
```python
# ✅ 正确: 明确标记数据状态
def get_product_info(url):
    result = {
        "url": url,
        "status": "pending",
        "data": None,
        "error": None,
        "attempts": 0
    }

    try:
        data = scrape(url)
        if data:
            result["status"] = "success"
            result["data"] = data
        else:
            result["status"] = "empty"
            result["error"] = "数据为空，页面可能已下架或结构变化"
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)

    result["attempts"] = 1
    result["timestamp"] = datetime.now().isoformat()

    return result
```

---

### 🚫 RED-02: 忽略错误静默继续

**错误行为**
```python
# ❌ 错误: 捕获异常但不处理
def batch_scrape(urls):
    results = []
    for url in urls:
        try:
            data = scrape(url)
            results.append(data)
        except:
            pass  # 静默忽略 - 危险！

    return results  # 用户不知道有失败
```

**为什么错误**
```
1. 数据不完整 - 用户以为全部成功
2. 问题被掩盖 - 无法发现系统问题
3. 无法修复 - 不知道哪些失败了
4. 统计失真 - 成功率虚高
```

**正确做法**
```python
# ✅ 正确: 记录每个请求的状态
def batch_scrape(urls):
    results = {
        "success": [],
        "failed": [],
        "summary": {
            "total": len(urls),
            "success_count": 0,
            "fail_count": 0
        }
    }

    for url in urls:
        try:
            data = scrape(url)
            results["success"].append({"url": url, "data": data})
            results["summary"]["success_count"] += 1
        except Exception as e:
            results["failed"].append({
                "url": url,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            results["summary"]["fail_count"] += 1

            # 记录到日志
            logger.error(f"采集失败: {url}, 错误: {e}")

    return results
```

---

### 🚫 RED-03: 无限重试

**错误行为**
```python
# ❌ 错误: 没有重试上限
def fetch_with_retry(url):
    while True:  # 无限循环 - 危险！
        try:
            return requests.get(url)
        except:
            time.sleep(1)
            continue  # 永远重试
```

**为什么错误**
```
1. 资源耗尽 - CPU/内存持续占用
2. 任务阻塞 - 卡在一个URL无法继续
3. IP被封 - 持续请求加速封禁
4. 无法退出 - 程序可能永远无法结束
```

**正确做法**
```python
# ✅ 正确: 有限重试 + 指数退避
def fetch_with_retry(url, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                # 最后一次尝试失败
                raise Exception(f"请求失败，已重试{max_retries}次: {e}")

            delay = base_delay * (2 ** attempt)  # 指数退避
            logger.warning(f"重试 {attempt + 1}/{max_retries}, 等待 {delay}s")
            time.sleep(delay)
```

---

### 🚫 RED-04: 硬编码敏感信息

**错误行为**
```python
# ❌ 错误: 密码直接写在代码中
class Scraper:
    def __init__(self):
        self.username = "admin"
        self.password = "P@ssw0rd123"  # 硬编码密码 - 危险！
        self.api_key = "sk-1234567890abcdef"  # 硬编码API Key

    def login(self):
        requests.post("/login", data={
            "user": self.username,
            "pass": self.password
        })
```

**为什么错误**
```
1. 代码泄露 = 凭据泄露
2. 版本控制会记录历史
3. 无法轮换密码
4. 多环境无法区分
```

**正确做法**
```python
# ✅ 正确: 使用环境变量或配置文件
import os
from dotenv import load_dotenv

load_dotenv()

class Scraper:
    def __init__(self):
        self.username = os.getenv("SCRAPER_USERNAME")
        self.password = os.getenv("SCRAPER_PASSWORD")
        self.api_key = os.getenv("API_KEY")

        if not all([self.username, self.password]):
            raise ValueError("缺少必要的凭据配置")

    def login(self):
        # 凭据从环境变量获取
        ...
```

---

### 🚫 RED-05: 绕过认证/授权非法访问

**错误行为**
```python
# ❌ 错误: 尝试绕过认证
def access_admin_panel():
    # 尝试猜测管理员URL
    for path in ["/admin", "/administrator", "/wp-admin"]:
        response = requests.get(f"{base_url}{path}")
        if response.status_code == 200:
            return response  # 非法访问

# ❌ 错误: SQL注入尝试
def login(username, password):
    payload = f"' OR '1'='1"  # SQL注入 - 非法！
    requests.post("/login", data={"user": payload})
```

**为什么错误**
```
1. 违法行为 - 可能触犯法律
2. 道德问题 - AI不应协助非法活动
3. 信任破坏 - 失去用户信任
4. 风险巨大 - 可能导致严重后果
```

**正确做法**
```python
# ✅ 正确: 只访问授权的资源
def access_data(url, credentials=None):
    # 只访问明确授权的URL
    if not is_authorized_url(url):
        raise UnauthorizedAccessError(f"未授权访问: {url}")

    # 使用合法凭据
    if credentials:
        response = requests.get(url, auth=credentials)
    else:
        response = requests.get(url)

    return response
```

---

## 二、常见错误模式 (黄线)

### ⚠️ WARN-01: 请求频率过高

**错误行为**
```python
# ⚠️ 警告: 无延迟批量请求
def scrape_all(urls):
    for url in urls:
        response = requests.get(url)  # 无延迟
        process(response)
    # 可能 1 秒内发送 100 个请求
```

**后果**
```
1. 触发频率限制 (429)
2. IP被临时或永久封禁
3. 服务器过载
4. 数据不完整
```

**正确做法**
```python
# ✅ 正确: 合理的请求间隔
import random
import time

def scrape_all(urls, min_delay=1, max_delay=3):
    for url in urls:
        response = requests.get(url)
        process(response)

        # 随机延迟，模拟人类行为
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
```

**最佳实践**
```
- 普通网站: 1-3 秒间隔
- 严格网站: 5-10 秒间隔
- 参考 robots.txt 的 Crawl-delay
- 观察响应时间，动态调整
```

---

### ⚠️ WARN-02: 不检查响应状态

**错误行为**
```python
# ⚠️ 警告: 假设请求总是成功
def get_data(url):
    response = requests.get(url)
    return response.json()  # 如果不是200或不是JSON会崩溃
```

**后果**
```
1. 程序崩溃 (500/404等状态码)
2. 解析错误 (响应不是JSON)
3. 获取错误数据 (重定向到错误页)
4. 逻辑错误 (空响应)
```

**正确做法**
```python
# ✅ 正确: 完整的响应检查
def get_data(url):
    try:
        response = requests.get(url, timeout=30)

        # 检查状态码
        if response.status_code != 200:
            logger.error(f"非200响应: {response.status_code}")
            return None

        # 检查内容类型
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            logger.error(f"非JSON响应: {content_type}")
            return None

        # 尝试解析JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return None

        # 检查数据结构
        if not data or 'error' in data:
            logger.error(f"响应包含错误: {data}")
            return None

        return data

    except requests.RequestException as e:
        logger.error(f"请求异常: {e}")
        return None
```

---

### ⚠️ WARN-03: 硬编码选择器

**错误行为**
```python
# ⚠️ 警告: 过于具体的选择器
def get_price(html):
    soup = BeautifulSoup(html)
    # 太脆弱 - 任何结构变化都会失效
    price = soup.select_one(
        "div.container > div.row:nth-child(3) > div:nth-child(2) > span.price"
    )
    return price.text
```

**后果**
```
1. 网站微小改动就失效
2. 不同页面结构无法复用
3. 维护成本高
4. 难以调试
```

**正确做法**
```python
# ✅ 正确: 多重选择器 + 容错
def get_price(html):
    soup = BeautifulSoup(html)

    # 按优先级尝试多个选择器
    selectors = [
        '[data-price]::attr(data-price)',  # 数据属性优先
        '.product-price .price',           # 语义class
        '.price',                          # 通用class
        '#price',                          # ID
    ]

    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            price_text = element.get('data-price') or element.text
            if price_text:
                return clean_price(price_text)

    # 都失败了，记录并返回None
    logger.warning(f"无法找到价格元素")
    return None

def clean_price(text):
    """清洗价格文本"""
    import re
    match = re.search(r'[\d,.]+', text)
    return match.group() if match else None
```

---

### ⚠️ WARN-04: 不保存中间状态

**错误行为**
```python
# ⚠️ 警告: 所有数据在内存中，程序崩溃全丢失
def scrape_large_site(urls):
    all_data = []  # 内存中积累

    for url in urls:
        data = scrape(url)
        all_data.append(data)
        # 如果在第 9999 个URL崩溃，之前的数据全丢

    # 最后才保存
    save(all_data)
```

**后果**
```
1. 崩溃丢失所有进度
2. 内存溢出风险
3. 无法断点续爬
4. 长时间无输出
```

**正确做法**
```python
# ✅ 正确: 增量保存 + 断点续爬
import json

class CheckpointScraper:
    def __init__(self, checkpoint_file="checkpoint.json"):
        self.checkpoint_file = checkpoint_file
        self.completed = set()
        self.load_checkpoint()

    def load_checkpoint(self):
        try:
            with open(self.checkpoint_file) as f:
                data = json.load(f)
                self.completed = set(data.get("completed", []))
        except FileNotFoundError:
            pass

    def save_checkpoint(self):
        with open(self.checkpoint_file, 'w') as f:
            json.dump({"completed": list(self.completed)}, f)

    def scrape(self, urls, output_file):
        with open(output_file, 'a') as f:
            for i, url in enumerate(urls):
                if url in self.completed:
                    continue  # 跳过已完成

                try:
                    data = self.fetch(url)
                    # 立即写入文件
                    f.write(json.dumps(data) + '\n')
                    f.flush()

                    self.completed.add(url)

                    # 定期保存检查点
                    if i % 100 == 0:
                        self.save_checkpoint()

                except Exception as e:
                    logger.error(f"失败: {url}, {e}")

        self.save_checkpoint()
```

---

### ⚠️ WARN-05: 忽略编码问题

**错误行为**
```python
# ⚠️ 警告: 不处理编码
def get_content(url):
    response = requests.get(url)
    # 可能出现乱码
    return response.text
```

**后果**
```
1. 中文乱码
2. 特殊字符丢失
3. 解析错误
4. 数据损坏
```

**正确做法**
```python
# ✅ 正确: 正确处理编码
def get_content(url):
    response = requests.get(url)

    # 方法1: 让requests自动检测
    response.encoding = response.apparent_encoding

    # 方法2: 从响应头获取
    content_type = response.headers.get('Content-Type', '')
    if 'charset=' in content_type:
        encoding = content_type.split('charset=')[-1]
        response.encoding = encoding

    # 方法3: 从HTML meta获取
    if '<meta charset=' in response.text[:1000]:
        import re
        match = re.search(r'charset=["\']?([^"\'\s>]+)', response.text[:1000])
        if match:
            response.encoding = match.group(1)

    return response.text
```

---

### ⚠️ WARN-06: 不验证数据完整性

**错误行为**
```python
# ⚠️ 警告: 不检查数据是否完整
def save_product(product):
    # 直接保存，不验证
    db.insert(product)
```

**后果**
```
1. 存储不完整数据
2. 后续处理出错
3. 数据质量差
4. 难以发现问题
```

**正确做法**
```python
# ✅ 正确: 验证后再保存
from dataclasses import dataclass
from typing import Optional

@dataclass
class Product:
    id: str
    title: str
    price: float
    url: str
    description: Optional[str] = None

    def validate(self) -> tuple[bool, list[str]]:
        errors = []

        if not self.id:
            errors.append("缺少id")
        if not self.title or len(self.title) < 2:
            errors.append("标题无效")
        if self.price is None or self.price < 0:
            errors.append("价格无效")
        if not self.url or not self.url.startswith("http"):
            errors.append("URL无效")

        return len(errors) == 0, errors

def save_product(data: dict):
    product = Product(**data)
    is_valid, errors = product.validate()

    if not is_valid:
        logger.warning(f"数据验证失败: {errors}, 数据: {data}")
        # 保存到错误队列，而不是丢弃
        save_to_error_queue(data, errors)
        return False

    db.insert(product)
    return True
```

---

## 三、反模式案例 (真实失败案例)

### CASE-F01: 签名算法猜测失败

**错误场景**
```
任务: 采集某电商网站数据
观察: URL中有sign参数，看起来是MD5
错误决定: 猜测签名算法，盲目尝试
结果: 浪费3小时，全部失败
```

**错误过程**
```python
# ❌ 错误: 盲目猜测签名算法
def guess_sign(params):
    # 猜测1: 简单MD5
    sign1 = md5(str(params))
    if test_request(sign1): return sign1

    # 猜测2: 排序后MD5
    sign2 = md5(sorted_params(params))
    if test_request(sign2): return sign2

    # 猜测3: 加盐MD5
    for salt in ['', 'key', 'secret', 'salt']:
        sign3 = md5(str(params) + salt)
        if test_request(sign3): return sign3

    # 永远猜不对...
```

**为什么失败**
```
1. 签名算法千变万化，猜测效率极低
2. 可能有时间戳验证，过期就失效
3. 可能有设备指纹参与
4. 浪费时间且容易被封IP
```

**正确方法**
```python
# ✅ 正确: 通过JS逆向找到算法
def correct_approach():
    """
    正确流程:
    1. 打开 DevTools → Network
    2. 找到带sign的请求
    3. 设置 XHR 断点
    4. 追踪调用栈找到签名函数
    5. 分析或提取签名代码
    6. 复现算法
    """
    # 参考 09-js-reverse.md
    pass
```

---

### CASE-F02: Cookie依赖判断错误

**错误场景**
```
任务: 采集需要登录的网站
观察: 不带cookie返回空数据
错误决定: 以为只需要session cookie
结果: 请求被拦截，无法获取数据
```

**错误过程**
```python
# ❌ 错误: 只携带部分cookie
def fetch_with_login():
    # 登录获取cookie
    login_response = requests.post("/login", data={...})

    # 只保存了session cookie
    session_id = login_response.cookies.get("session_id")

    # 请求数据
    response = requests.get("/api/data", cookies={"session_id": session_id})
    # 返回空或被拦截
```

**为什么失败**
```
实际需要的cookie:
- session_id (登录态)
- _device (设备标识) - 缺失！
- _trace (追踪ID) - 缺失！
```

**正确方法**
```python
# ✅ 正确: 使用Session保持所有cookie
def correct_approach():
    session = requests.Session()

    # 访问首页，获取设备cookie
    session.get("https://example.com")

    # 登录
    session.post("/login", data={...})

    # 此时session自动保持所有cookie
    response = session.get("/api/data")

    # 检查获取了哪些cookie
    print("所有cookie:", dict(session.cookies))
```

---

### CASE-F03: 反爬等级误判

**错误场景**
```
任务: 采集京东商品数据
错误判断: 以为只是普通Cookie验证
错误决定: 使用简单requests请求
结果: 全部返回空数据或被拦截
```

**错误过程**
```python
# ❌ 错误: 低估反爬难度
def naive_jd_scraper():
    # 以为加个User-Agent就行
    headers = {"User-Agent": "Mozilla/5.0..."}
    response = requests.get(
        "https://item.jd.com/12345.html",
        headers=headers
    )
    # 返回的是空页面或验证页面
```

**为什么失败**
```
京东反爬机制:
1. h5st签名验证 (算法复杂)
2. 设备指纹检测
3. 行为分析
4. 风控系统

用简单请求完全无法绑过
```

**正确方法**
```python
# ✅ 正确: 先侦查再决策
def correct_approach():
    # 1. 先进行侦查
    analysis = brain.smart_investigate("https://item.jd.com")

    # 2. 根据侦查结果决策
    print(f"反爬等级: {analysis.difficulty}")  # EXTREME
    print(f"需要: {analysis.requirements}")
    # 需要: h5st签名, 浏览器环境, 设备指纹

    # 3. 使用正确的方案
    # 参考 Case-08 京东h5st案例
```

---

### CASE-F04: 并发过高导致封禁

**错误场景**
```
任务: 采集10万条数据，追求速度
错误决定: 开100并发快速采集
结果: 5分钟内IP被永久封禁
```

**错误过程**
```python
# ❌ 错误: 激进的并发策略
import asyncio

async def aggressive_scraper(urls):
    # 100并发，无延迟
    semaphore = asyncio.Semaphore(100)

    async def fetch(url):
        async with semaphore:
            return await session.get(url)

    # 同时发起大量请求
    tasks = [fetch(url) for url in urls]
    return await asyncio.gather(*tasks)

# 1秒内发送上百请求 → 立即被封
```

**后果**
```
1. IP被永久封禁
2. 账号被封
3. 所有数据作废
4. 需要更换IP和账号
```

**正确方法**
```python
# ✅ 正确: 保守的并发策略
async def conservative_scraper(urls):
    # 低并发
    semaphore = asyncio.Semaphore(5)

    async def fetch(url):
        async with semaphore:
            result = await session.get(url)
            # 请求后延迟
            await asyncio.sleep(random.uniform(1, 3))
            return result

    results = []
    for batch in chunks(urls, 100):
        batch_results = await asyncio.gather(*[fetch(u) for u in batch])
        results.extend(batch_results)

        # 批次间休息
        await asyncio.sleep(60)

    return results
```

**经验总结**
```
宁可慢一点，也不要被封:
- 10万数据，10并发，3秒间隔 ≈ 8小时
- 被封后重新开始可能需要数天
```

---

### CASE-F05: 不检测蜜罐数据

**错误场景**
```
任务: 采集商品价格数据
陷阱: 网站返回了假数据
结果: 采集了10万条假数据，全部作废
```

**错误过程**
```python
# ❌ 错误: 不验证数据真实性
def scrape_prices(urls):
    results = []
    for url in urls:
        data = fetch_and_parse(url)
        # 直接存储，不验证
        results.append(data)

    save_all(results)
    # 事后发现：所有价格都是 0.01
```

**蜜罐特征**
```
1. 价格异常 (0.01, 9999999)
2. 名称重复或规律性强
3. 链接不可访问
4. 时间戳相同
5. 数据过于规整
```

**正确方法**
```python
# ✅ 正确: 数据真实性验证
def scrape_with_validation(urls):
    results = []
    suspicious_count = 0

    for url in urls:
        data = fetch_and_parse(url)

        # 蜜罐检测
        if is_honeypot(data):
            suspicious_count += 1
            logger.warning(f"疑似蜜罐数据: {data}")

            # 连续多次可疑，停止采集
            if suspicious_count > 10:
                logger.error("检测到蜜罐，停止采集")
                break

            continue

        results.append(data)

    return results

def is_honeypot(data):
    """蜜罐检测"""
    checks = [
        data.get('price', 0) < 0.1,  # 价格过低
        data.get('price', 0) > 100000,  # 价格过高
        len(set(data.get('name', '').split())) < 2,  # 名称太短
        'test' in data.get('name', '').lower(),  # 测试数据
    ]
    return any(checks)
```

---

## 四、决策反模式

### DEC-01: 过早优化

**错误模式**
```
还没跑通就开始优化性能
还没验证就开始考虑扩展性
还没数据就开始设计数据库
```

**正确顺序**
```
1. 先跑通一个URL
2. 验证数据正确
3. 扩展到批量
4. 再考虑性能优化
```

---

### DEC-02: 过度设计

**错误模式**
```
简单任务用复杂架构
采集100条数据却部署分布式系统
临时脚本却写成框架
```

**正确原则**
```
KISS - Keep It Simple, Stupid
够用就好，按需扩展
```

---

### DEC-03: 忽视侦查

**错误模式**
```
拿到URL就开始写代码
不分析直接用以前的方案
失败了才回头看
```

**正确原则**
```
侦查优先
知己知彼
一分侦查，十分回报
```

---

## 五、检查清单

### 开始前检查

```markdown
□ 是否进行了充分侦查?
□ 是否了解目标网站的反爬等级?
□ 是否有合法的访问权限?
□ 是否准备了错误处理方案?
□ 是否设置了重试上限?
□ 是否有数据验证机制?
```

### 编码时检查

```markdown
□ 是否处理了所有异常?
□ 是否检查了响应状态?
□ 是否有合理的延迟?
□ 是否保存了中间状态?
□ 是否记录了日志?
□ 是否避免了硬编码?
```

### 运行时检查

```markdown
□ 数据是否真实有效?
□ 是否有异常模式?
□ 成功率是否正常?
□ 是否被限流/封禁?
□ 内存使用是否正常?
□ 是否有进度输出?
```

---

## 诊断日志格式

```yaml
anti_pattern_detected:
  timestamp: "检测时间"
  pattern_id: "WARN-01"
  pattern_name: "请求频率过高"
  severity: "warning"

  context:
    code_location: "scraper.py:42"
    current_behavior: "无延迟批量请求"
    risk_assessment: "高风险，可能导致IP封禁"

  correction:
    recommended_action: "添加1-3秒随机延迟"
    code_example: "time.sleep(random.uniform(1, 3))"

  outcome:
    action_taken: "已修正"
    result: "请求正常，未被封禁"
```

---

## 关联模块

- **17-feedback-loop.md** - 从错误中学习
- **19-fault-decision-tree.md** - 故障处理
- **08-diagnosis.md** - 问题诊断
- **18-brain-controller.md** - 决策控制
