# 06 - 存储模块 (Storage)

---
name: storage
version: 1.0.0
description: 数据持久化、会话管理与导出
triggers:
  - "保存"
  - "导出"
  - "存储"
  - "export"
  - "save"
dependencies:
  - pandas
  - openpyxl
---

## 模块目标

**核心原则：给出需求，必须完成。**

| 目标 | 达成标准 |
|------|---------|
| **数据零丢失** | 爬取数据 100% 持久化，中断可恢复 |
| **格式全支持** | JSON/CSV/Excel 一键导出 |
| **会话可复用** | Cookie/Session 持久化，下次运行自动加载 |
| **增量可追加** | 支持去重更新，避免重复数据 |

## 模块概述

存储模块负责数据持久化，包括结果导出、会话管理、增量存储等功能。

```
┌─────────────────────────────────────────────────────────────────┐
│                        存储模块架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                      数据输入                            │  │
│   │  抓取数据 | API响应 | 会话状态 | 报告 | Cookie          │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│        ┌─────────┐     ┌─────────┐     ┌─────────┐             │
│        │文件存储  │     │会话存储  │     │缓存存储  │             │
│        └─────────┘     └─────────┘     └─────────┘             │
│              │               │               │                  │
│        ┌─────┴─────┐   ┌─────┴─────┐        │                  │
│        ▼     ▼     ▼   ▼     ▼     ▼        ▼                  │
│       JSON  CSV  Excel Session Cookie    Memory                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 数据导出

### export_data() - 导出数据

```python
def export_data(
    data: list[dict],
    filename: str,
    format: Literal["json", "csv"] = "json"
) -> Path
```

**使用示例**:
```python
from unified_agent import Brain

brain = Brain()

# 抓取数据
result = brain.scrape_page("https://example.com/products")

# 导出 JSON
path = brain.export_data(result.data, "products", format="json")
print(f"保存到: {path}")

# 导出 CSV
path = brain.export_data(result.data, "products", format="csv")
```

---

### JSON 导出

```python
import json
from pathlib import Path

def export_json(data: list[dict], filepath: Path) -> Path:
    """导出为 JSON 文件"""

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return filepath

# 使用
export_json(data, Path("output/products.json"))
```

**输出格式**:
```json
[
  {
    "title": "商品A",
    "price": 199.0,
    "url": "https://example.com/product/1"
  },
  {
    "title": "商品B",
    "price": 299.0,
    "url": "https://example.com/product/2"
  }
]
```

---

### CSV 导出

```python
import csv
from pathlib import Path

def export_csv(data: list[dict], filepath: Path) -> Path:
    """导出为 CSV 文件"""

    if not data:
        return filepath

    fieldnames = data[0].keys()

    with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    return filepath
```

**注意**: 使用 `utf-8-sig` 编码确保 Excel 正确显示中文

---

### Excel 导出

```python
import pandas as pd
from pathlib import Path

def export_excel(data: list[dict], filepath: Path) -> Path:
    """导出为 Excel 文件"""

    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False, engine='openpyxl')

    return filepath

# 多 Sheet 导出
def export_excel_multi_sheet(data_dict: dict[str, list], filepath: Path) -> Path:
    """多 Sheet 导出"""

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        for sheet_name, data in data_dict.items():
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    return filepath

# 使用
export_excel_multi_sheet({
    "商品列表": products,
    "评论数据": comments,
    "销售统计": stats,
}, Path("output/report.xlsx"))
```

---

## 会话管理

### save_session() - 保存会话

```python
def save_session(name: str) -> Path:
    """保存当前会话状态"""
```

**使用示例**:
```python
# 登录后保存会话
brain.set_cookies({"token": "xxx", "user_id": "123"})
brain.scraper.save_session("my_login_session")

