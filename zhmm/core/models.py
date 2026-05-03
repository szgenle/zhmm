"""领域模型：PasswordEntry / Vault.

使用 dataclass 替代老代码中的 TypedDict，使字段、类型、默认值、相等性一处定义。

字段命名保留与历史 JSON schema 的兼容（`userID` 而非 `user_id`），以便在不迁移历史数据
（已明确不迁移）的前提下，与 Excel 导入导出继续吻合。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field, replace
from typing import Any

DEFAULT_ROLES: tuple[str, ...] = ("个人", "工作", "其它")
DEFAULT_ROLE: str = "个人"

# 标签形状限制：单个标签长度与每条目最多数量。
# 弱约束：超出会被静默截断/丢弃，不抛异常，以免旧数据或 Excel 误导入时炸掉。
TAG_MAX_LEN: int = 32
TAGS_MAX_COUNT: int = 16

# 同条目内密码历史版本最大保留条数（FIFO，旧密码替换时插入栈顶）。
# 设计约束：只保存密码本身与被替换时间，不保存其它字段；仅随 .zmb 加密落盘，
# Excel 导出/导入链路刻意不承载，避免明文扩散。
HISTORY_MAX: int = 5


def _normalize_history(raw: Any) -> list[PasswordHistoryItem]:
    """归一化历史密码输入（容忍旧 .zmb 无该字段 / 字段异常）。

    - 非 list → 空列表
    - 元素为 ``PasswordHistoryItem`` 直接复用
    - 元素为 dict：取 ``pwd`` / ``utime``，pwd 必须为非空字符串
    - 其它元素静默丢弃
    - 最终截断到 ``HISTORY_MAX`` 条
    """
    if not isinstance(raw, list):
        return []
    out: list[PasswordHistoryItem] = []
    for it in raw:
        if isinstance(it, PasswordHistoryItem):
            out.append(it)
            continue
        if isinstance(it, dict):
            pwd = it.get("pwd", "")
            utime_raw = it.get("utime", 0)
            if not isinstance(pwd, str) or not pwd:
                continue
            utime = int(utime_raw) if isinstance(utime_raw, int | float) else 0
            out.append(PasswordHistoryItem(pwd=pwd, utime=utime))
        if len(out) >= HISTORY_MAX:
            break
    return out[:HISTORY_MAX]


def normalize_tags(raw: Any) -> list[str]:
    """归一化标签输入。

    接受 ``list | tuple | str | None``（字符串时按分号 ``;`` 拆分，
    兼容从 Excel 单元格不放心 normalize 的场景）。规则：

    - 非 str / None 元素丢弃
    - ``strip()`` 后丢空串
    - 去重（保持首次出现顺序）
    - 截断超过 ``TAG_MAX_LEN`` 的字符
    - 总数截断到 ``TAGS_MAX_COUNT``
    """
    if raw is None:
        return []
    items: Iterable[Any]
    if isinstance(raw, str):
        items = raw.split(";")
    elif isinstance(raw, (list | tuple)):
        items = raw
    else:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if not isinstance(it, str):
            continue
        t = it.strip()
        if not t:
            continue
        if len(t) > TAG_MAX_LEN:
            t = t[:TAG_MAX_LEN]
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= TAGS_MAX_COUNT:
            break
    return out


@dataclass(slots=True)
class PasswordHistoryItem:
    """同条目内的一条历史密码。

    - ``pwd``：被替换掉的旧密码原文（随 SM4 一起加密落盘）
    - ``utime``：该旧密码被替换的秒级 UNIX 时间戳
    """

    pwd: str = ""
    utime: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PasswordHistoryItem:
        pwd = data.get("pwd", "")
        utime = data.get("utime", 0)
        return cls(
            pwd=pwd if isinstance(pwd, str) else "",
            utime=int(utime) if isinstance(utime, int | float) else 0,
        )


@dataclass(slots=True)
class PasswordEntry:
    """一条密码记录。

    - `id` / `utime` 使用秒级 UNIX 时间戳
    - 所有字符串字段默认空串，避免 Optional 蔓延
    """

    id: int = 0
    role: str = DEFAULT_ROLE
    userID: str = ""
    pwd: str = ""
    phone: str = ""
    email: str = ""
    url: str = ""
    desc: str = ""
    utime: int = 0
    # TOTP 2FA：secret 为空串时表示该条目未启用 2FA
    totp_secret: str = ""  # Base32 原文
    totp_algo: str = ""  # "SHA1" | "SHA256" | "SHA512" | "SM3"
    totp_digits: int = 6  # 一般 6 或 8
    totp_period: int = 30  # 步长（秒）
    # 标签：弱分类，一个条目可贴 0~N 个，独立于 role
    tags: list[str] = field(default_factory=list)
    # 同条目内密码历史版本（最新在前，最多 HISTORY_MAX 条）。
    # 仅随 .zmb 加密落盘，Excel 通道不导出也不导入。
    history: list[PasswordHistoryItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """导出为普通 dict（用于 JSON 序列化 / Excel 导出）。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PasswordEntry:
        """从 dict 构造（容错：未知字段忽略、缺失字段走默认值、None 转默认值）。"""
        fields = set(cls.__dataclass_fields__)
        clean: dict[str, Any] = {}
        for key in fields:
            if key in data and data[key] is not None:
                clean[key] = data[key]
        # tags 统一交给 normalize_tags 处理，容忍旧数据中的 None / 非 list / 字符串 形态
        clean["tags"] = normalize_tags(clean.get("tags"))
        # history 统一归一化，容忍旧 .zmb 无该字段 / 结构异常
        clean["history"] = _normalize_history(clean.get("history"))
        entry = cls(**clean)
        if not entry.role:
            entry.role = DEFAULT_ROLE
        return entry

    def clone(self, **changes: Any) -> PasswordEntry:
        """基于当前实例生成一个改动后的新实例。"""
        return replace(self, **changes)


@dataclass(slots=True)
class Vault:
    """整个密码库（解密后的内存态）。"""

    entries: list[PasswordEntry] = field(default_factory=list)
    roles: list[str] = field(default_factory=lambda: list(DEFAULT_ROLES))
    utime: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "data": [e.to_dict() for e in self.entries],
            "roles": list(self.roles),
            "utime": self.utime,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Vault:
        raw_entries = data.get("data") or []
        entries = [PasswordEntry.from_dict(d) for d in raw_entries if isinstance(d, dict)]
        raw_roles = data.get("roles") or []
        roles: list[str] = [r for r in raw_roles if isinstance(r, str) and r]
        if not roles:
            roles = list(DEFAULT_ROLES)
        # 补齐 entry.role 不在 roles 中的角色
        for e in entries:
            if e.role and e.role not in roles:
                roles.append(e.role)
        utime_raw = data.get("utime", 0)
        utime = int(utime_raw) if isinstance(utime_raw, int | float) else 0
        return cls(entries=entries, roles=roles, utime=utime)

    @classmethod
    def empty(cls) -> Vault:
        return cls(entries=[], roles=list(DEFAULT_ROLES), utime=0)
