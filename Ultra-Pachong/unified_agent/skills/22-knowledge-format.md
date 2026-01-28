# 22-knowledge-format.md - 知识沉淀格式规范

## 模块目标

| 目标 | KPI | 验收标准 |
|------|-----|----------|
| 经验可复用 | 相似任务查询命中率 > 80% | 新任务能找到参考 |
| 知识可追溯 | 知识来源覆盖率 100% | 每条知识有出处 |
| 持续进化 | 知识库更新频率 > 1次/任务 | 不断积累 |

**核心原则**：`给出需求，必须完成` - 每次任务都是学习机会，每个经验都要沉淀。

---

## 一、知识类型分类

```
知识库
├── 网站知识 (Site Knowledge)
│   ├── 反爬特征
│   ├── 签名算法
│   ├── 有效策略
│   └── 失败记录
├── 技术知识 (Technical Knowledge)
│   ├── 算法实现
│   ├── 工具使用
│   └── 问题解决
├── 决策知识 (Decision Knowledge)
│   ├── 场景判断
│   ├── 方案选择
│   └── 权衡取舍
└── 错误知识 (Error Knowledge)
    ├── 失败原因
    ├── 修复方法
    └── 预防措施
```

---

## 二、网站知识格式

### 2.1 网站档案 (Site Profile)

```yaml
site_profile:
  # 基本信息
  site_id: "jd_com"  # 唯一标识
  domain: "jd.com"
  name: "京东"
  category: "电商"
  last_updated: "2026-01-27T10:30:00Z"

  # 反爬评估
  anti_crawl:
    level: "EXTREME"  # LOW|MEDIUM|HIGH|EXTREME
    score: 95  # 0-100
    features:
      - name: "h5st签名"
        difficulty: 5
        description: "复杂的时间戳+设备指纹签名"
      - name: "TLS指纹检测"
        difficulty: 4
        description: "检测JA3指纹"
      - name: "行为分析"
        difficulty: 4
        description: "检测非人类访问模式"

  # 成功策略
  working_strategies:
    - strategy_id: "jd_rpc_h5st"
      name: "RPC调用h5st"
      success_rate: 95
      last_verified: "2026-01-27"
      requirements:
        - "Chrome浏览器"
        - "登录账号"
        - "住宅代理"
      steps:
        - "启动浏览器访问京东"
        - "注入RPC服务"
        - "调用签名函数"
        - "使用签名请求API"
      code_reference: "examples/jd_h5st.py"

  # 失败记录
  failed_attempts:
    - attempt_id: "fail_001"
      date: "2026-01-25"
      method: "直接requests请求"
      result: "403 Forbidden"
      lesson: "必须有h5st签名"

    - attempt_id: "fail_002"
      date: "2026-01-26"
      method: "猜测MD5签名"
      result: "签名验证失败"
      lesson: "签名算法复杂，需要逆向"

  # 关键URL模式
  url_patterns:
    - pattern: "api.m.jd.com/client.action"
      type: "API"
      requires_sign: true
      sign_param: "h5st"

    - pattern: "item.jd.com/{sku_id}.html"
      type: "商品页"
      render: "SSR + JS"

  # 频率限制
  rate_limits:
    requests_per_minute: 10
    requests_per_hour: 200
    cool_down_after_block: 3600  # 秒

  # 相关技术文档
  references:
    - title: "京东h5st逆向分析"
      path: "skills/09-js-reverse.md#京东h5st"
    - title: "京东采集案例"
      path: "skills/20-e2e-cases.md#case-08"
```

### 2.2 签名算法档案

