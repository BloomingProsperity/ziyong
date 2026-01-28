"""依赖管理器 - Agent自动检测和安装依赖"""
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum


class DependencyStatus(str, Enum):
    """依赖状态"""
    INSTALLED = "installed"
    MISSING = "missing"
    VERSION_MISMATCH = "version_mismatch"


@dataclass
class Dependency:
    """依赖定义"""
    name: str
    version: str = ""                  # >=1.0.0 格式
    condition: str = ""                # 何时需要
    category: str = "design"           # current/design


# 依赖清单 (与SKILL-MATRIX同步)
DEPENDENCIES = {
    # 当前已实现所需
    "current": [
        Dependency("httpx", ">=0.24.0", "HTTP客户端"),
        Dependency("beautifulsoup4", ">=4.12.0", "HTML解析"),
        Dependency("lxml", ">=5.0.0", "快速解析"),
        Dependency("aiohttp", ">=3.9.0", "异步HTTP"),
    ],
    # 完整设计所需
    "design": [
        Dependency("playwright", ">=1.40.0", "浏览器自动化时"),
        Dependency("ddddocr", ">=1.4.0", "验证码识别时"),
        Dependency("pydantic", ">=2.0.0", "严格校验时"),
        Dependency("cryptography", ">=41.0.0", "加密存储时"),
    ],
}


class DependencyManager:
    """依赖管理器"""

    def check(self, name: str) -> Tuple[DependencyStatus, Optional[str]]:
        """检查单个依赖"""
        try:
            import importlib
            # 处理包名映射 (beautifulsoup4 -> bs4)
            import_name = self._get_import_name(name)
            mod = importlib.import_module(import_name)
            version = getattr(mod, "__version__", "unknown")
            return DependencyStatus.INSTALLED, version
        except ImportError:
            return DependencyStatus.MISSING, None

    def _get_import_name(self, package_name: str) -> str:
        """包名到导入名的映射"""
        mapping = {
            "beautifulsoup4": "bs4",
            "pillow": "PIL",
            "pyyaml": "yaml",
        }
        return mapping.get(package_name.lower(), package_name)

    def check_all(self, category: str = "current") -> Dict[str, DependencyStatus]:
        """检查一组依赖"""
        results = {}
        deps = DEPENDENCIES.get(category, [])
        for dep in deps:
            status, _ = self.check(dep.name)
            results[dep.name] = status
        return results

    def get_missing(self, category: str = "current") -> List[str]:
        """获取缺失的依赖"""
        results = self.check_all(category)
        return [name for name, status in results.items()
                if status == DependencyStatus.MISSING]

    def install(self, name: str, version: str = "") -> bool:
        """安装单个依赖"""
        pkg = f"{name}{version}" if version else name
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", pkg, "-q"
            ])
            return True
        except subprocess.CalledProcessError:
            return False

    def install_missing(self, category: str = "current",
                        auto_confirm: bool = False) -> Dict[str, bool]:
        """安装缺失的依赖"""
        missing = self.get_missing(category)
        if not missing:
            return {}

        if not auto_confirm:
            print(f"需要安装以下依赖: {', '.join(missing)}")
            # 在实际使用中可以询问用户确认

        results = {}
        for name in missing:
            # 找到完整的依赖定义
            dep = self._find_dep(name, category)
            version = dep.version if dep else ""
            results[name] = self.install(name, version)

        return results

    def _find_dep(self, name: str, category: str) -> Optional[Dependency]:
        """查找依赖定义"""
        deps = DEPENDENCIES.get(category, [])
        for dep in deps:
            if dep.name == name:
                return dep
        return None

    def ensure_ready(self, required: List[str] = None) -> bool:
        """确保所需依赖已就绪"""
        if required is None:
            required = [d.name for d in DEPENDENCIES["current"]]

        for name in required:
            status, _ = self.check(name)
            if status == DependencyStatus.MISSING:
                print(f"正在安装 {name}...")
                if not self.install(name):
                    print(f"安装 {name} 失败")
                    return False
        return True

    def report(self) -> str:
        """生成依赖报告"""
        lines = ["# 依赖状态报告\n"]

        for category in ["current", "design"]:
            lines.append(f"\n## {category.upper()}\n")
            deps = DEPENDENCIES.get(category, [])
            for dep in deps:
                status, version = self.check(dep.name)
                icon = "✅" if status == DependencyStatus.INSTALLED else "❌"
                ver_str = f" (v{version})" if version else ""
                lines.append(f"- {icon} {dep.name}{ver_str}")

        return "\n".join(lines)


# 便捷函数
def ensure_deps(required: List[str] = None) -> bool:
    """确保依赖就绪的便捷函数"""
    manager = DependencyManager()
    return manager.ensure_ready(required)


def check_deps() -> Dict[str, DependencyStatus]:
    """检查依赖状态"""
    manager = DependencyManager()
    return manager.check_all("current")
