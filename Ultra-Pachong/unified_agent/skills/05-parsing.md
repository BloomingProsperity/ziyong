---
skill_id: "05-parsing"
name: "解析模块"
version: "1.1.0"
status: "stable"                    # draft | beta | stable | deprecated
implementation_status: "complete"   # none | partial | complete
difficulty: 2
category: "core"

description: "数据提取、结构化与清洗"

triggers:
  - condition: "response.received == true"
  - pattern: "(解析|提取|抓取).*(数据|内容|字段)"

dependencies:
  required: []
  optional:
    - skill: "25-data-schema"
      reason: "数据校验"

external_dependencies:
  required:
    - name: "beautifulsoup4"
      version: ">=4.12.0"
      type: "python_package"
      install: "pip install beautifulsoup4"
    - name: "lxml"
      version: ">=4.9.0"
      type: "python_package"
      install: "pip install lxml"
  optional:
    - name: "parsel"
      version: ">=1.8.0"
      condition: "高级选择器"
      type: "python_package"
      install: "pip install parsel"

inputs:
  - name: "content"
    type: "string | bytes"
    required: true
  - name: "selectors"
    type: "dict[str, str]"
    required: false
  - name: "content_type"
    type: "string"
    default: "html"

outputs:
  - name: "ParsedData"
    fields: [data, errors, metadata]
---

# 05 - 解析模块 (Parsing)

## 模块目标

| 目标 | SLO | 适用范围 | 降级策略 |
|------|-----|----------|----------|
| 数据提取 | 成功率 ≥ 98% | 选择器正确 | 标记partial |
| 选择器有效 | 匹配率 ≥ 95% | 结构稳定页 | 备选选择器 |
| 分页处理 | 完整率 ≥ 99% | 标准分页 | 记录缺失页 |
| 数据清洗 | 格式正确率 ≥ 99% | 已定义规则 | 保留原始值 |

## 模块概述

解析模块负责从页面或 API 响应中提取结构化数据。

```
┌─────────────────────────────────────────────────────────────────┐
│                        解析模块架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐       │
│   │ 页面/响应 │────────▶│ 解析引擎  │────────▶│ 结构化数据│       │
│   └──────────┘         └──────────┘         └──────────┘       │
│                              │                                  │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│        ┌─────────┐     ┌─────────┐     ┌─────────┐             │
│        │ CSS选择器│     │  XPath  │     │  正则   │             │
│        └─────────┘     └─────────┘     └─────────┘             │
│              │               │               │                  │
│              └───────────────┼───────────────┘                  │
│                              ▼                                  │
│                       ┌──────────┐                              │
│                       │ 数据清洗  │                              │
│                       └──────────┘                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心接口

### scrape_page() - 智能提取

```python
def scrape_page(
    url: str,
    max_pages: int = 1,
) -> ScrapeResult
```

**使用示例**:
```python
from unified_agent import Brain

brain = Brain()

# 智能提取 - 自动识别列表和字段
result = brain.scrape_page("https://example.com/products")

if result.success:
    for item in result.data:
        print(item)
```

---

### scrape_with_selector() - 自定义选择器

```python
def scrape_with_selector(
    url: str,
    item_selector: str,           # 列表项选择器
    fields: list[dict[str, str]], # 字段配置
    max_pages: int = 1,
) -> ScrapeResult
```

**使用示例**:
```python
result = brain.scrape_with_selector(
    url="https://example.com/products",
    item_selector=".product-card",
    fields=[
        {"name": "title", "selector": ".title", "attr": "text"},
        {"name": "price", "selector": ".price", "attr": "text"},
        {"name": "image", "selector": "img", "attr": "src"},
        {"name": "link", "selector": "a", "attr": "href"},
        {"name": "sku", "selector": "[data-sku]", "attr": "data-sku"},
    ],
    max_pages=5
)
```

---

## 数据结构

### ScrapeResult

```python
@dataclass
class ScrapeResult:
    success: bool              # 是否成功
    data: list[dict]           # 提取的数据列表
    total_items: int           # 总条目数
    pages_scraped: int         # 已抓取页数
    errors: list[str]          # 错误信息

    def to_dataframe(self):
        """转为 pandas DataFrame"""
        import pandas as pd
        return pd.DataFrame(self.data)

    def to_json(self, indent: int = 2) -> str:
        """转为 JSON 字符串"""
        import json
        return json.dumps(self.data, ensure_ascii=False, indent=indent)