```yaml
signature_profile:
  sig_id: "jd_h5st_v4"
  site: "jd.com"
  name: "h5st v4.x"
  version: "4.7"
  last_updated: "2026-01-27"

  # 算法特征
  characteristics:
    output_format: "日期_版本_fp_ts_hash1_hash2_hash3_hash4"
    output_length: "约80字符"
    hash_algorithm: "自定义(含AES)"
    time_sensitive: true
    device_bound: true

  # 输入参数
  inputs:
    - name: "functionId"
      required: true
      description: "API功能标识"
    - name: "body"
      required: true
      description: "请求体JSON"
    - name: "timestamp"
      required: true
      description: "13位时间戳"
    - name: "appid"
      required: true
      description: "应用ID"

  # 生成流程
  generation_steps:
    - step: 1
      action: "收集设备指纹"
      details: "Canvas, WebGL, 屏幕信息等"
    - step: 2
      action: "生成fingerprint"
      details: "多个指纹hash组合"
    - step: 3
      action: "构建签名字符串"
      details: "参数排序+拼接"
    - step: 4
      action: "AES加密"
      details: "使用动态密钥"
    - step: 5
      action: "格式化输出"
      details: "组合各部分成最终h5st"

  # 实现方式
  implementations:
    - method: "RPC"
      difficulty: 3
      stability: "高"
      description: "通过浏览器调用原JS"
      code_path: "examples/jd_h5st_rpc.py"

    - method: "补环境"
      difficulty: 5
      stability: "中"
      description: "Node.js模拟浏览器环境"
      code_path: "examples/jd_h5st_env.js"

  # 常见问题
  common_issues:
    - issue: "签名过期"
      cause: "时间戳超过服务器允许范围"
      solution: "确保时间同步，签名后立即使用"

    - issue: "设备指纹不一致"
      cause: "指纹变化导致签名无效"
      solution: "保持固定的浏览器环境"

  # 验证方法
  verification:
    test_url: "https://api.m.jd.com/client.action"
    test_params:
      functionId: "wareBusiness"
      body: '{"skuId":"12345"}'
    expected_response: "包含商品信息的JSON"
```

---

## 三、技术知识格式

### 3.1 问题解决档案

```yaml
solution_profile:
  solution_id: "sol_cloudflare_bypass"
  category: "反检测"
  title: "Cloudflare 5秒盾绕过"
  created: "2026-01-20"
  last_verified: "2026-01-27"

  # 问题描述
  problem:
    description: "访问Cloudflare保护的网站时出现'Checking your browser'页面"
    symptoms:
      - "5秒等待页面"
      - "可能出现验证码"
      - "正常浏览器可访问，脚本被拦截"
    root_cause: "Cloudflare检测到非人类访问特征"

  # 解决方案
  solution:
    approach: "使用undetected-chromedriver + 指纹伪装"
    difficulty: 3
    time_to_implement: "30分钟"

    steps:
      - step: 1
        action: "安装undetected-chromedriver"
        code: "pip install undetected-chromedriver"

      - step: 2
        action: "配置浏览器"
        code: |
          import undetected_chromedriver as uc
          driver = uc.Chrome(headless=False)  # 初次不要headless

      - step: 3
        action: "访问目标网站"
        code: |
          driver.get("https://target.com")
          # 等待验证通过
          time.sleep(10)

      - step: 4
        action: "保存cookies供后续使用"
        code: |
          cookies = driver.get_cookies()
          # 保存到文件

    caveats:
      - "首次可能需要手动完成验证码"
      - "cookie有效期约4小时"
      - "不同地区可能有不同检测"

  # 验证
  verification:
    test_sites:
      - "https://nowsecure.nl"
      - "https://browserleaks.com"
    success_criteria: "能正常访问页面内容"

  # 相关知识
  related:
    - "sol_tls_fingerprint"
    - "sol_canvas_fingerprint"
    - "site_cloudflare"
```

### 3.2 工具使用档案

