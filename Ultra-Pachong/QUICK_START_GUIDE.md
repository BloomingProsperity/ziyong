# Ultra Pachong 核心模块快速使用指南

本指南展示如何使用新实现的4个核心模块。

---

## 目录

1. [签名模块 - 生成各类加密签名](#1-签名模块)
2. [调度模块 - 批量任务调度](#2-调度模块)
3. [诊断模块 - 错误诊断与修复](#3-诊断模块)
4. [资源评估 - 评估所需资源](#4-资源评估模块)

---

## 1. 签名模块

**文件**: `unified_agent/core/signature.py`

### 基础使用

```python
from unified_agent.core.signature import SignatureManager, SignatureRequest, SignType

# 创建签名管理器
manager = SignatureManager()

# MD5签名
request = SignatureRequest(
    params={"user_id": "123", "action": "login"},
    sign_type=SignType.MD5,
    credentials={"secret": "my_secret_key"}
)
result = manager.generate(request)
print(result.signature)  # 输出MD5签名
print(result.signed_params)  # 包含sign的完整参数
```

### OAuth 1.0签名

```python
request = SignatureRequest(
    params={"status": "Hello World"},
    sign_type=SignType.OAUTH1,
    credentials={
        "consumer_key": "your_consumer_key",
        "consumer_secret": "your_consumer_secret",
        "token": "your_access_token",
        "token_secret": "your_token_secret",
    },
    method="POST",
    url="https://api.twitter.com/1.1/statuses/update.json"
)
result = manager.generate(request)
print(result.headers["Authorization"])  # OAuth签名头
```

### B站WBI签名

```python
request = SignatureRequest(
    params={"mid": "123456", "pn": "1", "ps": "20"},
    sign_type=SignType.BILIBILI_WBI,
    credentials={
        "img_key": "your_img_key",  # 从B站API获取
        "sub_key": "your_sub_key",
    }
)
result = manager.generate(request)
print(result.signed_params)  # 包含w_rid和wts的完整参数
```

### 自动检测签名类型

```python
# 不指定sign_type，让系统自动检测
request = SignatureRequest(
    params={"w_rid": "", "wts": "1234567890"},
    sign_type=SignType.AUTO,  # 自动检测
)
result = manager.generate(request)
# 系统会自动识别为bilibili_wbi类型
```

### 验证签名

```python
# 验证签名是否正确
is_valid = manager.verify_signature(
    params={"user_id": "123"},
    signature="abc123...",
    sign_type=SignType.MD5,
    credentials={"secret": "my_secret_key"}
)
print(f"Signature valid: {is_valid}")
```

### 注册自定义签名算法

```python
from unified_agent.core.signature import SignatureGenerator

class CustomGenerator(SignatureGenerator):
    def generate(self, request):
        # 你的签名逻辑
        signature = "custom_sign_" + str(hash(str(request.params)))
        return self._create_success(signature=signature)

# 注册
manager.register(SignType.CUSTOM, CustomGenerator())
```

---

## 2. 调度模块

**文件**: `unified_agent/core/scheduling.py`

### 基础批量调度

```python
import asyncio
from unified_agent.core.scheduling import create_scheduler, Task

async def fetch_page(url: str) -> dict:
    """你的抓取函数"""
    # 模拟网络请求
    await asyncio.sleep(0.5)
    return {"url": url, "title": "页面标题"}

async def main():
    # 创建调度器
    scheduler = create_scheduler(
        concurrency=10,       # 最大并发10个任务
        rate_limit=5.0,       # 每秒最多5个请求
        max_retries=3,        # 失败最多重试3次
    )

    # 创建任务列表
    tasks = [
        Task(
            id=f"task_{i}",
            func=fetch_page,
            args=(f"https://example.com/page/{i}",),
        )
        for i in range(100)
    ]

    # 执行调度
    result = await scheduler.schedule(tasks)

    # 查看结果
    print(result.summary())
    # 输出: [Schedule Result] Total: 100 | Success: 98 (98.0%) | Failed: 2 | Duration: 45.2s

    # 访问结果数据
    for task_result in result.results:
        if task_result.status == "success":
            print(f"Task {task_result.task_id}: {task_result.result}")

asyncio.run(main())
```

### 带进度回调

```python
def progress_callback(completed, total):
    """进度回调函数"""
    percent = completed / total * 100
    print(f"\r进度: {completed}/{total} ({percent:.1f}%)", end="")

result = await scheduler.schedule(tasks, progress_callback=progress_callback)
```

### 优先级任务

```python
from unified_agent.core.scheduling import TaskPriority, ScheduleConfig

# 创建带优先级的任务
tasks = [
    Task(
        id="important_task",
        func=fetch_page,
        args=("https://important.com",),
        priority=TaskPriority.CRITICAL,  # 最高优先级
    ),
    Task(
        id="normal_task",
        func=fetch_page,
        args=("https://normal.com",),
        priority=TaskPriority.NORMAL,
    ),
]

# 使用优先级队列
config = ScheduleConfig(
    concurrency=5,
    queue_type="priority",  # 优先级队列
)
scheduler = BatchScheduler(config)
```

### 延迟任务

```python
# 创建延迟执行的任务
task = Task(
    id="delayed_task",
    func=fetch_page,
    args=("https://example.com",),
    delay=10.0,  # 延迟10秒执行
)
```

### 任务超时控制

```python
task = Task(
    id="timeout_task",
    func=slow_function,
    timeout=30.0,  # 30秒超时
)
```

---

## 3. 诊断模块

**文件**: `unified_agent/core/diagnosis.py`

### 基础诊断

```python
from unified_agent.core.diagnosis import create_diagnoser

# 创建诊断器
diagnoser = create_diagnoser()

# 捕获并诊断错误
try:
    response = requests.get("https://api.example.com")
    response.raise_for_status()
except Exception as e:
    # 诊断错误
    result = diagnoser.diagnose(e, context={
        "url": "https://api.example.com",
        "request_count": 10,
        "error_count": 3,
    })

    # 打印诊断报告
    print(result.to_report())

    # 输出:
    # # 🔴 错误诊断报告
    # ## 错误概述
    # - **类型**: 403_forbidden
    # - **严重程度**: 🔴 HIGH
    # ## 根本原因
    # IP被封禁 (置信度: 90%)
    # ## 解决方案
    # ### ✅ 推荐: 启用代理服务
    # ...
```

### 检查是否可自动修复

```python
if result.auto_fixable:
    print("✅ 此错误可以自动修复")
else:
    print("⚠️ 此错误需要人工处理")
```

### 使用自动修复器

```python
from unified_agent.core.diagnosis import create_auto_fixer

auto_fixer = create_auto_fixer()

if result.auto_fixable:
    success = auto_fixer.fix(result, context={
        "config": my_config,  # 你的配置对象
    })

    if success:
        print("✅ 自动修复成功，可以重试")
    else:
        print("❌ 自动修复失败，需要手动处理")
```

### 快速处理常见错误

```python
from unified_agent.core.diagnosis import handle_403, handle_timeout, handle_signature_error

# 处理403错误
result = handle_403(context={"url": "https://example.com"})
print(result.to_report())

# 处理超时错误
result = handle_timeout(context={"url": "https://slow-site.com"})
print(result.to_report())

# 处理签名错误
result = handle_signature_error(context={"sign_type": "md5"})
print(result.to_report())
```

### 导出诊断结果为JSON

```python
import json

# 导出为字典
diagnosis_dict = result.to_dict()

# 保存为JSON
with open("diagnosis_report.json", "w", encoding="utf-8") as f:
    json.dump(diagnosis_dict, f, indent=2, ensure_ascii=False)
```

### 注册自定义修复器

```python
from unified_agent.core.diagnosis import AutoFixer

auto_fixer = AutoFixer()

def my_custom_fixer(context):
    """自定义修复器"""
    # 你的修复逻辑
    print("Executing custom fix...")
    return True

# 注册
auto_fixer.register_fixer("my_custom_action", my_custom_fixer)
```

---

## 4. 资源评估模块

**文件**: `unified_agent/core/assessment.py`

### 基础资源评估

```python
from unified_agent.core.assessment import create_assessment

# 创建评估器
assessment = create_assessment()

# 评估资源需求
plan = assessment.assess(
    url="https://jd.com",
    target_count=5000,  # 目标抓取5000条数据
    analysis={
        "anti_scrape_level": "high",  # 反爬等级
        "requires_login": True,
        "has_signature": True,
        "detection_risks": ["ip_blocking", "rate_limiting"],
    }
)

# 打印评估报告
print(plan.to_report())

# 输出:
# # 资源需求评估报告
# ## 难度评估
# - **风险等级**: 🔴 HIGH
# - **预估时间**: 1-2小时
# - **预估成本**: 约￥100-500/月
# ## 代理需求
# **是否需要**: ✅ 需要
# ...
```

### 检查是否需要代理

```python
if plan.needs_proxy:
    print(f"需要代理: {plan.proxy_advice.reason}")
    print(f"代理类型: {plan.proxy_advice.proxy_type.value}")
    print(f"预估成本: {plan.proxy_advice.estimated_cost}")
```

### 检查是否需要登录

```python
if plan.needs_login:
    print(f"需要登录: {plan.account_advice.reason}")
    print(f"最少账号数: {plan.account_advice.min_accounts}")
    print(f"推荐账号数: {plan.account_advice.recommended_accounts}")
```

### 生成配置代码

```python
# 获取推荐配置
config = plan.recommended_config
print(f"推荐请求频率: {config['requests_per_second']}/秒")
print(f"推荐并发数: {config['concurrency']}")
print(f"推荐超时: {config['timeout']}秒")

# 或者直接生成配置代码
from unified_agent.core.assessment import generate_config_code
code = generate_config_code(plan)
print(code)

# 输出:
# from unified_agent import Brain, AgentConfig
#
# config = AgentConfig(
#     proxy_enabled=True,
#     proxy_url="http://your-proxy.com:8080",
#     requests_per_second=1.0,
#     concurrency=3,
#     timeout=60,
# )
# brain = Brain(config)
```

### 不同场景的评估

#### 场景1: 低反爬 + 小规模
```python
plan = assessment.assess(
    url="https://simple-site.com",
    target_count=100,
    analysis={"anti_scrape_level": "low"}
)
# 结果: 不需要代理，不需要登录，免费
```

#### 场景2: 中等反爬 + 中规模
```python
plan = assessment.assess(
    url="https://medium-site.com",
    target_count=1000,
    analysis={"anti_scrape_level": "medium", "requires_login": True}
)
# 结果: 建议使用代理，需要1个账号，约￥50-100/月
```

#### 场景3: 极高反爬 + 大规模
```python
plan = assessment.assess(
    url="https://taobao.com",
    target_count=10000,
    analysis={
        "anti_scrape_level": "extreme",
        "requires_login": True,
        "has_signature": True,
        "detection_risks": ["ip_blocking", "fingerprinting", "behavior_analysis"],
    }
)
# 结果: 必须使用住宅代理，需要5+个账号，需要签名服务，约￥500-2000/月
```

---

## 综合使用示例

将所有模块组合使用的完整示例：

```python
import asyncio
from unified_agent.core.signature import SignatureManager, SignatureRequest, SignType
from unified_agent.core.scheduling import create_scheduler, Task
from unified_agent.core.diagnosis import create_diagnoser
from unified_agent.core.assessment import create_assessment

async def scrape_jd_products():
    """抓取京东商品示例"""

    # 1. 资源评估
    print("=== 步骤1: 评估资源需求 ===")
    assessment = create_assessment()
    plan = assessment.assess(
        url="https://api.m.jd.com/client.action",
        target_count=1000,
        analysis={
            "anti_scrape_level": "extreme",
            "requires_login": False,
            "has_signature": True,
            "detection_risks": ["ip_blocking", "signature_check"],
        }
    )
    print(plan.to_report())

    # 2. 创建签名管理器
    print("\n=== 步骤2: 准备签名生成器 ===")
    signature_manager = SignatureManager()

    # 3. 创建诊断器
    diagnoser = create_diagnoser()

    # 4. 定义抓取函数
    async def fetch_product(product_id: str) -> dict:
        try:
            # 生成签名
            sign_request = SignatureRequest(
                params={"functionId": "getProductDetail", "productId": product_id},
                sign_type=SignType.MD5,
                credentials={"secret": "jd_secret_key"}
            )
            sign_result = signature_manager.generate(sign_request)

            if sign_result.status != "success":
                raise Exception(f"签名生成失败: {sign_result.errors}")

            # 模拟HTTP请求（实际应使用httpx或requests）
            await asyncio.sleep(0.5)

            return {
                "product_id": product_id,
                "name": f"商品{product_id}",
                "price": 99.99,
            }

        except Exception as e:
            # 诊断错误
            diagnosis = diagnoser.diagnose(e, context={
                "url": "https://api.m.jd.com/client.action",
                "product_id": product_id,
            })
            print(f"\n错误诊断:\n{diagnosis.to_report()}")
            raise

    # 5. 批量调度
    print("\n=== 步骤3: 开始批量抓取 ===")
    scheduler = create_scheduler(
        concurrency=plan.recommended_config["concurrency"],
        rate_limit=plan.recommended_config["requests_per_second"],
        max_retries=3,
    )

    tasks = [
        Task(
            id=f"product_{i}",
            func=fetch_product,
            args=(str(100000 + i),),
        )
        for i in range(20)  # 示例：抓取20个商品
    ]

    def progress(completed, total):
        print(f"\r进度: {completed}/{total}", end="")

    result = await scheduler.schedule(tasks, progress_callback=progress)

    # 6. 输出结果
    print(f"\n\n=== 步骤4: 抓取完成 ===")
    print(result.summary())
    print(f"\n成功获取 {result.success} 个商品数据")

    return result

# 运行
if __name__ == "__main__":
    asyncio.run(scrape_jd_products())
```

---

## 配置建议

### 1. 日志配置

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
```

### 2. 性能配置

根据资源评估结果调整：

- **低反爬**: `concurrency=10, rate_limit=5.0`
- **中反爬**: `concurrency=5, rate_limit=2.0`
- **高反爬**: `concurrency=3, rate_limit=1.0`
- **极高反爬**: `concurrency=1, rate_limit=0.3`

### 3. 缓存配置

```python
from unified_agent.core.signature import SignatureManager

# 自定义缓存配置
manager = SignatureManager(enable_cache=True)
manager.cache.max_size = 20000  # 增加缓存大小
manager.cache.default_ttl = 600  # 延长TTL到10分钟
```

---

## 常见问题

### Q1: 如何处理需要复杂JS签名的网站？

```python
# 使用CustomJSGenerator
request = SignatureRequest(
    params={"data": "test"},
    sign_type=SignType.CUSTOM,
    algorithm_impl="""
        function sign(params) {
            // 你的JS签名代码
            return "signed_value";
        }
    """
)
result = manager.generate(request)
```

### Q2: 如何处理429错误（限流）？

```python
# 诊断会自动给出解决方案
try:
    response = requests.get(url)
except Exception as e:
    diagnosis = diagnoser.diagnose(e)
    if diagnosis.error_type == "429_rate_limit":
        # 推荐方案：降低请求频率
        print(diagnosis.recommended_solution.description)
```

### Q3: 如何保存和恢复任务进度？

```python
# 保存任务结果
import json
with open("progress.json", "w") as f:
    json.dump([r.to_dict() for r in result.results], f)

# 恢复时跳过已完成的任务
completed_ids = load_completed_task_ids()
tasks = [t for t in tasks if t.id not in completed_ids]
```

---

## 下一步

1. 阅读 [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) 了解技术细节
2. 查看各模块的完整文档：
   - `unified_agent/skills/03-signature.md`
   - `unified_agent/skills/07-scheduling.md`
   - `unified_agent/skills/08-diagnosis.md`
   - `unified_agent/skills/00-quick-start.md`
3. 运行模块内置的示例代码测试功能
4. 根据你的需求定制和扩展

---

**Happy Scraping! 🚀**
