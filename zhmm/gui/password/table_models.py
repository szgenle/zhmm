#!/usr/bin/env python3
"""密码表格数据模型"""

from datetime import datetime

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt

from zhmm.core import totp as totp_mod
from zhmm.core.errors import ValidationError

# 密码掩码占位符（固定 8 个圆点，不暴露真实长度）
_PWD_MASK = "•" * 8
# 密码列索引
_PWD_COL = 3
# “显示”按钮列索引（紧跟在密码列后面）
_REVEAL_COL = 4
# “动态码”列索引（紧跟在显示列后面）
_TOTP_COL = 5
# “标签”列索引（网站列后、备注列前）
_TAGS_COL = 9
# “更新时间”列索引（新增标签列后顺延一位）
_UTIME_COL = 11
# TOTP 计算失败时的占位符
_TOTP_ERROR = "⚠"
# 未启用 TOTP 的占位符
_TOTP_DASH = "—"


def _format_utime(value) -> str:
    """把 utime（秒级 UNIX 时间戳）格式化为 YYYY-MM-DD；无效/为 0 返回空串。

    之所以选择仅显示到「日」而非带时分秒：更新时间对用户是「上次什么时候改过」
    的参考，精度到天足矣，也能让该列宽度稳定、表格更清爽。排序时 YYYY-MM-DD
    字典序与时间序一致，不会引入错序。
    """
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return ""
    if ts <= 0:
        return ""
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except (OSError, OverflowError, ValueError):
        return ""


def _format_tags(value) -> str:
    """把 tags 列表格式化为 "#a  #b" 可读形式；非法/空返回空串。"""
    if not value or not isinstance(value, list):
        return ""
    return "  ".join(f"#{t}" for t in value if isinstance(t, str) and t)


class PasswordTableModel(QAbstractTableModel):
    """密码表格数据模型"""

    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.headers = [
            "ID",
            "类别",
            "账号",
            "密码",
            "显示",
            "动态码",
            "手机",
            "邮箱",
            "网站",
            "标签",
            "备注",
            "更新时间",
        ]
        self.keys = [
            "id",
            "role",
            "userID",
            "pwd",
            "",  # “显示”列无直接字段，单独处理
            "",  # “动态码”列无直接字段，按 totp_* 动态计算
            "phone",
            "email",
            "url",
            "tags",  # 标签 list，display 下特殊渲染
            "desc",
            "utime",
        ]
        self._data = data if data else []
        # 记录当前明文显示的行 id 集合
        self._revealed_ids: set[int] = set()

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        if row < 0 or row >= len(self._data):
            return None
        item = self._data[row]

        if role == Qt.ItemDataRole.DisplayRole:
            # “显示”列：不返回文本，由 RevealColumnDelegate 绘制 SVG 图标
            if col == _REVEAL_COL:
                return ""
            # 密码列：未 reveal 返回掩码，reveal 返回明文
            if col == _PWD_COL:
                rid = item.get("id")
                if rid in self._revealed_ids:
                    return str(item.get("pwd", ""))
                return _PWD_MASK if item.get("pwd") else ""
            # 动态码列：根据 totp_secret 实时计算
            if col == _TOTP_COL:
                return self._compute_totp_display(item)
            # 标签列：list[str] 渲染为 "#a  #b"
            if col == _TAGS_COL:
                return _format_tags(item.get("tags"))
            # 更新时间列：把 UNIX 时间戳格式化为 YYYY-MM-DD
            if col == _UTIME_COL:
                return _format_utime(item.get("utime"))
            # 其他列：原样返回
            key = self.keys[col]
            return str(item.get(key, ""))

        if role == Qt.ItemDataRole.EditRole:
            # EditRole 始终返回真实值，供复制/导出等使用
            if col == _PWD_COL:
                return str(item.get("pwd", ""))
            if col == _REVEAL_COL:
                return ""
            if col == _TOTP_COL:
                return self._compute_totp_display(item)
            if col == _TAGS_COL:
                # 复制时用分号分隔形式，跟 Excel 导出一致
                tags = item.get("tags") or []
                if isinstance(tags, list):
                    return ";".join(str(t) for t in tags)
                return str(tags)
            key = self.keys[col]
            return str(item.get(key, ""))

        if role == Qt.ItemDataRole.TextAlignmentRole and col in (_REVEAL_COL, _TOTP_COL):
            return int(Qt.AlignmentFlag.AlignCenter)

        if role == Qt.ItemDataRole.ToolTipRole:
            if col == _REVEAL_COL:
                return "点击显示/隐藏密码"
            if col == _TOTP_COL:
                if item.get("totp_secret"):
                    return "点击复制当前动态码"
                return "未启用二次验证（TOTP）"

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None

    def setZhData(self, data):
        self.beginResetModel()
        self._data = data
        # 数据重置时清空明文显示状态，防止遗留
        self._revealed_ids.clear()
        self.endResetModel()

    # ------------------------------------------------------------------
    # 密码明文显示控制
    # ------------------------------------------------------------------
    def is_revealed(self, source_row: int) -> bool:
        if source_row < 0 or source_row >= len(self._data):
            return False
        rid = self._data[source_row].get("id")
        return rid in self._revealed_ids

    def set_revealed(self, source_row: int, revealed: bool) -> None:
        if source_row < 0 or source_row >= len(self._data):
            return
        rid = self._data[source_row].get("id")
        if rid is None:
            return
        if revealed:
            self._revealed_ids.add(rid)
        else:
            self._revealed_ids.discard(rid)
        # 通知该行的密码列与显示列刷新
        top = self.index(source_row, _PWD_COL)
        bottom = self.index(source_row, _REVEAL_COL)
        self.dataChanged.emit(top, bottom, [Qt.ItemDataRole.DisplayRole])

    def toggle_revealed(self, source_row: int) -> bool:
        """切换指定行的明文显示状态，返回切换后的状态。"""
        new_state = not self.is_revealed(source_row)
        self.set_revealed(source_row, new_state)
        return new_state

    def row_id(self, source_row: int) -> int | None:
        if source_row < 0 or source_row >= len(self._data):
            return None
        rid = self._data[source_row].get("id")
        return rid if isinstance(rid, int) else None

    def row_by_id(self, rid: int) -> int:
        for i, item in enumerate(self._data):
            if item.get("id") == rid:
                return i
        return -1

    @staticmethod
    def password_column() -> int:
        return _PWD_COL

    @staticmethod
    def reveal_column() -> int:
        return _REVEAL_COL

    @staticmethod
    def totp_column() -> int:
        return _TOTP_COL

    @staticmethod
    def tags_column() -> int:
        return _TAGS_COL

    @staticmethod
    def utime_column() -> int:
        return _UTIME_COL

    def flags(self, index: QModelIndex):  # type: ignore[override]
        base = super().flags(index)
        # “显示”列与“动态码”列不可选中/不可编辑，但可交互左键点击
        if index.column() in (_REVEAL_COL, _TOTP_COL):
            return Qt.ItemFlag.ItemIsEnabled
        return base

    # ------------------------------------------------------------------
    # TOTP 计算
    # ------------------------------------------------------------------
    @staticmethod
    def compute_totp_code(item: dict) -> str | None:
        """按条目字段实时计算 TOTP 码；secret 为空返回 None，失败抛 ValidationError。"""
        secret = str(item.get("totp_secret") or "").strip()
        if not secret:
            return None
        algo = str(item.get("totp_algo") or totp_mod.DEFAULT_ALGO).upper()
        try:
            digits = int(item.get("totp_digits") or totp_mod.DEFAULT_DIGITS)
            period = int(item.get("totp_period") or totp_mod.DEFAULT_PERIOD)
        except (TypeError, ValueError):
            digits = totp_mod.DEFAULT_DIGITS
            period = totp_mod.DEFAULT_PERIOD
        return totp_mod.generate(secret, algo=algo, digits=digits, period=period)

    @classmethod
    def _compute_totp_display(cls, item: dict) -> str:
        try:
            code = cls.compute_totp_code(item)
        except ValidationError:
            return _TOTP_ERROR
        if code is None:
            return _TOTP_DASH
        # 附加剩余秒数便于用户判断刷新节奏
        try:
            period = int(item.get("totp_period") or totp_mod.DEFAULT_PERIOD)
        except (TypeError, ValueError):
            period = totp_mod.DEFAULT_PERIOD
        left = totp_mod.remaining_seconds(period)
        return f"{code}  {left}s"


