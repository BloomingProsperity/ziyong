# 00-skill-template.md - Skills 文档规范

## 一、统一元数据 Schema

每个 Skill 文档头部必须包含以下 YAML frontmatter：

```yaml
---
# 基础信息
skill_id: "XX-name"           # 格式: 两位数字-英文名
name: "模块名称"
version: "1.0.0"              # 语义化版本
status: "stable"              # draft | beta | stable | deprecated
implementation_status: "partial"  # none | partial | complete (代码实现状态)
difficulty: 3                 # 1-5 整数，不用星星符号
category: "core"              # core | advanced | evolution | infrastructure

# 功能描述
description: "一句话描述模块职责"
triggers:                     # 什么情况下触发使用此模块
  - "需要分析目标网站时"
  - "开始新任务前"

# 依赖关系 (内部Skill依赖)
dependencies:
  required:                   # 必须依赖
    - skill: "01-reconnaissance"
      reason: "需要侦查结果作为输入"
      min_version: "1.0.0"
  optional:                   # 可选依赖
    - skill: "11-fingerprint"
      reason: "高反爬网站需要指纹伪装"
      condition: "anti_crawl_level >= HIGH"
      fallback: "使用默认指纹"

# 外部依赖 (Python包/npm包/服务)
external_dependencies:
  required:
    - name: "httpx"
      version: ">=0.24.0"
      type: "python_package"
      install: "pip install httpx"
  optional:
    - name: "playwright"
      version: ">=1.40.0"
      condition: "需要浏览器渲染时"
      type: "python_package"
      install: "pip install playwright"

# 输入输出
inputs:
  - name: "target_url"
    type: "string"
    required: true
    description: "目标URL"
  - name: "options"
    type: "dict"
    required: false
    description: "可选配置"

outputs:
  - name: "result"
    type: "AnalysisResult"
    description: "分析结果对象"

# SLO (Service Level Objectives)
slo:
  - metric: "成功率"
    target: ">= 95%"
    scope: "普通网站 (反爬等级 LOW/MEDIUM)"
    degradation: "降级到浏览器模式"
  - metric: "响应时间"
    target: "< 30s"
    scope: "单页面分析"
    degradation: "超时后返回部分结果"

# 风险与限制
risks:
  - risk: "目标网站结构变化"
    impact: "选择器失效"
    mitigation: "使用多重选择器 + AI辅助"
  - risk: "IP被封禁"
    impact: "无法继续采集"
    mitigation: "代理轮换 + 频率控制"

limitations:
  - "不支持需要人工验证的验证码"
  - "不处理违法内容"

# 标签
tags:
  - "侦查"
  - "分析"
  - "reconnaissance"
---
```

---

## 二、标准章节结构

每个 Skill 文档必须包含以下章节（按顺序）：

### 1. 模块目标 (必须)

```markdown
## 模块目标

| 目标 | SLO | 适用范围 | 降级策略 |
|------|-----|----------|----------|
| 目标1 | 可量化指标 | 前提条件 | 不达标时的处理 |
```

**要求**：
- 不使用"100%"、"必须"等绝对化表述
- 每个目标必须有明确的适用范围
- 每个目标必须有降级策略

### 2. 接口定义 (必须)

```markdown
## 接口定义

### 输入

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| url | string | 是 | - | 目标URL |
| timeout | int | 否 | 30 | 超时秒数 |

### 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| status | enum | success/partial/failed |
| data | object | 结果数据 |
| errors | list | 错误列表 (可为空) |

### 错误码

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| E001 | 连接超时 | 重试或切换代理 |
```

### 3. 核心逻辑 (必须)

```markdown
## 核心逻辑

### 决策流程图

[流程图或决策树]

### 关键算法/策略

[具体实现逻辑]
```

### 4. 与其他 Skill 的交互 (必须)

```markdown
## Skill 交互

### 上游 (谁调用我)

| Skill | 调用场景 | 传入数据 |
|-------|----------|----------|
| 18-brain-controller | 任务开始时 | task_context |

### 下游 (我调用谁)

| Skill | 调用场景 | 传出数据 |
|-------|----------|----------|
| 02-anti-detection | 需要伪装时 | stealth_config |

### 调用时序图

[时序图]
```

### 5. 使用示例 (必须)

```markdown
## 使用示例

### 基础用法

[代码示例]

### 进阶用法

[代码示例]

### 错误处理

[代码示例]
```

### 6. 配置选项 (可选)

```markdown
## 配置选项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
```

