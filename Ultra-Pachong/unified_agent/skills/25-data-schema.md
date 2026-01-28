---
skill_id: "25-data-schema"
name: "数据Schema质量"
version: "1.0.0"
status: "stable"                    # draft | beta | stable | deprecated
implementation_status: "partial"    # none | partial | complete
difficulty: 3
category: "infrastructure"

description: "定义数据结构、校验规则、增量去重和落库适配"

triggers:
  - "定义采集数据结构时"
  - "数据入库前校验时"
  - "增量更新时"

dependencies:
  required:
    - skill: "05-parsing"
      reason: "数据提取后进行校验"
  optional:
    - skill: "06-storage"
      reason: "校验后存储"

external_dependencies:
  required: []
  optional:
    - name: "pydantic"
      version: ">=2.0.0"
      condition: "使用Pydantic校验"
      type: "python_package"
      install: "pip install pydantic"
    - name: "jsonschema"
      version: ">=4.0.0"
      condition: "使用JSON Schema校验"
      type: "python_package"
      install: "pip install jsonschema"

inputs:
  - name: "data"
    type: "dict | list"
    required: true
  - name: "schema"
    type: "Schema"
    required: true

outputs:
  - name: "validated_data"
    type: "ValidatedData"

slo:
  - metric: "校验准确率"
    target: ">= 99%"
    scope: "符合schema的数据"
    degradation: "返回原始数据+警告"
  - metric: "去重准确率"
    target: ">= 99.9%"
    scope: "已定义唯一键"
    degradation: "保守去重(宁可重复)"

tags: ["Schema", "数据质量", "去重", "校验"]
---

# 25-data-schema.md - 数据 Schema 与质量管理

## 模块目标

| 目标 | SLO | 适用范围 | 降级策略 |
|------|-----|----------|----------|
| 数据结构一致 | Schema 符合率 ≥99% | 已定义 Schema | 返回原始+警告 |
| 数据完整性 | 必填字段完整率 ≥98% | 核心字段 | 标记 partial |
| 数据去重 | 去重准确率 ≥99.9% | 有唯一键 | 保守策略 |
| 数据质量 | 异常检出率 ≥95% | 可检测异常 | 人工审核 |

---

## 一、Schema 定义

### 1.1 Schema 结构

```python
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional, Callable
from enum import Enum

class FieldType(Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"
    ARRAY = "array"
    OBJECT = "object"
    ANY = "any"

class ValidationLevel(Enum):
    STRICT = "strict"     # 严格: 不符合则拒绝
    NORMAL = "normal"     # 正常: 不符合则警告
    LENIENT = "lenient"   # 宽松: 尽量转换

@dataclass
class FieldSchema:
    """字段Schema定义"""
    name: str
    type: FieldType
    required: bool = True
    default: Any = None
    description: str = ""

    # 验证规则
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None  # 正则
    enum: Optional[List[Any]] = None  # 枚举值

    # 转换规则
    transform: Optional[Callable] = None  # 转换函数
    normalize: bool = True  # 是否规范化

    # 质量规则
    unique: bool = False  # 是否唯一
    index: bool = False   # 是否索引

@dataclass
class DataSchema:
    """数据Schema定义"""
    name: str
    version: str
    description: str = ""

    fields: List[FieldSchema] = field(default_factory=list)

    # 记录级规则
    unique_keys: List[str] = field(default_factory=list)  # 唯一键组合
    required_fields: List[str] = field(default_factory=list)

    # 校验级别
    validation_level: ValidationLevel = ValidationLevel.NORMAL

    # 元数据
    created_at: str = ""
    updated_at: str = ""
```

### 1.2 Schema 示例