```yaml
tool_profile:
  tool_id: "tool_playwright"
  name: "Playwright"
  category: "浏览器自动化"
  version: "1.40.0"
  last_updated: "2026-01-27"

  # 基本信息
  description: "Microsoft开发的跨浏览器自动化工具"
  official_docs: "https://playwright.dev/"

  # 适用场景
  use_cases:
    - scenario: "动态渲染页面"
      advantage: "自动等待元素，稳定性高"
    - scenario: "需要登录的网站"
      advantage: "支持持久化context"
    - scenario: "需要截图/录屏"
      advantage: "内置截图和追踪功能"

  # 不适用场景
  avoid_when:
    - scenario: "简单静态页面"
      reason: "杀鸡用牛刀，requests更快"
    - scenario: "需要极致性能"
      reason: "浏览器开销大"

  # 常用代码片段
  snippets:
    - name: "基础使用"
      code: |
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://example.com")
            content = page.content()
            browser.close()

    - name: "等待元素"
      code: |
        page.wait_for_selector(".data-loaded")
        page.wait_for_load_state("networkidle")

    - name: "执行JavaScript"
      code: |
        result = page.evaluate("window.someFunction()")

    - name: "截图"
      code: |
        page.screenshot(path="screenshot.png", full_page=True)

  # 常见问题
  common_issues:
    - issue: "被检测为自动化"
      solution: "使用playwright-stealth或手动修改navigator"

    - issue: "内存泄漏"
      solution: "及时关闭browser和context"

    - issue: "超时错误"
      solution: "增加timeout参数，检查网络"
```

---

## 四、决策知识格式

### 4.1 决策记录档案

```yaml
decision_record:
  decision_id: "dec_20260127_001"
  timestamp: "2026-01-27T10:30:00Z"
  task_id: "task_jd_product"

  # 决策背景
  context:
    task: "采集京东商品数据"
    constraints:
      - "需要商品详情和价格"
      - "数据量: 1000个SKU"
      - "时间限制: 2小时内"
    initial_assessment:
      site_difficulty: "EXTREME"
      available_resources: ["代理池", "登录账号"]

  # 可选方案
  options:
    - option_id: "A"
      name: "RPC调用h5st"
      pros:
        - "稳定性高"
        - "成功率高"
      cons:
        - "需要保持浏览器运行"
        - "资源消耗大"
      estimated_success_rate: 95
      estimated_time: "1.5小时"

    - option_id: "B"
      name: "补环境执行JS"
      pros:
        - "资源消耗小"
        - "速度快"
      cons:
        - "维护成本高"
        - "环境检测可能失败"
      estimated_success_rate: 70
      estimated_time: "1小时"

    - option_id: "C"
      name: "使用已有cookie"
      pros:
        - "实现简单"
      cons:
        - "cookie会过期"
        - "数据可能不完整"
      estimated_success_rate: 50
      estimated_time: "30分钟"

  # 最终决策
  decision:
    chosen_option: "A"
    rationale: |
      - 任务要求数据准确性高
      - 时间充裕
      - RPC方案成功率最高
      - 虽然资源消耗大，但任务可接受

  # 执行结果
  outcome:
    status: "success"
    actual_time: "1小时20分"
    success_rate: 98
    issues_encountered:
      - "少量商品下架导致404"
    lessons_learned:
      - "RPC方案在京东上确实可靠"
      - "需要处理商品下架的情况"

  # 知识沉淀
  knowledge_extracted:
    - type: "site"
      content: "京东RPC方案成功率98%"
    - type: "decision"
      content: "高准确性要求优先选择RPC方案"
```

### 4.2 场景判断规则

