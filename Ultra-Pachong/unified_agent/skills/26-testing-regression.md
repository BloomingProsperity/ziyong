---
skill_id: "26-testing-regression"
name: "测试回归"
version: "1.0.0"
status: "stable"                    # draft | beta | stable | deprecated
implementation_status: "partial"    # none | partial | complete
difficulty: 3
category: "infrastructure"

description: "自动化测试、基准指标、回归门禁和红线检查"

triggers:
  - "代码变更后"
  - "定期健康检查"
  - "发布前验证"

dependencies:
  required: []
  optional:
    - skill: "all"
      reason: "测试各模块功能"

external_dependencies:
  required: []
  optional:
    - name: "pytest"
      version: ">=7.0.0"
      condition: "使用pytest框架"
      type: "python_package"
      install: "pip install pytest"

inputs:
  - name: "test_suite"
    type: "TestSuite"
    required: true

outputs:
  - name: "report"
    type: "TestReport"

slo:
  - metric: "测试覆盖率"
    target: ">= 80%"
    scope: "核心模块"
    degradation: "标记低覆盖模块"
  - metric: "回归通过率"
    target: ">= 99%"
    scope: "关键用例"
    degradation: "阻止发布+人工审核"

tags: ["测试", "回归", "基准", "CI/CD"]
---

# 26-testing-regression.md - 测试基准与回归检查

## 模块目标

| 目标 | SLO | 适用范围 | 降级策略 |
|------|-----|----------|----------|
| 变更不引入回归 | 回归通过率 ≥99% | 关键用例 | 阻止发布+人工审核 |
| 性能不下降 | 性能偏差 < 10% | 基准测试 | 告警+人工确认 |
| 红线不违反 | 违规率 < 1% | 安全规则 | 拒绝执行+报告 |
| 及时发现问题 | 检测时间 < 5min | CI流程 | 异步检测 |

---

## 一、测试体系

### 1.1 测试分层

```
测试金字塔
│
├── E2E Tests (少量)
│   └── 完整业务流程测试
│
├── Integration Tests (适量)
│   ├── 模块间交互测试
│   └── 外部服务模拟测试
│
├── Unit Tests (大量)
│   ├── 函数级测试
│   └── 类级测试
│
└── Static Analysis (基础)
    ├── 代码风格检查
    └── 类型检查
```

### 1.2 测试类型定义

```python
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from enum import Enum

class TestType(Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    REGRESSION = "regression"
    SECURITY = "security"

class TestPriority(Enum):
    CRITICAL = 1    # 必须通过，否则阻止发布
    HIGH = 2        # 重要，失败需要处理
    MEDIUM = 3      # 一般，可以稍后处理
    LOW = 4         # 可选，不阻止发布

@dataclass
class TestCase:
    """测试用例"""
    id: str
    name: str
    description: str
    type: TestType
    priority: TestPriority

    # 测试函数
    test_func: Callable

    # 前置条件
    preconditions: List[str] = field(default_factory=list)

    # 依赖
    depends_on: List[str] = field(default_factory=list)

    # 标签
    tags: List[str] = field(default_factory=list)

    # 超时
    timeout: int = 60  # 秒

    # 重试
    retries: int = 0

    # 预期结果
    expected_result: Optional[str] = None

@dataclass
class TestSuite:
    """测试套件"""
    name: str
    description: str
    test_cases: List[TestCase] = field(default_factory=list)

    # 全局设置
    setup: Optional[Callable] = None
    teardown: Optional[Callable] = None

    # 并发设置
    parallel: bool = False
    max_workers: int = 4
```

---

## 二、单元测试

### 2.1 模块测试示例

