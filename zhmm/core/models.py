"""领域模型：PasswordEntry / Vault.

使用 dataclass 替代老代码中的 TypedDict，使字段、类型、默认值、相等性一处定义。

字段命名保留与历史 JSON schema 的兼容（`userID` 而非 `user_id`），以便在不迁移历史数据
（已明确不迁移）的前提下，与 Excel 导入导出继续吻合。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any

DEFAULT_ROLES: tuple[str, ...] = ("个人", "工作", "其它")
DEFAULT_ROLE: str = "个人"


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