```yaml
decision_rule:
  rule_id: "rule_anti_crawl_level"
  name: "反爬等级判断规则"
  category: "侦查决策"
  version: "1.0"
  last_updated: "2026-01-27"

  # 规则描述
  description: "根据网站特征判断反爬等级"

  # 输入特征
  input_features:
    - name: "has_signature"
      type: "boolean"
      description: "是否有签名参数"
    - name: "signature_complexity"
      type: "enum"
      values: ["none", "simple", "complex", "extreme"]
    - name: "has_fingerprint_detection"
      type: "boolean"
    - name: "has_rate_limit"
      type: "boolean"
    - name: "has_captcha"
      type: "boolean"
    - name: "has_behavior_detection"
      type: "boolean"

  # 判断规则
  rules:
    - condition:
        has_signature: false
        has_fingerprint_detection: false
        has_rate_limit: false
      output:
        level: "LOW"
        score_range: [0, 25]

    - condition:
        OR:
          - has_rate_limit: true
          - has_captcha: true
        signature_complexity: ["none", "simple"]
      output:
        level: "MEDIUM"
        score_range: [26, 50]

    - condition:
        OR:
          - signature_complexity: "complex"
          - has_fingerprint_detection: true
      output:
        level: "HIGH"
        score_range: [51, 75]

    - condition:
        AND:
          - signature_complexity: "extreme"
          - has_fingerprint_detection: true
          - has_behavior_detection: true
      output:
        level: "EXTREME"
        score_range: [76, 100]

  # 使用示例
  examples:
    - input:
        has_signature: false
        has_rate_limit: true
        has_captcha: false
      output:
        level: "MEDIUM"
        explanation: "有频率限制但无签名"

    - input:
        has_signature: true
        signature_complexity: "extreme"
        has_fingerprint_detection: true
        has_behavior_detection: true
      output:
        level: "EXTREME"
        explanation: "京东级别的全方位防护"
```

---

## 五、错误知识格式

### 5.1 错误档案

```yaml
error_profile:
  error_id: "err_403_signature"
  category: "请求错误"
  first_seen: "2026-01-15"
  occurrences: 47
  last_seen: "2026-01-27"

  # 错误特征
  signature:
    http_status: 403
    response_patterns:
      - "signature invalid"
      - "sign error"
      - "illegal request"
    context_patterns:
      - "URL中有sign/signature参数"
      - "响应提示签名错误"

  # 根因分析
  root_causes:
    - cause_id: "rc1"
      probability: 40
      description: "签名算法错误"
      indicators:
        - "自行实现的签名"
        - "未逆向分析"

    - cause_id: "rc2"
      probability: 30
      description: "签名参数缺失或顺序错误"
      indicators:
        - "参数不全"
        - "排序方式错误"

    - cause_id: "rc3"
      probability: 20
      description: "签名已过期"
      indicators:
        - "时间戳参数存在"
        - "签名生成与请求间隔过长"

    - cause_id: "rc4"
      probability: 10
      description: "设备指纹变化"
      indicators:
        - "签名包含设备信息"
        - "环境发生变化"

  # 解决方案
  solutions:
    - for_cause: "rc1"
      action: "重新逆向分析签名算法"
      reference: "skills/09-js-reverse.md"

    - for_cause: "rc2"
      action: "检查签名函数的参数要求"
      code: |
        # 检查参数是否完整
        required_params = ['ts', 'appid', 'functionId', 'body']
        for p in required_params:
            assert p in params, f"缺少参数: {p}"

    - for_cause: "rc3"
      action: "减少签名到请求的间隔"
      code: |
        # 签名后立即请求
        sign = generate_sign(params)
        response = request_immediately(sign)  # 不要有延迟

    - for_cause: "rc4"
      action: "保持固定的设备环境"
      reference: "skills/11-fingerprint.md"

  # 预防措施
  prevention:
    - "签名前验证所有必需参数"
    - "签名后立即使用，不缓存"
    - "监控签名成功率，低于阈值告警"
```

### 5.2 故障排查流程

