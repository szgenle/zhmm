#!/usr/bin/env python3
# coding=utf-8
# @Date: 2024-07-03
# @LastEditTime: 2024-07-03

from PyQt6.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTableView, QHeaderView,
                             QMessageBox, QDialog, QComboBox, QFormLayout, QCheckBox, QApplication)

from zhmm.data_exporter import DataExporter
from zhmm.sm_data import SmData
from zhmm.ui.login_dialog import ZhmmFileInfo
from zhmm.utils import date_util
from zhmm.utils.log import logger


class PasswordTableModel(QAbstractTableModel):
    """密码表格数据模型"""

    def __init__(self, data=None):
        super().__init__()
        self.headers = ['ID', '类别', '账号', '密码', '手机', '邮箱', '网站', '备注', '更新时间']
        self.keys = ['id', 'role', 'userID', 'pwd', 'phone', 'email', 'url', 'desc', 'utime']
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
            return str(item.get(key, ''))

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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_all_data = True  # 新增控制属性

    def filterAcceptsRow(self, source_row, source_parent):
        """根据复选框状态调整过滤逻辑"""
        if self.show_all_data:
            return super().filterAcceptsRow(source_row, source_parent)
        if not self.filterRegularExpression().pattern():
            return False
        return super().filterAcceptsRow(source_row, source_parent)


class AddPasswordDialog(QDialog):
    """添加密码对话框"""

    def __init__(self, parent=None, edit_data=None):
        super().__init__(parent)
        self.setWindowTitle("添加账号密码")
        self.setFixedSize(500, 400)

        # 创建布局
        layout = QVBoxLayout()

        # 标题标签
        title_label = QLabel("请输入账号密码信息")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 添加一些间距
        layout.addSpacing(20)

        # 创建表单布局
        form_layout = QFormLayout()

        # 类别选择
        self.role_combo = QComboBox()
        self.role_combo.addItems(["个人", "工作", "社交", "金融", "其他"])
        form_layout.addRow("类别:", self.role_combo)

        # 账号输入
        self.userid_input = QLineEdit()
        self.userid_input.setPlaceholderText("请输入账号")
        form_layout.addRow("账号:", self.userid_input)

        # 密码输入
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        form_layout.addRow("密码:", self.password_input)

        # 手机输入
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("请输入手机号码（可选）")
        form_layout.addRow("手机:", self.phone_input)

        # 邮箱输入
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入邮箱（可选）")
        form_layout.addRow("邮箱:", self.email_input)

        # 网站输入
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入网站地址（可选）")
        form_layout.addRow("网站:", self.url_input)

        # 备注输入
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("请输入备注信息（可选）")
        form_layout.addRow("备注:", self.desc_input)

        layout.addLayout(form_layout)

        # 添加一些间距
        layout.addSpacing(20)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 确认按钮
        self.confirm_button = QPushButton("确认添加")
        button_layout.addWidget(self.confirm_button)

        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 如果是编辑模式，填充数据
        if edit_data:
            self._populate_data(edit_data)

    def _populate_data(self, data):
        """填充编辑数据"""
        index = self.role_combo.findText(data['role'])
        if index >= 0:
            self.role_combo.setCurrentIndex(index)
        self.userid_input.setText(data['userID'])
        self.password_input.setText(data['pwd'])
        self.phone_input.setText(data.get('phone', ''))
        self.email_input.setText(data.get('email', ''))
        self.url_input.setText(data.get('url', ''))
        self.desc_input.setText(data.get('desc', ''))

    def get_password_data(self):
        """获取表单数据"""
        return {
            'id': date_util.timestamp_int(),
            'role': self.role_combo.currentText(),
            'userID': self.userid_input.text().strip(),
            'pwd': self.password_input.text().strip(),
            'phone': self.phone_input.text().strip(),
            'email': self.email_input.text().strip(),
            'url': self.url_input.text().strip(),
            'desc': self.desc_input.text().strip(),
            'utime': date_util.timestamp_int()
        }


