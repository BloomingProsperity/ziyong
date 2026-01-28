"""MCP类型定义 (来自 23-mcp-protocol)"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from enum import Enum


class ToolResultStatus(str, Enum):
    """工具执行状态"""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


@dataclass
class ToolCall:
    """工具调用请求"""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class ToolResult:
    """工具执行结果 - 标准响应格式"""
    status: ToolResultStatus
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

    # 元数据
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str                          # "string", "integer", "boolean", "object"
    description: str
    required: bool = True
    default: Any = None


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    parameters: List[ToolParameter]
    handler: Callable                  # 实际执行函数

    def to_schema(self) -> Dict:
        """转换为JSON Schema格式"""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }
