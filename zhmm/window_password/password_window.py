#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03

from PyQt6.QtCore import (QAbstractTableModel, QSortFilterProxyModel, Qt,
                          QTimer, pyqtSignal)
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QMessageBox,
                             QPushButton, QTableView, QVBoxLayout, QWidget)

import zhmm
from zhmm.sm_data import SmData
from zhmm.ui_data_exporter import UiDataExporter
from zhmm.ui_defined import ZhmmFileInfo
from zhmm.utils import date_util
from zhmm.utils.log import logger
from zhmm.window_password.add_password_dialog import AddPasswordDialog


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
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return self.headers[section]
        return None

    def setZhData(self, data):
        self.beginResetModel()
        self._data = data
        self.endResetModel()


class CustomProxyModel(QSortFilterProxyModel):
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


class PasswordWindow(QWidget):
    """密码管理界面"""

    def __init__(self, info: ZhmmFileInfo, parent=None):
        super().__init__(parent)
        self.info = info
        if "sm_data" not in info or not info["sm_data"]:
            self.gl_data = SmData()
        else:
            self.gl_data = info["sm_data"]
        self.gl_data.file_path = info["file_path"]
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建搜索区域
        search_layout = QHBoxLayout()

        # 添加类别筛选下拉框
        self.ini_role_ui(search_layout)

        search_label = QLabel("搜索:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键字搜索账号、网站、备注等")
        self.search_input.textChanged.connect(self.filter_passwords)
        QTimer.singleShot(0, self.search_input.setFocus)  # 延迟聚焦到密码输入框

        # 在搜索区域添加复选框
        self.show_all_checkbox = QCheckBox("仅显示搜索结果")
        self.show_all_checkbox.setChecked(True)
        self.show_all_checkbox.setToolTip("勾选：仅显示匹配关键字的数据；未填写关键字时不显示任何数据。取消勾选：显示全部数据（仍受类别筛选影响）。")
        self.show_all_checkbox.toggled.connect(self.toggle_show_all)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.show_all_checkbox)  # 新增复选框

        main_layout.addLayout(search_layout)

        # 创建表格视图
        self.table_view = QTableView()
        self.table_model = PasswordTableModel(self.gl_data.mm["data"])

        # 设置选择模式（新增这两行）
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        # 创建代理模型用于过滤（替换为自定义代理模型）
        self.proxy_model = CustomProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)  # -1 表示搜索所有列

        self.table_view.setModel(self.proxy_model)
        # 默认隐藏密码列（索引3）
        self.table_view.setColumnHidden(3, False)

        # 新增单元格点击事件处理
        self.table_view.clicked.connect(self.copy_cell_to_clipboard)

        # 新增双击事件处理
        self.table_view.doubleClicked.connect(self.edit_selected_password)

        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)

        # 设置自适应列宽策略（新增以下三行）
        header = self.table_view.horizontalHeader()
        if header:
            # 获取表格字体度量
            font_metrics = self.table_view.fontMetrics()

            # 计算列宽方法
            def calculate_column_width(string, margin=8):
                # 计算内容最大宽度
                content_width = font_metrics.boundingRect(string).width()
                return content_width + margin

            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

            # 固定列宽度
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(0, calculate_column_width("8888888888"))
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(1, calculate_column_width("个人个人"))
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(4, calculate_column_width("+86888888888888"))
            header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(8, calculate_column_width("8888888888"))

        main_layout.addWidget(self.table_view)
        self.setup_ui_button(main_layout)

        # 添加状态标签（在表格下方）
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        main_layout.addWidget(self.status_label)

        # 初始化一次状态提示
        self.filter_passwords()

    def setup_ui_button(self, main_layout):
        # 创建按钮区域
        button_layout = QHBoxLayout()

        # 新增删除按钮
        delete_button = QPushButton("删除")
        delete_button.setMaximumWidth(128)
        delete_button.clicked.connect(self.delete_selected_password)

        add_button = QPushButton("添加")
        add_button.setMaximumWidth(128)
        add_button.clicked.connect(self.add_password)

        button_layout.addStretch()
        button_layout.addWidget(delete_button)
        button_layout.addWidget(add_button)

        main_layout.addLayout(button_layout)

    def ini_role_ui(self, search_layout):# 添加类别筛选下拉框
        role_filter_label = QLabel("类别:")
        self.role_filter_combo = QComboBox()
        self.reset_roles_option()
        self.role_filter_combo.currentIndexChanged.connect(self.filter_role)

        # 设置下拉框最小宽度
        self.role_filter_combo.setMinimumWidth(100)
        # 设置下拉列表视图的宽度自适应内容
        self.role_filter_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        search_layout.addWidget(role_filter_label)
        search_layout.addWidget(self.role_filter_combo)
        pass


    def reset_roles_option(self):
        self.role_filter_combo.clear()
        self.role_filter_combo.addItem("全部", "")  # 添加一个默认选项
        if self.gl_data.mm and "roles" in self.gl_data.mm:
            roles = self.gl_data.mm["roles"]
            if roles is not None:
                for role in roles:
                    self.role_filter_combo.addItem(role, role)
        pass

    def filter_role(self):
        # 获取选中的角色
        selected_role = self.role_filter_combo.currentData()

        # 设置角色过滤
        self.proxy_model.use_role_filter = bool(selected_role)  # 如果有选中角色则启用角色过滤
        self.proxy_model.filter_role = selected_role  # 设置过滤的角色值

        # 触发过滤刷新
        self.filter_passwords()

    def filter_passwords(self):
        """过滤密码列表"""
        search_text = self.search_input.text()

        # 设置通配符过滤
        self.proxy_model.setFilterFixedString(search_text)

        # 状态提示：根据复选框与关键字内容更新
        if self.show_all_checkbox.isChecked():
            # 仅显示搜索结果
            if not self.proxy_model._has_filter:
                self.status_label.setText("请输入关键字以显示结果")
            else:
                self.status_label.setText(f"已按“{search_text}”筛选")
        else:
            # 显示全部数据（仍受类别筛选影响）
            self.status_label.setText("显示全部数据")

    def toggle_show_all(self, checked):
        """复选框状态切换处理"""
        self.proxy_model.show_all_data = not checked
        # 触发过滤刷新
        self.filter_passwords()

    def add_password(self):
        """添加密码"""
        roles = self.gl_data.mm.get("roles") or []
        dialog = AddPasswordDialog(self, roles)
        dialog.confirm_button.clicked.connect(lambda: self.confirm_add_password(dialog))
        dialog.added_role.connect(lambda new_role: self.add_role(new_role))
        dialog.exec()

    def add_role(self, new_role):
        if "roles" not in self.gl_data.mm or self.gl_data.mm["roles"] is None:
            self.gl_data.mm["roles"] = []
        self.gl_data.mm["roles"].append(new_role)
        self.save()
        self.reset_roles_option()
        pass

    def confirm_add_password(self, dialog):
        """确认添加密码"""
        password_data = dialog.get_password_data()

        # 验证必填字段
        if not password_data["userID"]:
            QMessageBox.warning(dialog, "警告", "账号不能为空")
            return

        # 添加到数据模型
        try:
            # 使用gl_data添加数据
            self.gl_data.add(password_data)
            if self.save():
                # 更新表格模型
                self.table_model.setZhData(self.gl_data.mm["data"])
                QMessageBox.information(dialog, "成功", "账号密码添加成功")
                dialog.accept()
            else:
                QMessageBox.critical(dialog, "错误", "添加失败，无法保存数据")
        except Exception as e:
            logger.error(f"添加密码出错: {str(e)}")
            QMessageBox.critical(dialog, "错误", f"添加出错: {str(e)}")

    def export_passwords(self):
        """导出密码列表"""
        UiDataExporter.export_to_file(self.gl_data.mm["data"])

    def refresh_data(self):
        """刷新数据"""
        self.table_model.setZhData(self.gl_data.mm["data"])

    def delete_selected_password(self):
        """删除选中的密码项"""
        selected = self.table_view.selectionModel().selectedRows()  # type: ignore
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要删除的项目")
            return

        # 获取代理模型索引并转换为源模型索引
        proxy_index = selected[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        row = source_index.row()

        try:
            # 确认删除
            reply = QMessageBox.question(
                self,
                "确认删除",
                "确定要删除该账号记录吗？此操作不可恢复！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                # 从数据源中删除
                deleted_item = self.gl_data.mm["data"].pop(row)
                # 更新表格
                self.table_model.setZhData(self.gl_data.mm["data"])
                # 保存更改
                if not self.save():
                    self.gl_data.mm["data"].insert(row, deleted_item)  # 回滚
                    QMessageBox.critical(self, "错误", "删除失败，数据保存错误")
        except Exception as e:
            logger.error(f"删除账号出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def edit_selected_password(self):
        """编辑选中的密码项"""
        selected = self.table_view.selectionModel().selectedRows()  # type: ignore
        if not selected:
            QMessageBox.warning(self, "警告", "请先选择要编辑的项目")
            return

        # 获取源模型数据
        proxy_index = selected[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        row = source_index.row()
        edit_data = self.gl_data.mm["data"][row]

        # 创建编辑对话框并传入数据
        roles = self.gl_data.mm.get("roles") or []
        dialog = AddPasswordDialog(self, roles, edit_data=edit_data)
        dialog.confirm_button.clicked.connect(
            lambda: self._process_edit_result(dialog, row)
        )
        dialog.added_role.connect(lambda new_role: self.add_role(new_role))
        dialog.setWindowTitle("编辑账号信息")
        dialog.confirm_button.setText("确认修改")
        dialog.exec()

    def _process_edit_result(self, dialog, original_row):
        """处理编辑结果"""
        new_data = dialog.get_password_data()

        # 保留原始ID和创建时间
        new_data["id"] = self.gl_data.mm["data"][original_row]["id"]
        new_data["ctime"] = self.gl_data.mm["data"][original_row].get(
            "ctime", date_util.timestamp_int()
        )

        # 验证必填字段
        if not new_data["userID"]:
            QMessageBox.warning(dialog, "警告", "账号不能为空")
            return

        try:
            # 更新数据
            self.gl_data.mm["data"][original_row] = new_data
            if self.save():
                self.table_model.setZhData(self.gl_data.mm["data"])
                QMessageBox.information(dialog, "成功", "修改成功")
                dialog.accept()
            else:
                QMessageBox.critical(dialog, "错误", "修改失败，无法保存数据")
        except Exception as e:
            logger.error(f"编辑账号出错: {str(e)}")
            QMessageBox.critical(dialog, "错误", f"修改失败: {str(e)}")

    def confirm_modify_password(self, dialog):
        """确认添加密码"""
        password_data = dialog.get_password_data()

        # 验证必填字段
        if not password_data["userID"] or not password_data["pwd"]:
            QMessageBox.warning(dialog, "警告", "账号和密码不能为空")
            return

        # 添加到数据模型
        try:
            # 使用gl_data添加数据
            self.gl_data.add(password_data)
            if self.save():
                # 更新表格模型
                self.table_model.setZhData(self.gl_data.mm["data"])
                QMessageBox.information(dialog, "成功", "账号密码添加成功")
                dialog.accept()
            else:
                QMessageBox.critical(dialog, "错误", "添加失败，无法保存数据")
        except Exception as e:
            logger.error(f"添加密码出错: {str(e)}")
            QMessageBox.critical(dialog, "错误", f"添加出错: {str(e)}")

    def copy_cell_to_clipboard(self, index):
        """复制单元格内容到剪贴板"""
        if index.isValid():
            text = self.proxy_model.data(index, Qt.ItemDataRole.DisplayRole)
            QApplication.clipboard().setText(str(text))  # type: ignore
            # 更新状态标签
            self.status_label.setText("已复制到剪贴板")
            # 定时清空剪贴板，避免残留敏感信息
            QTimer.singleShot(10000, lambda: QApplication.clipboard().clear())  # type: ignore
            QTimer.singleShot(2000, lambda: self.status_label.setText(""))

    def save(self):
        ret: bool = self.gl_data.save()
        # 存储云数据是可选的
        zhmm.config.upload_cloud(self.gl_data.file_path)
        return ret