class PasswordManagerWidget(QWidget):
    """密码管理界面"""

    def __init__(self, info: ZhmmFileInfo, parent=None):
        super().__init__(parent)
        self.info = info
        if 'sm_data' not in info or not info['sm_data']:
            self.gl_data = SmData()
        else:
            self.gl_data = info['sm_data']
        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建按钮区域
        button_layout = QHBoxLayout()

        add_button = QPushButton("添加")
        add_button.clicked.connect(self.add_password)

        # 新增编辑按钮
        self.edit_button = QPushButton("编辑")
        self.edit_button.clicked.connect(self.edit_selected_password)

        # 新增删除按钮
        self.delete_button = QPushButton("删除")
        self.delete_button.clicked.connect(self.delete_selected_password)

        export_button = QPushButton("导出")
        export_button.clicked.connect(self.export_passwords)

        button_layout.addWidget(add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)  # 添加删除按钮
        button_layout.addWidget(export_button)

        main_layout.addLayout(button_layout)

        # 创建搜索区域
        search_layout = QHBoxLayout()

        search_label = QLabel("搜索:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键字搜索账号、网站、备注等")
        self.search_input.textChanged.connect(self.filter_passwords)
        QTimer.singleShot(0, self.search_input.setFocus)  # 延迟聚焦到密码输入框

        # 在搜索区域添加复选框
        self.show_all_checkbox = QCheckBox("隐藏非搜索数据")
        self.show_all_checkbox.setChecked(False)
        self.show_all_checkbox.toggled.connect(self.toggle_show_all)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.show_all_checkbox)  # 新增复选框

        main_layout.addLayout(search_layout)

        # 创建表格视图
        self.table_view = QTableView()
        self.table_model = PasswordTableModel(self.gl_data.mm['data'])

        # 设置选择模式（新增这两行）
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        # 创建代理模型用于过滤（替换为自定义代理模型）
        self.proxy_model = CustomProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)  # -1 表示搜索所有列

        self.table_view.setModel(self.proxy_model)

        # 新增单元格点击事件处理
        self.table_view.clicked.connect(self.copy_cell_to_clipboard)

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
            header.resizeSection(0, calculate_column_width('8888888888'))
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(1, calculate_column_width('个人个人'))
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(3, calculate_column_width('********'))
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(4, calculate_column_width('+86888888888888'))
            header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(8, calculate_column_width('8888888888'))

        main_layout.addWidget(self.table_view)

        # 添加状态标签（在表格下方）
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-size: 12px;")
        main_layout.addWidget(self.status_label)

    def filter_passwords(self):
        """过滤密码列表"""
        search_text = self.search_input.text()
        self.proxy_model.setFilterWildcard(f"*{search_text}*" if search_text else "")

    def toggle_show_all(self, checked):
        """复选框状态切换处理"""
        self.proxy_model.show_all_data = not checked
        # 触发过滤刷新
        self.filter_passwords()

    def add_password(self):
        """添加密码"""
        dialog = AddPasswordDialog(self)
        dialog.confirm_button.clicked.connect(lambda: self.confirm_add_password(dialog))
        dialog.exec()

    def confirm_add_password(self, dialog):
        """确认添加密码"""
        password_data = dialog.get_password_data()

        # 验证必填字段
        if not password_data['userID'] or not password_data['pwd']:
            QMessageBox.warning(dialog, "警告", "账号和密码不能为空")
            return

        # 添加到数据模型
        try:
            # 使用gl_data添加数据
            self.gl_data.add(password_data)
            if self.gl_data.save(self.info['file_path']):
                # 更新表格模型
                self.table_model.setZhData(self.gl_data.mm['data'])
                QMessageBox.information(dialog, "成功", "账号密码添加成功")
                dialog.accept()
            else:
                QMessageBox.critical(dialog, "错误", "添加失败，无法保存数据")
        except Exception as e:
            logger.error(f"添加密码出错: {str(e)}")
            QMessageBox.critical(dialog, "错误", f"添加出错: {str(e)}")

    def export_passwords(self):
        """导出密码列表"""
        DataExporter.export_to_file(self.gl_data.mm['data'])

    def refresh_data(self):
        """刷新数据"""
        self.table_model.setZhData(self.gl_data.mm['data'])

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
                self, "确认删除",
                "确定要删除该密码记录吗？此操作不可恢复！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                # 从数据源中删除
                deleted_item = self.gl_data.mm['data'].pop(row)
                # 更新表格
                self.table_model.setZhData(self.gl_data.mm['data'])
                # 保存更改
                if self.gl_data.save(self.info['file_path']):
                    QMessageBox.information(self, "成功", "删除成功")
                else:
                    self.gl_data.mm['data'].insert(row, deleted_item)  # 回滚
                    QMessageBox.critical(self, "错误", "删除失败，数据保存错误")
        except Exception as e:
            logger.error(f"删除密码出错: {str(e)}")
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
        edit_data = self.gl_data.mm['data'][row]

        # 创建编辑对话框并传入数据
        dialog = AddPasswordDialog(self, edit_data=edit_data)
        dialog.confirm_button.clicked.connect(lambda: self._process_edit_result(dialog, row))
        dialog.setWindowTitle("编辑密码信息")
        dialog.confirm_button.setText("确认修改")
        dialog.exec()

    def _process_edit_result(self, dialog, original_row):
        """处理编辑结果"""
        new_data = dialog.get_password_data()

        # 保留原始ID和创建时间
        new_data['id'] = self.gl_data.mm['data'][original_row]['id']
        new_data['ctime'] = self.gl_data.mm['data'][original_row].get('ctime', date_util.timestamp_int())

        # 验证必填字段
        if not new_data['userID'] or not new_data['pwd']:
            QMessageBox.warning(dialog, "警告", "账号和密码不能为空")
            return

        try:
            # 更新数据
            self.gl_data.mm['data'][original_row] = new_data
            if self.gl_data.save(self.info['file_path']):
                self.table_model.setZhData(self.gl_data.mm['data'])
                QMessageBox.information(dialog, "成功", "修改成功")
            else:
                QMessageBox.critical(dialog, "错误", "修改失败，无法保存数据")
        except Exception as e:
            logger.error(f"编辑密码出错: {str(e)}")
            QMessageBox.critical(dialog, "错误", f"修改失败: {str(e)}")

    def confirm_modify_password(self, dialog):
        """确认添加密码"""
        password_data = dialog.get_password_data()

        # 验证必填字段
        if not password_data['userID'] or not password_data['pwd']:
            QMessageBox.warning(dialog, "警告", "账号和密码不能为空")
            return

        # 添加到数据模型
        try:
            # 使用gl_data添加数据
            self.gl_data.add(password_data)
            if self.gl_data.save(self.info['file_path']):
                # 更新表格模型
                self.table_model.setZhData(self.gl_data.mm['data'])
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
            QTimer.singleShot(2000, lambda: self.status_label.setText(""))

