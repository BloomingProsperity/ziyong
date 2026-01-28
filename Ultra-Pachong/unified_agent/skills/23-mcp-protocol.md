---
skill_id: "23-mcp-protocol"
name: "MCP工具协议"
version: "1.0.0"
status: "stable"                    # draft | beta | stable | deprecated
implementation_status: "partial"    # none | partial | complete
difficulty: 3
category: "infrastructure"

description: "定义AI Agent与爬虫系统的标准交互协议"

triggers:
  - "AI需要调用爬虫功能时"
  - "外部系统集成时"
  - "构建Agent工具链时"

dependencies:
  required:
    - skill: "18-brain-controller"
      reason: "任务编排入口"
  optional: []

external_dependencies:
  required: []
  optional:
    - name: "fastapi"
      version: ">=0.100.0"
      condition: "HTTP服务模式"
      type: "python_package"
      install: "pip install fastapi"

inputs:
  - name: "tool_name"
    type: "string"
    required: true
  - name: "parameters"
    type: "dict"
    required: true

outputs:
  - name: "result"
    type: "ToolResult"

slo:
  - metric: "响应时间"
    target: "< 100ms"
    scope: "工具元数据查询"
    degradation: "返回缓存结果"
  - metric: "执行成功率"
    target: ">= 95%"
    scope: "参数正确的调用"
    degradation: "返回详细错误信息"

tags: ["MCP", "工具协议", "API"]
---

# 23-mcp-protocol.md - MCP 工具协议规范

## 模块目标

| 目标 | SLO | 适用范围 | 降级策略 |
|------|-----|----------|----------|
| 提供标准化工具接口 | 接口兼容 MCP 规范 | 所有对外工具 | 提供原生 Python 接口 |
| 确保调用安全 | 无越权访问 | 所有外部调用 | 默认拒绝未授权操作 |
| 返回结构化结果 | JSON Schema 兼容 (目标≥95%) | 所有响应 | 返回纯文本描述 |

---

## 一、MCP 协议概述

### 1.1 什么是 MCP

MCP (Model Context Protocol) 是 Anthropic 提出的 AI 模型与外部工具交互的标准协议。

```
┌─────────────┐     MCP Protocol      ┌─────────────────┐
│   AI Model  │◄────────────────────►│  Tool Provider  │
│  (Claude)   │                       │ (Scraper Agent) │
└─────────────┘                       └─────────────────┘
       │                                      │
       │  1. 发现工具                          │
       │  2. 调用工具                          │
       │  3. 接收结果                          │
       ▼                                      ▼
   决策/规划                              执行操作
```

### 1.2 本模块职责

```
23-mcp-protocol 职责:
├── 定义工具清单 (Tool Manifest)
├── 规范参数格式 (Parameter Schema)
├── 统一响应结构 (Response Envelope)
├── 实现安全边界 (Security Boundary)
└── 提供服务接口 (Service Interface)
```

---

## 二、工具清单 (Tool Manifest)

### 2.1 工具定义格式

```json
{
  "tools": [
    {
      "name": "scrape_page",
      "description": "抓取网页内容并提取结构化数据",
      "category": "data_extraction",
      "version": "1.0.0",
      "parameters": {
        "type": "object",
        "required": ["url"],
        "properties": {
          "url": {
            "type": "string",
            "format": "uri",
            "description": "目标网页URL"
          },
          "selectors": {
            "type": "object",
            "description": "CSS选择器映射",
            "additionalProperties": {
              "type": "string"
            }
          },
          "wait_for": {
            "type": "string",
            "description": "等待特定元素出现"
          },
          "timeout": {
            "type": "integer",
            "default": 30,
            "minimum": 1,
            "maximum": 300,
            "description": "超时秒数"
          }
        }
      },
      "returns": {
        "type": "object",
        "properties": {
          "status": {"type": "string", "enum": ["success", "partial", "failed"]},
          "data": {"type": "object"},
          "errors": {"type": "array"}
        }
      },
      "permissions": ["network_access", "data_extraction"],
      "rate_limit": {
        "requests_per_minute": 10,
        "burst": 3
      }
    }
  ]
}
```