```python
# 商品数据 Schema
product_schema = DataSchema(
    name="product",
    version="1.0.0",
    description="电商商品数据结构",

    fields=[
        FieldSchema(
            name="sku_id",
            type=FieldType.STRING,
            required=True,
            unique=True,
            pattern=r"^\d{8,15}$",
            description="商品SKU编号"
        ),
        FieldSchema(
            name="title",
            type=FieldType.STRING,
            required=True,
            min_length=2,
            max_length=200,
            transform=lambda x: x.strip(),
            description="商品标题"
        ),
        FieldSchema(
            name="price",
            type=FieldType.FLOAT,
            required=True,
            min_value=0.01,
            max_value=9999999,
            description="商品价格"
        ),
        FieldSchema(
            name="original_price",
            type=FieldType.FLOAT,
            required=False,
            min_value=0,
            description="原价"
        ),
        FieldSchema(
            name="stock",
            type=FieldType.INTEGER,
            required=False,
            min_value=0,
            default=0,
            description="库存数量"
        ),
        FieldSchema(
            name="category",
            type=FieldType.STRING,
            required=True,
            description="商品分类"
        ),
        FieldSchema(
            name="brand",
            type=FieldType.STRING,
            required=False,
            description="品牌"
        ),
        FieldSchema(
            name="images",
            type=FieldType.ARRAY,
            required=False,
            default=[],
            description="商品图片URL列表"
        ),
        FieldSchema(
            name="url",
            type=FieldType.URL,
            required=True,
            description="商品页面URL"
        ),
        FieldSchema(
            name="scraped_at",
            type=FieldType.DATETIME,
            required=True,
            description="采集时间"
        )
    ],

    unique_keys=["sku_id"],
    required_fields=["sku_id", "title", "price", "url"],
    validation_level=ValidationLevel.NORMAL
)
```

### 1.3 Schema 注册表

```python
class SchemaRegistry:
    """Schema 注册表"""

    def __init__(self):
        self._schemas: Dict[str, Dict[str, DataSchema]] = {}
        # {schema_name: {version: schema}}

    def register(self, schema: DataSchema):
        """注册 Schema"""
        if schema.name not in self._schemas:
            self._schemas[schema.name] = {}

        self._schemas[schema.name][schema.version] = schema

    def get(
        self,
        name: str,
        version: str = "latest"
    ) -> Optional[DataSchema]:
        """获取 Schema"""
        if name not in self._schemas:
            return None

        versions = self._schemas[name]

        if version == "latest":
            latest = max(versions.keys())
            return versions[latest]

        return versions.get(version)

    def list_schemas(self) -> List[str]:
        """列出所有 Schema"""
        return list(self._schemas.keys())

    def export_json_schema(self, name: str, version: str = "latest") -> dict:
        """导出为 JSON Schema 格式"""
        schema = self.get(name, version)
        if not schema:
            return {}

        return self._to_json_schema(schema)

    def _to_json_schema(self, schema: DataSchema) -> dict:
        """转换为 JSON Schema"""
        properties = {}
        required = []

        for field in schema.fields:
            properties[field.name] = self._field_to_json_schema(field)
            if field.required:
                required.append(field.name)

        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": schema.name,
            "description": schema.description,
            "type": "object",
            "properties": properties,
            "required": required
        }

    def _field_to_json_schema(self, field: FieldSchema) -> dict:
        """字段转 JSON Schema"""
        type_mapping = {
            FieldType.STRING: "string",
            FieldType.INTEGER: "integer",
            FieldType.FLOAT: "number",
            FieldType.BOOLEAN: "boolean",
            FieldType.ARRAY: "array",
            FieldType.OBJECT: "object",
        }

        result = {
            "type": type_mapping.get(field.type, "string"),
            "description": field.description
        }

        if field.min_length:
            result["minLength"] = field.min_length
        if field.max_length:
            result["maxLength"] = field.max_length
        if field.min_value is not None:
            result["minimum"] = field.min_value
        if field.max_value is not None:
            result["maximum"] = field.max_value
        if field.pattern:
            result["pattern"] = field.pattern
        if field.enum:
            result["enum"] = field.enum
        if field.type == FieldType.URL:
            result["format"] = "uri"
        if field.type == FieldType.EMAIL:
            result["format"] = "email"
        if field.type == FieldType.DATETIME:
            result["format"] = "date-time"

        return result

# 全局注册表
schema_registry = SchemaRegistry()
schema_registry.register(product_schema)
```

---

## 二、数据校验

### 2.1 校验器

