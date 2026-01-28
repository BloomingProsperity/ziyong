# 🔧 Ultra Pachong 代码审计问题修复报告

**审计日期**: 2026-01-28
**修复状态**: 进行中

---

## 📋 问题清单

### 🔴 Critical Issues

#### ✅ Issue 1: 文件编码/语法问题（已核查）

**报告问题**:
- assessment.py (line 104)
- collector.py (line 169)
- tools.py (line 107)
- agent.py (line 477)

**检查结果**: ✅ **未发现语法错误**
- 所有报告的行都是合法的Python代码
- 字符串都正确闭合
- 没有非法token

**可能原因**:
- IDE或编辑器的临时显示问题
- 文件编码设置问题（建议使用UTF-8）

**建议**:
```bash
# 验证文件编码
file -bi unified_agent/core/assessment.py
# 应该显示: text/x-python; charset=utf-8
```

---

#### ✅ Issue 2: 数据模型字段完整性（已核查）

**报告问题**:
- task.py (line 20, 25) - 字段被注释
- types.py (line 17, 23) - 枚举被注释
- schema.py (line 11, 41) - 字段被注释

**检查结果**: ✅ **未发现被注释的字段**

**实际情况**:
```python
# task.py - 所有字段都存在
@dataclass
class Task:
    task_type: TaskType = TaskType.EXPLICIT    # ✅ 存在
    difficulty: Difficulty = Difficulty.EASY    # ✅ 存在
    target_url: Optional[str] = None            # ✅ 存在
    target_data: Optional[List[str]] = None     # ✅ 存在

# types.py - 所有枚举值都存在
class TaskType(str, Enum):
    EXPLICIT = "explicit"    # ✅ 存在
    FUZZY = "fuzzy"          # ✅ 存在
    CONSULT = "consult"      # ✅ 存在
    HELP = "help"            # ✅ 存在

# schema.py - 所有字段都存在
class KnowledgeType(str, Enum):
    SITE = "site"            # ✅ 存在
    TECHNIQUE = "technique"  # ✅ 存在
    ERROR = "error"          # ✅ 存在
    DECISION = "decision"    # ✅ 存在
```

**结论**: 无需修复

---

#### ✅ Issue 3: learner.py 关键语句（已核查）

**报告问题**:
- learner.py (line 32, 36, 62, 67) - 关键语句被注释

**检查结果**: ✅ **未发现被注释的关键语句**

**实际代码**:
```python
# line 33: site对象加载 - ✅ 正常
site = self.store.load(f"site:{domain}")
if not site:
    site = SiteKnowledge(domain=domain)

# line 38-39: 策略更新 - ✅ 正常
for strategy in result.strategies_tried:
    self._update_strategy(site, strategy, result.status.value == "success")

# line 64-68: 成功率更新 - ✅ 正常
if existing:
    old_rate = existing.get("success_rate", 0.5)
    new_rate = old_rate * 0.8 + (1.0 if success else 0.0) * 0.2
    existing["success_rate"] = round(new_rate, 2)
```

**结论**: 代码逻辑完整，无需修复

---

#### 🔴 Issue 4: __main__.py 导入路径错误（需修复）

**报告问题**: python -m unified_agent 会 ImportError

**实际问题**:
```python
# 当前代码 (line 3) - ❌ 错误
from .orchestrator import AgentOrchestrator

# 正确路径应该是 - ✅ 正确
from .api.orchestrator import AgentOrchestrator
```

**修复方案**: 见下方修复代码

---

#### 🔴 Issue 5: MCP tools 占位实现（需优化）

**报告问题**: tools.py (line 62) 返回 "TODO"

**实际情况**:
```python
def scrape_page(url: str, selector: Optional[str] = None,
                wait_for: Optional[str] = None) -> ToolResult:
    """抓取页面 - 当前是占位实现"""
    # TODO: 实际实现需要调用 unified_agent.scraper
    return ToolResult(
        status="success",
        data={"url": url, "content": "TODO: 实际抓取结果"},
        message="占位实现"
    )
```

**问题**: MCP工具未连接到实际的Brain模块

**修复方案**: 见下方修复代码

---

### 🟡 Medium Issues

#### 🔴 Issue 6: MCP 限流计数器不复位（需修复）

**报告问题**: server.py (line 72) - 限流计数永久累加

**实际代码**:
```python
def _rate_limit_check(self) -> bool:
    """速率限制检查"""
    self._call_count += 1
    # TODO: 实现基于时间窗口的速率限制
    return self._call_count < 100
```

**问题**:
- `_call_count` 只增不减
- 达到100次后永久被拒
- 缺少时间窗口机制

**修复方案**: 见下方修复代码

---

#### 🔴 Issue 7: 缺少依赖库（需安装）