# 下次使用时加载
brain.scraper.load_session("my_login_session")
```

### 会话数据结构

```python
@dataclass
class SessionData:
    """会话数据"""

    # 基础信息
    name: str
    created_at: datetime
    updated_at: datetime

    # 认证数据
    cookies: dict[str, str]
    headers: dict[str, str]

    # 登录状态
    is_logged_in: bool
    user_info: dict | None

    # 浏览器状态
    local_storage: dict[str, str]
    session_storage: dict[str, str]
```

### 会话文件格式

```json
{
  "name": "jd_session",
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:30:00",
  "cookies": {
    "pt_key": "xxx",
    "pt_pin": "xxx"
  },
  "headers": {
    "User-Agent": "..."
  },
  "is_logged_in": true,
  "user_info": {
    "username": "user123"
  }
}
```

---

## 报告保存

### save_report() - 保存侦查报告

```python
def save_report(report: SiteReport, filename: str | None = None) -> Path:
    """保存侦查报告"""
```

**使用示例**:
```python
report = brain.investigate("https://jd.com")

# 自动生成文件名
path = brain.save_report(report)
# output: data/report_20240101_120000.json

# 指定文件名
path = brain.save_report(report, "jd_analysis")
# output: data/jd_analysis.json + data/jd_analysis_screenshot.png
```

### 报告包含内容

```
report_xxx/
├── report.json           # 完整报告数据
├── screenshot.png        # 页面截图
├── requests.json         # 捕获的API请求
├── cookies.json          # Cookie数据
└── analysis.md           # AI分析报告
```

---

## 增量存储

### 增量追加

```python
def append_data(data: list[dict], filepath: Path) -> int:
    """增量追加数据"""

    # 读取现有数据
    existing = []
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            existing = json.load(f)

    # 追加新数据
    existing.extend(data)

    # 保存
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    return len(data)

# 使用
for page in range(1, 11):
    result = brain.call_api(f"https://api.example.com/list?page={page}")
    append_data(result.body['data'], Path("output/all_data.json"))
```

### 去重存储

```python
def upsert_data(
    data: list[dict],
    filepath: Path,
    key_field: str = "id"
) -> dict:
    """去重更新存储"""

    # 读取现有数据
    existing = {}
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            for item in json.load(f):
                existing[item[key_field]] = item

    # 更新/新增
    new_count = 0
    update_count = 0
    for item in data:
        key = item[key_field]
        if key in existing:
            existing[key] = item
            update_count += 1
        else:
            existing[key] = item
            new_count += 1

    # 保存
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(list(existing.values()), f, ensure_ascii=False, indent=2)

    return {"new": new_count, "updated": update_count}

# 使用
result = upsert_data(products, Path("output/products.json"), key_field="product_id")
print(f"新增: {result['new']}, 更新: {result['updated']}")
```

---

## 断点续爬

### 进度保存

```python
@dataclass
class CrawlProgress:
    """爬取进度"""

    task_id: str
    total_pages: int
    current_page: int
    completed_urls: list[str]
    failed_urls: list[str]
    last_update: datetime

    def save(self, filepath: Path):
        """保存进度"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, default=str, indent=2)

    @classmethod
    def load(cls, filepath: Path) -> "CrawlProgress":
        """加载进度"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            data['last_update'] = datetime.fromisoformat(data['last_update'])
            return cls(**data)
```

### 使用断点续爬

```python
progress_file = Path("output/progress.json")

# 加载或创建进度
if progress_file.exists():
    progress = CrawlProgress.load(progress_file)
    print(f"从第 {progress.current_page} 页继续")
else:
    progress = CrawlProgress(
        task_id="task_001",
        total_pages=100,
        current_page=1,
        completed_urls=[],
        failed_urls=[],
        last_update=datetime.now()
    )