```python
from dataclasses import dataclass
from typing import List, Tuple
import re
from datetime import datetime

@dataclass
class ValidationError:
    """校验错误"""
    field: str
    error_type: str
    message: str
    value: Any = None
    suggestion: str = ""

@dataclass
class ValidationResult:
    """校验结果"""
    valid: bool
    data: Optional[dict] = None
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

class DataValidator:
    """数据校验器"""

    def validate(
        self,
        data: dict,
        schema: DataSchema
    ) -> ValidationResult:
        """校验单条数据"""
        errors = []
        warnings = []
        validated_data = {}

        # 校验每个字段
        for field_schema in schema.fields:
            field_name = field_schema.name
            value = data.get(field_name)

            # 检查必填
            if field_schema.required and value is None:
                if field_schema.default is not None:
                    value = field_schema.default
                else:
                    errors.append(ValidationError(
                        field=field_name,
                        error_type="REQUIRED",
                        message=f"必填字段 '{field_name}' 缺失",
                        suggestion="请确保数据源包含此字段"
                    ))
                    continue

            # 空值处理
            if value is None:
                validated_data[field_name] = field_schema.default
                continue

            # 类型校验和转换
            try:
                validated_value = self._validate_and_transform(
                    value, field_schema, schema.validation_level
                )
                validated_data[field_name] = validated_value
            except ValidationError as e:
                if schema.validation_level == ValidationLevel.STRICT:
                    errors.append(e)
                else:
                    warnings.append(e)
                    validated_data[field_name] = value  # 保留原值

        # 额外字段处理
        for key in data.keys():
            if key not in [f.name for f in schema.fields]:
                if schema.validation_level == ValidationLevel.STRICT:
                    warnings.append(ValidationError(
                        field=key,
                        error_type="UNKNOWN_FIELD",
                        message=f"未知字段 '{key}'"
                    ))
                else:
                    validated_data[key] = data[key]  # 保留额外字段

        return ValidationResult(
            valid=len(errors) == 0,
            data=validated_data if len(errors) == 0 else None,
            errors=errors,
            warnings=warnings,
            stats={
                "total_fields": len(schema.fields),
                "valid_fields": len(validated_data),
                "error_count": len(errors),
                "warning_count": len(warnings)
            }
        )

    def _validate_and_transform(
        self,
        value: Any,
        field: FieldSchema,
        level: ValidationLevel
    ) -> Any:
        """校验并转换字段值"""

        # 类型转换
        try:
            value = self._convert_type(value, field.type)
        except (ValueError, TypeError) as e:
            raise ValidationError(
                field=field.name,
                error_type="TYPE_ERROR",
                message=f"类型转换失败: {e}",
                value=value
            )

        # 自定义转换
        if field.transform:
            value = field.transform(value)

        # 规范化
        if field.normalize and isinstance(value, str):
            value = value.strip()

        # 长度校验
        if field.type == FieldType.STRING:
            if field.min_length and len(value) < field.min_length:
                raise ValidationError(
                    field=field.name,
                    error_type="MIN_LENGTH",
                    message=f"长度不足: {len(value)} < {field.min_length}",
                    value=value
                )
            if field.max_length and len(value) > field.max_length:
                if level == ValidationLevel.LENIENT:
                    value = value[:field.max_length]
                else:
                    raise ValidationError(
                        field=field.name,
                        error_type="MAX_LENGTH",
                        message=f"长度超出: {len(value)} > {field.max_length}",
                        value=value
                    )

        # 数值范围校验
        if field.type in [FieldType.INTEGER, FieldType.FLOAT]:
            if field.min_value is not None and value < field.min_value:
                raise ValidationError(
                    field=field.name,
                    error_type="MIN_VALUE",
                    message=f"值过小: {value} < {field.min_value}",
                    value=value
                )
            if field.max_value is not None and value > field.max_value:
                raise ValidationError(
                    field=field.name,
                    error_type="MAX_VALUE",
                    message=f"值过大: {value} > {field.max_value}",
                    value=value
                )

        # 正则校验
        if field.pattern and isinstance(value, str):
            if not re.match(field.pattern, value):
                raise ValidationError(
                    field=field.name,
                    error_type="PATTERN",
                    message=f"不匹配模式: {field.pattern}",
                    value=value
                )

        # 枚举校验
        if field.enum and value not in field.enum:
            raise ValidationError(
                field=field.name,
                error_type="ENUM",
                message=f"不在允许值列表中: {field.enum}",
                value=value
            )

        return value

    def _convert_type(self, value: Any, target_type: FieldType) -> Any:
        """类型转换"""
        if target_type == FieldType.STRING:
            return str(value)
        elif target_type == FieldType.INTEGER:
            return int(float(value))
        elif target_type == FieldType.FLOAT:
            return float(value)
        elif target_type == FieldType.BOOLEAN:
            if isinstance(value, bool):
                return value
            return str(value).lower() in ('true', '1', 'yes')
        elif target_type == FieldType.DATETIME:
            if isinstance(value, datetime):
                return value.isoformat()
            return value  # 保持原始格式
        elif target_type == FieldType.URL:
            if not value.startswith(('http://', 'https://')):
                raise ValueError("Invalid URL")
            return value
        else:
            return value

    def validate_batch(
        self,
        data_list: List[dict],
        schema: DataSchema
    ) -> Tuple[List[dict], List[dict], dict]:
        """批量校验"""
        valid_data = []
        invalid_data = []
        stats = {
            "total": len(data_list),
            "valid": 0,
            "invalid": 0,
            "error_types": {}
        }

        for data in data_list:
            result = self.validate(data, schema)

            if result.valid:
                valid_data.append(result.data)
                stats["valid"] += 1
            else:
                invalid_data.append({
                    "data": data,
                    "errors": [e.__dict__ for e in result.errors]
                })
                stats["invalid"] += 1

                # 统计错误类型
                for error in result.errors:
                    error_type = error.error_type
                    stats["error_types"][error_type] = \
                        stats["error_types"].get(error_type, 0) + 1

        return valid_data, invalid_data, stats
```