```

### 字段配置

```python
FIELD_CONFIG = {
    "name": str,        # 字段名
    "selector": str,    # CSS选择器或XPath
    "attr": str,        # 提取属性: text|html|href|src|data-*|@attr
    "default": Any,     # 默认值 (可选)
    "transform": str,   # 转换函数 (可选): strip|int|float|date
    "regex": str,       # 正则提取 (可选)
}
```

---

## CSS 选择器

### 基础选择器

```css
/* 标签选择器 */
div                 /* 所有 div */
a                   /* 所有链接 */

/* 类选择器 */
.product-card       /* class="product-card" */
.price.sale         /* 同时有两个类 */

/* ID选择器 */
#main-content       /* id="main-content" */

/* 属性选择器 */
[data-id]           /* 有 data-id 属性 */
[data-id="123"]     /* data-id="123" */
[href^="https"]     /* href 以 https 开头 */
[href$=".pdf"]      /* href 以 .pdf 结尾 */
[href*="product"]   /* href 包含 product */
```

### 组合选择器

```css
/* 后代选择器 */
.list .item         /* .list 下的所有 .item */

/* 子选择器 */
.list > .item       /* .list 的直接子元素 .item */

/* 相邻兄弟 */
h2 + p              /* h2 后紧跟的 p */

/* 通用兄弟 */
h2 ~ p              /* h2 之后的所有 p */
```

### 伪类选择器

```css
/* 位置 */
li:first-child      /* 第一个 li */
li:last-child       /* 最后一个 li */
li:nth-child(2)     /* 第2个 li */
li:nth-child(odd)   /* 奇数位置 */
li:nth-child(even)  /* 偶数位置 */
li:nth-child(3n)    /* 每第3个 */

/* 内容 */
:contains("价格")    /* 包含"价格"的元素 */
:empty              /* 空元素 */
:not(.hidden)       /* 不含 .hidden 类 */
```

---

## XPath 选择器

### 基础语法

```xpath
# 标签
//div               # 所有 div
/html/body/div      # 绝对路径

# 属性
//div[@class]       # 有 class 属性的 div
//div[@class="box"] # class="box" 的 div
//a[@href]          # 有 href 的链接

# 文本
//span/text()       # span 的文本内容
//p[text()="hello"] # 文本为 "hello" 的 p
```

### 高级用法

```xpath
# 包含
//div[contains(@class, "item")]     # class 包含 "item"
//p[contains(text(), "价格")]        # 文本包含 "价格"

# 位置
//li[1]                              # 第1个 li
//li[last()]                         # 最后一个 li
//li[position()<=3]                  # 前3个 li

# 逻辑
//div[@class="a" and @id="b"]       # 同时满足
//div[@class="a" or @class="b"]     # 满足其一