**检查结果**:
```bash
❌ playwright 未安装
   导致: from scraper.collector import InfoCollector 失败

❌ ddddocr 未安装（可选）
   影响: 验证码识别功能

❌ opencv-python 未安装（可选）
   影响: 图像处理功能
```

**修复方案**: 更新 requirements.txt

---

#### ⏳ Issue 8: 缺少测试文件（待补充）

**检查结果**:
```bash
$ find . -name "test_*.py" -o -name "*_test.py"
# 未找到任何测试文件
```

**建议**: 创建测试目录和基础测试

---

## 🔧 修复方案

### Fix 1: 修复 __main__.py 导入路径

```python
# unified_agent/__main__.py
"""统一入口 - 启动Agent"""
import asyncio
from .api.orchestrator import AgentOrchestrator  # ✅ 修复导入路径


def main():
    """主入口"""
    agent = AgentOrchestrator()
    print("Unified Agent Started")
    print(f"Available tools: {[t['name'] for t in agent.mcp.registry.list_tools()]}")
    # TODO: 启动HTTP服务或CLI交互


if __name__ == "__main__":
    main()
```

---

### Fix 2: 修复 MCP 工具实现

```python
# unified_agent/mcp/tools.py

def scrape_page(url: str, selector: Optional[str] = None,
                wait_for: Optional[str] = None) -> ToolResult:
    """抓取页面 - 实际实现"""
    try:
        # 调用实际的Brain模块
        from ..api.brain import Brain

        brain = Brain()

        if selector:
            # 使用选择器抓取
            result = brain.scrape_with_selector(
                url=url,
                item_selector=selector,
                fields=[],
                max_pages=1
            )
        else:
            # 智能抓取
            result = brain.scrape_page(url, max_pages=1)

        return ToolResult(
            status="success" if result.success else "failed",
            data=result.data,
            message=f"抓取成功: {len(result.data)} 条数据"
        )
    except Exception as e:
        return ToolResult(
            status="failed",
            data={},
            message=f"抓取失败: {str(e)}"
        )


def analyze_site(url: str) -> ToolResult:
    """分析网站 - 实际实现"""
    try:
        from ..api.brain import Brain

        brain = Brain()
        analysis = brain.smart_investigate(url, wait_seconds=3, scroll=False)

        return ToolResult(
            status="success",
            data={
                "site_type": analysis.site_type,
                "anti_scrape_level": analysis.anti_scrape_level,
                "recommended_approach": analysis.recommended_approach,
                "api_endpoints": [api["url"] for api in analysis.api_endpoints],
                "signature_params": [s.param_name for s in analysis.signature_params],
            },
            message=f"分析完成: {analysis.site_name or 'Unknown'}"
        )
    except Exception as e:
        return ToolResult(
            status="failed",
            data={},
            message=f"分析失败: {str(e)}"
        )
```

---

### Fix 3: 修复 MCP 限流计数器

```python
# unified_agent/mcp/server.py

import time
from collections import deque

class MCPServer:
    def __init__(self):
        # ...现有代码...

        # 速率限制 - 使用滑动窗口
        self._call_timestamps = deque(maxlen=100)  # 保留最近100次调用时间
        self._rate_limit_window = 60  # 时间窗口：60秒
        self._rate_limit_max = 100    # 窗口内最大调用次数

    def _rate_limit_check(self) -> bool:
        """速率限制检查 - 基于时间窗口"""
        current_time = time.time()

        # 移除窗口外的旧记录
        cutoff_time = current_time - self._rate_limit_window
        while self._call_timestamps and self._call_timestamps[0] < cutoff_time:
            self._call_timestamps.popleft()

        # 检查窗口内调用次数
        if len(self._call_timestamps) >= self._rate_limit_max:
            return False

        # 记录本次调用
        self._call_timestamps.append(current_time)
        return True
```

---

### Fix 4: 更新 requirements.txt

```txt
# unified_agent/requirements.txt

# === 核心依赖 (必须) ===
httpx>=0.24.0
playwright>=1.40.0        # ✅ 添加 playwright
beautifulsoup4>=4.12.0
lxml>=4.9.0

# === 可选依赖 ===
# 验证码识别
ddddocr>=1.4.0           # ✅ 添加 ddddocr（图形验证码）
opencv-python>=4.8.0     # ✅ 添加 opencv（图像处理）
Pillow>=10.0.0

# 签名生成
PyJWT>=2.8.0
js2py>=0.74              # JS代码执行

# 代理
kuaidaili>=1.0.0         # 快代理SDK（如需要）

# 数据库（可选）
sqlalchemy>=2.0.0        # 知识库持久化

# 监控（可选）
prometheus-client>=0.19.0

# 测试
pytest>=7.4.0            # ✅ 添加测试框架
pytest-asyncio>=0.21.0
```

---