class CustomProxyModel(QSortFilterProxyModel):
    """自定义代理模型。

    为避免动态变化的"动态码"列干扰搜索结果，过滤阶段不走 base 实现的全列
    文本匹配，而是只对若干稳定字段做大小写不敏感子串匹配。
    """

    # 参与搜索的原始字段（与老行为 ``SmData.SEARCHABLE_FIELDS`` 一致）
    _SEARCHABLE_FIELDS = ("userID", "phone", "email", "url", "desc")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_all_data = False  # 控制是否显示所有数据
        self.filter_role = ""  # 角色过滤值
        self.use_role_filter = False  # 是否使用角色过滤
        self.selected_tags: list[str] = []  # 侧边栏选中的标签（AND 语义）
        self._has_filter = False
        self._filter_text = ""

    def set_selected_tags(self, tags: list[str]) -> None:
        """设置侧边栏选中的标签（AND 语义）并刷新筛选。"""
        self.selected_tags = list(tags or [])
        self.invalidateFilter()

    def setFilterFixedString(self, text):  # type: ignore
        raw = (text or "").strip()
        self._has_filter = bool(raw)
        self._filter_text = raw.lower()
        # 仍调用 super()，保持代理内部 pattern 状态一致
        super().setFilterFixedString(text if text is not None else "")
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        """根据复选框状态和角色过滤调整过滤逻辑"""
        model = self.sourceModel()
        if model is None:
            return False

        # 角色过滤
        if self.use_role_filter and self.filter_role:
            role_index = model.index(source_row, 1)  # 1 是角色列
            role_value = model.data(role_index, Qt.ItemDataRole.DisplayRole)
            if role_value != self.filter_role:
                return False

        # 标签筛选（AND）：选中的标签必须全部存在于条目中
        if self.selected_tags:
            try:
                item = model._data[source_row]  # type: ignore[attr-defined]
            except (AttributeError, IndexError):
                return False
            entry_tags = item.get("tags") or []
            if not isinstance(entry_tags, list):
                return False
            entry_set = {str(t) for t in entry_tags if isinstance(t, str)}
            if not all(t in entry_set for t in self.selected_tags):
                return False

        # 搜索过滤
        if not self._has_filter:
            # 没有关键字：show_all_data 决定是否全显
            return bool(self.show_all_data)

        # 有关键字：在 SEARCHABLE_FIELDS 上做子串匹配，以及 tags 文本
        try:
            item = model._data[source_row]  # type: ignore[attr-defined]
        except (AttributeError, IndexError):
            return False
        ft = self._filter_text
        for field in self._SEARCHABLE_FIELDS:
            val = str(item.get(field) or "").lower()
            if ft in val:
                return True
        # 标签文本也纳入关键字匹配
        tags = item.get("tags") or []
        if isinstance(tags, list):
            joined = " ".join(str(t) for t in tags).lower()
            if ft in joined:
                return True
        return False