```python
import pytest
from unified_agent import Brain
from unified_agent.validator import DataValidator
from unified_agent.dedup import DataDeduplicator

class TestDataValidator:
    """数据校验器测试"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    @pytest.fixture
    def product_schema(self):
        return DataSchema(
            name="product",
            fields=[
                FieldSchema("sku_id", FieldType.STRING, required=True),
                FieldSchema("price", FieldType.FLOAT, required=True, min_value=0),
            ],
            required_fields=["sku_id", "price"]
        )

    def test_valid_data(self, validator, product_schema):
        """测试有效数据校验"""
        data = {"sku_id": "12345678", "price": 99.99}
        result = validator.validate(data, product_schema)

        assert result.valid
        assert result.data["sku_id"] == "12345678"
        assert result.data["price"] == 99.99

    def test_missing_required_field(self, validator, product_schema):
        """测试缺少必填字段"""
        data = {"sku_id": "12345678"}  # 缺少 price
        result = validator.validate(data, product_schema)

        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].field == "price"
        assert result.errors[0].error_type == "REQUIRED"

    def test_invalid_price(self, validator, product_schema):
        """测试无效价格"""
        data = {"sku_id": "12345678", "price": -10}
        result = validator.validate(data, product_schema)

        assert not result.valid
        assert result.errors[0].error_type == "MIN_VALUE"

    def test_type_conversion(self, validator, product_schema):
        """测试类型转换"""
        data = {"sku_id": "12345678", "price": "99.99"}  # 字符串价格
        result = validator.validate(data, product_schema)

        assert result.valid
        assert isinstance(result.data["price"], float)


class TestDataDeduplicator:
    """数据去重器测试"""

    def test_exact_duplicate(self):
        """测试完全重复"""
        dedup = DataDeduplicator(
            strategy=DeduplicationStrategy.KEY_BASED,
            unique_keys=["sku_id"]
        )

        data1 = {"sku_id": "123", "name": "Product A"}
        data2 = {"sku_id": "123", "name": "Product A Updated"}

        assert not dedup.is_duplicate(data1)
        assert dedup.is_duplicate(data2)  # 相同 sku_id

    def test_different_data(self):
        """测试不同数据"""
        dedup = DataDeduplicator(
            strategy=DeduplicationStrategy.KEY_BASED,
            unique_keys=["sku_id"]
        )

        data1 = {"sku_id": "123", "name": "A"}
        data2 = {"sku_id": "456", "name": "B"}

        assert not dedup.is_duplicate(data1)
        assert not dedup.is_duplicate(data2)  # 不同 sku_id

    def test_batch_dedup(self):
        """测试批量去重"""
        dedup = DataDeduplicator(
            strategy=DeduplicationStrategy.KEY_BASED,
            unique_keys=["sku_id"]
        )

        data_list = [
            {"sku_id": "1"},
            {"sku_id": "2"},
            {"sku_id": "1"},  # 重复
            {"sku_id": "3"},
            {"sku_id": "2"},  # 重复
        ]

        unique, duplicates, stats = dedup.deduplicate(data_list)

        assert len(unique) == 3
        assert len(duplicates) == 2
        assert stats["duplicate_rate"] == 0.4
```

### 2.2 请求模块测试

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from unified_agent.request import RequestClient

class TestRequestClient:
    """请求客户端测试"""

    @pytest.fixture
    def client(self):
        return RequestClient()

    @pytest.mark.asyncio
    async def test_successful_request(self, client):
        """测试成功请求"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                text="OK",
                json=lambda: {"data": "test"}
            )

            response = await client.get("https://example.com")

            assert response.status_code == 200
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, client):
        """测试失败重试"""
        call_count = 0

        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Failed")
            return Mock(status_code=200)

        with patch.object(client, '_do_request', side_effect=mock_request):
            response = await client.get(
                "https://example.com",
                retries=3
            )

            assert response.status_code == 200
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_timeout(self, client):
        """测试超时"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = TimeoutError()

            with pytest.raises(TimeoutError):
                await client.get("https://example.com", timeout=1)
```

---

## 三、集成测试

### 3.1 模块交互测试

```python
import pytest
from unified_agent import Brain

class TestBrainIntegration:
    """Brain 集成测试"""

    @pytest.fixture
    def brain(self):
        return Brain(config={"mode": "test"})

    @pytest.mark.integration
    async def test_analyze_and_scrape_flow(self, brain):
        """测试分析+抓取流程"""
        # 1. 分析网站
        analysis = await brain.analyze_site("https://httpbin.org")

        assert analysis is not None
        assert analysis.site_info is not None

        # 2. 根据分析结果抓取
        result = await brain.scrape_page(
            "https://httpbin.org/html",
            selectors={"title": "h1"}
        )

        assert result.status == "success"
        assert "title" in result.data

    @pytest.mark.integration
    async def test_error_diagnosis_flow(self, brain):
        """测试错误诊断流程"""
        # 触发一个错误
        try:
            await brain.call_api("https://httpbin.org/status/500")
        except Exception as e:
            # 诊断错误
            diagnosis = brain.diagnose_error(e)

            assert diagnosis is not None
            assert diagnosis.error_type is not None
            assert len(diagnosis.suggestions) > 0
