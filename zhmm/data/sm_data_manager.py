#!/usr/bin/env python3
"""密码数据管理器（UI 适配层）。

本类保留老 `SmData` 的公开接口（mm / file_path / init / load / save / add /
delete / search / merge / set_mm / add_with_dict / fix_id_is_None），让现有 UI
代码零改动即可使用。内部加解密已切换到 :mod:`zhmm.core.crypto`，文件格式为
v4（PBKDF2-HMAC-SHA256 + SM4-CBC + HMAC-SM3，账号同密码一同参与密钥派生），
文件后缀为 `.zmb`。
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path

from zhmm.core.crypto import Vault as CryptoVault
from zhmm.core.errors import CryptoError, StorageError
from zhmm.core.models import normalize_tags
from zhmm.core.vault import VaultFile
from zhmm.data.sm_data_types import SmDataConstants, ZhmmDataDict, ZhmmDict
from zhmm.utils import date_util, dict_util

DEFAULT_ROLES = ["个人", "工作", "其它"]


class SmData:
    """密码数据管理器。"""

    # 类级别常量（UI 层读取）
    field_mapping = SmDataConstants.FIELD_MAPPING
    keys = SmDataConstants.KEYS
    heads = SmDataConstants.HEADS
    SEARCHABLE_FIELDS = SmDataConstants.SEARCHABLE_FIELDS

    def __init__(self) -> None:
        self.mm: ZhmmDataDict = {
            "data": [],
            "roles": list(DEFAULT_ROLES),
            "utime": 0,
        }
        self.file_path: str = ""
        self._account: str = ""
        self._password: str = ""

    # ------------------------------------------------------------------
    # 初始化与 in-memory 状态
    # ------------------------------------------------------------------
    def init(self, account: str, password: str) -> None:
        """设置账号与密码（用于后续 load/save）。

        ``account`` 和 ``password`` 一同作为 KDF 输入参与密钥派生，账号本身不
        写入加密文件。业务层（UI/CLI）负责拒绝空账号；core.crypto 本身
        允许空账号以保持通用性。
        """
        if not isinstance(account, str):
            raise ValueError("账号必须为字符串")
        if not password:
            raise ValueError("密码不能为空")
        self._account = account
        self._password = password

    def set_mm(self, user_mm_data: ZhmmDataDict) -> None:
        """设置密码数据（补齐 roles / role / tags 默认值）。"""
        self.mm = user_mm_data
        if "roles" not in user_mm_data or not user_mm_data["roles"]:
            user_mm_data["roles"] = list(DEFAULT_ROLES)
        for item in user_mm_data["data"]:
            if "role" not in item or not item["role"]:
                item["role"] = "个人"
            if item["role"] not in user_mm_data["roles"]:
                user_mm_data["roles"].append(item["role"])
            # tags 容错：缺失 / None / 非 list / 含非法元素 统一过 normalize
            item["tags"] = normalize_tags(item.get("tags"))  # type: ignore[typeddict-item]
        user_mm_data.setdefault("utime", date_util.timestamp_int())

    # ------------------------------------------------------------------
    # 数据修复与 CRUD
    # ------------------------------------------------------------------
    def fix_id_is_None(self) -> bool:
        """修复 id/utime 非整数的遗留数据。

        Returns:
            True 表示所有项均已修复，无需再次调用。
        """
        if not self.mm or not self.mm["data"]:
            return True

        base = date_util.timestamp_int()
        offset = 0
        all_fixed = True
        for item in self.mm["data"]:
            if "id" not in item or not isinstance(item["id"], int):
                item["id"] = base + offset
                offset += 1
                all_fixed = False
            if "utime" not in item or not isinstance(item["utime"], int):
                item["utime"] = base
                all_fixed = False
        return all_fixed

    def search(self, words: str) -> list[ZhmmDict] | None:
        """多关键字搜索（OR，忽略大小写，按 id 去重）。

        除 ``SEARCHABLE_FIELDS`` 外，也包含标签（tags 拼接文本）。
        """
        if not self.mm or not self.mm["data"]:
            return None

        hits: dict[int, ZhmmDict] = {}
        for word in words.split():
            w = word.lower()
            for item in self.mm["data"]:
                if not item.get("id") or item["id"] in hits:
                    continue
                matched = False
                for field in self.SEARCHABLE_FIELDS:
                    value = item.get(field)
                    if value and w in str(value).lower():
                        matched = True
                        break
                if not matched:
                    tags = item.get("tags") or []
                    if isinstance(tags, list) and any(w in str(t).lower() for t in tags):
                        matched = True
                if matched:
                    hits[item["id"]] = item
        return list(hits.values()) if hits else None

    def delete(self, id: int) -> bool:
        """按 id 删除。"""
        if not self.mm or not self.mm["data"]:
            return False
        before = len(self.mm["data"])
        self.mm["data"] = [item for item in self.mm["data"] if item.get("id") != id]
        if len(self.mm["data"]) < before:
            self.mm["utime"] = date_util.timestamp_int()
            return True
        return False

    def add(self, info: ZhmmDict) -> None:
        """追加数据项（补齐 role/id/utime）。"""
        if not info.get("role"):
            info["role"] = "个人"
        if not info.get("id"):
            info["id"] = date_util.timestamp_int()
        if not info.get("utime"):
            info["utime"] = date_util.timestamp_int()
        self.mm["data"].append(info)
        self.mm["utime"] = date_util.timestamp_int()

    def merge(self, other: list[ZhmmDict], auto_save: bool = True) -> tuple[int, int]:
        """合并数据列表；按 utime 保留较新版本。"""
        if not other:
            return 0, 0

        append_times = 0
        update_times = 0
        for item in other:
            if "id" not in item:
                continue
            existing = next(
                (x for x in self.mm["data"] if x.get("id") == item["id"]),
                None,
            )
            if existing is None:
                self.mm["data"].append(item)
                append_times += 1
                continue
            if dict_util.is_equal(existing, item):  # type: ignore
                continue
            item_utime = item.get("utime", 0) or 0
            existing_utime = existing.get("utime", 0) or 0
            if item_utime > existing_utime:
                existing.update(item)
                update_times += 1
            elif item_utime == 0 or existing_utime == 0:
                self.mm["data"].append(item)
                append_times += 1

        if append_times + update_times > 0:
            self.mm["utime"] = date_util.timestamp_int()
            if auto_save:
                self.save()
        return append_times, update_times

    def add_with_dict(self, info: dict) -> None:
        """从普通 dict 构造并追加（字段补全）。"""
        self.add(
            {
                "id": info.get("id", date_util.timestamp_int()),
                "role": info.get("role", "个人"),
                "userID": info.get("userID", ""),
                "pwd": info.get("pwd", ""),
                "phone": info.get("phone", ""),
                "email": info.get("email", ""),
                "url": info.get("url", ""),
                "desc": info.get("desc", ""),
                "utime": info.get("utime", date_util.timestamp_int()),
                "tags": info.get("tags"),
                "history": info.get("history"),
            }
        )

    # ------------------------------------------------------------------
    # 标签批量操作
    # ------------------------------------------------------------------
    def collect_tag_counts(self) -> dict[str, int]:
        """统计当前库所有标签的使用次数。

        Returns:
            dict[tag, count]，不保证顺序（UI 层自行排序）。
        """
        counts: dict[str, int] = {}
        for item in self.mm.get("data") or []:
            tags = item.get("tags") if isinstance(item, dict) else None
            if not isinstance(tags, list):
                continue
            for t in tags:
                if isinstance(t, str) and t:
                    counts[t] = counts.get(t, 0) + 1
        return counts

    def rename_tag(self, old: str, new: str) -> int:
        """把所有条目中的 ``old`` 标签替换为 ``new``（含去重合并）。

        - ``old`` / ``new`` 先走 :func:`normalize_tags` 归一化
        - 归一化后为空 或 二者相等 → 不做任何改动，返回 0
        - 若条目同时带有 ``old`` 和 ``new``，去重后只保留一个 ``new``
        - 受影响条目的 ``utime`` 会刷新

        Returns:
            受影响的条目数（未调用 :meth:`save`，由调用方决定落盘时机）。
        """
        old_n = normalize_tags([old])
        new_n = normalize_tags([new])
        if not old_n or not new_n:
            return 0
        old_tag = old_n[0]
        new_tag = new_n[0]
        if old_tag == new_tag:
            return 0

        affected = 0
        now = date_util.timestamp_int()
        for item in self.mm.get("data") or []:
            tags = item.get("tags") if isinstance(item, dict) else None
            if not isinstance(tags, list) or old_tag not in tags:
                continue
            replaced = [new_tag if t == old_tag else t for t in tags]
            item["tags"] = normalize_tags(replaced)  # type: ignore[typeddict-item]
            item["utime"] = now
            affected += 1
        if affected:
            self.mm["utime"] = now
        return affected

    def delete_tag(self, tag: str) -> int:
        """从所有条目的 tags 列表中删除指定标签。

        Returns:
            受影响的条目数（未调用 :meth:`save`）。
        """
        n = normalize_tags([tag])
        if not n:
            return 0
        target = n[0]

        affected = 0
        now = date_util.timestamp_int()
        for item in self.mm.get("data") or []:
            tags = item.get("tags") if isinstance(item, dict) else None
            if not isinstance(tags, list) or target not in tags:
                continue
            item["tags"] = [t for t in tags if t != target]  # type: ignore[typeddict-item]
            item["utime"] = now
            affected += 1
        if affected:
            self.mm["utime"] = now
        return affected

    # ------------------------------------------------------------------
    # 加密读写（切到 core.crypto.Vault）
    # ------------------------------------------------------------------
    def load(self, file_path: str | None = None) -> bool:
        """从文件加载并解密数据。成功返回 True，失败返回 False。"""
        if file_path is None:
            file_path = self.file_path
        if not file_path:
            return False

        try:
            blob = Path(file_path).read_bytes()
        except OSError as e:
            print(f"[错误] 读取文件失败: {file_path}, 原因: {e}")
            return False

        if not blob:
            print(f"[错误] 文件为空: {file_path}")
            return False

        try:
            plaintext = CryptoVault.open(self._account, self._password, blob)
        except CryptoError as e:
            print(f"[错误] 解密失败: {file_path}, 原因: {e}")
            return False

        try:
            data = json.loads(plaintext.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"[错误] JSON 解析失败: {file_path}, 原因: {e}")
            return False

        self.set_mm(data)
        self.file_path = file_path
        return True

    def save(self, file_path: str | None = None) -> bool:
        """加密数据原子性落盘。成功返回 True，失败返回 False。"""
        if file_path is None:
            file_path = self.file_path
        if not file_path:
            print("[错误] 文件路径为空，无法保存")
            return False
        if not self._password:
            print("[错误] 密码未初始化，无法保存")
            return False

        try:
            plaintext = json.dumps(self.mm, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            blob = CryptoVault.seal(self._account, self._password, plaintext)
        except (CryptoError, ValueError) as e:
            print(f"[错误] 加密失败: {file_path}, 原因: {e}")
            return False

        file_dir = os.path.dirname(file_path) or "."
        file_name = os.path.basename(file_path)
        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=file_dir,
                prefix=f".{file_name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp_path = tmp.name
                tmp.write(blob)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, file_path)
            return True
        except (OSError, StorageError) as e:
            print(f"[错误] 保存文件失败: {file_path}, 原因: {e}")
            if tmp_path and os.path.exists(tmp_path):
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
            return False

    # ------------------------------------------------------------------
    # 主密码更换（Re-key）
    # ------------------------------------------------------------------
    def rekey(self, new_password: str) -> None:
        """原地更换主密码。

        前置：必须已 ``init(account, password)`` 且 ``file_path`` 非空。
        成功后 ``self._password`` 切换为 ``new_password``，后续 ``save()``
        将以新密码加密。

        账号保持不变，因此基于 account MD5 的 config 文件名与 saved_files
        索引键都无需迁移。

        Raises:
            ValueError: 前置条件未满足或新密码为空 / 与旧密码相同。
            StorageError: 读写失败。
            CryptoError:  旧密码错误 / 文件被篡改 / 版本不匹配。
        """
        if not self._account or not self._password:
            raise ValueError("数据管理器未初始化（缺少账号或当前密码）")
        if not self.file_path:
            raise ValueError("文件路径为空，无法换密")
        if not isinstance(new_password, str) or not new_password:
            raise ValueError("新密码不能为空")
        if new_password == self._password:
            raise ValueError("新密码不能与当前密码相同")

        VaultFile.rekey(self.file_path, self._account, self._password, new_password)
        self._password = new_password