---

## 三、数据去重

### 3.1 去重策略

```python
from hashlib import md5
from typing import Set, Dict
import json

class DeduplicationStrategy(Enum):
    EXACT = "exact"           # 完全匹配
    KEY_BASED = "key_based"   # 基于唯一键
    CONTENT_HASH = "content"  # 内容哈希
    FUZZY = "fuzzy"           # 模糊匹配

class DataDeduplicator:
    """数据去重器"""

    def __init__(
        self,
        strategy: DeduplicationStrategy = DeduplicationStrategy.KEY_BASED,
        unique_keys: List[str] = None
    ):
        self.strategy = strategy
        self.unique_keys = unique_keys or []
        self._seen: Set[str] = set()
        self._duplicates: List[dict] = []

    def is_duplicate(self, data: dict) -> bool:
        """检查是否重复"""
        key = self._generate_key(data)

        if key in self._seen:
            self._duplicates.append(data)
            return True

        self._seen.add(key)
        return False

    def _generate_key(self, data: dict) -> str:
        """生成去重键"""
        if self.strategy == DeduplicationStrategy.EXACT:
            # 完整数据哈希
            return md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

        elif self.strategy == DeduplicationStrategy.KEY_BASED:
            # 基于唯一键
            key_values = [str(data.get(k, "")) for k in self.unique_keys]
            return "|".join(key_values)

        elif self.strategy == DeduplicationStrategy.CONTENT_HASH:
            # 内容哈希 (排除时间戳等变化字段)
            content = {k: v for k, v in data.items()
                      if k not in ["scraped_at", "updated_at", "id"]}
            return md5(json.dumps(content, sort_keys=True).encode()).hexdigest()

        else:
            return md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def deduplicate(
        self,
        data_list: List[dict]
    ) -> Tuple[List[dict], List[dict], dict]:
        """批量去重"""
        unique_data = []
        duplicates = []

        for data in data_list:
            if not self.is_duplicate(data):
                unique_data.append(data)
            else:
                duplicates.append(data)

        stats = {
            "total": len(data_list),
            "unique": len(unique_data),
            "duplicates": len(duplicates),
            "duplicate_rate": len(duplicates) / len(data_list) if data_list else 0
        }

        return unique_data, duplicates, stats

    def reset(self):
        """重置状态"""
        self._seen.clear()
        self._duplicates.clear()

    def get_duplicate_count(self) -> int:
        """获取重复数量"""
        return len(self._duplicates)
```

