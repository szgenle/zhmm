#!/usr/bin/env python3
"""密码表格数据模型"""

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt

# 密码掩码占位符（固定 8 个圆点，不暴露真实长度）
_PWD_MASK = "•" * 8
# 密码列索引
_PWD_COL = 3
# “显示”按钮列索引（紧跟在密码列后面）
_REVEAL_COL = 4


class PasswordTableModel(QAbstractTableModel):
    """密码表格数据模型"""

    def __init__(self, data=None):
        super().__init__()
        self.headers = ["ID", "类别", "账号", "密码", "显示", "手机", "邮箱", "网站", "备注", "更新时间"]
        self.keys = [
            "id",
            "role",
            "userID",
            "pwd",
            "",  # “显示”列无直接字段，单独处理
            "phone",
            "email",
            "url",
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
            # 其他列：原样返回
            key = self.keys[col]
            return str(item.get(key, ""))

        if role == Qt.ItemDataRole.EditRole:
            # EditRole 始终返回真实值，供复制/导出等使用
            if col == _PWD_COL:
                return str(item.get("pwd", ""))
            if col == _REVEAL_COL:
                return ""
            key = self.keys[col]
            return str(item.get(key, ""))

        if role == Qt.ItemDataRole.TextAlignmentRole and col == _REVEAL_COL:
            return int(Qt.AlignmentFlag.AlignCenter)

        if role == Qt.ItemDataRole.ToolTipRole and col == _REVEAL_COL:
            return "点击显示/隐藏密码"

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

    def flags(self, index: QModelIndex):  # type: ignore[override]
        base = super().flags(index)
        # “显示”列不可选中/不可编辑，但可交互左键点击
        if index.column() == _REVEAL_COL:
            return Qt.ItemFlag.ItemIsEnabled
        return base


class CustomProxyModel(QSortFilterProxyModel):
    """自定义代理模型（支持灵活的过滤逻辑）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_all_data = False  # 控制是否显示所有数据
        self.filter_role = ""  # 角色过滤值
        self.use_role_filter = False  # 是否使用角色过滤
        self._has_filter = False

    def setFilterRegularExpression(self, pattern):  # type: ignore
        self._has_filter = bool(pattern and pattern.strip())
        super().setFilterRegularExpression(pattern)

    def setFilterFixedString(self, text):  # type: ignore
        self._has_filter = bool(text and text.strip())
        super().setFilterFixedString(text)

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        """根据复选框状态和角色过滤调整过滤逻辑"""
        # 首先检查是否需要角色过滤
        if self.use_role_filter and self.filter_role:
            model = self.sourceModel()
            if model is None:
                return False
            role_index = model.index(source_row, 1)  # 1是角色列
            role_value = model.data(role_index, Qt.ItemDataRole.DisplayRole)
            if role_value != self.filter_role:
                return False

        if self.show_all_data:
            # 正常过滤
            return super().filterAcceptsRow(source_row, source_parent)
        else:
            if not self._has_filter:
                return False
            # 当没有过滤条件时，隐藏所有数据
            return super().filterAcceptsRow(source_row, source_parent)