# 爬取
for page in range(progress.current_page, progress.total_pages + 1):
    try:
        url = f"https://api.example.com/list?page={page}"
        result = brain.call_api(url)

        if result.success:
            progress.completed_urls.append(url)
        else:
            progress.failed_urls.append(url)

        progress.current_page = page + 1
        progress.last_update = datetime.now()
        progress.save(progress_file)  # 每页保存进度

    except KeyboardInterrupt:
        print("中断，进度已保存")
        break
```

---

## Cookie 持久化

### 保存 Cookie

```python
def save_cookies(cookies: dict, filepath: Path):
    """保存 Cookie 到文件"""

    cookie_data = {
        "cookies": cookies,
        "saved_at": datetime.now().isoformat(),
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(cookie_data, f, indent=2)

# 使用
cookies = brain.get_collected_cookies()
save_cookies(cookies, Path("sessions/jd_cookies.json"))
```

### 加载 Cookie

```python
def load_cookies(filepath: Path) -> dict:
    """从文件加载 Cookie"""

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get("cookies", {})

# 使用
cookies = load_cookies(Path("sessions/jd_cookies.json"))
brain.set_cookies(cookies)
```

---

## 存储配置

### AgentConfig 存储相关

```python
@dataclass
class AgentConfig:
    # 存储目录
    data_dir: Path = Path("./data")
    session_dir: Path = Path("./sessions")

    # 文件命名
    timestamp_format: str = "%Y%m%d_%H%M%S"

    # 自动创建目录
    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session_dir.mkdir(parents=True, exist_ok=True)
```

### 目录结构

```
project/
├── data/                    # 数据目录
│   ├── products.json
│   ├── products.csv
│   ├── report_20240101_120000.json
│   └── report_20240101_120000_screenshot.png
│
├── sessions/                # 会话目录
│   ├── jd_session.json
│   ├── taobao_session.json
│   └── cookies/
│       ├── jd_cookies.json
│       └── taobao_cookies.json
│
└── cache/                   # 缓存目录
    ├── pages/
    └── responses/
```

---

## 数据压缩

### 压缩存储

```python
import gzip
import json

def save_compressed(data: list[dict], filepath: Path):
    """压缩保存"""

    json_str = json.dumps(data, ensure_ascii=False)

    with gzip.open(filepath.with_suffix('.json.gz'), 'wt', encoding='utf-8') as f:
        f.write(json_str)

def load_compressed(filepath: Path) -> list[dict]:
    """加载压缩文件"""

    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        return json.load(f)
```

---

## 诊断日志

```
# 数据导出
[STORAGE] 导出: products.json (1500 条记录, 2.3MB)
[STORAGE] 导出: products.csv (1500 行, 1.8MB)
[STORAGE] 导出: report.xlsx (3 sheets)

# 会话管理
[SESSION] 保存会话: jd_session
[SESSION] 包含: cookies=5, headers=8, localStorage=3
[SESSION] 加载会话: jd_session (创建于 2h 前)
[SESSION] 会话有效: is_logged_in=true

# 增量存储
[STORAGE] 增量追加: +50 条 (总计: 1550)
[STORAGE] 去重更新: 新增=30, 更新=20, 跳过=0

# 断点续爬
[PROGRESS] 保存进度: page=50/100, completed=49, failed=1
[PROGRESS] 加载进度: 从第 50 页继续
[PROGRESS] 任务完成: 100/100 页

# Cookie 管理
[COOKIE] 保存: sessions/jd_cookies.json
[COOKIE] 加载: 5 个 Cookie
[COOKIE] 警告: Cookie 保存时间 > 24h，可能需要刷新

# 错误情况
[STORAGE] ERROR: 磁盘空间不足
[STORAGE] ERROR: 文件写入失败 (权限)
[SESSION] WARN: 会话过期，需要重新登录
```

---

## 相关模块

- **上游**: [05-解析模块](05-parsing.md) - 提取的数据
- **配合**: [01-侦查模块](01-reconnaissance.md) - 保存报告
- **配合**: [04-请求模块](04-request.md) - 会话管理