### Fix 5: 创建基础测试框架

```python
# tests/test_core.py
"""核心模块测试"""
import pytest
from unified_agent.core.signature import SignatureManager, SignatureRequest, SignType


def test_signature_manager_init():
    """测试签名管理器初始化"""
    manager = SignatureManager()
    assert manager is not None
    assert hasattr(manager, 'recognizers')


def test_md5_signature():
    """测试MD5签名生成"""
    manager = SignatureManager()
    request = SignatureRequest(
        params={"test": "value"},
        sign_type=SignType.MD5,
        credentials={"secret": "test_secret"}
    )
    result = manager.generate(request)
    assert result.status == "success"
    assert result.signature is not None


# tests/test_scheduling.py
"""调度模块测试"""
import pytest
import asyncio
from unified_agent.core.scheduling import create_scheduler, Task


@pytest.mark.asyncio
async def test_scheduler_basic():
    """测试基础调度功能"""
    scheduler = create_scheduler(concurrency=2, rate_limit=10.0)

    async def dummy_task(x):
        await asyncio.sleep(0.1)
        return x * 2

    tasks = [
        Task(id=f"task_{i}", func=dummy_task, args=(i,))
        for i in range(5)
    ]

    result = await scheduler.schedule(tasks)
    assert result.success >= 5
    assert result.failed == 0
```

---

### Fix 6: 创建测试配置

```python
# tests/conftest.py
"""pytest配置"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def temp_data_dir(tmp_path):
    """临时数据目录"""
    return tmp_path / "data"


@pytest.fixture
def mock_config():
    """Mock配置"""
    from unified_agent.core.config import AgentConfig
    return AgentConfig(
        proxy_enabled=False,
        headless=True,
        data_dir=None  # 使用默认
    )
```

---

## 📝 执行修复步骤

### Step 1: 修复代码文件

```bash
# 1. 修复 __main__.py
# 手动编辑或使用sed
sed -i 's/from \.orchestrator/from .api.orchestrator/' unified_agent/__main__.py

# 2. 备份并更新 tools.py
cp unified_agent/mcp/tools.py unified_agent/mcp/tools.py.bak
# 然后手动应用 Fix 2 的代码

# 3. 备份并更新 server.py
cp unified_agent/mcp/server.py unified_agent/mcp/server.py.bak
# 然后手动应用 Fix 3 的代码
```

### Step 2: 安装依赖

```bash
# 安装核心依赖
pip install playwright
playwright install chromium

# 安装可选依赖
pip install ddddocr opencv-python Pillow PyJWT

# 安装测试依赖
pip install pytest pytest-asyncio
```

### Step 3: 验证修复

```bash
# 测试导入
python -c "from unified_agent.api.orchestrator import AgentOrchestrator; print('OK')"

# 测试主入口
python -m unified_agent

# 运行测试（创建测试文件后）
pytest tests/ -v
```

---

## ✅ 修复验证清单

- [ ] __main__.py 导入路径修复
- [ ] MCP tools 实际实现连接
- [ ] MCP 限流计数器时间窗口机制
- [ ] requirements.txt 更新
- [ ] playwright 安装成功
- [ ] 测试框架创建
- [ ] 基础测试编写
- [ ] 所有模块可正常导入
- [ ] python -m unified_agent 可运行

---

## 📊 问题总结

### 实际发现的问题

| 类别 | 数量 | 严重程度 | 状态 |
|------|------|----------|------|
| 导入路径错误 | 1 | 🔴 Critical | 待修复 |
| 功能占位实现 | 2 | 🔴 Critical | 待修复 |
| 限流机制缺陷 | 1 | 🟡 Medium | 待修复 |
| 缺少依赖 | 3 | 🟡 Medium | 待安装 |
| 缺少测试 | 1 | 🟢 Low | 待创建 |
| **总计** | **8** | - | **待处理** |

### 误报的问题

| 报告问题 | 检查结果 | 说明 |
|---------|---------|------|
| 文件编码/语法错误 | ✅ 无问题 | 可能是IDE显示问题 |
| 数据模型字段缺失 | ✅ 无问题 | 所有字段都存在 |
| learner.py 语句被注释 | ✅ 无问题 | 代码逻辑完整 |

---

## 🎯 优先级建议

### 立即修复（阻断性）
1. ✅ 修复 __main__.py 导入路径
2. ✅ 安装 playwright
3. ✅ 修复 MCP tools 实现

### 短期修复（1-2天）
4. ✅ 修复 MCP 限流机制
5. ✅ 安装可选依赖
6. ✅ 创建测试框架

### 中期完善（1周）
7. ✅ 编写完整测试
8. ✅ 添加CI/CD
9. ✅ 完善文档

---

**报告生成时间**: 2026-01-28
**下次审计**: 修复完成后