### 2.2 完整工具清单

| 工具名 | 类别 | 描述 | 权限要求 | 速率限制 |
|--------|------|------|----------|----------|
| `scrape_page` | extraction | 抓取网页提取数据 | network | 10/min |
| `scrape_api` | extraction | 调用API获取数据 | network | 30/min |
| `analyze_site` | reconnaissance | 分析网站特征 | network | 5/min |
| `solve_captcha` | bypass | 识别验证码 | network, captcha | 5/min |
| `manage_session` | session | 管理登录会话 | credential | 10/min |
| `export_data` | storage | 导出数据到文件 | file_write | 20/min |
| `get_status` | info | 查询任务状态 | - | 60/min |
| `list_presets` | info | 列出预设配置 | - | 60/min |

### 2.3 工具详细定义

#### scrape_page

```json
{
  "name": "scrape_page",
  "description": "抓取网页内容并根据选择器提取结构化数据。支持动态渲染页面。",
  "parameters": {
    "type": "object",
    "required": ["url"],
    "properties": {
      "url": {
        "type": "string",
        "format": "uri",
        "description": "目标网页的完整URL"
      },
      "selectors": {
        "type": "object",
        "description": "字段名到CSS选择器的映射",
        "example": {"title": "h1.title", "price": ".price-value"}
      },
      "render_js": {
        "type": "boolean",
        "default": false,
        "description": "是否启用JavaScript渲染"
      },
      "wait_for": {
        "type": "string",
        "description": "等待指定CSS选择器的元素出现"
      },
      "timeout": {
        "type": "integer",
        "default": 30,
        "minimum": 5,
        "maximum": 120
      },
      "proxy": {
        "type": "string",
        "description": "代理服务器地址 (可选)"
      }
    }
  },
  "returns": {
    "type": "object",
    "properties": {
      "status": {
        "type": "string",
        "enum": ["success", "partial", "failed"]
      },
      "data": {
        "type": "object",
        "description": "提取的数据，key对应selectors中的字段名"
      },
      "metadata": {
        "type": "object",
        "properties": {
          "url": {"type": "string"},
          "status_code": {"type": "integer"},
          "content_type": {"type": "string"},
          "elapsed_ms": {"type": "integer"}
        }
      },
      "errors": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "field": {"type": "string"},
            "error": {"type": "string"}
          }
        }
      }
    }
  }
}
```

#### analyze_site

```json
{
  "name": "analyze_site",
  "description": "分析目标网站的技术栈、反爬机制和最佳抓取策略",
  "parameters": {
    "type": "object",
    "required": ["url"],
    "properties": {
      "url": {
        "type": "string",
        "format": "uri"
      },
      "depth": {
        "type": "string",
        "enum": ["quick", "standard", "deep"],
        "default": "standard",
        "description": "分析深度"
      }
    }
  },
  "returns": {
    "type": "object",
    "properties": {
      "site_info": {
        "type": "object",
        "properties": {
          "domain": {"type": "string"},
          "tech_stack": {"type": "array"},
          "render_mode": {"type": "string"}
        }
      },
      "anti_crawl": {
        "type": "object",
        "properties": {
          "level": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "EXTREME"]},
          "features": {"type": "array"},
          "signature_required": {"type": "boolean"}
        }
      },
      "recommended_strategy": {
        "type": "object",
        "properties": {
          "approach": {"type": "string"},
          "modules": {"type": "array"},
          "rate_limit": {"type": "object"}
        }
      }
    }
  }
}
```

---

## 三、响应结构 (Response Envelope)

### 3.1 标准响应格式

```json
{
  "id": "req_abc123",
  "tool": "scrape_page",
  "timestamp": "2026-01-27T10:30:00Z",
  "duration_ms": 1234,

  "status": "success",

  "result": {
    // 工具特定的返回数据
  },

  "metadata": {
    "request_id": "req_abc123",
    "trace_id": "trace_xyz",
    "quota_remaining": 95,
    "rate_limit": {
      "limit": 10,
      "remaining": 8,
      "reset_at": "2026-01-27T10:31:00Z"
    }
  },

  "errors": []
}
```

