"""离线站点词典匹配器：根据 URL 建议中文名与标签。

数据源：``zhmm/resources/site_catalog.json``（随包发行，完全离线）。

典型用法（GUI 层）::

    from zhmm.core.site_catalog import suggest

    s = suggest("https://login.icbc.com.cn/")
    # s.name == "工商银行"
    # s.tags == ["金融", "银行"]

设计约束：
- 单例缓存：词典在首次调用时加载，失败容忍（缺文件 / 损坏）返回空 catalog。
- 不抛异常：调用方拿到 ``SiteSuggestion(name="", tags=[])`` 即意味着「没建议」。
- 匹配策略（按优先级）：
    1. 完整 host 精确匹配（如 ``mail.qq.com``）
    2. 根域名精确匹配（如 ``qq.com``）
    3. 顶级后缀 / 关键字规则兜底（如 ``*.gov.cn`` → ``政务``、
       ``*.edu.cn`` → ``教育``、``*bank*`` → ``金融``）
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zhmm.utils.log import logger
from zhmm.utils.url_util import extract_host, registrable_domain


@dataclass(frozen=True)
class SiteSuggestion:
    """站点建议结果。

    - ``name``: 中文 / 展示名；空串表示无建议
    - ``tags``: 建议标签列表（已去重，顺序稳定）
    - ``matched``: 命中来源，便于调试 / 单测：``"host" | "domain" | "rule" | ""``
    """

    name: str = ""
    tags: list[str] = field(default_factory=list)
    matched: str = ""

    def is_empty(self) -> bool:
        return not self.name and not self.tags


# ----------------------------------------------------------------------
# 词典加载
# ----------------------------------------------------------------------
_CATALOG_CACHE: dict[str, dict[str, Any]] | None = None


def _catalog_path() -> Path:
    """解析词典 JSON 的实际路径，兼容开发模式与 PyInstaller 打包。"""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", ""))
        return base / "resources" / "site_catalog.json"
    # zhmm/core/site_catalog.py → zhmm/resources/site_catalog.json
    return Path(__file__).resolve().parent.parent / "resources" / "site_catalog.json"


def _load_catalog() -> dict[str, dict[str, Any]]:
    """加载并缓存离线词典。失败时返回空 dict（降级为「无建议」模式）。"""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    path = _catalog_path()
    result: dict[str, dict[str, Any]] = {}
    try:
        if path.is_file():
            with path.open(encoding="utf-8") as f:
                raw = json.load(f)
            sites = raw.get("sites") if isinstance(raw, dict) else None
            if isinstance(sites, dict):
                for host, info in sites.items():
                    if not isinstance(host, str) or not isinstance(info, dict):
                        continue
                    name = info.get("name") or ""
                    tags = info.get("tags") or []
                    if not isinstance(name, str):
                        name = ""
                    if not isinstance(tags, list):
                        tags = []
                    # 仅保留字符串标签
                    tags = [t for t in tags if isinstance(t, str) and t.strip()]
                    result[host.lower().strip()] = {"name": name.strip(), "tags": tags}
    except (OSError, ValueError) as ex:
        logger.warning("加载站点词典失败，已降级为空词典: %s", ex)
        result = {}
    _CATALOG_CACHE = result
    return result


def reload_catalog() -> None:
    """清空缓存，主要给测试用。"""
    global _CATALOG_CACHE
    _CATALOG_CACHE = None


# ----------------------------------------------------------------------
# 规则兜底
# ----------------------------------------------------------------------
# 顶级后缀规则：host 以 key 结尾（完整标签匹配）→ 追加 value 里的标签
_SUFFIX_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (".gov.cn", ("政务",)),
    (".edu.cn", ("教育",)),
    (".ac.cn", ("教育",)),
    (".mil.cn", ("政务",)),
    (".gov", ("政务", "海外")),
    (".edu", ("教育", "海外")),
)

# 域名关键字规则：包含某子串（小写）→ 追加对应标签
_KEYWORD_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("bank", ("金融", "银行")),
    ("pay", ("金融", "支付")),
    ("mail", ("邮箱",)),
    ("shop", ("购物",)),
    ("mall", ("购物",)),
    ("game", ("游戏",)),
    ("cloud", ("云服务",)),
)


def _apply_rules(host: str) -> list[str]:
    """对 host 应用兜底规则，返回去重后的标签列表。"""
    host = host.lower()
    out: list[str] = []
    seen: set[str] = set()

    def _add(items: tuple[str, ...]) -> None:
        for t in items:
            if t not in seen:
                seen.add(t)
                out.append(t)

    for suffix, tags in _SUFFIX_RULES:
        if host.endswith(suffix):
            _add(tags)
            break
    for kw, tags in _KEYWORD_RULES:
        if kw in host:
            _add(tags)
    return out


# ----------------------------------------------------------------------
# 对外 API
# ----------------------------------------------------------------------
def suggest(url_or_host: str | None) -> SiteSuggestion:
    """根据 URL 或 host 给出中文名 + 建议标签。

    调用链：
    1. 提取完整 host 与根域名
    2. 先看完整 host 是否在词典（支持 ``mail.qq.com`` 这类子域精确条目）
    3. 再看根域名是否在词典
    4. 都未命中 → 走兜底规则（后缀 + 关键字）
    """
    host = extract_host(url_or_host)
    if not host:
        return SiteSuggestion()

    catalog = _load_catalog()

    # 1. 完整 host 精确匹配
    hit = catalog.get(host)
    if hit:
        return SiteSuggestion(
            name=hit.get("name", ""),
            tags=list(hit.get("tags") or []),
            matched="host",
        )

    # 2. 根域名精确匹配
    domain = registrable_domain(host)
    if domain and domain != host:
        hit = catalog.get(domain)
        if hit:
            return SiteSuggestion(
                name=hit.get("name", ""),
                tags=list(hit.get("tags") or []),
                matched="domain",
            )

    # 3. 兜底规则
    rule_tags = _apply_rules(host)
    if rule_tags:
        return SiteSuggestion(name="", tags=rule_tags, matched="rule")

    return SiteSuggestion()


__all__ = ["SiteSuggestion", "reload_catalog", "suggest"]