# 轴
//div/following-sibling::p           # div 之后的兄弟 p
//div/preceding-sibling::p           # div 之前的兄弟 p
//div/ancestor::section              # div 的祖先 section
//div/descendant::span               # div 的后代 span
```

---

## 属性提取

### attr 参数

| 值 | 说明 | 示例 |
|---|------|------|
| `text` | 文本内容 | `<span>hello</span>` → `"hello"` |
| `html` | 内部HTML | `<div><b>hi</b></div>` → `"<b>hi</b>"` |
| `href` | 链接地址 | `<a href="/page">` → `"/page"` |
| `src` | 资源地址 | `<img src="a.jpg">` → `"a.jpg"` |
| `data-*` | 数据属性 | `<div data-id="1">` → `"1"` |
| `@属性名` | 任意属性 | `<input value="x">` → `"x"` |

### 提取示例

```python
fields = [
    # 文本
    {"name": "title", "selector": "h1.title", "attr": "text"},

    # 链接
    {"name": "url", "selector": "a.link", "attr": "href"},

    # 图片
    {"name": "image", "selector": "img.cover", "attr": "src"},

    # data 属性
    {"name": "product_id", "selector": "[data-product-id]", "attr": "data-product-id"},

    # 任意属性
    {"name": "stock", "selector": "input.stock", "attr": "@value"},
]
```

---

## 数据清洗

### 内置转换函数

```python
TRANSFORMS = {
    "strip": lambda x: x.strip(),
    "int": lambda x: int(re.sub(r'\D', '', x)),
    "float": lambda x: float(re.sub(r'[^\d.]', '', x)),
    "date": lambda x: parse_date(x),
    "lower": lambda x: x.lower(),
    "upper": lambda x: x.upper(),
}
```

### 使用转换

```python
fields = [
    # 去除空白
    {"name": "title", "selector": ".title", "attr": "text", "transform": "strip"},

    # 提取数字
    {"name": "price", "selector": ".price", "attr": "text", "transform": "float"},
    # "¥199.00" → 199.0

    # 提取整数
    {"name": "sales", "selector": ".sales", "attr": "text", "transform": "int"},
    # "销量: 1234" → 1234
]
```

### 正则提取

```python
fields = [
    # 正则匹配
    {
        "name": "price",
        "selector": ".info",
        "attr": "text",
        "regex": r"¥(\d+\.?\d*)"  # 提取价格数字
    },

    # 提取 ID
    {
        "name": "id",
        "selector": "a",
        "attr": "href",
        "regex": r"/item/(\d+)"  # 从链接提取ID
    },
]
```

---

## 智能识别

### 列表容器识别

```python
def detect_list_container(html: str) -> str:
    """自动识别列表容器"""

    # 常见列表模式
    patterns = [
        ".product-list .product-item",
        ".goods-list .goods-item",
        ".list .item",
        "ul.list li",
        "[class*='-list'] [class*='-item']",
    ]

    for pattern in patterns:
        items = doc.css(pattern)
        if len(items) >= 3:  # 至少3个项目
            return pattern

    # 启发式检测: 找到重复最多的元素结构
    return detect_by_structure(html)
```

### 字段自动提取

```python
def auto_detect_fields(item_html: str) -> list[dict]:
    """自动检测字段"""

    fields = []

    # 图片
    if img := item_html.css("img"):
        fields.append({"name": "image", "selector": "img", "attr": "src"})

    # 标题 (通常是最大的文本)
    for sel in ["h1", "h2", "h3", ".title", ".name", "[class*='title']"]:
        if el := item_html.css(sel):
            fields.append({"name": "title", "selector": sel, "attr": "text"})
            break

    # 价格
    for sel in [".price", "[class*='price']", "[class*='cost']"]:
        if el := item_html.css(sel):
            fields.append({"name": "price", "selector": sel, "attr": "text"})
            break

    # 链接
    if a := item_html.css("a"):
        fields.append({"name": "link", "selector": "a", "attr": "href"})

    return fields
```

---

## 分页处理

### 分页模式

```python
PAGINATION_PATTERNS = {
    # 下一页按钮
    "next_button": [
        "a.next",
        ".pagination .next",
        "[class*='next']",
        "a:contains('下一页')",
        "a:contains('>')",
    ],

    # 页码链接
    "page_numbers": [
        ".pagination a",
        ".pager a",
    ],

    # 加载更多
    "load_more": [
        ".load-more",
        "[class*='loadmore']",
        "button:contains('加载更多')",
    ],

    # 无限滚动
    "infinite_scroll": True,
}
```

### 分页实现

```python
async def scrape_with_pagination(page, item_selector, fields, max_pages):
    """带分页的抓取"""
    all_data = []

    for page_num in range(max_pages):
        # 提取当前页数据
        items = await page.query_selector_all(item_selector)
        for item in items:
            data = await extract_item(item, fields)
            all_data.append(data)

        # 查找下一页
        next_btn = await page.query_selector("a.next:not(.disabled)")
        if not next_btn:
            break

        # 点击下一页
        await next_btn.click()
        await page.wait_for_load_state("networkidle")

    return all_data