### 3.2 错误响应格式

```json
{
  "id": "req_abc123",
  "tool": "scrape_page",
  "timestamp": "2026-01-27T10:30:00Z",
  "duration_ms": 500,

  "status": "failed",

  "result": null,

  "metadata": {
    "request_id": "req_abc123"
  },

  "errors": [
    {
      "code": "NETWORK_TIMEOUT",
      "message": "连接目标服务器超时",
      "details": {
        "url": "https://example.com",
        "timeout": 30,
        "elapsed": 30.5
      },
      "suggestion": "请增加timeout参数或检查目标网站可用性",
      "recoverable": true
    }
  ]
}
```

### 3.3 错误码定义

| 错误码 | HTTP状态 | 描述 | 可恢复 | 建议操作 |
|--------|----------|------|--------|----------|
| `INVALID_PARAMS` | 400 | 参数格式错误 | 否 | 检查参数 |
| `UNAUTHORIZED` | 401 | 未授权访问 | 否 | 提供凭据 |
| `FORBIDDEN` | 403 | 权限不足 | 否 | 申请权限 |
| `NOT_FOUND` | 404 | 目标不存在 | 否 | 检查URL |
| `RATE_LIMITED` | 429 | 超出速率限制 | 是 | 等待后重试 |
| `NETWORK_TIMEOUT` | 504 | 网络超时 | 是 | 重试或换代理 |
| `NETWORK_ERROR` | 502 | 网络错误 | 是 | 重试 |
| `PARSE_ERROR` | 500 | 解析失败 | 是 | 检查选择器 |
| `CAPTCHA_REQUIRED` | 403 | 需要验证码 | 是 | 调用验证码工具 |
| `BLOCKED` | 403 | IP被封禁 | 是 | 切换代理 |
| `INTERNAL_ERROR` | 500 | 内部错误 | 是 | 重试或报告 |

---

## 四、安全边界

### 4.1 权限模型

```yaml
permissions:
  # 基础权限 (默认授予)
  basic:
    - get_status         # 查询状态
    - list_presets       # 列出预设
    - analyze_site       # 分析网站 (只读)

  # 网络权限 (需要显式授权)
  network:
    - scrape_page        # 抓取网页
    - scrape_api         # 调用API
    requires: "network_access"

  # 凭据权限 (敏感操作)
  credential:
    - manage_session     # 管理会话
    - use_account        # 使用账号
    requires: "credential_access"

  # 文件权限 (本地操作)
  file:
    - export_data        # 导出文件
    - save_session       # 保存会话
    requires: "file_write"

  # 高级权限 (需要特别授权)
  advanced:
    - solve_captcha      # 验证码处理
    - bypass_detection   # 绑过检测
    requires: "advanced_bypass"
```

### 4.2 参数校验规则

```python
class ParameterValidator:
    """参数校验器"""

    # URL 白名单模式
    url_patterns = [
        r"^https?://",  # 必须是 HTTP(S)
    ]

    # URL 黑名单 (绝对禁止)
    url_blacklist = [
        r"localhost",
        r"127\.0\.0\.1",
        r"192\.168\.",
        r"10\.",
        r"172\.(1[6-9]|2[0-9]|3[01])\.",
        r"\.gov\.",        # 政府网站
        r"\.mil\.",        # 军事网站
    ]

    # 敏感参数检测
    sensitive_patterns = [
        r"password",
        r"secret",
        r"token",
        r"api_key",
    ]

    def validate_url(self, url: str) -> tuple[bool, str]:
        """验证URL安全性"""
        # 检查黑名单
        for pattern in self.url_blacklist:
            if re.search(pattern, url, re.I):
                return False, f"禁止访问的URL模式: {pattern}"

        # 检查协议
        if not any(re.match(p, url) for p in self.url_patterns):
            return False, "URL必须以http://或https://开头"

        return True, ""

    def sanitize_selectors(self, selectors: dict) -> dict:
        """清理选择器，防止注入"""
        safe_selectors = {}
        for key, value in selectors.items():
            # 移除可能的脚本注入
            if "<script" in value.lower() or "javascript:" in value.lower():
                continue
            safe_selectors[key] = value
        return safe_selectors
```