### 3.2 增量更新

```python
class IncrementalUpdater:
    """增量更新器"""

    def __init__(self, storage, unique_keys: List[str]):
        self.storage = storage
        self.unique_keys = unique_keys

    async def update(
        self,
        new_data: List[dict],
        strategy: str = "upsert"
    ) -> dict:
        """
        增量更新策略:
        - upsert: 存在则更新，不存在则插入
        - insert_only: 只插入新数据
        - replace: 完全替换
        """
        stats = {
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "errors": 0
        }

        for data in new_data:
            key = self._get_key(data)

            try:
                existing = await self.storage.get(key)

                if existing is None:
                    # 新数据
                    await self.storage.insert(data)
                    stats["inserted"] += 1

                elif strategy == "upsert":
                    # 检查是否有变化
                    if self._has_changes(existing, data):
                        await self.storage.update(key, data)
                        stats["updated"] += 1
                    else:
                        stats["unchanged"] += 1

                elif strategy == "insert_only":
                    stats["unchanged"] += 1

            except Exception as e:
                stats["errors"] += 1

        return stats

    def _get_key(self, data: dict) -> str:
        """获取唯一键"""
        return "|".join(str(data.get(k, "")) for k in self.unique_keys)

    def _has_changes(self, old: dict, new: dict) -> bool:
        """检查是否有变化"""
        # 排除时间戳字段比较
        exclude_fields = {"scraped_at", "updated_at", "created_at"}

        for key, new_value in new.items():
            if key in exclude_fields:
                continue
            if old.get(key) != new_value:
                return True

        return False
```

---

## 四、数据质量检查

### 4.1 质量规则

```python
class QualityChecker:
    """数据质量检查器"""

    def __init__(self):
        self.rules: List[QualityRule] = []

    def add_rule(self, rule: 'QualityRule'):
        """添加规则"""
        self.rules.append(rule)

    def check(self, data: dict, schema: DataSchema) -> QualityReport:
        """执行质量检查"""
        issues = []
        score = 100

        for rule in self.rules:
            result = rule.check(data, schema)
            if not result.passed:
                issues.append(result)
                score -= result.severity * 5  # 每个问题扣分

        return QualityReport(
            score=max(0, score),
            issues=issues,
            passed=len(issues) == 0
        )

@dataclass
class QualityRule:
    """质量规则"""
    name: str
    description: str
    severity: int  # 1-5

    def check(self, data: dict, schema: DataSchema) -> 'QualityResult':
        raise NotImplementedError

@dataclass
class QualityResult:
    """质量检查结果"""
    rule: str
    passed: bool
    severity: int
    message: str = ""
    field: str = ""

@dataclass
class QualityReport:
    """质量报告"""
    score: int
    issues: List[QualityResult]
    passed: bool


# 预定义规则

class CompletenessRule(QualityRule):
    """完整性规则"""
    def __init__(self, threshold: float = 0.9):
        super().__init__(
            name="completeness",
            description="必填字段完整性",
            severity=3
        )
        self.threshold = threshold

    def check(self, data: dict, schema: DataSchema) -> QualityResult:
        required_fields = schema.required_fields
        filled = sum(1 for f in required_fields if data.get(f) is not None)
        ratio = filled / len(required_fields) if required_fields else 1

        return QualityResult(
            rule=self.name,
            passed=ratio >= self.threshold,
            severity=self.severity,
            message=f"完整率: {ratio:.1%} (阈值: {self.threshold:.1%})"
        )

class AnomalyRule(QualityRule):
    """异常检测规则"""
    def __init__(self, field: str, min_val: float, max_val: float):
        super().__init__(
            name=f"anomaly_{field}",
            description=f"{field} 异常值检测",
            severity=2
        )
        self.field = field
        self.min_val = min_val
        self.max_val = max_val

    def check(self, data: dict, schema: DataSchema) -> QualityResult:
        value = data.get(self.field)

        if value is None:
            return QualityResult(
                rule=self.name,
                passed=True,
                severity=self.severity
            )

        try:
            num_value = float(value)
            passed = self.min_val <= num_value <= self.max_val

            return QualityResult(
                rule=self.name,
                passed=passed,
                severity=self.severity,
                field=self.field,
                message=f"值 {num_value} 超出范围 [{self.min_val}, {self.max_val}]" if not passed else ""
            )
        except (ValueError, TypeError):
            return QualityResult(
                rule=self.name,
                passed=False,
                severity=self.severity,
                field=self.field,
                message=f"无法转换为数值: {value}"
            )

class ConsistencyRule(QualityRule):
    """一致性规则"""
    def __init__(self, field1: str, field2: str, relation: str):
        super().__init__(
            name=f"consistency_{field1}_{field2}",
            description=f"{field1} 与 {field2} 的一致性",
            severity=2
        )
        self.field1 = field1
        self.field2 = field2
        self.relation = relation  # ">=", "<=", "=="

    def check(self, data: dict, schema: DataSchema) -> QualityResult:
        val1 = data.get(self.field1)
        val2 = data.get(self.field2)

        if val1 is None or val2 is None:
            return QualityResult(rule=self.name, passed=True, severity=self.severity)

        try:
            num1, num2 = float(val1), float(val2)

            if self.relation == ">=":
                passed = num1 >= num2
            elif self.relation == "<=":
                passed = num1 <= num2
            else:
                passed = num1 == num2

            return QualityResult(
                rule=self.name,
                passed=passed,
                severity=self.severity,
                message=f"{self.field1}({num1}) 应 {self.relation} {self.field2}({num2})" if not passed else ""
            )
        except (ValueError, TypeError):
            return QualityResult(rule=self.name, passed=True, severity=self.severity)


# 使用示例
quality_checker = QualityChecker()
quality_checker.add_rule(CompletenessRule(threshold=0.95))
quality_checker.add_rule(AnomalyRule("price", 0.01, 999999))
quality_checker.add_rule(ConsistencyRule("price", "original_price", "<="))
```

