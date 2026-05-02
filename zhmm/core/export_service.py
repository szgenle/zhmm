"""Excel 导入导出服务。

从老 `data_exporter.py` 迁移到 core 层，统一：
- 输入输出是 `PasswordEntry` 列表，不再是 TypedDict dict
- 失败抛 `StorageError` / `ValidationError`，不再 print + return None
- 不再有 `print` 侧效，由调用方决定如何汇报

特殊字符转义规则与历史一致：`\r` ↔ `[r]`，`\n` ↔ `[n]`，便于跨 sheet 编辑。
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook, load_workbook

from zhmm.core.errors import StorageError, ValidationError
from zhmm.core.models import PasswordEntry

CN_HEADS: tuple[str, ...] = (
    "ID",
    "类别",
    "账号",
    "密码",
    "手机",
    "邮箱",
    "网站",
    "备注",
    "更新时间",
)
EN_HEADS: tuple[str, ...] = (
    "id",
    "role",
    "userID",
    "pwd",
    "phone",
    "email",
    "url",
    "desc",
    "utime",
)
_INT_FIELDS = {"id", "utime"}


def _escape(value: str) -> str:
    return value.replace("\r", "[r]").replace("\n", "[n]")


def _unescape(value: str) -> str:
    return value.replace("[r]", "\r").replace("[n]", "\n")


class ExportService:
    """Excel 导入导出。静态方法形式。"""

    # ---------- 导出 ----------

    @staticmethod
    def export_xlsx(file_path: str | Path, entries: list[PasswordEntry]) -> None:
        """把条目导出为 xlsx。

        Raises:
            StorageError: 文件写入失败
        """
        wb = Workbook()
        ws = wb.active
        if ws is None:  # pragma: no cover - openpyxl 保证
            raise StorageError("failed to create worksheet")
        ws.title = "密码数据"
        ws.append(list(CN_HEADS))
        for e in entries:
            row: list[str] = []
            d = e.to_dict()
            for key in EN_HEADS:
                v = d.get(key, "")
                row.append(_escape(str(v) if v is not None else ""))
            ws.append(row)
        try:
            wb.save(str(file_path))
        except OSError as ex:
            raise StorageError(f"write failed: {file_path}: {ex}") from ex
        finally:
            wb.close()

    # ---------- 导入 ----------

    @staticmethod
    def import_xlsx(file_path: str | Path) -> list[PasswordEntry]:
        """从 xlsx 导入条目。

        Raises:
            StorageError: 文件不存在 / 读取失败
            ValidationError: 表头不匹配
        """
        p = Path(file_path)
        if not p.exists():
            raise StorageError(f"file not found: {p}")
        try:
            wb = load_workbook(str(p), data_only=True)
        except OSError as ex:
            raise StorageError(f"read failed: {p}: {ex}") from ex

        try:
            ws = wb.active
            if ws is None:
                raise ValidationError("worksheet is empty")
            header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
            if not header_row:
                raise ValidationError("header row is missing")
            headers = [str(h) if h is not None else "" for h in header_row]
            missing = [h for h in CN_HEADS if h not in headers]
            if missing:
                raise ValidationError(f"missing columns: {missing}")
            index_map = {h: i for i, h in enumerate(headers)}

            entries: list[PasswordEntry] = []
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row is None or all(v is None or v == "" for v in row):
                    continue
                data: dict[str, object] = {}
                for cn, en in zip(CN_HEADS, EN_HEADS, strict=True):
                    col = index_map.get(cn, -1)
                    value = row[col] if 0 <= col < len(row) else None
                    if value is None:
                        data[en] = 0 if en in _INT_FIELDS else ""
                        continue
                    text = str(value)
                    # openpyxl 对纯数字列常会返回 float，手机号需去掉小数尾
                    if en == "phone" and text.endswith(".0"):
                        text = text[:-2]
                    text = _unescape(text)
                    if en in _INT_FIELDS:
                        try:
                            data[en] = int(float(text)) if text else 0
                        except (ValueError, TypeError):
                            data[en] = 0
                    else:
                        data[en] = text
                entries.append(PasswordEntry.from_dict(data))
            return entries
        finally:
            wb.close()
