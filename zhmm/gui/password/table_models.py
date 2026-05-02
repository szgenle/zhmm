#!/usr/bin/env python3
"""密码表格数据模型"""

from PyQt6.QtCore import QAbstractTableModel, QSortFilterProxyModel, Qt


class PasswordTableModel(QAbstractTableModel):
    """密码表格数据模型"""

    def __init__(self, data=None):
        super().__init__()
        self.headers = ["ID", "类别", "账号", "密码", "手机", "邮箱", "网站", "备注", "更新时间"]
        self.keys = [
            "id",
            "role",
            "userID",
            "pwd",
            "phone",
            "email",
            "url",
            "desc",
            "utime",
        ]
        self._data = data if data else []

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            row = index.row()
            col = index.column()
            item = self._data[row]
            key = self.keys[col]

            # 返回对应的数据，如果不存在则返回空字符串
            return str(item.get(key, ""))

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None

    def setZhData(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()


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