---

## 五、落库适配器

### 5.1 适配器接口

```python
from abc import ABC, abstractmethod

class StorageAdapter(ABC):
    """存储适配器接口"""

    @abstractmethod
    async def insert(self, data: dict) -> str:
        """插入数据，返回ID"""
        pass

    @abstractmethod
    async def insert_batch(self, data_list: List[dict]) -> List[str]:
        """批量插入"""
        pass

    @abstractmethod
    async def update(self, key: str, data: dict) -> bool:
        """更新数据"""
        pass

    @abstractmethod
    async def get(self, key: str) -> Optional[dict]:
        """获取数据"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除数据"""
        pass

    @abstractmethod
    async def query(self, filters: dict, limit: int = 100) -> List[dict]:
        """查询数据"""
        pass
```

### 5.2 JSON 文件适配器

```python
import json
import os
from datetime import datetime

class JSONFileAdapter(StorageAdapter):
    """JSON文件存储适配器"""

    def __init__(self, file_path: str, key_field: str = "id"):
        self.file_path = file_path
        self.key_field = key_field
        self._data: Dict[str, dict] = {}
        self._load()

    def _load(self):
        """加载数据"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data_list = json.load(f)
                for item in data_list:
                    key = item.get(self.key_field)
                    if key:
                        self._data[str(key)] = item

    def _save(self):
        """保存数据"""
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(list(self._data.values()), f, ensure_ascii=False, indent=2)

    async def insert(self, data: dict) -> str:
        key = data.get(self.key_field) or str(len(self._data))
        data[self.key_field] = key
        data["created_at"] = datetime.now().isoformat()
        self._data[str(key)] = data
        self._save()
        return str(key)

    async def insert_batch(self, data_list: List[dict]) -> List[str]:
        ids = []
        for data in data_list:
            id = await self.insert(data)
            ids.append(id)
        return ids

    async def update(self, key: str, data: dict) -> bool:
        if key not in self._data:
            return False
        data["updated_at"] = datetime.now().isoformat()
        self._data[key].update(data)
        self._save()
        return True

    async def get(self, key: str) -> Optional[dict]:
        return self._data.get(key)

    async def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            self._save()
            return True
        return False

    async def query(self, filters: dict, limit: int = 100) -> List[dict]:
        results = []
        for data in self._data.values():
            match = all(data.get(k) == v for k, v in filters.items())
            if match:
                results.append(data)
                if len(results) >= limit:
                    break
        return results
```