### 7. 诊断日志 (必须)

```markdown
## 诊断日志

### 正常日志格式

[日志示例]

### 错误日志格式

[日志示例]

### AI 自诊断检查点

[检查项列表]
```

### 8. 常见问题 (可选)

```markdown
## FAQ

### Q: 问题1?
A: 回答

### Q: 问题2?
A: 回答
```

---

## 三、命名规范

### Skill ID 规范

```
00-09: 核心流程模块
10-19: 高级专业模块
20-29: 自主进化模块
30-39: 基础设施模块
```

### 当前分配

| 范围 | 类别 | 已分配 |
|------|------|--------|
| 00-09 | 核心流程 | 00-quick-start, 01-reconnaissance, 02-anti-detection, 03-signature, 04-request, 05-parsing, 06-storage, 07-scheduling, 08-diagnosis |
| 10-16 | 高级专业 | 09-js-reverse, 10-captcha, 11-fingerprint, 12-mobile, 13-distributed, 14-monitoring, 15-compliance, 16-tactics |
| 17-22 | 自主进化 | 17-feedback-loop, 18-brain-controller, 19-fault-decision-tree, 20-e2e-cases, 21-anti-patterns, 22-knowledge-format |
| 23-29 | 基础设施 | 23-mcp-protocol, 24-credential-pool, 25-data-schema, 26-testing-regression (待建) |

---

## 四、SLO 编写规范

### 好的 SLO 示例

```yaml
slo:
  - metric: "数据完整性"
    target: ">= 98%"
    scope: "结构稳定的页面，选择器验证通过"
    measurement: "成功提取字段数 / 预期字段数"
    degradation:
      - level: 1
        condition: "完整性 80-98%"
        action: "标记为 partial，继续执行"
      - level: 2
        condition: "完整性 < 80%"
        action: "标记为 failed，触发诊断模块"
```

### 坏的 SLO 示例 (避免)

```yaml
# ❌ 错误: 绝对化表述，无降级
slo:
  - metric: "成功率"
    target: "100%"  # 不现实
    scope: "所有网站"  # 太宽泛
    degradation: null  # 无降级
```

---

## 五、依赖声明规范

### 内部依赖 (Skills)

```yaml
dependencies:
  required:
    - skill: "01-reconnaissance"
      reason: "需要目标分析结果"
      min_version: "1.0.0"

  optional:
    - skill: "11-fingerprint"
      reason: "高反爬网站需要指纹"
      condition: "site.anti_crawl_level in ['HIGH', 'EXTREME']"
      fallback: "使用默认指纹"
```

### 外部依赖 (库/服务)

```yaml
external_dependencies:
  required:
    - name: "httpx"
      type: "python_package"
      version: ">=0.24.0"
      install: "pip install httpx"

  optional:
    - name: "redis"
      type: "service"
      version: ">=6.0"
      condition: "分布式模式"
      fallback: "使用本地文件存储"
```

---

## 六、版本兼容性

### Skill 版本号规则

```
MAJOR.MINOR.PATCH

MAJOR: 不兼容的接口变更
MINOR: 向后兼容的功能新增
PATCH: 向后兼容的问题修复
```

### 变更日志格式

```markdown
## 变更历史

| 版本 | 日期 | 变更类型 | 说明 |
|------|------|----------|------|
| 1.1.0 | 2026-01-27 | feature | 新增XXX功能 |
| 1.0.1 | 2026-01-26 | fix | 修复XXX问题 |
| 1.0.0 | 2026-01-25 | initial | 初始版本 |
```

---

## 七、验收检查清单

每个 Skill 发布前必须通过以下检查：

```markdown
□ YAML frontmatter 完整且格式正确
□ 所有必须章节都存在
□ SLO 都有适用范围和降级策略
□ 依赖关系明确标注 required/optional
□ 输入输出接口定义完整
□ 与其他 Skill 的交互关系已声明
□ 诊断日志格式已定义
□ 至少有一个使用示例
□ 无"100%"、"必须完成"等绝对化表述 (除红线行为)
□ 版本号符合语义化规范
```

---

## 八、文档状态流转

```
draft → beta → stable → deprecated

draft: 初稿，未验证
beta: 已验证，可能有变化
stable: 稳定，可生产使用
deprecated: 已废弃，提供迁移路径
```

---

## 关联模块

- **18-brain-controller.md** - 使用此规范编排 Skills
- **22-knowledge-format.md** - 知识沉淀使用类似结构
