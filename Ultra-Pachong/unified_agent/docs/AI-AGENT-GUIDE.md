# AI Agent 决策指南 - Skills串联使用手册

> **目标读者**: AI Agent (Claude等大语言模型)
> **用途**: 理解如何串联使用27个Skills模块，实现智能爬虫任务

---

## 📋 快速导航

- [核心决策逻辑](#核心决策逻辑)
- [任务类型识别](#任务类型识别)
- [Skills串联模式](#skills串联模式)
- [决策树](#决策树)
- [实战案例](#实战案例)

---

## 🎯 核心决策逻辑

### 你的角色定位

作为AI Agent，你是**18-brain-controller**（决策总控）：
- **输入**: 用户的自然语言任务描述
- **职责**: 理解任务 → 选择Skills → 编排执行 → 处理结果
- **输出**: 结构化数据或分析报告

### 三步决策框架

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI Agent 决策框架                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: 任务理解 (UNDERSTAND)                                   │
│  ├─ 提取关键信息: URL、目标数据、数量、时间要求                   │
│  ├─ 识别任务类型: EXPLICIT/FUZZY/TROUBLESHOOT/QUERY              │
│  └─ 判断信息完整性: 缺失则询问用户                               │
│                                                                 │
│  Step 2: 模块选择 (SELECT)                                       │
│  ├─ 匹配触发条件: 根据task_type和site_features                   │
│  ├─ 检查依赖关系: 确保required依赖满足                           │
│  └─ 生成执行计划: [skill_1, skill_2, ...]                       │
│                                                                 │
│  Step 3: 流程执行 (EXECUTE)                                      │
│  ├─ 顺序调用Skills                                              │
│  ├─ 监控执行状态                                                │
│  ├─ 错误自动恢复: 调用19-fault-decision-tree                     │
│  └─ 返回结果或报告                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 任务类型识别

### TYPE_EXPLICIT (明确任务) - 80%的场景

**触发特征:**
- ✅ 有明确的URL
- ✅ 有明确的目标数据
- ✅ 信息完整，可直接执行

**用户输入示例:**
```
"爬取豆瓣电影Top250的标题、评分、导演"
"获取https://example.com/api/products的前100条数据"
"抓取京东手机分类下的商品信息"
```

**处理流程:**
```
EXPLICIT → 01-reconnaissance (侦查)
         → 判断anti_level
         → 选择执行路径 (见下方决策树)
         → 返回数据
```

---

### TYPE_FUZZY (模糊任务) - 15%的场景

**触发特征:**
- ✅ 有URL，但目标数据不明确
- ⚠️ 需要探索和分析

**用户输入示例:**
```
"分析一下https://example.com这个网站"
"看看这个网站有什么数据可以爬"
"监控这个网站的价格变化"
```

**处理流程:**
```
FUZZY → 01-reconnaissance (深度侦查)
      → 16-tactics (战术决策，入口发现)
      → 询问用户确认目标
      → 转为EXPLICIT继续执行
```

---

### TYPE_TROUBLESHOOT (故障诊断) - 4%的场景

**触发特征:**
- 🔴 包含错误码 (403/验证码/签名失败)
- 🔴 执行失败需要诊断

**用户输入示例:**
```
"请求返回403怎么办"
"遇到验证码了"
"签名参数一直错误"
```

**处理流程:**
```
TROUBLESHOOT → 19-fault-decision-tree (故障决策树)
             → 自动诊断 (网络/HTTP/反爬/数据层)
             → 应用恢复策略
             → 重试或报告
```

---

### TYPE_QUERY (信息查询) - 1%的场景

**触发特征:**
- ❓ 无action动词
- ❓ 询问知识或方法

**用户输入示例:**
```
"京东的反爬机制是什么"
"h5st签名怎么破解"
"什么时候需要代理"
```

**处理流程:**
```
QUERY → 22-knowledge-format (查询知识库)
      → 返回知识条目
      → (可选) 20-e2e-cases (提供案例)
```

---

## 🔗 Skills串联模式

### 模式1: 简单流程 (LOW反爬)

**适用场景**: 静态页面、公开API、无加密

```
01-reconnaissance (侦查)
    ↓
判断: anti_level = LOW
    ↓
04-request (直接请求)
    ↓
05-parsing (数据解析)
    ↓
06-storage (存储导出)
```

**代码示例:**
```python
# Step 1: 侦查
analysis = brain.smart_investigate(url)

# Step 2: 判断
if analysis.anti_scrape_level == "low":
    # Step 3: 直接请求
    result = brain.call_api(analysis.main_data_api["url"])

    # Step 4: 解析 (如果返回HTML)
    if "html" in result.headers.get("content-type"):
        data = brain.scrape_page(url)
    else:
        data = result.body

    # Step 5: 存储
    brain.export_data(data, "output")
```

---

### 模式2: 中等流程 (MEDIUM反爬)

**适用场景**: Cookie验证、简单签名、限流

```
01-reconnaissance (侦查)
    ↓
判断: anti_level = MEDIUM
    ↓
02-anti-detection (伪装)
    ↓
24-credential-pool (可选，如需登录)
    ↓
04-request (请求)
    ↓
05-parsing (解析)
    ↓
06-storage (存储)
```

**代码示例:**
```python
# Step 1: 侦查
analysis = brain.smart_investigate(url)

# Step 2: 判断
if analysis.anti_scrape_level == "medium":
    # Step 3: 配置反检测
    config = AgentConfig(
        stealth_mode=True,
        use_random_ua=True
    )

    # Step 4: 如需登录
    if analysis.login_required:
        brain.use_pool_cookie(url)

    # Step 5: 请求
    result = brain.call_api(url, use_collected_cookies=True)

    # Step 6-7: 解析和存储
    brain.export_data(result.body, "output")
```

---

### 模式3: 复杂流程 (HIGH反爬)

**适用场景**: 复杂签名、验证码、强反爬

```
01-reconnaissance (侦查)
    ↓
判断: anti_level = HIGH
    ↓
16-tactics (战术决策，选择最优入口)
    ↓
├─ 路径A: 有签名 ────────────────────┐
│  03-signature (签名分析)            │
│      ↓                             │
│  09-js-reverse (JS逆向，如复杂)     │
│      ↓                             │
│  RPC签名服务 或 补环境               │
│                                    │
├─ 路径B: 有验证码 ───────────────────┤
│  10-captcha (验证码识别)            │
│                                    │
├─ 路径C: 需指纹伪装 ─────────────────┤
│  11-fingerprint (指纹生成)         │
│                                    │
└────────────────┬───────────────────┘
                 ↓
        02-anti-detection (反检测)
                 ↓
        04-request (请求)
                 ↓
        05-parsing (解析)
                 ↓
        06-storage (存储)
```

**代码示例:**
```python
# Step 1: 侦查
analysis = brain.smart_investigate(url)

# Step 2: 判断
if analysis.anti_scrape_level == "high":
    # Step 3: 战术决策
    # (16-tactics 自动选择最优路径)

    # Step 4: 签名处理
    if analysis.signature_params:
        # 使用RPC或补环境方案
        # (参考03-signature.md示例)
        pass

    # Step 5: 验证码处理
    if "captcha" in analysis.anti_scrape_features:
        # (参考10-captcha.md)
        pass

    # Step 6: 指纹伪装
    config = AgentConfig(
        use_fingerprint=True,
        stealth_mode=True
    )

    # Step 7-10: 请求、解析、存储
    # ...
```

---

### 模式4: 极限流程 (EXTREME反爬)

**适用场景**: 京东h5st、淘宝mtop、Cloudflare

```
01-reconnaissance (侦查)
    ↓
判断: anti_level = EXTREME
    ↓
决策: 是否有预设配置?
    ├─ YES → 使用预设 (presets.py)
    └─ NO  → 继续分析
        ↓
16-tactics (战术决策)
    ↓
09-js-reverse (深度逆向)
    ↓
03-signature (RPC方案)
    ↓
11-fingerprint (完整指纹)
    ↓
02-anti-detection (TLS指纹)
    ↓
24-credential-pool (账号池)
    ↓
07-scheduling (限流控制)
    ↓
04-request (请求)
    ↓
17-feedback-loop (效果验证)
    ↓
05-parsing (解析)
    ↓
06-storage (存储)
```

**代码示例:**
```python
# Step 1: 侦查
analysis = brain.smart_investigate(url)

# Step 2: 判断
if analysis.anti_scrape_level == "extreme":
    # Step 3: 检查预设
    if analysis.matched_preset:
        preset = brain.get_preset(url)
        # 使用预设配置

    # Step 4: 如果是need_reverse
    if analysis.recommended_approach == "need_reverse":
        print("需要深度逆向，建议:")
        for step in analysis.next_steps:
            print(f"  - {step}")

        # 使用RPC方案或真实浏览器
        # (参考09-js-reverse.md的RPC示例)
```

---

## 🌳 决策树

### 反爬等级决策树

```
用户任务
    ↓
调用: brain.smart_investigate(url)
    ↓
获得: analysis.anti_scrape_level
    ↓
    ├─ LOW ──────→ 模式1 (简单流程)
    │              Skills: 01 → 04 → 05 → 06
    │
    ├─ MEDIUM ───→ 模式2 (中等流程)
    │              Skills: 01 → 02 → 04 → 05 → 06
    │
    ├─ HIGH ─────→ 模式3 (复杂流程)
    │              Skills: 01 → 16 → (03+09) → 02 → 04 → 05 → 06
    │
    └─ EXTREME ──→ 模式4 (极限流程)
                   Skills: 01 → 16 → 09 → 03 → 11 → 02 → 24 → 07 → 04 → 17 → 05 → 06
```

### 错误处理决策树

```
执行失败
    ↓
触发: 19-fault-decision-tree
    ↓
    ├─ 网络层错误 (TIMEOUT/DNS/SSL)
    │      ↓
    │  自动重试 3次
    │      ↓
    │  仍失败 → 切换代理 → 重试
    │      ↓
    │  仍失败 → 报告用户
    │
    ├─ HTTP层错误 (403/404/429/5xx)
    │      ↓
    │  403 → 诊断TLS指纹/Cookie/IP
    │      ↓
    │  应用修复 (02-anti-detection)
    │      ↓
    │  重试 → 成功/失败
    │
    ├─ 反爬层错误 (CAPTCHA/IP_BANNED/SIGNATURE_INVALID)
    │      ↓
    │  CAPTCHA → 10-captcha
    │  IP_BANNED → 切换代理 + 降低频率
    │  SIGNATURE_INVALID → 03-signature + 09-js-reverse
    │
    └─ 数据层错误 (SELECTOR_FAILED/EMPTY_DATA/SCHEMA_MISMATCH)
           ↓
       更新选择器 / 标记partial / 报告
```

---

## 💡 实战案例

### 案例1: 简单任务（豆瓣电影）

**用户输入:**
```
"爬取豆瓣电影Top250的标题、评分、导演"
```

**AI Agent决策流程:**

```python
# 1. 任务理解
task_type = "EXPLICIT"  # 有URL、有目标
url = "https://movie.douban.com/top250"
target_fields = ["title", "rating", "director"]

# 2. 侦查
analysis = brain.smart_investigate(url)
# 结果: anti_level = "LOW", recommended_approach = "browser_scrape"

# 3. 选择Skills
skills_chain = [
    "01-reconnaissance",  # 已完成
    "04-request",         # 直接请求HTML
    "05-parsing",         # 解析DOM
    "06-storage"          # 存储
]

# 4. 执行
result = brain.scrape_with_selector(
    url=url,
    item_selector=".item",
    fields=[
        {"name": "title", "selector": ".title", "attr": "text"},
        {"name": "rating", "selector": ".rating_num", "attr": "text"},
        {"name": "director", "selector": ".bd p", "attr": "text"}
    ],
    max_pages=10  # Top250需要翻页
)

# 5. 导出
brain.export_data(result.data, "douban_top250", format="csv")
```

---

### 案例2: 复杂任务（B站UP主视频）

**用户输入:**
```
"获取B站UP主 uid=123456 的所有视频数据"
```

**AI Agent决策流程:**

```python
# 1. 任务理解
task_type = "EXPLICIT"
url = "https://space.bilibili.com/123456"
target_data = "视频列表"

# 2. 侦查
analysis = brain.smart_investigate(url)
# 结果: anti_level = "MEDIUM", 检测到WBI签名

# 3. 选择Skills
skills_chain = [
    "01-reconnaissance",  # 已完成，发现API
    "03-signature",       # 需要WBI签名
    "02-anti-detection",  # 反检测
    "07-scheduling",      # 分页调度
    "04-request",         # API请求
    "05-parsing",         # JSON解析
    "06-storage"          # 存储
]

# 4. 战术决策
# B站WBI签名相对简单，可以直接复现
# (参考03-signature.md的B站示例)

# 5. 执行
# (这里是伪代码示例)
wbi_key = get_wbi_key()  # 从页面提取
signed_params = sign_wbi(params, wbi_key)

results = []
for page in range(1, max_pages+1):
    result = brain.call_api(
        url=f"https://api.bilibili.com/x/space/wbi/arc/search",
        params=signed_params
    )
    results.extend(result.body["data"]["list"]["vlist"])

brain.export_data(results, "bilibili_videos")
```

---

### 案例3: 故障恢复（京东403）

**用户输入:**
```
"爬取京东商品，但遇到403错误"
```

**AI Agent决策流程:**

```python
# 1. 任务类型
task_type = "TROUBLESHOOT"
error_code = "HTTP_403"

# 2. 触发故障决策树
fault_result = diagnose_fault(error_code, context={
    "url": "https://item.jd.com/...",
    "headers": {...},
    "response": "403 Forbidden"
})

# 3. 诊断结果
# fault_result.root_cause = "TLS_FINGERPRINT"
# fault_result.recovery_actions = [
#     "使用curl_cffi库",
#     "添加完整浏览器指纹",
#     "启用代理"
# ]

# 4. 自动应用修复
config = AgentConfig(
    use_curl_cffi=True,      # TLS指纹伪装
    stealth_mode=True,        # 反检测
    proxy_enabled=True        # 启用代理
)
brain = Brain(config)

# 5. 重试
result = brain.call_api(url)

# 6. 验证
if result.success:
    brain.report_cookie_result(success=True)
    # 记录到17-feedback-loop
else:
    # 升级到人工处理
    escalate_to_user(fault_result)
```

---

## 📊 Skills调用频率参考

基于任务类型的Skills调用频率:

| Skill | 调用频率 | 必须调用? | 说明 |
|-------|---------|----------|------|
| 01-reconnaissance | 100% | ✅ 是 | 每个任务都要先侦查 |
| 18-brain-controller | 100% | ✅ 是 | 你就是这个模块 |
| 04-request | 95% | ✅ 是 | 几乎所有任务都要请求 |
| 05-parsing | 90% | ⚠️ 看情况 | API返回JSON可跳过 |
| 06-storage | 85% | ❌ 否 | 用户要求才存储 |
| 02-anti-detection | 40% | ❌ 否 | MEDIUM+才需要 |
| 03-signature | 30% | ❌ 否 | 有签名才需要 |
| 07-scheduling | 25% | ❌ 否 | 批量任务才需要 |
| 19-fault-decision-tree | 20% | ❌ 否 | 出错时自动触发 |
| 09-js-reverse | 15% | ❌ 否 | 复杂签名才需要 |
| 16-tactics | 15% | ❌ 否 | HIGH+才需要 |
| 10-captcha | 10% | ❌ 否 | 遇到验证码 |
| 其他 | <5% | ❌ 否 | 特殊场景 |

---

## ✅ 验证清单

在执行每个任务前，检查以下事项:

### 任务理解阶段
- [ ] 是否提取了URL?
- [ ] 是否明确了目标数据?
- [ ] 是否识别了任务类型?
- [ ] 信息是否完整?（不完整则询问用户）

### 模块选择阶段
- [ ] 是否调用了01-reconnaissance?
- [ ] 是否根据anti_level选择了正确的模式?
- [ ] 是否检查了依赖关系?
- [ ] 是否有预设配置可用?

### 执行阶段
- [ ] 是否按顺序调用Skills?
- [ ] 是否处理了中间结果?
- [ ] 遇到错误是否触发了19-fault-decision-tree?
- [ ] 是否记录了执行日志?

### 结果交付阶段
- [ ] 数据是否符合预期格式?
- [ ] 是否需要存储?（06-storage）
- [ ] 是否需要反馈学习?（17-feedback-loop）
- [ ] 是否告知用户完成状态?

---

## 🚀 快速参考卡片

### 你最常用的代码模式

```python
# ========== 标准流程模板 ==========
from unified_agent import Brain

brain = Brain()

# 1️⃣ 侦查（必须）
analysis = brain.smart_investigate(url)

# 2️⃣ 决策（根据anti_level）
if analysis.anti_scrape_level in ["low", "medium"]:
    # 简单模式
    result = brain.call_api(analysis.main_data_api["url"])

elif analysis.anti_scrape_level == "high":
    # 复杂模式：可能需要签名
    # (参考03-signature.md)
    pass

elif analysis.anti_scrape_level == "extreme":
    # 极限模式：检查预设或需要逆向
    if analysis.matched_preset:
        preset = brain.get_preset(url)
    else:
        print("需要深度逆向")
        print(analysis.next_steps)

# 3️⃣ 存储（可选）
if result.success:
    brain.export_data(result.body, "output")
```

---

## 🔗 相关文档

- **[SKILLS.md](SKILLS.md)** - Skills总览和工作流程
- **[SKILL-MATRIX.md](SKILL-MATRIX.md)** - Skills依赖矩阵
- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - 人类用户使用指南
- **[18-brain-controller.md](../skills/18-brain-controller.md)** - 你的核心逻辑
- **[19-fault-decision-tree.md](../skills/19-fault-decision-tree.md)** - 错误处理决策
- **[20-e2e-cases.md](../skills/20-e2e-cases.md)** - 端到端案例库

---

## 📌 总结

**作为AI Agent，你需要：**

1. ✅ **理解任务** - 识别TYPE，提取关键信息
2. ✅ **先侦查** - 永远先调用`brain.smart_investigate()`
3. ✅ **看anti_level** - 根据反爬等级选择模式
4. ✅ **串联Skills** - 按依赖关系顺序调用
5. ✅ **自动恢复** - 错误时触发19-fault-decision-tree
6. ✅ **反馈学习** - 记录决策和结果到17-feedback-loop

**记住：你就是18-brain-controller，这些Skills都是你的工具！**

---

**版本**: 1.0.0
**更新日期**: 2026-01-28
**适用Agent**: Claude Sonnet/Opus, GPT-4, 其他支持function calling的LLM
