"""知识存储 - 持久化层"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from .schema import KnowledgeEntry, SiteKnowledge, ErrorKnowledge, KnowledgeType


class KnowledgeStore:
    """知识存储管理器 - 基于文件的简单实现"""

    def __init__(self, base_path: str = "data/knowledge"):
        self.base_path = Path(base_path)
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保目录存在"""
        for subdir in ["sites", "errors", "techniques", "decisions"]:
            (self.base_path / subdir).mkdir(parents=True, exist_ok=True)

    def _get_path(self, entry: KnowledgeEntry) -> Path:
        """获取存储路径"""
        type_dirs = {
            KnowledgeType.SITE: "sites",
            KnowledgeType.ERROR: "errors",
            KnowledgeType.TECHNIQUE: "techniques",
            KnowledgeType.DECISION: "decisions",
        }
        subdir = type_dirs.get(entry.type, "misc")
        filename = entry.id.replace(":", "_").replace("/", "_") + ".json"
        return self.base_path / subdir / filename

    def save(self, entry: KnowledgeEntry) -> bool:
        """保存知识条目"""
        entry.updated_at = datetime.now()
        path = self._get_path(entry)

        data = asdict(entry)
        # 转换datetime为字符串
        data["created_at"] = entry.created_at.isoformat()
        data["updated_at"] = entry.updated_at.isoformat()

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

    def load(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """加载知识条目"""
        # 从id推断类型: "site:jd.com" -> sites/site_jd.com.json
        type_prefix = entry_id.split(":")[0]
        type_dirs = {"site": "sites", "error": "errors", "tech": "techniques"}
        subdir = type_dirs.get(type_prefix, "misc")

        filename = entry_id.replace(":", "_").replace("/", "_") + ".json"
        path = self.base_path / subdir / filename

        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self._dict_to_entry(data)

    def _dict_to_entry(self, data: Dict) -> KnowledgeEntry:
        """字典转知识条目"""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        entry_type = KnowledgeType(data["type"])
        if entry_type == KnowledgeType.SITE:
            return SiteKnowledge(**data)
        elif entry_type == KnowledgeType.ERROR:
            return ErrorKnowledge(**data)
        return KnowledgeEntry(**data)

    def list_sites(self) -> List[str]:
        """列出所有网站知识"""
        sites_dir = self.base_path / "sites"
        return [f.stem.replace("site_", "") for f in sites_dir.glob("*.json")]

    def delete(self, entry_id: str) -> bool:
        """删除知识条目"""
        entry = self.load(entry_id)
        if entry:
            path = self._get_path(entry)
            path.unlink(missing_ok=True)
            return True
        return False