```

### 3.2 外部服务模拟

```python
import pytest
from unittest.mock import patch

class TestExternalServiceMock:
    """外部服务模拟测试"""

    @pytest.mark.integration
    async def test_captcha_service_mock(self):
        """测试验证码服务模拟"""
        from unified_agent.captcha import CaptchaSolver

        solver = CaptchaSolver()

        # 模拟打码服务响应
        with patch.object(solver, '_call_service') as mock_service:
            mock_service.return_value = {"code": "abc123", "confidence": 0.95}

            result = await solver.solve_image(b"fake_image_data")

            assert result == "abc123"

    @pytest.mark.integration
    async def test_proxy_pool_mock(self):
        """测试代理池模拟"""
        from unified_agent.proxy import ProxyPool

        pool = ProxyPool()

        # 模拟代理池
        pool._proxies = [
            {"host": "1.1.1.1", "port": 8080, "health": 100},
            {"host": "2.2.2.2", "port": 8080, "health": 80},
        ]

        proxy = pool.get_proxy()
        assert proxy is not None
        assert proxy["health"] >= 80
```

---

## 四、E2E 测试

### 4.1 完整业务流程测试

```python
import pytest

class TestE2EScrapingFlow:
    """端到端抓取流程测试"""

    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_full_scraping_flow(self):
        """测试完整抓取流程 (使用测试网站)"""
        from unified_agent import Brain

        brain = Brain()

        # 1. 侦查
        analysis = await brain.smart_investigate("https://quotes.toscrape.com")
        assert analysis.difficulty in ["LOW", "MEDIUM"]

        # 2. 配置
        config = brain.generate_config(analysis)
        assert config is not None

        # 3. 抓取
        result = await brain.scrape_page(
            "https://quotes.toscrape.com",
            selectors={
                "quotes": ".quote .text::text",
                "authors": ".quote .author::text"
            }
        )

        assert result.status == "success"
        assert len(result.data.get("quotes", [])) > 0

        # 4. 校验
        from unified_agent.schema import DataValidator
        validator = DataValidator()

        # 5. 存储
        brain.export_data(result.data, path="test_output.json")

    @pytest.mark.e2e
    async def test_pagination_flow(self):
        """测试分页流程"""
        from unified_agent import Brain

        brain = Brain()

        all_data = []
        for page in range(1, 4):
            result = await brain.scrape_page(
                f"https://quotes.toscrape.com/page/{page}/",
                selectors={"quotes": ".quote .text::text"}
            )

            if result.status == "success":
                all_data.extend(result.data.get("quotes", []))
            else:
                break

        assert len(all_data) >= 20  # 至少3页数据
```

### 4.2 场景测试

```python
class TestScenarios:
    """场景测试"""

    @pytest.mark.e2e
    @pytest.mark.scenario("静态页面")
    async def test_static_page_scenario(self):
        """场景: 静态页面采集"""
        brain = Brain()

        result = await brain.scrape_page(
            "https://example.com",
            selectors={"title": "h1"}
        )

        assert result.status == "success"

    @pytest.mark.e2e
    @pytest.mark.scenario("动态渲染")
    async def test_dynamic_render_scenario(self):
        """场景: 动态渲染页面"""
        brain = Brain()

        result = await brain.scrape_page(
            "https://quotes.toscrape.com/js/",
            selectors={"quotes": ".quote .text::text"},
            render_js=True
        )

        assert result.status == "success"
        assert len(result.data.get("quotes", [])) > 0

    @pytest.mark.e2e
    @pytest.mark.scenario("API调用")
    async def test_api_call_scenario(self):
        """场景: API调用"""
        brain = Brain()

        result = await brain.call_api(
            "https://httpbin.org/json"
        )

        assert result.status_code == 200
        assert "slideshow" in result.json()
```

---

## 五、性能基准测试

### 5.1 基准定义

```python
@dataclass
class Benchmark:
    """性能基准"""
    name: str
    description: str

    # 指标
    metric: str  # response_time, throughput, memory
    baseline: float
    tolerance: float  # 允许偏差百分比

    # 测试配置
    iterations: int = 100
    warmup: int = 10
    concurrent: int = 1

    # 测试函数
    test_func: Callable = None