```

---

## 懒加载处理

### 滚动加载

```python
async def handle_lazy_load(page, scroll_count: int = 5):
    """处理懒加载"""

    for i in range(scroll_count):
        # 滚动到底部
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        # 等待内容加载
        await page.wait_for_timeout(1000)

        # 检查是否有新内容
        new_height = await page.evaluate("document.body.scrollHeight")
        # ...
```

### Intersection Observer

```python
async def wait_for_lazy_images(page):
    """等待懒加载图片"""

    await page.evaluate("""
        () => {
            return new Promise(resolve => {
                const images = document.querySelectorAll('img[data-src]');
                let loaded = 0;

                images.forEach(img => {
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.onload = () => {
                            loaded++;
                            if (loaded === images.length) resolve();
                        };
                    }
                });

                if (images.length === 0) resolve();
            });
        }
    """)
```

---

## JSON 解析

### API 响应解析

```python
def parse_api_response(response: dict, data_path: str) -> list:
    """解析API响应，提取数据列表"""

    # 支持点号路径: "data.list.items"
    parts = data_path.split(".")
    result = response

    for part in parts:
        if isinstance(result, dict):
            result = result.get(part)
        elif isinstance(result, list) and part.isdigit():
            result = result[int(part)]
        else:
            return []

    return result if isinstance(result, list) else [result]

# 使用
response = {"code": 0, "data": {"list": [{"id": 1}, {"id": 2}]}}
items = parse_api_response(response, "data.list")
# [{"id": 1}, {"id": 2}]
```

### JSONPath

```python
from jsonpath_ng import parse

def extract_jsonpath(data: dict, path: str) -> list:
    """使用 JSONPath 提取数据"""
    expr = parse(path)
    return [match.value for match in expr.find(data)]

# 使用
data = {"store": {"books": [{"title": "A"}, {"title": "B"}]}}
titles = extract_jsonpath(data, "$.store.books[*].title")
# ["A", "B"]
```

---

## 常见问题

### 1. 选择器不匹配

```python
# 问题: 动态生成的类名
# 错误: .css-1abc2de
# 正确: [class*="title"], h1, [data-testid="title"]

# 问题: iframe 内容
# 需要先切换到 iframe
frame = page.frame("iframe_name")
await frame.query_selector(".content")
```

### 2. 编码问题

```python
# 处理特殊字符
text = element.text
text = text.encode('utf-8').decode('utf-8')
text = html.unescape(text)  # 处理 HTML 实体
```

### 3. 相对路径转绝对路径

```python
from urllib.parse import urljoin

base_url = "https://example.com/page/"
relative_url = "../images/photo.jpg"
absolute_url = urljoin(base_url, relative_url)
# https://example.com/images/photo.jpg
```

---

## 诊断日志

```
# 列表识别
[PARSE] 页面加载完成: https://example.com/products
[PARSE] 自动识别列表: .product-card (找到 24 个项目)
[PARSE] 字段检测: title, price, image, link

# 数据提取
[PARSE] 提取进度: 24/24 项目
[PARSE] 字段提取: title=OK, price=OK, image=OK
[PARSE] 数据清洗: 去除空白, 价格格式化

# 分页处理
[PARSE] 检测到分页: .pagination .next
[PARSE] 翻页: 2/10
[PARSE] 总计提取: 240 条记录

# 懒加载
[PARSE] 检测到懒加载
[PARSE] 滚动加载: 第 3/5 次
[PARSE] 新内容加载: +12 项目

# JSON 解析
[PARSE] API 响应: 200 OK
[PARSE] 数据路径: data.list (50 条)
[PARSE] 字段映射: id, name, price

# 错误情况
[PARSE] WARN: 选择器 .price 未匹配 (5 项)
[PARSE] WARN: 图片懒加载未完成
[PARSE] ERROR: 选择器无效 - 页面结构可能已变化
[PARSE] ERROR: JSON 解析失败 - 返回了 HTML
```

---

## 相关模块

- **上游**: [04-请求模块](04-request.md) - 获取页面/API响应
- **下游**: [06-存储模块](06-storage.md) - 保存提取的数据
- **配合**: [01-侦查模块](01-reconnaissance.md) - 分析页面结构