### 4.3 速率限制

```python
class RateLimiter:
    """速率限制器"""

    # 默认限制配置
    DEFAULT_LIMITS = {
        "scrape_page": {"rpm": 10, "burst": 3},
        "scrape_api": {"rpm": 30, "burst": 5},
        "analyze_site": {"rpm": 5, "burst": 2},
        "solve_captcha": {"rpm": 5, "burst": 2},
        "export_data": {"rpm": 20, "burst": 5},
        "get_status": {"rpm": 60, "burst": 10},
    }

    def check_rate_limit(self, tool: str, client_id: str) -> tuple[bool, dict]:
        """检查速率限制"""
        limit = self.DEFAULT_LIMITS.get(tool, {"rpm": 10, "burst": 3})

        # 实现令牌桶算法
        tokens = self.get_tokens(client_id, tool)

        if tokens > 0:
            self.consume_token(client_id, tool)
            return True, {
                "limit": limit["rpm"],
                "remaining": tokens - 1,
                "reset_at": self.get_reset_time(client_id, tool)
            }
        else:
            return False, {
                "limit": limit["rpm"],
                "remaining": 0,
                "reset_at": self.get_reset_time(client_id, tool),
                "retry_after": self.get_retry_seconds(client_id, tool)
            }
```

---

## 五、服务接口

### 5.1 Python SDK 接口

```python
from unified_agent.mcp import MCPServer, Tool, ToolResult

class ScraperMCPServer(MCPServer):
    """爬虫 MCP 服务器"""

    def __init__(self):
        super().__init__()
        self.brain = Brain()

        # 注册工具
        self.register_tool(Tool(
            name="scrape_page",
            description="抓取网页内容",
            handler=self.handle_scrape_page,
            parameters=SCRAPE_PAGE_SCHEMA
        ))

    async def handle_scrape_page(
        self,
        url: str,
        selectors: dict = None,
        render_js: bool = False,
        timeout: int = 30,
        **kwargs
    ) -> ToolResult:
        """处理 scrape_page 调用"""

        # 1. 参数校验
        is_valid, error = self.validator.validate_url(url)
        if not is_valid:
            return ToolResult.error("INVALID_PARAMS", error)

        # 2. 速率检查
        allowed, rate_info = self.rate_limiter.check_rate_limit(
            "scrape_page", self.client_id
        )
        if not allowed:
            return ToolResult.error("RATE_LIMITED", "超出速率限制", rate_info)

        # 3. 执行抓取
        try:
            if render_js:
                data = await self.brain.scrape_with_browser(
                    url, selectors, timeout
                )
            else:
                data = await self.brain.scrape_page(url, selectors)

            return ToolResult.success(data, metadata=rate_info)

        except TimeoutError:
            return ToolResult.error(
                "NETWORK_TIMEOUT",
                f"请求超时 ({timeout}s)",
                recoverable=True
            )
        except Exception as e:
            return ToolResult.error("INTERNAL_ERROR", str(e))


# 使用示例
server = ScraperMCPServer()

# 作为 HTTP 服务启动
server.serve(host="127.0.0.1", port=8000)

# 或直接调用
result = await server.call_tool("scrape_page", {
    "url": "https://example.com",
    "selectors": {"title": "h1"}
})
```

### 5.2 HTTP API 接口

```
POST /mcp/tools/{tool_name}
Content-Type: application/json
Authorization: Bearer {api_key}

{
  "parameters": {
    "url": "https://example.com",
    "selectors": {"title": "h1"}
  },
  "options": {
    "timeout": 30,
    "trace": true
  }
}
```

