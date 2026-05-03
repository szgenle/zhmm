"""密码条目业务逻辑：CRUD / 搜索 / 合并 / 修复。

围绕 [Vault][zhmm.core.models.Vault] 提供纯内存操作，所有落盘交给调用方
（一般是 [VaultFile.save][zhmm.core.vault.VaultFile.save]）。

设计原则：
- 不涉及 I/O，便于单测
- 输入输出全部是领域对象，不吐 TypedDict
- 时间戳从外部注入（默认 time.time()），方便测试确定
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable

from zhmm.core.models import DEFAULT_ROLE, DEFAULT_ROLES, HISTORY_MAX, PasswordEntry, PasswordHistoryItem, Vault

Clock = Callable[[], int]

SEARCHABLE_FIELDS: tuple[str, ...] = ("url", "desc", "userID", "phone", "email")


def _now() -> int:
    return int(time.time())


class PasswordService:
    """纯内存的密码库操作。持有 Vault 引用，方法直接修改之。"""

    def __init__(self, vault: Vault | None = None, clock: Clock = _now) -> None:
        self.vault: Vault = vault if vault is not None else Vault.empty()
        self._clock = clock

    # ---------- 基础 ----------

    def set_vault(self, vault: Vault) -> None:
        """替换当前 vault，并补齐 roles / 默认 role / utime。"""
        # 确保 roles 非空
        if not vault.roles:
            vault.roles = list(DEFAULT_ROLES)
        # 补默认 role + 收集未知 role
        for e in vault.entries:
            if not e.role:
                e.role = DEFAULT_ROLE
            if e.role not in vault.roles:
                vault.roles.append(e.role)
        if not vault.utime:
            vault.utime = self._clock()
        self.vault = vault

    # ---------- CRUD ----------

    def add(self, entry: PasswordEntry) -> PasswordEntry:
        """追加一条记录；自动补 role/id/utime，并推进 vault.utime。"""
        now = self._clock()
        if not entry.role:
            entry.role = DEFAULT_ROLE
        if not entry.id:
            entry.id = now
        if not entry.utime:
            entry.utime = now
        if entry.role not in self.vault.roles:
            self.vault.roles.append(entry.role)
        self.vault.entries.append(entry)
        self.vault.utime = now
        return entry

    def delete(self, entry_id: int) -> bool:
        """按 id 删除，成功返回 True。"""
        before = len(self.vault.entries)
        self.vault.entries = [e for e in self.vault.entries if e.id != entry_id]
        if len(self.vault.entries) < before:
            self.vault.utime = self._clock()
            return True
        return False

    def update(self, entry_id: int, **changes: object) -> PasswordEntry | None:
        """按 id 就地更新指定字段。返回更新后的对象；未找到返回 None。

        密码历史规则：当且仅当 ``pwd`` 实际发生变化且旧密码非空时，将旧密码
        连同当前时间戳压入 ``history`` 栈顶，最多保留 ``HISTORY_MAX`` 条。调用方不
        需显式传 ``history``；如显式传入会被历史注写覆盖，避免绕过记录。
        """
        for idx, e in enumerate(self.vault.entries):
            if e.id == entry_id:
                now = self._clock()
                updated_changes = dict(changes)
                updated_changes.setdefault("utime", now)
                # 密码变更→自动注入历史→截断。仅当 pwd 传入且与现值不同。
                new_pwd = updated_changes.get("pwd")
                if "pwd" in updated_changes and isinstance(new_pwd, str) and new_pwd != e.pwd and e.pwd:
                    history = [PasswordHistoryItem(pwd=e.pwd, utime=now), *e.history]
                    updated_changes["history"] = history[:HISTORY_MAX]
                new_entry = e.clone(**updated_changes)
                if new_entry.role and new_entry.role not in self.vault.roles:
                    self.vault.roles.append(new_entry.role)
                self.vault.entries[idx] = new_entry
                self.vault.utime = now
                return new_entry
        return None

    def rollback(self, entry_id: int, history_index: int = 0) -> PasswordEntry | None:
        """把 ``history[history_index]`` 的旧密码恢复为当前密码；当前密码同时压回栈顶。

        - 回滚本身也算一次“历史事件”：两次回滚能还原原始状态
        - 条目不存在或索引越界→返回 None
        - 目标历史密码为空（脏数据）→返回 None
        """
        for idx, e in enumerate(self.vault.entries):
            if e.id != entry_id:
                continue
            if history_index < 0 or history_index >= len(e.history):
                return None
            target = e.history[history_index]
            if not target.pwd:
                return None
            now = self._clock()
            # 用一次性重建的 history：移除 target 下标，并将当前 pwd 压入栈顶
            remaining = [h for i, h in enumerate(e.history) if i != history_index]
            new_history = [PasswordHistoryItem(pwd=e.pwd, utime=now), *remaining]
            new_entry = e.clone(pwd=target.pwd, utime=now, history=new_history[:HISTORY_MAX])
            self.vault.entries[idx] = new_entry
            self.vault.utime = now
            return new_entry
        return None

    def get(self, entry_id: int) -> PasswordEntry | None:
        for e in self.vault.entries:
            if e.id == entry_id:
                return e
        return None

    # ---------- 搜索 / 修复 ----------

    def search(self, words: str) -> list[PasswordEntry]:
        """在 SEARCHABLE_FIELDS 中做大小写不敏感的多关键字 OR 搜索。

        - 多个关键字用空白分隔
        - 空查询返回空列表
        - 结果按出现顺序去重
        - ``tags`` 作为 list 字段，拼接成空格分隔文本一同参与匹配
        """
        tokens = [w.lower() for w in words.split() if w]
        if not tokens:
            return []
        seen: set[int] = set()
        out: list[PasswordEntry] = []
        for e in self.vault.entries:
            if e.id in seen:
                continue
            haystack_parts = [getattr(e, f, "") or "" for f in SEARCHABLE_FIELDS]
            # tags 为 list，单独拼接后并入 haystack
            tags = getattr(e, "tags", None) or []
            if tags:
                haystack_parts.append(" ".join(str(t) for t in tags))
            haystack = " ".join(haystack_parts).lower()
            if any(tok in haystack for tok in tokens):
                out.append(e)
                seen.add(e.id)
        return out

    def fix_missing_ids(self) -> int:
        """为缺失/非整数的 id/utime 填上时间戳，返回修复的条目数。"""
        base = self._clock()
        offset = 0
        fixed = 0
        for e in self.vault.entries:
            changed = False
            if not isinstance(e.id, int) or not e.id:
                e.id = base + offset
                offset += 1
                changed = True
            if not isinstance(e.utime, int) or not e.utime:
                e.utime = base
                changed = True
            if changed:
                fixed += 1
        if fixed:
            self.vault.utime = base
        return fixed

    # ---------- 合并 ----------

    def merge(self, others: Iterable[PasswordEntry]) -> tuple[int, int]:
        """把外部记录合并进当前 vault。

        规则：
        - id 不存在 → 追加
        - id 存在且内容完全相同 → 跳过
        - id 存在且 utime 较新 → 覆盖
        - 两边 utime 缺失 → 追加（视为独立条目）

        Returns:
            (append_count, update_count)
        """
        append = 0
        update = 0
        index: dict[int, int] = {e.id: i for i, e in enumerate(self.vault.entries) if e.id}

        for item in others:
            if not item.id:
                continue
            if item.id not in index:
                self.vault.entries.append(item)
                index[item.id] = len(self.vault.entries) - 1
                if item.role and item.role not in self.vault.roles:
                    self.vault.roles.append(item.role)
                append += 1
                continue

            existing = self.vault.entries[index[item.id]]
            if existing == item:
                continue
            item_utime = item.utime or 0
            existing_utime = existing.utime or 0
            if item_utime > existing_utime:
                self.vault.entries[index[item.id]] = item
                if item.role and item.role not in self.vault.roles:
                    self.vault.roles.append(item.role)
                update += 1
            elif item_utime == 0 and existing_utime == 0:
                # 无时间戳，追加为新条目保持老行为
                self.vault.entries.append(item)
                append += 1

        if append or update:
            self.vault.utime = self._clock()
        return append, update