### 5.3 SQLite 适配器

```python
import sqlite3
import json

class SQLiteAdapter(StorageAdapter):
    """SQLite存储适配器"""

    def __init__(self, db_path: str, table_name: str, schema: DataSchema):
        self.db_path = db_path
        self.table_name = table_name
        self.schema = schema
        self._init_table()

    def _init_table(self):
        """初始化表"""
        columns = []
        for field in self.schema.fields:
            col_type = self._get_sqlite_type(field.type)
            col_def = f"{field.name} {col_type}"
            if field.unique:
                col_def += " UNIQUE"
            columns.append(col_def)

        sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            {', '.join(columns)},
            created_at TEXT,
            updated_at TEXT
        )
        """

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(sql)

    def _get_sqlite_type(self, field_type: FieldType) -> str:
        mapping = {
            FieldType.STRING: "TEXT",
            FieldType.INTEGER: "INTEGER",
            FieldType.FLOAT: "REAL",
            FieldType.BOOLEAN: "INTEGER",
            FieldType.DATETIME: "TEXT",
            FieldType.URL: "TEXT",
            FieldType.ARRAY: "TEXT",  # JSON存储
            FieldType.OBJECT: "TEXT",  # JSON存储
        }
        return mapping.get(field_type, "TEXT")

    async def insert(self, data: dict) -> str:
        # 处理复杂类型
        processed = self._process_for_insert(data)

        columns = list(processed.keys())
        placeholders = ["?" for _ in columns]

        sql = f"""
        INSERT INTO {self.table_name} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        """

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(sql, list(processed.values()))
            return str(cursor.lastrowid)

    def _process_for_insert(self, data: dict) -> dict:
        """处理数据以便插入"""
        result = {}
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                result[key] = json.dumps(value, ensure_ascii=False)
            else:
                result[key] = value
        result["created_at"] = datetime.now().isoformat()
        return result

    # ... 其他方法类似实现
```

---

## 六、Skill 交互

### 上游

| 调用者 | 场景 | 传入数据 |
|--------|------|----------|
| 05-parsing | 提取后校验 | raw_data, schema_name |
| 18-brain | 定义输出格式 | schema_definition |

### 下游

| 被调用者 | 场景 | 传出数据 |
|----------|------|----------|
| 06-storage | 存储数据 | validated_data |
| 14-monitoring | 质量指标 | quality_metrics |

---

## 七、诊断日志

```
# Schema 操作
[SCHEMA] 注册 Schema: name={name}, version={version}
[SCHEMA] 获取 Schema: name={name}, version={version}

# 数据校验
[VALIDATE] 开始校验: schema={schema}, count={count}
[VALIDATE] 校验结果: valid={valid}, invalid={invalid}
[VALIDATE] 错误分布: {error_types}

# 去重
[DEDUP] 去重开始: strategy={strategy}, keys={keys}
[DEDUP] 去重结果: total={total}, unique={unique}, duplicates={duplicates}

# 质量检查
[QUALITY] 质量检查: score={score}/100
[QUALITY] 问题: {issues}

# 落库
[STORAGE] 适配器: {adapter_type}
[STORAGE] 操作: {operation}, count={count}, success={success}
```

---

## 八、配置选项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `schema.registry_path` | string | "./schemas" | Schema存储路径 |
| `schema.validation_level` | string | "normal" | 默认校验级别 |
| `dedup.strategy` | string | "key_based" | 默认去重策略 |
| `quality.min_score` | int | 60 | 最低质量分数 |
| `storage.adapter` | string | "json" | 默认存储适配器 |

---

## 变更历史

| 版本 | 日期 | 变更类型 | 说明 |
|------|------|----------|------|
| 1.0.0 | 2026-01-27 | initial | 初始版本 |

---

## 关联模块

- **05-parsing.md** - 数据提取
- **06-storage.md** - 数据存储
- **14-monitoring.md** - 质量监控
- **17-feedback-loop.md** - 质量反馈