class BenchmarkRunner:
    """基准测试运行器"""

    def __init__(self):
        self.benchmarks: List[Benchmark] = []
        self.results: Dict[str, BenchmarkResult] = {}

    def add_benchmark(self, benchmark: Benchmark):
        self.benchmarks.append(benchmark)

    async def run_all(self) -> Dict[str, BenchmarkResult]:
        """运行所有基准测试"""
        for benchmark in self.benchmarks:
            result = await self._run_benchmark(benchmark)
            self.results[benchmark.name] = result
        return self.results

    async def _run_benchmark(self, benchmark: Benchmark) -> 'BenchmarkResult':
        """运行单个基准测试"""
        measurements = []

        # Warmup
        for _ in range(benchmark.warmup):
            await benchmark.test_func()

        # 实际测试
        for _ in range(benchmark.iterations):
            start = time.perf_counter()
            await benchmark.test_func()
            elapsed = time.perf_counter() - start
            measurements.append(elapsed)

        # 计算统计
        avg = sum(measurements) / len(measurements)
        p50 = sorted(measurements)[len(measurements) // 2]
        p95 = sorted(measurements)[int(len(measurements) * 0.95)]
        p99 = sorted(measurements)[int(len(measurements) * 0.99)]

        # 判断是否通过
        deviation = (avg - benchmark.baseline) / benchmark.baseline
        passed = abs(deviation) <= benchmark.tolerance

        return BenchmarkResult(
            benchmark=benchmark.name,
            passed=passed,
            baseline=benchmark.baseline,
            actual=avg,
            deviation=deviation,
            stats={
                "avg": avg,
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "min": min(measurements),
                "max": max(measurements)
            }
        )

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    benchmark: str
    passed: bool
    baseline: float
    actual: float
    deviation: float
    stats: dict
```

### 5.2 基准测试用例

```python
# 定义基准测试

async def benchmark_simple_request():
    """简单请求基准"""
    client = RequestClient()
    await client.get("https://httpbin.org/get")

async def benchmark_page_parsing():
    """页面解析基准"""
    parser = PageParser()
    html = "<html>...</html>"  # 标准测试HTML
    parser.parse(html, selectors={"title": "h1"})

benchmarks = [
    Benchmark(
        name="simple_request",
        description="简单HTTP请求响应时间",
        metric="response_time",
        baseline=0.5,  # 500ms
        tolerance=0.2,  # 允许20%偏差
        iterations=50,
        test_func=benchmark_simple_request
    ),
    Benchmark(
        name="page_parsing",
        description="页面解析时间",
        metric="response_time",
        baseline=0.01,  # 10ms
        tolerance=0.3,
        iterations=100,
        test_func=benchmark_page_parsing
    )
]

# 运行
runner = BenchmarkRunner()
for b in benchmarks:
    runner.add_benchmark(b)

results = await runner.run_all()
```

---

## 六、回归检查

### 6.1 回归测试套件

```python
class RegressionTestSuite:
    """回归测试套件"""

    def __init__(self):
        self.test_cases: List[TestCase] = []
        self.baseline_results: Dict[str, Any] = {}

    def add_test(self, test_case: TestCase):
        """添加测试用例"""
        self.test_cases.append(test_case)

    def load_baseline(self, path: str):
        """加载基线结果"""
        with open(path) as f:
            self.baseline_results = json.load(f)

    def save_baseline(self, path: str, results: Dict[str, Any]):
        """保存基线结果"""
        with open(path, 'w') as f:
            json.dump(results, f, indent=2)

    async def run(self) -> 'RegressionReport':
        """运行回归测试"""
        results = []
        regressions = []

        for test in self.test_cases:
            # 运行测试
            result = await self._run_test(test)

            # 对比基线
            baseline = self.baseline_results.get(test.id)
            if baseline:
                regression = self._check_regression(result, baseline)
                if regression:
                    regressions.append(regression)

            results.append(result)

        return RegressionReport(
            total=len(self.test_cases),
            passed=len([r for r in results if r.passed]),
            failed=len([r for r in results if not r.passed]),
            regressions=regressions,
            results=results
        )

    def _check_regression(
        self,
        current: 'TestResult',
        baseline: dict
    ) -> Optional['Regression']:
        """检查回归"""
        # 功能回归: 之前通过现在失败
        if baseline.get("passed") and not current.passed:
            return Regression(
                test_id=current.test_id,
                type="functional",
                message=f"测试从 PASS 变为 FAIL",
                baseline=baseline,
                current=current.__dict__
            )

        # 性能回归: 性能下降超过阈值
        if "duration" in baseline:
            deviation = (current.duration - baseline["duration"]) / baseline["duration"]
            if deviation > 0.2:  # 20% 性能下降
                return Regression(
                    test_id=current.test_id,
                    type="performance",
                    message=f"性能下降 {deviation:.1%}",
                    baseline=baseline,
                    current=current.__dict__
                )

        return None

@dataclass
class Regression:
    """回归问题"""
    test_id: str
    type: str  # functional, performance
    message: str
    baseline: dict
    current: dict

@dataclass
class RegressionReport:
    """回归报告"""
    total: int
    passed: int
    failed: int
    regressions: List[Regression]
    results: List['TestResult']

    def has_blocking_regressions(self) -> bool:
        """是否有阻塞性回归"""
        return any(r.type == "functional" for r in self.regressions)
```

---

## 七、红线检查

### 7.1 红线规则

```python
class RedLineChecker:
    """红线检查器"""

    RULES = [
        # 安全红线
        {
            "id": "SEC-001",
            "name": "禁止硬编码凭据",
            "pattern": r"(password|secret|api_key)\s*=\s*['\"][^'\"]+['\"]",
            "severity": "critical",
            "message": "检测到硬编码凭据"
        },
        {
            "id": "SEC-002",
            "name": "禁止访问内网地址",
            "pattern": r"(localhost|127\.0\.0\.1|192\.168\.|10\.|172\.(1[6-9]|2|3[01]))",
            "severity": "critical",
            "message": "检测到内网地址访问"
        },

        # 数据红线
        {
            "id": "DATA-001",
            "name": "禁止伪造数据",
            "check": "fake_data_check",
            "severity": "critical",
            "message": "检测到数据伪造行为"
        },
        {
            "id": "DATA-002",
            "name": "禁止忽略错误",
            "pattern": r"except:\s*pass",
            "severity": "high",
            "message": "检测到空异常处理"
        },

        # 行为红线
        {
            "id": "BEHAV-001",
            "name": "禁止无限重试",
            "check": "infinite_retry_check",
            "severity": "high",
            "message": "检测到可能的无限重试"
        },
        {
            "id": "BEHAV-002",
            "name": "禁止过高并发",
            "check": "high_concurrency_check",
            "severity": "high",
            "message": "并发数超过安全阈值"
        }
    ]

    def check_code(self, code: str) -> List['RedLineViolation']:
        """检查代码"""
        violations = []

        for rule in self.RULES:
            if "pattern" in rule:
                if re.search(rule["pattern"], code):
                    violations.append(RedLineViolation(
                        rule_id=rule["id"],
                        rule_name=rule["name"],
                        severity=rule["severity"],
                        message=rule["message"]
                    ))

        return violations

    def check_runtime(self, context: dict) -> List['RedLineViolation']:
        """运行时检查"""
        violations = []

        # 检查并发数
        if context.get("concurrency", 0) > 50:
            violations.append(RedLineViolation(
                rule_id="BEHAV-002",
                rule_name="禁止过高并发",
                severity="high",
                message=f"并发数 {context['concurrency']} 超过阈值 50"
            ))

        # 检查请求频率
        if context.get("requests_per_second", 0) > 10:
            violations.append(RedLineViolation(
                rule_id="BEHAV-003",
                rule_name="请求频率过高",
                severity="high",
                message=f"请求频率 {context['requests_per_second']}/s 超过阈值"
            ))

        return violations

@dataclass
class RedLineViolation:
    """红线违规"""
    rule_id: str
    rule_name: str
    severity: str  # critical, high, medium
    message: str
    location: str = ""
```

### 7.2 CI/CD 门禁

```python
class CIGate:
    """CI 门禁"""

    def __init__(self):
        self.test_runner = TestRunner()
        self.benchmark_runner = BenchmarkRunner()
        self.regression_suite = RegressionTestSuite()
        self.red_line_checker = RedLineChecker()

    async def run_gate(self, commit_info: dict) -> 'GateResult':
        """运行门禁检查"""
        results = {
            "unit_tests": None,
            "integration_tests": None,
            "benchmarks": None,
            "regression": None,
            "red_lines": None
        }

        passed = True
        blocking_issues = []

        # 1. 红线检查 (最先)
        red_line_violations = self.red_line_checker.check_code(
            commit_info.get("changed_code", "")
        )
        if any(v.severity == "critical" for v in red_line_violations):
            passed = False
            blocking_issues.append("红线违规: " + red_line_violations[0].message)
        results["red_lines"] = red_line_violations

        # 2. 单元测试
        unit_result = await self.test_runner.run_suite("unit")
        if unit_result.failed > 0:
            passed = False
            blocking_issues.append(f"单元测试失败: {unit_result.failed} 个")
        results["unit_tests"] = unit_result

        # 3. 集成测试
        integration_result = await self.test_runner.run_suite("integration")
        if integration_result.failed > 0:
            passed = False
            blocking_issues.append(f"集成测试失败: {integration_result.failed} 个")
        results["integration_tests"] = integration_result

        # 4. 回归测试
        regression_result = await self.regression_suite.run()
        if regression_result.has_blocking_regressions():
            passed = False
            blocking_issues.append("检测到功能回归")
        results["regression"] = regression_result

        # 5. 性能基准 (警告，不阻塞)
        benchmark_result = await self.benchmark_runner.run_all()
        results["benchmarks"] = benchmark_result

        return GateResult(
            passed=passed,
            blocking_issues=blocking_issues,
            results=results,
            commit=commit_info.get("commit_id")
        )

@dataclass
class GateResult:
    """门禁结果"""
    passed: bool
    blocking_issues: List[str]
    results: dict
    commit: str

    def to_report(self) -> str:
        """生成报告"""
        lines = [
            f"## CI 门禁报告",
            f"Commit: {self.commit}",
            f"状态: {'✅ 通过' if self.passed else '❌ 失败'}",
            ""
        ]

        if self.blocking_issues:
            lines.append("### 阻塞问题")
            for issue in self.blocking_issues:
                lines.append(f"- {issue}")

        return "\n".join(lines)
```

---

## 八、诊断日志

```
# 测试执行
[TEST] 开始测试套件: {suite_name}
[TEST] 运行用例: {test_id} - {test_name}
[TEST] 用例结果: {test_id} - {PASS|FAIL} ({duration}ms)
[TEST] 套件完成: passed={passed}, failed={failed}

# 基准测试
[BENCH] 开始基准: {benchmark_name}
[BENCH] 基准结果: {benchmark_name} - {PASS|FAIL}
[BENCH] 偏差: baseline={baseline}ms, actual={actual}ms, deviation={deviation}%

# 回归检查
[REGRESS] 检测到回归: {test_id}
[REGRESS] 类型: {functional|performance}
[REGRESS] 详情: {message}

# 红线检查
[REDLINE] 违规: {rule_id} - {rule_name}
[REDLINE] 严重性: {severity}
[REDLINE] 位置: {location}

# CI 门禁
[GATE] 门禁开始: commit={commit_id}
[GATE] 门禁结果: {PASS|FAIL}
[GATE] 阻塞问题: {issues}
```

---

## 九、配置选项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `test.parallel` | bool | true | 并行执行测试 |
| `test.timeout` | int | 60 | 单个测试超时(秒) |
| `test.retries` | int | 0 | 失败重试次数 |
| `benchmark.iterations` | int | 100 | 基准测试迭代次数 |
| `benchmark.tolerance` | float | 0.2 | 性能偏差容忍度 |
| `gate.block_on_regression` | bool | true | 回归是否阻塞 |
| `gate.block_on_red_line` | bool | true | 红线违规是否阻塞 |

---

## 变更历史

| 版本 | 日期 | 变更类型 | 说明 |
|------|------|----------|------|
| 1.0.0 | 2026-01-27 | initial | 初始版本 |

---

## 关联模块

- **21-anti-patterns.md** - 红线规则来源
- **14-monitoring.md** - 测试指标监控
- **17-feedback-loop.md** - 测试结果反馈