```yaml
troubleshooting_guide:
  guide_id: "tsg_data_empty"
  title: "数据为空排查指南"
  category: "数据问题"
  last_updated: "2026-01-27"

  # 问题描述
  problem: "请求成功但获取的数据为空"

  # 排查步骤
  steps:
    - step: 1
      check: "响应状态码是否200?"
      if_no:
        action: "参考HTTP错误处理"
        reference: "skills/19-fault-decision-tree.md#http层故障"
      if_yes: "继续下一步"

    - step: 2
      check: "响应内容是否为预期格式(HTML/JSON)?"
      if_no:
        possible_causes:
          - "被重定向到登录页"
          - "被重定向到验证页"
          - "返回了错误页面"
        action: "检查响应内容，识别重定向目标"
      if_yes: "继续下一步"

    - step: 3
      check: "HTML中是否有预期元素(浏览器vs请求对比)?"
      if_no:
        possible_causes:
          - "内容需要JS渲染"
          - "选择器失效"
          - "内容在iframe中"
        action: "使用浏览器访问，对比差异"
      if_yes: "继续下一步"

    - step: 4
      check: "选择器是否正确?"
      if_no:
        action: "更新选择器"
        code: |
          # 使用浏览器验证选择器
          document.querySelectorAll(".your-selector")
      if_yes: "继续下一步"

    - step: 5
      check: "是否触发了反爬机制?"
      indicators:
        - "返回假数据"
        - "返回空数据"
        - "返回少量数据"
      action: "参考反爬处理"
      reference: "skills/02-anti-detection.md"

  # 决策树
  decision_tree: |
    响应200?
    ├── 否 → HTTP错误处理
    └── 是 → 内容格式正确?
        ├── 否 → 检查重定向/验证
        └── 是 → 元素存在?
            ├── 否 → 检查JS渲染/iframe
            └── 是 → 选择器正确?
                ├── 否 → 更新选择器
                └── 是 → 检查反爬机制
```

---

## 六、知识检索与复用

### 6.1 知识索引结构

```yaml
knowledge_index:
  # 按网站索引
  by_site:
    jd.com:
      profiles: ["site_jd_com"]
      signatures: ["jd_h5st_v4"]
      solutions: ["sol_jd_login", "sol_jd_price"]
      errors: ["err_jd_403", "err_jd_captcha"]

    taobao.com:
      profiles: ["site_taobao"]
      signatures: ["tb_mtop"]
      # ...

  # 按问题类型索引
  by_problem:
    signature_error:
      - "err_403_signature"
      - "err_invalid_sign"
    data_empty:
      - "tsg_data_empty"
      - "err_empty_response"
    blocked:
      - "err_ip_blocked"
      - "err_account_blocked"

  # 按技术栈索引
  by_technology:
    playwright:
      - "tool_playwright"
      - "sol_playwright_stealth"
    requests:
      - "tool_requests"
      - "sol_requests_session"

  # 按反爬等级索引
  by_difficulty:
    LOW: ["site_news", "site_blog"]
    MEDIUM: ["site_zhihu", "site_weibo"]
    HIGH: ["site_xiaohongshu"]
    EXTREME: ["site_jd_com", "site_taobao"]
```

### 6.2 知识查询接口

```python
class KnowledgeQuery:
    """知识库查询接口"""

    def find_by_site(self, domain: str) -> SiteProfile:
        """根据域名查找网站档案"""
        pass

    def find_similar_sites(self, features: dict) -> list[SiteProfile]:
        """根据特征查找相似网站"""
        pass

    def find_solution(self, problem: str) -> list[Solution]:
        """根据问题查找解决方案"""
        pass

    def find_error_cause(self, error_signature: dict) -> list[ErrorCause]:
        """根据错误特征查找可能原因"""
        pass

    def get_decision_history(self, context: dict) -> list[DecisionRecord]:
        """获取相似场景的历史决策"""
        pass
```

### 6.3 知识复用流程