```
GET /mcp/tools
# 返回所有可用工具列表

GET /mcp/tools/{tool_name}/schema
# 返回特定工具的参数 schema

GET /mcp/status
# 返回服务状态和配额
```

### 5.3 Claude Desktop 集成

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "web-scraper": {
      "command": "python",
      "args": ["-m", "unified_agent.mcp.server"],
      "env": {
        "SCRAPER_API_KEY": "your-api-key"
      }
    }
  }
}
```

---

## 六、Skill 交互

### 上游 (谁调用我)

| 调用者 | 场景 | 传入数据 |
|--------|------|----------|
| 外部 AI (Claude) | 需要抓取数据时 | tool_call 请求 |
| 自动化流程 | 定时任务 | 预定义参数 |

### 下游 (我调用谁)

| 被调用者 | 场景 | 传出数据 |
|----------|------|----------|
| 18-brain-controller | 复杂任务 | task_context |
| 04-request | 简单请求 | url, params |
| 05-parsing | 数据提取 | html, selectors |

### 调用时序

```
外部调用者                MCP Server              Brain
    │                        │                      │
    │  POST /tools/scrape    │                      │
    │──────────────────────►│                      │
    │                        │                      │
    │                        │  validate params     │
    │                        │─────────────────────│
    │                        │                      │
    │                        │  check rate limit    │
    │                        │─────────────────────│
    │                        │                      │
    │                        │  brain.scrape()      │
    │                        │─────────────────────►│
    │                        │                      │
    │                        │◄─────────────────────│
    │                        │      result          │
    │                        │                      │
    │◄──────────────────────│                      │
    │    ToolResult          │                      │
```

---

## 七、诊断日志

### 正常日志

```
[MCP] Tool called: scrape_page
[MCP] Client: client_abc, Request: req_123
[MCP] Parameters validated: OK
[MCP] Rate limit check: 8/10 remaining
[MCP] Executing tool...
[MCP] Tool completed: 1234ms, status=success
[MCP] Response sent: req_123
```

### 错误日志

```
[MCP] ERROR: Tool call failed
[MCP] Tool: scrape_page, Request: req_123
[MCP] Error code: NETWORK_TIMEOUT
[MCP] Error message: 连接超时 (30s)
[MCP] Recoverable: true
[MCP] Suggestion: 增加timeout或检查网站
```

### AI 自诊断检查点

```yaml
mcp_health_check:
  - check: "工具注册完整性"
    command: "GET /mcp/tools"
    expect: "返回所有定义的工具"

  - check: "参数校验有效"
    command: "POST /tools/scrape_page with invalid URL"
    expect: "返回 INVALID_PARAMS 错误"

  - check: "速率限制生效"
    command: "连续快速调用超过限制"
    expect: "返回 RATE_LIMITED 错误"

  - check: "安全边界有效"
    command: "尝试访问 localhost"
    expect: "被拦截并返回错误"
```

---

## 八、配置选项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `mcp.enabled` | bool | true | 是否启用 MCP 服务 |
| `mcp.host` | string | "127.0.0.1" | 监听地址 |
| `mcp.port` | int | 8000 | 监听端口 |
| `mcp.auth.enabled` | bool | true | 是否启用认证 |
| `mcp.auth.api_keys` | list | [] | 允许的 API Keys |
| `mcp.rate_limit.enabled` | bool | true | 是否启用速率限制 |
| `mcp.rate_limit.default_rpm` | int | 10 | 默认每分钟请求数 |
| `mcp.security.url_blacklist` | list | [...] | URL 黑名单 |

---

## 变更历史

| 版本 | 日期 | 变更类型 | 说明 |
|------|------|----------|------|
| 1.0.0 | 2026-01-27 | initial | 初始版本 |

---

## 关联模块

- **18-brain-controller.md** - 任务编排
- **04-request.md** - 请求执行
- **24-credential-pool.md** - 凭据管理
- **15-compliance.md** - 安全合规