```
新任务到来
│
├─→ Step 1: 提取任务特征
│   - 目标网站
│   - 数据类型
│   - 约束条件
│
├─→ Step 2: 查询知识库
│   - 查找网站档案
│   - 查找相似案例
│   - 查找历史决策
│
├─→ Step 3: 知识应用
│   │
│   ├─ 找到完全匹配:
│   │   └─→ 直接使用已验证方案
│   │
│   ├─ 找到部分匹配:
│   │   └─→ 参考方案，根据差异调整
│   │
│   └─ 无匹配:
│       └─→ 从基础开始，记录新知识
│
└─→ Step 4: 执行后更新
    - 更新成功率
    - 记录新发现
    - 沉淀经验
```

---

## 七、知识更新机制

### 7.1 自动更新触发

```yaml
auto_update_triggers:
  # 成功后更新
  on_success:
    - update_site_strategy_success_rate
    - record_working_configuration
    - update_last_verified_time

  # 失败后更新
  on_failure:
    - record_failed_attempt
    - analyze_failure_cause
    - update_anti_pattern_if_new

  # 发现新特征
  on_discovery:
    - add_new_signature_if_unknown
    - update_site_anti_crawl_features
    - create_new_solution_if_solved

  # 定期验证
  scheduled:
    - verify_strategies_weekly
    - check_signature_validity_daily
    - cleanup_outdated_knowledge_monthly
```

### 7.2 知识质量评估

```yaml
knowledge_quality:
  metrics:
    - name: "验证时间"
      description: "最后一次验证的时间"
      threshold: "30天内"
      action_if_exceeded: "标记为待验证"

    - name: "成功率"
      description: "基于此知识的任务成功率"
      threshold: "> 70%"
      action_if_below: "标记为低可靠"

    - name: "使用频率"
      description: "被引用的次数"
      threshold: "> 5次/月"
      action_if_below: "标记为冷门"

  quality_levels:
    - level: "VERIFIED"
      criteria: "30天内验证 + 成功率>90%"
    - level: "RELIABLE"
      criteria: "60天内验证 + 成功率>70%"
    - level: "OUTDATED"
      criteria: "超过60天未验证"
    - level: "DEPRECATED"
      criteria: "多次失败或已过时"
```

---

## 八、知识文件组织

```
unified_agent/
├── knowledge/
│   ├── sites/                    # 网站档案
│   │   ├── jd.com.yaml
│   │   ├── taobao.com.yaml
│   │   └── ...
│   ├── signatures/               # 签名算法
│   │   ├── h5st.yaml
│   │   ├── mtop.yaml
│   │   └── ...
│   ├── solutions/                # 解决方案
│   │   ├── cloudflare_bypass.yaml
│   │   ├── captcha_ocr.yaml
│   │   └── ...
│   ├── errors/                   # 错误档案
│   │   ├── signature_errors.yaml
│   │   ├── block_errors.yaml
│   │   └── ...
│   ├── decisions/                # 决策记录
│   │   ├── 2026-01/
│   │   │   ├── dec_001.yaml
│   │   │   └── ...
│   │   └── ...
│   ├── index.yaml                # 知识索引
│   └── quality_report.yaml       # 质量报告
```

---

## 诊断日志格式

```yaml
knowledge_operation:
  operation: "query|create|update|verify"
  timestamp: "操作时间"

  # 查询操作
  query:
    type: "site|solution|error"
    input: "查询条件"
    results: ["匹配结果"]
    match_quality: "exact|partial|none"

  # 创建操作
  create:
    knowledge_type: "类型"
    content: "内容摘要"
    source: "来源任务"

  # 更新操作
  update:
    knowledge_id: "ID"
    field: "更新字段"
    old_value: "旧值"
    new_value: "新值"
    reason: "更新原因"

  # 验证操作
  verify:
    knowledge_id: "ID"
    result: "valid|invalid|outdated"
    details: "验证详情"
```

---

## 关联模块

- **17-feedback-loop.md** - 知识学习入口
- **18-brain-controller.md** - 知识检索调用
- **19-fault-decision-tree.md** - 错误知识应用
- **20-e2e-cases.md** - 案例知识来源
- **21-anti-patterns.md** - 错误知识来源
